"""Bundled third-party binaries: helm/kustomize/git-lfs in Argo CD, gomplate in Dex, credential helpers
in closed-source images. For each one: find the version the image ships (Go build info at the path),
patch and test exactly that upstream version with its component recipe, then swap the rebuilt binary
in with an overlay build (cross-compiled per platform, no QEMU)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from . import detect, upstream
from .config import Repo, line_key, render
from .models import RELEASABLE_STATUSES, ComponentRef, Line, Recipe
from .proc import log, retry_on_network, run
from .scan import ScanReport


USABLE = RELEASABLE_STATUSES  # component runs whose binary may be swapped in


@dataclass
class Component:
    ref: ComponentRef
    recipe: Recipe | None
    version: str | None = None
    tag: str | None = None
    status: str = ""
    src: Path | None = None
    out: Path | None = None  # the component run's output dir (its generated/ is copied into the parent's)
    changes: int = 0
    tests: str = ""
    note: str = ""
    go: str | None = None  # Go the component's run required (stdlib fixes, raised `go` lines); else go.mod decides

    @property
    def usable(self) -> bool:
        return self.src is not None and self.status in USABLE

    def row(self) -> dict:
        return {"recipe": self.ref.recipe, "path": self.ref.path, "version": self.version, "tag": self.tag,
                "status": self.status, "changes": self.changes, "tests": self.tests, "note": self.note}


def swappable(comps: list[Component], chosen: dict[str, str], image_key: str, notes: list[str]) -> list[Component]:
    """The usable components for one image. A line keeps one version per component (its generated/ holds one
    patch set per component), so an image bundling a different version than an earlier image keeps its own."""
    out = []
    for c in comps:
        if not c.usable:
            continue
        first = chosen.setdefault(c.ref.recipe, c.version)
        if first != c.version:
            notes.append(f"component {c.ref.recipe}: image {image_key} bundles {c.version} but another image of this line "
                         f"bundles {first}; only one version per component and line is released, so {image_key} keeps its own")
            continue
        out.append(c)
    return out


def image_row(c: Component, image_key: str, swapped: list[Component]) -> dict:
    """Report row for `c` in one image; a usable component that this image didn't take says so."""
    row = dict(c.row(), image=image_key)
    if c.usable and c not in swapped:
        row["status"] = "kept-original"
    return row


def bundled_version(report: ScanReport | None, path: str) -> str | None:
    """Main-module version of the Go binary at `path` (None for `(devel)` builds or non-Go files)."""
    loc = path.strip("/")
    for p in (report.packages if report else []):
        if p.target.strip("/") == loc and p.relationship == "root" and p.version not in ("", "(devel)"):
            return p.version.lstrip("v")
    return None


def applicable(recipe: Recipe, image_key: str) -> list[ComponentRef]:
    return [c for c in recipe.components if not c.images or image_key in c.images]


def find_version(ref: ComponentRef, scan: ScanReport | None, src: Path | None, image: str | None, platform: str) -> tuple[str | None, str]:
    """(version, how): explicit `version`, `versionFrom` in the parent checkout, Go build info, `versionCommand`."""
    if ref.version:
        return ref.version.lstrip("v"), "pinned"
    if ref.versionFrom and src is not None:
        vf = ref.versionFrom
        try:
            return upstream.version_from_text((src / vf.file).read_text(), vf.var, vf.pattern).lstrip("v"), vf.file
        except (OSError, LookupError):
            pass
    v = bundled_version(scan, ref.path)
    if v:
        return v, "Go build info"
    if ref.versionCommand and image:
        from .build import run_container
        from .proc import CommandError

        # pull first, quietly: otherwise docker's "Unable to find image '…:1.6.0' locally" lands in the output, and the
        # first version in it is the image's tag, not the binary's
        run(["docker", "pull", "--quiet", "--platform", platform, image], check=False, quiet=True, timeout=600)
        try:
            res = run_container(image, list(ref.versionCommand), platform=platform, timeout=120, entrypoint=ref.path, check=False)
        except CommandError:  # timed out
            return None, ""
        m = re.search(r"v?(\d+\.\d+\.\d+)", res.out)
        if m:
            return m.group(1), f"`{ref.path} {' '.join(ref.versionCommand)}`"
    return None, ""


def prepare(repo: Repo, refs: list[ComponentRef], scan: ScanReport | None, opts, out: Path, cache: dict,
            src: Path | None = None, image: str | None = None) -> list[Component]:
    """Patch + test each component at the version the image bundles (cached per recipe+version)."""
    from .pipeline import RunOptions, run_line

    comps = []
    for ref in refs:
        try:
            recipe = repo.load_recipe(ref.recipe)
        except (FileNotFoundError, ValueError) as e:
            comps.append(Component(ref, None, status="error", note=str(e)[:200]))
            continue
        version, how = find_version(ref, scan, src, image, opts.platform)
        if version is None:
            comps.append(Component(ref, recipe, status="not-found",
                                   note=f"version of {ref.path} unknown: set `version`, `versionFrom` or `versionCommand`"))
            continue
        key = (recipe.name, version)
        if key in cache:
            comps.append(cache[key])
            continue
        tag = render(ref.tag, {"version": version})
        line = Line(tag=tag, name=f"{recipe.name}-{version}")
        sub = RunOptions(workdir=opts.workdir, out=out / "components", platform=opts.platform, skip_tests=opts.skip_tests,
                         skip_build=True, copa=False, retry_patch_level=opts.retry_patch_level, cooldown=opts.cooldown)
        log(f"== component {recipe.name} {tag} (bundled at {ref.path})")
        try:
            s = run_line(repo, recipe, line, sub)
        except Exception as e:  # a component must never take the parent run down
            comp = Component(ref, recipe, version, tag, status="error", note=str(e).splitlines()[0][:200])
        else:
            comp_out = sub.out / recipe.name / line_key(line)
            comp = Component(ref, recipe, version, tag, status=s.status, src=Path(s.src) if s.src else None,
                             out=comp_out, changes=len(s.changes),
                             tests=("passed" if s.tests.passed else "failed") if s.tests and s.tests.ran else "not run",
                             note=f"version from {how}", go=_required_go(comp_out / "generated" / "bump-plan.json"))
        cache[key] = comp
        comps.append(comp)
    return comps


def overlay_dockerfile(base_ref: str, comps: list[Component]) -> str:
    lines = []
    for i, c in enumerate(comps):
        art = c.recipe.artifact
        go_dirs = [d for e in c.recipe.ecosystems if e.type == "gomod" for d in e.dirs]
        candidates = [v for v in (c.go, detect.go_version(c.src, go_dirs)) if v]
        go = max(candidates, key=lambda v: tuple(int(x) for x in v.split("."))) if candidates else "1"
        builder = render(art.builder, {"go": go})
        build = render(art.build, {"version": c.version, "tag": c.tag})
        lines += [f"FROM --platform=$BUILDPLATFORM {builder} AS comp{i}", "WORKDIR /src", f"COPY --from=comp{i}-src . .",
                  "ARG TARGETOS TARGETARCH", f"RUN {build}", ""]
    lines.append(f"FROM {base_ref}")
    lines += [f"COPY --from=comp{i} {c.recipe.artifact.output} {c.ref.path}" for i, c in enumerate(comps)]
    return "\n".join(lines) + "\n"


def overlay(base_ref: str, comps: list[Component], out: Path, *, platforms: list[str], tag_ref: str, push: bool,
            local_base: bool, timeout: int = 3600) -> None:
    """Rebuild `base_ref` with the components' binaries swapped in, as `tag_ref`.

    `local_base`: the base exists only in the local image store, so use the docker driver (which sees
    it) instead of a docker-container buildx builder."""
    out.mkdir(parents=True, exist_ok=True)
    for c in comps:
        upstream.reset_tree(c.src)
    dockerfile = out / "Dockerfile.overlay"
    dockerfile.write_text(overlay_dockerfile(base_ref, comps))
    args = ["docker", "buildx", "build", "--platform", ",".join(platforms), "-f", str(dockerfile), "-t", tag_ref, "--provenance=false"]
    for i, c in enumerate(comps):
        args += ["--build-context", f"comp{i}-src={c.src}"]
    args += ["--push"] if push else ["--load"]
    args.append(str(out))
    # the builder stages download Go modules: one more try on a network blip
    retry_on_network(lambda: run(args, env={"BUILDX_BUILDER": "default"} if local_base else None, log_file=out / "overlay.log",
                                 capture=False, clean=True, timeout=timeout), timeouts=True)


def from_generated(repo: Repo, recipe: Recipe, gen: Path, workdir: Path) -> dict[str, Component]:
    """Release flow: re-create each component's reviewed source from generated/<recipe>/<tag>/components/."""
    comps: dict[str, Component] = {}
    refs = {c.recipe: c for c in recipe.components}
    for plan_file in sorted((gen / "components").glob("*/bump-plan.json")):
        doc = json.loads(plan_file.read_text())
        ref = refs.get(doc["recipe"])
        if ref is None or doc.get("status") not in USABLE:  # the PR run kept the original binary for these
            continue
        comp_recipe = repo.load_recipe(doc["recipe"])
        src = workdir / "components" / doc["recipe"] / doc["tag"] / "src"
        if src.exists():
            import shutil

            shutil.rmtree(src)
        upstream.checkout(comp_recipe.source.url, doc["tag"], src, expected_commit=doc["commit"])
        patch = plan_file.parent / "deps.patch"
        if patch.exists() and patch.stat().st_size:
            run(["git", "-C", str(src), "apply", "--binary", "--whitespace=nowarn", str(patch.resolve())])
        version = doc["tag"].lstrip("v").split("/")[-1].lstrip("v")
        comps[doc["recipe"]] = Component(ref, comp_recipe, version, doc["tag"], status=doc.get("status", ""), src=src,
                                         go=(doc.get("requires") or {}).get("go"))
    return comps


def _required_go(plan_file: Path) -> str | None:
    try:
        go = (json.loads(plan_file.read_text()).get("requires") or {}).get("go")
    except (OSError, ValueError):
        return None
    return ".".join(go.split(".")[:2]) if go else None  # builder images are tagged major.minor
