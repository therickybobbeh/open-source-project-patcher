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
crates, Maven and Gradle jars, npm and Python packages and the Go standard library, which need a
rebuild from source. This repo does that rebuild, and uses Copa as the final OS-package step and as a
fast path for OS-only refreshes.

Beyond the rebuild:
- **Bundled binaries:** third-party binaries an image bundles (helm, kustomize, git-lfs, gomplate,
  credential helpers) are rebuilt from their own source as **components** and swapped in. This also
  works inside closed-source images.
- **Bundled Java distributions:** when an image unpacks a distribution whose jars no bump can reach
  (Maven's own `lib/`), each vulnerable jar is swapped for the fixed release from Maven Central,
  pinned by sha256 and smoke-tested (`bundledJars`).
- **Fresh releases:** bumps only use releases at least 7 days old (CRITICAL and CISA-KEV fixes go
  in at once). Bumped versions are checked against malicious-package advisories, and test setups
  only install releases older than the same cutoff.
- **Pre-existing failures:** failing upstream tests are re-run on the unpatched source, so failures
  that upstream already had don't block a PR.
- **Onboarding and coverage:** `patcher init` drafts a recipe for a new project, and
  `patcher coverage` shows which images in `inventory.yaml` are covered.

| Project | Recipe | Source | Ecosystems patched | Upstream tests |
|---|---|---|---|---|
| Argo CD | `argo-cd` | argoproj/argo-cd | gomod (+ gitops-engine, k8s replace group), pnpm, Dockerfile bases; components helm, kustomize, git-lfs | `make test-local` |
| Argo Workflows (`workflow-controller`, `argocli`, `argoexec`) | `argo-workflows` | argoproj/argo-workflows | gomod, yarn (classic) UI, Dockerfile bases | `make test` via gotestsum (Postgres/MySQL in Testcontainers) |
| Argo Rollouts (`argo-rollouts`, `kubectl-argo-rollouts`) | `argo-rollouts` | argoproj/argo-rollouts | gomod, pnpm UI, Dockerfile bases | unit tests via gotestsum |
| Dex | `dex` | dexidp/dex | gomod (+ api/v2), Dockerfile bases; component gomplate | `go test -race ./...` via gotestsum |
| External Secrets | `external-secrets` | external-secrets/external-secrets | gomod (root + providers/generators), Dockerfile bases | `make test` (envtest) |
| Trivy | `trivy` | aquasecurity/trivy | gomod, Dockerfile bases | `mage test:unit` |
| Copacetic | `copacetic` | project-copacetic/copacetic | gomod, Dockerfile bases (builds a copa CLI image + frontend) | `make test` (pkg) |
| Apollo Router | `apollo-router` | apollographql/router | cargo, Dockerfile bases | `cargo nextest` + compose services |
| Apollo GraphOS Operator | `apollo-operator` | closed source | image-only: components docker-credential-ecr-login and -gcr rebuilt and swapped in; scan, VEX | – (components run their own tests) |
| Redis | `redis` | redis/docker-library-redis | Redis point release, Dockerfile bases | Redis `./runtest` |
| Strimzi operator | `strimzi` | strimzi/strimzi-kafka-operator | maven, Dockerfile bases | `mvn -DskipITs install` |
| Strimzi maven-builder | `strimzi-maven-builder` | strimzi/strimzi-kafka-operator | Dockerfile base (UBI) + rebuild | smoke `mvn -v` |
| Maven (official image) | `maven` | carlossg/docker-maven (branch `main`) | Dockerfile bases (eclipse-temurin); Maven's own jars swapped from Maven Central (`bundledJars`) | upstream bats suite |
| OpenTelemetry Collector contrib | `otelcol-contrib` | open-telemetry/opentelemetry-collector-releases | gomod of the module ocb generates from the manifest (247 components), Dockerfile bases | none of its own (generated module); smoke `components`, `validate` |
| Splunk OpenTelemetry Collector | `splunk-otel-collector` | signalfx/splunk-otel-collector | gomod (root + the local modules in the binary) | `make test-all` |

Component recipes (`mode: component`, never released on their own): `helm`, `kustomize`, `git-lfs`,
`gomplate`, `docker-credential-ecr-login`, `docker-credential-gcr`.

| Language | Ecosystems | Test frameworks |
|---|---|---|
| Go | `gomod` (+ govulncheck reachability) | `go` (go test / gotestsum) |
| Java | `maven`, `gradle` (version catalogs, generated constraints, lockfiles) | `surefire`, `gradle` |
| JavaScript | `npm`, `pnpm`, `yarn` (classic and berry) | `jest`, `vitest`, `mocha` |
| Python | `python`: uv, poetry, pipenv, pip-tools, pinned requirements | `pytest` |
| Rust | `cargo` | `nextest` |
| Anything | `dockerfile` (base images), `files` (pinned versions) | `generic`, `bats`, `redis` |

## Documentation

| Doc | For |
|---|---|
| [docs/architecture.md](docs/architecture.md) | How it works: components, the end-to-end flow (diagram), trust boundaries, tags and revisions, how the pipeline itself stays current |
| [docs/onboarding.md](docs/onboarding.md) | Adding a project or vendor image: coverage check, `patcher init`, resolving the draft, a clean first run, merge and release, with a checklist |
| [docs/recipes.md](docs/recipes.md) | Reference for every recipe field, skip handling per test framework, `_global.yaml`, worked examples |
| [docs/runbook.md](docs/runbook.md) | Setup, reviewing patch PRs (statuses, malicious packages, VEX suggestions), skips, VEX decisions, releases, onboarding a project, coverage, dependency hygiene, CLI reference |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Symptom → cause → fix for problems hit while bringing the pipeline up |
| [docs/examples/](docs/examples/README.md) | Validated example recipes for Python (pip-compiled, pytest), Gradle and a vendor image with Copa library patching |
| [wiki/](wiki/Home.md) | Curated wiki navigation and generated patch history (`wiki/history.parquet`) |
| [docs/roadmap.md](docs/roadmap.md) | Review findings: patterns to break out next and architecture gaps, in priority order |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Local loop; how to add a project, component, ecosystem or test framework; rules that keep the pipeline trustworthy |

## Layout

```
recipes/_global.yaml        org-wide policy, overrides/holds, registry, tag format
recipes/<project>.yaml      one recipe per upstream project (or bundled component)
inventory.yaml              the images we actually run (`patcher coverage`)
skips/<project>.yaml        upstream tests to skip / quarantine (reason, owner, expiry)
vex/<project>.yaml          decisions for findings we can't fix (published as OpenVEX)
patches/<project>/*.patch   hand-written patches applied after checkout
patches/<project>/files/    files copied over the checkout (e.g. extra Dockerfiles)
generated/<project>/<tag>/  WRITTEN BY CI, reviewed via PR: deps.patch, bump-plan.json, report.md
state/<project>/<line>.yaml what was released per line (tag, revision, digests); written by the release flow
patcher/                    the Python CLI + the portable patcher image (patcher/Dockerfile)
scripts/patcher-docker.sh   runs the CLI in the patcher image (used by CI and locally)
schema/                     JSON schemas (`patcher schema`); recipes reference them for editor validation
docs/                       architecture, recipe reference, runbook, troubleshooting, examples/
.github/                    workflows, the run-patcher composite action, dependabot.yml
```

## Quick start

```bash
# validate every recipe/skip/VEX/state file
cd patcher && uv sync && cd ..
patcher/.venv/bin/patcher validate

# run one project exactly like CI does: inside the patcher image (never pushes)
docker build -t patcher:dev patcher
scripts/patcher-docker.sh run dex --out out
# -> out/dex/v2/generated/report.md (the PR body), deps.patch, bump-plan.json
```

`scripts/patcher-docker.sh` is the one place the container setup lives; CI's `run-patcher` action
calls it too. What it sets up:
- **Docker:** the host's Docker socket and host networking, so builds, compose services and
  Testcontainers work, and test containers are reachable on localhost.
- **Paths:** the repo is mounted at the same path, so bind mounts resolve identically on both sides.
- **Caches:** toolchain, module and Trivy DB caches persist in `~/.cache/support-images`.
- **Work dir:** upstream checkouts go to the `patcher-work` Docker volume. On macOS, bind mounts
  don't enforce file permissions, which some suites test.
- **macOS + Docker Desktop:** set `PATCHER_DOCKER_CONFIG` to a dir with a plain `config.json`; see
  the script header.

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
| `patch.yml` | nightly, dispatch, push to `recipes/` `skips/` `patches/` `vex/` (not `patcher/`: dispatch with `all` to re-run every line) | `plan` → per line `patch` (no secrets, no push) → `pr` opens/updates `patch/<recipe>/<line>`, as a draft when tests fail |
| `release.yml` | push to `generated/**` (merged PR); dispatch per line (`rebuild: false` finishes a release that failed after its builds) | one run per line: per-platform builds on native runners, without credentials (images leave as archives) → push per-arch tags → merge → Copa → cosign sign + SBOM + OpenVEX attestations → SLSA provenance → `state/` PR |
| `rescan.yml` | daily | re-scans published images; new OS-only findings → Copa refresh, new language findings → `patch.yml`; opens issues for upstream release lines no recipe tracks and for end-of-life runtimes |
| `wiki-history.yml` | patch/release/rescan completion, relevant pushes, dispatch | refreshes the versioned wiki history snapshot and commits `wiki/history.parquet` |
| `patcher-image.yml` | PRs, pushes to `patcher/`, weekly | unit tests, `validate`, schema/lock drift; publishes the signed multi-arch patcher image |
| `tool-pins.yml` | Mondays 07:00 ET | updates the version+sha256 tool pins in `patcher/Dockerfile` (releases ≥ 14 days old) |
| Dependabot | daily 07:00 ET | GitHub Actions, the patcher's Python packages and image bases (14-day cooldown) |

Setup (GitHub App, code security settings, GHCR visibility) is in the [runbook](docs/runbook.md#one-time-setup). Jobs run on GitHub-hosted runners unless the `PATCHER_RUNS_ON*` variables select your own ([self-hosted runners](docs/runbook.md#self-hosted-runners)).

## Known limits

- **Upstream must still compile:** language fixes need a bump the upstream code still compiles with.
  Fixes beyond the policy cap, or in modules frozen upstream (e.g. `github.com/docker/docker` v28
  `+incompatible`), are listed as needs-human. Record decisions in `vex/`.
- **Bundled binaries:** components are rebuilt at the version the image bundles, with that
  version's dependencies bumped. A fix that needs a newer release of the tool itself is reported,
  not applied (e.g. gomplate v5.2 → v5.3).
- **Closed source:** a vendor's own binaries can only be reported and tracked with VEX. Components
  cover any open-source helpers they ship, and Copa covers OS packages (and optionally Python and
  npm packages).
- **Redis:** its vendored C dependencies are patched by moving to the newest Redis point release,
  not individually.
- **Bundled jars:** a jar of a bundled distribution is swapped on its own, within `bundledJars.level`,
  and keeps its old file name. A fix beyond that level, or in a library shaded into another jar, is
  reported, not applied. Only the image's smoke tests exercise the distribution with the new jar
  (upstream tests never run against the overlaid image).
- **Strimzi Kafka images:** Kafka's own jars come from the Apache release tarball; those images aren't
  built by the `strimzi` recipe. A recipe for them would swap those jars with
  `bundledJars: {paths: [opt/kafka/libs/]}`.
- **Apollo GraphOS Operator:** closed source with no package database: the credential helpers are
  rebuilt, and the operator binary's own findings are reported.
- **Python without lockfiles:** loose requirements are only seen in the built image (`scan.image`).
  Bumps go into the requirements file the image installs from; if the Dockerfile installs from
  elsewhere, the finding stays in the report.
- **Test retries:** a failing test run is retried once with patch-level bumps only, which doubles
  test time for that line (`--no-retry` turns it off).

## Status

The pipeline runs in GitHub Actions: nightly patch runs, releases from merged patch PRs, and a daily rescan. Where to
look:
- **What is released now:** `state/<recipe>/<line>.yaml`, one file per line, with the tag, revision, platforms,
  digests and the fixable findings known at release. The images are under `ghcr.io/<owner>/`.
- **How each line got there:** the patch PRs (their reports) and release runs, and the patch history in the
  [wiki](wiki/Home.md).
- **What is broken now:** open issues labelled `ci-failure` ([failure alerts](docs/runbook.md#failure-alerts)), plus
  `end-of-life` and new-release-line issues from the daily checks.
- **Which images in use are covered:** `patcher coverage` against [inventory.yaml](inventory.yaml).

The local verification runs from before the pipeline ran in Actions (2026-10-27 to 10-29) are in
[docs/verification-log.md](docs/verification-log.md).
