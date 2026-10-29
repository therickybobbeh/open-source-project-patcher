# Architecture

The detailed architecture reference is [`docs/architecture.md`](../docs/architecture.md).

## End-to-end flow

1. `patch.yml` plans release lines from recipes and upstream tags.
2. The patch job runs in the patcher image without secrets, applies dependency
   updates, runs upstream tests, builds images and runs scans.
3. The PR job collects `generated/<recipe>/<tag>/` and opens or updates one
   patch PR per release line.
4. Merging a successful patch PR triggers `release.yml`, one run per line. It
   builds per architecture without registry credentials (the build runs
   upstream code) and saves the images as archives; a separate job pushes them.
   Then it merges manifests, runs Copa, signs the image, publishes attestations
   and, last, opens the `state/` PR.
5. `rescan.yml` finds new findings in published images and either refreshes OS
   packages or starts a new source patch.
6. `wiki-history.yml` records the repository's patch and release trail in
   `wiki/history.parquet`.

Recipes are policy and configuration; generated reports and state are the
auditable outputs. See the [layout](../README.md#layout) in the main README.
