## ✅ helm `v4.3.2` — success

Upstream: https://github.com/helm/helm @ `8346aaa55e71` (line `helm-4.3.2`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 1 / 5 / 0 | 0 / 0 / 1 / 0 | 4 | 0 |

- `CVE-2026-128085` is still in source (`trivy fs`) (`go.mod`), in `go.opentelemetry.io/otel/sdk/log` v0.21.0, fixed in 1.47.0: not counted as fixed
- `CVE-2026-128085` is still in source (`trivy fs`) (`go.mod`), in `go.opentelemetry.io/otel/sdk/log` v0.21.0, fixed in 1.47.0: not counted as fixed

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `github.com/go-jose/go-jose/v4` | `v4.1.4` | `v4.1.6` | CVE-2026-116585, CVE-2026-116586, CVE-2026-116587 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/sdk` | `v1.45.0` | `v1.47.0` | CVE-2026-128085 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/trace` | `v1.45.0` | `v1.47.0` | CVE-2026-128085 |
| gomod | `go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.59.0` | GO-2026-5932 |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| MEDIUM | CVE-2026-128085 | `go.opentelemetry.io/otel/sdk/log` | `v0.21.0` | `1.47.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `minor` policy |

### Upstream tests

✅ passed in 2.6 min — `go test  ./...`

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/helm.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| CVE-2026-128085 | `go.opentelemetry.io/otel/sdk/log` | vulnerable_code_not_in_execute_path | govulncheck (v1.9.0): go.opentelemetry.io/otel/sdk/log is imported but the vulnerable function is never called |
