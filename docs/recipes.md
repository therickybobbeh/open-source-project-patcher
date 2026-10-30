# Recipe reference

Each upstream project has one recipe, `recipes/<name>.yaml`. `recipes/_global.yaml` holds org-wide
settings. Everything is validated by `patcher validate`. The JSON schemas in `schema/` are generated
from `patcher/src/patcher/models.py` (`patcher schema`) and are the authoritative field list. The
`# yaml-language-server: $schema=...` line at the top of each file gives editors autocompletion.

Real recipes are the best examples. See [Worked examples](#worked-examples) at the end.

## Top level

| Field | Type | Default | Meaning |
|---|---|---|---|
| `name` | string | required | Recipe id, `^[a-z0-9][a-z0-9-]*$`; must match the file name |
| `description` | string | | Free text |
| `mode` | `source` \| `image-only` \| `component` | `source` | `image-only`: no source rebuild (closed source); scan, Copa and mirror the upstream image. `component`: patched and tested like a source recipe, but only shipped inside other images ([Components](#components)) |
| `publish` | bool | `true` | `false`: patch, test, scan and report as usual, but never push images. The release workflow and Copa refresh skip the recipe, and `patcher coverage` shows it as *scanned only*. For images you may not redistribute, e.g. a closed-source vendor image (`apollo-operator`) |
| `source` | [Source](#source-and-release-lines) | required for `source` | Where upstream lives and which release lines we track |
| `toolchain` | [Toolchain](#toolchain) | | Toolchains to install with mise |
| `policy` | [Policy](#policy) | from `_global.yaml` | How far a dependency may move without a human |
| `ecosystems` | list of [ecosystems](#ecosystems) | `[]` | What to patch and how |
| `overrides` / `holds` | map ecosystem → list | `{}` | [Forced versions and pins](#overrides-and-holds) |
| `prepare` | list of commands | `[]` | Run after checkout, before the first scan (e.g. warm `~/.m2`) |
| `regen` | list of `{when, run}` | `[]` | Code generation after bumps; `when`: `always` \| `replaceGroupMoved` \| `never` |
| `gitIdentity` | bool | `true` | Provide a throwaway git user (local commits; some test suites need one) |
| `scan` | [Scan](#scan) | | Source-scan scope |
| `tests` | [Tests](#tests) | | The upstream test suite |
| `build` | [Build](#build) | | Images to build and publish |
| `components` | list of [component refs](#components) | `[]` | Bundled third-party binaries to rebuild from source and swap into this recipe's images |
| `artifact` | [Artifact](#components) | required for `component` | How a component recipe's binary is built |
| `env` | map | `{}` | Environment for every stage |
| `notes` | list of strings | `[]` | Copied into every PR report |

`prepare`, `regen`, test and build commands run with the pipeline's own `TRIVY_*`, `PATCHER_*` and
`COPA_*` variables removed, so upstream code never sees the patcher's configuration.

## Source and release lines

```yaml
source:
  repo: argoproj/argo-cd          # GitHub owner/name, or any git URL
  exclude: ['^helm-chart']        # tag regexes to ignore
  lines:
    - tagPattern: '^v3\.5\.\d+$'  # newest tag matching -> key "v3.5"
    - tagPattern: '^v3\.4\.\d+$'
```

Each line is one of the following:
- **`tagPattern`**: follow the newest tag matching this regex (semver order). The line key is a
  slug of the pattern (`^v3\.5\.\d+$` → `v3.5`) unless `name` is set.
- **`tag`**: pin one exact tag.
- **`branch`** + **`versionFrom`** + **`name`**: for projects that release from a branch without
  tags. The version is read from a file at the branch head:

  ```yaml
  - name: maven3
    branch: main
    versionFrom: { file: eclipse-temurin-17-noble/Dockerfile, var: MAVEN_VERSION }   # or pattern: '...(?P<version>...)'
  ```

Each line gets its own patch PR, release state and image tags. List the versions you actually run.

## Toolchain

| Field | Example | Meaning |
|---|---|---|
| `go` | `"1.27"` | Go major.minor. mise installs its newest patch release, which carries the stdlib fixes |
| `rust` | `"1.99.0"` / `from-repo` | `from-repo` honors the upstream `rust-toolchain.toml` |
| `java`, `maven`, `node`, `pnpm` | `temurin-21`, `"3.9"`, `"24"`, `"10.28.1"` | mise specs |
| `yarn` | `1.22.22` / `4.5.0` | Classic (1.x) or berry; the adapter handles them differently |
| `python` | `"3.12"` | mise spec |
| `extra` | `{protoc: "29.3"}` | Any other mise tool |
| `repoMise` | `true` or `[rust, protoc, "cargo:cargo-nextest"]` | Use tools pinned in the upstream repo's own mise config. A list installs just those, in order |

When bumps need a newer Go than the recipe's line (a raised `go` directive, or stdlib fixes), mise
installs that minor instead. A requirement never lowers the recipe's version. Go builder images in
Dockerfiles are raised the same way.

Fields the recipe leaves unset are **detected from the checkout** at run time:

| Toolchain | Read from |
|---|---|
| Go | `go.mod` `go` / `toolchain` |
| Node | `.nvmrc`, `.node-version`, `engines.node` |
| pnpm, yarn | `packageManager` in `package.json` |
| Python | `.python-version`, `requires-python` |
| Java | `maven.compiler.release`, the Gradle toolchain, `.java-version` |
| Rust | `rust-toolchain.toml` |

Explicit recipe values always win.

## Policy

```yaml
policy:
  default: minor            # patch | minor | major
  ecosystems: { gomod: minor, cargo: patch, go-toolchain: minor }
  minReleaseAgeDays: 7      # set in _global.yaml for every recipe
  cooldownBypass: { severities: [CRITICAL], kev: true }
```

- For each finding, the planner picks the **smallest** fixed version above the installed one. It
  prefers the same major.minor, then the same major. Anything beyond the cap is not applied and
  shows up as **needs-human** in the PR.
- For npm, pnpm, yarn and Cargo, a **0.x minor bump counts as major**, because their caret ranges
  treat it as breaking (`^0.18` excludes `0.25`). For Go, `golang.org/x/*` v0 bumps stay routine.
- `go-toolchain` caps how far Go stdlib fixes may move the build's Go version.
- **Release age:** a fix version must have been published at least `minReleaseAgeDays` ago, so a
  freshly hijacked release can't ride in on a bump. The next-oldest fixed version that is old enough
  is used instead. When none is, the finding is reported as `cooldown: <ver> released N day(s) ago
  (eligible <date>)` and a later nightly run picks it up.
  - Publish times come from the Go module proxy, the npm registry, PyPI, Maven Central and crates.io.
    When a publish time can't be found, the bump goes ahead with a note in the report.
  - `cooldownBypass`: findings of these severities, and CVEs on CISA's Known Exploited Vulnerabilities
    list (fetched once per run), are fixed immediately.
  - `patcher run --no-cooldown` turns the rule off for one local run.
- **Withdrawn releases are never used**, whatever the severity: a version npm marks deprecated, or
  PyPI or crates.io marks yanked, is replaced by the next release in the same major line that
  stands. For example, lodash 4.18.0 ("Bad release" on npm, it broke `lodash/template`) becomes
  4.18.1. The report notes the substitution.

## Ecosystems

### `gomod`

```yaml
- type: gomod
  dirs: [".", "api/v2", "providers/v1/*"]     # module dirs (globs); each has a go.mod
  replaceGroups:
    - pattern: '^k8s\.io/'                    # members at the same version move together
  bumpToolchainDirective: true                # raise an existing `toolchain` line for stdlib fixes
```

How it works:
- **Bumping:** `go get mod@version` for every bump in a module, as one batch. If the batch fails,
  modules are applied one at a time, skipping any that another bump has already raised past its
  target. `go get` would otherwise silently *downgrade*.
- **Replace-pinned modules:** `go mod edit -replace/-require` is used instead of `go get`, and a
  replace group moves once, to the highest fix any member needs.
- **Afterwards:** `go mod tidy`, plus `go mod vendor` if a `vendor/` dir exists. A raised `go`
  directive is recorded and raises the Go requirement.
- **Unlisted modules:** findings in a module that isn't in `dirs` are reported, not applied.

### `cargo`

```yaml
- type: cargo
  dirs: ["."]          # workspace roots (contain Cargo.lock)
```

`cargo update -p name@installed --precise version`, so each version of a crate in the lockfile is
handled separately. A fix outside the semver range that `Cargo.toml` allows becomes a needs-human
failure: bump the parent crate or add `[patch.crates-io]` via `patches/`.

### `maven`

```yaml
- type: maven
  poms: [pom.xml, "kafka-thirdparty-libs/*/pom.xml"]   # reactor roots (globs)
```

Each finding is handled in the **deepest reactor root whose directory contains its `pom.xml`**:
1. `versions:use-dep-version` updates explicit declarations, including the properties they use.
2. The dependency is pinned in that root's `<dependencyManagement>`. Dependency management beats
   mediation, so this fixes transitive dependencies too. The pin is indented like the file and
   commented with the CVEs.

Pair Maven recipes with `prepare: ["mvn -DskipTests install"]` and `scan.offline: true`; see [Scan](#scan).

### `npm` / `pnpm` / `yarn`

```yaml
- type: pnpm
  dirs: [ui]           # dirs with package.json + the lockfile
```

- **Where overrides go:**
  - npm: `overrides`
  - pnpm: `pnpm.overrides` in `package.json`, or `overrides` in `pnpm-workspace.yaml` (pnpm ≥ 11, or
    when the file exists)
  - yarn: `resolutions`
- **How they're keyed:** `name@installed`, so only the vulnerable copy moves and other major lines in
  the lockfile stay put. If upstream already pins the package to the vulnerable version, that pin is
  moved instead of adding a second entry.
- **Afterwards:** the lockfile is regenerated with lifecycle scripts disabled.
- **yarn classic vs. berry:** the major version comes from `packageManager` (or `toolchain.yarn`).
  Classic installs with `--ignore-scripts` through a temporary yarnrc, so an upstream `.yarnrc` with
  `--frozen-lockfile` doesn't block the update. Berry uses `--mode=update-lockfile`.
- **yarn resolutions** move every installed copy of a package. A package installed in several major
  lines therefore becomes needs-human, instead of one resolution that would force every copy onto
  one major.

### `python`

```yaml
- type: python
  dirs: [".", "services/*"]   # project dirs (globs)
  tool: auto                  # auto | uv | poetry | pipenv | pip-tools | pip
  toolVersion: "2.5.1"        # poetry / pipenv / pip-tools version (default: from the lockfile header, else pinned)
```

The tool is detected per dir:

| Tool | Detected by | How a bump is applied |
|---|---|---|
| uv | `uv.lock` | `uv lock --upgrade-package name==ver` |
| poetry | `poetry.lock` | `poetry update --lock name`. If the lock still has the old version, a direct dependency becomes needs-human (its constraint doesn't allow the fix) and a transitive one gets an explicit `name>=ver` constraint |
| pipenv | `Pipfile.lock` | `pipenv upgrade name>=ver` |
| pip-tools | `requirements.in`, or a `pip-compile` / `uv pip compile` header in `requirements.txt` | The command recorded in the header is re-run, with `--upgrade-package name==ver` and without any `--upgrade` that would move everything else |
| pip | `requirements*.txt` | `name==old` becomes `name==new`. A loose line gets a lower bound (`name>=1.0` → `name>=1.0,>=1.2.5`), and a transitive package gets its own `name>=fixed` line, like an npm override. A hash-checked file with nothing to recompile from is needs-human |

- poetry, pipenv and pip-tools run through `uvx` at pinned versions. uv itself is pinned in the
  patcher image.
- Versions are compared with PEP 440 rules.
- Every change is checked against the lockfile afterwards. A bump that didn't land is reported, not
  claimed.
- Trivy only reads lockfiles and exact `==` pins. Dependencies an image installs from loose ranges
  are found by the [image scan](#scan) instead, and bumped in the first `dirs` entry's lockfile or
  requirements file. That only helps if the Dockerfile installs from that file; otherwise the finding
  stays in the report.

### `gradle`

```yaml
- type: gradle
  dirs: ["."]                            # build roots
  catalog: gradle/libs.versions.toml     # default
```

- **Direct dependencies in the version catalog:** the catalog version is edited. This covers
  `[versions]` refs, `version = "..."` and `"group:artifact:version"` forms. A shared `[versions]`
  entry only moves when every library using it is in the same group (a family like `jackson-*`);
  otherwise the dependency is pinned in the constraints script instead.
- **Everything else:** pins go into a generated `gradle/patcher-constraints.gradle`, wired in with one
  `apply from:` line in the root `build.gradle(.kts)`.
  - **What it does:** for every project it registers a `resolutionStrategy.eachDependency` rule after
    the project is evaluated. The rule raises each request for a listed module to at least the fixed
    version, and records the CVE with `because`.
  - **Why a rule:** it runs after the rules plugins add, so it also beats versions that Spring's
    dependency-management plugin sets from its BOM. Plain `dependencies { constraints { } }` lose to
    that plugin: it rewrites them back to the BOM version (seen with spring-petclinic).
  - **Never downgrades:** requests already above the fixed version are left alone.
- **Lockfiles:** when `gradle.lockfile`s exist, they are re-written with
  `./gradlew dependencies --write-locks`.
- **Finding the versions:** without lockfiles, Trivy can't see Gradle dependencies in the source tree.
  Gradle recipes therefore plan from the built image's jars (`scan.image`, on by default for
  `gradle` and `python`).

### `dockerfile`

```yaml
- type: dockerfile
  files: [Dockerfile, "docker-images/*/Dockerfile"]
  level: patch           # how far a base tag may move
  pinDigest: true        # write image:tag@sha256:...
  ignore: ['^maven$']    # image names to leave alone
  minVersions: {node: "24"}   # release lines a base image must not fall below
```

- **Tag selection:** each `FROM` moves to the newest tag of the same shape: same prefix, same suffix
  (`-alpine3.24`), same number of version parts, within `level`. Floating tags (`latest`,
  `bookworm-slim`) keep their tag but get a fresh digest pin.
- **ARG-based images:** `ARG GO_VERSION=…` + `FROM golang:${GO_VERSION}-alpine${ALPINE_VERSION}`
  and `FROM $BASE_IMAGE` are handled by updating the ARG defaults. When the ARGs only build the name
  and the tag is written out (`FROM ${DOCKER_REPO}/alpine:3.24`), the tag is moved in the `FROM` line.
- **Go builders:** Go builder images are raised to the Go version the plan requires.
- **End-of-life bases (`minVersions`):** a release line per image name (`node`, `alpine`, `golang`;
  one or two numbers). A tag below it moves to the newest tag of the same shape in that line, past
  `level`: with `{node: "24"}`, `node:20-alpine` becomes `node:24-alpine` and `node:23.0.0` the newest
  `24.x.y`. Tags at or above the line follow `level` as usual. Use it when upstream builds on an
  end-of-life runtime, and say why in a comment; the report marks these moves `(minVersions: …)`.
  The daily rescan's `end-of-life` issues say when one is needed (`patcher eol`).
- **Hints:** a newer *minor* of the same major is reported, e.g. gomplate v5.2 → v5.3. It is not
  applied unless you raise `level`.

### `files`

Version pins in scripts and Dockerfiles, plus edits that must follow them:

```yaml
- type: files
  edits:
    - file: "*/Dockerfile"                 # glob
      var: REDIS_VERSION                   # NAME=1.2.3 / NAME 1.2.3 / NAME: 1.2.3 / ENV|ARG|export NAME=...
      to: latest-patch                     # latest-patch | latest-minor | an explicit version
      source: { git: redis/redis, tagPattern: '^\d+\.\d+\.\d+$' }
      derived:
        - var: REDIS_DOWNLOAD_URL
          value: "https://github.com/redis/redis/releases/download/{{version}}/redis-full.tar.gz"
        - var: REDIS_DOWNLOAD_SHA
          sha256Of: "https://github.com/redis/redis/releases/download/{{version}}/redis-full.tar.gz"
```

- `pattern:` can be used instead of `var:`. Main edits need a named group `version`; derived edits
  need a named group `value`.
- Derived templates: `{{version}}`, `{{version_v}}` (with a `v`), `{{old_version}}`.

## Overrides and holds

```yaml
overrides:   # "if a lower version is found, force at least this", even without a CVE
  gomod:
    - { name: golang.org/x/net, min: v0.45.0, reason: org baseline }
    - { name: "golang.org/x/*", min: ..., reason: ... }     # globs allowed
  maven:
    - { name: "com.fasterxml.jackson.core:jackson-databind", version: 2.18.2, reason: exact pin }
holds:       # never bump (or never past `max`)
  gomod:
    - { name: k8s.io/kube-openapi, reason: upstream pin (SMD v6) }
    - { name: oras.land/oras-go/v2, tagPattern: '^v3\.', reason: helm 3 only }   # only for these upstream tags
  npm:
    - { name: react, max: 18.3.1, reason: UI not ready for 19 }
```

- **Keys** are ecosystem names: `gomod`, `cargo`, `maven`, `gradle`, `npm`, `pnpm`, `yarn`, `python`,
  `dockerfile`, `files`.
- **Precedence:** entries in `_global.yaml` apply to every recipe, and a recipe entry with the same
  `name` replaces the global one.
- **Overrides ignore the policy cap:** an override is a human decision.
- **`tagPattern` on a hold** limits it to the upstream tags it matches. A component recipe serves
  every version its parents bundle, so a bump that breaks one major (helm 3) can be held there
  without holding back the next (helm 4).

## Scan

| Field | Default | Meaning |
|---|---|---|
| `source` | `true` | `false` skips `trivy fs` for Dockerfile-only projects (only the images are judged) |
| `offline` | `false` | `trivy fs --offline-scan`: resolve Maven POMs from the local `~/.m2`. Avoids Maven Central's per-IP rate limiting (HTTP 429) |
| `skipDirs`, `skipFiles` | `[]` | Unshipped trees: test fixtures, examples, release tooling. Added to `_global.yaml`'s `scan.skipDirs` |
| `image` | on for `gradle`/`python`, else off | Also plan from fixable findings in the built image's **own** artifacts (jars, Python packages, node_modules) that the source scan couldn't see; costs one extra build. Bundled third-party binaries and base-image tooling (pip, the global npm) are excluded |
| `reachability` | `true` | Go recipes: run `govulncheck` on the patched source and draft VEX suggestions for remaining findings whose vulnerable code is never called. See the [runbook](runbook.md#vex-suggestions-from-reachability) |

## Tests

| Field | Default | Meaning |
|---|---|---|
| `framework` | required | `go`, `nextest`, `surefire`, `gradle`, `pytest`, `jest`, `vitest`, `mocha`, `redis`, `bats`, `generic`. Decides how skips are applied |
| `setup` | `[]` | Commands before the test command (always as root) |
| `command` | required | The upstream test command. May use `{{skip_args}}`, `{{skip_regex}}`, `{{skip_file}}`, `{{src}}` |
| `skipVia` | | `{env: TEST_FLAGS, format: "-skip={{skip_regex}}"}` for suites that read flags from an env var |
| `env` | `{}` | Test environment (values may use the same placeholders) |
| `services` | | `{compose: docker-compose.yml, services: [...]}`, started before and torn down after the tests |
| `junit` | `[]` | Globs of JUnit files to collect (needed for `quarantine`) |
| `timeoutMinutes` | `90` | |
| `runAs` | `root` | `nonroot` runs the command as an unprivileged user. Use it when tests assert permission errors, which root bypasses |
| `enabled` | `true` | |

How `skips/<name>.yaml` entries become filters:

| Framework | Applied as |
|---|---|
| `go` | `-skip=<joined regex>` via `{{skip_args}}`, or `{{skip_regex}}` inside `skipVia` |
| `nextest` | `-E 'not (test(/match/) \| …)'`; an entry's `filter:` is used verbatim |
| `surefire` | `-Dsurefire.excludesFile=<file>` |
| `redis` | `--skipfile <file>` |
| `gradle` | a generated init script (`--init-script <file>`) with `filter.excludeTestsMatching` per entry |
| `pytest` | entries with `::` are node ids, passed as `--deselect`; others are joined into `-k 'not (…)'` |
| `jest` | `match` = test-name regex, as `--testNamePattern '^(?!.*(…))'`; `filter` = path, as `--testPathIgnorePatterns` |
| `vitest` | like jest; paths as `--exclude` |
| `mocha` | `--grep <joined regex> --invert` |
| `generic` | exported as `PATCHER_SKIP_REGEX` |
| `bats` | not supported (a non-empty skip list is refused) |

A run fails rather than silently ignoring skips when the skip file has entries but the command uses
no skip placeholder.

When the patched tests fail, the same tests run on the **unpatched** source (upstream tag plus
`patches/`, no bumps). If every failing test also fails there, the run is `tests-preexisting`: the
PR is ready for review and labeled `preexisting-test-failures`. Otherwise the run retries with
patch-level bumps only, and the PR is a draft if failures remain. Failing tests are compared using
JUnit when available, otherwise by test ids parsed from the log (durations and counts removed). The
same patch-level retry happens when the image **build** or a smoke test fails. If the suite fails
before any test runs, with the same error on the unpatched source, the report calls it an
environment problem and skips the retry.

Install test dependencies into the checkout, never into the shared toolchain. For Python, use a
project `.venv`, `uv sync` or `poetry install` with `POETRY_VIRTUALENVS_IN_PROJECT=true`; see
`patcher init`'s drafts.

**Install cutoff:** while the release-age rule is on, `setup` and `command` run with
`UV_EXCLUDE_NEWER`, `PIP_UPLOADED_PRIOR_TO` (pip ≥ 26) and `npm_config_before` set to the rule's
cutoff, or to the upstream release time if that is later. Dependencies a test setup installs from
version ranges then resolve roughly as they did for upstream's CI, and a release from yesterday can't
break, or compromise, the run. Lockfile installs are unaffected. Set any of these in `tests.env` to
override, e.g. `UV_EXCLUDE_NEWER: "2026-10-01T00:00:00Z"`. When a CRITICAL or KEV fix younger than the
rule was bumped, no cutoff is set, so the fix stays installable.

## Build

```yaml
build:
  platforms: [linux/amd64, linux/arm64]   # the default; each is built on its own native runner at release
  setup: ["make build"]               # optional, before the images
  env: { BUILDX_BUILDER: default }    # optional
  images:
    - name: dex                       # our repository: ghcr.io/<owner>/dex
      id: dex-distroless              # unique key when variants share a repository
      upstream: ghcr.io/dexidp/dex    # baseline scan
      upstreamTag: "{{tag}}-distroless"   # upstream tag, also the base of ours
      dockerfile: Dockerfile
      context: .
      args: { VERSION: "{{tag}}", BASE_IMAGE: distroless }
      smoke: ["dex version"]          # `docker run --rm <image> dex version` must exit 0
      # smokeEnv: {SPLUNK_REALM: us0}  # `docker run -e` for the smoke commands, for images that refuse to start without
      ownBinaries: [usr/local/bin/dex]   # everything else is reported as a bundled artifact
      copa: true
```

| Image field | Meaning |
|---|---|
| `command` + `builtImage` | Custom build instead of buildx, e.g. `make docker.build`. It must produce `builtImage`, for `{{platform}}` only: the release checks that each image it saves is one image of that platform |
| `platforms` | An image that exists for fewer platforms than `build.platforms` (e.g. Apollo's amd64-only bundle-loader): it is built, pushed and merged for those only. Only platforms also in `build.platforms` count, and at least one must be |
| `tagPattern` | Image-only recipes: an image that versions separately from the line |
| `timeoutMinutes` (on `build`) | Per image build, build `setup` command and component overlay (default 60). A build that hangs or fails on a network error is retried once |
| `copa` | `true` (default): Copa patches leftover OS packages. `false`: off. `{libraries: true, level: patch}`: also patch Python and npm packages inside the image (Copa's experimental library patching, `COPA_EXPERIMENTAL=1`); meant for closed-source images that can't be rebuilt |
| `bundledJars` | `{paths: [usr/share/maven/], level: patch}`: swap vulnerable jars of a third-party Java distribution the image unpacks for fixed releases from Maven Central. See [Bundled jars](#bundled-jars) |

Templates: `{{tag}}`, `{{version}}` (tag without `v`), `{{commit}}`, `{{short_commit}}`, and in
image builds also `{{image}}`, `{{platform}}`, `{{arch}}`. Unknown placeholders are errors.

## Components

Images often bundle third-party binaries that their own build doesn't compile: helm, kustomize and
git-lfs in Argo CD; gomplate in Dex; the credential helpers in Apollo's closed-source operator. Their
findings can't be fixed by bumping the parent's dependencies. A **component** rebuilds such a binary
from its own source at the same version, with patched dependencies and its own tests, and swaps it
into the parent image.

```yaml
# recipes/argo-cd.yaml (the parent)
components:
  - recipe: helm
    path: /usr/local/bin/helm               # version from the binary's Go build info
  - recipe: kustomize
    path: /usr/local/bin/kustomize
    tag: "kustomize/v{{version}}"            # upstream tag for that version
    versionFrom: { file: hack/tool-versions.sh, var: kustomize5_version }
  - recipe: git-lfs
    path: /usr/bin/git-lfs
    versionCommand: [version]                # run `git-lfs version` in the image
    images: [argocd]                         # default: every image of the recipe
```

```yaml
# recipes/helm.yaml (the component)
name: helm
mode: component
source: { repo: helm/helm, lines: [{ tagPattern: '^v4\.\d+\.\d+$' }] }
toolchain: { go: "1.26" }                    # the floor for tests and the build
ecosystems: [{ type: gomod }]
tests: { framework: go, command: "go test {{skip_args}} ./..." }
artifact:
  builder: "golang:{{go}}"                   # {{go}}: the highest of toolchain.go, go.mod and the bumps' needs
  build: CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH go build -o /out/helm ./cmd/helm
  output: /out/helm
```

- **Version:** the first of `version`, `versionFrom` (a file in the parent's checkout), the binary's
  Go build info, and `versionCommand` that yields one.
- **Patch and test:** the component recipe runs like a source recipe on exactly that tag:
  policy, release-age rule, skips and baseline included. Results are cached per run, so several
  images share one build.
- **Overlay:** the parent image is rebuilt `FROM` itself with each usable component's binary copied
  over the original. Binaries are cross-compiled per platform in a buildx stage, with no emulation.
- **Go version:** set `toolchain.go` on Go components. A tool's `go.mod` can name an end-of-life Go
  (git-lfs 3.7.1 and kustomize 5.8.1 name 1.24), and a binary built with it ships that Go's
  unpatched standard library. The builder uses the highest of `toolchain.go`, the `go.mod` and what
  the bumps need.
  Smoke tests, Copa and the after-scan run on the result.
- **Usable** means the component's run ended `success`, `no-changes` or `tests-preexisting`.
  Otherwise the original binary stays, and the report says why.
- **One version per line:** if two images of a line bundle different versions of the same component,
  the first image's version is rebuilt. The other image keeps its original binary (`kept-original`,
  with a note).
- **PR and release:** the component's diff and report go into the parent's PR under
  `generated/<recipe>/<tag>/components/<component>/`. The release rebuilds exactly that reviewed
  diff.
- **Planning:** a change to a component recipe, its skips or its patches re-runs every parent.
  Components never run on their own.

## Bundled jars

Some images unpack a third-party Java distribution whose jars their own build doesn't control: Apache
Maven in `/usr/share/maven` in the official maven image, Kafka's release tarball in `/opt/kafka/libs`
in Strimzi's broker images. No recipe bump reaches those jars, and the distribution may have no fixed
release yet. `bundledJars` on an image swaps each vulnerable jar for the fixed release from Maven
Central:

```yaml
build:
  images:
    - name: maven
      smoke: ["mvn -v", "mvn -B -emp smoke"]   # include a command that loads the swapped jars
      bundledJars: { paths: [usr/share/maven/], level: patch }
```

| Field | Default | Meaning |
|---|---|---|
| `paths` | required | Directory prefixes (or jar paths) in the image. Fixable findings in jars under them are swapped |
| `level` | `patch` | How far a jar may move. A fix beyond it is reported as needs-human |

Per image, after the build (and its components) and before the smoke tests:
- **Planning:** the built image's fixable jar findings under `paths` are planned like Maven source
  bumps. That means the smallest fixed version within `level`, the [release-age rule](#policy) with its
  CRITICAL/KEV bypass, and `holds` under the `maven` key. The withdrawn-release check runs too, but
  Maven Central never withdraws a release, so it has nothing to find there. `overrides` don't apply.
- **Fix versions:** advisories don't always name a release that exists. Each fix version is matched
  to Central's releases in the installed jar's flavor: Guava's advisory says `33.7.2`, so a
  `33.7.1-jre` jar gets `33.7.2-jre`.
- **Only the artifact's own jar:** the file must be named `artifact-version[-classifier].jar`. A library
  shaded into another jar, or a renamed jar, isn't swapped, and the report says why.
- **Download:** from Maven Central, checked against the sha256 Central publishes next to it (sha1 for
  older releases). Its sha256 becomes the pin.
- **Swap:** the overlay build that swaps [components](#components) in also copies each new jar **over
  the old one, keeping the old file name**:
  - it needs no RUN step, so it works for images without a shell, and for every platform without
    emulation;
  - anything that names the jar (a manifest `Class-Path`, a launcher script) keeps working;
  - scanners read the version from the jar's own `pom.properties`, so Trivy reports the new one.

  The image gets a `patcher.swapped-jars` label listing each swap.
- **Then** come the smoke tests, Copa and the after-scan. Pick a smoke command that loads the
  distribution's jars: `mvn -v` doesn't (it passes even with an empty Guava jar), while
  `mvn -B -emp smoke` starts Maven's DI container offline.
- **Report:** a *Bundled jars swapped* section lists each swap: coordinates, from → to, CVEs and
  sha256. Findings left in those jars get a reason starting with `bundled jar:`, e.g. a cooldown, or
  needs-human beyond `bundledJars.level`.
- **PR and release:** the swaps are recorded in `generated/<recipe>/<tag>/jars.json`. The release
  overlays exactly those swaps, after two checks:
  - each jar is downloaded again and must match its pin;
  - on every platform, the rebuilt (or vendor) image must still have exactly the jar that was
    replaced, by sha256.

  A mismatch fails the release, rather than adding a second, unreviewed jar.
- **Image planning** (`scan.image`) leaves jars under `paths` alone: they aren't built from the source.

A run that only swaps jars (no source changes) still opens a PR: the image changed. For the Kafka
broker images, the same setting would be `bundledJars: {paths: [opt/kafka/libs/]}` on each image,
with a smoke command that runs one of Kafka's own tools (e.g. `/opt/kafka/bin/kafka-storage.sh
random-uuid`), so the JVM starts with `libs/` on its classpath.

## Global config (`recipes/_global.yaml`)

| Field | Meaning |
|---|---|
| `registry` | Where images go; CI overrides it with `PATCHER_REGISTRY=ghcr.io/<owner>` |
| `tagFormat` | `{{upstream_tag}}-patched.{{revision}}` |
| `policy`, `overrides`, `holds` | Defaults for every recipe (including the 7-day `minReleaseAgeDays` rule) |
| `skipGraceDays` | Expired skips warn, and fail the run this many days after `expires` |
| `scan.severities`, `scan.maxRounds`, `scan.skipDirs` | Trivy severities, plan/apply rounds, dirs skipped everywhere |

## Worked examples

| Recipe | Shows |
|---|---|
| [`dex.yaml`](../recipes/dex.yaml) | Go with a nested module, gotestsum JUnit, two image variants (`id`), `ownBinaries` |
| [`argo-cd.yaml`](../recipes/argo-cd.yaml) | Go replace group (`k8s.io/*`), pnpm UI, `skipVia` through `TEST_FLAGS`, `runAs: nonroot`, two release lines |
| [`external-secrets.yaml`](../recipes/external-secrets.yaml) | Go multi-module with globs, a hold, custom build `command` |
| [`trivy.yaml`](../recipes/trivy.yaml) | `go tool mage` tests, custom build into goreleaser's layout, tags without `v` |
| [`copacetic.yaml`](../recipes/copacetic.yaml) | Extra files from `patches/copacetic/files/` (our own CLI image Dockerfile), multi-ARG `FROM` |
| [`apollo-router.yaml`](../recipes/apollo-router.yaml) | Cargo, `repoMise` tool list, nextest skips, docker-compose `services` |
| [`strimzi.yaml`](../recipes/strimzi.yaml) | Maven reactor, `prepare` + `scan.offline`, surefire, custom multi-step image build |
| [`redis.yaml`](../recipes/redis.yaml) | `files` edits with derived URL + sha256, Redis' own `runtest` |
| [`maven.yaml`](../recipes/maven.yaml) | Branch-tracked line with `versionFrom`, bats tests, `scan.source: false` |
| [`strimzi-maven-builder.yaml`](../recipes/strimzi-maven-builder.yaml) | Dockerfile-only rebuild (UBI base refresh) |
| [`apollo-operator.yaml`](../recipes/apollo-operator.yaml) | `mode: image-only`, per-image `tagPattern` and `platforms`, components in a closed-source image |
| [`argo-workflows.yaml`](../recipes/argo-workflows.yaml) | Three images from one Dockerfile (`target`), yarn classic UI, Testcontainers-backed Go tests |
| [`argo-rollouts.yaml`](../recipes/argo-rollouts.yaml) | pnpm workspace UI, default target plus a named target |
| [`helm.yaml`](../recipes/helm.yaml), [`kustomize.yaml`](../recipes/kustomize.yaml), [`gomplate.yaml`](../recipes/gomplate.yaml) | `mode: component` with an `artifact` build |
| [`examples/`](examples/README.md) | Python (pip-compiled image build; pytest with a venv), Gradle (image-driven planning), a vendor image with Copa library patching |
