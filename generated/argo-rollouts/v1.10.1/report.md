## ✅ argo-rollouts `v1.10.1` — success

Upstream: https://github.com/argoproj/argo-rollouts @ `356117c8e9a2` (line `v1.10`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 15 / 14 / 1 | 0 / 1 / 1 / 0 | 28 | 0 |
| image `argo-rollouts` | 0 / 10 / 7 / 0 | 0 / 0 / 0 / 0 | 20 | 3 |
| image `kubectl-argo-rollouts` | 0 / 10 / 7 / 0 | 0 / 0 / 0 / 0 | 20 | 3 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `google.golang.org/grpc` | `v1.80.0` | `v1.83.2` | CVE-2026-84303, CVE-2026-84304, CVE-2026-84445, GHSA-hrxh-6v49-42gf |
| gomod | `go.mod` | `go.opentelemetry.io/otel` | `v1.39.0` | `v1.41.0` | CVE-2026-29181 |
| gomod | `go.mod` | `github.com/klauspost/compress` | `v1.18.0` | `v1.18.7` | CVE-2026-63209 |
| gomod | `go.mod` | `golang.org/x/net` | `v0.56.0` | `v0.60.0` | CVE-2026-78659, CVE-2026-78660, CVE-2026-78663, CVE-2026-78669, CVE-2026-97032 |
| gomod | `go.mod` | `golang.org/x/crypto` | `v0.53.0` | `v0.56.0` | CVE-2026-56854, CVE-2026-56855, CVE-2026-78662 |
| gomod | `go.mod` | `golang.org/x/text` | `v0.38.0` | `v0.41.0` | CVE-2026-56851, CVE-2026-56852 |
| gomod | `go.mod` | `golang.org/x/mod` | `v0.36.0` | `v0.40.0` | CVE-2026-56864, CVE-2026-56865 |
| pnpm | `ui/pnpm-lock.yaml` | `@babel/runtime` | `7.23.5` | `7.26.10` | CVE-2025-27789 |
| pnpm | `ui/pnpm-lock.yaml` | `lodash` | `4.17.21` | `4.18.1` | CVE-2025-13465, CVE-2026-2950, CVE-2026-4800 |
| pnpm | `ui/pnpm-lock.yaml` | `lodash-es` | `4.17.21` | `4.18.1` | CVE-2025-13465, CVE-2026-2950, CVE-2026-4800 |
| pnpm | `ui/pnpm-lock.yaml` | `min-document` | `2.19.0` | `2.19.1` | CVE-2025-57352 |
| pnpm | `ui/pnpm-lock.yaml` | `moment` | `2.29.4` | `2.31.0` | CVE-2026-17495 |
| pnpm | `ui/pnpm-lock.yaml` | `path-to-regexp` | `1.8.0` | `1.9.0` | CVE-2024-45296 |
| dockerfile | `Dockerfile` | `golang` | `golang:1.26` | `golang:1.26@sha256:670bb5aa5349ae03b8516764718486f4f16399134bdc9acd0c46a23f043ab05c` | base image refresh |
| dockerfile | `Dockerfile` | `docker.io/library/node` | `node:22` | `node:22@sha256:18a6d90fd60542269850c80ca03b29b1d9b14d6b221ac7ee8e35b0d33ef904bd` | base image refresh |
| dockerfile | `Dockerfile` | `golang` | `golang:1.26` | `golang:1.26@sha256:670bb5aa5349ae03b8516764718486f4f16399134bdc9acd0c46a23f043ab05c` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| HIGH | CVE-2022-0235 | `node-fetch` | `1.7.3` | `3.1.1, 2.6.7` | source (`trivy fs`): `ui/pnpm-lock.yaml` | needs-human: fix requires a bump beyond the `minor` policy |
| MEDIUM | CVE-2026-41907 | `uuid` | `9.0.1` | `11.1.1, 12.0.1, 13.0.1` | source (`trivy fs`): `ui/pnpm-lock.yaml` | needs-human: fix requires a bump beyond the `minor` policy |
| UNKNOWN | DLA-4845-1 | `ca-certificates` | `20250419~deb12u1` | `20250419~deb12u2` | image `argo-rollouts` | Copa failed: #22 2.487 dpkg: error processing package ca-certificates (--install): |
| UNKNOWN | DLA-4845-1 | `ca-certificates` | `20250419~deb12u1` | `20250419~deb12u2` | image `kubectl-argo-rollouts` | Copa failed: #22 2.111 dpkg: error processing package ca-certificates (--install): |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `go.mod` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `go.mod` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `argo-rollouts` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `argo-rollouts` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `kubectl-argo-rollouts` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `kubectl-argo-rollouts` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | DLA-4792-1 | `tzdata` | `2026b-0+deb12u1` | `2026c-0+deb12u1` | image `argo-rollouts` | Copa failed: #22 2.487 dpkg: error processing package ca-certificates (--install): |
| UNKNOWN | DLA-4854-1 | `tzdata` | `2026b-0+deb12u1` | `2026e-0+deb12u1` | image `argo-rollouts` | Copa failed: #22 2.487 dpkg: error processing package ca-certificates (--install): |
| UNKNOWN | DLA-4792-1 | `tzdata` | `2026b-0+deb12u1` | `2026c-0+deb12u1` | image `kubectl-argo-rollouts` | Copa failed: #22 2.111 dpkg: error processing package ca-certificates (--install): |
| UNKNOWN | DLA-4854-1 | `tzdata` | `2026b-0+deb12u1` | `2026e-0+deb12u1` | image `kubectl-argo-rollouts` | Copa failed: #22 2.111 dpkg: error processing package ca-certificates (--install): |

### Newer releases beyond the policy (not applied)

- `golang` → `1.27` in `Dockerfile`: newer tag 1.27 exists beyond the `patch` level for base images (set `level: minor` on this dockerfile ecosystem, or bump it in patches/)

### Upstream tests

✅ passed in 4.5 min — `go run gotest.tools/gotestsum@v1.13.0 --junitfile junit-unit-test.xml --format testname -- $(go list ./... | grep -v ./test/cmd/metrics-plugin-sample) -cover `

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| argo-rollouts | `patcher.local/argo-rollouts:v1.10.1-patched.dev` | ✅ `--help` | failed: #22 2.487 dpkg: error processing package ca-certificates (--install): |
| kubectl-argo-rollouts | `patcher.local/kubectl-argo-rollouts:v1.10.1-patched.dev` | ✅ `version` | failed: #22 2.111 dpkg: error processing package ca-certificates (--install): |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/argo-rollouts.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |
| CVE-2026-78661 | `golang.org/x/net` | vulnerable_code_not_in_execute_path | govulncheck (v1.9.0): golang.org/x/net is imported but the vulnerable function is never called |
| CVE-2026-97045 | `golang.org/x/net` | vulnerable_code_not_in_execute_path | govulncheck (v1.9.0): golang.org/x/net is imported but the vulnerable function is never called |

### Notes

- lodash 4.18.0 was withdrawn by its registry (Bad release. Please use lodash@4.17.21 instead.); 4.18.1 considered instead
- lodash-es 4.18.0 was withdrawn by its registry (Bad release. Please use lodash-es@4.17.23 instead.); 4.18.1 considered instead
