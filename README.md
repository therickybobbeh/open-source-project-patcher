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

## Documentation

| Doc | For |
|---|---|
| [docs/architecture.md](docs/architecture.md) | How it works: components, the end-to-end flow (diagram), trust boundaries, tags and revisions, how the pipeline itself stays current |
| [docs/recipes.md](docs/recipes.md) | Reference for every recipe field, skip handling per test framework, `_global.yaml`, worked examples |
| [docs/runbook.md](docs/runbook.md) | Setup, reviewing patch PRs, skips, VEX decisions, releases and verification, dependency hygiene, CLI reference |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Symptom → cause → fix for problems hit while bringing the pipeline up |

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
docs/                       architecture, recipe reference, runbook, troubleshooting
.github/                    workflows, the run-patcher composite action, dependabot.yml
```

## Quick start

```bash
# validate every recipe/skip/VEX/state file
cd patcher && uv sync && cd ..
patcher/.venv/bin/patcher validate

# run one project exactly like CI does: inside the patcher image (never pushes)
docker build -t patcher:dev patcher
docker run --rm --network host -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$PWD:$PWD" -w "$PWD" \
  patcher:dev run dex --out out --workdir "$PWD/.work"
# -> out/dex/v2/generated/report.md (the PR body), deps.patch, bump-plan.json
```

- **Same-path mounts:** mount the repo and workdir at the same path. Builds, compose services and
  Testcontainers go through the host's Docker daemon, which resolves bind mounts on the host.
- **Host networking:** use `--network host`, so services and test containers are reachable on localhost.
- **macOS:** put `--workdir` on a Docker named volume when a suite tests file permissions
  (see [troubleshooting](docs/troubleshooting.md)).

A minimal recipe (the full reference is in [docs/recipes.md](docs/recipes.md)):

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

## CI (GitHub Actions)

| Workflow | Trigger | What it does |
|---|---|---|
| `patch.yml` | nightly, dispatch, push to `recipes/` `skips/` `patches/` `vex/` `patcher/` | `plan` → per line `patch` (no secrets, no push) → `pr` opens/updates `patch/<recipe>/<line>`, as a draft when tests fail |
| `release.yml` | push to `generated/**` (merged PR) | per-arch builds on native runners → merge → Copa → cosign sign + SBOM + OpenVEX attestations → SLSA provenance → `state/` PR |
| `rescan.yml` | daily | re-scans published images; new OS-only findings → Copa refresh, new language findings → `patch.yml` |
| `patcher-image.yml` | PRs, pushes to `patcher/`, weekly | unit tests, `validate`, schema/lock drift; publishes the signed multi-arch patcher image |
| `tool-pins.yml` | Mondays 07:00 ET | updates the version+sha256 tool pins in `patcher/Dockerfile` (releases ≥ 14 days old) |
| Dependabot | daily 07:00 ET | GitHub Actions, the patcher's Python packages and image bases (14-day cooldown) |

Setup (GitHub App, code security settings, GHCR visibility) is in the [runbook](docs/runbook.md#one-time-setup).

## Known limits

- **Upstream must still compile:** language fixes need a bump the upstream code still compiles with.
  Fixes beyond the policy cap, or in modules frozen upstream (e.g. `github.com/docker/docker` v28
  `+incompatible`), are listed as needs-human. Record decisions in `vex/`.
- **Bundled binaries:** third-party binaries in an image (Argo CD's helm/kustomize/git-lfs, Dex's
  gomplate) are only as fresh as their pinned version or base image.
- **Redis:** its vendored C dependencies are patched by moving to the newest Redis point release,
  not individually.
- **Strimzi Kafka images:** Kafka's own jars come from the Apache release tarball; those images aren't
  built by the `strimzi` recipe.
- **Apollo GraphOS Operator:** closed source, and its image has no package database, so it gets
  scanning and reporting only.
- **Test retries:** a failing test run is retried once with patch-level bumps only, which doubles
  test time for that line (`--no-retry` turns it off).

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
