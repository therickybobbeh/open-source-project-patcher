"""Read what an upstream checkout declares about itself: toolchain versions (go.mod, .nvmrc,
packageManager, requires-python, maven.compiler.release, ...) and which ecosystems it uses.
Used to fill unset recipe toolchain fields and by `patcher init` to draft recipes."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

PREFERRED_PYTHON = "3.12"

SKIP_PARTS = {"node_modules", "vendor", "testdata", "test", "tests", "examples", "docs", ".git", "third_party", "hack", "e2e"}


def _read(p: Path) -> str:
    try:
        return p.read_text(errors="replace")
    except OSError:
        return ""


def _major(spec: str) -> str | None:
    m = re.search(r"(\d+)", spec)
    return m.group(1) if m else None


def go_version(src: Path, dirs: list[str] = ()) -> str | None:
    """Go major.minor the module(s) need: the highest `toolchain`/`go` line of the root go.mod and of the
    module dirs given (globs allowed), e.g. a repo whose only module is in `ecr-login/`."""
    best = None
    for d in [".", *dirs]:
        for mod_dir in (sorted(src.glob(d)) if any(c in d for c in "*?[") else [src / d]):
            text = _read(mod_dir / "go.mod")
            m = re.search(r"(?m)^toolchain go(\d+\.\d+)", text) or re.search(r"(?m)^go (\d+\.\d+)", text)
            if m and (best is None or tuple(map(int, m.group(1).split("."))) > tuple(map(int, best.split(".")))):
                best = m.group(1)
    return best


def node_versions(d: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for f in (".nvmrc", ".node-version"):
        if (d / f).exists():
            major = _major(_read(d / f).strip().lstrip("v"))
            if major:
                out["node"] = major
                break
    pkg = d / "package.json"
    if pkg.exists():
        try:
            data = json.loads(_read(pkg))
        except json.JSONDecodeError:
            data = {}
        engines = (data.get("engines") or {}).get("node")
        if engines and "node" not in out:
            majors = [int(x) for x in re.findall(r"(\d+)(?:\.\d+)*", engines)]
            if majors:
                out["node"] = str(max(majors))
        pm = data.get("packageManager") or ""
        m = re.match(r"(pnpm|yarn)@(\d+\.\d+\.\d+)", pm)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def python_version(d: Path) -> str | None:
    pv = _read(d / ".python-version").strip().splitlines()
    if pv and re.match(r"\d+\.\d+", pv[0]):
        return ".".join(pv[0].split(".")[:2])
    pyproject = d / "pyproject.toml"
    if pyproject.exists():
        try:
            req = tomllib.loads(_read(pyproject)).get("project", {}).get("requires-python")
        except tomllib.TOMLDecodeError:
            req = None
        if req:
            from packaging.specifiers import InvalidSpecifier, SpecifierSet

            try:
                spec = SpecifierSet(req)
            except InvalidSpecifier:
                return None
            if spec.contains(PREFERRED_PYTHON + ".0"):
                return PREFERRED_PYTHON
            for minor in range(9, 20):  # lowest allowed 3.x
                if spec.contains(f"3.{minor}.0"):
                    return f"3.{minor}"
    return None


def java_version(d: Path) -> str | None:
    pom = _read(d / "pom.xml")
    for tag in ("maven.compiler.release", "release", "java.version", "maven.compiler.target", "maven.compiler.source"):
        m = re.search(rf"<{re.escape(tag)}>\s*(?:1\.)?(\d+)\s*</{re.escape(tag)}>", pom)
        if m:
            return f"temurin-{m.group(1)}"
    for f in ("build.gradle", "build.gradle.kts"):
        text = _read(d / f)
        m = (re.search(r"JavaLanguageVersion\.of\(\s*(\d+)\s*\)", text) or re.search(r"JavaVersion\.VERSION_(?:1_)?(\d+)", text)
             or re.search(r"(?:source|target)Compatibility\s*=\s*['\"]?(?:1\.)?(\d+)", text))
        if m:
            return f"temurin-{m.group(1)}"
    jv = _read(d / ".java-version").strip()
    if jv:
        return f"temurin-{_major(jv)}"
    m = re.search(r"(?m)^java=(\d+)", _read(d / ".sdkmanrc"))
    if m:
        return f"temurin-{m.group(1)}"
    return None


def toolchain(src: Path, node_dirs: list[str] = (), python_dirs: list[str] = (), go_dirs: list[str] = ()) -> dict[str, str]:
    """Toolchain versions declared by the checkout (keys match `Toolchain` fields)."""
    out: dict[str, str] = {}
    go = go_version(src, go_dirs)
    if go:
        out["go"] = go
    for d in [*node_dirs, "."]:
        for k, v in node_versions(src / d).items():
            out.setdefault(k, v)
    if node_dirs and "node" not in out:
        node = node_from_dockerfiles(src)
        if node:
            out["node"] = node
    for d in [*python_dirs, "."]:
        py = python_version(src / d)
        if py:
            out.setdefault("python", py)
            break
    java = java_version(src)
    if java:
        out["java"] = java
    return out


# --- ecosystems (for `patcher init`) -------------------------------------------------------------


def _skip(rel: Path) -> bool:
    return any(part in SKIP_PARTS or part.startswith(".") for part in rel.parts[:-1])


def ecosystems(src: Path) -> list[dict]:
    """Ecosystem entries (recipe `ecosystems:` items) for the manifests found in the checkout."""
    found: dict[str, set[str]] = {}

    def add(kind: str, f: Path) -> None:
        rel = f.relative_to(src)
        if not _skip(rel):
            found.setdefault(kind, set()).add(rel.parent.as_posix() or ".")

    for f in src.rglob("*"):
        if not f.is_file() or ".git" in f.parts or "node_modules" in f.parts:
            continue
        name = f.name
        if name == "go.mod":
            add("gomod", f)
        elif name == "Cargo.lock":
            add("cargo", f)
        elif name == "pom.xml" and not (f.parent.parent / "pom.xml").exists():
            add("maven", f)  # reactor roots only
        elif name in ("settings.gradle", "settings.gradle.kts"):
            add("gradle", f)
        elif name == "package-lock.json":
            add("npm", f)
        elif name == "pnpm-lock.yaml":
            add("pnpm", f)
        elif name == "yarn.lock":
            add("yarn", f)
        elif name in ("uv.lock", "poetry.lock", "Pipfile.lock", "requirements.in") or re.fullmatch(r"requirements.*\.txt", name):
            add("python", f)
    out = []
    order = ["gomod", "cargo", "maven", "gradle", "npm", "pnpm", "yarn", "python"]
    for kind in order:
        dirs = sorted(found.get(kind, []), key=lambda x: (x != ".", x))
        if not dirs:
            continue
        if kind == "maven":
            out.append({"type": "maven", "poms": [f"{d}/pom.xml" if d != "." else "pom.xml" for d in dirs]})
        else:
            out.append({"type": kind, "dirs": dirs})
    dockerfiles = sorted(f.relative_to(src).as_posix() for f in src.rglob("*Dockerfile*")
                         if f.is_file() and not _skip(f.relative_to(src)) and not f.name.endswith((".md", ".dockerignore")))
    if dockerfiles:
        out.append({"type": "dockerfile", "files": dockerfiles})
    return out


def dockerfile_targets(path: Path) -> list[str]:
    """Named stages that are images in their own right: no later stage copies from them or builds on them
    (`COPY --from=builder`, `FROM base AS final` mark builder/base as intermediate)."""
    text = _read(path)
    named = re.findall(r"(?im)^FROM\s+(?:--\S+\s+)*\S+\s+AS\s+(\S+)\s*$", text)
    used = {u.lower() for u in re.findall(r"(?im)--from=([\w.-]+)", text)}
    used |= {u.lower() for u in re.findall(r"(?im)^FROM\s+(?:--\S+\s+)*([\w.-]+)(?:\s+AS\s+\S+)?\s*$", text)}
    return [n for n in named if n.lower() not in used]


def final_stage_unnamed(path: Path) -> bool:
    """True when the Dockerfile's last stage has no name: the default build target is an image too."""
    froms = re.findall(r"(?im)^FROM\s+(?:--\S+\s+)*\S+(\s+AS\s+\S+)?\s*$", _read(path))
    return bool(froms) and not froms[-1]


def node_from_dockerfiles(src: Path) -> str | None:
    """Node major of a `FROM node:<major>` stage (UI builders), when the project declares nothing else."""
    for f in sorted(src.glob("Dockerfile*")):
        m = re.search(r"(?im)^FROM\s+(?:--\S+\s+)*(?:docker\.io/(?:library/)?)?node:(\d+)", _read(f))
        if m:
            return m.group(1)
    return None
