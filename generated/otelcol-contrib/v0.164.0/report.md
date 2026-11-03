## ✅ otelcol-contrib `v0.164.0` — success

Upstream: https://github.com/open-telemetry/opentelemetry-collector-releases @ `bf626fce5c80` (line `v0`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 1 / 0 / 0 | 0 / 0 / 0 / 0 | 3 | 0 |
| image `opentelemetry-collector-contrib` | 0 / 1 / 0 / 0 | 0 / 0 / 0 / 0 | 3 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `opentelemetry-collector-contrib`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `github.com/go-jose/go-jose/v4` | `v4.1.5` | `v4.1.6` | CVE-2026-116587 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| dockerfile | `distributions/otelcol-contrib/Dockerfile` | `alpine` | `alpine:3.24@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6` | `alpine:3.24@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `distributions/otelcol-contrib/gen/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `opentelemetry-collector-contrib` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |

### Upstream tests

Not run.

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| opentelemetry-collector-contrib | `patcher.local/opentelemetry-collector-contrib:0.164.0-patched.dev` | ✅ `--version`, ✅ `components`, ✅ `validate --config /etc/otelcol-contrib/config.yaml` | no fixable OS packages |

### Notes

- The generated module has no tests of its own (the components' tests live in opentelemetry-collector-contrib, 1,000+ modules); the build, `components` and `validate` against the default config are the checks.
- Releases come every two weeks. The v0 line follows the newest; the pinned line patches the version we run.
