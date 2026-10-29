## ✅ argo-cd `v3.5.6` — success

Upstream: https://github.com/argoproj/argo-cd @ `c2b1e3017e2c` (line `v3.5`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 1 / 23 / 22 / 6 | 0 / 2 / 2 / 0 | 49 | 0 |
| image `argocd` | 2 / 122 / 124 / 10 | 0 / 25 / 18 / 2 | 217 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `github.com/go-jose/go-jose/v4` | `v4.1.4` | `v4.1.6` | CVE-2026-116585, CVE-2026-116586, CVE-2026-116587 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace` | `v1.44.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc` | `v1.44.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/sdk` | `v1.44.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `github.com/klauspost/compress` | `v1.18.0` | `v1.18.7` | CVE-2026-63209 |
| gomod | `go.mod` | `golang.org/x/net` | `v0.59.0` | `v0.60.0` | CVE-2026-78659, CVE-2026-78660, CVE-2026-78663, CVE-2026-78669, CVE-2026-97032 |
| gomod | `go.mod` | `github.com/slack-go/slack` | `v0.16.0` | `v0.23.1` | GHSA-gxhx-2686-5h9g |
| gomod | `gitops-engine/go.mod` | `golang.org/x/net` | `v0.49.0` | `v0.60.0` | CVE-2026-25680, CVE-2026-25681, CVE-2026-27136, CVE-2026-33814, CVE-2026-39821, CVE-2026-42502, CVE-2026-42506, CVE-2026 |
| gomod | `gitops-engine/go.mod` | `golang.org/x/sys` | `v0.40.0` | `v0.44.0` | CVE-2026-39824 |
| gomod | `gitops-engine/go.mod` | `golang.org/x/text` | `v0.33.0` | `v0.41.0` | CVE-2026-56851, CVE-2026-56852 |
| pnpm | `ui/pnpm-lock.yaml` | `brace-expansion` | `1.1.14` | `1.1.21` | CVE-2026-102276, CVE-2026-102277, CVE-2026-102278, CVE-2026-13149, CVE-2026-14257, CVE-2026-69152 |
| pnpm | `ui/pnpm-lock.yaml` | `brace-expansion` | `2.1.0` | `2.1.7` | CVE-2026-102276, CVE-2026-102277, CVE-2026-102278, CVE-2026-13149, CVE-2026-14257, CVE-2026-69152 |
| pnpm | `ui/pnpm-lock.yaml` | `dompurify` | `3.4.13` | `3.4.17` | GHSA-6688-9rhm-gjv2, GHSA-c6gr-qvv4-5v3f, GHSA-cg2g-xh64-v4q7, GHSA-mrv2-3pqr-j5jr, GHSA-p98j-92pf-mc4p |
| pnpm | `ui/pnpm-lock.yaml` | `form-data` | `4.0.5` | `4.0.6` | CVE-2026-12143 |
| pnpm | `ui/pnpm-lock.yaml` | `js-yaml` | `4.1.1` | `4.3.2` | CVE-2026-53550, CVE-2026-59869, CVE-2026-84375, GHSA-5p4m-2wfm-xmqj |
| pnpm | `ui/pnpm-lock.yaml` | `js-yaml` | `4.3.0` | `4.3.2` | CVE-2026-84375, GHSA-5p4m-2wfm-xmqj |
| pnpm | `ui/pnpm-lock.yaml` | `moment` | `2.30.1` | `2.31.0` | CVE-2026-17495 |
| pnpm | `ui/pnpm-lock.yaml` | `qs` | `6.15.2` | `6.16.1` | CVE-2026-110816, CVE-2026-82417, CVE-2026-82562 |
| dockerfile | `Dockerfile` | `docker.io/library/golang` | `golang:1.26.10@sha256:5c3f3f28a273c9b61698b2d34f18375929790ab1f1d3835d032d21e2b31eae0c` | `golang:1.26.10@sha256:670bb5aa5349ae03b8516764718486f4f16399134bdc9acd0c46a23f043ab05c` | base image refresh |
| dockerfile | `Dockerfile` | `ARG BASE_IMAGE` | `ubuntu:26.04@sha256:f3d28607ddd78734bb7f71f117f3c6706c666b8b76cbff7c9ff6e5718d46ff64` | `ubuntu:26.04@sha256:0e73b71479e7bc5f006bca872e25c3cd680dc052a0116f90d63ae363537db0dd` | base image refresh |
| dockerfile | `Dockerfile` | `docker.io/library/golang` | `golang:1.26.10@sha256:5c3f3f28a273c9b61698b2d34f18375929790ab1f1d3835d032d21e2b31eae0c` | `golang:1.26.10@sha256:670bb5aa5349ae03b8516764718486f4f16399134bdc9acd0c46a23f043ab05c` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| HIGH | CVE-2026-56851 | `golang.org/x/text` | `v0.28.0` | `0.41.0` | image `argocd` | component `kustomize` (rebuilt from source): needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-56852 | `golang.org/x/text` | `v0.28.0` | `0.39.0` | image `argocd` | component `kustomize` (rebuilt from source): needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-48801 | `linkify-it` | `3.0.3` | `5.0.1` | source (`trivy fs`): `ui/pnpm-lock.yaml` | needs-human: fix requires a bump beyond the `minor` policy |
| HIGH | CVE-2026-59887 | `linkify-it` | `3.0.3` | `5.0.2` | source (`trivy fs`): `ui/pnpm-lock.yaml` | needs-human: fix requires a bump beyond the `minor` policy |
| HIGH | CVE-2026-111943 | `stdlib` | `v1.24.13` | `1.26.10, 1.27.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-25679 | `stdlib` | `v1.24.13` | `1.25.8, 1.26.1` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-27145 | `stdlib` | `v1.24.13` | `1.25.11, 1.26.4` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-32280 | `stdlib` | `v1.24.13` | `1.25.9, 1.26.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-32281 | `stdlib` | `v1.24.13` | `1.25.9, 1.26.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-32283 | `stdlib` | `v1.24.13` | `1.25.9, 1.26.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-33811 | `stdlib` | `v1.24.13` | `1.25.10, 1.26.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-33814 | `stdlib` | `v1.24.13` | `1.25.10, 1.26.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-33818 | `stdlib` | `v1.24.13` | `1.25.13, 1.26.6, 1.27.0-rc.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-39820 | `stdlib` | `v1.24.13` | `1.25.10, 1.26.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-39821 | `stdlib` | `v1.24.13` | `1.25.13, 1.26.6, 1.27.0-rc.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-39822 | `stdlib` | `v1.24.13` | `1.25.12, 1.26.5, 1.27.0-rc.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-39836 | `stdlib` | `v1.24.13` | `1.25.10, 1.26.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-42499 | `stdlib` | `v1.24.13` | `1.25.10, 1.26.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-42504 | `stdlib` | `v1.24.13` | `1.25.11, 1.26.4` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-56853 | `stdlib` | `v1.24.13` | `1.25.13, 1.26.6, 1.27.0-rc.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-56858 | `stdlib` | `v1.24.13` | `1.25.13, 1.26.6, 1.27.0-rc.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-56859 | `stdlib` | `v1.24.13` | `1.25.13, 1.26.6, 1.27.0-rc.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-56860 | `stdlib` | `v1.24.13` | `1.25.13, 1.26.6, 1.27.0-rc.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-56862 | `stdlib` | `v1.24.13` | `1.25.13, 1.26.6, 1.27.0-rc.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-78667 | `stdlib` | `v1.24.13` | `1.26.9, 1.27.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-78669 | `stdlib` | `v1.24.13` | `1.26.9, 1.27.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| HIGH | CVE-2026-97031 | `stdlib` | `v1.24.13` | `1.26.9, 1.27.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | GHSA-67mh-4wv8-2f99 | `esbuild` | `0.18.20` | `0.25.0` | source (`trivy fs`): `ui/pnpm-lock.yaml` | needs-human: fix requires a bump beyond the `minor` policy |
| MEDIUM | CVE-2026-27142 | `stdlib` | `v1.24.13` | `1.25.8, 1.26.1` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-32282 | `stdlib` | `v1.24.13` | `1.25.9, 1.26.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-32288 | `stdlib` | `v1.24.13` | `1.25.9, 1.26.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-32289 | `stdlib` | `v1.24.13` | `1.25.9, 1.26.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-39823 | `stdlib` | `v1.24.13` | `1.25.10, 1.26.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-39825 | `stdlib` | `v1.24.13` | `1.25.10, 1.26.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-39826 | `stdlib` | `v1.24.13` | `1.25.10, 1.26.3` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-42505 | `stdlib` | `v1.24.13` | `1.25.12, 1.26.5, 1.27.0-rc.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-42507 | `stdlib` | `v1.24.13` | `1.25.11, 1.26.4` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-56866 | `stdlib` | `v1.24.13` | `1.26.9, 1.27.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-78659 | `stdlib` | `v1.24.13` | `1.26.9, 1.27.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-78660 | `stdlib` | `v1.24.13` | `1.26.9, 1.27.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-78663 | `stdlib` | `v1.24.13` | `1.26.9, 1.27.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-94439 | `stdlib` | `v1.24.13` | `1.26.9, 1.27.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-94440 | `stdlib` | `v1.24.13` | `1.26.9, 1.27.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-94448 | `stdlib` | `v1.24.13` | `1.26.9, 1.27.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-97030 | `stdlib` | `v1.24.13` | `1.26.9, 1.27.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-97032 | `stdlib` | `v1.24.13` | `1.26.9, 1.27.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| MEDIUM | CVE-2026-41907 | `uuid` | `9.0.1` | `11.1.1, 12.0.1, 13.0.1` | source (`trivy fs`): `ui/pnpm-lock.yaml` | needs-human: fix requires a bump beyond the `minor` policy |
| LOW | CVE-2026-27139 | `stdlib` | `v1.24.13` | `1.25.8, 1.26.1` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| LOW | CVE-2026-56857 | `stdlib` | `v1.24.13` | `1.26.9, 1.27.2` | image `argocd` | component `kustomize` (rebuilt from source): not fixed there, see `components/kustomize/report.md` |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `gitops-engine/go.mod` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `gitops-engine/go.mod` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `go.mod` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `go.mod` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `argocd` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `argocd` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `argocd` | component `git-lfs` (rebuilt from source): cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `argocd` | component `git-lfs` (rebuilt from source): cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `argocd` | component `helm` (rebuilt from source): cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `argocd` | component `helm` (rebuilt from source): cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |

### Newer releases beyond the policy (not applied)

- `docker.io/library/golang` → `1.27.3` in `Dockerfile`: newer tag 1.27.3 exists beyond the `patch` level for base images (set `level: minor` on this dockerfile ecosystem, or bump it in patches/)
- `docker.io/library/node` → `24.22.2` in `Dockerfile`: newer tag 24.22.2 exists beyond the `patch` level for base images (set `level: minor` on this dockerfile ecosystem, or bump it in patches/)

### Upstream tests

✅ passed in 11.4 min — `make test-local`

Skipped tests (from `skips/argo-cd.yaml`):

| Match | Reason | Owner | Expires |
|---|---|---|---|
| `^TestIndex$` | Downloads the live argo-helm index (argoproj.github.io); fails on network flakes, unrelated to dependency updates | platform-team | 2027-04-30 |
| `^Test_nativeHelmChart_ExtractChart$` | Pulls a chart from the live argo-helm repository | platform-team | 2027-04-30 |

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| argocd | `patcher.local/argocd:v3.5.6-patched.dev` | ✅ `argocd version --client` | no fixable OS packages |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/argo-cd.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| CVE-2026-78661 | `golang.org/x/net` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/net is not imported |
| CVE-2026-97045 | `golang.org/x/net` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/net is not imported |
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |

### Bundled components (rebuilt from source and swapped in)

| Image | Component | Path | Version | Status | Bumps | Tests | Notes |
|---|---|---|---|---|---|---|---|
| argocd | helm | `/usr/local/bin/helm` | 4.2.1 | success | 14 | passed | version from Go build info |
| argocd | kustomize | `/usr/local/bin/kustomize` | 5.8.1 | no-changes | 0 | passed | version from hack/tool-versions.sh |
| argocd | git-lfs | `/usr/local/bin/git-lfs` | 3.7.1 | success | 5 | passed | version from hack/tool-versions.sh |

### Notes

- helm, kustomize and git-lfs are rebuilt from source at the versions in hack/tool-versions.sh (components); moving to a newer tool version still needs a patch that updates tool-versions.sh and hack/installers/checksums/.
- End-to-end tests (k3s cluster) are not part of `make test-local` and are not run.
- brace-expansion 3.0.3 was withdrawn by its registry (contains bloat files); 3.0.4 considered instead
