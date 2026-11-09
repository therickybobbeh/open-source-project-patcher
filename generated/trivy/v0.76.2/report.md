## ✅ trivy `v0.76.2` — success

Upstream: https://github.com/aquasecurity/trivy @ `3f6334d223b5` (line `v0`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| image `trivy` | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `trivy`: ✅ passes
  - ⚠️ trivy runs as root: give it a numeric non-root user (`user` on the recipe's image), or run it with runAsUser

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| dockerfile | `Dockerfile` | `alpine` | `alpine:3.24.3` | `alpine:3.24.4@sha256:93b41ef40b1677fce8fcc64ff4af09daddfacf5040afde618bc46c1e2d1cc7d4` | 3.24.3 -> 3.24.4 |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| MEDIUM | CVE-2026-33997 | `github.com/docker/docker` | `v28.5.2+incompatible` | `29.3.1` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `minor` policy |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `trivy` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |

### Upstream tests

✅ passed in 11.2 min — `go tool mage test:unit`

### Images

| Image | Ref | Runs as | Smoke | Copa |
|---|---|---|---|---|
| trivy | `patcher.local/trivy:0.76.2-patched.dev` | root (no `USER`) | ✅ `--version` | no fixable OS packages |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/trivy.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |

### Notes

- Trivy's release channels were compromised in March 2026 (GHSA-69fq-xp46-6x23). The patcher image should use this rebuilt Trivy, pinned by digest.
