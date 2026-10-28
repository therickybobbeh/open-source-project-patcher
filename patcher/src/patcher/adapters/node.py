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
            cmd = ["yarn", "install", "--mode=update-lockfile"] if (cwd / ".yarnrc.yml").exists() else ["yarn", "install", "--ignore-scripts", "--frozen-lockfile=false"]
        for b in mine:
            if section.get(b.name) == b.installed or kind == "yarn":
                # upstream already pins this package (to the vulnerable version): move its pin; yarn
                # resolutions don't take installed-version selectors portably
                section[b.name] = b.to
            else:
                # pin exactly the vulnerable installed version, so other major lines aren't dragged along
                section[f"{b.name}@{b.installed}"] = b.to
            res.changes.append(Change(kind, b.target, b.name, b.installed, b.to, ", ".join(b.reasons)))
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
