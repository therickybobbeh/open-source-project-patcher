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
   `patcher validate`, schema and lock-file drift). Dependabot, tool-pins and patch PRs all go
   through it.
4. **GHCR:** images are published to `ghcr.io/<owner>/<image>` and start **private**. Make them
   public, or give your clusters' pull secrets access.
5. **Release lines:** edit each recipe's `source.lines` to the versions you actually run.
6. **First run:** *Actions → patch → Run workflow*, `recipe=dex`. Check the job summary (the report
   is posted there), then the PR it opens.

## Reviewing a patch PR

Each PR is titled `[<recipe>] <tag>: dependency updates (<status>)`. The body is the generated
report; the same files are in `generated/<recipe>/<tag>/`. The PR is a **draft** when tests, the
build or a smoke test failed.

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
| Nightly (03:17 UTC) | Lines whose newest upstream tag isn't released yet, **minus** lines whose patch set for that tag is in a PR (open, or merged into `generated/`: a failed release is re-run with `release.yml`, not re-patched) and lines another run is patching right now. A `no-changes` line comes back every night, so a new fix is picked up the next day; a line with nothing to change costs a clone and the scans |
| Push to `recipes/`, `skips/`, `patches/`, `vex/` | The lines of the recipes that changed (`_global.yaml`: all of them) |
| Manual dispatch | The recipe (and line) you name, or every line with `all` |

Two runs never patch the same line at once: the second one waits.

### Failure alerts

`ci-alerts.yml` follows every run on `main` of patch, release, rescan, patcher-image, tool-pins
and wiki history. Each failed or timed-out job opens an issue labelled `ci-failure`, titled
`CI failure: <workflow> / <job>`. The issue names the failed step and links the job log. Another
failure of the same job adds a comment. The issue closes itself the next time that job passes, so the
open `ci-failure` issues are exactly what is broken now. Watch the label, or subscribe to it, to get
notified.

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

`release.yml` runs when a patch PR merges:
1. Rebuilds the reviewed patch set per platform.
2. Merges the platforms and runs Copa.
3. Signs with cosign (keyless).
4. Attaches a CycloneDX SBOM, the OpenVEX document and SLSA provenance.
5. Pushes the tags.
6. Opens a `state/` PR.

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

### Consuming images

| Tag | Use |
|---|---|
| `<tag>-patched.<n>`, or the digest | Production manifests. Immutable |
| `<tag>-patched` | Dev/canary. Always the newest revision, including Copa refreshes |

**Rollback:** point the moving tag back at an older revision, e.g.
`docker buildx imagetools create -t ghcr.io/<owner>/dex:v2.46.1-patched ghcr.io/<owner>/dex:v2.46.1-patched.2`.
Immutable tags are never rewritten.

### Copa refresh PRs

When `rescan` finds new fixable **OS** packages in a published image, it publishes and signs the
next revision right away (Copa only, no source rebuild). It then opens a `state/` PR titled
`[<recipe>] copa refresh of <line>`. Merge it so the state matches the registry. New **language**
findings instead trigger a `patch.yml` run, which ends in a normal patch PR.

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
| `patcher plan [--recipe X] [--all] [--changed-files F]` | Matrix of lines that need a run |
| `patcher run <recipe> [--line L] [--skip-tests] [--skip-build] [--no-copa] [--no-retry] [--no-cooldown]` | The PR flow, locally. Never pushes. Report in `out/<recipe>/<line>/generated/report.md` |
| `patcher init [owner/repo] [--image REF] [--name N]` | Draft a recipe for a new project or image |
| `patcher coverage [--json] [--fail-on-uncovered]` | Which inventory images are covered and patched |
| `patcher new-lines [--json]` | Upstream release lines newer than every line a recipe tracks |
| `patcher collect --out out` | Copy run outputs into `generated/` (what the PR job commits) |
| `patcher release-build <recipe> --line L --platform P` / `patcher publish <recipe> --line L` | Release flow |
| `patcher rescan` / `patcher refresh <recipe> --line L` | Nightly re-scan and the Copa-only refresh |
| `patcher pins [--write]` | Tool pin updates for `patcher/Dockerfile` |
