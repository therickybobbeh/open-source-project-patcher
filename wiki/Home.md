# Support Images Wiki

This is the repository-native wiki source for **support-images**, an automated
source-level patching pipeline for the open-source images we run.

## Start here

- [How it works](Architecture.md): the patch, test, build, Copa and release flow.
- [Operations runbook](Runbook.md): setup, review, releases, VEX and onboarding.
- [Onboarding](Onboarding.md): adding a new project or vendor image, from `patcher init` to the first release.
- [Recipe reference](Recipes.md): ecosystems, policy, release lines and examples.
- [Contributing](Contributing.md): the safe local development loop and extension points.
- [Patch history](../../wiki-history/History.md): a generated overview of commits that touch patch artifacts
  (the `wiki-history` branch).

The canonical documentation remains in [`docs/`](../docs/). These pages are a
curated navigation layer so the project can be read as a wiki without
duplicating the detailed reference.

## What this project does

For each configured upstream project, the pipeline checks out a release,
updates vulnerable dependencies with ecosystem-native tooling, runs upstream
tests, builds the image, patches remaining OS packages with Copa, and opens a
reviewable pull request. Merging the reviewed patch publishes signed images to
GHCR with SBOM, VEX and SLSA provenance attestations.

The tracked images and their current versions are listed in
[`inventory.yaml`](../inventory.yaml).
