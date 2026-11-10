## ✅ kafka-exporter `v1.11.0` — success

Upstream: https://github.com/danielqsj/kafka_exporter @ `c08240632142` (line `kafka-exporter-1.11.0`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 1 / 1 / 0 | 0 / 0 / 0 / 0 | 2 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `golang.org/x/net` | `v0.60.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |

### Upstream tests

✅ passed in 0.3 min — `go test -short  ./...`

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/kafka-exporter.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |
