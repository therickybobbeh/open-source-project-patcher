# Onboarding a project or image

The full walk-through is [`docs/onboarding.md`](../docs/onboarding.md). In short:

1. **Check coverage.** Add the image to [`inventory.yaml`](../inventory.yaml) and run
   `patcher coverage`. It may already be covered, or only need a new release line.
2. **Draft the recipe.** `patcher init owner/repo --image <the image you run>`, or
   `patcher init --image <vendor image>` for closed source. It detects the release line,
   ecosystems, toolchain, Dockerfiles and tests, and leaves `TODO`s for decisions.
3. **Resolve the TODOs.** Check release lines, the upstream image, smoke commands and a test command
   that mirrors upstream CI. Set `publish: false` for images you may not redistribute.
4. **Run it locally.** `scripts/patcher-docker.sh run <name>` produces the same report the PR will
   carry. Skip only tests that fail on the unpatched source too, with a reason, owner and expiry.
   Handle bundled binaries with components or `bundledJars`.
5. **Merge and release.** Merging the recipe starts the first patch run. Merging its PR publishes
   the signed images and opens a `state/` PR to record the release.

| You have | Mode |
|---|---|
| Source with tagged releases | `source`: bumps, upstream tests, rebuild, Copa |
| Only an image | `image-only`: scan, Copa, rebuilt bundled helpers |
| A binary inside another image | `component`: rebuilt and copied into the parent |
