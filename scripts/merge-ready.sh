#!/usr/bin/env bash
# merge-ready.sh [--merge]: the daily merge round. Lists every open PR by kind and what it waits for; with --merge,
# merges what is ready, in the order that keeps the pipeline moving:
#   1. release records (`[x] record release of …`, `copa refresh of …`): no decision in them, and until one merges the
#      rescan skips its line;
#   2. patch PRs the merge policy allows (policy/merge/, Rego run with conftest, on the patch set the PR would merge):
#      merging one is the release decision, so a PR the policy holds waits for a person, with the policy's reason;
#   3. dependency PRs (tool pins, Dependabot).
# Code and docs PRs are listed, never merged: a person merges those (bottom-up, when they are a stack).
# Ready = not a draft, every check passed, no conflict. Each merge is pinned to the commit that was checked.
# Needs gh logged in with write access (GH_TOKEN works too), jq, and conftest for patch PRs (without it they are held).
# DRY_RUN=1 prints the merges instead of running them.
set -euo pipefail
repo=${GITHUB_REPOSITORY:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}
policy="$(cd "$(dirname "$0")/.." && pwd)/policy"
merge=false
for arg in "$@"; do
  case $arg in
    --merge) merge=true ;;
    *) echo "usage: $0 [--merge]" >&2; exit 2 ;;
  esac
done

act() { if [ -n "${DRY_RUN:-}" ]; then printf 'would run:'; printf ' %q' "$@"; echo; else "$@" >/dev/null; fi; }

# patch PRs are re-run by the day's rescan: until it has finished, they can still change
last=$(gh run list -R "$repo" --workflow rescan.yml --limit 1 --json createdAt,status -q '.[0] | "\(.createdAt[:10]) \(.status)"' || true)
if [ "$last" != "$(date -u +%F) completed" ]; then
  echo "note: today's rescan hasn't finished (latest: ${last:-none}); patch PRs may still change"
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# the merge policy's verdict on patch PR $1 at commit $2: "allow", "allow (warn: …)" or "held: <reason>"
verdict() {
  local number=$1 sha=$2 path out
  command -v conftest >/dev/null || { echo "held: conftest isn't installed, so the merge policy can't run"; return; }
  # the patch set the PR adds or changes (a new tag's PR also removes the line's older one)
  path=$(gh api --paginate "repos/$repo/pulls/$number/files" -q '.[] | select(.status != "removed") | .filename' </dev/null \
    | grep -E '^generated/[^/]+/[^/]+/bump-plan\.json$' | head -1 || true)
  [ -n "$path" ] || { echo "held: no patch set (generated/<recipe>/<tag>/bump-plan.json) in the PR"; return; }
  gh api -H "Accept: application/vnd.github.raw" "repos/$repo/contents/$path?ref=$sha" </dev/null > "$tmp/plan.json" 2>/dev/null \
    || { echo "held: couldn't read $path at the PR's commit"; return; }
  out=$(conftest test --no-color --output json --namespace patcher.merge --policy "$policy" "$tmp/plan.json" </dev/null || true)
  jq -r 'first(.[]) as $r
    | if ($r.exceptions // []) != [] then "held: the merge policy raised an error"
      elif ($r.failures // []) != [] then "held: \($r.failures[0].msg)"
        + (if ($r.failures | length) > 1 then " (+\(($r.failures | length) - 1) more)" else "" end)
      elif ($r.warnings // []) != [] then "allow (warn: \($r.warnings[0].msg))"
      else "allow" end' <<<"$out" 2>/dev/null || echo "held: the merge policy couldn't be evaluated"
}

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
while IFS=$'\t' read -r kind number state sha title; do
  [ -n "$kind" ] || continue
  note=$state
  go=false
  if [ "$state" = ready ]; then
    case $kind in
      record | deps) go=$merge ;;
      patch)
        note=$(verdict "$number" "$sha")
        case $note in allow*) go=$merge; note="ready: ${note/allow/the merge policy allows it}" ;; esac ;;
      *) note="ready: a person merges code and docs" ;;
    esac
  fi
  if [ "$go" = true ]; then
    if act gh pr merge "$number" -R "$repo" --merge --match-head-commit "$sha" </dev/null; then
      note=${DRY_RUN:+would merge}; note=${note:-merged}; merged=$((merged + 1))
    else
      note="merge failed (see above)"
    fi
  fi
  printf '%-7s #%-5s %-60s %s\n' "$kind" "$number" "$note" "$title"
done <<<"$rows"
if [ "$merge" = true ]; then echo "merged: $merged"; fi
