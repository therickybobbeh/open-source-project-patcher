## ✅ splunk-otel-collector `v0.165.1` — success

Upstream: https://github.com/signalfx/splunk-otel-collector @ `ea2445c6e13a` (line `v0`)

> **Upgrade:** `v0.164.0` → `v0.165.1`, a minor release ([release notes](https://github.com/signalfx/splunk-otel-collector/releases/tag/v0.165.1)). The daily merge round leaves it for a person: merge it by hand once you've read what changed.
Attempts: full plan: tests failed → unpatched baseline: tests passed → capped at patch: tests passed

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 1 / 0 / 0 / 0 | 1 / 0 / 0 / 0 | 0 | 0 |
| image `splunk-otel-collector` | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `splunk-otel-collector`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| dockerfile | `cmd/otelcol/Dockerfile` | `docker.io/alpine` | `alpine:3.24` | `alpine:3.24@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf` | base image refresh |
| dockerfile | `cmd/otelcol/Dockerfile` | `docker.io/alpine` | `alpine:3.17.0` | `alpine:3.24.4@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf` | 3.17.0 -> 3.24.4 (minVersions: the 3.24 line) |
| dockerfile | `cmd/otelcol/Dockerfile` | `docker.io/debian` | `debian:13` | `debian:13@sha256:9c6e381421d0f48d1b8133e573f33c185ee16cbf505eda9c4a8a4791b25ea8a6` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| CRITICAL | CVE-2026-130001 | `mustache` | `0.99.8` | `1.1.3` | source (`trivy fs`): `instrumentation/packaging/fpm/Gemfile.lock` | not addressed - investigate |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `baseline/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `internal/signalfx-agent/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `pkg/receiver/smartagentreceiver/go.mod` | needs-human: fix requires a bump beyond the `patch` policy |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `splunk-otel-collector` | needs-human: fix requires a bump beyond the `patch` policy |

### Upstream tests

✅ passed in 2.3 min — `make test-all`

### Images

| Image | Ref | Runs as | Smoke | Copa |
|---|---|---|---|---|
| splunk-otel-collector | `patcher.local/splunk-otel-collector:0.165.1-patched.dev` | `999:999` | ✅ `--version`, ✅ `validate` | no fixable OS packages |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/splunk-otel-collector.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |

### Notes

- Published on quay.io only (not Docker Hub). Every command except --version and --help needs SPLUNK_ACCESS_TOKEN and SPLUNK_REALM, so the smoke tests pass placeholders.
- We ran 0.147.0, which still has the Smart Agent bundle; this recipe patches the newest release to upgrade to.
