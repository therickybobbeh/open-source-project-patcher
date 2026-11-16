## ✅ apollo-router `v2.19.1` — success

Upstream: https://github.com/apollographql/router @ `c8843a46d657` (line `v2`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 2 / 2 / 1 | 0 / 0 / 1 / 0 | 4 | 0 |
| image `router` | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `router`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| cargo | `Cargo.lock` | `cmov` | `0.5.3` | `0.5.4` | CVE-2026-50185 |
| cargo | `Cargo.lock` | `quinn-proto` | `0.11.12` | `0.11.15` | CVE-2026-31812, GHSA-4w2j-m93h-cj5j |
| cargo | `Cargo.lock` | `rand` | `0.8.5` | `0.8.6` | GHSA-cq8v-f236-94qc |
| cargo | `Cargo.lock` | `rand` | `0.9.2` | `0.9.3` | GHSA-cq8v-f236-94qc |
| dockerfile | `dockerfiles/diy/dockerfiles/Dockerfile.repo` | `rust` | `rust:1.99.0-slim-bookworm` | `rust:1.99.1-slim-bookworm@sha256:f2c004e3d2d8b547e8cf7ffbc29205385f4e71d23e53e4e383065db5e9f822cd` | 1.99.0-slim-bookworm -> 1.99.1-slim-bookworm |
| dockerfile | `dockerfiles/diy/dockerfiles/Dockerfile.repo` | `debian` | `debian:bookworm-slim` | `debian:bookworm-slim@sha256:734a72b3d6142a71993b4bc580ca01d8ca687f77a2c422d96a961d3376b179bc` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| MEDIUM | CVE-2026-48504 | `opentelemetry_sdk` | `0.31.0` | `0.32.1` | source (`trivy fs`): `Cargo.lock` | needs-human: fix requires a bump beyond the `minor` policy |

### Newer releases beyond the policy (not applied)

- `rust` → `1.100.0-slim-bookworm` in `dockerfiles/diy/dockerfiles/Dockerfile.repo`: newer tag 1.100.0-slim-bookworm exists beyond the `patch` level for base images (set `level: minor` on this dockerfile ecosystem, or bump it in patches/)

### Upstream tests

✅ passed in 10.1 min — `cargo nextest run --locked --no-fail-fast --workspace --features ci,snapshot --profile ci -E 'not ((test(/integration::connectors::authentication::test_aws_sig_v4_signing$/)))'`

Skipped tests (from `skips/apollo-router.yaml`):

| Match | Reason | Owner | Expires |
|---|---|---|---|
| `integration::connectors::authentication::test_aws_sig_v4_signing$` | Calls live AWS (STS AssumeRole, then a SigV4-signed EC2 DescribeInstances) with upstream CI's role (AWS_ROLE_ARN); see tests/integration/fixtures/connectors_sigv4.router.yaml. Fails the same on the unpatched source | platform-team | 2027-04-30 |

### Images

| Image | Ref | Runs as | Smoke | Copa |
|---|---|---|---|---|
| router | `patcher.local/router:v2.19.1-patched.dev` | `1000:1000` | ✅ `--version` | no fixable OS packages |

### Notes

- GraphOS-licensed integration tests (entity cache, APQ, reporting) return early without TEST_APOLLO_KEY / TEST_APOLLO_GRAPH_REF, so they pass without exercising anything.
- The DIY image's entrypoint is /dist/router_wrapper.sh; config path and user match the official image.
