"""Gradle: direct dependencies declared in the version catalog get their version edited; everything else
is pinned through a generated constraints script. Gradle dependency constraints take part in conflict
resolution, so they raise a version but never downgrade one that something else needs higher."""

from __future__ import annotations

import posixpath
import re
import tomllib
from pathlib import Path

from ..models import GradleEco
from ..planner import Bump
from ..proc import CommandError, run
from ..versions import parse_maven
from .base import Change, Ctx, Failure, Result

CONSTRAINTS = "gradle/patcher-constraints.gradle"
BUILD_FILES = ("build.gradle", "build.gradle.kts")
SETTINGS_FILES = ("settings.gradle", "settings.gradle.kts")


def is_root(d: Path) -> bool:
    return any((d / f).exists() for f in BUILD_FILES + SETTINGS_FILES)


def _roots(src: Path, patterns: list[str]) -> list[str]:
    out = []
    for pat in patterns:
        for p in sorted(src.glob(pat)) if any(c in pat for c in "*?[") else [src / pat]:
            if p.is_dir() and is_root(p):
                rel = p.relative_to(src).as_posix() or "."
                if rel not in out:
                    out.append(rel)
    return out


def _root_for(target_dir: str, roots: list[str]) -> str | None:
    for r in sorted(roots, key=len, reverse=True):
        if r == "." or target_dir == r or target_dir.startswith(r + "/"):
            return r
    return None


def apply(ctx: Ctx, eco: GradleEco) -> Result:
    res = Result()
    bumps = ctx.plan.for_ecosystem("gradle")
    roots = _roots(ctx.src, eco.dirs)
    per_root: dict[str, dict[str, Bump]] = {}
    for b in bumps:
        root = _root_for(posixpath.dirname(b.target) or ".", roots)
        if root is None:
            res.failures.append(Failure("gradle", b.target, b.name, b.to, f"{b.target} is not under any of gradle.dirs {eco.dirs}"))
            continue
        cur = per_root.setdefault(root, {}).get(b.name)
        if cur is None or parse_maven(b.to) > parse_maven(cur.to):
            per_root[root][b.name] = b
    for root, wanted in per_root.items():
        base = ctx.src / root
        pins: list[Bump] = []
        catalog = base / eco.catalog
        for name, b in sorted(wanted.items()):
            note = ", ".join(b.reasons)
            if catalog.exists() and bump_catalog(catalog, name, b.to):
                res.changes.append(Change("gradle", posixpath.normpath(posixpath.join(root, eco.catalog)), name, b.installed, b.to, note))
            else:
                pins.append(b)
        if pins:
            write_constraints(base, pins)
            wire_constraints(base)
            res.changes += [Change("gradle", posixpath.normpath(posixpath.join(root, CONSTRAINTS)), b.name, b.installed, b.to,
                                   ", ".join(b.reasons)) for b in pins]
        if list(base.rglob("gradle.lockfile")):
            try:
                _relock(ctx, base)
            except CommandError as e:
                res.failures.append(Failure("gradle", root, "*", "", f"re-locking failed: {e.tail[-1500:]}"))
    return res


# --- version catalog ---------------------------------------------------------------------------


def bump_catalog(catalog: Path, ga: str, version: str) -> bool:
    """Edit the version of `group:artifact` in a version catalog. A shared `version.ref` is only moved
    when every library using it belongs to the same group (a family like jackson-*), else False."""
    text = catalog.read_text()
    data = tomllib.loads(text)
    group = ga.split(":", 1)[0]
    libs = data.get("libraries", {})
    for alias, spec in libs.items():
        coords, ver = _lib(spec)
        if coords != ga:
            continue
        if isinstance(ver, dict) and "ref" in ver:
            ref = ver["ref"]
            users = [_lib(s)[0] for s in libs.values() if isinstance(_lib(s)[1], dict) and _lib(s)[1].get("ref") == ref]
            if any(u.split(":", 1)[0] != group for u in users if u):
                return False
            new, n = re.subn(rf'(?m)^(\s*{re.escape(ref)}\s*=\s*")[^"]*(")', lambda m: m.group(1) + version + m.group(2), text, count=1)
        elif isinstance(spec, str):  # alias = "g:a:1.2.3"
            new, n = re.subn(rf'(?m)^(\s*{re.escape(alias)}\s*=\s*"{re.escape(ga)}:)[^"]*(")', lambda m: m.group(1) + version + m.group(2), text)
        else:  # alias = { module = "g:a", version = "1.2.3" }
            new, n = re.subn(rf'(?m)^(\s*{re.escape(alias)}\s*=\s*\{{.*?\bversion\s*=\s*")[^"]*(")', lambda m: m.group(1) + version + m.group(2), text)
        if n:
            catalog.write_text(new)
            return True
    return False


def _lib(spec) -> tuple[str, object]:
    if isinstance(spec, str):
        parts = spec.split(":")
        return ":".join(parts[:2]), (parts[2] if len(parts) > 2 else None)
    module = spec.get("module") or (f"{spec['group']}:{spec['name']}" if "group" in spec and "name" in spec else "")
    return module, spec.get("version")


# --- constraints script --------------------------------------------------------------------------


def write_constraints(base: Path, pins: list[Bump]) -> None:
    """A resolution rule, not dependency constraints: plugins that manage versions with their own rule
    (Spring's io.spring.dependency-management applies its BOM that way) rewrite constraints too, so a
    plain `constraints { }` block loses to them. This rule runs after theirs and only ever raises."""
    entries = "\n".join(f"    '{b.name}': ['{b.to}', '{', '.join(b.reasons)[:180]}']," for b in pins)
    script = base / CONSTRAINTS
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(
        "// Generated by support-images patcher: minimum versions for vulnerable dependencies.\n"
        "// Every request for these modules is raised to at least the fixed version, including versions set by\n"
        "// other rules (e.g. Spring dependency-management BOMs). Higher requests are left alone: nothing is\n"
        "// downgraded. Registered after each project is evaluated, so it runs after the rules plugins add.\n"
        "def patcherMinimums = [\n" + entries + "\n]\n"
        "def patcherOlder = { String a, String b ->\n"
        "    def x = (a =~ /\\d+/).collect { it as long }, y = (b =~ /\\d+/).collect { it as long }\n"
        "    for (int i = 0; i < Math.max(x.size(), y.size()); i++) {\n"
        "        long u = i < x.size() ? x[i] : 0L, v = i < y.size() ? y[i] : 0L\n"
        "        if (u != v) { return u < v }\n"
        "    }\n"
        "    return false\n"
        "}\n"
        "def patcherRule = { Project p ->\n"
        "    p.configurations.configureEach { conf ->\n"
        "        if (conf.state != Configuration.State.UNRESOLVED) { return }\n"
        "        conf.resolutionStrategy.eachDependency { details ->\n"
        "            def min = patcherMinimums[\"${details.requested.group}:${details.requested.name}\".toString()]\n"
        "            def current = details.target.version\n"
        "            if (min != null && current && patcherOlder(current, min[0])) {\n"
        "                details.useVersion(min[0])\n"
        "                details.because(\"support-images patcher: ${min[1]}\")\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "}\n"
        "allprojects { p ->\n"
        "    if (p.state.executed) { patcherRule(p) } else { p.afterEvaluate { patcherRule(p) } }\n"
        "}\n")


def wire_constraints(base: Path) -> None:
    groovy, kts = base / "build.gradle", base / "build.gradle.kts"
    if kts.exists():
        line, target = f'apply(from = "{CONSTRAINTS}")', kts
    else:
        line, target = f"apply from: '{CONSTRAINTS}'", groovy
    text = target.read_text() if target.exists() else ""
    if CONSTRAINTS not in text:
        target.write_text(text.rstrip("\n") + ("\n\n" if text else "") + f"// support-images patcher\n{line}\n")


def _relock(ctx: Ctx, base: Path) -> None:
    gradlew = ["./gradlew"] if (base / "gradlew").exists() else ["gradle"]
    projects = []
    for lock in base.rglob("gradle.lockfile"):
        rel = lock.parent.relative_to(base).as_posix()
        projects.append("dependencies" if rel == "." else f":{rel.replace('/', ':')}:dependencies")
    run([*gradlew, "--no-daemon", "--write-locks", *sorted(set(projects))], cwd=base, env=ctx.env, log_file=ctx.log, capture=False)


def init_script_for_skips(patterns: list[str]) -> str:
    """Gradle init script excluding tests (used by the `gradle` test framework)."""
    excludes = "\n".join(f"            excludeTestsMatching {p!r}" for p in patterns)
    return ("allprojects {\n"
            "    tasks.withType(Test).configureEach {\n"
            "        filter {\n" + excludes + "\n"
            "            failOnNoMatchingTests = false\n"
            "        }\n"
            "    }\n"
            "}\n")
