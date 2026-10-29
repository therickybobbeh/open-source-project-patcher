"""Copacetic: patch remaining fixable OS packages in a built image."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from .models import ImageSpec
from .proc import CommandError, first_error, log, run, which
from .scan import scan_image


@dataclass
class CopaResult:
    patched_ref: str | None
    os_fixable_before: int
    vex: Path | None = None
    error: str | None = None
    skipped: str | None = None
    summary: str = ""  # Copa's own "N total, N patched, N skipped"
    libraries: bool = False

    def note(self) -> str:
        """One line for the report's Copa column."""
        if self.skipped:
            return self.skipped
        if not self.patched_ref:
            return f"failed: {first_error(self.error)}"
        kind = "OS + library" if self.libraries else "OS"
        return f"patched ({kind}): {self.summary}" if self.summary else f"patched {self.os_fixable_before} {kind} finding(s)"


def for_image(spec: ImageSpec, image: str, out_tag: str, out: Path, *, platforms: list[str], severities: list[str],
              push: bool = False, src: str | None = None) -> CopaResult | None:
    """Copa for one recipe image, honoring its `copa` setting (None when it is `false`)."""
    if not spec.copa_enabled:
        return None
    o = spec.copa_options
    return patch(image, out_tag, out / f"copa-{spec.key}", platforms=platforms, severities=severities, push=push, src=src,
                 libraries=o.libraries, level=o.level.value)


def patch(image: str, out_tag: str, workdir: Path, *, platforms: list[str], severities: list[str], push: bool = False,
          src: str | None = None, libraries: bool = False, level: str = "patch") -> CopaResult:
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
                         pkg_types="os,library" if libraries else "os", ignore_unfixed=True, src=src)
        fixable += len(rep.fixable())
    if fixable == 0:
        return CopaResult(None, 0, skipped="no fixable packages" if libraries else "no fixable OS packages", libraries=libraries)
    if not which("copa"):
        return CopaResult(None, fixable, skipped="copa not installed", libraries=libraries)
    vex = workdir / "copa.vex.json"
    args = ["copa", "patch", "-i", image, "-t", out_tag, "--timeout", "30m", "-f", "openvex", "-o", str(vex)]
    args += ["-r", str(reports) if len(platforms) > 1 else str(next(reports.glob("*.json")))]
    env = {}
    if libraries:
        # experimental in Copa: patches pip/npm packages inside the image (no rebuild); closed-source images
        env["COPA_EXPERIMENTAL"] = "1"
        args += ["--pkg-types", "os,library", "--library-patch-level", level]
    if push:
        args.append("--push")
    if os.environ.get("COPA_ADDR"):
        args += ["--addr", os.environ["COPA_ADDR"]]
    try:
        run(args, env=env, log_file=workdir / "copa.log", capture=False)
    except CommandError as e:
        log(f"copa failed: {e.tail[-500:]}")
        return CopaResult(None, fixable, error=e.tail[-2000:], libraries=libraries)
    repo = image.rsplit("@", 1)[0]
    last = repo.rsplit("/", 1)[-1]
    if ":" in last:
        repo = repo.rsplit(":", 1)[0]
    log_text = (workdir / "copa.log").read_text(errors="replace") if (workdir / "copa.log").exists() else ""
    m = re.findall(r"Patch Summary: ([^\"]+?)\s*\"", log_text)
    return CopaResult(f"{repo}:{out_tag}", fixable, vex=vex if vex.exists() else None, summary=m[-1] if m else "",
                      libraries=libraries)
