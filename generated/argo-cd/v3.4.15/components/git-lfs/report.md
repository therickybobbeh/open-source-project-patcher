## ✅ git-lfs `v3.8.1` — success

Upstream: https://github.com/git-lfs/git-lfs @ `a662a6dbfedf` (line `git-lfs-3.8.1`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 4 / 7 / 0 | 0 / 0 / 0 / 0 | 12 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `golang.org/x/net` | `v0.57.0` | `v0.62.0` | CVE-2026-78659, CVE-2026-78660, CVE-2026-78661, CVE-2026-78663, CVE-2026-78669, CVE-2026-97032, CVE-2026-97045 |
| gomod | `go.mod` | `golang.org/x/crypto` | `v0.54.0` | `v0.59.0` | CVE-2026-56854, CVE-2026-56855, CVE-2026-78662, GO-2026-5932 |
| gomod | `go.mod` | `golang.org/x/text` | `v0.40.0` | `v0.41.0` | CVE-2026-56851 |
| gomod | `go.mod` | `go` | `1.25.0` | `1.26.0` | required by a bumped dependency |

### Upstream tests

✅ passed in 0.2 min — `go test -vet=off  ./...`
