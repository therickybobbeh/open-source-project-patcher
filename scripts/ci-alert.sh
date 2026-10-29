#!/usr/bin/env bash
# ci-alert.sh <run-id>: one GitHub issue per failing CI job, so a failed release or nightly doesn't go
# unnoticed in the Actions tab (all six releases of 2026-10-29 failed that way).
#   - a job that failed or timed out opens "CI failure: <workflow> / <job>", or comments on the open one;
#   - a job that passed closes its open issue.
# Called by .github/workflows/ci-alerts.yml for runs on main. Needs GH_TOKEN with issues: write and
# actions: read, and GITHUB_REPOSITORY. DRY_RUN=1 prints the gh commands instead of running them.
set -euo pipefail
run_id=$1
repo=${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is not set}
label=ci-failure

act() { if [ -n "${DRY_RUN:-}" ]; then printf 'would run:'; printf ' %q' "$@"; echo; else "$@"; fi; }

run=$(gh api "repos/$repo/actions/runs/$run_id")
workflow=$(jq -r .name <<<"$run")
run_url=$(jq -r .html_url <<<"$run")
context="$(jq -r .event <<<"$run") of $(jq -r '.head_sha[0:7]' <<<"$run")"
jobs=$(gh api --paginate "repos/$repo/actions/runs/$run_id/jobs?per_page=100" --jq '.jobs[]' | jq -s .)
open=$(gh issue list -R "$repo" --label "$label" --state open --limit 500 --json number,title)
issue_for() { jq -r --arg t "CI failure: $workflow / $1" '.[] | select(.title == $t) | .number' <<<"$open" | head -1; }

if [ -z "${DRY_RUN:-}" ]; then
  gh label create "$label" -R "$repo" --color B60205 \
    --description "A CI job on main failed; the issue closes when that job passes again" >/dev/null 2>&1 || true
fi

jq -r '.[] | select(.conclusion == "success") | .name' <<<"$jobs" | while IFS= read -r job; do
  n=$(issue_for "$job")
  [ -z "$n" ] || act gh issue close "$n" -R "$repo" --comment "Passed again in [$workflow run]($run_url) ($context)."
done

jq -c '.[] | select(.conclusion == "failure" or .conclusion == "timed_out")' <<<"$jobs" | while IFS= read -r j; do
  job=$(jq -r .name <<<"$j")
  steps=$(jq -r '[.steps[]? | select(.conclusion == "failure") | .name] | join(", ")' <<<"$j")
  body="**$job** $(jq -r .conclusion <<<"$j") in [$workflow run]($run_url) ($context).
Failed step: ${steps:-unknown}. [Job log]($(jq -r .html_url <<<"$j"))

This issue closes itself when \`$job\` passes again."
  n=$(issue_for "$job")
  if [ -z "$n" ]; then
    act gh issue create -R "$repo" --title "CI failure: $workflow / $job" --label "$label" --body "$body"
  else
    act gh issue comment "$n" -R "$repo" --body "$body"
  fi
done
