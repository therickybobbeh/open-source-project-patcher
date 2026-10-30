"""End-of-life runtimes: the base images in each tracked line's Dockerfiles and the recipes' toolchains,
checked against endoflife.date, so a release that has lost support, or is about to, is flagged before a
scanner or an audit finds it (`patcher eol`; rescan.yml opens one issue each). A `minVersions` floor
counts: an image below it is checked at the line it is raised to."""

from __future__ import annotations

import datetime as dt
import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

from . import registry, upstream
from .adapters import dockerfile
from .config import Repo, line_key
from .models import DockerfileEco, Level, Recipe
from .proc import log

API = "https://endoflife.date/api/v1/products/{}"

# image name (last part of the repository) -> endoflife.date product, and how many tag numbers name a release
IMAGES = {
    "node": ("nodejs", 1), "golang": ("go", 2), "python": ("python", 2), "alpine": ("alpine-linux", 2),
    "debian": ("debian", 1), "ubuntu": ("ubuntu", 2), "eclipse-temurin": ("eclipse-temurin", 1),
    "redis": ("redis", 2), "postgres": ("postgresql", 1), "kubectl": ("kubernetes", 2),
}
# releases spelled inside a name or tag: static-debian12, golang:1.26-alpine3.23, maven:…-eclipse-temurin-21-noble, ubi9
EMBEDDED = [
    (re.compile(r"(?:^|[-/])debian(\d+)(?=$|[-/:])"), "debian"),
    (re.compile(r"alpine(\d+\.\d+)"), "alpine-linux"),
    (re.compile(r"eclipse-temurin-(\d+)"), "eclipse-temurin"),
    (re.compile(r"(?:^|/)ubi(\d+)(?=$|[-/])"), "rhel"),
]
CODENAMED = ("debian", "ubuntu")  # bookworm-slim, noble: matched against endoflife.date's codenames
TOOLCHAINS = {"go": ("go", 2), "node": ("nodejs", 1), "python": ("python", 2), "java": ("eclipse-temurin", 1)}


@dataclass
class Runtime:
    recipe: str
    product: str  # endoflife.date product: nodejs
    label: str  # Node.js
    release: str  # 20
    eol: str | None  # 2026-04-30; None: no date announced (only `isEol`)
    days: int | None  # days left, negative once past
    uses: list[str] = field(default_factory=list)


class Releases:
    """endoflife.date, one request per product, retried: a failed lookup fails the run instead of closing issues."""

    def __init__(self, fetch: Callable[[str], dict] | None = None):
        self._fetch = fetch or _fetch
        self._cache: dict[str, dict] = {}

    def product(self, name: str) -> dict:
        if name not in self._cache:
            self._cache[name] = self._fetch(name)
        return self._cache[name]

    def get(self, product: str, release: str) -> dict | None:
        return next((r for r in self.product(product).get("releases", []) if r.get("name") == release), None)

    def codenames(self) -> dict[str, tuple[str, str]]:
        """bookworm -> (debian, 12), noble -> (ubuntu, 24.04): the first word of each release's codename."""
        found = {}
        for product in CODENAMED:
            for r in self.product(product).get("releases", []):
                if r.get("codename"):
                    found[r["codename"].split()[0].lower()] = (product, r["name"])
        return found


def _fetch(product: str) -> dict:
    for attempt in range(3):
        try:
            with urllib.request.urlopen(API.format(product), timeout=30) as resp:
                return json.load(resp)["result"]
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 2:
                raise RuntimeError(f"endoflife.date: {product}: {e}") from e
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def _release(version: str, parts: int) -> str | None:
    """The release a version names: 1.26.10-alpine3.23 (2 parts) -> 1.26, 24.04 -> 24.04, v1.36.3 -> 1.36;
    None when the version is less precise (a floating `alpine:3` is always the newest 3.x)."""
    m = re.match(r"v?(\d+(?:\.\d+)*)", version)
    nums = m.group(1).split(".") if m else []
    return ".".join(nums[:parts]) if len(nums) >= parts else None


def image_releases(image: str, eco: DockerfileEco, codenames: dict[str, tuple[str, str]]) -> list[tuple[str, str, str]]:
    """(product, release, note) for each runtime an image ref names, after `minVersions` (a stage below its
    line is checked at the line) and `level` (above `patch` the tag follows the newer releases)."""
    ref = registry.parse_ref(image)
    name = ref.repository.rsplit("/", 1)[-1]
    tag = ref.tag or ""
    found: list[tuple[str, str, str]] = []
    if name in IMAGES and tag:
        product, parts = IMAGES[name]
        floor = dockerfile.min_line(eco, ref)
        if floor and dockerfile.below_line(tag, floor) and len(floor.split(".")) >= parts:
            found.append((product, ".".join(floor.split(".")[:parts]), f"raised to {floor} by minVersions"))
        elif eco.level == Level.patch or (eco.level == Level.minor and parts == 1):
            rel = _release(tag, parts)
            if rel:
                found.append((product, rel, ""))
    for rx, product in EMBEDDED:
        m = rx.search(f"{ref.repository}:{tag}")
        if m and not any(p == product for p, _, _ in found):
            found.append((product, m.group(1), ""))
    for token in re.split(r"[-_.]", tag):
        if token.lower() in codenames and not any(p == codenames[token.lower()][0] for p, _, _ in found):
            found.append((*codenames[token.lower()], ""))
    return found


def _from_images(text: str) -> list[tuple[str, str | None]]:
    """(image ref with ARG defaults filled in, stage) for each external FROM; stages and scratch skipped."""
    args: dict[str, str] = {}
    stages: set[str] = set()
    found = []
    for line in text.splitlines():
        am = dockerfile.ARG_RE.match(line)
        if am:
            args[am.group("name")] = am.group("value")
            continue
        m = dockerfile.FROM_RE.match(line)
        if not m:
            continue
        sm = dockerfile.STAGE_RE.search(m.group("rest"))
        stage = sm.group("stage") if sm else None
        image = m.group("image")
        if stage:
            stages.add(stage)
        if image in stages or image.lower() == "scratch":
            continue
        if any(n not in args for n in dockerfile.VAR_RE.findall(image)):
            continue  # a build-time-only ARG
        found.append((dockerfile.VAR_RE.sub(lambda v: args[v.group(1)], image), stage))
    return found


def _resolver():
    """upstream.resolve_line, listing each repo's tags once."""
    tags: dict[str, dict[str, str]] = {}

    def resolve(source, line):
        if line.branch:
            return upstream.resolve_line(source, line)
        if source.url not in tags:
            tags[source.url] = upstream.list_tags(source.url)
        return upstream.resolve_line(source, line, tags[source.url])
    return resolve


def _read(source, commit: str, path: str) -> str | None:
    """A file at a commit; None when it isn't there. Other errors are retried, then raised: a file that couldn't
    be read must fail the run, or its runtimes' issues would close as if nothing used them any more."""
    for attempt in range(3):
        try:
            return upstream.read_remote_file(source, commit, path)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            err: Exception = e
        except (urllib.error.URLError, TimeoutError) as e:
            err = e
        if attempt == 2:
            raise RuntimeError(f"{source.url} {commit[:12]}: {path}: {err}") from err
        time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def _uses(repo: Repo, recipe: Recipe, releases: Releases, read, resolve) -> list[tuple[str, str, str]]:
    """(product, release, where) for every runtime the recipe builds with."""
    uses = []
    for tool, (product, parts) in TOOLCHAINS.items():
        value = getattr(recipe.toolchain, tool)
        if not value or (tool == "java" and not value.startswith("temurin-")):
            continue
        rel = _release(value.removeprefix("temurin-"), parts)
        if rel:
            uses.append((product, rel, f"toolchain `{tool}: {value}`"))
    if not recipe.source or recipe.mode != "source":
        return uses
    # the dockerfile ecosystems' files, then the Dockerfiles images are built from (without an ecosystem their
    # bases stay as written); custom build commands name theirs in a shell line, so they need an ecosystem
    files: dict[str, DockerfileEco] = {}
    for eco in recipe.ecosystems:
        if isinstance(eco, DockerfileEco):
            for path in eco.files:
                files.setdefault(path, eco)
    for spec in recipe.build.images if recipe.build else []:
        if spec.dockerfile and not spec.command and "{{" not in spec.dockerfile:
            files.setdefault(spec.dockerfile, DockerfileEco(type="dockerfile"))
    if not files:
        return uses
    codenames = releases.codenames()
    for line in recipe.source.lines:
        try:
            tag, commit = resolve(recipe.source, line)
        except LookupError as e:
            log(f"warning: {recipe.name} {line_key(line)}: {e}")
            continue
        for path, eco in files.items():
            if any(c in path for c in "*?["):
                log(f"warning: {recipe.name}: {path}: globs aren't read without a checkout; not checked")
                continue
            overlay = repo.overlay_dir(recipe.name) / path  # our own files (patches/<recipe>/files/) win
            text = overlay.read_text() if overlay.is_file() else read(recipe.source, commit, path)
            if text is None:
                log(f"warning: {recipe.name} {tag}: no {path}")
                continue
            for image, stage in _from_images(text):
                shown = image.split("@")[0]
                for product, rel, note in image_releases(image, eco, codenames):
                    where = f"{line_key(line)} `{path}`" + (f" (stage {stage})" if stage else "") + f": `{shown}`"
                    uses.append((product, rel, where + (f", {note}" if note else "")))
    return uses


def check(repo: Repo, within_days: int = 90, today: dt.date | None = None, fetch=None, read=None, resolve=None) -> list[Runtime]:
    """Runtimes past their end of life, or within `within_days` of it, one per recipe and release."""
    today = today or dt.datetime.now(dt.timezone.utc).date()
    releases = Releases(fetch)
    read = read or _read
    resolve = resolve or _resolver()
    found: dict[tuple[str, str, str], Runtime] = {}
    for path in repo.recipe_paths():
        recipe = repo.load_recipe(path.stem)
        for product, rel, where in _uses(repo, recipe, releases, read, resolve):
            info = releases.get(product, rel)
            if info is None:
                continue  # not released yet, or a release endoflife.date doesn't list
            eol = info.get("eolFrom")
            days = (dt.date.fromisoformat(eol) - today).days if eol else None
            if not (info.get("isEol") or (days is not None and days <= within_days)):
                continue
            label = releases.product(product).get("label") or product
            rt = found.setdefault((recipe.name, product, rel), Runtime(recipe.name, product, label, rel, eol, days))
            if where not in rt.uses:
                rt.uses.append(where)
    return sorted(found.values(), key=lambda r: (r.recipe, r.product, r.release))


def render_markdown(found: list[Runtime], within_days: int) -> str:
    rows = ["| Recipe | Runtime | End of life | Used by |", "|---|---|---|---|"]
    for r in found:
        when = r.eol or "—"
        if r.days is not None:
            when += f" ({-r.days} days ago)" if r.days < 0 else f" (in {r.days} days)"
        rows.append(f"| {r.recipe} | {r.label} {r.release} | {when} | {'<br>'.join(r.uses)} |")
    if not found:
        rows.append(f"| — | nothing is end-of-life or within {within_days} days of it | | |")
    return "\n".join(rows)
