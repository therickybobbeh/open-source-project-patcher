# Onboarding a project or image

This guide takes a new open-source project, or a vendor image, from nothing to a released, signed
image whose updates arrive as pull requests. Allow an afternoon for a typical project, most of it
spent getting the upstream tests to run. The field-by-field reference is [recipes.md](recipes.md);
reviewing and releasing is in the [runbook](runbook.md).

## Before you start

**Is it already covered?** Add the image to [`inventory.yaml`](../inventory.yaml), then run
`patcher coverage`. Each image gets one of these answers:

- *Covered:* it shows the patched image to switch to.
- *Newer upstream release:* only a new release line is needed. See
  [Adding a release line](runbook.md#adding-a-release-line-or-a-project).
- *No recipe:* continue below.

**Pick the mode** from what you have:

| You have | Mode | What the pipeline does |
|---|---|---|
| The source, with tagged releases | `source` (default) | Bumps vulnerable dependencies, runs upstream's tests, rebuilds the image, then Copa for OS packages |
| Only an image (vendor or closed source) | `image-only` | Scans it, runs Copa on OS packages (and on pip/npm libraries with `copa: {libraries: true}`), rebuilds bundled open-source helpers. Set `publish: false` if the license doesn't allow republishing |
| A binary bundled inside another image (helm in Argo CD, …) | `component` | Rebuilt from source at the bundled version, then copied into the parent's image. Never released alone |

## 1. Draft the recipe

```bash
cd patcher
uv run patcher init owner/repo --image quay.io/org/app:1.2.3   # open source
uv run patcher init --image registry.example.com/vendor/app:4.5  # image only
```

`init` clones the repo at its newest release and writes `recipes/<name>.yaml` and
`skips/<name>.yaml`. It detects:

- the release line (a `tagPattern` for the newest major/minor);
- the ecosystems (Go, Rust, Maven, Gradle, npm/pnpm/yarn, Python) and their tools;
- the toolchain versions;
- the Dockerfiles and their targets;
- the test framework, with the test commands upstream CI runs, written as comments.

For an image only, the source repo is read from the image's `org.opencontainers.image.source` label.
Without that label, it writes an `image-only` draft.

## 2. Resolve the TODOs

Every `TODO` in the draft needs a decision. Compare with the closest
[worked example](recipes.md#worked-examples) or the [validated examples](examples/README.md).

| Field | What to check |
|---|---|
| `source.lines` | One entry per version you run. `tagPattern` must match only that line's tags |
| `ecosystems` | One entry per manifest directory. Remove anything that isn't shipped (docs sites, examples) |
| `build.images` | Dockerfile, `target`, the `upstream` image you run today (it's the "before" in every report), `smoke` commands that prove the image starts, `ownBinaries` if the image also carries third-party binaries |
| `tests` | Mirror the upstream CI job: same command, setup, services (compose, Testcontainers) and env. Set `timeoutMinutes` |
| `components` / `bundledJars` | Only after a first run shows findings `in bundled artifact` (step 4) |
| `publish` | `false` for vendor images you may not redistribute |

`patcher validate` checks the result against the schema.

## 3. Run it locally

The patcher runs in the same container image as CI:

```bash
scripts/patcher-docker.sh validate
scripts/patcher-docker.sh run <name> --skip-tests --skip-build   # the plan only: what would be bumped
scripts/patcher-docker.sh run <name>                             # tests, build, smoke, Copa, report
```

The report is `out/<name>/<line>/generated/report.md`, the same one the PR will carry. On macOS, set
`PATCHER_DOCKER_CONFIG` first. [Troubleshooting](troubleshooting.md) explains why, and covers the
other failures seen when bringing up a project.

## 4. Make the first run clean

Read the report section by section:

- **Tests that fail on both sides.** The report says when failing tests *also fail on the unpatched
  source*. Those are upstream's or the environment's, not yours. A test that needs live credentials
  or an external service goes in `skips/<name>.yaml`, with a reason, an owner and `expires`. The
  router's live-AWS test is an example. Never skip a test that fails only after the bumps.
- **Findings `in bundled artifact`.** These are binaries the source doesn't build:
  - a Go/Rust tool from another project → add a [component](recipes.md#components);
  - a jar from a Java distribution the image unpacks → set [`bundledJars`](recipes.md#bundled-jars)
    on the image, with a smoke command that loads the jars.
- **Still fixable after patching.** Each row gives a reason, such as a fix waiting out the 7-day
  release age, or a fix only in a newer major. Act on the row, or accept it with a VEX statement
  (see the [runbook](runbook.md#recording-vex-decisions)).

Repeat until the run ends `success`, or `tests-preexisting` with every failure understood.

## 5. Merge, review, release

1. Open a PR containing the recipe, the skips and any `patches/<name>/`, plus the image in
   `inventory.yaml` with `usedBy` and `owner`. Its checks run `patcher validate` and the unit tests.
2. Merge it. The push starts `patch.yml` for the new recipe. Its PR, `[<name>] <tag>: dependency
   updates (<status>)`, carries the report.
   [Reviewing a patch PR](runbook.md#reviewing-a-patch-pr) covers what to check.
3. Merge the patch PR. `release.yml` then:
   - builds each platform on a native runner;
   - pushes to GHCR;
   - signs the image and attaches the SBOM, OpenVEX and SLSA provenance;
   - opens a `[<name>] record release of <line>` PR. Merge it: `state/` is what the nightly run and
     `patcher coverage` read.

## After onboarding

- **New upstream releases:** the nightly run checks every line. A new tag in a line starts a patch
  run, and its PR follows.
- **Lines with nothing to change:** these stop after the scans, so watching them is cheap. A fix that
  is still too new is retried after its release-age wait.
- **Released images** are rescanned daily. New fixable findings re-run the line, or refresh the image
  with Copa.
- **A new version line** (for example the next minor) is a one-line change to `source.lines`.

## Checklist for the onboarding PR

- [ ] `patcher validate` passes
- [ ] A local run's report has been read: tests pass, or every skip has a reason, owner and expiry
- [ ] Bundled findings are handled (component, `bundledJars`, or VEX with a reason)
- [ ] The image is in `inventory.yaml` with `usedBy` and `owner`
- [ ] `publish: false` is set if the image may not be redistributed
