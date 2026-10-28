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

### Maven pin "didn't take effect"
**Cause:** the finding is in a separate Maven project (its own reactor) that doesn't inherit the
root POM's `<dependencyManagement>`.
**Fix:** list that project's root in `maven.poms`; pins go into the deepest listed root containing the
finding. Or `skipDirs` it if it isn't part of the shipped image (Strimzi's
`kafka-thirdparty-libs`).

## Upstream tests

### Tests that expect "permission denied" fail (`An error is expected but got nil`)
**Cause:** the tests run as root, and root bypasses file permissions. Argo CD has several such tests.
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
pre-existing upstream failure, not the bumps. Run the same tests on the unpatched tag to confirm.

## Images and Copa

### Copa fails on a distroless image: `No config file found at /usr/share/perl5/Debconf/Config.pm … dpkg: error processing package ca-certificates`
**Cause:** Copa can't run package scripts that need debconf inside distroless Debian images.
**Fix:** the base-image refresh (dockerfile adapter) usually resolves those findings. Set
`copa: false` on that image to silence the attempt. The report shows `Copa failed: …` for whatever
remains.

### A multi-stage build needs a locally built base (`FROM strimzi/base:latest`)
**Cause:** docker-container buildx builders can't see images in the local store.
**Fix:** `build.env: { BUILDX_BUILDER: default }` (the docker driver), as the Strimzi recipe does.

## Releases

### `publish` failed halfway
Re-run **only the publish job**: it finishes the same revision, the highest one whose per-arch builds
all exist. Re-running the whole workflow builds the next revision instead. Published tags are never
overwritten.

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
