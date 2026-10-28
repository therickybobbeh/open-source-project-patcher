"""Image builds: buildx (default) or a recipe-defined command, plus smoke tests."""

from __future__ import annotations

import json
import platform as _platform
import shlex
from dataclasses import dataclass, field
from pathlib import Path

from .config import render
from .models import Build, ImageSpec
from .proc import CommandError, output, run


def native_platform() -> str:
    arch = _platform.machine().lower()
    arch = {"x86_64": "amd64", "aarch64": "arm64"}.get(arch, arch)
    return f"linux/{arch}"


def arch_of(platform: str) -> str:
    return platform.split("/", 1)[1].replace("/", "")


@dataclass
class BuiltImage:
    spec: ImageSpec
    ref: str  # tag in the local daemon or registry
    platform: str
    pushed: bool = False
    smoke: list[dict] = field(default_factory=list)


def template_ctx(tag: str, commit: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    version = tag[1:] if tag.startswith("v") else tag
    return {"tag": tag, "version": version, "commit": commit, "short_commit": commit[:7], **(extra or {})}


def build_image(src: Path, b: Build, spec: ImageSpec, ref: str, platform: str, tctx: dict[str, str], env: dict[str, str],
                log: Path, *, push: bool) -> BuiltImage:
    ctx = {**tctx, "image": ref, "platform": platform, "arch": arch_of(platform)}
    if spec.command:
        run(render(spec.command, ctx), cwd=src, env={**env, **{k: render(v, ctx) for k, v in b.env.items()}}, log_file=log, capture=False,
            clean=True)
        produced = render(spec.builtImage or "", ctx)
        if not produced:
            raise ValueError(f"image {spec.name}: `builtImage` is required with a custom `command`")
        if produced != ref:
            run(["docker", "tag", produced, ref], log_file=log)
        if push:
            run(["docker", "push", ref], log_file=log, capture=False)
        return BuiltImage(spec, ref, platform, pushed=push)
    args = ["docker", "buildx", "build", "--platform", platform, "-t", ref, "--provenance=false"]
    if spec.dockerfile:
        args += ["-f", str(src / render(spec.dockerfile, ctx))]
    if spec.target:
        args += ["--target", spec.target]
    for k, v in spec.args.items():
        args += ["--build-arg", f"{k}={render(v, ctx)}"]
    args += ["--label", f"org.opencontainers.image.revision={tctx['commit']}", "--label", f"org.opencontainers.image.version={tctx['tag']}"]
    args += ["--push"] if push else ["--load"]
    args.append(str(src / render(spec.context, ctx)))
    run(args, cwd=src, env=env, log_file=log, capture=False, clean=True)
    return BuiltImage(spec, ref, platform, pushed=push)


def smoke_test(img: BuiltImage, log: Path) -> bool:
    ok = True
    for cmd in img.spec.smoke:
        try:
            r = run(["docker", "run", "--rm", "--platform", img.platform, img.ref, *shlex.split(cmd)], log_file=log, timeout=300)
            img.smoke.append({"cmd": cmd, "ok": True, "out": r.out[-500:]})
        except CommandError as e:
            img.smoke.append({"cmd": cmd, "ok": False, "out": e.tail[-500:]})
            ok = False
    return ok


def image_digest(ref: str) -> str:
    out = output(["docker", "buildx", "imagetools", "inspect", ref, "--format", "{{json .Manifest}}"])
    return json.loads(out)["digest"]
