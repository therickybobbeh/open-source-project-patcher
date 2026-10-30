## ✅ copacetic `v0.15.0` — success

Upstream: https://github.com/project-copacetic/copacetic @ `bce7b4305e37` (line `v0`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 9 / 11 / 2 | 0 / 0 / 1 / 0 | 21 | 0 |
| image `copa` | n/a | 0 / 0 / 0 / 0 | 0 | 2 |
| image `copacetic-frontend` | 0 / 11 / 19 / 3 | 0 / 0 / 0 / 0 | 37 | 4 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `github.com/containerd/containerd/v2` | `v2.2.5` | `v2.2.9` | CVE-2026-53493, CVE-2026-53495, CVE-2026-95837, CVE-2026-95838 |
| gomod | `go.mod` | `google.golang.org/grpc` | `v1.83.1` | `v1.83.2` | CVE-2026-84445 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/exporters/otlp/otlptrace` | `v1.44.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/sdk` | `v1.44.0` | `v1.45.0` | CVE-2026-81870 |
| gomod | `go.mod` | `github.com/aquasecurity/trivy` | `v0.69.3` | `v0.72.0` | CVE-2026-54448, CVE-2026-55092, CVE-2026-63328 |
| gomod | `go.mod` | `golang.org/x/net` | `v0.56.0` | `v0.60.0` | CVE-2026-78659, CVE-2026-78660, CVE-2026-78663, CVE-2026-78669, CVE-2026-97032 |
| gomod | `go.mod` | `golang.org/x/crypto` | `v0.54.0` | `v0.56.0` | CVE-2026-56854, CVE-2026-56855, CVE-2026-78662 |
| gomod | `go.mod` | `golang.org/x/text` | `v0.40.0` | `v0.41.0` | CVE-2026-56851 |
| gomod | `go.mod` | `golang.org/x/mod` | `v0.37.0` | `v0.40.0` | CVE-2026-56864, CVE-2026-56865 |
| gomod | `go.mod` | `go` | `1.25.13` | `1.26.8` | required by a bumped dependency |
| gomod | `go.mod` | `github.com/containerd/containerd/v2` | `v2.3.2` | `v2.3.6` | CVE-2026-53493, CVE-2026-53495, CVE-2026-95837, CVE-2026-95838 |
| dockerfile | `frontend.Dockerfile` | `ARG GO_VERSION` | `1.25.13` | `1.26.10` | golang:1.25.13-alpine3.23 -> 1.26.10-alpine3.23 (minVersions: the 1.26 line) |
| dockerfile | `frontend.Dockerfile` | `gcr.io/distroless/static-debian12` | `static-debian12:nonroot` | `static-debian12:nonroot@sha256:afa5c872c891853ca7fcf1f12c3edb23f7eeef36189728842dd51042ff57f7ab` | base image refresh |
| dockerfile | `Dockerfile.copa` | `debian` | `debian:13-slim` | `debian:13-slim@sha256:f6b08b09a05725f9431502d3b5714f5c4576e82c1a84fa1debe0c24a7e0c3ec4` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| MEDIUM | CVE-2026-33997 | `github.com/docker/docker` | `v28.5.2+incompatible` | `29.3.1` | source (`trivy fs`): `go.mod` | needs-human: fix requires a bump beyond the `minor` policy |
| UNKNOWN | DLA-4845-1 | `ca-certificates` | `20250419~deb12u1` | `20250419~deb12u2` | image `copacetic-frontend` | Copa failed: #22 2.376 dpkg: error processing package ca-certificates (--install): |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `go.mod` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `copa` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `copa` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `copacetic-frontend` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `copacetic-frontend` | cooldown: v0.62.0 released 2 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | DLA-4792-1 | `tzdata` | `2026b-0+deb12u1` | `2026c-0+deb12u1` | image `copacetic-frontend` | Copa failed: #22 2.376 dpkg: error processing package ca-certificates (--install): |
| UNKNOWN | DLA-4854-1 | `tzdata` | `2026b-0+deb12u1` | `2026e-0+deb12u1` | image `copacetic-frontend` | Copa failed: #22 2.376 dpkg: error processing package ca-certificates (--install): |
| UNKNOWN | DLA-4867-1 | `tzdata` | `2026b-0+deb12u1` | `2026f-0+deb12u1` | image `copacetic-frontend` | Copa failed: #22 2.376 dpkg: error processing package ca-certificates (--install): |

### Upstream tests

✅ passed in 1.0 min — `make test CODECOV_OPTS=""`

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| copa | `patcher.local/copa:v0.15.0-patched.dev` | ✅ `--version` | no fixable OS packages |
| copacetic-frontend | `patcher.local/copacetic-frontend:v0.15.0-patched.dev` | - | failed: #22 2.376 dpkg: error processing package ca-certificates (--install): |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/copacetic.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |
| CVE-2026-78661 | `golang.org/x/net` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/net is not imported |
| CVE-2026-97045 | `golang.org/x/net` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/net is not imported |

### Notes

- github.com/docker/docker is frozen at v28.x `+incompatible` (moby moved to github.com/moby/moby/v2); CVEs fixed only in moby v29+ need upstream code changes and are tracked in vex/copacetic.yaml.
