"""npm / pnpm / yarn: version overrides for transitive deps, then regenerate the lockfile."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from ..models import NodeEco
from ..proc import CommandError, output, run
from .base import Change, Ctx, Failure, Result, expand_dirs

LOCKFILES = {"npm": "package-lock.json", "pnpm": "pnpm-lock.yaml", "yarn": "yarn.lock"}


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text())


def _write_json(p: Path, data: dict, original: str) -> None:
    indent = 2
    m = re.search(r"\n( +)\"", original)
    if m:
        indent = len(m.group(1))
    p.write_text(json.dumps(data, indent=indent, ensure_ascii=False) + ("\n" if original.endswith("\n") else ""))


def _pnpm_major(env) -> int:
    try:
        return int(output(["pnpm", "--version"], env=env).strip().split(".")[0])
    except (CommandError, ValueError):
        return 0


def _major(version: str) -> int:
    m = re.match(r"v?(\d+)", version)
    return int(m.group(1)) if m else -1


def _yarn_majors(lockfile: Path, name: str) -> set[int]:
    """Major versions of `name` installed per yarn.lock (classic and berry formats)."""
    majors: set[int] = set()
    if not lockfile.exists():
        return majors
    header = re.compile(rf'^"?{re.escape(name)}@')
    current = False
    for line in lockfile.read_text().splitlines():
        if line and not line.startswith(" "):
            current = any(header.match(part.strip()) for part in line.rstrip(":").split(","))
        elif current:
            m = re.match(r'^\s+version:?\s+"?([^"\s]+)"?', line)
            if m:
                majors.add(_major(m.group(1)))
    return majors


def _yarn_install_cmd(cwd: Path, ctx: Ctx) -> list[str]:
    if (cwd / ".yarnrc.yml").exists():  # yarn berry
        return ["yarn", "install", "--mode=update-lockfile"]
    rc = cwd / ".yarnrc"
    if rc.exists():
        # classic: projects often set `--install.frozen-lockfile true` in .yarnrc, which would refuse the
        # regeneration; keep every other setting (registry, ...) through a copy without that line
        kept = [l for l in rc.read_text().splitlines() if "frozen-lockfile" not in l]
        tmp = ctx.log.parent / "yarnrc.patcher"
        tmp.write_text("\n".join(kept) + "\n")
        return ["yarn", "install", "--ignore-scripts", "--non-interactive", "--no-default-rc", "--use-yarnrc", str(tmp)]
    return ["yarn", "install", "--ignore-scripts", "--non-interactive"]


def apply(ctx: Ctx, eco: NodeEco) -> Result:
    res = Result()
    kind = eco.type
    lock = LOCKFILES[kind]
    dirs = expand_dirs(ctx.src, eco.dirs, lock)
    bumps = ctx.plan.for_ecosystem(kind)
    for d in dirs:
        mine = [b for b in bumps if b.dir == d]
        if not mine:
            continue
        cwd = ctx.src / d
        pkg_path = cwd / "package.json"
        original = pkg_path.read_text()
        pkg = json.loads(original)
        ws = cwd / "pnpm-workspace.yaml"
        ws_data = None
        if kind == "npm":
            section = pkg.setdefault("overrides", {})
            cmd = ["npm", "install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund"]
        elif kind == "pnpm" and (ws.exists() or _pnpm_major(ctx.env) >= 11):
            ws_data = (yaml.safe_load(ws.read_text()) if ws.exists() else None) or {}
            section = ws_data.setdefault("overrides", {})
            cmd = ["pnpm", "install", "--lockfile-only", "--ignore-scripts"]
        elif kind == "pnpm":
            section = pkg.setdefault("pnpm", {}).setdefault("overrides", {})
            cmd = ["pnpm", "install", "--lockfile-only", "--ignore-scripts"]
        else:
            section = pkg.setdefault("resolutions", {})
            cmd = _yarn_install_cmd(cwd, ctx)
        applied = []
        for b in mine:
            if kind == "yarn":
                # yarn resolutions can't target one installed version portably, so `name: to` moves
                # every copy: only safe when all installed copies share the fix's major version
                majors = _yarn_majors(cwd / lock, b.name)
                if len(majors) > 1 or (majors and _major(b.to) not in majors):
                    res.failures.append(Failure(kind, b.target, b.name, b.to,
                                                f"needs-human: yarn.lock has {b.name} on majors {sorted(majors)}; a yarn resolution "
                                                f"would force all of them to {b.to}"))
                    continue
                section[b.name] = b.to
            elif section.get(b.name) == b.installed:
                # upstream already pins this package (to the vulnerable version): move its pin
                section[b.name] = b.to
            else:
                # pin exactly the vulnerable installed version, so other major lines aren't dragged along
                section[f"{b.name}@{b.installed}"] = b.to
            applied.append(b)
            res.changes.append(Change(kind, b.target, b.name, b.installed, b.to, ", ".join(b.reasons)))
        if not applied:
            continue
        mine = applied
        if ws_data is not None:
            ws.write_text(yaml.safe_dump(ws_data, sort_keys=False))
        else:
            _write_json(pkg_path, pkg, original)
        try:
            run(cmd, cwd=cwd, env=ctx.env, log_file=ctx.log, capture=False)
        except CommandError as e:
            for b in mine:
                res.failures.append(Failure(kind, b.target, b.name, b.to, f"lockfile regeneration failed: {e.tail[-1500:]}"))
            res.changes = [c for c in res.changes if c.target not in {b.target for b in mine}]
    return res
