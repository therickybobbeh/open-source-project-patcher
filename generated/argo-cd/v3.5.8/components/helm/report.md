## ✅ helm `v4.2.1` — success

Upstream: https://github.com/helm/helm @ `d591a19b953b` (line `helm-4.2.1`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 14 / 15 / 4 | 0 / 0 / 1 / 0 | 31 | 0 |

- `CVE-2026-128085` is still in source (`trivy fs`) (`go.mod`), in `go.opentelemetry.io/otel/sdk/log` v0.21.0, fixed in 1.47.0: not counted as fixed
- `CVE-2026-128085` is still in source (`trivy fs`) (`go.mod`), in `go.opentelemetry.io/otel/sdk/log` v0.21.0, fixed in 1.47.0: not counted as fixed

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `github.com/distribution/distribution/v3` | `v3.1.1` | `v3.1.2` | CVE-2026-85747 |
| gomod | `go.mod` | `oras.land/oras-go/v2` | `v2.6.1` | `v2.6.2` | CVE-2026-50163, CVE-2026-85731, CVE-2026-85732 |
| gomod | `go.mod` | `google.golang.org/grpc` | `v1.80.0` | `v1.83.1` | CVE-2026-84303, CVE-2026-84304, CVE-2026-84445, GHSA-hrxh-6v49-42gf |
| gomod | `go.mod` | `go.opentelemetry.io/otel/sdk` | `v1.43.0` | `v1.47.0` | CVE-2026-128085, CVE-2026-81870 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/trace` | `v1.43.0` | `v1.47.0` | CVE-2026-128085 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace` | `v1.43.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc` | `v1.42.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp` | `v1.43.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `github.com/klauspost/compress` | `v1.18.4` | `v1.18.7` | CVE-2026-63209 |
| gomod | `go.mod` | `golang.org/x/net` | `v0.55.0` | `v0.62.0` | CVE-2026-46600, CVE-2026-78659, CVE-2026-78660, CVE-2026-78661, CVE-2026-78663, CVE-2026-78669, CVE-2026-97032, CVE-2026 |
| gomod | `go.mod` | `golang.org/x/crypto` | `v0.53.0` | `v0.59.0` | CVE-2026-56854, CVE-2026-56855, CVE-2026-78662, GO-2026-5932 |
| gomod | `go.mod` | `golang.org/x/text` | `v0.38.0` | `v0.41.0` | CVE-2026-56851, CVE-2026-56852 |
| gomod | `go.mod` | `golang.org/x/mod` | `v0.36.0` | `v0.40.0` | CVE-2026-56864, CVE-2026-56865 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlplog/otlploggrpc` | `v0.18.0` | `v0.21.0` | CVE-2026-81871 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/sdk/log` | `v0.19.0` | `v0.21.0` | CVE-2026-81872 |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| MEDIUM | CVE-2026-128085 | `go.opentelemetry.io/otel/sdk/log` | `v0.21.0` | `1.47.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `minor` policy |

### Upstream tests

✅ passed in 1.9 min — `go test  ./...`
