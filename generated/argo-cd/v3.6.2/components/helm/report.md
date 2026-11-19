## ✅ helm `v4.3.2` — success

Upstream: https://github.com/helm/helm @ `8346aaa55e71` (line `helm-4.3.2`)
Attempts: full plan: tests failed → unpatched baseline: tests passed → capped at patch: tests passed

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 1 / 5 / 0 | 0 / 0 / 3 / 0 | 3 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `github.com/go-jose/go-jose/v4` | `v4.1.4` | `v4.1.6` | CVE-2026-116585, CVE-2026-116586, CVE-2026-116587 |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| MEDIUM | CVE-2026-128085 | `go.opentelemetry.io/otel/sdk` | `v1.45.0` | `1.47.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-128085 | `go.opentelemetry.io/otel/sdk/log` | `v0.21.0` | `1.47.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-128085 | `go.opentelemetry.io/otel/trace` | `v1.45.0` | `1.47.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |

### Upstream tests

✅ passed in 1.0 min — `go test  ./...`

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/helm.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |
