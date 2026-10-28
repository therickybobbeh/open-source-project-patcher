"""Copacetic: patch remaining fixable OS packages in a built image."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .proc import CommandError, log, run, which
from .scan import scan_image


@dataclass
class CopaResult:
    patched_ref: str | None
    os_fixable_before: int
    vex: Path | None = None
    error: str | None = None
    skipped: str | None = None


def patch(image: str, out_tag: str, workdir: Path, *, platforms: list[str], severities: list[str], push: bool = False,
          src: str | None = None) -> CopaResult:
    """Scan `image` for fixable OS packages per platform; if any, `copa patch` it to `out_tag`.

    `out_tag` is a tag only (Copa keeps the repository). With `push`, `image` must be in a
    registry and the result is pushed; otherwise it is loaded into the local daemon (needs the
    containerd image store, or Docker's BuildKit, to see local images).
    """
    reports = workdir / "copa-reports"
    reports.mkdir(parents=True, exist_ok=True)
    fixable = 0
    for p in platforms:
        rep = scan_image(image, reports / f"{p.replace('/', '-')}.json", severities=severities, platform=p,
                         pkg_types="os", ignore_unfixed=True, src=src)
        fixable += len(rep.fixable())
    if fixable == 0:
        return CopaResult(None, 0, skipped="no fixable OS packages")
    if not which("copa"):
        return CopaResult(None, fixable, skipped="copa not installed")
    vex = workdir / "copa.vex.json"
    args = ["copa", "patch", "-i", image, "-t", out_tag, "--timeout", "30m", "-f", "openvex", "-o", str(vex)]
    args += ["-r", str(reports) if len(platforms) > 1 else str(next(reports.glob("*.json")))]
    if push:
        args.append("--push")
    if os.environ.get("COPA_ADDR"):
        args += ["--addr", os.environ["COPA_ADDR"]]
    try:
        run(args, log_file=workdir / "copa.log", capture=False)
    except CommandError as e:
        log(f"copa failed: {e.tail[-500:]}")
        return CopaResult(None, fixable, error=e.tail[-2000:])
    repo = image.rsplit("@", 1)[0]
    last = repo.rsplit("/", 1)[-1]
    if ":" in last:
        repo = repo.rsplit(":", 1)[0]
    return CopaResult(f"{repo}:{out_tag}", fixable, vex=vex if vex.exists() else None)
