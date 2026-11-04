# Release gate: what a released image may still contain. The patcher evaluates this package with conftest (OPA) on
# each image's final scan: patch PRs report the verdict, and with `gate.enforce` a release it denies stops before it is
# signed. `deny` fails the gate; `warn` is only reported. Add rules in other files of this directory, in the same
# package, for anything the parameters below don't cover.
#
# input (one image; docs/gate.md):
#   stage        "patch" (the patch PR's image) or "release" (what a release or Copa refresh is about to sign)
#   recipe, line, image, ref
#   user         the image's configured user ("" when it sets none, so root), or null when the scan isn't of an image
#   params       the recipe's `gate.failOn` merged over _global.yaml's:
#                  fixable  severities of fixable findings that fail the gate, e.g. ["CRITICAL", "HIGH"]
#                  unfixed  severities of findings with no fix released that fail it
#   findings     {id, severity, package, installed, fixed, fixable, ecosystem, location, vex}
#                vex is the status of the VEX statement that covers the finding (not_affected, affected, ...), or null
package patcher.gate

# A finding a VEX statement settles (not_affected, fixed) is a decision on record: it never fails the gate. An
# `affected` or `under_investigation` statement doesn't settle it.
settled := {"not_affected", "fixed"}

open contains f if {
	some f in input.findings
	not f.vex in settled
}

deny contains msg if {
	some f in open
	f.fixable
	f.severity in input.params.fixable
	msg := sprintf("%s %s in %s %s (%s) is fixable: fixed in %s", [f.severity, f.id, f.package, f.installed, f.location, f.fixed])
}

deny contains msg if {
	some f in open
	not f.fixable
	f.severity in input.params.unfixed
	msg := sprintf("%s %s in %s %s (%s) has no fix released", [f.severity, f.id, f.package, f.installed, f.location])
}

# How the image runs. Pod Security Admission's `restricted` profile (runAsNonRoot) needs a user that is numeric and not
# root: a name can't be checked, so the kubelet refuses to start the container (docs/running-non-root.md)
warn contains msg if {
	is_string(input.user)
	runs_as_root(input.user)
	msg := sprintf("%s runs as root: give it a numeric non-root user (`user` on the recipe's image), or run it with runAsUser", [input.image])
}

warn contains msg if {
	is_string(input.user)
	not runs_as_root(input.user)
	not regex.match(`^[0-9]+(:[0-9]+)?$`, input.user)
	msg := sprintf("%s runs as user %s, a name: runAsNonRoot can't check it, so set the same user as a number (`user` on the recipe's image)", [input.image, input.user])
}

runs_as_root(user) if user == ""

runs_as_root(user) if split(user, ":")[0] in {"0", "root"}
