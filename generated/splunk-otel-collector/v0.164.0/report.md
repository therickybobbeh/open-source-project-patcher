## ✅ splunk-otel-collector `v0.164.0` — success

Upstream: https://github.com/signalfx/splunk-otel-collector @ `370a0a68ebf6` (line `v0`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 10 | 0 |
| image `splunk-otel-collector` | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 2 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `splunk-otel-collector`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `baseline/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `internal/signalfx-agent/go.mod` | `golang.org/x/net` | `v0.60.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `pkg/receiver/smartagentreceiver/go.mod` | `golang.org/x/net` | `v0.60.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `pkg/splunkta/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| dockerfile | `cmd/otelcol/Dockerfile` | `docker.io/alpine` | `alpine:3.24` | `alpine:3.24@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a` | base image refresh |
| dockerfile | `cmd/otelcol/Dockerfile` | `docker.io/alpine` | `alpine:3.17.0` | `alpine:3.24.3@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a` | 3.17.0 -> 3.24.3 (minVersions: the 3.24 line) |
| dockerfile | `cmd/otelcol/Dockerfile` | `docker.io/debian` | `debian:13` | `debian:13@sha256:2dc419c6d7fe3dad0a2f9fd469c34cc90b0f9ba642d8fde837fe3d7d34a0e7f1` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `baseline/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `internal/signalfx-agent/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `pkg/receiver/smartagentreceiver/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `pkg/splunkta/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `splunk-otel-collector` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |

### Upstream tests

✅ passed in 24.2 min — `make test-all`

### Images

| Image | Ref | Runs as | Smoke | Copa |
|---|---|---|---|---|
| splunk-otel-collector | `patcher.local/splunk-otel-collector:0.164.0-patched.dev` | `999:999` | ✅ `--version`, ✅ `validate` | no fixable OS packages |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/splunk-otel-collector.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |

### Notes

- Published on quay.io only (not Docker Hub). Every command except --version and --help needs SPLUNK_ACCESS_TOKEN and SPLUNK_REALM, so the smoke tests pass placeholders.
- We ran 0.147.0, which still has the Smart Agent bundle; this recipe patches the newest release to upgrade to.
