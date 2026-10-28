"""Cargo: `cargo update <crate>@<installed> --precise <ver>` (lockfile-only, semver-compatible)."""

from __future__ import annotations

from ..models import CargoEco
from ..proc import CommandError, run
from .base import Change, Ctx, Failure, Result, expand_dirs


def apply(ctx: Ctx, eco: CargoEco) -> Result:
    res = Result()
    dirs = expand_dirs(ctx.src, eco.dirs, "Cargo.lock")
    for b in ctx.plan.for_ecosystem("cargo"):
        if b.dir not in dirs:
            res.failures.append(Failure("cargo", b.target, b.name, b.to, f"workspace {b.dir!r} is not listed in the recipe's cargo.dirs"))
            continue
        manifest = ctx.src / b.dir / "Cargo.toml"
        try:
            # `name@installed` disambiguates crates present in several versions
            run(["cargo", "update", "--manifest-path", str(manifest), "-p", f"{b.name}@{b.installed}", "--precise", b.to],
                env=ctx.env, log_file=ctx.log)
            res.changes.append(Change("cargo", b.target, b.name, b.installed, b.to, ", ".join(b.reasons)))
        except CommandError as e:
            hint = ""
            if "failed to select a version" in e.tail or "candidate versions found which didn't match" in e.tail:
                hint = "needs-human: the fix is outside the semver range a Cargo.toml requires (bump the parent crate or add [patch.crates-io]); "
            res.failures.append(Failure("cargo", b.target, b.name, b.to, hint + e.tail[-1500:]))
    return res
