"""Go modules: `go get mod@ver` / `go mod edit -replace`, replace groups, toolchain directive, tidy."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..models import GoModEco
from ..planner import Bump
from ..proc import CommandError, output, run
from ..versions import parse_semver, try_parse
from .base import Change, Ctx, Failure, Result, expand_dirs


def mod_info(src: Path, d: str, env: dict[str, str]) -> dict:
    return json.loads(output(["go", "mod", "edit", "-json"], cwd=src / d, env=env))


def _v(version: str) -> str:
    return version if version.startswith("v") else f"v{version}"


def apply(ctx: Ctx, eco: GoModEco) -> Result:
    res = Result()
    env = {**ctx.env, "GOWORK": "off", "GOFLAGS": "-mod=mod"}
    dirs = expand_dirs(ctx.src, eco.dirs, "go.mod")
    bumps = ctx.plan.for_ecosystem("gomod")
    for b in bumps:
        if b.dir not in dirs:
            res.failures.append(Failure("gomod", b.target, b.name, b.to, f"module dir {b.dir!r} is not listed in the recipe's gomod.dirs"))
    groups = [(re.compile(g.pattern), g) for g in eco.replaceGroups]
    want_go = ctx.plan.toolchain.get("go")
    for d in dirs:
        mine = [b for b in bumps if b.dir == d]
        # without bumps, a module is only touched to raise an existing `toolchain` directive
        if not mine and not (want_go and eco.bumpToolchainDirective and mod_info(ctx.src, d, env).get("Toolchain")):
            continue
        res.extend(_apply_dir(ctx, eco, d, mine, groups, env))
    return res


def _apply_dir(ctx: Ctx, eco: GoModEco, d: str, bumps: list[Bump], groups, env) -> Result:
    res = Result()
    target = f"{d}/go.mod" if d != "." else "go.mod"
    before = mod_info(ctx.src, d, env)
    replaces = {r["Old"]["Path"]: r for r in before.get("Replace") or []}
    requires = {r["Path"]: r["Version"] for r in before.get("Require") or []}

    edits: list[str] = []  # go mod edit flags
    gets: dict[str, str] = {}  # module -> version for `go get`
    handled: set[str] = set()  # a group moves once even if several members have CVEs
    # highest target first: when several members of a replace group have CVEs, the group moves to the max
    for b in sorted(bumps, key=lambda b: try_parse("gomod", _v(b.to)) or parse_semver("0"), reverse=True):
        to = _v(b.to)
        if b.name in handled:
            continue
        rep = replaces.get(b.name)
        if rep and not rep["New"].get("Version"):
            res.failures.append(Failure("gomod", target, b.name, to, f"replaced by local path {rep['New']['Path']}; bump it there"))
            continue
        moved = [(b.name, b.installed)]
        for rx, g in groups:
            if rx.search(b.name) and g.sameVersion:
                for path, ver in list(requires.items()) + [(p, (r["New"].get("Version") or "")) for p, r in replaces.items()]:
                    if (path != b.name and path not in handled and rx.search(path) and _v(ver) == _v(b.installed)
                            and all(path != m for m, _ in moved)):
                        moved.append((path, ver))
        if len(moved) > 1:
            res.flags.add("replaceGroupMoved")
        for path, old in moved:
            handled.add(path)
            if path in replaces and replaces[path]["New"].get("Version"):
                new_path = replaces[path]["New"]["Path"]
                old_spec = path + (f"@{replaces[path]['Old']['Version']}" if replaces[path]["Old"].get("Version") else "")
                edits.append(f"-replace={old_spec}={new_path}@{to}")
                if path in requires:
                    edits.append(f"-require={path}@{to}")
                res.flags.add("replaceGroupMoved")
            else:
                gets[path] = to
            res.changes.append(Change("gomod", target, path, old, to, ", ".join(b.reasons) if path == b.name else f"moves with {b.name} (replace group)"))

    want_go = ctx.plan.toolchain.get("go")
    if want_go and eco.bumpToolchainDirective and before.get("Toolchain"):
        cur = try_parse("gomod", before["Toolchain"])
        new = try_parse("gomod", want_go)
        if cur and new and new > cur:
            edits.append(f"-toolchain=go{want_go}")
            res.changes.append(Change("gomod", target, "toolchain", before["Toolchain"], f"go{want_go}", "Go stdlib CVEs"))

    cwd = ctx.src / d
    if not edits and not gets:
        return res
    if edits:
        run(["go", "mod", "edit", *edits], cwd=cwd, env=env, log_file=ctx.log)
    if gets:
        _go_get(cwd, gets, env, ctx, res, target)
    try:
        run(["go", "mod", "tidy"], cwd=cwd, env=env, log_file=ctx.log, capture=False)
    except CommandError as e:
        res.failures.append(Failure("gomod", target, "*", "", f"go mod tidy failed: {e.tail[-2000:]}"))
    if (cwd / "vendor").is_dir():
        run(["go", "mod", "vendor"], cwd=cwd, env=env, log_file=ctx.log, check=False)

    after = mod_info(ctx.src, d, env)
    if after.get("Go") != before.get("Go"):
        res.flags.add("goDirectiveChanged")
        res.changes.append(Change("gomod", target, "go", before.get("Go") or "", after.get("Go") or "", "required by a bumped dependency"))
        _raise_requirement(ctx, after.get("Go"))
    if after.get("Toolchain"):
        _raise_requirement(ctx, after["Toolchain"].removeprefix("go"))
    return res


def _go_get(cwd: Path, gets: dict[str, str], env, ctx: Ctx, res: Result, target: str) -> None:
    specs = [f"{m}@{v}" for m, v in gets.items()]
    try:
        run(["go", "get", *specs], cwd=cwd, env=env, log_file=ctx.log, capture=False)
        return
    except CommandError:
        pass
    # Isolate the failing module(s) so one bad bump doesn't block the rest. A batch usually fails
    # because one target is below what another target requires (x/net@v0.60.0 needs x/text>=v0.42.0
    # while the plan asked x/text@v0.41.0), and `go get` would happily *downgrade* in that case, so
    # skip anything already selected at or above its target.
    for spec in specs:
        mod, ver = spec.rsplit("@", 1)
        cur = try_parse("gomod", _selected(cwd, mod, env))
        want = try_parse("gomod", ver)
        if cur and want and cur >= want:
            continue
        try:
            run(["go", "get", spec], cwd=cwd, env=env, log_file=ctx.log)
        except CommandError as e:
            res.changes = [c for c in res.changes if not (c.name == mod and c.target == target)]
            res.failures.append(Failure("gomod", target, mod, ver, e.tail[-1500:]))


def _selected(cwd: Path, mod: str, env) -> str | None:
    """Version of `mod` the module graph currently selects."""
    try:
        return output(["go", "list", "-m", "-f", "{{.Version}}", mod], cwd=cwd, env=env).strip() or None
    except CommandError:
        return None


def _raise_requirement(ctx: Ctx, version: str | None) -> None:
    if not version:
        return
    cur = try_parse("gomod", ctx.requires.get("go", "0"))
    new = try_parse("gomod", version)
    if new and (cur is None or new > cur):
        ctx.requires["go"] = version
