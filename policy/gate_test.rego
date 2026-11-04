# `conftest verify --policy policy`: the gate's rules against small inputs.
package patcher.gate_test

import data.patcher.gate

finding(id, severity, fixed, vex) := {
	"id": id, "severity": severity, "package": "golang.org/x/net", "installed": "0.30.0", "fixed": fixed,
	"fixable": fixed != "", "ecosystem": "gomod", "location": "usr/local/bin/app", "vex": vex,
}

image(params, findings) := {"stage": "release", "recipe": "app", "line": "v1", "image": "app", "params": params, "findings": findings}

test_a_fixable_finding_of_a_listed_severity_fails if {
	count(gate.deny) == 1 with input as image({"fixable": ["CRITICAL", "HIGH"], "unfixed": []}, [
		finding("CVE-1", "HIGH", "0.38.0", null),
		finding("CVE-2", "MEDIUM", "0.38.0", null),
	])
}

test_unfixed_findings_fail_only_when_asked if {
	findings := [finding("CVE-1", "CRITICAL", "", null)]
	count(gate.deny) == 0 with input as image({"fixable": ["CRITICAL"], "unfixed": []}, findings)
	some msg in gate.deny with input as image({"fixable": [], "unfixed": ["CRITICAL"]}, findings)
	contains(msg, "no fix released")
}

test_findings_vex_settles_never_fail if {
	count(gate.deny) == 0 with input as image({"fixable": ["CRITICAL"], "unfixed": ["CRITICAL"]}, [
		finding("CVE-1", "CRITICAL", "0.38.0", "not_affected"),
		finding("CVE-2", "CRITICAL", "", "fixed"),
	])
}

test_an_affected_statement_doesnt_settle_a_finding if {
	count(gate.deny) == 1 with input as image({"fixable": ["CRITICAL"], "unfixed": []}, [
		finding("CVE-1", "CRITICAL", "0.38.0", "affected"),
	])
}

test_nothing_fails_with_no_severities_listed if {
	count(gate.deny) == 0 with input as image({"fixable": [], "unfixed": []}, [finding("CVE-1", "CRITICAL", "0.38.0", null)])
}

runs_as(user) := object.union(image({"fixable": [], "unfixed": []}, []), {"user": user})

test_an_image_that_runs_as_root_is_a_warning if {
	every user in ["", "0", "0:0", "root", "root:root"] {
		gate.warn["app runs as root: give it a numeric non-root user (`user` on the recipe's image), or run it with runAsUser"] with input as runs_as(user)
	}
	count(gate.deny) == 0 with input as runs_as("")
}

test_a_user_name_is_a_warning if {
	gate.warn["app runs as user dex:dex, a name: runAsNonRoot can't check it, so set the same user as a number (`user` on the recipe's image)"] with input as runs_as("dex:dex")
}

test_a_numeric_user_and_a_source_scan_say_nothing if {
	count(gate.warn) == 0 with input as runs_as("1001:1001")
	count(gate.warn) == 0 with input as runs_as("65532")
	count(gate.warn) == 0 with input as runs_as(null)
	count(gate.warn) == 0 with input as image({"fixable": [], "unfixed": []}, [])
}
