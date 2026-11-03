## ✅ trivy `v0.76.1` — success

Upstream: https://github.com/aquasecurity/trivy @ `e713f67f7d54` (line `v0`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 1 / 1 / 0 | 0 / 0 / 1 / 0 | 3 | 0 |
| image `trivy` | 1 / 4 / 2 / 22 | 0 / 0 / 0 / 0 | 34 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `trivy`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `github.com/go-jose/go-jose/v4` | `v4.1.5` | `v4.1.6` | CVE-2026-116587 |
| gomod | `go.mod` | `golang.org/x/net` | `v0.60.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| dockerfile | `Dockerfile` | `alpine` | `alpine:3.24.2` | `alpine:3.24.3@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a` | 3.24.2 -> 3.24.3 |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| MEDIUM | CVE-2026-33997 | `github.com/docker/docker` | `v28.5.2+incompatible` | `29.3.1` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `minor` policy |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `trivy` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |

### Upstream tests

✅ passed in 9.8 min — `go tool mage test:unit`

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| trivy | `patcher.local/trivy:0.76.1-patched.dev` | ✅ `--version` | no fixable OS packages |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/trivy.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |

### Notes

- Trivy's release channels were compromised in March 2026 (GHSA-69fq-xp46-6x23). The patcher image should use this rebuilt Trivy, pinned by digest.
