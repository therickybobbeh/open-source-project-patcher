"""Image archives: how a release build hands its images to the job that pushes them.

The release build runs upstream code (build commands, Dockerfile RUN steps) with the Docker socket, which is root on
the runner, so it gets no registry credentials. It saves each image it built with `docker save` (Docker's tar format;
since Docker 25 also an OCI image layout) to `<out>/images/<arch>/<image key>.tar`, and release.yml uploads them as
artifacts. The push job runs no upstream code, holds the credentials, and pushes each archive with crane to a tag
it computes itself (`pipeline.release_push`).

An archive was written by a job that ran upstream code, so it is data, never instructions: no name, tag or path in
it is used. `check` reads it without extracting anything and accepts exactly one image, of the platform its path
names; crane then pushes that one image to the given reference only."""

from __future__ import annotations

import json
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .build import arch_of
from .proc import retry_on_network, run

MAX_JSON = 4 << 20  # manifest.json and an image config are a few KB; anything this big is not an image archive


def path_for(images: Path, platform: str, image_key: str) -> Path:
    """Where an image's archive lives: one directory per architecture, so the build jobs' artifacts merge into one tree."""
    return images / arch_of(platform) / f"{image_key}.tar"


def export(ref: str, dest: Path, log: Path | None = None) -> None:
    """Save `ref` from the local image store to `dest` (release build)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.unlink(missing_ok=True)
    run(["docker", "save", "--output", str(dest), ref], log_file=log)


@dataclass(frozen=True)
class Archived:
    """The one image in an archive."""

    os: str
    architecture: str
    variant: str
    layers: int

    @property
    def platform(self) -> str:
        return "/".join(p for p in (self.os, self.architecture, self.variant) if p)


def _json(tar: tarfile.TarFile, name: str):
    try:
        member = tar.getmember(name)
    except KeyError:
        raise ValueError(f"no {name}") from None
    if not member.isfile() or member.size > MAX_JSON:
        raise ValueError(f"{name} is not a regular file of at most {MAX_JSON} bytes")
    f = tar.extractfile(member)
    assert f is not None
    return json.loads(f.read())


def inspect(path: Path) -> Archived:
    """The image a `docker save` archive holds. Raises ValueError unless it is an uncompressed tar with exactly one
    image whose config and layers are all in it."""
    try:
        with tarfile.open(path, "r:") as tar:  # plain tar only: docker save never compresses
            manifest = _json(tar, "manifest.json")
            if not isinstance(manifest, list) or len(manifest) != 1 or not isinstance(manifest[0], dict):
                raise ValueError(f"expected exactly one image, found {len(manifest) if isinstance(manifest, list) else 'none'}")
            entry = manifest[0]
            if not isinstance(entry.get("Config"), str):
                raise ValueError("manifest.json names no image config")
            config = _json(tar, entry["Config"])
            layers = entry.get("Layers")
            if not isinstance(layers, list) or not isinstance(config, dict):
                raise ValueError("malformed manifest.json or image config")
            names = set(tar.getnames())
            missing = [l for l in layers if l not in names]
            if missing:
                raise ValueError(f"layers missing from the archive: {missing[:3]}")
    except (tarfile.TarError, OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"{path}: not an image archive ({e})") from None
    except ValueError as e:
        raise ValueError(f"{path}: {e}") from None
    return Archived(str(config.get("os", "")), str(config.get("architecture", "")), str(config.get("variant", "")), len(layers))


def check(path: Path, platform: str) -> Archived:
    """`inspect`, and the image must be for `platform` (`linux/arm64` accepts any arm64 variant)."""
    img = inspect(path)
    os_, _, rest = platform.partition("/")
    arch, _, variant = rest.partition("/")
    if (img.os, img.architecture) != (os_, arch) or (variant and img.variant != variant):
        raise ValueError(f"{path}: holds a {img.platform} image, expected {platform}")
    return img


def push(path: Path, ref: str, log: Path | None = None) -> str:
    """Push the image in archive `path` to `ref` (and nowhere else) with crane; returns the pushed manifest digest.
    Uses the docker credentials (`docker login`) like the rest of the pipeline."""
    with tempfile.TemporaryDirectory() as tmp:
        refs = Path(tmp) / "refs"
        # registry blips: crane pushes blobs again only if they're missing, so a second try is cheap
        retry_on_network(lambda: run(["crane", "push", "--image-refs", str(refs), str(path), ref], log_file=log, capture=False))
        pushed = refs.read_text().split()
    digest = pushed[0].rsplit("@", 1)[-1] if len(pushed) == 1 else ""
    if not digest.startswith("sha256:"):
        raise RuntimeError(f"crane push {ref}: unexpected image refs {pushed}")
    return digest
