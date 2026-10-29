## ✅ gomplate `v5.2.0` — success

Upstream: https://github.com/hairyhenderson/gomplate @ `117c916d306b` (line `gomplate-5.2.0`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 8 / 10 / 1 | 0 / 0 / 0 / 0 | 19 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `github.com/go-git/go-git/v5` | `v5.19.1` | `v5.19.2` | CVE-2026-71556, CVE-2026-71557 |
| gomod | `go.mod` | `github.com/go-jose/go-jose/v4` | `v4.1.4` | `v4.1.6` | CVE-2026-116585, CVE-2026-116586, CVE-2026-116587 |
| gomod | `go.mod` | `google.golang.org/grpc` | `v1.81.1` | `v1.83.2` | CVE-2026-84303, CVE-2026-84304, CVE-2026-84445, GHSA-hrxh-6v49-42gf |
| gomod | `go.mod` | `go.opentelemetry.io/otel/sdk` | `v1.43.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `golang.org/x/net` | `v0.56.0` | `v0.60.0` | CVE-2026-78659, CVE-2026-78660, CVE-2026-78663, CVE-2026-78669, CVE-2026-97032 |
| gomod | `go.mod` | `golang.org/x/crypto` | `v0.54.0` | `v0.56.0` | CVE-2026-56854, CVE-2026-56855, CVE-2026-78662 |
| gomod | `go.mod` | `golang.org/x/text` | `v0.40.0` | `v0.41.0` | CVE-2026-56851 |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `go.mod` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `go.mod` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |

### Upstream tests

✅ passed in 2.3 min — `go test  $(go list ./... | grep -v /internal/tests/integration)`

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/gomplate.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |
| CVE-2026-78661 | `golang.org/x/net` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/net is not imported |
| CVE-2026-97045 | `golang.org/x/net` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/net is not imported |
