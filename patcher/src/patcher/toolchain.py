"""Install the recipe's toolchains with mise and return the environment that activates them.

Without mise on PATH (e.g. a developer laptop) we fall back to whatever is installed, and rely
on GOTOOLCHAIN to fetch the Go version the plan requires."""

from __future__ import annotations

import json
from pathlib import Path

from .ecosystems import ECOSYSTEMS
from .models import Toolchain
from .proc import CommandError, log, output, run, which
from .versions import try_parse


def go_spec(recipe_go: str | None, required: str | None) -> str | None:
    """mise Go spec: the recipe's major.minor (mise picks its newest patch, which carries the
    stdlib fixes) unless the plan requires a newer minor. A requirement never lowers it."""
    req = try_parse("gomod", required) if required else None
    if not recipe_go:
        return f"{req.major}.{req.minor}" if req else None
    cur = try_parse("gomod", recipe_go)
    if req and cur and (req.major, req.minor) > (cur.major, cur.minor):
        return f"{req.major}.{req.minor}"
    return recipe_go


# which toolchain fields each test framework needs (ecosystems declare theirs in ecosystems.py)
FRAMEWORK_FIELDS = {"go": ["go"], "surefire": ["java", "maven"], "gradle": ["java"], "jest": ["node"], "vitest": ["node"],
                    "mocha": ["node"], "pytest": ["python"]}
LANGUAGE_FIELDS = {k: list(e.toolchain) for k, e in ECOSYSTEMS.items()} | FRAMEWORK_FIELDS


def effective(tc: Toolchain, recipe, src: Path | None) -> Toolchain:
    """Fill toolchain fields the recipe leaves unset from what the checkout declares (go.mod, .nvmrc,
    packageManager, requires-python, maven.compiler.release, ...), only for languages the recipe uses."""
    if src is None or recipe is None:
        return tc
    from . import detect

    kinds = {e.type for e in recipe.ecosystems} | ({recipe.tests.framework} if recipe.tests else set())
    wanted = {f for k in kinds for f in LANGUAGE_FIELDS.get(k, [])}
    node_dirs = [d for e in recipe.ecosystems if e.type in ("npm", "pnpm", "yarn") for d in e.dirs]
    python_dirs = [d for e in recipe.ecosystems if e.type == "python" for d in e.dirs]
    go_dirs = [d for e in recipe.ecosystems if e.type == "gomod" for d in e.dirs]
    found = detect.toolchain(src, node_dirs, python_dirs, go_dirs)
    if "maven" in wanted and "maven" not in found:
        found["maven"] = "3"  # newest Maven 3.x when the project doesn't say
    fill = {k: v for k, v in found.items() if k in wanted and getattr(tc, k, None) in (None, "")}
    return tc.model_copy(update=fill) if fill else tc


def mise_specs(tc: Toolchain, requires: dict[str, str]) -> list[str]:
    specs: list[str] = []
    go = go_spec(tc.go, requires.get("go"))
    if go:
        specs.append(f"go@{go}")
    if tc.rust and tc.rust != "from-repo":
        specs.append(f"rust@{tc.rust}")
    if tc.java:
        specs.append(f"java@{tc.java}")
    if tc.maven:
        specs.append(f"maven@{tc.maven}")
    if tc.node:
        specs.append(f"node@{tc.node}")
    if tc.pnpm:
        specs.append(f"pnpm@{tc.pnpm}")
    if tc.yarn:
        specs.append(f"yarn@{tc.yarn}")
    if tc.python:
        specs.append(f"python@{tc.python}")
    specs += [f"{k}@{v}" for k, v in tc.extra.items()]
    return specs


def _local_go(env: dict[str, str]) -> str | None:
    try:
        return output(["go", "env", "GOVERSION"], env=env).strip().removeprefix("go")
    except (CommandError, FileNotFoundError):
        return None


def activate(tc: Toolchain, env: dict[str, str], requires: dict[str, str] | None = None, src: Path | None = None,
             recipe=None) -> dict[str, str]:
    requires = requires or {}
    env = dict(env)
    tc = effective(tc, recipe, src)
    specs = mise_specs(tc, requires)
    use_repo = bool(tc.repoMise) and src is not None
    if not which("mise"):
        go_req = requires.get("go")
        local = _local_go(env)
        req_v, local_v = try_parse("gomod", go_req), try_parse("gomod", local)
        if req_v and (local_v is None or req_v > local_v):
            # GOTOOLCHAIN downloads the fixed release; a go.mod that needs newer still wins
            env["GOTOOLCHAIN"] = f"go{go_req}+auto"
        if specs or use_repo:
            log(f"mise not found; using toolchains from PATH (wanted: {' '.join(specs) or 'repo mise config'})")
        return env
    if not specs and not use_repo:
        return env
    try:
        if use_repo:
            # the upstream repo pins its own tools (e.g. apollo router: rust, cargo-nextest, protoc)
            run(["mise", "trust", "--yes", str(src)], env=env, check=False, quiet=True)
            if isinstance(tc.repoMise, list):
                for tool in tc.repoMise:  # in order: e.g. cargo-binstall before cargo:* tools
                    run(["mise", "install", "--yes", tool], cwd=src, env=env, capture=False)
            else:
                run(["mise", "install", "--yes"], cwd=src, env=env, capture=False)
        if specs:
            run(["mise", "install", "--yes", *specs], cwd=src if use_repo else None, env=env, capture=False)
        data = json.loads(output(["mise", "env", "--json", *specs], cwd=src if use_repo else None, env=env))
    except CommandError as e:
        raise RuntimeError(f"toolchain install failed for {specs or 'repo mise config'}: {e.tail}") from e
    env.update({k: str(v) for k, v in data.items()})
    return env
