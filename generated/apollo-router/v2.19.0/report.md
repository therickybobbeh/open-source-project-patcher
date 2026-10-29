## ✅ apollo-router `v2.19.0` — success

Upstream: https://github.com/apollographql/router @ `95383e1e952e` (line `v2`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 2 / 2 / 1 | 0 / 0 / 1 / 0 | 4 | 0 |
| image `router` | 0 / 2 / 8 / 2 | 0 / 0 / 0 / 0 | 13 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| cargo | `Cargo.lock` | `cmov` | `0.5.3` | `0.5.4` | CVE-2026-50185 |
| cargo | `Cargo.lock` | `quinn-proto` | `0.11.12` | `0.11.15` | CVE-2026-31812, GHSA-4w2j-m93h-cj5j |
| cargo | `Cargo.lock` | `rand` | `0.8.5` | `0.8.6` | GHSA-cq8v-f236-94qc |
| cargo | `Cargo.lock` | `rand` | `0.9.2` | `0.9.3` | GHSA-cq8v-f236-94qc |
| dockerfile | `dockerfiles/diy/dockerfiles/Dockerfile.repo` | `rust` | `rust:1.99.0-slim-bookworm` | `rust:1.99.1-slim-bookworm@sha256:24707e70a4f1e23d9a7b25202ec43126d28a52294b96aad5c670df1fd1f1d400` | 1.99.0-slim-bookworm -> 1.99.1-slim-bookworm |
| dockerfile | `dockerfiles/diy/dockerfiles/Dockerfile.repo` | `debian` | `debian:bookworm-slim` | `debian:bookworm-slim@sha256:99c0b25c46d0214d5a2091092e7908907dcaecd6a962cde0ac700acee222b6f3` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| MEDIUM | CVE-2026-48504 | `opentelemetry_sdk` | `0.31.0` | `0.32.1` | source (`trivy fs`): `Cargo.lock` | needs-human: fix requires a bump beyond the `minor` policy |

### Upstream tests

✅ passed in 16.0 min — `cargo nextest run --locked --no-fail-fast --workspace --features ci,snapshot --profile ci -E 'not ((test(/integration::connectors::authentication::test_aws_sig_v4_signing$/)))'`

Skipped tests (from `skips/apollo-router.yaml`):

| Match | Reason | Owner | Expires |
|---|---|---|---|
| `integration::connectors::authentication::test_aws_sig_v4_signing$` | Calls live AWS (STS AssumeRole, then a SigV4-signed EC2 DescribeInstances) with upstream CI's role (AWS_ROLE_ARN); see tests/integration/fixtures/connectors_sigv4.router.yaml. Fails the same on the unpatched source | platform-team | 2027-04-30 |

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| router | `patcher.local/router:v2.19.0-patched.dev` | ✅ `--version` | no fixable OS packages |

### Notes

- GraphOS-licensed integration tests (entity cache, APQ, reporting) return early without TEST_APOLLO_KEY / TEST_APOLLO_GRAPH_REF, so they pass without exercising anything.
- The DIY image's entrypoint is /dist/router_wrapper.sh; config path and user match the official image.
