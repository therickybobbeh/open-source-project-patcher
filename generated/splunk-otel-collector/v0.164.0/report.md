## ✅ splunk-otel-collector `v0.164.0` — success

Upstream: https://github.com/signalfx/splunk-otel-collector @ `370a0a68ebf6` (line `v0`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 5 / 5 / 0 | 0 / 0 / 0 / 0 | 10 | 0 |
| image `splunk-otel-collector` | 0 / 1 / 1 / 0 | 0 / 0 / 0 / 0 | 3 | 0 |

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
| dockerfile | `cmd/otelcol/Dockerfile` | `docker.io/alpine` | `alpine:3.24` | `alpine:3.24@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf` | base image refresh |
| dockerfile | `cmd/otelcol/Dockerfile` | `docker.io/alpine` | `alpine:3.17.0` | `alpine:3.24.4@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf` | 3.17.0 -> 3.24.4 (minVersions: the 3.24 line) |
| dockerfile | `cmd/otelcol/Dockerfile` | `docker.io/debian` | `debian:13` | `debian:13@sha256:9c6e381421d0f48d1b8133e573f33c185ee16cbf505eda9c4a8a4791b25ea8a6` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `baseline/go.mod` | cooldown: v0.59.0 released 1 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `go.mod` | cooldown: v0.59.0 released 1 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `internal/signalfx-agent/go.mod` | cooldown: v0.59.0 released 1 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `pkg/receiver/smartagentreceiver/go.mod` | cooldown: v0.59.0 released 1 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `pkg/splunkta/go.mod` | cooldown: v0.59.0 released 1 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `splunk-otel-collector` | cooldown: v0.59.0 released 1 day(s) ago (eligible 2026-11-18) |

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
