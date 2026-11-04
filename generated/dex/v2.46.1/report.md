## ✅ dex `v2.46.1` — success

Upstream: https://github.com/dexidp/dex @ `75eb19238e10` (line `v2`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 4 / 8 / 0 | 0 / 0 / 0 / 0 | 16 | 0 |
| image `dex` | 0 / 22 / 24 / 2 | 0 / 0 / 0 / 0 | 54 | 0 |
| image `dex-distroless` | 0 / 22 / 23 / 2 | 0 / 0 / 0 / 0 | 52 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `dex`: ✅ passes
- image `dex-distroless`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `github.com/go-jose/go-jose/v4` | `v4.1.5` | `v4.1.6` | CVE-2026-116587 |
| gomod | `go.mod` | `golang.org/x/net` | `v0.59.0` | `v0.62.0` | CVE-2026-78659, CVE-2026-78660, CVE-2026-78661, CVE-2026-78663, CVE-2026-78669, CVE-2026-97032, CVE-2026-97045 |
| gomod | `api/v2/go.mod` | `golang.org/x/net` | `v0.57.0` | `v0.62.0` | CVE-2026-78659, CVE-2026-78660, CVE-2026-78661, CVE-2026-78663, CVE-2026-78669, CVE-2026-97032, CVE-2026-97045 |
| gomod | `api/v2/go.mod` | `golang.org/x/text` | `v0.40.0` | `v0.41.0` | CVE-2026-56851 |
| gomod | `api/v2/go.mod` | `go` | `1.25.0` | `1.26.0` | required by a bumped dependency |
| dockerfile | `Dockerfile` | `golang` | `golang:1.27.3-alpine3.24@sha256:f2c872bcee949b7be9c490efd02b48a8a2fbf947cdf533f1c58525ec9d8170fd` | `golang:1.27.3-alpine3.24@sha256:d200d2dd76b03a99b52651fd1325aff7dcd35422c35c01bac56571b0507f3deb` | base image refresh |
| dockerfile | `Dockerfile` | `alpine` | `alpine:3.24.2@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6` | `alpine:3.24.3@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a` | 3.24.2 -> 3.24.3 |
| dockerfile | `Dockerfile` | `alpine` | `alpine:3.24.2@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6` | `alpine:3.24.3@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a` | 3.24.2 -> 3.24.3 |
| dockerfile | `Dockerfile` | `gcr.io/distroless/static-debian13` | `static-debian13:nonroot@sha256:e2e927ec666bae08560abb3c55d0659eceabb657f56b6782ab500a9fc7f555e3` | `static-debian13:nonroot@sha256:25ac8f0c3b2334a9eb05452266bd4697864a8c8ef0ef71e5e6480d7f92868329` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `dex` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `dex` | component `gomplate` (rebuilt from source): untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after  |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `dex-distroless` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `dex-distroless` | component `gomplate` (rebuilt from source): untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after  |

### Newer releases beyond the policy (not applied)

- `tonistiigi/xx` → `1.10.0` in `Dockerfile`: newer tag 1.10.0 exists beyond the `patch` level for base images (set `level: minor` on this dockerfile ecosystem, or bump it in patches/)
- `ghcr.io/hairyhenderson/gomplate` → `v5.3.1` in `Dockerfile`: newer tag v5.3.1 exists beyond the `patch` level for base images (set `level: minor` on this dockerfile ecosystem, or bump it in patches/)

### Upstream tests

✅ passed in 2.4 min — `go run gotest.tools/gotestsum@v1.13.0 --format pkgname-and-test-fails --junitfile junit.xml -- -race  ./...`

### Images

| Image | Ref | Runs as | Smoke | Copa |
|---|---|---|---|---|
| dex | `patcher.local/dex:v2.46.1-patched.dev` | `1001:1001` | ✅ `dex version` | no fixable OS packages |
| dex-distroless | `patcher.local/dex:v2.46.1-distroless-patched.dev` | `1001:1001` | ✅ `dex version` | no fixable OS packages |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/dex.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |

### Bundled components (rebuilt from source and swapped in)

| Image | Component | Path | Version | Status | Bumps | Tests | Notes |
|---|---|---|---|---|---|---|---|
| dex | gomplate | `/usr/local/bin/gomplate` | 5.2.0 | success | 7 | passed | version from Go build info |
| dex-distroless | gomplate | `/usr/local/bin/gomplate` | 5.2.0 | success | 7 | passed | version from Go build info |
