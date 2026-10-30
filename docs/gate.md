# Release gate

The release gate decides whether an image may be released with what it still contains. Its rules are
[Rego](https://www.openpolicyagent.org/docs/latest/policy-language/) in [`policy/`](../policy). The patcher evaluates
them with [conftest](https://www.conftest.dev/), the Open Policy Agent CLI for policies over files, on each image's
final scan: after the rebuild, the bundled-tool and jar swaps, and Copa.

| Where | What happens |
|---|---|
| Patch PR | A **Release gate** section in the report shows whether the release would pass, and why not. With `enforce`, a PR whose release would stop opens as a draft. |
| Release (`publish`), Copa refresh | The verdict goes into the release record, which the `state/` PR shows. With `enforce`, a denied image stops the release before it is signed: nothing is signed, promoted or recorded, and the run fails (a CI alert). |

## Settings

In [`recipes/_global.yaml`](../recipes/_global.yaml), with any field overridden per recipe:

```yaml
gate:
  enforce: false          # true: a denied release stops; false: the verdict is only reported
  failOn:
    fixable: [CRITICAL]   # severities of findings that have a fix released but are still in the image
    unfixed: []           # severities of findings with no fix released yet
```

| You want | Set |
|---|---|
| Report only, to see what would fail (the default) | `enforce: false` |
| Stop a release on a fixable CRITICAL | `enforce: true`, `failOn.fixable: [CRITICAL]` |
| Stop on highs too | `failOn.fixable: [CRITICAL, HIGH]` |
| Also stop on CRITICALs nobody can fix yet | `failOn.unfixed: [CRITICAL]` |
| Stricter for one recipe | `gate: {enforce: true, failOn: {fixable: [CRITICAL, HIGH]}}` in that recipe |

**What counts:**
- Findings a VEX statement in `vex/<recipe>.yaml` settles, with status `not_affected` or `fixed`, never fail the gate.
  That is how a reviewed exception is recorded: with its justification, an expiry, and the OpenVEX document every
  release carries.
- An `affected` or `under_investigation` statement doesn't settle a finding.
- Everything else in the image's scan counts, bundled third-party binaries included: the gate judges the image people
  run, not only the code we rebuild.

**Rolling it out:** keep `enforce: false` for a while and read the gate sections in the PRs. Then turn `enforce` on,
first for the recipes that already pass. A gate that stops a release also stops a *better* image: the one released
before stays current. Fix the finding, or record a VEX decision, rather than leave a line stuck.

## Rules of your own

Every `.rego` file in `policy/` with `package patcher.gate` adds to the gate:
- each `deny` message fails it;
- each `warn` message is only reported.

For example, a rule that stops any image with a finding in OpenSSL whose fix is out:

```rego
package patcher.gate

deny contains msg if {
	some f in open
	f.package == "openssl"
	f.fixable
	msg := sprintf("OpenSSL %s %s is fixable (fixed in %s)", [f.id, f.installed, f.fixed])
}
```

`open` is the policy's set of findings no VEX statement settles. Test your rules next to
[`gate_test.rego`](../policy/gate_test.rego), then run:

```bash
conftest verify --policy policy   # the Rego tests; CI runs them, with `conftest fmt --check policy`
```

## Input

One document per image:

```json
{
  "stage": "release",
  "recipe": "argo-cd", "line": "v3.4", "image": "argocd", "ref": "ghcr.io/<owner>/argocd@sha256:…",
  "params": {"fixable": ["CRITICAL"], "unfixed": []},
  "findings": [
    {"id": "CVE-2026-1234", "severity": "HIGH", "package": "golang.org/x/net", "installed": "0.30.0", "fixed": "0.38.0",
     "fixable": true, "ecosystem": "gomod", "location": "usr/local/bin/helm", "vex": null}
  ]
}
```

| Field | Meaning |
|---|---|
| `stage` | `patch` (the patch PR's image) or `release` (what a release or Copa refresh is about to sign) |
| `params` | The recipe's `gate.failOn`, merged over `_global.yaml`'s |
| `findings[].fixable` | Trivy has a fixed version, and the finding's status allows the fix |
| `findings[].location` | The file the package is in: a binary or jar in the image, or the OS package database |
| `findings[].vex` | The status of the VEX statement that covers the finding, or `null` |

To see what the gate sees for an image, take the scan the release writes (`out/<recipe>/<line>/scan-release-*.json`).
Then evaluate it by hand:

```bash
conftest test --namespace patcher.gate --policy policy input.json
```

## When the gate can't run

A gate that can't be evaluated, because there's no conftest or the policy doesn't parse, never counts as a pass:
- **With `enforce`,** the release stops.
- **Without `enforce`,** the run goes on with a warning, because the gate only reports.

conftest is pinned with the other tools in `patcher/Dockerfile`, and `tool-pins.yml` keeps it current.
