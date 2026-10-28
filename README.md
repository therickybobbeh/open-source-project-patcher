# support-images

Automated, source-level patching of the open-source images we run. For every upstream project:

1. check out the upstream release from GitHub,
2. bump vulnerable dependencies with each ecosystem's own tooling, driven by a **recipe**
   (`recipes/<project>.yaml`) with forced minimum versions (**overrides**) and **holds**,
3. run the **upstream test suite**, minus the entries in `skips/<project>.yaml`,
4. build the image with the upstream build, then patch leftover OS packages with **Copa**,
5. open a **PR in this repo** with the patch set, a before/after CVE report and test results.
   Merging it publishes a signed image to GHCR.

Copa on its own only patches OS packages. Most CVEs in these images are in Go modules, Rust
crates, Maven jars, npm packages and the Go standard library, which need a rebuild from source.
This repo does that rebuild, and uses Copa as the final OS-package step and as a fast path for
OS-only refreshes.

| Project | Recipe | Source | Ecosystems patched | Upstream tests |
|---|---|---|---|---|
| Argo CD | `argo-cd` | argoproj/argo-cd | gomod (+ gitops-engine, k8s replace group), pnpm, Dockerfile bases | `make test-local` |
| Dex | `dex` | dexidp/dex | gomod (+ api/v2), Dockerfile bases | `go test -race ./...` via gotestsum |
| External Secrets | `external-secrets` | external-secrets/external-secrets | gomod (root + providers/generators), Dockerfile bases | `make test` (envtest) |
| Trivy | `trivy` | aquasecurity/trivy | gomod, Dockerfile bases | `mage test:unit` |
| Copacetic | `copacetic` | project-copacetic/copacetic | gomod, Dockerfile bases (builds a copa CLI image + frontend) | `make test` (pkg) |
| Apollo Router | `apollo-router` | apollographql/router | cargo, Dockerfile bases | `cargo nextest` + compose services |
| Apollo GraphOS Operator | `apollo-operator` | closed source | image-only: mirror + scan + Copa (no OS layer, so report only) | – |
| Redis | `redis` | redis/docker-library-redis | Redis point release, Dockerfile bases | Redis `./runtest` |
| Strimzi operator | `strimzi` | strimzi/strimzi-kafka-operator | maven, Dockerfile bases | `mvn -DskipITs install` |
| Strimzi maven-builder | `strimzi-maven-builder` | strimzi/strimzi-kafka-operator | Dockerfile base (UBI) + rebuild | smoke `mvn -v` |
| Maven (official image) | `maven` | carlossg/docker-maven (branch `main`) | Dockerfile bases (eclipse-temurin) | upstream bats suite |

## Layout

```
recipes/_global.yaml        org-wide policy, overrides/holds, registry, tag format
recipes/<project>.yaml      one recipe per upstream project
skips/<project>.yaml        upstream tests to skip / quarantine (reason, owner, expiry)
vex/<project>.yaml          decisions for findings we can't fix (published as OpenVEX)
patches/<project>/*.patch   hand-written patches applied after checkout
patches/<project>/files/    files copied over the checkout (e.g. extra Dockerfiles)
generated/<project>/<tag>/  WRITTEN BY CI, reviewed via PR: deps.patch, bump-plan.json, report.md
state/<project>.yaml        what was released (tag, revision, digests); written by the release flow
patcher/                    the Python CLI + the portable patcher image (patcher/Dockerfile)
schema/                     JSON schemas (`patcher schema`); recipes reference them for editor validation
```

## How a run works (`patcher run <recipe>`)

1. **resolve**: for each release line in the recipe, the newest upstream tag matching
   `tagPattern` (or a pinned `tag`, or a `branch` head with the version read from a file).
2. **checkout**: shallow clone at that tag; apply `patches/<project>/`.
3. **toolchains**: mise installs the recipe's Go/Rust/Java/Maven/Node/pnpm versions, or tools
   pinned in the upstream repo's own mise config (`repoMise: [rust, protoc, …]`; `true` = all of them).
4. **scan**: `trivy fs` on the source and `trivy image` on the upstream image (the baseline).
5. **plan**: for every fixable finding, the *smallest* fixed version above the installed one,
   preferring the same major.minor, capped by the policy (`patch`/`minor`/`major`). Then
   overrides are forced and holds are removed. Go `stdlib` findings become a Go toolchain
   requirement (the build uses a fixed Go), not a go.mod change.
6. **apply**, per ecosystem:
   - `gomod`: `go get`; replace-pinned modules and replace groups via `go mod edit`; `go mod tidy`.
   - `cargo`: `cargo update -p name@installed --precise`.
   - `maven`: `versions:use-dep-version`, then `<dependencyManagement>` pins for transitive deps.
   - `npm`/`pnpm`/`yarn`: overrides/resolutions, then the lockfile is regenerated.
   - Re-scan and repeat (up to 3 rounds), because a bump can pull in other versions.
   - Then `dockerfile` (base images to the newest patch tag, digest-pinned; Go builders raised to
     the required Go) and `files` (version pins in scripts/Dockerfiles, with derived URL/sha256 edits).
7. **regen** (optional per recipe), then a local **commit**. The upstream tag is moved to that
   commit so version stamping still reports the upstream version.
8. **test**: the recipe's command, with `skips/` translated into the framework's own filter.
   If tests fail and some bumps were minor/major, the run retries once with patch-level bumps only.
9. **build** with the upstream Dockerfile/build, plus smoke commands; **Copa** for leftover OS packages.
10. **report**: before/after table, applied changes, what's still fixable and why (needs-human,
    held, VEX, bundled binary, failed bump), tests and skipped tests, plus `deps.patch` and `bump-plan.json`.

## Recipes

Minimal example (see `recipes/*.yaml` for real ones; `schema/recipe.schema.json` documents every field):

```yaml
name: dex
source:
  repo: dexidp/dex
  lines:
    - name: v2
      tagPattern: '^v2\.\d+\.\d+$'     # track the newest v2.x.y; add one line per version you run
toolchain: { go: "1.27" }
ecosystems:
  - { type: gomod, dirs: [".", "api/v2"] }
  - { type: dockerfile, files: [Dockerfile] }
overrides:          # "if a lower version is found, force at least this" (even without a CVE)
  gomod:
    - { name: golang.org/x/net, min: v0.45.0, reason: org baseline }
holds:              # never bump (or never past `max`)
  gomod:
    - { name: k8s.io/kube-openapi, reason: upstream pin }
tests:
  framework: go
  command: go test -race {{skip_args}} ./...
build:
  images:
    - { name: dex, upstream: ghcr.io/dexidp/dex, args: { VERSION: "{{tag}}" }, smoke: ["dex version"] }
```

- **Policy**: `policy.default` (and `policy.ecosystems.<eco>`) caps how far a dependency may
  move without a person. Fixes beyond the cap show up in the PR as `needs-human`. The global
  default is `minor`; `go-toolchain` caps Go stdlib fixes.
- **Overrides / holds** in `_global.yaml` apply to every recipe; a recipe entry with the same
  `name` wins. `name` accepts `*` globs.
- **Prepare / scan scope**: `prepare` runs after checkout, before the first scan (Strimzi builds
  once so Trivy can resolve POMs from `~/.m2` with `scan.offline: true`, because Maven Central
  rate-limits per-POM lookups). `scan.skipDirs` excludes unshipped trees (test fixtures, release
  tooling), and `scan.source: false` skips the source scan for Dockerfile-only projects.
- **Images**: `build.images[]` lists every image a recipe ships. Variants of one repository
  get an `id` (e.g. Dex's distroless). `ownBinaries` lists the binaries built from this source, so
  findings in anything else are reported as bundled artifacts. Image-only recipes can give each
  image its own `tagPattern` and `platforms`.
- **Templates** in commands and build args: `{{tag}}`, `{{version}}` (no `v`), `{{commit}}`,
  `{{short_commit}}`, `{{image}}`, `{{platform}}`, `{{arch}}`, `{{skip_args}}`,
  `{{skip_regex}}`, `{{skip_file}}`. Unknown names are errors.

## Skipping upstream tests

`skips/<project>.yaml`:

```yaml
skips:
  - match: '^TestIndex$'           # framework-native selector
    reason: hits a live external service
    owner: platform-team
    expires: 2027-04-30            # warns after expiry; fails the run skipGraceDays later
quarantine: []                     # run them, report failures, don't fail (needs JUnit output)
```

How `match` is applied for each framework:

| Framework | How `match` is applied |
|---|---|
| go | joined into `go test -skip` (`{{skip_args}}`) or an env var via `skipVia` |
| nextest | `-E 'not (test(/match/) \| …)'`; or a raw `filter:` filterset |
| surefire | written to `-Dsurefire.excludesFile` |
| redis | written to `runtest --skipfile` |
| jest | `--testPathIgnorePatterns` |
| bats | not supported: bats can only select tests, so a non-empty list is refused |

If the skip file has entries but the recipe's command never uses the skip placeholders, the run
fails instead of silently ignoring the skips.

Test environment:
- Upstream builds and tests never see the pipeline's own `TRIVY_*`, `PATCHER_*` or `COPA_*`
  variables. Trivy's own suite reads `TRIVY_*`.
- `tests.runAs: nonroot` runs the test command as an unprivileged user (setup still runs as root).
  Use it when a suite asserts permission errors, which root bypasses. Argo CD needs this.

## Running locally

```bash
# CLI only (needs git, docker, trivy, and the toolchains the recipe needs on PATH)
cd patcher && uv sync && cd ..
patcher/.venv/bin/patcher validate
patcher/.venv/bin/patcher run dex --skip-build       # out/dex/v2/generated/report.md

# Exactly like CI: inside the patcher image
docker build -t patcher:dev patcher
docker run --rm --network host -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$PWD:$PWD" -w "$PWD" \
  patcher:dev run dex --out out --workdir "$PWD/.work"
```

Mount the repo and workdir at the **same path** inside the container: builds, docker compose
services and Testcontainers talk to the host's Docker daemon, which resolves bind-mount paths on
the host.

Use `--network host`: services from `tests.services` and containers that tests start (Testcontainers)
publish ports on localhost. The image sets `TESTCONTAINERS_HOST_OVERRIDE=localhost` for that.

On macOS (Docker Desktop), bind-mounted host folders don't enforce Linux permission bits, so
upstream tests that assert "permission denied" fail there (Argo CD has a few). Put `--workdir` on
a Docker named volume, or run on Linux; CI runners are fine.

Other commands: `plan` (CI matrix), `collect` (copy `out/` into `generated/`),
`release-build` / `publish` (release flow), `rescan` / `refresh` (Copa fast path), `schema`.

## CI (GitHub Actions)

| Workflow | Trigger | What it does |
|---|---|---|
| `patch.yml` | nightly, dispatch, push to `recipes/` `skips/` `patches/` `vex/` `patcher/` | `plan` → per line `patch` (no secrets, no push) → `pr` opens/updates `patch/<recipe>/<line>`, as a draft when tests fail |
| `release.yml` | push to `generated/**` (merged PR) | per-arch builds on native runners → merge → Copa → cosign sign + CycloneDX SBOM + OpenVEX attestations → SLSA provenance → PR updating `state/` |
| `rescan.yml` | daily | re-scans published images and acts only on fixable findings that are new since the release (`state/` keeps the known ones): OS-only → Copa refresh to the next revision; language → dispatches `patch.yml` |
| `patcher-image.yml` | PRs, pushes to `patcher/`, weekly | unit tests, `validate`, schema/lock drift; publishes the signed multi-arch patcher image |

Setup:

1. Create a GitHub App with *Contents: read & write* and *Pull requests: read & write*, and
   install it on this repo. Set the variable `PATCHER_APP_ID` and the secret
   `PATCHER_APP_PRIVATE_KEY`. PRs opened with the default `GITHUB_TOKEN` wouldn't trigger PR checks.
2. Images go to `ghcr.io/<owner>/<image>`; `PATCHER_REGISTRY` is set from the repo owner. GHCR
   packages start private; change their visibility as needed.
3. Arm64 builds use `ubuntu-24.04-arm` runners.
4. Every action is pinned by commit SHA and every tool in `patcher/Dockerfile` by version + sha256.
   Trivy's release channels were compromised in March 2026 (GHSA-69fq-xp46-6x23), so keep it that way.

Tags: `<upstream tag>-patched.<revision>` is immutable. `<upstream tag>-patched` always points to
the newest revision. Revisions never reuse a tag that already exists in the registry.

## Adding a project

1. Write `recipes/<name>.yaml`. Start with `source`, `ecosystems`, `tests` and `build`; copy the
   closest existing recipe.
2. `patcher validate`, then `patcher run <name> --skip-build`, then a full run, locally or via
   `workflow_dispatch` of `patch.yml` with `recipe=<name>`.
3. Add skips with reasons for tests that need infrastructure we don't have.

## Known limits

- Language fixes need a bump the upstream code still compiles with. Fixes beyond the policy cap,
  or in modules frozen upstream (e.g. `github.com/docker/docker` v28 `+incompatible`), are listed
  as needs-human. Record decisions in `vex/`.
- Bundled third-party binaries (Argo CD's helm/kustomize/git-lfs, Dex's gomplate) are only as
  fresh as their pinned version or base image.
- Redis' vendored C dependencies are patched by moving to the newest Redis point release, not individually.
- Kafka's own jars inside Strimzi's Kafka images come from the Apache release tarball; those images
  aren't built by the `strimzi` recipe.
- The Apollo GraphOS Operator is closed source and its image has no package database, so it gets
  scanning and reporting only.
- A failing test run is retried once with patch-level bumps only, which doubles test time for that
  line (`--no-retry` turns it off). If both attempts fail with the same tests, suspect the
  environment or a pre-existing upstream failure before the bumps.

## Verification status (2026-10-27)

Run locally inside the patcher image (linux/arm64, Docker Desktop), against the upstream releases
current on that date. Nothing has run in GitHub Actions yet.

| Recipe | Verified | Result |
|---|---|---|
| dex v2.46.1 | full run + release flow | source 6 → 0 fixable; 1,210 upstream tests pass; both images build, smoke OK; `release-build` → `publish` → `rescan` against a local registry |
| argo-cd v3.5.6 | full run | source 49 → 4 (all need-human majors); 8,082 tests pass as non-root; image builds, smoke OK; every remaining image finding is in bundled helm/kustomize/git-lfs |
| trivy v0.76.1 | full run | unit tests pass; image 25 → 0 fixable |
| copacetic v0.15.0 | full run | source 22 → 1 (`docker/docker` v28, needs-human); tests pass; copa + frontend images built |
| strimzi-maven-builder 1.3.0 | full run | image 28 → 0 fixable |
| maven 3.10.0 | full run | 34/34 bats tests; both variants build |
| apollo-operator 1.6.0 | image-only run | report only: no OS layer for Copa |
| apollo-router v2.19.0 | patch stage only | 4 crates bumped; tests (compose services) and source build not run locally |
| strimzi 1.3.0 | patch stage only | source 63 → 0 fixable (2 dependencyManagement pins). Unit tests use Testcontainers and couldn't run under Docker Desktop's networking; the image build wasn't run |
| redis v8.10.3 | patch stage only | base images refreshed; `runtest` and image builds not run locally |
| external-secrets v2.14.0 | patch stage only | no fixable findings at this release; `make test` and build not run locally |

The Copa fast path (`rescan` → `refresh`) was also verified against a local registry.

