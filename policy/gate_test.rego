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
