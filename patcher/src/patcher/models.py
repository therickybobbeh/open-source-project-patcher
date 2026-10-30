"""Pydantic models for recipes, skip files, VEX decisions and release state.

These models are the source of truth for the JSON schemas in `schema/`
(regenerate with `patcher schema`).
"""

from __future__ import annotations

import datetime as dt
import re
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .ecosystems import ECOSYSTEMS


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Level(str, Enum):
    """How far a dependency may move without a human: patch < minor < major."""

    patch = "patch"
    minor = "minor"
    major = "major"

    @property
    def rank(self) -> int:
        return {"patch": 0, "minor": 1, "major": 2}[self.value]


# --- source -----------------------------------------------------------------


class VersionFrom(_Model):
    """Where a branch-tracked line reads its version (e.g. `ARG MAVEN_VERSION=3.10.0`)."""

    file: str
    var: str | None = None
    pattern: str | None = Field(None, description="Regex with a named group `version`")

    @model_validator(mode="after")
    def _one(self) -> "VersionFrom":
        if bool(self.var) == bool(self.pattern):
            raise ValueError("exactly one of `var` or `pattern` is required")
        return self


class Line(_Model):
    """A release line we track: the newest tag matching `tagPattern` (e.g. every v3.5.x), a pinned
    `tag`, or the head of a `branch` for projects that don't tag releases."""

    tagPattern: str | None = Field(None, description="Regex an upstream tag must match to belong to this line")
    name: str | None = Field(None, description="Short name used in branch/state keys; defaults to a slug of tagPattern")
    tag: str | None = Field(None, description="Pin an exact upstream tag instead of following the newest one")
    branch: str | None = Field(None, description="Track this branch's head instead of tags (requires `versionFrom` and `name`)")
    versionFrom: VersionFrom | None = None

    @model_validator(mode="after")
    def _check(self) -> "Line":
        if sum(bool(x) for x in (self.tagPattern, self.tag, self.branch)) != 1:
            raise ValueError("exactly one of `tagPattern`, `tag` or `branch` is required")
        if self.branch and not (self.versionFrom and self.name):
            raise ValueError("branch lines need `versionFrom` and `name`")
        return self


class Source(_Model):
    repo: str = Field(description="GitHub `owner/name` or a full git URL")
    lines: list[Line] = Field(min_length=1)
    exclude: list[str] = Field(default_factory=list, description="Tag regexes to ignore (e.g. sub-module tags like `api/v2.*`)")

    @property
    def url(self) -> str:
        if "://" in self.repo or self.repo.startswith("git@"):
            return self.repo
        return f"https://github.com/{self.repo}"


# --- toolchain / policy -----------------------------------------------------


class Toolchain(_Model):
    go: str | None = Field(None, description="Go major.minor; the latest patch is installed (fixes stdlib CVEs)")
    rust: str | None = Field(None, description="Rust version, or `from-repo` to honor rust-toolchain.toml")
    java: str | None = Field(None, description="mise java spec, e.g. `temurin-21`")
    maven: str | None = None
    node: str | None = None
    pnpm: str | None = None
    yarn: str | None = Field(None, description="e.g. `1.22.22` (classic) or `4.5.0` (berry)")
    python: str | None = Field(None, description="Python version for mise, e.g. `3.12`")
    extra: dict[str, str] = Field(default_factory=dict, description="Additional mise tools, e.g. {protoc: '29.3'}")
    repoMise: bool | list[str] = Field(False, description="Use the upstream repo's own mise config (exact upstream tool pins): "
                                       "`true` = every tool in it, or a list of tool names to install from it, in order")


class CooldownBypass(_Model):
    severities: list[str] = Field(default_factory=lambda: ["CRITICAL"], description="Findings of these severities skip the age rule")
    kev: bool = Field(True, description="CVEs on CISA's Known Exploited Vulnerabilities list skip the age rule")


class Policy(_Model):
    default: Level = Level.minor
    ecosystems: dict[str, Level] = Field(default_factory=dict, description="Per-ecosystem override of `default`")
    minReleaseAgeDays: int | None = Field(None, description="Only bump to versions published at least this many days ago "
                                          "(supply-chain cooldown); unset/0 = off")
    cooldownBypass: CooldownBypass = Field(default_factory=CooldownBypass)

    def for_ecosystem(self, eco: str) -> Level:
        return self.ecosystems.get(eco, self.default)


# --- ecosystems -------------------------------------------------------------


class ReplaceGroup(_Model):
    pattern: str = Field(description="Regex over module paths, e.g. `^k8s\\.io/(api|apimachinery|client-go)$`")
    sameVersion: bool = Field(True, description="Members that currently share a version move together")


class GoModEco(_Model):
    type: Literal["gomod"]
    dirs: list[str] = Field(default_factory=lambda: ["."], description="Module directories (each has a go.mod); globs allowed")
    replaceGroups: list[ReplaceGroup] = Field(default_factory=list)
    bumpToolchainDirective: bool = Field(True, description="Raise an existing `toolchain` directive to the fixed Go version")


class CargoEco(_Model):
    type: Literal["cargo"]
    dirs: list[str] = Field(default_factory=lambda: ["."], description="Workspace roots (contain Cargo.lock)")


class MavenEco(_Model):
    type: Literal["maven"]
    poms: list[str] = Field(default_factory=lambda: ["pom.xml"],
                            description="Reactor root POMs (globs). A finding is patched in the deepest root whose directory "
                                        "contains its pom.xml: explicit versions via versions-maven-plugin, transitives "
                                        "pinned in that root's <dependencyManagement>")


class NodeEco(_Model):
    type: Literal["npm", "pnpm", "yarn"]
    dirs: list[str] = Field(default_factory=lambda: ["."])


class PythonEco(_Model):
    type: Literal["python"]
    dirs: list[str] = Field(default_factory=lambda: ["."], description="Project dirs (globs); the tool is detected per dir")
    tool: Literal["auto", "uv", "poetry", "pipenv", "pip-tools", "pip"] = Field(
        "auto", description="auto: uv.lock -> uv, poetry.lock -> poetry, Pipfile.lock -> pipenv, requirements.in or a "
                            "pip-compile / `uv pip compile` header -> pip-tools, other requirements*.txt -> pip")
    toolVersion: str | None = Field(None, description="poetry/pipenv/pip-tools version (default: read from the lockfile header, "
                                                      "else a pinned default)")


class GradleEco(_Model):
    type: Literal["gradle"]
    dirs: list[str] = Field(default_factory=lambda: ["."], description="Gradle build roots (settings.gradle[.kts] or build.gradle[.kts])")
    catalog: str = Field("gradle/libs.versions.toml", description="Version catalog, relative to the build root")


class DockerfileEco(_Model):
    type: Literal["dockerfile"]
    files: list[str] = Field(default_factory=lambda: ["Dockerfile"])
    pinDigest: bool = True
    ignore: list[str] = Field(default_factory=list, description="Image-name regexes to leave alone")
    level: Level = Field(Level.patch, description="How far a base image tag may move")
    minVersions: dict[str, str] = Field(default_factory=dict, description=(
        "Release lines base images must not fall below, by image name (`node`, `alpine`, `library/node`), e.g. "
        "{node: \"24\"} for a build stage on an end-of-life Node. A tag below its line moves to the newest tag of the "
        "same shape in it (24: 24.x.y, 3.24: 3.24.x), whatever `level` says; tags at or above it follow `level`"))

    @model_validator(mode="after")
    def _release_lines(self) -> "DockerfileEco":
        for image, line in self.minVersions.items():
            parts = line.split(".")
            if len(parts) > 2 or not all(p.isdigit() for p in parts):
                raise ValueError(f"minVersions.{image}: {line!r} is not a release line (one or two numbers: 24, 3.24)")
        return self


class VersionSource(_Model):
    git: str = Field(description="Repo to read tags from (`owner/name` or URL)")
    tagPattern: str = Field(r"^v?\d+\.\d+\.\d+$", description="Only tags matching this regex are candidates")


class DerivedEdit(_Model):
    """A second edit that follows the main version change (URL, checksum...)."""

    var: str | None = None
    pattern: str | None = Field(None, description="Regex with a named group `value`")
    value: str | None = Field(None, description="Template, e.g. `https://download.redis.io/redis-{{version}}.tar.gz`")
    sha256Of: str | None = Field(None, description="Template URL to download; its sha256 becomes the value")

    @model_validator(mode="after")
    def _one_target(self) -> "DerivedEdit":
        if bool(self.var) == bool(self.pattern):
            raise ValueError("exactly one of `var` or `pattern` is required")
        if bool(self.value) == bool(self.sha256Of):
            raise ValueError("exactly one of `value` or `sha256Of` is required")
        return self


class FileEdit(_Model):
    file: str = Field(description="Path (glob allowed) relative to the checkout")
    var: str | None = Field(None, description="Variable name: matches NAME=ver, NAME ver, NAME: ver (ENV/ARG/export ok)")
    pattern: str | None = Field(None, description="Regex with a named group `version`")
    to: str = Field("latest-patch", description="`latest-patch`, `latest-minor`, or an explicit version")
    source: VersionSource | None = Field(None, description="Where to look up `latest-*` versions")
    derived: list[DerivedEdit] = Field(default_factory=list)

    @model_validator(mode="after")
    def _one_target(self) -> "FileEdit":
        if bool(self.var) == bool(self.pattern):
            raise ValueError("exactly one of `var` or `pattern` is required")
        if self.to.startswith("latest-") and not self.source:
            raise ValueError("`source` is required when `to` is latest-patch/latest-minor")
        return self


class FilesEco(_Model):
    type: Literal["files"]
    edits: list[FileEdit] = Field(min_length=1)


Ecosystem = Annotated[
    Union[GoModEco, CargoEco, MavenEco, NodeEco, PythonEco, GradleEco, DockerfileEco, FilesEco],
    Field(discriminator="type"),
]

ECOSYSTEM_KEYS = tuple(ECOSYSTEMS)

# run outcomes whose result may ship: a line's patch set may be released, a component's binary swapped in
RELEASABLE_STATUSES = ("success", "no-changes", "tests-preexisting")


# --- overrides / holds ------------------------------------------------------


class Override(_Model):
    """Force a dependency: if a lower version is found, raise it to `min` (or set exactly `version`)."""

    name: str = Field(description="Package name; `*` globs allowed (e.g. `golang.org/x/*`)")
    min: str | None = None
    version: str | None = None
    reason: str

    @model_validator(mode="after")
    def _one(self) -> "Override":
        if bool(self.min) == bool(self.version):
            raise ValueError("exactly one of `min` or `version` is required")
        return self


class Hold(_Model):
    """Never bump a dependency (or never past `max`)."""

    name: str
    max: str | None = None
    reason: str
    tagPattern: str | None = Field(None, description="Only for upstream tags matching this regex, e.g. '^v3\\.' to hold a "
                                                     "dependency for one major of a component and not the next")

    @model_validator(mode="after")
    def _pattern(self) -> "Hold":
        if self.tagPattern:
            try:
                re.compile(self.tagPattern)
            except re.error as e:  # fail `patcher validate`, not a run
                raise ValueError(f"tagPattern {self.tagPattern!r}: {e}") from e
        return self


# --- regen / tests / build --------------------------------------------------


class Regen(_Model):
    when: Literal["always", "replaceGroupMoved", "never"] = "always"
    run: list[str] = Field(min_length=1)


class SkipVia(_Model):
    env: str | None = Field(None, description="Put the rendered skip args into this env var instead of `{{skip_args}}`")
    format: str = Field("{{skip_args}}", description="Template; `{{skip_regex}}` = joined skip regex, `{{skip_args}}` = framework args")


class Services(_Model):
    compose: str = Field(description="docker compose file (relative to the checkout)")
    services: list[str] = Field(default_factory=list, description="Subset to start; empty = all")


class Tests(_Model):
    framework: Literal["go", "nextest", "surefire", "gradle", "pytest", "jest", "vitest", "mocha", "redis", "bats", "generic"]
    setup: list[str] = Field(default_factory=list)
    command: str = Field(description="May contain `{{skip_args}}`, `{{skip_regex}}`, `{{skip_file}}`")
    skipVia: SkipVia | None = None
    env: dict[str, str] = Field(default_factory=dict)
    services: Services | None = None
    junit: list[str] = Field(default_factory=list, description="Globs of JUnit XML files to collect")
    timeoutMinutes: int = 90
    enabled: bool = True
    runAs: Literal["root", "nonroot"] = Field("root", description="`nonroot`: run tests.command as an unprivileged user (needed when "
                                              "tests assert permission errors, which root bypasses); setup still runs as root")


class CopaOptions(_Model):
    libraries: bool = Field(False, description="Also patch language packages (COPA_EXPERIMENTAL library patching: pip and npm "
                                               "packages inside the image); for closed-source images")
    level: Level = Field(Level.patch, description="How far Copa may move library versions")


class BundledJars(_Model):
    """A third-party Java distribution the image unpacks (Maven in /usr/share/maven, Kafka's libs/): the image's
    build doesn't control its jars, so vulnerable ones are swapped for fixed releases from Maven Central."""

    paths: list[str] = Field(min_length=1, description="Directory prefixes (or jar paths) in the image, e.g. `usr/share/maven/` "
                             "or `opt/kafka/libs/`. Fixable findings in jars under them are swapped after the build")
    level: Level = Field(Level.patch, description="How far a swapped jar may move (the policy cap for these swaps). The "
                         "release-age rule and holds (`maven` key) apply as for source bumps")


class ImageSpec(_Model):
    name: str = Field(description="Our image repository name, e.g. `argocd`")
    id: str | None = Field(None, description="Unique key when several variants share a repository (defaults to `name`)")
    upstream: str | None = Field(None, description="Upstream image repo (for the baseline scan), e.g. `quay.io/argoproj/argocd`")
    upstreamTag: str = Field("{{tag}}", description="Upstream tag template, also the base of our tag: `{{version}}` strips the leading v, e.g. `{{tag}}-distroless`")
    dockerfile: str | None = "Dockerfile"
    context: str = "."
    target: str | None = None
    args: dict[str, str] = Field(default_factory=dict)
    command: str | None = Field(None, description="Custom build command instead of buildx; must produce `builtImage`")
    builtImage: str | None = Field(None, description="Image ref the custom command produces (template)")
    smoke: list[str] = Field(default_factory=list, description="Args passed to `docker run --rm <image>`; each must exit 0")
    smokeEnv: dict[str, str] = Field(default_factory=dict, description="Environment for the smoke commands (`docker run -e`), "
                                     "e.g. placeholder credentials a distribution requires before it will even validate its config")
    ownBinaries: list[str] = Field(default_factory=list, description="Paths or directory prefixes (in the image) of what this source builds, "
                                   "e.g. `usr/local/bin/dex` or `app/`; anything else is a bundled artifact. Empty = guess from the source scan.")
    bundledJars: BundledJars | None = Field(None, description="Jars of a bundled third-party Java distribution: vulnerable ones are "
                                            "replaced with the fixed release from Maven Central (pinned by sha256) in an overlay "
                                            "on the built image, before smoke tests and Copa")
    copa: bool | CopaOptions = Field(True, description="Copa for leftover OS packages; an object enables library patching too")
    tagPattern: str | None = Field(None, description="image-only: this image's own tag regex when it versions separately from the line")
    platforms: list[str] = Field(default_factory=list, description="Platforms this image exists for, when fewer than build.platforms: "
                                 "it is built and released for those of build.platforms it lists")

    @property
    def key(self) -> str:
        return self.id or self.name

    @property
    def copa_enabled(self) -> bool:
        return bool(self.copa)

    @property
    def copa_options(self) -> CopaOptions:
        return self.copa if isinstance(self.copa, CopaOptions) else CopaOptions()


class Build(_Model):
    setup: list[str] = Field(default_factory=list, description="Commands run before image builds (e.g. `make build`)")
    platforms: list[str] = Field(default_factory=lambda: ["linux/amd64", "linux/arm64"], min_length=1,
                                 description="Platforms the line is released for. The release builds each one on its own native "
                                             "runner (linux/amd64, linux/arm64) and merges them")
    env: dict[str, str] = Field(default_factory=dict)
    images: list[ImageSpec] = Field(min_length=1)
    timeoutMinutes: int = Field(60, description="Per image build (and per component overlay); a build that hangs is killed "
                                                "and retried once")

    @model_validator(mode="after")
    def _unique(self) -> "Build":
        keys = [i.key for i in self.images]
        if len(keys) != len(set(keys)):
            raise ValueError(f"image keys must be unique (set `id` on variants): {keys}")
        for i in self.images:
            if i.platforms and not set(i.platforms) & set(self.platforms):
                raise ValueError(f"image {i.key}: none of its platforms {i.platforms} is in build.platforms {self.platforms}")
        return self


# --- recipe -----------------------------------------------------------------


class Artifact(_Model):
    """How a component recipe's binary is built (inside a buildx stage, cross-compiled per platform)."""

    builder: str = Field("golang:{{go}}", description="Builder image; `{{go}}` = the Go version the component needs")
    build: str = Field(description="Shell command run in the checkout (/src) with TARGETOS/TARGETARCH set; must write `output`")
    output: str = Field(description="Path of the built binary inside the builder, e.g. /out/helm")


class ComponentRef(_Model):
    """A third-party binary bundled in this recipe's images, rebuilt from source and swapped in."""

    recipe: str = Field(description="Component recipe (mode: component) that patches and builds it")
    path: str = Field(description="Where the binary lives in the image, e.g. /usr/local/bin/helm")
    tag: str = Field("v{{version}}", description="Upstream tag for the version found in the image (`{{version}}` = without v)")
    images: list[str] = Field(default_factory=list, description="Image keys to apply it to (default: every image)")
    # how the bundled version is found, first match wins: version, versionFrom, Go build info, versionCommand
    version: str | None = Field(None, description="Pin the bundled version explicitly")
    versionFrom: VersionFrom | None = Field(None, description="Read it from a file in the parent's checkout (e.g. hack/tool-versions.sh)")
    versionCommand: list[str] = Field(default_factory=list, description="Run the binary in the image with these args and take "
                                                                        "the first version in its output (e.g. [version])")


class RecipeScan(_Model):
    source: bool = Field(True, description="Scan the source tree (`trivy fs`); false for Dockerfile-only projects")
    offline: bool = Field(False, description="`trivy fs --offline-scan`: resolve Maven POMs from the local ~/.m2 only (fill it with `prepare`); "
                          "avoids Maven Central rate limits")
    reachability: bool = Field(True, description="Go recipes: run govulncheck on the patched source and suggest VEX statements "
                               "for remaining findings whose vulnerable code isn't reached")
    image: bool | None = Field(None, description="Also plan bumps from findings in the built image's own artifacts (jars, Python "
                               "packages, node_modules) the source scan can't see; costs one extra run. Default: on for gradle/python")
    skipDirs: list[str] = Field(default_factory=list, description="Extra `trivy fs --skip-dirs` globs (test fixtures, examples)")
    skipFiles: list[str] = Field(default_factory=list)


class Recipe(_Model):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    description: str | None = None
    mode: Literal["source", "image-only", "component"] = Field("source", description="component: patched and tested like a source "
                                                                 "recipe, but only shipped inside other images (see `components`)")
    publish: bool = Field(True, description="false: patch, test, scan and report as usual, but never push images to the registry "
                                            "(release and Copa refresh skip the recipe). For images you may not redistribute, e.g. "
                                            "a closed-source vendor image")
    source: Source | None = None
    toolchain: Toolchain = Field(default_factory=Toolchain)
    policy: Policy = Field(default_factory=Policy)
    ecosystems: list[Ecosystem] = Field(default_factory=list)
    overrides: dict[str, list[Override]] = Field(default_factory=dict)
    holds: dict[str, list[Hold]] = Field(default_factory=dict)
    prepare: list[str] = Field(default_factory=list, description="Commands run after checkout, before the first scan "
                               "(e.g. `mvn -DskipTests install` so Trivy can resolve POMs from ~/.m2)")
    regen: list[Regen] = Field(default_factory=list)
    gitIdentity: bool = Field(True, description="Configure a throwaway git user (needed for local commits and some tests)")
    tests: Tests | None = None
    build: Build | None = None
    artifact: Artifact | None = Field(None, description="mode: component - how to build the binary")
    components: list[ComponentRef] = Field(default_factory=list, description="Bundled third-party binaries to rebuild and swap in")
    env: dict[str, str] = Field(default_factory=dict, description="Env for every stage")
    scan: RecipeScan = Field(default_factory=RecipeScan)
    notes: list[str] = Field(default_factory=list, description="Free-form notes copied into the PR report")

    @model_validator(mode="after")
    def _check(self) -> "Recipe":
        if self.mode in ("source", "component") and not self.source:
            raise ValueError(f"`source` is required when mode={self.mode}")
        if self.mode == "component" and (not self.artifact or self.build):
            raise ValueError("mode=component needs `artifact` (and no `build`)")
        for key in list(self.overrides) + list(self.holds):
            if key not in ECOSYSTEM_KEYS:
                raise ValueError(f"unknown ecosystem key {key!r} in overrides/holds (expected one of {ECOSYSTEM_KEYS})")
        return self

    def for_tag(self, tag: str) -> "Recipe":
        """This recipe as it applies to one upstream tag: holds whose `tagPattern` doesn't match it are left out."""
        holds = {eco: [h for h in hs if not h.tagPattern or re.search(h.tagPattern, tag)] for eco, hs in self.holds.items()}
        return self if holds == self.holds else self.model_copy(update={"holds": holds})


class GlobalConfig(_Model):
    registry: str = Field(description="Where patched images go, e.g. `ghcr.io/my-org`")
    tagFormat: str = Field("{{upstream_tag}}-patched.{{revision}}", description="Template for immutable patched tags")
    policy: Policy = Field(default_factory=Policy)
    overrides: dict[str, list[Override]] = Field(default_factory=dict)
    holds: dict[str, list[Hold]] = Field(default_factory=dict)
    skipGraceDays: int = Field(30, description="Expired skips warn; after this many days they fail the run")
    scan: "ScanConfig" = Field(default_factory=lambda: ScanConfig())


class ScanConfig(_Model):
    severities: list[str] = Field(default_factory=lambda: ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"])
    maxRounds: int = Field(3, description="Re-scan/re-plan rounds until the plan is empty")
    skipDirs: list[str] = Field(default_factory=lambda: ["**/testdata", "**/node_modules", "**/vendor"],
                                description="`trivy fs --skip-dirs` applied to every recipe")


# --- skips ------------------------------------------------------------------


class SkipEntry(_Model):
    match: str = Field(description="Framework-native selector: Go/nextest regex, surefire pattern, redis test name...")
    reason: str
    owner: str
    expires: dt.date | None = None
    filter: str | None = Field(None, description="nextest: raw filterset expression; jest/vitest: a test *path* pattern; "
                                                "instead of the test-name regex in `match`")


class SkipFile(_Model):
    skips: list[SkipEntry] = Field(default_factory=list)
    quarantine: list[SkipEntry] = Field(default_factory=list, description="Run, report, but don't fail when every failing test is "
                                        "quarantined; needs JUnit output (`tests.junit`)")


# --- vex --------------------------------------------------------------------


class VexStatement(_Model):
    vulnerability: str
    status: Literal["not_affected", "affected", "fixed", "under_investigation"]
    justification: Literal[
        "component_not_present",
        "vulnerable_code_not_present",
        "vulnerable_code_not_in_execute_path",
        "vulnerable_code_cannot_be_controlled_by_adversary",
        "inline_mitigations_already_exist",
    ] | None = None
    impact: str | None = Field(None, description="impact_statement for not_affected")
    action: str | None = Field(None, description="action_statement for affected, e.g. 'waiting on upstream moby v29 migration'")
    packages: list[str] = Field(default_factory=list, description="Package names/PURLs this applies to; empty = any")
    expires: dt.date | None = None

    @model_validator(mode="after")
    def _check(self) -> "VexStatement":
        if self.status == "not_affected" and not (self.justification or self.impact):
            raise ValueError("not_affected requires `justification` or `impact`")
        return self


class VexFile(_Model):
    statements: list[VexStatement] = Field(default_factory=list)


# --- inventory --------------------------------------------------------------


class InventoryImage(_Model):
    image: str = Field(description="Image reference as deployed, e.g. `quay.io/argoproj/argocd:v3.5.6`")
    usedBy: list[str] = Field(default_factory=list, description="Where it runs (clusters, apps, charts)")
    owner: str | None = None
    notes: str | None = None


class Inventory(_Model):
    images: list[InventoryImage] = Field(default_factory=list)


# --- state ------------------------------------------------------------------


class ReleasedImage(_Model):
    name: str
    ref: str
    digest: str
    knownFixable: list[str] = Field(default_factory=list, description="`vuln|package|location` of fixable findings at release; "
                                    "rescan only acts on findings not in this list")


class LineState(_Model):
    upstreamTag: str
    commit: str
    revision: int
    releasedAt: dt.datetime
    platforms: list[str] = Field(default_factory=list)
    images: list[ReleasedImage] = Field(default_factory=list)


class State(_Model):
    lines: dict[str, LineState] = Field(default_factory=dict)


GlobalConfig.model_rebuild()
