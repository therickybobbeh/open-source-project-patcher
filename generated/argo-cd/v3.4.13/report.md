## ✅ argo-cd `v3.4.13` — success

Upstream: https://github.com/argoproj/argo-cd @ `83ad9cd88fa0` (line `v3.4`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 1 / 26 / 32 / 9 | 1 / 8 / 6 / 5 | 44 | 0 |
| image `argocd` | 4 / 159 / 181 / 12 | 0 / 5 / 4 / 1 | 354 | 1 |

- `CVE-2026-116585` is still in source (`trivy fs`) (`go.mod`), in `github.com/go-jose/go-jose/v3` v3.0.5 (no fix): not counted as fixed
- `CVE-2026-116586` is still in source (`trivy fs`) (`go.mod`), in `github.com/go-jose/go-jose/v3` v3.0.5 (no fix): not counted as fixed
- `CVE-2026-116587` is still in source (`trivy fs`) (`go.mod`), in `github.com/go-jose/go-jose/v3` v3.0.5 (no fix): not counted as fixed
- `CVE-2026-2950` is still in source (`trivy fs`) (`ui/yarn.lock`), in `lodash-es` 4.17.23, fixed in 4.18.1: not counted as fixed
- `CVE-2026-4800` is still in source (`trivy fs`) (`ui/yarn.lock`), in `lodash-es` 4.17.23, fixed in 4.18.0: not counted as fixed

### Release gate (reported only (`gate.enforce: false`))

- image `argocd`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `github.com/go-jose/go-jose/v4` | `v4.1.4` | `v4.1.6` | CVE-2026-116585, CVE-2026-116586, CVE-2026-116587 |
| gomod | `go.mod` | `github.com/go-jose/go-jose/v3` | `v3.0.1` | `v3.0.5` | CVE-2024-28180, CVE-2025-27144, CVE-2026-34986 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace` | `v1.44.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc` | `v1.44.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/sdk` | `v1.44.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `github.com/klauspost/compress` | `v1.18.0` | `v1.18.7` | CVE-2026-63209 |
| gomod | `go.mod` | `golang.org/x/net` | `v0.58.0` | `v0.62.0` | CVE-2026-78659, CVE-2026-78660, CVE-2026-78661, CVE-2026-78663, CVE-2026-78669, CVE-2026-97032, CVE-2026-97045 |
| gomod | `go.mod` | `github.com/slack-go/slack` | `v0.16.0` | `v0.23.1` | GHSA-gxhx-2686-5h9g |
| gomod | `gitops-engine/go.mod` | `go.opentelemetry.io/otel` | `v1.38.0` | `v1.41.0` | CVE-2026-29181 |
| gomod | `gitops-engine/go.mod` | `golang.org/x/net` | `v0.44.0` | `v0.62.0` | CVE-2025-47911, CVE-2025-58190, CVE-2026-25680, CVE-2026-25681, CVE-2026-27136, CVE-2026-33814, CVE-2026-39821, CVE-2026 |
| gomod | `gitops-engine/go.mod` | `golang.org/x/sys` | `v0.36.0` | `v0.44.0` | CVE-2026-39824 |
| gomod | `gitops-engine/go.mod` | `golang.org/x/text` | `v0.29.0` | `v0.41.0` | CVE-2026-56851, CVE-2026-56852 |
| gomod | `gitops-engine/go.mod` | `github.com/moby/spdystream` | `v0.5.0` | `v0.5.1` | CVE-2026-35469 |
| yarn | `ui/yarn.lock` | `dompurify` | `3.4.13` | `3.4.17` | GHSA-6688-9rhm-gjv2, GHSA-c6gr-qvv4-5v3f, GHSA-cg2g-xh64-v4q7, GHSA-mrv2-3pqr-j5jr, GHSA-p98j-92pf-mc4p |
| yarn | `ui/yarn.lock` | `form-data` | `4.0.4` | `4.0.6` | CVE-2026-12143 |
| yarn | `ui/yarn.lock` | `formidable` | `2.1.2` | `2.1.5` | CVE-2025-46653 |
| yarn | `ui/yarn.lock` | `lodash` | `4.17.23` | `4.18.1` | CVE-2026-2950, CVE-2026-4800 |
| yarn | `ui/yarn.lock` | `lodash-es` | `4.17.23` | `4.18.1` | CVE-2026-2950, CVE-2026-4800 |
| yarn | `ui/yarn.lock` | `moment` | `2.29.4` | `2.31.0` | CVE-2026-17495 |
| yarn | `ui/yarn.lock` | `qs` | `6.14.2` | `6.16.1` | CVE-2026-110816, CVE-2026-82417, CVE-2026-82562, CVE-2026-8723 |
| yarn | `ui/yarn.lock` | `yaml` | `1.10.2` | `1.10.3` | CVE-2026-33532 |
| yarn | `ui/yarn.lock` | `dompurify` | `3.4.13` | `3.4.17` | GHSA-6688-9rhm-gjv2, GHSA-c6gr-qvv4-5v3f, GHSA-cg2g-xh64-v4q7, GHSA-mrv2-3pqr-j5jr, GHSA-p98j-92pf-mc4p |
| yarn | `ui/yarn.lock` | `lodash-es` | `4.17.23` | `4.18.1` | CVE-2026-2950, CVE-2026-4800 |
| yarn | `ui/yarn.lock` | `moment` | `2.29.4` | `2.31.0` | CVE-2026-17495 |
| yarn | `ui/yarn.lock` | `dompurify` | `3.4.13` | `3.4.17` | GHSA-6688-9rhm-gjv2, GHSA-c6gr-qvv4-5v3f, GHSA-cg2g-xh64-v4q7, GHSA-mrv2-3pqr-j5jr, GHSA-p98j-92pf-mc4p |
| yarn | `ui/yarn.lock` | `lodash-es` | `4.17.23` | `4.18.1` | CVE-2026-2950, CVE-2026-4800 |
| yarn | `ui/yarn.lock` | `moment` | `2.29.4` | `2.31.0` | CVE-2026-17495 |
| dockerfile | `Dockerfile` | `docker.io/library/golang` | `golang:1.26.10@sha256:5c3f3f28a273c9b61698b2d34f18375929790ab1f1d3835d032d21e2b31eae0c` | `golang:1.26.11@sha256:957952ae74dc010608717144399a59a2c6e82ea03d63be1c7ff6577c5a135f93` | 1.26.10 -> 1.26.11 |
| dockerfile | `Dockerfile` | `ARG BASE_IMAGE` | `ubuntu:26.04@sha256:f3d28607ddd78734bb7f71f117f3c6706c666b8b76cbff7c9ff6e5718d46ff64` | `ubuntu:26.04@sha256:065aa8626841f16057b78b027b464cd59c4fac36c204c72dcbf48d66f5fa8a96` | base image refresh |
| dockerfile | `Dockerfile` | `docker.io/library/node` | `node:23.0.0@sha256:9d09fa506f5b8465c5221cbd6f980e29ae0ce9a3119e2b9bc0842e6a3f37bb59` | `node:24.22.3@sha256:9d266751ca3d7fdbe651c878ffd5ad0a42fed49a18c283509267c97f025b7496` | 23.0.0 -> 24.22.3 (minVersions: the 24 line) |
| dockerfile | `Dockerfile` | `docker.io/library/golang` | `golang:1.26.10@sha256:5c3f3f28a273c9b61698b2d34f18375929790ab1f1d3835d032d21e2b31eae0c` | `golang:1.26.11@sha256:957952ae74dc010608717144399a59a2c6e82ea03d63be1c7ff6577c5a135f93` | 1.26.10 -> 1.26.11 |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| CRITICAL | GHSA-cg2g-xh64-v4q7 | `dompurify` | `3.4.13` | `3.4.17` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-102276 | `brace-expansion` | `2.1.4` | `5.0.10, 3.0.7, 2.1.5, 1.1.19` | source (`trivy fs`): `ui/yarn.lock` | bump failed: needs-human: yarn.lock has brace-expansion on majors [1, 2]; a yarn resolution would force all of them to 1.1.21 |
| HIGH | CVE-2026-102278 | `brace-expansion` | `2.1.4` | `5.0.11, 3.0.8, 2.1.6, 1.1.20` | source (`trivy fs`): `ui/yarn.lock` | bump failed: needs-human: yarn.lock has brace-expansion on majors [1, 2]; a yarn resolution would force all of them to 1.1.21 |
| HIGH | GHSA-h6ch-v84p-w6p9 | `diff` | `2.2.3` | `3.5.0` | source (`trivy fs`): `ui/yarn.lock` | needs-human: fix requires a bump beyond the `minor` policy |
| HIGH | GHSA-mrv2-3pqr-j5jr | `dompurify` | `3.4.13` | `3.4.17` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-56851 | `golang.org/x/text` | `v0.28.0` | `0.41.0` | image `argocd` | component `kustomize` (rebuilt from source): needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-56852 | `golang.org/x/text` | `v0.28.0` | `0.39.0` | image `argocd` | component `kustomize` (rebuilt from source): needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-4800 | `lodash-es` | `4.17.23` | `4.18.0` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-27904 | `minimatch` | `5.1.6` | `10.2.3, 9.0.7, 8.0.6, 7.4.8, 6.2.2, 5.1.8, 4.2.5, 3.1.4` | source (`trivy fs`): `ui/yarn.lock` | still at 3.1.3 after 3 round(s) |
| HIGH | CVE-2026-26996 | `minimatch` | `5.1.6` | `10.2.1, 9.0.6, 8.0.5, 7.4.7, 6.2.1, 5.1.7, 4.2.4, 3.1.3` | source (`trivy fs`): `ui/yarn.lock` | bump failed: needs-human: yarn.lock has minimatch on majors [3, 5, 9]; a yarn resolution would force all of them to 3.1.4 |
| HIGH | CVE-2026-27903 | `minimatch` | `5.1.6` | `10.2.3, 9.0.7, 8.0.6, 7.4.8, 6.2.2, 5.1.8, 4.2.5, 3.1.3` | source (`trivy fs`): `ui/yarn.lock` | bump failed: needs-human: yarn.lock has minimatch on majors [3, 5, 9]; a yarn resolution would force all of them to 3.1.4 |
| HIGH | CVE-2026-50151 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.1` | image `argocd` | component `helm` (rebuilt from source): held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| HIGH | CVE-2026-50163 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.2` | image `argocd` | component `helm` (rebuilt from source): held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| HIGH | CVE-2026-85731 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.2` | image `argocd` | component `helm` (rebuilt from source): held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| MEDIUM | CVE-2026-102277 | `brace-expansion` | `2.1.4` | `5.0.12, 3.0.9, 2.1.7, 1.1.21` | source (`trivy fs`): `ui/yarn.lock` | bump failed: needs-human: yarn.lock has brace-expansion on majors [1, 2]; a yarn resolution would force all of them to 1.1.21 |
| MEDIUM | GHSA-67mh-4wv8-2f99 | `esbuild` | `0.14.38` | `0.25.0` | source (`trivy fs`): `ui/yarn.lock` | needs-human: fix requires a bump beyond the `minor` policy |
| MEDIUM | CVE-2026-41650 | `fast-xml-parser` | `4.5.6` | `5.7.0` | source (`trivy fs`): `ui/yarn.lock` | needs-human: fix requires a bump beyond the `minor` policy |
| MEDIUM | CVE-2026-35206 | `helm.sh/helm/v3` | `v3.19.4` | `3.20.2` | image `argocd` | component `helm` (rebuilt from source): not fixed there, see `components/helm/report.md` |
| MEDIUM | CVE-2026-2950 | `lodash-es` | `4.17.23` | `4.18.1` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| MEDIUM | CVE-2026-17495 | `moment` | `2.29.4` | `2.31.0` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| MEDIUM | CVE-2026-50162 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.1` | image `argocd` | component `helm` (rebuilt from source): held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| MEDIUM | CVE-2026-85732 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.2` | image `argocd` | component `helm` (rebuilt from source): held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| MEDIUM | GHSA-vh4v-2xq2-g5cg | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.1` | image `argocd` | component `helm` (rebuilt from source): held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| MEDIUM | CVE-2026-41907 | `uuid` | `9.0.0` | `11.1.1, 12.0.1, 13.0.1` | source (`trivy fs`): `ui/yarn.lock` | needs-human: fix requires a bump beyond the `minor` policy |
| LOW | CVE-2026-24001 | `diff` | `2.2.3` | `8.0.3, 5.2.2, 4.0.4, 3.5.1` | source (`trivy fs`): `ui/yarn.lock` | needs-human: fix requires a bump beyond the `minor` policy |
| LOW | GHSA-6688-9rhm-gjv2 | `dompurify` | `3.4.13` | `3.4.16` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| LOW | GHSA-c6gr-qvv4-5v3f | `dompurify` | `3.4.13` | `3.4.17` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| LOW | GHSA-p98j-92pf-mc4p | `dompurify` | `3.4.13` | `3.4.16` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| LOW | CVE-2026-126066 | `fast-xml-parser` | `4.5.6` | `5.12.0` | source (`trivy fs`): `ui/yarn.lock` | needs-human: fix requires a bump beyond the `minor` policy |
| LOW | CVE-2026-48978 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.1` | image `argocd` | component `helm` (rebuilt from source): held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `argocd` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `argocd` | component `git-lfs` (rebuilt from source): cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `argocd` | component `helm` (rebuilt from source): cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | CVE-2026-97054 | `stdlib` | `v1.27.3` | `1.26.11, 1.27.4` | image `argocd` | in bundled artifact `usr/bin/pebble` (not built from this source) |

### Bumps that could not be applied

- `brace-expansion` → `1.1.21` in `ui/yarn.lock`: needs-human: yarn.lock has brace-expansion on majors [1, 2]; a yarn resolution would force all of them to 1.1.21
- `brace-expansion` → `2.1.7` in `ui/yarn.lock`: needs-human: yarn.lock has brace-expansion on majors [1, 2]; a yarn resolution would force all of them to 2.1.7
- `minimatch` → `3.1.4` in `ui/yarn.lock`: needs-human: yarn.lock has minimatch on majors [3, 5, 9]; a yarn resolution would force all of them to 3.1.4
- `minimatch` → `5.1.8` in `ui/yarn.lock`: needs-human: yarn.lock has minimatch on majors [3, 5, 9]; a yarn resolution would force all of them to 5.1.8

### Newer releases beyond the policy (not applied)

- `docker.io/library/golang` → `1.27.4` in `Dockerfile`: newer tag 1.27.4 exists beyond the `patch` level for base images (set `level: minor` on this dockerfile ecosystem, or bump it in patches/)

### Upstream tests

✅ passed in 11.8 min — `make test-local`

Skipped tests (from `skips/argo-cd.yaml`):

| Match | Reason | Owner | Expires |
|---|---|---|---|
| `^TestIndex$` | Downloads the live argo-helm index (argoproj.github.io); fails on network flakes, unrelated to dependency updates | platform-team | 2027-04-30 |
| `^Test_nativeHelmChart_ExtractChart$` | Pulls a chart from the live argo-helm repository | platform-team | 2027-04-30 |
| `^TestVerifyCommitSignature$` | Fetches the whole argo-cd repository with tags from GitHub (util/git); timed out after 90s on 2026-11-03 while the unpatched baseline's fetch made it, unrelated to dependency updates | platform-team | 2027-04-30 |

### Images

| Image | Ref | Runs as | Smoke | Copa |
|---|---|---|---|---|
| argocd | `patcher.local/argocd:v3.4.13-patched.dev` | `999` | ✅ `argocd version --client` | no fixable OS packages |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/argo-cd.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |

### Bundled components (rebuilt from source and swapped in)

| Image | Component | Path | Version | Status | Bumps | Tests | Notes |
|---|---|---|---|---|---|---|---|
| argocd | helm | `/usr/local/bin/helm` | 3.19.4 | success | 19 | passed | version from hack/tool-versions.sh |
| argocd | kustomize | `/usr/local/bin/kustomize` | 5.8.1 | no-changes | 0 | passed | version from hack/tool-versions.sh |
| argocd | git-lfs | `/usr/local/bin/git-lfs` | 3.7.1 | success | 5 | passed | version from hack/tool-versions.sh |

### Notes

- helm, kustomize and git-lfs are rebuilt from source at the versions in hack/tool-versions.sh (components); moving to a newer tool version still needs a patch that updates tool-versions.sh and hack/installers/checksums/.
- End-to-end tests (k3s cluster) are not part of `make test-local` and are not run.
- formidable 2.1.3 was withdrawn by its registry (ATTENTION: please upgrade to v3! The v1 and v2 versions are pretty old and depre); 2.1.5 considered instead
- formidable 3.5.3 was withdrawn by its registry (ATTENTION: please upgrade to latest of v3 (v3.5.4), should be working on Node v1); 3.5.4 considered instead
- lodash 4.18.0 was withdrawn by its registry (Bad release. Please use lodash@4.17.21 instead.); 4.18.1 considered instead
- lodash-es 4.18.0 was withdrawn by its registry (Bad release. Please use lodash-es@4.17.23 instead.); 4.18.1 considered instead
