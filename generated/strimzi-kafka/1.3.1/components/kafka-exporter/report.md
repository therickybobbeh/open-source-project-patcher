## ✅ kafka-exporter `v1.11.0` — success

Upstream: https://github.com/danielqsj/kafka_exporter @ `c08240632142` (line `kafka-exporter-1.11.0`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 1 / 1 / 0 | 0 / 0 / 0 / 0 | 3 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `golang.org/x/net` | `v0.60.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `go.mod` | `golang.org/x/crypto` | `v0.57.0` | `v0.59.0` | GO-2026-5932 |

### Upstream tests

✅ passed in 0.4 min — `go test -short  ./...`
