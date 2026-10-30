#!/usr/bin/env bash
# eol-issues.sh <eol.json>: one issue per recipe runtime that is end-of-life or soon will be
# (`patcher eol --json`), e.g. "End of life: argo-workflows Node.js 20".
#   - a newly reported runtime opens an issue, once: closing it means "accepted", and it stays closed;
#   - an open issue whose runtime is no longer reported (raised with minVersions or a toolchain bump, or
#     upstream moved on) closes.
# Called by rescan.yml. Needs GH_TOKEN with issues: write, and GITHUB_REPOSITORY. DRY_RUN=1 prints the
# gh commands instead of running them.
set -euo pipefail
file=$1
repo=${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is not set}
label=end-of-life

act() { if [ -n "${DRY_RUN:-}" ]; then printf 'would run:'; printf ' %q' "$@"; echo; else "$@"; fi; }

if [ -z "${DRY_RUN:-}" ]; then
  gh label create "$label" -R "$repo" --color B60205 \
    --description "A recipe builds on a runtime that is end-of-life, or soon will be" >/dev/null 2>&1 || true
fi
issues=$(gh issue list -R "$repo" --label "$label" --state all --limit 500 --json number,title,state)
reported=$(jq -r '.[] | "End of life: \(.recipe) \(.label) \(.release)"' "$file")

jq -c '.[]' "$file" | while IFS= read -r x; do
  recipe=$(jq -r .recipe <<<"$x")
  title="End of life: $recipe $(jq -r '"\(.label) \(.release)"' <<<"$x")"
  if jq -e --arg t "$title" 'any(.[]; .title == $t)' <<<"$issues" >/dev/null; then
    continue  # open, or closed on purpose
  fi
  when=$(jq -r 'if .days == null then "is end-of-life"
    elif .days < 0 then "has been end-of-life since \(.eol)"
    else "reaches end of life on \(.eol), in \(.days) days" end' <<<"$x")
  body="**$(jq -r '"\(.label) \(.release)"' <<<"$x")** $when ([endoflife.date](https://endoflife.date/$(jq -r .product <<<"$x"))).

\`recipes/$recipe.yaml\` builds with it:
$(jq -r '.uses[] | "- \(.)"' <<<"$x")

- **A Dockerfile stage:** raise it with \`minVersions\` on the recipe's dockerfile ecosystem, for example
  \`minVersions: {node: \"24\"}\` ([how](https://github.com/$repo/blob/HEAD/docs/recipes.md#dockerfile)). On the next run,
  images below that line move to its newest tag. Pick a line the stage still builds on (Node 26 images have no
  yarn, for example); the patch PR shows the image build.
- **A toolchain:** raise it in the recipe's \`toolchain\`.

The issue closes by itself once nothing in the recipe uses this release. To accept it, close the issue; it isn't
reopened."
  act gh issue create -R "$repo" --title "$title" --label "$label" --body "$body"
done

jq -r '.[] | select(.state == "OPEN") | "\(.number)\t\(.title)"' <<<"$issues" | while IFS=$'\t' read -r n title; do
  grep -qxF -- "$title" <<<"$reported" && continue
  act gh issue close "$n" -R "$repo" --comment "No longer reported: nothing in the recipe builds with this release any more."
done
