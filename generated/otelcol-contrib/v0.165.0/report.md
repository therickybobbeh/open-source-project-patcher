## ✅ otelcol-contrib `v0.165.0` — success

Upstream: https://github.com/open-telemetry/opentelemetry-collector-releases @ `b9425f263115` (line `v0`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |
| image `opentelemetry-collector-contrib` | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 1 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `opentelemetry-collector-contrib`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| dockerfile | `distributions/otelcol-contrib/Dockerfile` | `alpine` | `alpine:3.24@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a` | `alpine:3.24@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `distributions/otelcol-contrib/gen/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `opentelemetry-collector-contrib` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |

### Upstream tests

Not run.

### Images

| Image | Ref | Runs as | Smoke | Copa |
|---|---|---|---|---|
| opentelemetry-collector-contrib | `patcher.local/opentelemetry-collector-contrib:0.165.0-patched.dev` | `10001:10001` | ✅ `--version`, ✅ `components`, ✅ `validate --config /etc/otelcol-contrib/config.yaml` | no fixable OS packages |

### Notes

- The generated module has no tests of its own (the components' tests live in opentelemetry-collector-contrib, 1,000+ modules); the build, `components` and `validate` against the default config are the checks.
- Releases come every two weeks. The v0 line follows the newest; the pinned line patches the version we run.
