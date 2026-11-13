## ✅ trivy-operator `v0.36.1` — success

Upstream: https://github.com/aquasecurity/trivy-operator @ `b40091af2bfb` (line `v0`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |
| image `trivy-operator` | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 2 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `trivy-operator`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| dockerfile | `build/trivy-operator/Dockerfile` | `alpine` | `alpine:3.24.2` | `alpine:3.24.4@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf` | 3.24.2 -> 3.24.4 |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `trivy-operator` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |

### Upstream tests

✅ passed in 6.4 min — `go test -v -short -timeout 60s  ./...`

### Images

| Image | Ref | Runs as | Smoke | Copa |
|---|---|---|---|---|
| trivy-operator | `patcher.local/trivy-operator:0.36.1-patched.dev` | `10000` | - | no fixable OS packages |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/trivy-operator.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |

### Notes

- Only the default Alpine image is built. Upstream's `-ubi9` and `-ubi9-fips` variants (and s390x/ppc64le) are not.
- Scan jobs run a separate Trivy image (Helm values `trivy.image.registry`, `trivy.image.repository`, `trivy.image.tag`); point them at the patched image of the `trivy` recipe.
