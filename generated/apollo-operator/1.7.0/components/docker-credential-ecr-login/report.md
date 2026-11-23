## ✅ docker-credential-ecr-login `v0.13.0` — success

Upstream: https://github.com/awslabs/amazon-ecr-credential-helper @ `9740915f670d` (line `docker-credential-ecr-login-0.13.0`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 1 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `ecr-login/go.mod` | `golang.org/x/sys` | `v0.20.0` | `v0.44.0` | CVE-2026-39824 |
| gomod | `ecr-login/go.mod` | `go` | `1.24` | `1.25.0` | required by a bumped dependency |

### Upstream tests

✅ passed in 0.3 min — `cd ecr-login && go test  ./...`
