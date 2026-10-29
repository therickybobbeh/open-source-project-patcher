# Review and roadmap

A review of the pipeline as of 2026-10-28, after the Python, Gradle, components and security-depth
work. The objective it's measured against: **pull open-source projects in from their tagged
releases, keep them patched and tested with as little hand work as possible, and keep the system
easy to extend**. Items are ordered by priority within each section.

## Done in this review

| Change | Why |
|---|---|
| `ecosystems.py`: one table per ecosystem (Trivy types, lockfiles, toolchain needs, 0.x rule, CVE-driven or not) | Seven constants in seven modules each listed the ecosystems; two of them were the same list defined twice |
| `RELEASABLE_STATUSES` in `models.py` | The "may ship" status set was spelled out in four places |
| `copa.for_image()`: one entry point per recipe image | Five call sites repeated the option plumbing. One of them had already dropped `copa: false` (`refresh` patched images that opted out) |
| `upstream.reset_tree()`, `proc.first_error()` | Duplicated in the PR flow, components and report code |
| `scripts/patcher-docker.sh`, used by CI's `run-patcher` action and for local runs | The container setup (mounts, caches, work dir) existed in three diverging copies |
| Timeouts kill the whole process tree; timed-out containers are removed | A hung test produced no output, so the timeout never fired. A JupyterHub run sat for four hours |
| `build.timeoutMinutes` (default 60) for image builds, build setup and component overlays, with one retry | Builds had no timeout at all: a buildx client that stalled after a finished build held an Argo Workflows run for 80 minutes |
| Network retries for git, image builds, component builds and the Trivy DB | Laptop and CI networks blip. Every failure seen in validation was a fetch, not the work |

## Patterns to break out next

1. **Test-framework registry.** Adding a framework touches five places: the `Tests.framework`
   literal, three tables in `tests_runner.py` (failure pattern, skip rendering, failure-id
   normalization), `toolchain.FRAMEWORK_FIELDS`, and onboarding inference. Do it the way
   `ecosystems.py` does: a `frameworks.py` with one row per framework holding those four pieces,
   and the literal derived from it.
2. **Split `pipeline.py` (≈1,000 lines) by flow.**
   - `flows/patch.py`: attempts, baseline, image planning.
   - `flows/release.py`: release-build, publish, image-only publish.
   - `flows/rescan.py`: rescan, refresh.
   - `plan.py`: plan matrix, collect.

   Most of the duplication left is one stage, **"finish an image"**: build → components overlay →
   smoke → Copa → scan → OpenVEX. It exists separately in the PR flow, the image-only flow and both
   publish paths. Extract it once.
3. **Output layout as code.** The names under `out/<recipe>/<line>/` (scans, copa-*, overlay-*,
   `generated/`) and `generated/<recipe>/<tag>/` are a contract between the patch job, `collect`,
   the release and `rescan`. Today they are f-strings in many places. A small `Layout` class makes
   the contract explicit and testable.
4. **Recipe presets** (less YAML, fewer mistakes):
   - `artifact.go: {dir, package, versionVar}` for Go-binary components. All six component recipes
     repeat the same cross-compiling `go build -trimpath -ldflags …` line.
   - One pinned gotestsum version. The recipes use both v1.12.3 and v1.13.0.
5. **One place for runtime tool pins.** `tool-pins.yml` manages the Dockerfile ARGs, but these are
   pinned in code or YAML and don't get its 14-day rule or its update PRs:
   - gotestsum (recipes);
   - govulncheck (`reach.py`);
   - poetry, pipenv and pip-tools (`adapters/python.py`).

   Move them to a `tools.yaml` that both read.
6. **Generate what is derived from recipes.** The README project table and the component list
   are hand-written copies of recipe data. A `patcher catalog` command, plus a CI drift check like
   the one for `schema/`, keeps them true.

## Architecture gaps

### Security

1. **Release builds hold registry credentials while running upstream code.**
   - **What happens:** the release `build` job logs in to GHCR (`packages: write`) and then runs
     `release-build`, which runs `build.setup` and custom build `command`s (upstream Makefile
     targets) in a container with `~/.docker` mounted. Compromised upstream build code could read
     the token and push images under our names.
   - **Fix:** build without credentials and export OCI archives (`--output type=oci`) as workflow
     artifacts. A separate job that runs no upstream code loads, pushes, Copa-patches and signs
     them. Components' overlays move with the build.
2. **Upstream authenticity.**
   - **Today:** tags are pinned to the commit `ls-remote` reports and re-checked after checkout.
   - **Not verified:**
     - signed tags or commits (GPG, gitsign);
     - upstream image signatures (cosign), where publishers sign;
     - checksums of downloaded release assets (Redis's tarball sha256 is computed at bump time,
       i.e. trust on first use).
   - **Fix:** add an optional `source.verify`, and prefer upstream-published `SHA256SUMS` where they
     exist.
3. **License changes in bumps.** A bump can move a dependency to a non-OSS license. Scan changed
   packages with Trivy's license scanner and report license changes against an allow and review
   list.

### Lifecycle of what we pull in

4. **Release lines.** The newest tag of a tracked line is followed automatically. Missing:
   - a signal when upstream starts a line we don't track (v3.6 appears);
   - a signal when a tracked line stops getting releases (EOL);
   - a nudge to move inventory images forward. `patcher coverage` already says "newer release
     patched".

   Add these to `coverage` and to the nightly summary.
5. **Hand-written patches.**
   - **Today:** files in `patches/` have no reason, owner or expiry. When upstream tags a new
     release, a patch may conflict, or may already be merged upstream.
   - **Fix:** add `patches/<recipe>/patches.yaml` with reason, upstream PR or issue, owner and
     expiry. On checkout, check each patch with `git apply --check` and `--reverse --check`, and
     report "conflicts" or "already upstream: delete".
6. **Upstreaming.** Every bump we carry is downstream divergence.
   - **Signal first:** report whether upstream's default branch already has the fix, meaning the
     next release makes our bump obsolete.
   - **Later:** `patcher upstream-pr` opens the same tested bump against upstream from a bot fork.
7. **Downstream consumption.** We publish patched images, but clusters keep referencing upstream
   ones until someone edits each chart. `inventory.yaml` and `coverage` already know the mapping.
   Two ways to close the loop:
   - publish it as JSON for a Renovate custom datasource that opens PRs in GitOps repos;
   - ship a Kyverno or Gatekeeper mutation policy that rewrites upstream image references to the
     patched digest at admission.

### Quality and operations

8. **Exceptions governance.** Skips, quarantine entries and VEX statements have owners and expiry;
   holds, overrides and patches don't. Add `expires` everywhere, and a `patcher exceptions` report
   listing every exception with its owner, age and expiry.
9. **Flaky tests.** Failures that pass on rerun, or fail only in the patched run with network
   errors, are signals. Keep per-run JUnit results as artifacts or in `state/`, compute flake
   rates, and suggest quarantine entries.
10. **A self-test for the pipeline.**
    - **Today:** end-to-end validation is done by hand.
    - **Fix:** add a weekly and on-demand workflow, triggered by changes under `patcher/`. It runs a
      few small, fast recipes through `scripts/patcher-docker.sh`: dex with `--skip-tests`, the
      Python and Gradle examples in `docs/examples/`, and the image-only Copa example. That catches
      adapter and flow regressions before the nightly run does.
11. **Metrics.** Two numbers show whether the program works and find stuck lines:
    - time from "fix available" to "patched image released";
    - fixable findings per image over time, from `state/` and `rescan`.

    Both feed a dashboard.
12. **Reproducible builds.** Set `SOURCE_DATE_EPOCH` and use BuildKit's `rewrite-timestamp`, so
    rebuilding the same patch set gives identical digests.
13. **Cost.** Test durations per recipe vary from about 1 minute (spring-petclinic) to about 25
    (Argo Workflows). Record them in `summary.json`. Heavy suites may need larger or self-hosted
    runners.

## Suggested order

1. Isolate release credentials (gap 1): a small workflow change with the largest risk reduction.
2. The pipeline self-test workflow (gap 10): it protects every later change.
3. Release-line and patch lifecycle (gaps 4 and 5).
4. The downstream mapping (gap 7).
5. The framework registry and the `pipeline.py` split (patterns 1 and 2), done before the next
   ecosystem or framework is added.
