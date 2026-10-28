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
| `mode` | `source` \| `image-only` | `source` | `image-only`: no source rebuild (closed source); scan, Copa and mirror the upstream image |
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
| `extra` | `{protoc: "29.3"}` | Any other mise tool |
| `repoMise` | `true` or `[rust, protoc, "cargo:cargo-nextest"]` | Use tools pinned in the upstream repo's own mise config. A list installs just those, in order |

When bumps need a newer Go than the recipe's line (a raised `go` directive, or stdlib fixes), mise
installs that minor instead. A requirement never lowers the recipe's version. Go builder images in
Dockerfiles are raised the same way.

## Policy

```yaml
policy:
  default: minor            # patch | minor | major
  ecosystems: { gomod: minor, cargo: patch, go-toolchain: minor }
```

- For each finding, the planner picks the **smallest** fixed version above the installed one. It
  prefers the same major.minor, then the same major. Anything beyond the cap is not applied and
  shows up as **needs-human** in the PR.
- For npm, pnpm, yarn and Cargo, a **0.x minor bump counts as major**, because their caret ranges
  treat it as breaking (`^0.18` excludes `0.25`). For Go, `golang.org/x/*` v0 bumps stay routine.
- `go-toolchain` caps how far Go stdlib fixes may move the build's Go version.

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

### `dockerfile`

```yaml
- type: dockerfile
  files: [Dockerfile, "docker-images/*/Dockerfile"]
  level: patch           # how far a base tag may move
  pinDigest: true        # write image:tag@sha256:...
  ignore: ['^maven$']    # image names to leave alone
```

- **Tag selection:** each `FROM` moves to the newest tag of the same shape: same prefix, same suffix
  (`-alpine3.24`), same number of version parts, within `level`. Floating tags (`latest`,
  `bookworm-slim`) keep their tag but get a fresh digest pin.
- **ARG-based images:** `ARG GO_VERSION=…` + `FROM golang:${GO_VERSION}-alpine${ALPINE_VERSION}`
  and `FROM $BASE_IMAGE` are handled by updating the ARG defaults.
- **Go builders:** Go builder images are raised to the Go version the plan requires.
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
  npm:
    - { name: react, max: 18.3.1, reason: UI not ready for 19 }
```

- **Keys** are ecosystem names: `gomod`, `cargo`, `maven`, `npm`, `pnpm`, `yarn`, `dockerfile`, `files`.
- **Precedence:** entries in `_global.yaml` apply to every recipe, and a recipe entry with the same
  `name` replaces the global one.
- **Overrides ignore the policy cap:** an override is a human decision.

## Scan

| Field | Default | Meaning |
|---|---|---|
| `source` | `true` | `false` skips `trivy fs` for Dockerfile-only projects (only the images are judged) |
| `offline` | `false` | `trivy fs --offline-scan`: resolve Maven POMs from the local `~/.m2`. Avoids Maven Central's per-IP rate limiting (HTTP 429) |
| `skipDirs`, `skipFiles` | `[]` | Unshipped trees: test fixtures, examples, release tooling. Added to `_global.yaml`'s `scan.skipDirs` |

## Tests

| Field | Default | Meaning |
|---|---|---|
| `framework` | required | `go`, `nextest`, `surefire`, `redis`, `jest`, `bats`, `generic`. Decides how skips are applied |
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
| `jest` | `--testPathIgnorePatterns ...` |
| `generic` | exported as `PATCHER_SKIP_REGEX` |
| `bats` | not supported (a non-empty skip list is refused) |

A run fails rather than silently ignoring skips when the skip file has entries but the command uses
no skip placeholder.

## Build

```yaml
build:
  platforms: [linux/amd64, linux/arm64]
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
      ownBinaries: [usr/local/bin/dex]   # everything else is reported as a bundled artifact
      copa: true
```

| Image field | Meaning |
|---|---|
| `command` + `builtImage` | Custom build instead of buildx, e.g. `make docker.build`. It must produce `builtImage` |
| `tagPattern`, `platforms` | Image-only recipes: an image that versions or ships separately from the line (e.g. Apollo's bundle-loader) |

Templates: `{{tag}}`, `{{version}}` (tag without `v`), `{{commit}}`, `{{short_commit}}`, and in
image builds also `{{image}}`, `{{platform}}`, `{{arch}}`. Unknown placeholders are errors.

## Global config (`recipes/_global.yaml`)

| Field | Meaning |
|---|---|
| `registry` | Where images go; CI overrides it with `PATCHER_REGISTRY=ghcr.io/<owner>` |
| `tagFormat` | `{{upstream_tag}}-patched.{{revision}}` |
| `policy`, `overrides`, `holds` | Defaults for every recipe |
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
| [`apollo-operator.yaml`](../recipes/apollo-operator.yaml) | `mode: image-only`, per-image `tagPattern` and `platforms` |
