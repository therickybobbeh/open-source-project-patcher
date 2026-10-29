# Architecture

support-images rebuilds the upstream open-source images we run from source, with vulnerable
dependencies bumped. It verifies each rebuild with the upstream project's own tests and publishes
signed, patched images. This page explains how the pieces fit together. For field-level
configuration see [recipes.md](recipes.md); for day-to-day operation see [runbook.md](runbook.md).

## Why rebuild from source

Copacetic (Copa) patches OS packages inside an existing image. Most findings in these images are
elsewhere:
- in **language dependencies** (Go modules, Rust crates, Maven and Gradle jars, npm and Python packages),
- in the **Go standard library** compiled into binaries,
- in **third-party binaries the image bundles** (helm, kustomize, git-lfs, gomplate, credential helpers).

Only a rebuild fixes those. The pipeline does the rebuild, and keeps Copa for the OS packages that
remain. What can't be rebuilt gets what is possible:

| Image | What the pipeline does |
|---|---|
| Open source, buildable | Rebuild with bumped dependencies, upstream tests, then Copa |
| Bundles open-source binaries it doesn't build | Each binary is a **component**: rebuilt from its own source at the same version, tested, and swapped into the image |
| Closed source (`mode: image-only`) | Components for any open-source helpers it ships; Copa for OS packages, optionally Python and npm packages too (`copa: {libraries: true}`); VEX and vendor-release tracking for the rest |

## Components

| Component | Where | Role |
|---|---|---|
| Recipes | `recipes/<project>.yaml`, `recipes/_global.yaml` | What to patch, test and build for each upstream project, plus org-wide policy, overrides and holds |
| Skips / VEX / patches | `skips/`, `vex/`, `patches/<project>/` | Human decisions: tests to skip, findings accepted with a reason, hand-written patches and extra files |
| `patcher` CLI | `patcher/src/patcher/` | All of the logic (below). Every workflow job is a thin wrapper around one CLI command |
| Patcher image | `patcher/Dockerfile` | The CLI plus every tool it shells out to (trivy, copa, mise, cosign, yq, docker CLI, buildx, compose, compilers). All pinned |
| Generated patch sets | `generated/<project>/<tag>/` | Written by CI and reviewed through PRs: `deps.patch`, `bump-plan.json`, `report.md` |
| Release state | `state/<project>.yaml` | What was published: tag, revision, platforms, digests, and the fixable findings known at release time |
| Workflows | `.github/workflows/` | `patch`, `release`, `rescan`, `patcher-image`, `tool-pins`, plus Dependabot (`.github/dependabot.yml`) |

### Inside the CLI

| Module | Responsibility |
|---|---|
| `models.py`, `config.py` | Recipe, skip, VEX and state models (these generate `schema/`); loading and merging `_global.yaml` |
| `upstream.py` | Resolving release lines (tags or branch heads) and shallow checkout. Applies patches, commits locally, re-tags, and produces the diff |
| `scan.py`, `planner.py`, `versions.py` | Trivy wrappers. The planner picks the smallest fixed version within policy, then applies overrides and holds. Version ordering for semver, Maven and Go |
| `ecosystems.py` | One row per ecosystem: Trivy types, lockfiles, toolchain needs, version-level rules. The other modules derive their per-ecosystem tables from it |
| `adapters/` | One adapter per ecosystem: `gomod`, `cargo`, `maven`, `gradle`, `node` (npm/pnpm/yarn), `python` (uv/poetry/pipenv/pip-tools/pinned), `dockerfile`, `files` |
| `toolchain.py`, `detect.py` | mise-installed toolchains for each recipe (or the upstream repo's own mise pins); versions the checkout declares fill unset fields |
| `tests_runner.py` | Runs the upstream tests, translates skips per framework, handles quarantine via JUnit, optionally runs as non-root, extracts comparable failing-test ids |
| `releases.py` | Publish times per registry, the release-age gate, the CISA KEV list, and the install cutoff for test environments |
| `reach.py` | govulncheck reachability (draft VEX) and the osv-scanner malicious-package check |
| `components.py` | Bundled binaries: find the version, patch and test it with its component recipe, overlay it into the image |
| `onboarding.py`, `inventory.py` | `patcher init` drafts; `inventory.yaml` coverage |
| `build.py`, `copa.py`, `registry.py` | buildx or custom builds, smoke tests, Copa per platform, anonymous registry lookups |
| `report.py`, `vex.py` | Before/after report (the PR body), and OpenVEX documents for each image |
| `pipeline.py` | Stage orchestration for `run`, `release-build`, `publish`, `rescan`, `refresh`, `plan` and `collect` |
| `pins.py` | Updates the tool pins (version + sha256) in `patcher/Dockerfile` |

## End-to-end flow

```mermaid
flowchart TD
    cron["nightly / dispatch / push to recipes, skips, patches, vex"] --> plan["patch.yml: plan<br/>(new upstream tag? recipe changed?)"]
    plan --> patch["patch.yml: patch job, one per release line<br/>checkout, scan, bump, test, build, Copa, report<br/>NO secrets, NO push"]
    patch --> pr["patch.yml: pr job<br/>generated/{project}/{tag}/ to a PR in this repo<br/>(draft if tests failed)"]
    pr --> review{"human review"}
    review -->|merge| release["release.yml<br/>per-arch build on native runners, merge,<br/>Copa, cosign sign, SBOM + OpenVEX attest,<br/>SLSA provenance"]
    release --> state["PR updating state/{project}.yaml"]
    state --> rescan["rescan.yml, daily<br/>scan published images"]
    rescan -->|new OS-only findings| refresh["Copa refresh to the next revision<br/>(no rebuild)"]
    rescan -->|new language findings| plan
```

### Stages of `patcher run` (the patch job)

1. **Resolve** the release line to an upstream tag (or branch head) and commit.
2. **Scan the upstream image** to get the "before" picture.
3. **Check out** the source, apply `patches/<project>/*.patch`, copy `patches/<project>/files/`.
4. **Install toolchains** with mise, then run the recipe's `prepare` commands.
5. **Scan the source** with `trivy fs`, plan the bumps, apply them, and scan again (up to `maxRounds`).
   A fix is only planned when its release is at least `minReleaseAgeDays` old, unless the finding is
   CRITICAL or on CISA's KEV list.
6. **Refresh base images** and edit pinned versions in files. The Go builder images are raised to the
   Go version the plan requires.
7. **Regenerate** code if the recipe says so, then **commit locally**. The upstream tag is moved to
   that commit, so version stamping still reports the upstream version.
8. **Check the bumped versions** against OSV's malicious-package advisories (osv-scanner). A hit stops
   the run here, before any upstream code runs with the new packages.
9. **Run the upstream tests** with skips applied. Installs the test setup does from version ranges
   only see releases older than the release-age rule (`UV_EXCLUDE_NEWER`, `PIP_UPLOADED_PRIOR_TO`,
   npm `before`), or the upstream release time if that is later. If tests fail:
   - the same tests run on the unpatched source (the **baseline**). If every failure is also there,
     the run is `tests-preexisting`;
   - otherwise, if any bump was above patch level, the run retries once with patch-level bumps only.
10. **Build** each image for the native platform.
11. **Components:** the built image is scanned, each bundled binary's version is found, its component
    recipe is patched and tested at that version, and the binaries are swapped in with an overlay
    build. The binaries are cross-compiled per platform in buildx stages.
12. **Smoke** commands, then **Copa** for fixable OS packages (and libraries if enabled), then the
    "after" scan.
13. **Plan from the image** (`scan.image`, default for Gradle and Python): fixable findings in the
    image's own jars, Python packages or node_modules that the source scan couldn't see become bumps
    in the matching ecosystem. One more attempt runs; if its tests fail, the first pass is kept.
14. **Reachability** (Go): govulncheck drafts VEX suggestions for what remains.
15. **Write** `report.md`, `deps.patch`, `bump-plan.json`, `summary.json`, `vex-suggestions.yaml`,
    OpenVEX, and each component's own outputs under `components/`.

`deps.patch` is the full diff from the upstream commit. It includes the hand-written patches and
files, so the release flow rebuilds exactly what was reviewed: it re-applies `deps.patch` to the
verified upstream commit and nothing else. Components work the same way: their reviewed
`components/<name>/deps.patch` is applied to their own verified commit and overlaid.

### Why the baseline and the cutoffs

Upstream suites fail for reasons that have nothing to do with our bumps. Seen in this repo:
- tests that need the internet, a cloud account, or a binary we don't install;
- a test dependency that upstream doesn't pin, released days ago and incompatible. For example,
  pytest-asyncio 1.4.1 broke all 857 JupyterHub tests three days after JupyterHub 6.1.1 shipped.

The baseline separates "broken upstream" from "broken by us" without anyone reading logs. The install
cutoff keeps test environments close to what upstream's CI saw when it released. It also keeps a
freshly published, possibly malicious package out of the test run.

## Trust boundaries

| Job | Runs upstream code? | Credentials |
|---|---|---|
| `patch.yml` / patch | yes (builds and tests) | none: `contents: read`, no secrets, nothing pushed |
| `patch.yml` / pr | no | GitHub App token (to open PRs that trigger checks) |
| `release.yml` / build | yes (re-runs the reviewed build) | `packages: write` (GHCR push) |
| `release.yml` / publish, attest | no | `packages: write`, `id-token: write` (keyless cosign), `attestations: write` |
| `rescan.yml` | no | `packages: read`; refresh adds `packages: write` + `id-token: write` |
| `tool-pins.yml` | no | GitHub App token |

Supply-chain rules for the pipeline itself:
- Every GitHub Action is pinned to a commit SHA.
- Every tool download in the patcher image is pinned to a version and its sha256.
- New releases of anything the pipeline uses are only adopted once they are **14 days old**:
  Dependabot's `cooldown` and `patcher pins --min-age-days`. Trivy's release channels were
  compromised in March 2026 (GHSA-69fq-xp46-6x23); a waiting period gives such incidents time to surface.

The same idea protects the images we build: bumps must be **7 days old** (CRITICAL and KEV fixes
excepted), bumped versions are checked against malicious-package advisories, and test installs are
held to the same cutoff.

## Tags and revisions

| Tag | Meaning |
|---|---|
| `<upstream tag>-patched.<revision>` | Immutable release, e.g. `v2.46.1-patched.3`, `v2.46.1-distroless-patched.3` |
| `<upstream tag>-patched` | Moving tag that always points to the newest revision |
| `<final>-<arch>`, `<final>-build` | Staging tags used while releasing; safe to garbage-collect |

How revisions are chosen:
- **First release** of a new upstream tag is revision 1.
- **Release flow:**
  - `release-build` takes the next revision whose final tag doesn't exist in the registry yet. A
    `state/` PR that hasn't been merged can never cause a tag to be overwritten.
  - `publish` merges the highest revision whose per-arch builds all exist. A retried publish therefore
    finishes its own revision.
- **Copa refresh:** each refresh publishes the next revision of the same upstream tag.

## Rescan and `knownFixable`

At release time, each image's fixable findings are stored in `state/` as `knownFixable`. These are
already explained in the release PR (for example, CVEs inside a bundled helm binary). `rescan` acts
only on fixable findings that are **new** and not covered by a VEX statement:
- **new OS-package findings only:** `refresh`, a Copa re-patch that publishes the next revision;
- **any new language finding:** dispatch `patch.yml` for that line, so it is rebuilt from source.

## Keeping the pipeline itself current

| What | How | Schedule |
|---|---|---|
| GitHub Actions (workflows + composite action) | Dependabot `github-actions` | daily 07:00 America/New_York, 14-day cooldown |
| Patcher Python dependencies (`patcher/uv.lock`) | Dependabot `uv` | same |
| Patcher image bases (`python`, `uv` stages) | Dependabot `docker` | same |
| Tool downloads in `patcher/Dockerfile` (mise, trivy, copa, cosign, osv-scanner, yq) | `tool-pins.yml` → `patcher pins --write` | weekly, Monday 07:00 ET |

The upstream projects themselves are **not** handled by Dependabot. Their dependencies are bumped
by the patch flow above. Dependabot only acts on repositories you host, and the Dependabot CLI's job
format is undocumented. Each ecosystem's own tooling gives the pipeline control over minimum fixed
versions and policy caps.
