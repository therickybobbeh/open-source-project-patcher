# Runbook

For the people who review patch PRs and operate the pipeline. Background is in
[architecture.md](architecture.md), configuration in [recipes.md](recipes.md), and known problems in
[troubleshooting.md](troubleshooting.md).

## One-time setup

1. **GitHub App** for opening PRs. PRs opened with the default `GITHUB_TOKEN` don't trigger checks.
   - Permissions: *Contents: read & write*, *Pull requests: read & write*.
   - Install it on this repository.
   - Add the variable `PATCHER_APP_ID` and the secret `PATCHER_APP_PRIVATE_KEY`.
   - **Until then:** the workflows fall back to `GITHUB_TOKEN` (with a warning in the run) if you
     turn on *Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create
     and approve pull requests*. The PRs open, but their checks don't run.
2. **Code security settings:** enable *Dependency graph*, *Dependabot alerts* and *Dependabot
   security updates*. Version updates are configured in `.github/dependabot.yml` (see
   [Dependency hygiene](#dependency-hygiene-of-this-repo)).
3. **Branch protection on `main`:** require the `test` job of `patcher-image.yml` (unit tests,
   `patcher validate`, schema and lock-file drift). It runs on every PR, so Dependabot, tool-pins,
   patch, state and docs PRs all report it. Bot PRs only run checks once the GitHub App (step 1) opens
   them.
4. **GHCR:** images are published to `ghcr.io/<owner>/<image>` and start **private**. Make them
   public, or give your clusters' pull secrets access.
5. **Release lines:** edit each recipe's `source.lines` to the versions you actually run.
6. **First run:** *Actions → patch → Run workflow*, `recipe=dex`. Check the job summary (the report
   is posted there), then the PR it opens.

## Self-hosted runners

Every job runs on GitHub-hosted runners by default: `ubuntu-24.04`, plus `ubuntu-24.04-arm` for arm64
builds. To use your own runners, set repository or organization **variables**. Each one holds the job's
`runs-on` value as JSON:

| Variable | Jobs | Example |
|---|---|---|
| `PATCHER_RUNS_ON` | every job not listed below | `{"group": "patcher"}` |
| `PATCHER_RUNS_ON_ARM64` | arm64 builds (release builds, the patcher image) | `{"group": "patcher", "labels": ["ARM64"]}` |
| `PATCHER_RUNS_ON_UPSTREAM` | jobs that run code we don't vet: patch runs (upstream builds and tests), release builds, PR tests | `{"group": "patcher-sandbox"}` |
| `PATCHER_RUNS_ON_UPSTREAM_ARM64` | arm64 release builds | `{"group": "patcher-sandbox", "labels": ["ARM64"]}` |

Any `runs-on` form works:
- a runner group: `{"group": "name"}`;
- a group with labels;
- a label list: `["self-hosted", "linux", "x64"]`;
- an Actions Runner Controller scale set: `"patcher-x64"`.

**Fallbacks:**
- `PATCHER_RUNS_ON` and `PATCHER_RUNS_ON_ARM64` fall back to GitHub-hosted runners.
- The `UPSTREAM` variables never fall back to the trusted pool. Upstream code must not land on the runners that
  hold registry, signing and GitHub App credentials.
- Unset, the `UPSTREAM` variables mean GitHub-hosted runners. Once `PATCHER_RUNS_ON` or `PATCHER_RUNS_ON_ARM64`
  is set, its `UPSTREAM` counterpart must be set too. Otherwise the run stops at its first job with an error
  naming the variable (`scripts/check-runner-pools.sh`).
- To keep upstream code on GitHub-hosted runners in a self-hosted setup, set the `UPSTREAM` variable to
  `"ubuntu-24.04"` (arm64: `"ubuntu-24.04-arm"`).
- With no arm64 runners, set `PATCHER_PLATFORMS` to `linux/amd64` ([Fewer platforms](#fewer-platforms)).

**Security.** Patch runs and release builds run upstream build and test code with the Docker socket,
which is root on the runner.
- **Use ephemeral runners** (one job per runner: ARC, or just-in-time runners). A runner that is reused
  lets a malicious build persist into the next job, including the jobs that hold registry credentials
  or the GitHub App's token.
- **Keep those jobs apart.** Point `PATCHER_RUNS_ON_UPSTREAM` at a separate group that can't reach
  internal systems. The check warns when it names the same runners as `PATCHER_RUNS_ON`.
- **On a public repository,** fork pull requests run the `test` job on the `UPSTREAM` runners. Require
  approval for outside contributors (*Settings → Actions → General*), or set the `UPSTREAM` variables to the
  GitHub-hosted labels.

**Runner requirements.** Linux, with:
- **Docker:** Docker Engine 25 or later, with the buildx plugin and the **containerd image store** enabled
  (`{"features": {"containerd-snapshotter": true}}` in `/etc/docker/daemon.json`). Copa needs it to patch
  locally built images, and patch runs check for it and stop with an error if it's missing.
- **Tools:** `bash`, `git`, `curl`, `jq`, `tar` and the GitHub CLI (`gh`).
- **QEMU binfmt handlers:** release `publish` jobs and Copa refreshes install them with
  `docker/setup-qemu-action`, which runs a privileged container.
- **Space:** room for upstream checkouts, module caches and images. GitHub's runners (4 CPUs, 16 GB, about
  70 GB of disk) are enough. The OpenTelemetry contrib build is the largest so far.
- **Network:** outbound access to GitHub, the registries (GHCR, Docker Hub, quay.io and others), the
  language package registries and Trivy's DB mirrors, or to your proxies (see the
  [roadmap's artifact-proxy notes](roadmap.md#later-running-behind-an-artifact-proxy-nexus-artifactory)).

Two steps of the patch job run on GitHub-hosted runners only, because on your own machine they would
delete the host's files and restart its Docker:
- the disk clean-up, which removes preinstalled SDKs;
- the switch to the containerd image store.

The checkout is handed back to the runner's user without `sudo`.

**A private registry for base-image lookups.** The patcher reads tags and digests of base images anonymously.
For one registry that needs credentials, set:
- `PATCHER_REGISTRY_BASIC_AUTH` to `user:token`;
- `PATCHER_REGISTRY_AUTH_HOST` to that registry's host, port included, e.g. `nexus.example.com:8443`.

The credentials go only to that registry, and only when its token service is https on the same host. They
don't follow redirects. Upstream Dockerfiles choose which registries get contacted, and any registry's auth
challenge can name any server. Without the host variable the credentials are sent nowhere, and a warning is
logged. This covers a self-hosted registry or proxy (Harbor, Nexus, Artifactory) that issues its own tokens.
Docker Hub's token service is on another host, so this variable doesn't cover Docker Hub.

## Fewer platforms

Each recipe is built and released for every platform in its `build.platforms`: by default `linux/amd64` and
`linux/arm64`. Where one is enough, for example a setup that runs only arm64, set the repository or organization
**variable** `PATCHER_PLATFORMS`:

| `PATCHER_PLATFORMS` | Built and released |
|---|---|
| unset (default) | each recipe's `build.platforms` |
| `linux/arm64`, or `arm64` | arm64 only |
| `linux/amd64`, or `amd64` | amd64 only |

What changes:
- **Releases** build, push, Copa and publish only those platforms. That's one build job instead of two, and
  `publish` runs Copa once instead of twice (the second platform runs emulated). The images and `state/` list only
  those platforms.
- **Patch runs** build and test on the first of them, on that platform's runner: `ubuntu-24.04-arm` for arm64, or
  `PATCHER_RUNS_ON_UPSTREAM_ARM64` on your own runners.
- **It only narrows:** a recipe never builds a platform its `build.platforms` doesn't list.
  - A recipe left with none of them, such as an amd64-only recipe with `linux/arm64`, is neither patched nor
    released. `release-plan` reports it as skipped.
  - An image that exists only for other platforms is left out of its recipe's builds and releases.
- **Images released earlier** keep their platforms until their line's next release, because a Copa refresh patches
  exactly what was released.
- **Only platforms with a release runner** (`linux/amd64`, `linux/arm64`) are accepted. Anything else fails the plan
  jobs, so a typo can't quietly skip every recipe.

Locally, `scripts/patcher-docker.sh` passes the variable into the container, e.g.
`PATCHER_PLATFORMS=arm64 scripts/patcher-docker.sh release-plan --recipe dex --line v2`. `patcher run` builds for the
machine it runs on unless `--platform` says otherwise.

## Reviewing a patch PR

Each PR is titled `[<recipe>] <tag>: dependency updates (<status>)`. The body is the generated
report; the same files are in `generated/<recipe>/<tag>/`. The PR is a **draft** when tests, the
build or a smoke test failed. It is also a draft when the [release gate](gate.md) is enforced and would stop
the release. The report's **Release gate** section shows the verdict either way.

| Status | Meaning |
|---|---|
| `success` | Bumps applied, tests passed, images built. Also a rebuild without bumps whose images have fewer fixable findings than upstream's (Copa, rebuilt components, a newer base); its report says so |
| `no-changes` | Nothing to release, so no PR. When every fixable finding in upstream's images is one the source plan left unresolved (for example a fix still in its release-age wait), the run stops after the scans, without tests or a build |
| `tests-preexisting` | Tests failed, but the same tests also fail on the unpatched upstream source. Ready for review; labeled `preexisting-test-failures` |
| `tests-failed` | Tests failed only after the bumps, even with patch-level bumps. Draft |
| `malicious-dependency` | A bumped version has an OSV malicious-package advisory. Draft; nothing is built. See [below](#malicious-package-check) |
| `build-failed` / `smoke-failed` | The image didn't build or didn't start. Draft |
| `scan-failed` | Image-only recipes: the vendor image couldn't be scanned (wrong tag or platform). Draft |

What to check, section by section:

1. **Fixable vulnerabilities:** counts before and after, for the source tree and each image.
   **New > 0 needs attention:** a bump pulled in something that's vulnerable.
2. **Changes applied:** every bump, with the CVEs it fixes. Bumps above the policy cap only appear
   when you added an override. **Bundled jars swapped** lists each jar replaced in an image: coordinates,
   from → to, CVEs and the sha256 pin. The jar keeps its old file name. Check that the image's smoke
   tests passed, and that they actually load those jars.
3. **Still fixable after patching:** every remaining finding with a reason:

   | Reason | What to do |
   |---|---|
   | `needs-human: … beyond the policy` | Choose one: raise `policy` for that ecosystem in the recipe; add an `override` with a reason; write a patch in `patches/<recipe>/` (e.g. a `Cargo.toml` change); or accept it with a VEX statement |
   | `held: …` | Intentional (see `holds`). Revisit the hold if the fix matters |
   | `in bundled artifact …` | The finding is in a binary this source doesn't build. If it's open source, add it as a [component](recipes.md#components) so it's rebuilt with patched dependencies (helm, kustomize, git-lfs, gomplate and the credential helpers already are). If it's a jar of a Java distribution the image unpacks (Maven, Kafka), add [`bundledJars`](recipes.md#bundled-jars) to the image. Otherwise bump its pin with a `patches/` patch or a `files` edit, or record a VEX decision |
   | `bundled jar: …` | A jar under `bundledJars.paths` wasn't swapped; the rest says why. A cooldown clears itself. For needs-human beyond `bundledJars.level`, raise `level` if the smoke tests cover the jar, or add a `maven` hold. A jar shaded into another one waits for a release of the distribution |
   | `cooldown: <ver> released N day(s) ago (eligible <date>)` | The fix is newer than the 7-day release-age rule allows. Nothing to do: a nightly run after `<date>` applies it. If it can't wait, add an `override` with a reason, or run with `--no-cooldown` |
   | `the Go toolchain used for the build is older than the fix` | No patched Go release of that line exists yet. The next run picks it up automatically |
   | `Copa failed: …` / `OS package not patched` | Check the image base. Copa can't patch some distroless images (see troubleshooting); a base-image bump may be needed |
   | `bump failed: …` | Read the error under *Bumps that could not be applied*. Usually conflicting requirements, so a code change or patch is needed |
   | `no fixed version` | Nothing to apply yet. Assess it, and record a VEX statement if appropriate |
   | `VEX …` | Already decided; shown for visibility |

4. **Upstream tests:** pass or fail, the command, the failing tests, and the skipped tests with their
   owners and expiry dates.
   - **Retries:** the *Attempts* line shows when a run retried with patch-level bumps only. If only
     the full attempt failed, a minor bump broke a test, and the PR contains the patch-level result.
     If both attempts fail with the **same** tests, suspect the environment or a pre-existing upstream
     failure before suspecting the bumps (see [troubleshooting.md](troubleshooting.md)).
   - **Pre-existing failures:** when the patched tests fail, they also run on the unpatched source.
     If every failing test fails there too, the report says so ("also fail on the unpatched source")
     and lists them, and the status is `tests-preexisting`. They are broken upstream, or in our
     environment, regardless of the bumps. Consider skipping them with a reason so the next PR is clean.
5. **Images:** smoke results and what Copa did.
6. **Components:** for each bundled binary, the version found in the image, how it was found, the
   component's status and tests, and whether it was swapped in. The component's own report and diff
   are under `components/<name>/`.
7. **VEX suggestions** (Go): drafts for remaining findings whose vulnerable code is never reached.
   See [below](#vex-suggestions-from-reachability).
8. **`deps.patch`:** skim it. Lockfile churn is expected; unexpected source changes are not.

**Merging releases the line.** `release.yml` refuses patch sets whose status isn't `success`,
`no-changes` or `tests-preexisting`, so a draft can't be released by accident. Afterwards, merge the
`state/` PR it opens: `rescan` depends on it.

### Malicious-package check

After the bumps, `osv-scanner` checks the changed lockfiles against OSV's malicious-package advisories
(`MAL-*`). A hit stops the run before any test or build executes the package, and the report names
the package, version and lockfile. Don't merge. Hold the package at a known-good version (`holds`,
`max:`), and report the advisory upstream if it isn't known there yet. The 7-day release-age rule
(see [recipes.md](recipes.md#policy)) is the first line of defense: most malicious releases are
pulled within days.

### VEX suggestions from reachability

For Go recipes, `govulncheck` runs on the patched source. For each remaining Go finding whose
vulnerable function is never called (or whose vulnerable package is never imported), the report
drafts a `not_affected` statement, also written to `vex-suggestions.yaml` next to the report. They
are **never applied automatically**. To accept one, check the reasoning (govulncheck only sees the
code paths in this build), then copy it into `vex/<recipe>.yaml` with an `expires` date.

### What's in `generated/`, and why it doesn't pile up

A patch PR adds `generated/<recipe>/<upstream tag>/`:
- `deps.patch`: the exact diff applied to upstream's source;
- `bump-plan.json`: the upstream commit, status and changes;
- `report.md`: the report, also the PR description.

The release rebuilds from exactly these files. There is **one patch set per release line**: the PR
for a newer upstream tag (say 1.3.1) deletes the line's previous folder (1.3.0) in the same commit,
and the release ignores the deletion. Old patch sets stay in git history, and the released images
carry their SBOM, VEX and provenance. Each line has one PR branch (`patch/<recipe>/<line>`) that's
updated in place.

### What runs when

| Trigger | What runs |
|---|---|
| Nightly (03:17 UTC) | Lines whose newest upstream tag isn't released yet, **minus** lines whose patch set for that tag is in a PR (open, or merged into `generated/`: a failed release is re-run with `release.yml`, not re-patched; see [A release failed after the builds](#a-release-failed-after-the-builds)) and lines another run is patching right now. A `no-changes` line comes back every night, so a new fix is picked up the next day; a line with nothing to change costs a clone and the scans |
| Push to `recipes/`, `skips/`, `patches/`, `vex/` | The lines of the recipes that changed (`_global.yaml`: all of them). A file whose only changes are comments, formatting, or a recipe's `description` or `notes` runs nothing; the next run picks the text up |
| Manual dispatch | The recipe (and line) you name, or every line with `all` |

Two runs never patch the same line at once: the second one waits.

### Failure alerts

`ci-alerts.yml` follows every run on `main` of patch, release, rescan, patcher-image, tool-pins
and wiki history. Each failed or timed-out job opens an issue labelled `ci-failure`, titled
`CI failure: <workflow> / <job>`. The issue names the failed step and links the job log. Another
failure of the same job adds a comment. The issue closes itself the next time that job passes, so the
open `ci-failure` issues are exactly what is broken now. Watch the label, or subscribe to it, to get
notified.

One broken recipe doesn't stop the others. Examples: a recipe file that doesn't parse, upstream tags that can't be
listed, a rescan that fails for one line. The nightly patch plan and the rescan report it, and the other recipes still
run. Then a small job fails for it, which opens the alert: `patch / plan-errors` or `rescan / scan-errors`. Its log
names the recipe and the error. That job runs every time, so the alert closes once every recipe plans and scans again.

## Skipping upstream tests

Skip a test only if it needs infrastructure the pipeline doesn't have (cloud credentials, a live
external service), or it is flaky for reasons unrelated to dependencies. Add the entry to
`skips/<recipe>.yaml`:

```yaml
skips:
  - match: '^TestIndex$'        # framework-native selector, see recipes.md
    reason: Downloads the live argo-helm index; fails on network flakes
    owner: platform-team
    expires: 2027-04-30
quarantine:                     # run, report failures, but don't fail the build (needs tests.junit)
  - match: '^TestFlakyThing$'
    reason: upstream issue #1234
    owner: platform-team
    expires: 2027-01-31
```

An expired entry produces a warning; `skipGraceDays` (30) after expiry, the run fails until someone
renews or removes it. Every skipped test is listed in the PR report.

## Recording VEX decisions

When a finding can't be fixed here (a module frozen upstream, a closed-source binary) and you've
assessed it, add a statement to `vex/<recipe>.yaml`:

```yaml
statements:
  - vulnerability: CVE-2026-33997
    status: affected                      # not_affected | affected | fixed | under_investigation
    action: waiting for upstream to migrate from github.com/docker/docker v28 to moby/moby/v2
    packages: [github.com/docker/docker]
    expires: 2027-01-31
  - vulnerability: CVE-YYYY-NNNNN         # placeholder
    status: not_affected
    justification: vulnerable_code_not_in_execute_path
    impact: the affected parser is only used by a subcommand the image never runs
```

Effects:
- The report shows the decision instead of an unexplained row.
- The statement is published as an OpenVEX attestation on the image.
- `rescan` ignores the finding.

Set `expires` so decisions get revisited.

## Releases

`release.yml` runs when a patch PR merges, one run per line:
1. **build**: rebuilds the reviewed patch set on a native runner for each of the recipe's platforms
   (`build.platforms`, default amd64 and arm64; an image's own `platforms` narrows it). This job runs upstream
   code, so it has no registry credentials: it saves the images as archives instead of pushing them.
2. **push**: pushes the archives as per-arch tags of a new revision, after checking each one.
3. **publish**: merges the platforms, runs Copa, and pushes the final tags. Then it checks each image's final
   scan against the [release gate](gate.md). With `gate.enforce`, a denied image stops the release here, unsigned
   and unrecorded. Last, it signs with cosign (keyless), and attaches a CycloneDX SBOM and the OpenVEX document.
4. **attest**: SLSA provenance for each image.
5. **promote**: moves the moving tag (`<tag>-patched`) to the signed digest. If anything before failed, it stays on
   the previous revision.
6. **state**: opens the `state/` PR. It comes last, so `state/` only records complete releases.

Why the jobs are split this way is in [architecture.md](architecture.md#release-flow). A push that lands several
patch sets starts one run per line. A line that can't be released (an unknown recipe or line, a platform without a
native runner) fails its run, which raises a [failure alert](#failure-alerts); the push's other lines still go out.

### A release failed after the builds

When `push`, `publish`, the signing, `attest`, `promote` or `state` failed, the images are built already. Finish the release
without building again:

```bash
gh workflow run release.yml -f recipe=<recipe> -f line=<line> -f rebuild=false
```

(or *Actions → release → Run workflow*, with *rebuild* unticked). It skips `build` and `push`. `publish` takes the
highest revision after the one `state/` records whose per-arch images (`<final>-<arch>`, every image, every platform)
are all in the registry, and carries on from there:
- **Its final tag doesn't exist yet:** it is merged and Copa-patched as usual.
- **Its final tag exists** (the earlier `publish` pushed it, then failed): the image is kept as it is, with no second
  merge or Copa, so its digest doesn't change. It is scanned, and the OpenVEX document is written from that scan
  (without Copa's own statements, which the earlier run had). A signature, SBOM, OpenVEX
  or provenance attestation is only added if this workflow hasn't attached one yet.
- `attest`, `promote` and `state` run as usual: the moving tag moves, and the `state/` PR records the revision.

Notes:
- A revision that `state/` records is never published again. With nothing left to finish, the run fails with
  "no revision ... has all its per-arch images": dispatch with `rebuild: true` instead.
- Use `rebuild: false` for the patch set that failed. If the line's `generated/` patch set changed since (a new PR
  merged), release with `rebuild: true`.
- If `build` itself failed, or `push` failed before pushing every per-arch image, there is nothing complete to
  finish: dispatch with `rebuild: true`. A new build always takes a new revision, so the numbers can skip.
- Image-only recipes build nothing in `build`: their `publish` overlays the vendor image and always publishes a new
  revision, so `rebuild` makes no difference for them.
- `publish` failing with "… exists, but this run's push just took revision N: something else … published it since":
  a Copa refresh of the line published that revision while this run was building. Nothing was published by this
  run; dispatch the release again (`rebuild: true`), and it takes the next revision.
- The [failure alert](#failure-alerts) of a job closes itself when that job passes in the finishing run. A run with
  `rebuild: false` skips `build` and `push`, so close their alerts by hand.
- **Re-run failed jobs** (`gh run rerun --failed`) only for transient failures (a registry or Sigstore blip). A re-run
  of `publish` keeps the final tags its first attempt pushed (`--finish-existing`). A re-run uses the workflow and
  action files of the commit that started the run, so it repeats a failure that a later commit fixed. A new dispatch
  uses the current files.
- Revisions that a failed run published but `state/` never recorded (for example `-patched.1` and `-patched.2` of
  the releases of 2026-10-29) stay in the registry, signed, without provenance. Nothing uses them. To remove them,
  delete their package versions in GHCR after the line's `state/` records a later revision; numbers below that one
  are never used again.

### Verifying an image

```bash
IMG=ghcr.io/<owner>/dex:v2.46.1-patched.1

# signature, made by this repository's release workflow
cosign verify "$IMG" \
  --certificate-identity-regexp '^https://github.com/<owner>/<repo>/\.github/workflows/release\.yml@' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com

# SLSA build provenance
gh attestation verify "oci://$IMG" --owner <owner>

# our VEX decisions, applied to a fresh scan
cosign verify-attestation "$IMG" --type openvex \
  --certificate-identity-regexp '^https://github.com/<owner>/<repo>/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  | jq -r '.payload' | base64 -d | jq '.predicate' > vex.json
trivy image --vex vex.json "$IMG"
```

Copa refreshes are signed and attested by the same workflow. An image a refresh published before refreshes moved into
`release.yml` (2026-10-31) has only a `rescan.yml` signature, with no SBOM, OpenVEX or provenance, until its line is
refreshed or released again.

### Consuming images

| Tag | Use |
|---|---|
| `<tag>-patched.<n>`, or the digest | Production manifests. Immutable |
| `<tag>-patched` | Dev/canary. Always the newest revision, including Copa refreshes |

**Rollback:** point the moving tag back at an older revision, e.g.
`docker buildx imagetools create -t ghcr.io/<owner>/dex:v2.46.1-patched ghcr.io/<owner>/dex:v2.46.1-patched.2`.
Immutable tags are never rewritten.

### Copa refresh PRs

When `rescan` finds new fixable **OS** packages in a published image, it dispatches a `refresh` run of `release.yml`
for that line. That run builds nothing. Its `publish` job re-patches the released images with Copa to the next
revision. The run then handles that revision exactly like a release:
- it signs it and attaches its SBOM and OpenVEX;
- it attests its provenance;
- it moves the moving tag;
- it opens a `state/` PR titled `[<recipe>] copa refresh of <line>`.

Merge that PR so the state matches the registry; until it's merged, rescan skips the line. New **language** findings
instead trigger a `patch.yml` run, which ends in a normal patch PR.

To refresh a line by hand: *Actions → release → Run workflow*, with `refresh` ticked. A refresh stops before Copa,
and publishes nothing, if a moving tag no longer points at the digest `state/` records. That means a newer release or
refresh isn't recorded yet: merge its `state/` PR first.

## Adding a release line or a project

The full walk-through for a new project, with a checklist, is [onboarding.md](onboarding.md).

- **Line:** add it to `source.lines` in the recipe and merge. The push triggers `patch.yml` for that
  recipe.
- **Project:**
  1. Draft the recipe:
     - **Open source:** `patcher init owner/repo [--image quay.io/org/app:1.2.3]`. It detects the
       release line, ecosystems, toolchain, Dockerfile targets and test framework, and lists the test
       commands upstream CI runs as comments.
     - **Only an image:** `patcher init --image registry/org/app:1.2.3`. The source repo is read from
       the image's `org.opencontainers.image.source` label. Without one, an `image-only` draft is
       written.
  2. Resolve every `TODO` in `recipes/<name>.yaml`. Compare with the closest example in
     [recipes.md](recipes.md#worked-examples). The test command and its setup need the most care:
     mirror the upstream CI job, and install test dependencies into the checkout.
  3. Run `patcher validate`, then a local `patcher run <name> --skip-tests --skip-build`, then a full
     local run.
  4. Add the image to `inventory.yaml`, merge, then dispatch `patch.yml` with `recipe=<name>`.
- **Bundled binaries:** if the report lists findings `in bundled artifact`, add a component recipe
  (`mode: component`, see [recipes.md](recipes.md#components)) and reference it from the parent.
  For jars of a Java distribution the image unpacks, set [`bundledJars`](recipes.md#bundled-jars) on
  the image instead, with a smoke command that loads them.

## Coverage of the images we run

`inventory.yaml` lists the images our clusters actually run (`image`, optional `usedBy` and `owner`).
`patcher coverage` reports, for each one:

| Status | Meaning |
|---|---|
| `patched` | A recipe line covers this version and a patched image exists: use the ref shown |
| `newer release patched` | We patch a newer release of this image; upgrade to it |
| `pending first release` | The recipe and line exist, but nothing has been released yet |
| `version not tracked` | A recipe exists, but no line matches this version: add a line, or upgrade |
| `no recipe` | Nothing covers it: `patcher init` (see above) |
| `scanned only` | The recipe has `publish: false`: patched and reported, never pushed. Keep running the vendor image |

`rescan.yml` posts the table to its run summary every night. Keep the inventory current when
deployments change; `patcher coverage --fail-on-uncovered` can gate a CI job on it.

**New upstream release lines.** A recipe follows the lines you list. When upstream ships a newer line
(Argo CD v3.6 while the recipe tracks v3.5 and v3.4), the daily rescan reports it (`patcher
new-lines`) and opens one issue per line, labelled `new-release-line`. A prerelease, a Go submodule tag
and a tag the recipe's `exclude` patterns match don't count. Add the line to track it, and the issue closes
itself. To stay where you are, close the issue: it isn't reopened, and the next major or minor opens a
new one.

**End-of-life runtimes.** The same daily run checks what each recipe builds with against
[endoflife.date](https://endoflife.date) (`patcher eol`):
- **What it checks:** the base images in each tracked line's Dockerfiles (after `minVersions`) and the
  recipe's toolchain (Go, Node.js, Python, Temurin).
- **When it opens an issue:** one per recipe and release, labelled `end-of-life`, once the release is
  within 90 days of its end of life or past it. For example: "End of life: argo-rollouts Node.js 22".
- **What it covers:** runtimes in an image name or tag (`static-debian12`, `-alpine3.23`, `bookworm`)
  count. Bases a custom build command builds from count only when a dockerfile ecosystem lists the file.
- **To fix:** raise the base with `minVersions` on the dockerfile ecosystem (see
  [recipes.md](recipes.md#dockerfile)), or bump `toolchain`. The issue closes itself on the next run.
- **To accept it:** close the issue; it isn't reopened.
- **If a lookup fails** (endoflife.date or a Dockerfile can't be read), the job fails rather than
  closing issues.

## Dependency hygiene of this repo

| What | Mechanism | When | Your part |
|---|---|---|---|
| GitHub Actions | Dependabot (`github-actions`) | daily 07:00 ET | Review the grouped PR; the `# vX.Y.Z` comments next to each SHA are updated too |
| Patcher Python packages (`patcher/uv.lock`) | Dependabot (`uv`) | daily 07:00 ET | Review; CI runs the unit tests |
| Patcher image bases (`python`, `uv`) | Dependabot (`docker`) | daily 07:00 ET | Review; digest-pinned |
| mise, trivy, copa, cosign, osv-scanner, yq downloads | `tool-pins.yml` → `patcher pins --write` | Mondays 07:00 ET | Review the version table. The workflow already built the image, so every sha256 was checked |
| govulncheck, gotestsum, poetry / pipenv / pip-tools | Pinned in code (`reach.py`, recipes, `adapters/python.py`) | When you choose | Bump deliberately, to releases at least 14 days old |

- **Cooldown:** version updates wait until a release is **14 days old** (Dependabot `cooldown`,
  `patcher pins --min-age-days 14`). If you enable Dependabot *security updates*, those aren't held
  back.
- **Manual update:** `patcher pins` shows what would change; `patcher pins --write` applies it.

## CLI quick reference

| Command | Purpose |
|---|---|
| `patcher validate` | Check every recipe, skip, VEX and state file |
| `patcher schema --out schema` | Regenerate the JSON schemas after model changes (CI checks for drift) |
| `patcher plan [--recipe X] [--all] [--changed-files F]` | Matrix of lines that need a run, each with the platform its patch run builds on; recipes that can't be planned are listed under `errors` |
| `patcher run <recipe> [--line L] [--skip-tests] [--skip-build] [--no-copa] [--no-retry] [--no-cooldown]` | The PR flow, locally. Never pushes. Report in `out/<recipe>/<line>/generated/report.md` |
| `patcher init [owner/repo] [--image REF] [--name N]` | Draft a recipe for a new project or image |
| `patcher coverage [--json] [--fail-on-uncovered]` | Which inventory images are covered and patched |
| `patcher new-lines [--json]` | Upstream release lines newer than every line a recipe tracks |
| `patcher collect --out out` | Copy run outputs into `generated/` (what the PR job commits) |
| `patcher release-plan --recipe R --line L` (or `--changed-files F`) | The release's line, platforms and runners (release.yml's plan job) |
| `patcher release-build <recipe> --line L --platform P` | Release build for one platform: saves the images to `out/<recipe>/<line>/images/<arch>/`, pushes nothing |
| `patcher release-push <recipe> --line L [--platforms P,…]` | Pushes those archives as `<final>-<arch>` of a new revision; never overwrites a tag |
| `patcher publish <recipe> --line L [--revision N [--finish-existing]] [--platforms P,…]` | Merge, Copa, final tags, `state/`. Without `--revision`: finishes the newest revision whose per-arch images all exist |
| `patcher promote <recipe> --line L --release FILE` | Move the moving tags to the digests in a release record (after signing) |
| `patcher rescan [--pending F]` / `patcher refresh <recipe> --line L` | Nightly re-scan (skipping the lines whose state files `F` lists: open state PRs) and the Copa-only refresh, which release.yml runs in place of `publish` |
| `patcher pins [--write]` | Tool pin updates for `patcher/Dockerfile` |
