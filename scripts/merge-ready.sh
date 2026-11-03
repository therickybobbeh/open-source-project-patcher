#!/usr/bin/env bash
# merge-ready.sh [--merge [--patch]]: the daily merge round. Lists every open PR by kind and what it waits for; merges
# what is ready, in the order that keeps the pipeline moving:
#   1. release records (`[x] record release of …`, `copa refresh of …`): no decision in them, and until one merges the
#      rescan skips its line;
#   2. patch PRs, with --patch only, and only those whose run succeeded: merging one is the release decision;
#   3. dependency PRs (tool pins, Dependabot).
# Code and docs PRs are listed, never merged: a person merges those (bottom-up, when they are a stack).
# Ready = not a draft, every check passed, no conflict. Each merge is pinned to the commit that was checked.
# Needs gh logged in with write access (GH_TOKEN works too). DRY_RUN=1 prints the merges instead of running them.
set -euo pipefail
repo=${GITHUB_REPOSITORY:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}
merge=false
patch=false
for arg in "$@"; do
  case $arg in
    --merge) merge=true ;;
    --patch) patch=true ;;
    *) echo "usage: $0 [--merge [--patch]]" >&2; exit 2 ;;
  esac
done

act() { if [ -n "${DRY_RUN:-}" ]; then printf 'would run:'; printf ' %q' "$@"; echo; else "$@" >/dev/null; fi; }

# patch PRs are re-run by the day's rescan: until it has finished, they can still change
last=$(gh run list -R "$repo" --workflow rescan.yml --limit 1 --json createdAt,status -q '.[0] | "\(.createdAt[:10]) \(.status)"' || true)
if [ "$last" != "$(date -u +%F) completed" ]; then
  echo "note: today's rescan hasn't finished (latest: ${last:-none}); patch PRs may still change"
fi

# kind, number, verdict ("ready" or what it waits for), head commit, title; sorted in merge order
rows=$(gh pr list -R "$repo" --state open --limit 300 \
  --json number,title,headRefName,headRefOid,isDraft,mergeable,statusCheckRollup | jq -r '
  def kind: .headRefName as $h
    | if ($h | startswith("state/")) then "record"
      elif ($h | startswith("patch/")) then "patch"
      elif ($h | startswith("deps/")) or ($h | startswith("dependabot/")) then "deps"
      else "other" end;
  def results: [.statusCheckRollup[]?
    | if .__typename == "StatusContext" then .state elif .status != "COMPLETED" then "PENDING" else .conclusion end];
  def verdict: results as $r
    | if .isDraft then "draft"
      elif .mergeable == "CONFLICTING" then "conflicts"
      elif ($r | length) == 0 then "no checks yet"
      elif any($r[]; . as $x | ["SUCCESS", "SKIPPED", "NEUTRAL"] | index($x) | not)
        then (if any($r[]; . == "PENDING" or . == "QUEUED" or . == "IN_PROGRESS" or . == "EXPECTED") then "checks running"
              else "checks failed" end)
      else "ready" end;
  map({k: kind, o: ({record: 0, patch: 1, deps: 2, other: 3}[kind]), n: .number, v: verdict, sha: .headRefOid, t: .title})
  | sort_by(.o, .n)[] | [.k, .n, .v, .sha, .t] | @tsv')

merged=0
while IFS=$'\t' read -r kind number verdict sha title; do
  [ -n "$kind" ] || continue
  note=$verdict
  if [ "$verdict" = ready ]; then
    case $kind in
      record | deps) go=$merge ;;
      patch) go=false
        if [[ $title != *"(success)" ]]; then note="ready, but its run says ${title##*(}: read the report"
        elif [ "$patch" = true ]; then go=$merge
        else note="ready: merging it releases (--patch)"; fi ;;
      *) go=false; note="ready: a person merges code and docs" ;;
    esac
    if [ "$go" = true ]; then
      if act gh pr merge "$number" -R "$repo" --merge --match-head-commit "$sha"; then
        note=${DRY_RUN:+would merge}; note=${note:-merged}; merged=$((merged + 1))
      else
        note="merge failed (see above)"
      fi
    fi
  fi
  printf '%-7s #%-5s %-44s %s\n' "$kind" "$number" "$note" "$title"
done <<<"$rows"
if [ "$merge" = true ]; then echo "merged: $merged"; fi
