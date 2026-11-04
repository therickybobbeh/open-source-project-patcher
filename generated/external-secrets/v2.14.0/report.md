## ✅ external-secrets `v2.14.0` — success

Upstream: https://github.com/external-secrets/external-secrets @ `e932f3a3f6f2` (line `v2`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 124 | 0 |
| image `external-secrets` | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 2 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `external-secrets`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| gomod | `go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `apis/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `runtime/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/akeyless/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/aws/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/azure/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/barbican/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/beyondtrust/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/beyondtrustworkloadcredentials/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/bitwarden/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/chef/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/cloudru/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/conjur/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/crd/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/delinea/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/doppler/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/dvls/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/fake/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/fortanix/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/gcp/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/github/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/gitlab/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/ibm/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/infisical/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/keepersecurity/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/kubernetes/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/nebius/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/ngrok/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/onboardbase/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/onepassword/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/onepasswordsdk/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/openbao/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/oracle/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/ovh/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/passbolt/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/passworddepot/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/previder/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/pulumi/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/scaleway/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/secretserver/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/senhasegura/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/vault/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/volcengine/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/webhook/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `providers/v1/yandex/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `generators/v1/acr/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `generators/v1/beyondtrustworkloadcredentials/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `generators/v1/cloudsmith/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `generators/v1/ecr/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `generators/v1/fake/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `generators/v1/gcr/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `generators/v1/github/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `generators/v1/gitlab/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `generators/v1/grafana/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `generators/v1/mfa/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `generators/v1/password/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `generators/v1/quay/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `generators/v1/sshkey/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `generators/v1/sts/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| gomod | `generators/v1/uuid/go.mod` | `golang.org/x/net` | `v0.61.0` | `v0.62.0` | CVE-2026-78661, CVE-2026-97045 |
| … | | | | | 2 more in `bump-plan.json` |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/acr/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/beyondtrustworkloadcredentials/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/cloudsmith/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/gcr/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/quay/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/sshkey/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/vault/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `generators/v1/webhook/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/akeyless/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/aws/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/azure/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/beyondtrust/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/beyondtrustworkloadcredentials/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/bitwarden/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/chef/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/cloudru/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/conjur/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/crd/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/delinea/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/doppler/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/dvls/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/fake/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/fortanix/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/gcp/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/github/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/gitlab/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/ibm/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/infisical/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/keepersecurity/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/kubernetes/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/nebius/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/onboardbase/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/onepassword/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/onepasswordsdk/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/openbao/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/oracle/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/ovh/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/passbolt/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/passworddepot/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/pulumi/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/scaleway/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/secretserver/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/vault/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/volcengine/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `providers/v1/webhook/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | source (`trivy fs`): `runtime/go.mod` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `external-secrets` | untagged: the fix (0.58.1-0.20261009181718-2f1f834330b2) is a commit, not a release; the first tagged release after it is applied once there is one |

### Upstream tests

✅ passed in 10.2 min — `make test`

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| external-secrets | `patcher.local/external-secrets:v2.14.0-patched.dev` | ✅ `--help` | no fixable OS packages |

### VEX suggestions (govulncheck reachability)

Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/external-secrets.yaml`.

| Vulnerability | Package | Suggested | Evidence |
|---|---|---|---|
| GO-2026-5932 | `golang.org/x/crypto` | vulnerable_code_not_present | govulncheck (v1.9.0): the vulnerable package of golang.org/x/crypto is not imported |

### Notes

- Upstream publishes release images by promoting main-branch builds; ours are built from the release tag.
- Never build Dockerfile.standalone; it compiles without `-tags all_providers` and ships no providers.
