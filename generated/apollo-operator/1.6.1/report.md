## ✅ apollo-operator `1.6.1` — success

Upstream: https://hub.docker.com/r/apollograph/operator @ `n/a` (line `v1`)

> **Not published** (`publish: false` in the recipe): merging records this patch set, but the release workflow pushes no image for this recipe.

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | n/a | n/a | 0 | 0 |
| image `apollo-operator 1.6.1` | 0 / 35 / 27 / 3 | 0 / 4 / 9 / 1 | 52 | 0 |
| image `apollo-bundle-loader 0.4.3` | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| HIGH | CVE-2026-111943 | `stdlib` | `v1.25.14` | `1.26.10, 1.27.3` | image `apollo-operator 1.6.1` | component `docker-credential-ecr-login` (rebuilt from source): not fixed there, see `components/docker-credential-ecr-login/report.md` |
| HIGH | CVE-2026-78667 | `stdlib` | `v1.25.14` | `1.26.9, 1.27.2` | image `apollo-operator 1.6.1` | component `docker-credential-ecr-login` (rebuilt from source): not fixed there, see `components/docker-credential-ecr-login/report.md` |
| HIGH | CVE-2026-78669 | `stdlib` | `v1.25.14` | `1.26.9, 1.27.2` | image `apollo-operator 1.6.1` | component `docker-credential-ecr-login` (rebuilt from source): not fixed there, see `components/docker-credential-ecr-login/report.md` |
| HIGH | CVE-2026-97031 | `stdlib` | `v1.25.14` | `1.26.9, 1.27.2` | image `apollo-operator 1.6.1` | component `docker-credential-ecr-login` (rebuilt from source): not fixed there, see `components/docker-credential-ecr-login/report.md` |
| MEDIUM | CVE-2026-56866 | `stdlib` | `v1.25.14` | `1.26.9, 1.27.2` | image `apollo-operator 1.6.1` | component `docker-credential-ecr-login` (rebuilt from source): not fixed there, see `components/docker-credential-ecr-login/report.md` |
| MEDIUM | CVE-2026-78659 | `stdlib` | `v1.25.14` | `1.26.9, 1.27.2` | image `apollo-operator 1.6.1` | component `docker-credential-ecr-login` (rebuilt from source): not fixed there, see `components/docker-credential-ecr-login/report.md` |
| MEDIUM | CVE-2026-78660 | `stdlib` | `v1.25.14` | `1.26.9, 1.27.2` | image `apollo-operator 1.6.1` | component `docker-credential-ecr-login` (rebuilt from source): not fixed there, see `components/docker-credential-ecr-login/report.md` |
| MEDIUM | CVE-2026-78663 | `stdlib` | `v1.25.14` | `1.26.9, 1.27.2` | image `apollo-operator 1.6.1` | component `docker-credential-ecr-login` (rebuilt from source): not fixed there, see `components/docker-credential-ecr-login/report.md` |
| MEDIUM | CVE-2026-94439 | `stdlib` | `v1.25.14` | `1.26.9, 1.27.2` | image `apollo-operator 1.6.1` | component `docker-credential-ecr-login` (rebuilt from source): not fixed there, see `components/docker-credential-ecr-login/report.md` |
| MEDIUM | CVE-2026-94440 | `stdlib` | `v1.25.14` | `1.26.9, 1.27.2` | image `apollo-operator 1.6.1` | component `docker-credential-ecr-login` (rebuilt from source): not fixed there, see `components/docker-credential-ecr-login/report.md` |
| MEDIUM | CVE-2026-94448 | `stdlib` | `v1.25.14` | `1.26.9, 1.27.2` | image `apollo-operator 1.6.1` | component `docker-credential-ecr-login` (rebuilt from source): not fixed there, see `components/docker-credential-ecr-login/report.md` |
| MEDIUM | CVE-2026-97030 | `stdlib` | `v1.25.14` | `1.26.9, 1.27.2` | image `apollo-operator 1.6.1` | component `docker-credential-ecr-login` (rebuilt from source): not fixed there, see `components/docker-credential-ecr-login/report.md` |
| MEDIUM | CVE-2026-97032 | `stdlib` | `v1.25.14` | `1.26.9, 1.27.2` | image `apollo-operator 1.6.1` | component `docker-credential-ecr-login` (rebuilt from source): not fixed there, see `components/docker-credential-ecr-login/report.md` |
| LOW | CVE-2026-56857 | `stdlib` | `v1.25.14` | `1.26.9, 1.27.2` | image `apollo-operator 1.6.1` | component `docker-credential-ecr-login` (rebuilt from source): not fixed there, see `components/docker-credential-ecr-login/report.md` |

### Upstream tests

Not run.

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| apollo-operator 1.6.1 | `docker.io/apollograph/operator:1.6.1` | - | no fixable OS packages |
| apollo-bundle-loader 0.4.3 | `docker.io/apollograph/bundle-loader:0.4.3` | - | no fixable OS packages |

### Bundled components (rebuilt from source and swapped in)

| Image | Component | Path | Version | Status | Bumps | Tests | Notes |
|---|---|---|---|---|---|---|---|
| apollo-operator | docker-credential-ecr-login | `/usr/bin/docker-credential-ecr-login` | 0.12.0 | success | 2 | passed | version from `/usr/bin/docker-credential-ecr-login version` |
| apollo-operator | docker-credential-gcr | `/usr/bin/docker-credential-gcr` | 2.2.1 | no-changes | 0 | passed | version from Go build info |

### Notes

- The images have no OS package database, so Copa has nothing to patch. The credential helpers are rebuilt and swapped in (components); findings in the closed-source operator binary are reported and tracked in vex/apollo-operator.yaml until the vendor releases fixes.
- To run a patched Apollo Router under the operator, set `spec.deployment.podTemplate.image` on the Supergraph to the apollo-router image from this repo.
