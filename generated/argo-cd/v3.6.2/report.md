## ✅ argo-cd `v3.6.2` — success

Upstream: https://github.com/argoproj/argo-cd @ `8e8268ef2f3d` (line `v3.6`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 11 / 15 / 0 | 0 / 2 / 2 / 0 | 23 | 0 |
| image `argocd` | 0 / 20 / 30 / 2 | 0 / 0 / 1 / 0 | 53 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `argocd`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `go.opentelemetry.io/otel/sdk` | `v1.46.0` | `v1.47.0` | CVE-2026-128085 |
| gomod | `go.mod` | `go.opentelemetry.io/otel/trace` | `v1.46.0` | `v1.47.0` | CVE-2026-128085 |
| gomod | `go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.59.0` | GO-2026-5932 |
| gomod | `gitops-engine/go.mod` | `go.opentelemetry.io/otel/trace` | `v1.44.0` | `v1.47.0` | CVE-2026-128085 |
| gomod | `gitops-engine/go.mod` | `golang.org/x/net` | `v0.57.0` | `v0.62.0` | CVE-2026-78659, CVE-2026-78660, CVE-2026-78661, CVE-2026-78663, CVE-2026-78669, CVE-2026-97032, CVE-2026-97045 |
| gomod | `gitops-engine/go.mod` | `golang.org/x/text` | `v0.40.0` | `v0.41.0` | CVE-2026-56851 |
| pnpm | `ui/pnpm-lock.yaml` | `brace-expansion` | `1.1.14` | `1.1.21` | CVE-2026-102276, CVE-2026-102277, CVE-2026-102278, CVE-2026-13149, CVE-2026-14257, CVE-2026-69152 |
| pnpm | `ui/pnpm-lock.yaml` | `brace-expansion` | `2.1.0` | `2.1.7` | CVE-2026-102276, CVE-2026-102277, CVE-2026-102278, CVE-2026-13149, CVE-2026-14257, CVE-2026-69152 |
| pnpm | `ui/pnpm-lock.yaml` | `form-data` | `4.0.5` | `4.0.6` | CVE-2026-12143 |
| pnpm | `ui/pnpm-lock.yaml` | `moment` | `2.30.1` | `2.31.0` | CVE-2026-17495 |
| pnpm | `ui/pnpm-lock.yaml` | `qs` | `6.15.2` | `6.16.1` | CVE-2026-110816, CVE-2026-82417, CVE-2026-82562 |
| pnpm | `ui/pnpm-lock.yaml` | `source-map-js` | `1.2.1` | `1.2.2` | CVE-2026-93749 |
| dockerfile | `Dockerfile` | `docker.io/library/golang` | `golang:1.27.4@sha256:08bcb99a38f85a265f9a93d1d3323e2440eec333380f3ea26ee0dec9264bb41c` | `golang:1.27.4@sha256:205c7636d74e0ffbe3d007162df7d74f859f5a8c8322dfb9f907977686c126cf` | base image refresh |
| dockerfile | `Dockerfile` | `ARG BASE_IMAGE` | `ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b` | `ubuntu:26.04@sha256:d66b366dac61b575bee2aef07e9c26e8070096fbe84a3d4d3eb0da069b5d76db` | base image refresh |
| dockerfile | `Dockerfile` | `docker.io/library/node` | `node:24.17.0@sha256:032e78d7e54e352129831743737e3a83171d9cc5b5896f411649c597ce0b11ea` | `node:24.17.0@sha256:733e1c06ada118ed9f6133a31aa1290be6929664026fb28821500437c61f2c6f` | base image refresh |
| dockerfile | `Dockerfile` | `docker.io/library/golang` | `golang:1.27.4@sha256:08bcb99a38f85a265f9a93d1d3323e2440eec333380f3ea26ee0dec9264bb41c` | `golang:1.27.4@sha256:205c7636d74e0ffbe3d007162df7d74f859f5a8c8322dfb9f907977686c126cf` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| HIGH | CVE-2026-48801 | `linkify-it` | `3.0.3` | `5.0.1` | source (`trivy fs`): `ui/pnpm-lock.yaml` | needs-human: fix requires a bump beyond the `minor` policy |
| HIGH | CVE-2026-59887 | `linkify-it` | `3.0.3` | `5.0.2` | source (`trivy fs`): `ui/pnpm-lock.yaml` | needs-human: fix requires a bump beyond the `minor` policy |
| MEDIUM | CVE-2026-118764 | `minimatch` | `9.0.9` | `11.0.1` | source (`trivy fs`): `ui/pnpm-lock.yaml` | needs-human: fix requires a bump beyond the `minor` policy |
| MEDIUM | CVE-2026-97054 | `stdlib` | `v1.27.3` | `1.26.11, 1.27.4` | image `argocd` | in bundled artifact `usr/bin/pebble` (not built from this source) |
| MEDIUM | CVE-2026-41907 | `uuid` | `9.0.1` | `11.1.1, 12.0.1, 13.0.1` | source (`trivy fs`): `ui/pnpm-lock.yaml` | needs-human: fix requires a bump beyond the `minor` policy |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `argocd` | component `helm` (rebuilt from source): needs-human: fix requires a bump beyond the `patch` policy |

### Newer releases beyond the policy (not applied)

- `docker.io/library/node` → `24.22.3` in `Dockerfile`: newer tag 24.22.3 exists beyond the `patch` level for base images (set `level: minor` on this dockerfile ecosystem, or bump it in patches/)

### Upstream tests

✅ passed in 8.8 min — `make test-local`

Skipped tests (from `skips/argo-cd.yaml`):

| Match | Reason | Owner | Expires |
|---|---|---|---|
| `^TestIndex$` | Downloads the live argo-helm index (argoproj.github.io); fails on network flakes, unrelated to dependency updates | platform-team | 2027-04-30 |
| `^Test_nativeHelmChart_ExtractChart$` | Pulls a chart from the live argo-helm repository | platform-team | 2027-04-30 |
| `^TestVerifyCommitSignature$` | Fetches the whole argo-cd repository with tags from GitHub (util/git); timed out after 90s on 2026-11-03 while the unpatched baseline's fetch made it, unrelated to dependency updates | platform-team | 2027-04-30 |

### Images

| Image | Ref | Runs as | Smoke | Copa |
|---|---|---|---|---|
| argocd | `patcher.local/argocd:v3.6.2-patched.dev` | `999` | ✅ `argocd version --client` | no fixable OS packages |

### Bundled components (rebuilt from source and swapped in)

| Image | Component | Path | Version | Status | Bumps | Tests | Notes |
|---|---|---|---|---|---|---|---|
| argocd | helm | `/usr/local/bin/helm` | 4.3.2 | success | 1 | passed | version from hack/tool-versions.sh |
| argocd | kustomize | `/usr/local/bin/kustomize` | 5.8.3 | no-changes | 0 | passed | version from hack/tool-versions.sh |
| argocd | git-lfs | `/usr/local/bin/git-lfs` | 3.8.1 | success | 4 | passed | version from hack/tool-versions.sh |

### Notes

- helm, kustomize and git-lfs are rebuilt from source at the versions in hack/tool-versions.sh (components); moving to a newer tool version still needs a patch that updates tool-versions.sh and hack/installers/checksums/.
- End-to-end tests (k3s cluster) are not part of `make test-local` and are not run.
- brace-expansion 3.0.3 was withdrawn by its registry (contains bloat files); 3.0.4 considered instead
