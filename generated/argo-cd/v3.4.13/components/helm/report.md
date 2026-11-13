## ✅ helm `v3.19.4` — success

Upstream: https://github.com/helm/helm @ `7cfb6e486dac` (line `helm-3.19.4`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 1 / 35 / 29 / 5 | 0 / 3 / 3 / 1 | 64 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `github.com/distribution/distribution/v3` | `v3.0.0` | `v3.1.2` | CVE-2026-33540, CVE-2026-35172, CVE-2026-41888, CVE-2026-85747 |
| gomod | `go.mod` | `google.golang.org/grpc` | `v1.72.1` | `v1.83.1` | CVE-2026-33186, CVE-2026-84303, CVE-2026-84304, CVE-2026-84445, GHSA-hrxh-6v49-42gf |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace` | `v1.34.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc` | `v1.34.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp` | `v1.32.0` | `v1.45.0` | CVE-2026-39882, CVE-2026-81870 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/sdk` | `v1.34.0` | `v1.45.0` | CVE-2026-24051, CVE-2026-39883, CVE-2026-81870 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetrichttp` | `v1.32.0` | `v1.43.0` | CVE-2026-39882 |
| gomod | `go.mod` | `github.com/klauspost/compress` | `v1.18.0` | `v1.18.7` | CVE-2026-63209 |
| gomod | `go.mod` | `github.com/containerd/containerd` | `v1.7.29` | `v1.7.36` | CVE-2026-46680, CVE-2026-47262, CVE-2026-53488, CVE-2026-53493, CVE-2026-53495, CVE-2026-95838 |
| gomod | `go.mod` | `golang.org/x/net` | `v0.47.0` | `v0.62.0` | CVE-2026-25680, CVE-2026-25681, CVE-2026-27136, CVE-2026-33814, CVE-2026-39821, CVE-2026-42502, CVE-2026-42506, CVE-2026 |
| gomod | `go.mod` | `golang.org/x/crypto` | `v0.45.0` | `v0.56.0` | CVE-2026-39827, CVE-2026-39828, CVE-2026-39829, CVE-2026-39830, CVE-2026-39831, CVE-2026-39832, CVE-2026-39833, CVE-2026 |
| gomod | `go.mod` | `golang.org/x/sys` | `v0.38.0` | `v0.44.0` | CVE-2026-39824 |
| gomod | `go.mod` | `golang.org/x/text` | `v0.31.0` | `v0.41.0` | CVE-2026-56851, CVE-2026-56852 |
| gomod | `go.mod` | `golang.org/x/mod` | `v0.29.0` | `v0.40.0` | CVE-2026-56864, CVE-2026-56865 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlplog/otlploggrpc` | `v0.8.0` | `v0.21.0` | CVE-2026-81871 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/sdk/log` | `v0.8.0` | `v0.21.0` | CVE-2026-81872 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlplog/otlploghttp` | `v0.8.0` | `v0.19.0` | CVE-2026-39882 |
| gomod | `go.mod` | `github.com/moby/spdystream` | `v0.5.0` | `v0.5.1` | CVE-2026-35469 |
| gomod | `go.mod` | `go` | `1.24.0` | `1.26.0` | required by a bumped dependency |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| HIGH | CVE-2026-50151 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.1` | source (`trivy fs`): `go.mod` | held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| HIGH | CVE-2026-50163 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.2` | source (`trivy fs`): `go.mod` | held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| HIGH | CVE-2026-85731 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.2` | source (`trivy fs`): `go.mod` | held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| MEDIUM | CVE-2026-50162 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.1` | source (`trivy fs`): `go.mod` | held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| MEDIUM | CVE-2026-85732 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.2` | source (`trivy fs`): `go.mod` | held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| MEDIUM | GHSA-vh4v-2xq2-g5cg | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.1` | source (`trivy fs`): `go.mod` | held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| LOW | CVE-2026-48978 | `oras.land/oras-go/v2` | `v2.6.0` | `2.6.1` | source (`trivy fs`): `go.mod` | held: helm 3's registry login fails with oras-go 2.6.1+ (TestRegistryLogin); helm 4 is not held |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |

### Upstream tests

✅ passed in 2.1 min — `go test  ./...`

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/helm.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| CVE-2026-50163 | `oras.land/oras-go/v2` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of oras.land/oras-go/v2 is not imported |
| CVE-2026-50162 | `oras.land/oras-go/v2` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of oras.land/oras-go/v2 is not imported |
