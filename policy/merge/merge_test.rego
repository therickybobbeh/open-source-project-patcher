# `conftest verify --policy policy`: the merge policy's rules against small patch sets.
package patcher.merge_test

import data.patcher.merge

clean := {
	"status": "success",
	"tests": {"configured": true, "ran": true, "passed": true},
	"gate": {"app": {"passed": true, "deny": [], "warn": []}},
	"changes": [{"ecosystem": "gomod", "target": "go.mod", "name": "golang.org/x/net", "old": "v0.60.0", "new": "v0.62.0", "note": "", "level": "minor"}],
}

test_a_clean_run_merges if {
	count(merge.deny) == 0 with input as clean
}

test_a_run_that_did_not_succeed_waits_for_a_person if {
	merge.deny["the run ended tests-preexisting: read the report"] with input as object.union(clean, {"status": "tests-preexisting"})
}

test_tests_that_should_have_run_but_didnt_hold_it if {
	some msg in merge.deny with input as object.union(clean, {"tests": {"configured": true, "ran": false, "passed": false}})
	msg == "upstream tests didn't run"
}

test_a_recipe_without_tests_is_only_a_warning if {
	no_tests := object.union(clean, {"tests": {"configured": false, "ran": false, "passed": false}})
	count(merge.deny) == 0 with input as no_tests
	count(merge.warn) == 1 with input as no_tests
}

test_a_gate_denial_holds_it if {
	denied := object.union(clean, {"gate": {"app": {"passed": false, "deny": ["CRITICAL CVE-1 in x is fixable"], "warn": []}}})
	merge.deny["the release gate denies app: CRITICAL CVE-1 in x is fixable"] with input as denied
}

test_a_major_bump_holds_it if {
	major := object.union(clean, {"changes": [{"ecosystem": "npm", "target": "package-lock.json", "name": "minimatch", "old": "3.1.2", "new": "10.2.3", "note": "", "level": "major"}]})
	merge.deny["major bump: minimatch 3.1.2 -> 10.2.3"] with input as major
}

test_a_patch_set_from_before_the_policy_waits if {
	old := {"status": "success", "changes": []}
	count(merge.deny) == 1 with input as old
}
