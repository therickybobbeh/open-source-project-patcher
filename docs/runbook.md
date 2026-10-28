# Runbook

For the people who review patch PRs and operate the pipeline. Background is in
[architecture.md](architecture.md), configuration in [recipes.md](recipes.md), and known problems in
[troubleshooting.md](troubleshooting.md).

## One-time setup

1. **GitHub App** for opening PRs. PRs opened with the default `GITHUB_TOKEN` don't trigger checks.
   - Permissions: *Contents: read & write*, *Pull requests: read & write*.
   - Install it on this repository.
   - Add the variable `PATCHER_APP_ID` and the secret `PATCHER_APP_PRIVATE_KEY`.
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

What to check, section by section:

1. **Fixable vulnerabilities:** counts before and after, for the source tree and each image.
   **New > 0 needs attention:** a bump pulled in something that's vulnerable.
2. **Changes applied:** every bump, with the CVEs it fixes. Bumps above the policy cap only appear
   when you added an override.
3. **Still fixable after patching:** every remaining finding with a reason:

   | Reason | What to do |
   |---|---|
   | `needs-human: … beyond the policy` | Choose one: raise `policy` for that ecosystem in the recipe; add an `override` with a reason; write a patch in `patches/<recipe>/` (e.g. a `Cargo.toml` change); or accept it with a VEX statement |
   | `held: …` | Intentional (see `holds`). Revisit the hold if the fix matters |
   | `in bundled artifact …` | The finding is in a binary this source doesn't build (Argo CD's helm/kustomize/git-lfs, Dex's gomplate). Bump that tool's pin with a `patches/` patch or a `files` edit, or record a VEX decision |
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
5. **Images:** smoke results and what Copa did.
6. **`deps.patch`:** skim it. Lockfile churn is expected; unexpected source changes are not.

**Merging releases the line.** `release.yml` refuses patch sets whose status isn't `success` or
`no-changes`, so a draft can't be released by accident. Afterwards, merge the `state/` PR it opens:
`rescan` depends on it.

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
  --certificate-identity-regexp '^https://github.com/<owner>/support-images/\.github/workflows/release\.yml@' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com

# SLSA build provenance
gh attestation verify "oci://$IMG" --owner <owner>

# our VEX decisions, applied to a fresh scan
cosign verify-attestation "$IMG" --type openvex \
  --certificate-identity-regexp '^https://github.com/<owner>/support-images/' \
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

- **Line:** add it to `source.lines` in the recipe and merge. The push triggers `patch.yml` for that
  recipe.
- **Project:**
  1. Write a recipe; start from the closest example in [recipes.md](recipes.md#worked-examples).
  2. Run `patcher validate`, then a local `patcher run <name> --skip-tests --skip-build`, then a full
     local run.
  3. Merge, then dispatch `patch.yml` with `recipe=<name>`.

## Dependency hygiene of this repo

| What | Mechanism | When | Your part |
|---|---|---|---|
| GitHub Actions | Dependabot (`github-actions`) | daily 07:00 ET | Review the grouped PR; the `# vX.Y.Z` comments next to each SHA are updated too |
| Patcher Python packages (`patcher/uv.lock`) | Dependabot (`uv`) | daily 07:00 ET | Review; CI runs the unit tests |
| Patcher image bases (`python`, `uv`) | Dependabot (`docker`) | daily 07:00 ET | Review; digest-pinned |
| mise, trivy, copa, cosign, yq downloads | `tool-pins.yml` → `patcher pins --write` | Mondays 07:00 ET | Review the version table. The workflow already built the image, so every sha256 was checked |

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
| `patcher run <recipe> [--line L] [--skip-tests] [--skip-build] [--no-copa] [--no-retry]` | The PR flow, locally. Never pushes. Report in `out/<recipe>/<line>/generated/report.md` |
| `patcher collect --out out` | Copy run outputs into `generated/` (what the PR job commits) |
| `patcher release-build <recipe> --line L --platform P` / `patcher publish <recipe> --line L` | Release flow |
| `patcher rescan` / `patcher refresh <recipe> --line L` | Nightly re-scan and the Copa-only refresh |
| `patcher pins [--write]` | Tool pin updates for `patcher/Dockerfile` |
