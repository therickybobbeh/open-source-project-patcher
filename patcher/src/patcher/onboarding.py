"""`patcher init`: draft a recipe for a new upstream project from what its checkout declares.

The draft is a starting point. It is commented, every guess is marked TODO, and it should be
checked with `patcher run <name> --skip-tests --skip-build` before it's trusted."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from . import detect

NON_FINAL_STAGE = re.compile(r"(?i)^(build|builder|base|deps|dev|debug|test|tools?|download(er)?|stager|.*-(build|builder|base|dev|debug|deps))$")
CI_TEST_LINE = re.compile(r"(make\s+test\S*|go test\b.*|npm (run )?test\b.*|pnpm (run )?test\b.*|yarn (run )?test\b.*|pytest\b.*|"
                          r"tox\b.*|mvn\b.*\b(test|verify|install)\b.*|\./gradlew\b.*\btest\b.*|cargo (test|nextest)\b.*)")


def tag_pattern(tag: str) -> str:
    """`v4.1.6` -> `^v4\\.1\\.\\d+$` (the line of the newest release)."""
    m = re.match(r"^(?P<prefix>.*?)(?P<major>\d+)\.(?P<minor>\d+)\.\d+$", tag)
    if not m:
        return "^" + re.escape(tag) + "$"
    return f"^{re.escape(m.group('prefix'))}{m.group('major')}\\.{m.group('minor')}\\.\\d+$"


def _yaml_str(s: str) -> str:
    return json.dumps(s)  # JSON strings are valid YAML scalars


# workflow lines that can't hold a command: comments, step names, bare mapping keys (`pytest:`)
CI_NOT_A_COMMAND = re.compile(r"^\s*(#|-?\s*name:|[\w.-]+:\s*$)")


def ci_test_hints(src: Path) -> list[str]:
    hints: list[str] = []
    for wf in sorted((src / ".github" / "workflows").glob("*.y*ml")) if (src / ".github" / "workflows").is_dir() else []:
        for line in wf.read_text(errors="replace").splitlines():
            if CI_NOT_A_COMMAND.match(line):
                continue
            m = CI_TEST_LINE.search(line)
            if m and "run" in line or (m and line.strip().startswith(("make", "go ", "npm", "pnpm", "yarn", "pytest", "tox", "mvn", "./gradlew", "cargo"))):
                hint = m.group(0).strip().rstrip("`'\"")
                if hint not in hints:
                    hints.append(hint)
    return hints[:8]


def infer_tests(src: Path, ecos: list[dict]) -> dict:
    kinds = {e["type"]: e for e in ecos}
    makefile = (src / "Makefile").read_text(errors="replace") if (src / "Makefile").exists() else ""
    if "gomod" in kinds:
        note = "upstream Makefile has a `test` target" if re.search(r"(?m)^test:", makefile) else ""
        return {"framework": "go", "command": "go test {{skip_args}} ./...", "note": note}
    if "maven" in kinds:
        return {"framework": "surefire", "command": "mvn -B -ntp -DskipITs {{skip_args}} install",
                "junit": ["**/target/surefire-reports/TEST-*.xml"]}
    if "gradle" in kinds:
        return {"framework": "gradle", "command": "./gradlew --no-daemon test {{skip_args}}", "junit": ["**/build/test-results/test/*.xml"]}
    if "python" in kinds:
        return _python_tests(src, kinds["python"]["dirs"][0])
    for pm in ("pnpm", "yarn", "npm"):
        if pm in kinds:
            d = src / kinds[pm]["dirs"][0]
            pkg = json.loads((d / "package.json").read_text()) if (d / "package.json").exists() else {}
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            framework = next((f for f in ("vitest", "jest", "mocha") if f in deps), "generic")
            install = {"pnpm": "pnpm install --frozen-lockfile", "yarn": "yarn install --frozen-lockfile", "npm": "npm ci"}[pm]
            run = {"npm": "npm test --"}.get(pm, f"{pm} test")
            cd = "" if kinds[pm]["dirs"][0] in (".", "") else f"cd {kinds[pm]['dirs'][0]} && "
            return {"framework": framework, "setup": [cd + install], "command": f"{cd}{run} {{{{skip_args}}}}".rstrip()}
    return {}


def _python_tests(src: Path, rel: str) -> dict:
    """pytest in a project-local .venv (never the shared mise Python), installed the way the lockfile says."""
    from .adapters.python import DEFAULT_TOOL_VERSIONS, detect_tool

    d = src / rel
    cd = "" if rel in (".", "") else f"cd {rel} && "
    tool = detect_tool(d)
    pyproject = tomllib.loads((d / "pyproject.toml").read_text()) if (d / "pyproject.toml").exists() else {}
    extras = list(pyproject.get("project", {}).get("optional-dependencies", {}))
    groups = list(pyproject.get("dependency-groups", {}))
    if tool == "uv":
        setup = "uv sync --frozen --all-extras --all-groups"
    elif tool == "poetry":
        setup = f"POETRY_VIRTUALENVS_IN_PROJECT=true uvx --from poetry=={DEFAULT_TOOL_VERSIONS['poetry']} poetry install --all-extras"
    elif tool == "pipenv":
        setup = f"PIPENV_VENV_IN_PROJECT=1 uvx --from pipenv=={DEFAULT_TOOL_VERSIONS['pipenv']} pipenv install --dev --deploy"
    else:  # uv (pinned in the patcher image) as the installer: fast, and knows dependency groups;
        # --seed puts pip in the venv too, for suites that run `python -m pip`
        steps = ["uv venv --seed .venv"]
        reqs = next((r for r in ("requirements.txt", "requirements-dev.txt", "requirements/dev.txt") if (d / r).exists()), None)
        if reqs:
            steps.append(f"uv pip install --python .venv -r {reqs}")
        if pyproject or (d / "setup.py").exists():
            extra = next((e for e in ("test", "tests", "testing", "dev") if e in extras), None)
            group = next((g for g in ("test", "tests", "testing", "dev") if g in groups), None)
            steps.append("uv pip install --python .venv -e " + (f"'.[{extra}]'" if extra else ".") + (f" --group {group}" if group else ""))
        setup = " && ".join(steps)
    return {"framework": "pytest", "setup": [cd + setup],
            # the venv's bin on PATH, as in an activated env: suites run console scripts (alembic, ...)
            "command": f'{cd}PATH="$PWD/.venv/bin:$PATH" python -m pytest -p no:cacheprovider --junitxml=junit.xml {{{{skip_args}}}}',
            "junit": [f"{rel}/junit.xml".removeprefix("./") if cd else "junit.xml"],
            "note": "TODO: check the test dependencies and services against upstream CI (hints below)"}


def infer_images(src: Path, ecos: list[dict], repo: str, image: str | None) -> list[dict]:
    files = next((e["files"] for e in ecos if e["type"] == "dockerfile"), [])
    root = [f for f in files if f == "Dockerfile"] or files[:1]
    if not root:
        return []
    dockerfile = root[0]
    targets = [t for t in detect.dockerfile_targets(src / dockerfile) if not NON_FINAL_STAGE.match(t)]
    if targets and detect.final_stage_unnamed(src / dockerfile):
        targets = [None, *targets]  # the default target builds an image as well
    image_repo = image.rsplit(":", 1)[0] if image and ":" in image.rsplit("/", 1)[-1] else image
    readme = next((p for p in (src / "README.md", src / "README") if p.exists()), None)
    refs = sorted(set(re.findall(r"\b((?:ghcr\.io|quay\.io|docker\.io|registry\.k8s\.io|public\.ecr\.aws)/[\w.-]+/[\w./-]+)",
                                 readme.read_text(errors="replace")))) if readme else []
    name = repo.rsplit("/", 1)[-1]

    def guess(n: str) -> str | None:
        if image_repo and (image_repo.rsplit("/", 1)[-1] == n or len(targets) <= 1):
            return image_repo
        exact = next((r for r in refs if r.rsplit("/", 1)[-1] == n), None)
        if exact:
            return exact
        if image_repo:  # sibling images usually live next to the one you run (quay.io/argoproj/<name>)
            return f"{image_repo.rsplit('/', 1)[0]}/{n}"
        return next((r for r in refs if n in r.rsplit("/", 1)[-1]), None)

    out = []
    for t in targets or [None]:
        entry = {"name": t or name, "dockerfile": dockerfile}
        if t:
            entry["target"] = t
        entry["upstream"] = guess(t or name)
        out.append(entry)
    return out


def draft(src: Path, name: str, repo: str, tag: str, image: str | None = None) -> str:
    ecos = detect.ecosystems(src)
    node_dirs = [d for e in ecos if e["type"] in ("npm", "pnpm", "yarn") for d in e["dirs"]]
    python_dirs = [d for e in ecos if e["type"] == "python" for d in e["dirs"]]
    tc = detect.toolchain(src, node_dirs, python_dirs)
    tests = infer_tests(src, ecos)
    images = infer_images(src, ecos, repo, image)
    hints = ci_test_hints(src)

    y = ["# yaml-language-server: $schema=../schema/recipe.schema.json",
         f"# Draft generated by `patcher init` from {repo}@{tag}. Review every TODO, then run:",
         f"#   patcher run {name} --skip-tests --skip-build     (patching only), then a full run.",
         f"name: {name}",
         f"description: {_yaml_str(repo + ' (TODO: describe)')}",
         "source:",
         f"  repo: {repo}",
         "  lines:   # TODO: one line per release line you run",
         f"    - tagPattern: '{tag_pattern(tag)}'"]
    if tc:
        y.append("toolchain:   # detected from the checkout; recipe values win over detection at run time anyway")
        y += [f"  {k}: {_yaml_str(v)}" for k, v in tc.items()]
    y.append("ecosystems:")
    for e in ecos:
        y.append(f"  - type: {e['type']}")
        for k, v in e.items():
            if k != "type":
                y.append(f"    {k}: {json.dumps(v)}")
    y.append("scan:")
    y.append("  skipDirs: []   # TODO: unshipped trees with lockfiles (examples, docs, test fixtures, tooling)")
    if tests:
        y.append("tests:")
        y.append(f"  framework: {tests['framework']}")
        if tests.get("setup"):
            y.append(f"  setup: {json.dumps(tests['setup'])}")
        y.append(f"  command: {_yaml_str(tests['command'])}")
        if tests.get("junit"):
            y.append(f"  junit: {json.dumps(tests['junit'])}")
        if tests.get("note"):
            y.append(f"  # {tests['note']}")
    else:
        y.append("# tests: TODO (no test command could be inferred)")
    if hints:
        y.append("# upstream CI runs:")
        y += [f"#   {h}" for h in hints]
    if images:
        y.append("build:")
        y.append("  platforms: [linux/amd64, linux/arm64]")
        y.append("  images:")
        for img in images:
            y.append(f"    - name: {img['name']}")
            y.append(f"      upstream: {img['upstream'] or 'null   # TODO: the published image this replaces'}")
            y.append(f"      dockerfile: {img['dockerfile']}")
            if img.get("target"):
                y.append(f"      target: {img['target']}")
            y.append('      smoke: ["--help"]   # TODO: a command that proves the image starts')
            y.append("      # ownBinaries: [usr/local/bin/...]   # TODO: what this source builds (the rest is reported as bundled)")
    else:
        y.append("# build: TODO (no Dockerfile found; add one under patches/<name>/files/ or use mode: image-only)")
    return "\n".join(y) + "\n"


def draft_image_only(name: str, image_repo: str, tag: str, platforms: list[str]) -> str:
    return "\n".join([
        "# yaml-language-server: $schema=../schema/recipe.schema.json",
        f"# Draft generated by `patcher init --image` for {image_repo}:{tag}: no public source was found",
        "# (no org.opencontainers.image.source label), so this is an image-only recipe: scan, Copa, mirror, report.",
        f"name: {name}",
        f"description: {_yaml_str(image_repo + ' (closed source)')}",
        "mode: image-only",
        "source:",
        f"  repo: {image_repo}",
        "  lines:",
        f"    - tagPattern: '{tag_pattern(tag)}'",
        "build:",
        f"  platforms: {json.dumps(platforms)}",
        "  images:",
        f"    - name: {name}",
        f"      upstream: {image_repo}",
    ]) + "\n"
