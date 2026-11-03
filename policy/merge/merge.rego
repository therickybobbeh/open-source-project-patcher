# Merge policy: which patch PRs the daily merge round (scripts/merge-ready.sh --merge) merges without a person.
# Merging a patch PR is the release decision; these rules take it when the run's own checks are enough. Each `deny`
# holds the PR for a person and says why; `warn` is shown and doesn't hold it. Change the rules here, or add rules in
# other files of this directory in the same package.
#
# input: the patch set the PR would merge (generated/<recipe>/<tag>/bump-plan.json), notably
#   status   the run's outcome: success, tests-preexisting, tests-failed, build-failed, ...
#   tests    {configured, ran, passed}: the recipe's upstream test suite in this run
#   gate     {<image>: {passed, deny, warn}}: the release gate's verdict on each image
#   changes  [{ecosystem, target, name, old, new, note, level}]; level is patch, minor or major (patch when the change
#            isn't between two versions, e.g. a base image reference)
package patcher.merge

deny contains msg if {
	input.status != "success"
	msg := sprintf("the run ended %s: read the report", [input.status])
}

deny contains "the patch set records no test or gate results (it predates the merge policy): re-run the line" if {
	not input.tests
}

deny contains "upstream tests didn't run" if {
	input.tests.configured
	not input.tests.ran
}

deny contains msg if {
	some image, verdict in input.gate
	not verdict.passed
	msg := sprintf("the release gate denies %s: %s", [image, concat("; ", verdict.deny)])
}

deny contains msg if {
	some c in input.changes
	c.level == "major"
	msg := sprintf("major bump: %s %s -> %s", [c.name, c.old, c.new])
}

warn contains "the recipe runs no upstream tests: only the build and the smoke tests checked it" if {
	input.tests
	not input.tests.configured
}
