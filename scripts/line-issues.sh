#!/usr/bin/env bash
# line-issues.sh <new-lines.json>: one issue per upstream release line that no recipe tracks
# (`patcher new-lines --json`), e.g. "New release line: argo-cd v3.6".
#   - a newly reported line opens an issue, once: closing it means "not tracking that line", and it stays
#     closed (a later major or minor is a new line, with a new issue);
#   - an open issue whose line is no longer reported (now tracked, or a newer line superseded it) closes.
# Called by rescan.yml. Needs GH_TOKEN with issues: write, and GITHUB_REPOSITORY. DRY_RUN=1 prints the
# gh commands instead of running them.
set -euo pipefail
file=$1
repo=${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is not set}
label=new-release-line

act() { if [ -n "${DRY_RUN:-}" ]; then printf 'would run:'; printf ' %q' "$@"; echo; else "$@"; fi; }

if [ -z "${DRY_RUN:-}" ]; then
  gh label create "$label" -R "$repo" --color 0E8A16 \
    --description "Upstream shipped a release line no recipe tracks" >/dev/null 2>&1 || true
fi
issues=$(gh issue list -R "$repo" --label "$label" --state all --limit 500 --json number,title,state)
reported=$(jq -r '.[] | "New release line: \(.recipe) \(.line)"' "$file")

jq -c '.[]' "$file" | while IFS= read -r x; do
  recipe=$(jq -r .recipe <<<"$x")
  title="New release line: $recipe $(jq -r .line <<<"$x")"
  if jq -e --arg t "$title" 'any(.[]; .title == $t)' <<<"$issues" >/dev/null; then
    continue  # open, or closed on purpose
  fi
  body="Upstream released **$(jq -r .tag <<<"$x")**. \`recipes/$recipe.yaml\` tracks: $(jq -r '.tracked | join(", ")' <<<"$x").

To follow it, add a release line to \`source.lines\` and merge: the push starts the patch run for it
(see [Adding a release line](https://github.com/$repo/blob/HEAD/docs/runbook.md#adding-a-release-line-or-a-project)). A new
major can need recipe changes (toolchain, Dockerfile targets, tests).

If you won't track this line, close the issue; it isn't reopened."
  act gh issue create -R "$repo" --title "$title" --label "$label" --body "$body"
done

jq -r '.[] | select(.state == "OPEN") | "\(.number)\t\(.title)"' <<<"$issues" | while IFS=$'\t' read -r n title; do
  grep -qxF -- "$title" <<<"$reported" && continue
  act gh issue close "$n" -R "$repo" --comment "No longer reported: the line is tracked now, or a newer line superseded it."
done
