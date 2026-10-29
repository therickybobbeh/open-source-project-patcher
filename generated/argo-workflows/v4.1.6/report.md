## ✅ argo-workflows `v4.1.6` — success

Upstream: https://github.com/argoproj/argo-workflows @ `43021573c5a3` (line `v4.1`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 2 / 4 / 1 | 0 / 1 / 1 / 1 | 4 | 0 |
| image `workflow-controller` | 0 / 1 / 2 / 0 | 0 / 0 / 0 / 0 | 3 | 0 |
| image `argocli` | 0 / 1 / 2 / 0 | 0 / 0 / 0 / 0 | 3 | 0 |
| image `argoexec` | 0 / 1 / 2 / 0 | 0 / 0 / 0 / 0 | 3 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `github.com/go-jose/go-jose/v4` | `v4.1.4` | `v4.1.6` | CVE-2026-116585, CVE-2026-116586, CVE-2026-116587 |
| yarn | `ui/yarn.lock` | `qs` | `6.16.0` | `6.16.1` | CVE-2026-110816 |
| dockerfile | `Dockerfile` | `golang` | `golang:1.26.10-alpine3.23` | `golang:1.26.10-alpine3.23@sha256:34414731924cf2263160f0021f5cf6e1807382d85248f7cb419d4187b96d5e43` | base image refresh |
| dockerfile | `Dockerfile` | `node` | `node:20-alpine` | `node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293` | base image refresh |
| dockerfile | `Dockerfile` | `gcr.io/distroless/static-debian13` | `static-debian13:latest@sha256:034df5c1737e8241f6ed6423a12e720ee0f6d6f088609ee172f98f6f2166ef5d` | `static-debian13:latest@sha256:15f8637509792e05b97d83451b0b6ccfa4abd548f997e406ac1e72c87fe1fa78` | base image refresh |
| dockerfile | `Dockerfile` | `gcr.io/distroless/static-debian13` | `static-debian13:latest@sha256:034df5c1737e8241f6ed6423a12e720ee0f6d6f088609ee172f98f6f2166ef5d` | `static-debian13:latest@sha256:15f8637509792e05b97d83451b0b6ccfa4abd548f997e406ac1e72c87fe1fa78` | base image refresh |
| dockerfile | `Dockerfile` | `gcr.io/distroless/static-debian13` | `static-debian13:latest@sha256:034df5c1737e8241f6ed6423a12e720ee0f6d6f088609ee172f98f6f2166ef5d` | `static-debian13:latest@sha256:15f8637509792e05b97d83451b0b6ccfa4abd548f997e406ac1e72c87fe1fa78` | base image refresh |
| dockerfile | `Dockerfile` | `registry.k8s.io/kubectl` | `kubectl:v1.36.3@sha256:6e4fce3c83651edb91b74bc67701c5cd263dd8aa3cd4254b1798d6425a5ab789` | `kubectl:v1.36.6@sha256:0650805141538d13ccbb6bb9e0dd647bc415bc002898357970211c4d47224396` | v1.36.3 -> v1.36.6 |
| dockerfile | `Dockerfile` | `alpine` | `alpine:3.24` | `alpine:3.24@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a` | base image refresh |
| dockerfile | `Dockerfile` | `alpine` | `alpine:3.24` | `alpine:3.24@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a` | base image refresh |
| dockerfile | `Dockerfile` | `alpine` | `alpine:3.24` | `alpine:3.24@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| HIGH | CVE-2024-45296 | `path-to-regexp` | `1.8.0` | `1.9.0, 0.1.10, 8.0.0, 3.3.0, 6.3.0` | source (`trivy fs`): `ui/yarn.lock` | still at 1.8.0 after 3 round(s) |
| MEDIUM | CVE-2026-41907 | `uuid` | `9.0.1` | `11.1.1, 12.0.1, 13.0.1` | source (`trivy fs`): `ui/yarn.lock` | needs-human: fix requires a bump beyond the `minor` policy |
| LOW | CVE-2026-24001 | `diff` | `5.1.0` | `8.0.3, 5.2.2, 4.0.4, 3.5.1` | source (`trivy fs`): `ui/yarn.lock` | still at 5.1.0 after 3 round(s) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `go.mod` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | source (`trivy fs`): `go.mod` | cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `workflow-controller` | in bundled artifact `usr/bin/workflow-controller` (not built from this source) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `workflow-controller` | in bundled artifact `usr/bin/workflow-controller` (not built from this source) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `argocli` | in bundled artifact `usr/bin/argo` (not built from this source) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `argocli` | in bundled artifact `usr/bin/argo` (not built from this source) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `argoexec` | in bundled artifact `usr/bin/argoexec` (not built from this source) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.60.0` | `0.62.0` | image `argoexec` | in bundled artifact `usr/bin/argoexec` (not built from this source) |

### Bumps that could not be applied

- `diff` → `5.2.2` in `ui/yarn.lock`: needs-human: yarn.lock has diff on majors [4, 5]; a yarn resolution would force all of them to 5.2.2
- `path-to-regexp` → `1.9.0` in `ui/yarn.lock`: needs-human: yarn.lock has path-to-regexp on majors [0, 1]; a yarn resolution would force all of them to 1.9.0

### Newer releases beyond the policy (not applied)

- `golang` → `1.27.3-alpine3.23` in `Dockerfile`: newer tag 1.27.3-alpine3.23 exists beyond the `patch` level for base images (set `level: minor` on this dockerfile ecosystem, or bump it in patches/)
- `registry.k8s.io/kubectl` → `v1.37.2` in `Dockerfile`: newer tag v1.37.2 exists beyond the `patch` level for base images (set `level: minor` on this dockerfile ecosystem, or bump it in patches/)

### Upstream tests

✅ passed in 12.4 min — `make ui/dist/app/index.html STATIC_FILES=false && go mod vendor && go build -mod=vendor ./... && env KUBECONFIG=/dev/null go run gotest.tools/gotestsum@v1.12.3 --junitfile junit.xml --format testname --rerun-fails=2 --rerun-fails-run-root-test --packages ./... -- -p 20 -timeout 30m -skip='^TestArtif`

Skipped tests (from `skips/argo-workflows.yaml`):

| Match | Reason | Owner | Expires |
|---|---|---|---|
| `^TestArtifactoryArtifactDriver_Load$` | Downloads https://github.com/argoproj/argo-workflows over the live network (failed with `unexpected EOF` after 33s); unrelated to dependency updates | platform-team | 2027-04-30 |

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| workflow-controller | `patcher.local/workflow-controller:v4.1.6-patched.dev` | ✅ `--help` | no fixable OS packages |
| argocli | `patcher.local/argocli:v4.1.6-patched.dev` | ✅ `version` | no fixable OS packages |
| argoexec | `patcher.local/argoexec:v4.1.6-patched.dev` | ✅ `--help` | no fixable OS packages |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/argo-workflows.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |
| CVE-2026-78661 | `golang.org/x/net` | vulnerable_code_not_in_execute_path | govulncheck (v1.9.0): golang.org/x/net is imported but the vulnerable function is never called |
| CVE-2026-97045 | `golang.org/x/net` | vulnerable_code_not_in_execute_path | govulncheck (v1.9.0): golang.org/x/net is imported but the vulnerable function is never called |

### Notes

- The argocli image embeds the UI (STATIC_FILES=true in its build stage); UI dependencies are patched through ui/yarn.lock.
