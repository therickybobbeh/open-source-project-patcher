## ➖ kustomize `kustomize/v5.8.1` — no-changes

Upstream: https://github.com/kubernetes-sigs/kustomize @ `9790a1c3efd2` (line `kustomize-5.8.1`)
Attempts: full plan: tests failed → unpatched baseline: tests passed → capped at patch: tests passed

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 6 / 0 / 0 | 0 / 6 / 0 / 0 | 0 | 0 |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| HIGH | CVE-2026-56864 | `golang.org/x/mod` | `v0.27.0` | `0.40.0` | source (`trivy fs`): `cmd/gorepomod/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-56865 | `golang.org/x/mod` | `v0.27.0` | `0.40.0` | source (`trivy fs`): `cmd/gorepomod/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-56851 | `golang.org/x/text` | `v0.28.0` | `0.41.0` | source (`trivy fs`): `cmd/gorepomod/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-56852 | `golang.org/x/text` | `v0.28.0` | `0.39.0` | source (`trivy fs`): `cmd/gorepomod/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-56851 | `golang.org/x/text` | `v0.28.0` | `0.41.0` | source (`trivy fs`): `kustomize/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| HIGH | CVE-2026-56852 | `golang.org/x/text` | `v0.28.0` | `0.39.0` | source (`trivy fs`): `kustomize/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | CVE-2026-39824 | `golang.org/x/sys` | `v0.35.0` | `0.44.0` | source (`trivy fs`): `api/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | CVE-2026-39824 | `golang.org/x/sys` | `v0.35.0` | `0.44.0` | source (`trivy fs`): `cmd/config/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | CVE-2026-39824 | `golang.org/x/sys` | `v0.35.0` | `0.44.0` | source (`trivy fs`): `cmd/config/internal/commands/e2e/e2econtainerconfig/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | CVE-2026-39824 | `golang.org/x/sys` | `v0.35.0` | `0.44.0` | source (`trivy fs`): `cmd/config/internal/commands/e2e/e2econtainerenvgenerator/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | CVE-2026-39824 | `golang.org/x/sys` | `v0.35.0` | `0.44.0` | source (`trivy fs`): `cmd/config/internal/commands/e2e/e2econtainermountbind/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | CVE-2026-39824 | `golang.org/x/sys` | `v0.35.0` | `0.44.0` | source (`trivy fs`): `cmd/config/internal/commands/e2e/e2econtainersimplegenerator/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | CVE-2026-39824 | `golang.org/x/sys` | `v0.35.0` | `0.44.0` | source (`trivy fs`): `cmd/gorepomod/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | CVE-2026-39824 | `golang.org/x/sys` | `v0.35.0` | `0.44.0` | source (`trivy fs`): `cmd/pluginator/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | CVE-2026-39824 | `golang.org/x/sys` | `v0.35.0` | `0.44.0` | source (`trivy fs`): `kustomize/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | CVE-2026-39824 | `golang.org/x/sys` | `v0.35.0` | `0.44.0` | source (`trivy fs`): `kyaml/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |

### Upstream tests

✅ passed in 0.2 min — `cd kustomize && go test  ./...`

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/kustomize.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| CVE-2026-56851 | `golang.org/x/text` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/text is not imported |
