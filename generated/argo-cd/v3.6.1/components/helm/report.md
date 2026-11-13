## ✅ helm `v4.3.1` — success

Upstream: https://github.com/helm/helm @ `c0d08d0d6d94` (line `helm-4.3.1`)
Attempts: full plan: tests failed → unpatched baseline: tests passed → capped at patch: tests passed

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 3 / 4 / 0 | 0 / 1 / 1 / 0 | 5 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `github.com/go-jose/go-jose/v4` | `v4.1.4` | `v4.1.6` | CVE-2026-116585, CVE-2026-116586, CVE-2026-116587 |
| gomod | `go.mod` | `github.com/distribution/distribution/v3` | `v3.1.1` | `v3.1.2` | CVE-2026-85747 |
| gomod | `go.mod` | `google.golang.org/grpc` | `v1.83.1` | `v1.83.2` | CVE-2026-84445 |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| HIGH | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| MEDIUM | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |

### Upstream tests

✅ passed in 1.0 min — `go test  ./...`

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/helm.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |
| CVE-2026-78661 | `golang.org/x/net` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/net is not imported |
| CVE-2026-97045 | `golang.org/x/net` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/net is not imported |
