## ✅ helm `v3.19.4` — success

Upstream: https://github.com/helm/helm @ `7cfb6e486dac` (line `helm-3.19.4`)
Attempts: full plan: tests failed → unpatched baseline: tests passed → capped at patch: tests passed

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 1 / 35 / 31 / 5 | 1 / 19 / 20 / 5 | 28 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `github.com/klauspost/compress` | `v1.18.0` | `v1.18.7` | CVE-2026-63209 |
| gomod | `go.mod` | `github.com/containerd/containerd` | `v1.7.29` | `v1.7.36` | CVE-2026-46680, CVE-2026-47262, CVE-2026-53488, CVE-2026-53493, CVE-2026-53495, CVE-2026-95838 |
| gomod | `go.mod` | `github.com/moby/spdystream` | `v0.5.0` | `v0.5.1` | CVE-2026-35469 |
| gomod | `go.mod` | `go` | `1.24.0` | `1.25.0` | required by a bumped dependency |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| CRITICAL | CVE-2026-33186 | `google.golang.org/grpc` | `v1.72.1` | `1.79.3` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-33540 | `github.com/distribution/distribution/v3` | `v3.0.0` | `3.1.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-35172 | `github.com/distribution/distribution/v3` | `v3.0.0` | `3.1.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-24051 | `go.opentelemetry.io/otel/sdk` | `v1.34.0` | `1.40.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-39883 | `go.opentelemetry.io/otel/sdk` | `v1.34.0` | `1.43.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-56854 | `golang.org/x/crypto` | `v0.52.0` | `0.55.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-56864 | `golang.org/x/mod` | `v0.35.0` | `0.40.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-56865 | `golang.org/x/mod` | `v0.35.0` | `0.40.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-39821 | `golang.org/x/net` | `v0.55.0` | `0.57.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-46600 | `golang.org/x/net` | `v0.55.0` | `0.56.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-78661 | `golang.org/x/net` | `v0.55.0` | `0.62.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-78669 | `golang.org/x/net` | `v0.55.0` | `0.60.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-56851 | `golang.org/x/text` | `v0.37.0` | `0.41.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-56852 | `golang.org/x/text` | `v0.37.0` | `0.39.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-84304 | `google.golang.org/grpc` | `v1.72.1` | `1.83.1` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-84445 | `google.golang.org/grpc` | `v1.72.1` | `1.82.2, 1.83.2, 1.84.0-dev.0.20260825144003-d5a41119e0e3, 1.85.0-dev.0.20260825072537-93e31b48545e` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | GHSA-hrxh-6v49-42gf | `google.golang.org/grpc` | `v1.72.1` | `1.82.1` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-50151 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.1` | source (`trivy fs`): `go.mod` | held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| HIGH | CVE-2026-50163 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.2` | source (`trivy fs`): `go.mod` | held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| HIGH | CVE-2026-85731 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.2` | source (`trivy fs`): `go.mod` | held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| MEDIUM | CVE-2026-41888 | `github.com/distribution/distribution/v3` | `v3.0.0` | `3.1.1` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-85747 | `github.com/distribution/distribution/v3` | `v3.0.0` | `3.1.2` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-81871 | `go.opentelemetry.io/otel/exporters/otlp/otlplog/otlploggrpc` | `v0.8.0` | `0.21.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-39882 | `go.opentelemetry.io/otel/exporters/otlp/otlplog/otlploghttp` | `v0.8.0` | `0.19.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-39882 | `go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetrichttp` | `v1.32.0` | `1.43.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-39882 | `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp` | `v1.32.0` | `1.43.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-128085 | `go.opentelemetry.io/otel/sdk` | `v1.34.0` | `1.47.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-81872 | `go.opentelemetry.io/otel/sdk/log` | `v0.8.0` | `0.21.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-128085 | `go.opentelemetry.io/otel/trace` | `v1.35.0` | `1.47.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-56855 | `golang.org/x/crypto` | `v0.52.0` | `0.56.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-78662 | `golang.org/x/crypto` | `v0.52.0` | `0.56.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-78659 | `golang.org/x/net` | `v0.55.0` | `0.60.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-78660 | `golang.org/x/net` | `v0.55.0` | `0.60.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-78663 | `golang.org/x/net` | `v0.55.0` | `0.60.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-97032 | `golang.org/x/net` | `v0.55.0` | `0.60.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-97045 | `golang.org/x/net` | `v0.55.0` | `0.62.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-84303 | `google.golang.org/grpc` | `v1.72.1` | `1.83.1` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-50162 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.1` | source (`trivy fs`): `go.mod` | held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| MEDIUM | CVE-2026-85732 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.2` | source (`trivy fs`): `go.mod` | held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| MEDIUM | GHSA-vh4v-2xq2-g5cg | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.1` | source (`trivy fs`): `go.mod` | held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| LOW | CVE-2026-81870 | `go.opentelemetry.io/otel/exporters/otlp/otlptrace` | `v1.34.0` | `1.45.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| LOW | CVE-2026-81870 | `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc` | `v1.34.0` | `1.45.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| LOW | CVE-2026-81870 | `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp` | `v1.32.0` | `1.45.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| LOW | CVE-2026-81870 | `go.opentelemetry.io/otel/sdk` | `v1.34.0` | `1.45.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| LOW | CVE-2026-48978 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.1` | source (`trivy fs`): `go.mod` | held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.52.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |

### Upstream tests

✅ passed in 1.6 min — `go test  ./...`

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/helm.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| CVE-2026-39883 | `go.opentelemetry.io/otel/sdk` | vulnerable_code_not_in_execute_path | govulncheck (v1.9.0): go.opentelemetry.io/otel/sdk is imported but the vulnerable function is never called |
| CVE-2026-56854 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |
| CVE-2026-56855 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |
| CVE-2026-78662 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |
| CVE-2026-46600 | `golang.org/x/net` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/net is not imported |
| CVE-2026-78661 | `golang.org/x/net` | vulnerable_code_not_in_execute_path | govulncheck (v1.9.0): golang.org/x/net is imported but the vulnerable function is never called |
| CVE-2026-97045 | `golang.org/x/net` | vulnerable_code_not_in_execute_path | govulncheck (v1.9.0): golang.org/x/net is imported but the vulnerable function is never called |
| CVE-2026-56851 | `golang.org/x/text` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/text is not imported |
| CVE-2026-33186 | `google.golang.org/grpc` | vulnerable_code_not_in_execute_path | govulncheck (v1.9.0): google.golang.org/grpc is imported but the vulnerable function is never called |
| CVE-2026-84445 | `google.golang.org/grpc` | vulnerable_code_not_in_execute_path | govulncheck (v1.9.0): google.golang.org/grpc is imported but the vulnerable function is never called |
| CVE-2026-84303 | `google.golang.org/grpc` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of google.golang.org/grpc is not imported |
| CVE-2026-50163 | `oras.land/oras-go/v2` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of oras.land/oras-go/v2 is not imported |
| CVE-2026-50162 | `oras.land/oras-go/v2` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of oras.land/oras-go/v2 is not imported |
