# Verification log, 2026-10-27 to 2026-10-29

A record of the local runs that brought the pipeline up, before it ran in GitHub Actions. It is kept as it was written
and isn't updated. For what is released now, and how each release went, see [Status](../README.md#status).

## Local runs (2026-10-28)

Run locally inside the patcher image (linux/arm64, Docker Desktop) against the upstream releases
current on that date. The trivy, copacetic and strimzi-maven-builder rows come from 2026-10-27 runs,
before this round's changes. Nothing has run in GitHub Actions yet. Fixable counts are critical,
high, medium and low findings, before → after.

| Recipe | Verified | Result |
|---|---|---|
| dex v2.46.1 | full run + release flow | Source 12 → 0; images 46–48 → 0. Bundled gomplate rebuilt (7 bumps, tests pass) and swapped in. 4 fixes held back by the 7-day rule. `release-build` → `publish` → `rescan` verified against a local registry earlier |
| argo-cd v3.5.6 | full run | Source 50 → 4 (needs-human majors). Upstream tests pass as non-root. Image 256 → 148; everything left was in bundled kustomize and git-lfs, whose component fixes came after this run. A re-run with all three components was in progress |
| apollo-operator 1.6.0 (closed source) | image-only + components | 65 → 14. Both credential helpers rebuilt from source and swapped in; the rest is in the vendor's own binary |
| argo-workflows v4.1.6 | tests + 2 of 3 images | 3,840 upstream tests pass (one flaky test passed on upstream's own rerun). `workflow-controller` and `argocli` built and smoke-tested; `argoexec` not reached (a local Docker hang) |
| argo-rollouts v1.10.1 | tests | Source 30 → 2; unit tests pass. Image builds failed on local network errors (Go proxy EOFs) |
| trivy v0.76.1 | full run | Unit tests pass; image 25 → 0 |
| copacetic v0.15.0 | full run | Source 22 → 1 (`docker/docker` v28, needs-human); tests pass; images built |
| strimzi-maven-builder 1.3.0 | full run | Image 28 → 0 |
| maven 3.10.0 | full run + release flow | 34/34 bats tests; both variants build. Bundled Guava 33.7.1-jre → 33.7.2-jre swapped (`bundledJars`): images 1 → 0 (HIGH CVE-2026-102554); `mvn -v` and `mvn -B -emp smoke` pass. `release-build` → `publish` re-applied the swap from `jars.json` against a local registry, and refused a base whose jar didn't match the record |
| helm, kustomize, git-lfs, docker-credential-gcr | component recipes, standalone | Full upstream test suites pass (helm as non-root) |
| apollo-router v2.19.0 | patch stage only | 4 crates bumped; tests (compose services) and source build not run locally |
| strimzi 1.3.0 | patch stage only | Source 63 → 0. Unit tests need Testcontainers networking that Docker Desktop lacks; image build attempts hit local DNS outages |
| redis v8.10.3 | patch stage only | Base images refreshed; `runtest` and image builds not run locally |
| external-secrets v2.14.0 | patch stage only | No fixable findings at this release; `make test` and build not run locally |
| [examples](examples/README.md): spring-petclinic (Gradle) | full run | 17 → 0 jar findings (6 critical) via image-driven planning; Gradle tests pass |
| examples: z2jh-hub (Python image) | build path | 63 → 6 (only pip from the base image remains) |
| examples: k8s-hub-vendor (Copa library patching) | image-only | pip upgraded inside the vendor image at `level: minor`; 65 → 5 |
| examples: jupyterhub (pytest) | tests | Environment fixed (install cutoff, venv on PATH, proxy prefix): 500+ tests passing; a full clean run was in progress |

The Copa fast path (`rescan` → `refresh`) was also verified against a local registry.

The release flow with credential-free builds (2026-10-29) was verified locally against a throwaway registry, linux/arm64
only: maven 3.10.0 (two images in one repository, bundled-jar overlay) and trivy v0.76.1 (custom build `command`) went
through `release-build` (archives, no registry access) → `release-push` → `publish`. Also checked: finishing a revision
whose final tag existed (`publish` without `--revision`, as `rebuild: false` runs it) kept its digests; an archive of the
wrong platform was refused before anything was pushed; a second attempt took a new revision; a recorded revision was
refused; archives from Docker's classic image store push fine; Copa patches an image that came through an archive.
It has not run in GitHub Actions yet.
