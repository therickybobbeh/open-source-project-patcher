## ✅ splunk-otel-collector `v0.163.1` — success

Upstream: https://github.com/signalfx/splunk-otel-collector @ `4b86b8ce0dac` (line `v0`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 3 / 4 / 0 | 0 / 0 / 0 / 0 | 7 | 0 |
| image `splunk-otel-collector` | 0 / 1 / 2 / 0 | 0 / 0 / 0 / 0 | 3 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `github.com/go-jose/go-jose/v4` | `v4.1.4` | `v4.1.6` | CVE-2026-116585, CVE-2026-116586, CVE-2026-116587 |
| gomod | `baseline/go.mod` | `github.com/go-jose/go-jose/v4` | `v4.1.4` | `v4.1.6` | CVE-2026-116585, CVE-2026-116586, CVE-2026-116587 |
| gomod | `internal/signalfx-agent/go.mod` | `github.com/klauspost/compress` | `v1.18.0` | `v1.18.7` | CVE-2026-63209 |
| dockerfile | `cmd/otelcol/Dockerfile` | `docker.io/alpine` | `alpine:3.24` | `alpine:3.24@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a` | base image refresh |
| dockerfile | `cmd/otelcol/Dockerfile` | `docker.io/alpine` | `alpine:3.17.0` | `alpine:3.24.3@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a` | 3.17.0 -> 3.24.3 (minVersions: the 3.24 line) |
| dockerfile | `cmd/otelcol/Dockerfile` | `docker.io/debian` | `debian:13` | `debian:13@sha256:2dc419c6d7fe3dad0a2f9fd469c34cc90b0f9ba642d8fde837fe3d7d34a0e7f1` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `baseline/go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `baseline/go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `internal/signalfx-agent/go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `internal/signalfx-agent/go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `pkg/exporter/splunkoutputsexporter/go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `pkg/exporter/splunkoutputsexporter/go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `pkg/receiver/smartagentreceiver/go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `pkg/receiver/smartagentreceiver/go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `pkg/receiver/splunkinputsreceiver/go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `pkg/receiver/splunkinputsreceiver/go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `pkg/splunkta/go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `pkg/splunkta/go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | image `splunk-otel-collector` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | image `splunk-otel-collector` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |

### Upstream tests

✅ passed in 15.9 min — `make test-all`

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| splunk-otel-collector | `patcher.local/splunk-otel-collector:0.163.1-patched.dev` | ✅ `--version`, ✅ `validate` | no fixable OS packages |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/splunk-otel-collector.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |
| CVE-2026-78661 | `golang.org/x/net` | vulnerable_code_not_in_execute_path | govulncheck (v1.9.0): golang.org/x/net is imported but the vulnerable function is never called |
| CVE-2026-97045 | `golang.org/x/net` | vulnerable_code_not_in_execute_path | govulncheck (v1.9.0): golang.org/x/net is imported but the vulnerable function is never called |

### Notes

- Published on quay.io only (not Docker Hub). Every command except --version and --help needs SPLUNK_ACCESS_TOKEN and SPLUNK_REALM, so the smoke tests pass placeholders.
- We ran 0.147.0, which still has the Smart Agent bundle; this recipe patches the newest release to upgrade to.
