# Operations runbook

Use the canonical [`docs/runbook.md`](../docs/runbook.md) for the complete
operator instructions.

The short version:

1. Configure the GitHub App, the `release` environment (main only, holds the App key), security
   settings, branch protection and GHCR.
2. Review patch PR reports for fixable findings, test status, image smoke tests,
   components, VEX suggestions and `deps.patch`.
3. Merge only `success`, `no-changes` or `tests-preexisting` patch sets.
4. Watch the release workflow; its `state/` PR merges itself once `test` passes.
   If a release fails after its builds, dispatch `release.yml` for the line with
   `rebuild: false` to finish it without building again.
5. Keep `inventory.yaml` aligned with the images actually deployed.

Never run upstream commands with credentials. Holds, overrides, skips and VEX
decisions must have explicit reasons and expiry where applicable.
