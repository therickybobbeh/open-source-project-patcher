## ✅ argo-cd `v3.4.12` — success

Upstream: https://github.com/argoproj/argo-cd @ `590e562a5ae6` (line `v3.4`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 1 / 45 / 58 / 9 | 1 / 31 / 40 / 6 | 36 | 0 |
| image `argocd` | 4 / 154 / 148 / 12 | 2 / 77 / 59 / 5 | 179 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `github.com/go-jose/go-jose/v4` | `v4.1.4` | `v4.1.6` | CVE-2026-116585, CVE-2026-116586, CVE-2026-116587 |
| gomod | `go.mod` | `github.com/go-jose/go-jose/v3` | `v3.0.1` | `v3.0.5` | CVE-2024-28180, CVE-2025-27144, CVE-2026-34986 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace` | `v1.44.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc` | `v1.44.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/sdk` | `v1.44.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `github.com/klauspost/compress` | `v1.18.0` | `v1.18.7` | CVE-2026-63209 |
| gomod | `go.mod` | `golang.org/x/net` | `v0.58.0` | `v0.60.0` | CVE-2026-78659, CVE-2026-78660, CVE-2026-78663, CVE-2026-78669, CVE-2026-97032 |
| gomod | `go.mod` | `github.com/slack-go/slack` | `v0.16.0` | `v0.23.1` | GHSA-gxhx-2686-5h9g |
| gomod | `gitops-engine/go.mod` | `go.opentelemetry.io/otel` | `v1.38.0` | `v1.41.0` | CVE-2026-29181 |
| gomod | `gitops-engine/go.mod` | `golang.org/x/net` | `v0.44.0` | `v0.60.0` | CVE-2025-47911, CVE-2025-58190, CVE-2026-25680, CVE-2026-25681, CVE-2026-27136, CVE-2026-33814, CVE-2026-39821, CVE-2026 |
| gomod | `gitops-engine/go.mod` | `golang.org/x/sys` | `v0.36.0` | `v0.44.0` | CVE-2026-39824 |
| gomod | `gitops-engine/go.mod` | `golang.org/x/text` | `v0.29.0` | `v0.41.0` | CVE-2026-56851, CVE-2026-56852 |
| gomod | `gitops-engine/go.mod` | `github.com/moby/spdystream` | `v0.5.0` | `v0.5.1` | CVE-2026-35469 |
| dockerfile | `Dockerfile` | `docker.io/library/golang` | `golang:1.26.10@sha256:5c3f3f28a273c9b61698b2d34f18375929790ab1f1d3835d032d21e2b31eae0c` | `golang:1.26.10@sha256:670bb5aa5349ae03b8516764718486f4f16399134bdc9acd0c46a23f043ab05c` | base image refresh |
| dockerfile | `Dockerfile` | `ARG BASE_IMAGE` | `ubuntu:26.04@sha256:f3d28607ddd78734bb7f71f117f3c6706c666b8b76cbff7c9ff6e5718d46ff64` | `ubuntu:26.04@sha256:6a06111c3b0a8600feadb270aec771dc239bf407b25625f93f44ab00e11f4d3c` | base image refresh |
| dockerfile | `Dockerfile` | `docker.io/library/node` | `node:23.0.0@sha256:9d09fa506f5b8465c5221cbd6f980e29ae0ce9a3119e2b9bc0842e6a3f37bb59` | `node:24.22.2@sha256:e7add2a490bb17d97b485b8641bd88455fff7839ade0f5eba493c3508124d413` | 23.0.0 -> 24.22.2 (minVersions: the 24 line) |
| dockerfile | `Dockerfile` | `docker.io/library/golang` | `golang:1.26.10@sha256:5c3f3f28a273c9b61698b2d34f18375929790ab1f1d3835d032d21e2b31eae0c` | `golang:1.26.10@sha256:670bb5aa5349ae03b8516764718486f4f16399134bdc9acd0c46a23f043ab05c` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| CRITICAL | GHSA-cg2g-xh64-v4q7 | `dompurify` | `3.4.13` | `3.4.17` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| CRITICAL | CVE-2026-33186 | `google.golang.org/grpc` | `v1.72.1` | `1.79.3` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| CRITICAL | CVE-2025-68121 | `stdlib` | `v1.24.11` | `1.24.13, 1.25.7, 1.26.0-rc.3` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-101898 | `axios` | `1.13.5` | `1.20.0` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-101901 | `axios` | `1.13.5` | `1.20.0` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-42033 | `axios` | `1.13.5` | `1.15.1, 0.31.1` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-42035 | `axios` | `1.13.5` | `1.15.1, 0.31.1` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-42043 | `axios` | `1.13.5` | `1.15.1, 0.31.1` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-42264 | `axios` | `1.13.5` | `1.15.2` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-44486 | `axios` | `1.13.5` | `1.16.0, 0.32.0` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-44487 | `axios` | `1.13.5` | `1.16.0, 0.32.0` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-44488 | `axios` | `1.13.5` | `1.16.0` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-44494 | `axios` | `1.13.5` | `1.16.0` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-44495 | `axios` | `1.13.5` | `1.15.2, 0.31.1` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-44496 | `axios` | `1.13.5` | `1.16.0, 0.32.0` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-102990 | `basic-ftp` | `5.2.0` | `6.2.1` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-39983 | `basic-ftp` | `5.2.0` | `5.2.1` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-41324 | `basic-ftp` | `5.2.0` | `5.3.0` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-44240 | `basic-ftp` | `5.2.0` | `5.3.1` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | GHSA-6v7q-wjvx-w8wg | `basic-ftp` | `5.2.0` | `5.2.2` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-102276 | `brace-expansion` | `2.1.4` | `5.0.10, 3.0.7, 2.1.5, 1.1.19` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-102278 | `brace-expansion` | `2.1.4` | `5.0.11, 3.0.8, 2.1.6, 1.1.20` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| HIGH | GHSA-h6ch-v84p-w6p9 | `diff` | `2.2.3` | `3.5.0` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| HIGH | GHSA-mrv2-3pqr-j5jr | `dompurify` | `3.4.13` | `3.4.17` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-12143 | `form-data` | `4.0.5` | `2.5.6, 3.0.5, 4.0.6` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-12143 | `form-data` | `4.0.4` | `2.5.6, 3.0.5, 4.0.6` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-46680 | `github.com/containerd/containerd` | `v1.7.29` | `1.7.32` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-53488 | `github.com/containerd/containerd` | `v1.7.29` | `1.7.33` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-63209 | `github.com/klauspost/compress` | `v1.18.0` | `1.18.7` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-35469 | `github.com/moby/spdystream` | `v0.5.0` | `0.5.1` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-39828 | `golang.org/x/crypto` | `v0.45.0` | `0.52.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-39829 | `golang.org/x/crypto` | `v0.45.0` | `0.52.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-39830 | `golang.org/x/crypto` | `v0.45.0` | `0.52.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-39831 | `golang.org/x/crypto` | `v0.45.0` | `0.52.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-39832 | `golang.org/x/crypto` | `v0.45.0` | `0.52.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-39835 | `golang.org/x/crypto` | `v0.45.0` | `0.52.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-42508 | `golang.org/x/crypto` | `v0.45.0` | `0.52.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-46595 | `golang.org/x/crypto` | `v0.45.0` | `0.52.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-46597 | `golang.org/x/crypto` | `v0.45.0` | `0.52.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-56854 | `golang.org/x/crypto` | `v0.45.0` | `0.55.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-25681 | `golang.org/x/net` | `v0.47.0` | `0.55.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-27136 | `golang.org/x/net` | `v0.47.0` | `0.55.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-33814 | `golang.org/x/net` | `v0.47.0` | `0.53.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-39821 | `golang.org/x/net` | `v0.47.0` | `0.55.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-46600 | `golang.org/x/net` | `v0.47.0` | `0.56.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-78669 | `golang.org/x/net` | `v0.47.0` | `0.60.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-56851 | `golang.org/x/text` | `v0.31.0` | `0.41.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-56852 | `golang.org/x/text` | `v0.31.0` | `0.39.0` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-56851 | `golang.org/x/text` | `v0.28.0` | `0.41.0` | image `argocd` | component `kustomize` (rebuilt from source): needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-56852 | `golang.org/x/text` | `v0.28.0` | `0.39.0` | image `argocd` | component `kustomize` (rebuilt from source): needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-84304 | `google.golang.org/grpc` | `v1.72.1` | `1.83.1` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-84445 | `google.golang.org/grpc` | `v1.72.1` | `1.82.2, 1.83.2, 1.84.0-dev.0.20260825144003-d5a41119e0e3, 1.85.0-dev.0.20260825072537-93e31b48545e` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | GHSA-hrxh-6v49-42gf | `google.golang.org/grpc` | `v1.72.1` | `1.82.1` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| HIGH | CVE-2026-69192 | `ip-address` | `9.0.5` | `10.3.1` | source (`trivy fs`): `ui-test/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-4800 | `lodash` | `4.17.23` | `4.18.0` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-4800 | `lodash-es` | `4.17.23` | `4.18.0` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-27904 | `minimatch` | `5.1.6` | `10.2.3, 9.0.7, 8.0.6, 7.4.8, 6.2.2, 5.1.8, 4.2.5, 3.1.4` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-26996 | `minimatch` | `5.1.6` | `10.2.1, 9.0.6, 8.0.5, 7.4.7, 6.2.1, 5.1.7, 4.2.4, 3.1.3` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-27903 | `minimatch` | `5.1.6` | `10.2.3, 9.0.7, 8.0.6, 7.4.8, 6.2.2, 5.1.8, 4.2.5, 3.1.3` | source (`trivy fs`): `ui/yarn.lock` | not addressed - investigate |
| HIGH | CVE-2026-50151 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.1` | image `argocd` | component `helm` not swapped in (not-found): the original binary is still shipped |
| | | | | | | 172 more in `summary.json` |

### Newer releases beyond the policy (not applied)

- `docker.io/library/golang` → `1.27.3` in `Dockerfile`: newer tag 1.27.3 exists beyond the `patch` level for base images (set `level: minor` on this dockerfile ecosystem, or bump it in patches/)

### Upstream tests

✅ passed in 9.6 min — `make test-local`

Skipped tests (from `skips/argo-cd.yaml`):

| Match | Reason | Owner | Expires |
|---|---|---|---|
| `^TestIndex$` | Downloads the live argo-helm index (argoproj.github.io); fails on network flakes, unrelated to dependency updates | platform-team | 2027-04-30 |
| `^Test_nativeHelmChart_ExtractChart$` | Pulls a chart from the live argo-helm repository | platform-team | 2027-04-30 |

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| argocd | `patcher.local/argocd:v3.4.12-patched.dev` | ✅ `argocd version --client` | no fixable OS packages |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/argo-cd.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| CVE-2026-78661 | `golang.org/x/net` | vulnerable_code_not_in_execute_path | govulncheck (v1.9.0): golang.org/x/net is imported but the vulnerable function is never called |
| CVE-2026-97045 | `golang.org/x/net` | vulnerable_code_not_in_execute_path | govulncheck (v1.9.0): golang.org/x/net is imported but the vulnerable function is never called |
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |

### Bundled components (rebuilt from source and swapped in)

| Image | Component | Path | Version | Status | Bumps | Tests | Notes |
|---|---|---|---|---|---|---|---|
| argocd | helm | `/usr/local/bin/helm` | - | not-found | 0 | - | version of /usr/local/bin/helm unknown: set `version`, `versionFrom` or `versionCommand` |
| argocd | kustomize | `/usr/local/bin/kustomize` | 5.8.1 | no-changes | 0 | passed | version from hack/tool-versions.sh |
| argocd | git-lfs | `/usr/local/bin/git-lfs` | 3.7.1 | success | 5 | passed | version from hack/tool-versions.sh |

### Notes

- helm, kustomize and git-lfs are rebuilt from source at the versions in hack/tool-versions.sh (components); moving to a newer tool version still needs a patch that updates tool-versions.sh and hack/installers/checksums/.
- End-to-end tests (k3s cluster) are not part of `make test-local` and are not run.
