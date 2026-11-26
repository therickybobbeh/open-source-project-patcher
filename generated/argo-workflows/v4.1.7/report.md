## ✅ argo-workflows `v4.1.7` — success

Upstream: https://github.com/argoproj/argo-workflows @ `21748f1a8b8d` (line `v4.1`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 1 / 1 / 1 | 0 / 1 / 1 / 1 | 0 | 0 |
| image `workflow-controller` | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 1 | 0 |
| image `argocli` | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 1 | 0 |
| image `argoexec` | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 1 | 0 |
| image `argoexec-nonroot` | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 1 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `workflow-controller`: ✅ passes
- image `argocli`: ✅ passes
- image `argoexec`: ✅ passes
  - ⚠️ argoexec runs as root: give it a numeric non-root user (`user` on the recipe's image), or run it with runAsUser
- image `argoexec-nonroot`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| dockerfile | `Dockerfile` | `golang` | `golang:1.26.10-alpine3.23` | `golang:1.26.11-alpine3.23@sha256:23f198931d4bd83b4f5a613bd75656257ae8bf832dcbc2db80e1050b5219ca2a` | 1.26.10-alpine3.23 -> 1.26.11-alpine3.23 |
| dockerfile | `Dockerfile` | `node` | `node:20-alpine` | `node:24-alpine@sha256:116b800c3754b440ee0aa3ed2f20f5bf3d99a554bfd9adeea09ea8017f6e85f5` | 20-alpine -> 24-alpine (minVersions: the 24 line) |
| dockerfile | `Dockerfile` | `gcr.io/distroless/static-debian13` | `static-debian13:latest@sha256:034df5c1737e8241f6ed6423a12e720ee0f6d6f088609ee172f98f6f2166ef5d` | `static-debian13:latest@sha256:4c2cd1dee442c9a99924a378c7c126fac8fef14771579ef567c3f2bdd7a5122a` | base image refresh |
| dockerfile | `Dockerfile` | `gcr.io/distroless/static-debian13` | `static-debian13:latest@sha256:034df5c1737e8241f6ed6423a12e720ee0f6d6f088609ee172f98f6f2166ef5d` | `static-debian13:latest@sha256:4c2cd1dee442c9a99924a378c7c126fac8fef14771579ef567c3f2bdd7a5122a` | base image refresh |
| dockerfile | `Dockerfile` | `gcr.io/distroless/static-debian13` | `static-debian13:latest@sha256:034df5c1737e8241f6ed6423a12e720ee0f6d6f088609ee172f98f6f2166ef5d` | `static-debian13:latest@sha256:4c2cd1dee442c9a99924a378c7c126fac8fef14771579ef567c3f2bdd7a5122a` | base image refresh |
| dockerfile | `Dockerfile` | `registry.k8s.io/kubectl` | `kubectl:v1.36.3@sha256:6e4fce3c83651edb91b74bc67701c5cd263dd8aa3cd4254b1798d6425a5ab789` | `kubectl:v1.36.7@sha256:3f2cf571aa96e47b5df0c4770aef92322e9c6542ca8c3c412a5cb6c108a24ecc` | v1.36.3 -> v1.36.7 |
| dockerfile | `Dockerfile` | `alpine` | `alpine:3.24` | `alpine:3.24@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf` | base image refresh |
| dockerfile | `Dockerfile` | `alpine` | `alpine:3.24` | `alpine:3.24@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf` | base image refresh |
| dockerfile | `Dockerfile` | `alpine` | `alpine:3.24` | `alpine:3.24@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| HIGH | CVE-2024-45296 | `path-to-regexp` | `1.8.0` | `1.9.0, 0.1.10, 8.0.0, 3.3.0, 6.3.0` | source (`trivy fs`): `ui/yarn.lock` | bump failed: needs-human: yarn.lock has path-to-regexp on majors [0, 1]; a yarn resolution would force all of them to 1.9.0 |
| MEDIUM | CVE-2026-41907 | `uuid` | `9.0.1` | `11.1.1, 12.0.1, 13.0.1` | source (`trivy fs`): `ui/yarn.lock` | needs-human: fix requires a bump beyond the `minor` policy |
| LOW | CVE-2026-24001 | `diff` | `5.1.0` | `8.0.3, 5.2.2, 4.0.4, 3.5.1` | source (`trivy fs`): `ui/yarn.lock` | bump failed: needs-human: yarn.lock has diff on majors [4, 5]; a yarn resolution would force all of them to 5.2.2 |

### Bumps that could not be applied

- `diff` → `5.2.2` in `ui/yarn.lock`: needs-human: yarn.lock has diff on majors [4, 5]; a yarn resolution would force all of them to 5.2.2
- `path-to-regexp` → `1.9.0` in `ui/yarn.lock`: needs-human: yarn.lock has path-to-regexp on majors [0, 1]; a yarn resolution would force all of them to 1.9.0

### Newer releases beyond the policy (not applied)

- `golang` → `1.27.4-alpine3.23` in `Dockerfile`: newer tag 1.27.4-alpine3.23 exists beyond the `patch` level for base images (set `level: minor` on this dockerfile ecosystem, or bump it in patches/)
- `registry.k8s.io/kubectl` → `v1.37.3` in `Dockerfile`: newer tag v1.37.3 exists beyond the `patch` level for base images (set `level: minor` on this dockerfile ecosystem, or bump it in patches/)

### Upstream tests

✅ passed in 12.6 min — `make ui/dist/app/index.html STATIC_FILES=false && go mod vendor && go build -mod=vendor ./... && env KUBECONFIG=/dev/null go run gotest.tools/gotestsum@v1.12.3 --junitfile junit.xml --format testname --rerun-fails=2 --rerun-fails-run-root-test --packages ./... -- -p 20 -timeout 30m -skip='^TestArtif`

Skipped tests (from `skips/argo-workflows.yaml`):

| Match | Reason | Owner | Expires |
|---|---|---|---|
| `^TestArtifactoryArtifactDriver_Load$` | Downloads https://github.com/argoproj/argo-workflows over the live network (failed with `unexpected EOF` after 33s); unrelated to dependency updates | platform-team | 2027-04-30 |

### Images

| Image | Ref | Runs as | Smoke | Copa |
|---|---|---|---|---|
| workflow-controller | `patcher.local/workflow-controller:v4.1.7-patched.dev` | `8737` | ✅ `--help` | no fixable OS packages |
| argocli | `patcher.local/argocli:v4.1.7-patched.dev` | `8737` | ✅ `version` | no fixable OS packages |
| argoexec | `patcher.local/argoexec:v4.1.7-patched.dev` | `0` (root) | ✅ `--help` | no fixable OS packages |
| argoexec-nonroot | `patcher.local/argoexec:v4.1.7-nonroot-patched.dev` | `8737` | ✅ `--help` | no fixable OS packages |

### Notes

- The argocli image embeds the UI (STATIC_FILES=true in its build stage); UI dependencies are patched through ui/yarn.lock.
