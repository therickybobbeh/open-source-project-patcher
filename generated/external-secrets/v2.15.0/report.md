## ✅ external-secrets `v2.15.0` — success

Upstream: https://github.com/external-secrets/external-secrets @ `b872cf4b508f` (line `v2`)

> **Upgrade:** `v2.14.0` → `v2.15.0`, a minor release ([release notes](https://github.com/external-secrets/external-secrets/releases/tag/v2.15.0)). The daily merge round leaves it for a person: merge it by hand once you've read what changed.

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |
| image `external-secrets` | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 1 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `external-secrets`: ✅ passes

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/acr/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/beyondtrustworkloadcredentials/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/cloudsmith/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/gcr/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/quay/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/sshkey/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/vault/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/webhook/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/akeyless/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/aws/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/azure/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/beyondtrust/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/beyondtrustworkloadcredentials/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/bitwarden/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/chef/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/cloudru/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/conjur/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/crd/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/delinea/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/doppler/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/dvls/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/fake/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/fortanix/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/gcp/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/github/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/gitlab/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/ibm/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/infisical/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/keepersecurity/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/kubernetes/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/nebius/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/onboardbase/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/onepassword/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/onepasswordsdk/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/openbao/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/oracle/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/ovh/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/passbolt/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/passworddepot/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/pulumi/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/scaleway/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/secretserver/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/senhasegura/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/vault/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/volcengine/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/webhook/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `runtime/go.mod` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `external-secrets` | cooldown: v0.59.0 released 2 day(s) ago (eligible 2026-11-18) |

### Upstream tests

✅ passed in 12.5 min — `make test`

### Images

| Image | Ref | Runs as | Smoke | Copa |
|---|---|---|---|---|
| external-secrets | `patcher.local/external-secrets:v2.15.0-patched.dev` | `65534` | ✅ `--help` | no fixable OS packages |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/external-secrets.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |

### Notes

- Upstream publishes release images by promoting main-branch builds; ours are built from the release tag.
- Never build Dockerfile.standalone; it compiles without `-tags all_providers` and ships no providers.
- No dependency bumps: this patch set is a rebuild of upstream's source, whose image(s) fix 1 finding(s) that upstream's have.
