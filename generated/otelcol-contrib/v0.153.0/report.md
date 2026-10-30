## ✅ otelcol-contrib `v0.153.0` — success

Upstream: https://github.com/open-telemetry/opentelemetry-collector-releases @ `6c0352ec0d8e` (line `v0.153`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 3 / 20 / 17 / 6 | 0 / 0 / 2 / 0 | 44 | 0 |
| image `opentelemetry-collector-contrib` | 3 / 35 / 28 / 7 | 0 / 0 / 2 / 0 | 71 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `github.com/go-jose/go-jose/v4` | `v4.1.4` | `v4.1.6` | CVE-2026-116585, CVE-2026-116586, CVE-2026-116587 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `go.mongodb.org/mongo-driver/v2` | `v2.3.1` | `v2.4.2` | CVE-2026-2303 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `github.com/snowflakedb/gosnowflake/v2` | `v2.0.2` | `v2.2.0` | CVE-2026-86597 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `google.golang.org/grpc` | `v1.81.1` | `v1.83.2` | CVE-2026-84303, CVE-2026-84304, CVE-2026-84445, GHSA-hrxh-6v49-42gf |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace` | `v1.43.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc` | `v1.43.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp` | `v1.43.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `go.opentelemetry.io/otel/sdk` | `v1.43.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `github.com/klauspost/compress` | `v1.18.6` | `v1.18.7` | CVE-2026-63209 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `github.com/rabbitmq/amqp091-go` | `v1.11.0` | `v1.14.0` | CVE-2026-107386, CVE-2026-77403, CVE-2026-77404, CVE-2026-77405, CVE-2026-77406, CVE-2026-77407, CVE-2026-77408, CVE-202 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `github.com/open-telemetry/opentelemetry-collector-contrib/exporter/sentryexporter` | `v0.153.0` | `v0.154.0` | CVE-2026-47256 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `golang.org/x/net` | `v0.55.0` | `v0.60.0` | CVE-2026-46600, CVE-2026-78659, CVE-2026-78660, CVE-2026-78663, CVE-2026-78669, CVE-2026-97032 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `golang.org/x/crypto` | `v0.52.0` | `v0.56.0` | CVE-2026-56854, CVE-2026-56855, CVE-2026-78662 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `golang.org/x/text` | `v0.37.0` | `v0.41.0` | CVE-2026-56851, CVE-2026-56852 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `golang.org/x/mod` | `v0.36.0` | `v0.40.0` | CVE-2026-56864, CVE-2026-56865 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `github.com/apache/thrift` | `v0.23.1-0.20260429145742-d2acd3c49e58` | `v0.24.0` | CVE-2026-43871 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `github.com/cilium/ebpf` | `v0.21.0` | `v0.22.0` | CVE-2026-10722 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `software.sslmate.com/src/go-pkcs12` | `v0.7.1` | `v0.7.2` | GHSA-mpwr-8vm7-h73f |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `go.opentelemetry.io/ebpf-profiler` | `v0.0.202618` | `v0.0.202622` | CVE-2026-48496 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `go.opentelemetry.io/otel/schema` | `v0.0.16` | `v0.0.17` | CVE-2026-45287 |
| gomod | `distributions/otelcol-contrib/gen/go.mod` | `go` | `1.25.0` | `1.26.0` | required by a bumped dependency |
| dockerfile | `distributions/otelcol-contrib/Dockerfile` | `alpine` | `alpine:3.23@sha256:5b10f432ef3da1b8d4c7eb6c487f2f5a8f096bc91145e68878dd4a5019afde11` | `alpine:3.23@sha256:ff7f0c727dd796aa36787bfcd9a64bf35a6ce72a73451b3359fde849b6703d63` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| MEDIUM | CVE-2026-81871 | `go.opentelemetry.io/otel/exporters/otlp/otlplog/otlploggrpc` | `v0.19.0` | `0.21.0` | source (`trivy fs`): `distributions/otelcol-contrib/gen/go.mod` | held: same lockstep as go.opentelemetry.io/otel/sdk/log |
| MEDIUM | CVE-2026-81871 | `go.opentelemetry.io/otel/exporters/otlp/otlplog/otlploggrpc` | `v0.19.0` | `0.21.0` | image `opentelemetry-collector-contrib` | held: same lockstep as go.opentelemetry.io/otel/sdk/log |
| MEDIUM | CVE-2026-81872 | `go.opentelemetry.io/otel/sdk/log` | `v0.19.0` | `0.21.0` | source (`trivy fs`): `distributions/otelcol-contrib/gen/go.mod` | held: moves in lockstep with the log exporters and bridges; bumped alone it breaks the build (fixed in newer collector releases) |
| MEDIUM | CVE-2026-81872 | `go.opentelemetry.io/otel/sdk/log` | `v0.19.0` | `0.21.0` | image `opentelemetry-collector-contrib` | held: moves in lockstep with the log exporters and bridges; bumped alone it breaks the build (fixed in newer collector releases) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `distributions/otelcol-contrib/gen/go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `distributions/otelcol-contrib/gen/go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `opentelemetry-collector-contrib` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `opentelemetry-collector-contrib` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |

### Newer releases beyond the policy (not applied)

- `alpine` → `3.24` in `distributions/otelcol-contrib/Dockerfile`: newer tag 3.24 exists beyond the `patch` level for base images (set `level: minor` on this dockerfile ecosystem, or bump it in patches/)

### Upstream tests

Not run.

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| opentelemetry-collector-contrib | `patcher.local/opentelemetry-collector-contrib:0.153.0-patched.dev` | ✅ `--version`, ✅ `components`, ✅ `validate --config /etc/otelcol-contrib/config.yaml` | no fixable OS packages |

### Notes

- The generated module has no tests of its own (the components' tests live in opentelemetry-collector-contrib, 1,000+ modules); the build, `components` and `validate` against the default config are the checks.
- Releases come every two weeks. The v0 line follows the newest; the pinned line patches the version we run.
