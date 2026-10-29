# Troubleshooting

Problems hit while bringing up the pipeline, written as symptom → cause → fix. Most of them are
already handled in code or recipes; this page explains what you'll see if they come back.

## Scanning

### `trivy fs` fails with `429 Too Many Requests` from `repo.maven.apache.org`
**Cause:** Trivy resolves every transitive POM of a Maven project one request at a time. Maven
Central rate-limits per IP and then blocks the IP (`Retry-After: 1800`).
**Fix:** for Maven recipes, build once before scanning and scan offline against the local cache.
CI caches `~/.m2` between runs.
```yaml
prepare: ["mvn -B -ntp -q -DskipTests install"]
scan: { offline: true }
```
If you're already blocked, wait out the `Retry-After` (30 minutes).

Without `scan.offline`, a 429 no longer fails the run: the scan waits 60 seconds, retries, and then
falls back to `--offline-scan`. The report then carries a note that transitive Maven dependencies may
be missing. Projects that are built with Gradle but also ship a `pom.xml` (spring-petclinic) should
skip it: `scan.skipFiles: [pom.xml]`.

### Trivy DB download fails: `failed to download vulnerability DB … unexpected EOF`
**Cause:** the pull of `trivy-db` / `trivy-java-db` from `mirror.gcr.io` (or its `ghcr.io` fallback)
broke off. Seen locally after a 27-minute stall.
**Handled:** each patcher process downloads both DBs once, before its first scan, retrying up to three
times (30 s, then 60 s apart). Every later scan runs with `--skip-db-update`, so a run's before and
after scans use the same advisories. If all three attempts fail, the run fails: re-run it. In CI the
DBs come from the `actions/cache` of `/opt/trivy-cache`.

### Findings from files that aren't shipped (test fixtures, release tooling, examples)
**Cause:** `trivy fs` scans the whole checkout.
**Fix:** `scan.skipDirs` in the recipe (Redis skips `release-automation/`, Strimzi skips the Kafka
third-party-libs projects). `testdata`, `node_modules` and `vendor` are skipped globally.

### Image scan fails: `no child with platform linux/amd64 in index`
**Cause:** the image doesn't exist for the platform Trivy defaulted to.
**Fix:** released images are scanned for their released platforms (`state/` records them). For an
upstream image published for one architecture only, set `platforms` on that image in the recipe
(Apollo's `bundle-loader` is amd64-only).

## Patching

### A Go bump "doesn't stick" or comes back next round; `go get` downgraded something
**Cause:** a batch `go get a@x b@y` fails when one target requires a higher version of another
(`x/net@v0.60.0` needs `x/text >= v0.42.0`, but the plan asked for `x/text@v0.41.0`). Applying them
one by one would then *downgrade*.
**Fix (built in):** the per-module fallback skips any module already selected at or above its target.
If the report says `still at X after N round(s)`, another dependency pins it lower; check
`go mod graph`.

### `go` directive raised in `go.mod` (e.g. `1.25.13` → `1.26.8`)
**Cause:** a bumped dependency requires a newer Go. Copacetic's Trivy-library bump did this.
**Expected:** the report lists it as "required by a bumped dependency", and the toolchain and Go
builder images follow automatically. Official `golang` images set `GOTOOLCHAIN=local`, so the build
would fail otherwise. To refuse it, `hold` the module that needs it.

### A 0.x npm/Cargo fix is listed as needs-human (e.g. `esbuild 0.18 → 0.25`)
**By design:** caret ranges treat 0.x minors as breaking, so these count as major bumps. Add an
`override` if you've decided to take it.

### pnpm/npm: duplicate or conflicting overrides; lockfile regeneration fails
- If upstream already pins the vulnerable version (`"dompurify": "3.4.13"`), the adapter moves that
  pin instead of adding a second override.
- For pnpm ≥ 11, overrides go in `pnpm-workspace.yaml`.
- If `pnpm install --lockfile-only` fails, make sure `toolchain.pnpm` matches the project's
  `packageManager`. The image build runs `--frozen-lockfile` with that exact version.

### `bumped to X in …, but the image still has Y`
**Cause:** the bump was written, but the image build resolved the dependency some other way. With
Gradle, Spring's dependency-management plugin used to win over the generated constraints. That is
fixed: the generated script now uses a resolution rule that runs after the plugin's. Other causes are
a Dockerfile that installs from a different file than the one bumped, or a build that downloads a
released artifact instead of compiling the checkout.
**Check:** `./gradlew dependencyInsight --dependency <name> --configuration runtimeClasspath` in the
checkout shows which rule picked the version (`mvn dependency:tree -Dverbose` for Maven).

### Maven pin "didn't take effect"
**Cause:** the finding is in a separate Maven project (its own reactor) that doesn't inherit the
root POM's `<dependencyManagement>`.
**Fix:** list that project's root in `maven.poms`; pins go into the deepest listed root containing the
finding. Or `skipDirs` it if it isn't part of the shipped image (Strimzi's
`kafka-thirdparty-libs`).

## Upstream tests

### Tests that expect "permission denied" fail (`An error is expected but got nil`)
**Cause:** the tests run as root, and root bypasses file permissions. Argo CD and helm have such tests
(helm's shows up as a push to `localhost:5000` being refused, because the unreadable chart was read).
**Fix:** `tests.runAs: nonroot`.

### Same tests still fail on a Mac
**Cause:** Docker Desktop bind mounts of macOS folders don't enforce Linux permission bits.
**Fix:** put the work dir on a Docker named volume (`-v patcher-work:/work-vol … --workdir
/work-vol`) or run on Linux. CI runners are fine.

### An upstream suite fails because of the pipeline's own settings
**Cause:** Trivy's `TestFlag_IsSet` failed because it saw our `TRIVY_CACHE_DIR`.
**Fix (built in):** upstream test, build, `prepare` and `regen` commands run without the
`TRIVY_*`, `PATCHER_*` and `COPA_*` variables. If a recipe really needs one of those, set it in
`tests.env`.

### Testcontainers: `Connection refused`, `Container startup failed`, `Docker host IP address is 172.17.0.1`
**Cause:** the patcher runs with `--network host`. Testcontainers detects that it is inside a
container and dials the bridge gateway instead of `localhost`, where the ports are published.
**Fix (built in):** the patcher image sets `TESTCONTAINERS_HOST_OVERRIDE=localhost`.
- **Docker Desktop (macOS):** containers started from inside the host-networked patcher container
  still aren't reachable there, so run these suites (Strimzi's `mockkube`) on Linux.
- **Ryuk:** don't disable it (`TESTCONTAINERS_RYUK_DISABLED`) in recipes. It's what removes test
  containers when a run is interrupted.

### Skips are ignored / the run fails with `skips/ has entries but tests.command uses none of …`
**Cause:** the recipe's test command doesn't consume the skips.
**Fix:** add `{{skip_args}}` (or `skipVia`) to the command. bats can't exclude tests at all; Trivy
(`mage`) and External Secrets (`make test`) take no extra flags, so skipping there means calling
`go test` directly in the recipe.

### The run fails because of an expired skip
Renew `expires` (with a fresh look at the reason) or remove the entry. Expired entries warn first,
then fail `skipGraceDays` (30) after expiry.

### Both attempts failed with the same tests
The retry uses patch-level bumps only. Identical failures point at the environment or a
pre-existing upstream failure, not the bumps. The baseline run (the same tests on the unpatched
source) makes this call automatically: see the report's *also fail on the unpatched source* list.

### Almost every test fails, on the unpatched source too
**Cause:** usually the environment, not the code. Seen so far:
- **An unpinned test dependency released after upstream's release.** pytest-asyncio 1.4.1 broke all
  857 JupyterHub 6.1.1 tests (`AssertionError` in `pytest_asyncio/plugin.py`).
- **A missing service or binary**, such as Consul and Vault for gomplate's integration tests, or
  the helper binary that docker-credential-gcr's end-to-end tests run.

**Fix:**
- Installs in the test setup already only see releases older than the release-age cutoff, through
  uv, pip ≥ 26 and npm. Install with one of those, not an old pip or `pip install --upgrade`. To pin
  the cutoff yourself, set `UV_EXCLUDE_NEWER` (or `PIP_UPLOADED_PRIOR_TO`, `npm_config_before`) in
  `tests.env`.
- Mirror upstream CI's setup: build the binary first, put it on `PATH`, and start services with
  `tests.services`. Or narrow the command to the unit tests and say why in a comment (see
  `recipes/gomplate.yaml` and `recipes/docker-credential-gcr.yaml`).

### `go test` fails with a vet error only after the bumps (`… format %q has arg … of wrong type`)
**Cause:** `go test` runs a subset of `go vet`. Stdlib fixes move the build to a newer Go, whose vet
can flag code that upstream's older Go accepted. That's a lint change, not a behavior change.
**Fix:** add `-vet=off` to that recipe's `go test`, with a comment (see `recipes/git-lfs.yaml`).
Otherwise the patch-level retry also drops the Go upgrade, and the stdlib CVEs stay.

### Tests fail with `git checkout master: pathspec 'master' did not match`
**Cause:** the suite creates repositories and assumes git's default branch. The patcher's throwaway
git config keeps git's default (`master`, as on CI runners), so this only appears if someone sets
`init.defaultBranch` in `recipe.env` or a `prepare` step.

### Tests fail only in the patched run, with network errors (`no such host`, `connection reset`)
**Cause:** tests that reach the internet (Argo Workflows' controller tests query Docker Hub) hit a
network blip. The baseline ran later and passed, so the run is `tests-failed` (a draft PR) even though
the bumps are innocent. Read the failure messages before suspecting the bumps.
**Fix:** keep upstream's own retry settings when you call the test runner directly, e.g.
`gotestsum --rerun-fails=2 --rerun-fails-run-root-test` (Argo Workflows' `TEST_RETRIES`), pytest's
`--reruns`, or jest's `retryTimes`. Quarantine tests that depend on a live service. Re-running the
patch job is safe.

### A Go test package dies with `panic: test timed out after 10m0s`
**Cause:** `go test`'s default 10-minute timeout per package. Testcontainers-backed suites (Postgres
and MySQL in Argo Workflows' `workflow/sync`) exceed it on a busy Docker host.
**Fix:** pass `-timeout 30m` in `tests.command`.

## Images and Copa

### Copa fails on a distroless image: `No config file found at /usr/share/perl5/Debconf/Config.pm … dpkg: error processing package ca-certificates`
**Cause:** Copa can't run package scripts that need debconf inside distroless Debian images.
**Fix:** the base-image refresh (dockerfile adapter) usually resolves those findings. Set
`copa: false` on that image to silence the attempt. The report shows `Copa failed: …` for whatever
remains.

### Copa library patching leaves Python or npm packages alone: `No Python update packages were specified to apply`
**Cause:** every fix is beyond the image's `copa.level`. For example, pip 25.0.1's fixes are 25.3
(minor) and 26.x (major), so `level: patch` has nothing to apply.
**Fix:** raise `level` on that image (`copa: {libraries: true, level: minor}`) if the vendor image
tolerates it, or accept the findings with VEX. The Copa column of the report shows Copa's own
`N total, N patched, N skipped`.

### `base-image tooling (pip ships with the base image)` in the report
`pip`, `setuptools` and `wheel` in a Python base image, and the global npm in a Node base image,
aren't the project's dependencies, so no recipe bump reaches them. A newer base image (the
dockerfile ecosystem refreshes digests every run), Copa library patching, or an upgrade line in the
Dockerfile (via `patches/`) fixes them.

### A component shows `error` or `not-found`
- **`version of /usr/bin/x unknown`:** the binary has no Go build info version. Set `version`,
  `versionFrom` (a file in the parent's checkout), or `versionCommand` (args that print it).
- **The component's own tests fail:** run it standalone to iterate quickly:
  `patcher run <component> --skip-build`. It uses the component recipe's own release line.
- **Not swapped in:** only `success`, `no-changes` and `tests-preexisting` components are used. The
  report says `component … not swapped in (<status>)` and the original binary stays.

### A multi-stage build needs a locally built base (`FROM strimzi/base:latest`)
**Cause:** docker-container buildx builders can't see images in the local store.
**Fix:** `build.env: { BUILDX_BUILDER: default }` (the docker driver), as the Strimzi recipe does.

## Releases

### A release failed after the builds (`push`, `publish`, signing, `attest` or the `state/` PR)
Dispatch `release.yml` for the line with `rebuild: false`: it builds nothing and finishes the newest revision whose
per-arch images are all in the registry, keeping an image whose final tag an earlier attempt pushed. Re-running the
failed jobs only helps with transient failures: a re-run uses the workflow files of the commit that started the run.
See the [runbook](runbook.md#a-release-failed-after-the-builds). Published tags are never overwritten.

### `release-push`: "holds a linux/amd64 image, expected linux/arm64", "expected exactly one image"
**Cause:** an archive from the build job isn't one image of the platform its path names (`images/<arch>/<image>.tar`).
The push job checks every archive before it pushes any, so nothing was pushed.
**Fix:** look at the build job of that platform. A custom build `command` must build `{{platform}}` and produce exactly
`builtImage`.

### `release-plan`: "no native runner for linux/…"
**Cause:** `build.platforms` lists a platform without a native GitHub-hosted runner. Release builds run natively,
one runner per platform: `linux/amd64` and `linux/arm64`.
**Fix:** remove the platform, or add its runner to `pipeline.RUNNERS` if there is one.

## Network

### A run fails on `Could not resolve host`, `unexpected EOF`, `connection reset`
**Cause:** a network blip while fetching something. On a laptop these come in bursts; on CI runners
they are rare but happen.
**Handled automatically:**

| Step | What happens |
|---|---|
| git `ls-remote` / `fetch` of the upstream | retried once after 30 s |
| Image builds (module, package and base-image downloads) | retried once after 30 s when the error is a network one (compile errors are not retried) |
| Trivy DB download | up to three tries, then pinned for the run |
| `trivy fs` and Maven Central 429 | wait, retry, then an offline scan with a note |

Upstream tests are not retried by the patcher: keep upstream's own retry flags (see above).
Anything else: re-run the job.

## Running locally (macOS)

### `trivy image`, `docker buildx imagetools` or pulls hang forever
**Cause:** `~/.docker/config.json` has `"credsStore": "desktop"`, and the credential helper waits on
Keychain in non-interactive shells.
**Fix:** use a scratch Docker config for those commands:
```bash
mkdir -p /tmp/dockercfg && echo '{}' > /tmp/dockercfg/config.json && ln -sfn ~/.docker/cli-plugins /tmp/dockercfg/cli-plugins
export DOCKER_CONFIG=/tmp/dockercfg DOCKER_HOST=unix://$HOME/.docker/run/docker.sock
```

### A throwaway registry on port 5000 won't start
macOS uses port 5000 for AirPlay Receiver. Use another port (`-p 5055:5000`).
