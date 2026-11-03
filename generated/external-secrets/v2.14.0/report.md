## ✅ external-secrets `v2.14.0` — success

Upstream: https://github.com/external-secrets/external-secrets @ `e932f3a3f6f2` (line `v2`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 47 | 0 |
| image `external-secrets` | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 1 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `external-secrets`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `runtime/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/akeyless/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/aws/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/azure/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/beyondtrust/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/beyondtrustworkloadcredentials/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/bitwarden/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/chef/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/cloudru/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/conjur/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/crd/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/delinea/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/doppler/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/dvls/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/fake/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/fortanix/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/gcp/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/github/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/gitlab/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/ibm/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/infisical/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/keepersecurity/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/kubernetes/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/nebius/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/onboardbase/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/onepassword/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/onepasswordsdk/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/openbao/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/oracle/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/ovh/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/passbolt/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/passworddepot/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/pulumi/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/scaleway/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/secretserver/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/vault/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/volcengine/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `providers/v1/webhook/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `generators/v1/acr/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `generators/v1/beyondtrustworkloadcredentials/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `generators/v1/cloudsmith/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `generators/v1/gcr/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `generators/v1/quay/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `generators/v1/sshkey/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `generators/v1/vault/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |
| gomod | `generators/v1/webhook/go.mod` | `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` | GO-2026-5932 |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `apis/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `apis/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/acr/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/acr/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/beyondtrustworkloadcredentials/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/beyondtrustworkloadcredentials/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/cloudsmith/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/cloudsmith/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/ecr/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/ecr/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/fake/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/fake/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/gcr/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/gcr/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/github/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/github/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/gitlab/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/gitlab/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/grafana/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/grafana/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/mfa/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/mfa/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/password/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/password/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/quay/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/quay/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/sshkey/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/sshkey/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/sts/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/sts/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/uuid/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/uuid/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/vault/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/vault/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/webhook/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `generators/v1/webhook/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/akeyless/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/akeyless/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/aws/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/aws/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/azure/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/azure/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/barbican/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/barbican/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/beyondtrust/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/beyondtrust/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/beyondtrustworkloadcredentials/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/beyondtrustworkloadcredentials/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/bitwarden/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/bitwarden/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/chef/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/chef/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/cloudru/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/cloudru/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/conjur/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/conjur/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-78661 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/crd/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| UNKNOWN | CVE-2026-97045 | `golang.org/x/net` | `v0.61.0` | `0.62.0` | source (`trivy fs`): `providers/v1/crd/go.mod` | cooldown: v0.62.0 released 6 day(s) ago (eligible 2026-11-03) |
| | | | | | | 66 more in `summary.json` |

### Upstream tests

✅ passed in 12.1 min — `make test`

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| external-secrets | `patcher.local/external-secrets:v2.14.0-patched.dev` | ✅ `--help` | no fixable OS packages |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/external-secrets.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| CVE-2026-78661 | `golang.org/x/net` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/net is not imported |
| CVE-2026-97045 | `golang.org/x/net` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/net is not imported |

### Notes

- Upstream publishes release images by promoting main-branch builds; ours are built from the release tag.
- Never build Dockerfile.standalone; it compiles without `-tags all_providers` and ships no providers.
