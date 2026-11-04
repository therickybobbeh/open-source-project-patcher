"""scripts/merge-ready.sh, the daily merge round, against a stand-in `gh` and the real merge policy (policy/merge/,
with conftest when it is installed: the patcher image and CI have it): what it merges, and in which order."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
OK = [{"__typename": "CheckRun", "name": "test", "status": "COMPLETED", "conclusion": "SUCCESS"},
      {"__typename": "CheckRun", "name": "image", "status": "COMPLETED", "conclusion": "SKIPPED"}]
needs_tools = pytest.mark.skipif(not (shutil.which("jq") and shutil.which("conftest")), reason="needs jq and conftest")


def pr(n, head, title, checks=OK, draft=False, mergeable="MERGEABLE"):
    return {"number": n, "headRefName": head, "headRefOid": f"{n:040d}", "title": title, "isDraft": draft,
            "mergeable": mergeable, "statusCheckRollup": checks}


def plan(status="success", ran=True, gate=True, level="minor", upgrade="patch"):
    """A patch set as a patch run writes it (generated/<recipe>/<tag>/bump-plan.json)."""
    return {"recipe": "app", "line": "v1", "tag": "v1.1.0" if upgrade == "minor" else "v1.0.1", "status": status,
            "upstream": {"released": "v1.0.0", "level": upgrade},
            "tests": {"configured": True, "ran": ran, "passed": ran},
            "gate": {"app": {"passed": gate, "deny": [] if gate else ["CRITICAL CVE-1 is fixable"], "warn": []}},
            "changes": [{"ecosystem": "gomod", "target": "go.mod", "name": "golang.org/x/net", "old": "v0.60.0",
                         "new": "v0.62.0", "note": "", "level": level}]}


PRS = [
    pr(1, "fix/thing", "Fix a thing"),                                              # code: a person merges it
    pr(2, "patch/dex/v2", "[dex] v2.46.1: dependency updates (success)"),           # the policy allows it
    pr(3, "deps/tool-pins", "deps(tools): update pinned tool downloads in patcher/Dockerfile"),
    pr(4, "state/dex/v2", "[dex] record release of v2"),
    pr(5, "patch/maven/maven3", "[maven] 3.10.0: dependency updates (tests-preexisting)"),
    pr(6, "patch/trivy/v0", "[trivy] v0.76.1: dependency updates (tests-failed)", draft=True),
    pr(7, "state/strimzi/1-refresh", "[strimzi] copa refresh of 1",
       checks=[{"__typename": "CheckRun", "name": "test", "status": "IN_PROGRESS", "conclusion": None}]),
    pr(8, "dependabot/docker/patcher/x", "deps(image): bump uv",
       checks=[{"__typename": "CheckRun", "name": "test", "status": "COMPLETED", "conclusion": "FAILURE"}]),
    pr(9, "patch/argo-cd/v3.4", "[argo-cd] v3.4.13: dependency updates (success)"),  # a major bump: held
    pr(10, "patch/external-secrets/v2", "[external-secrets] v2.14.1 → v2.15.0: dependency updates (success)"),  # an upgrade
]
PLANS = {2: plan(), 5: plan(status="tests-preexisting"), 6: plan(status="tests-failed", ran=True), 9: plan(level="major"),
         10: plan(upgrade="minor")}


@pytest.fixture
def round_(tmp_path):
    (tmp_path / "prs.json").write_text(json.dumps(PRS))
    for n, doc in PLANS.items():
        f = tmp_path / "generated" / f"app{n}" / "v1.0.0" / "bump-plan.json"
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps(doc))
    fake = tmp_path / "bin" / "gh"
    fake.parent.mkdir()
    fake.write_text(f"""#!/usr/bin/env bash
case "$1 $2" in
  "pr list") cat {tmp_path}/prs.json ;;
  "run list") echo "$(date -u +%F) completed" ;;
  "api --paginate") n="${{3#repos/o/r/pulls/}}"; n="${{n%/files}}"  # a new tag's PR also removes the older patch set
    echo "generated/app$n/v1.0.0/bump-plan.json" ;;  # (the removed v0.9.0 one is filtered out by -q)
  "pr merge") echo "$3" >> {tmp_path}/merged ;;
  "api -H") p="${{4#repos/o/r/contents/}}"; cat "{tmp_path}/${{p%%\\?*}}" ;;
  *) echo "unexpected: gh $*" >&2; exit 1 ;;
esac
""")
    fake.chmod(0o755)

    def run(*args, path_extra=""):
        env = {**os.environ, "PATH": f"{fake.parent}:{path_extra}{os.environ['PATH']}", "GITHUB_REPOSITORY": "o/r"}
        env.pop("DRY_RUN", None)
        out = subprocess.run([str(ROOT / "scripts" / "merge-ready.sh"), *args], env=env, capture_output=True, text=True,
                             check=True)
        log = tmp_path / "merged"
        merged = log.read_text().split() if log.exists() else []
        log.unlink(missing_ok=True)
        return out.stdout, merged
    return run


@needs_tools
def test_listing_merges_nothing_and_shows_the_policy_s_reasons(round_):
    out, merged = round_()
    assert merged == []
    rows = [line.split()[1] for line in out.splitlines() if not line.startswith("note:")]
    assert rows == ["#4", "#7", "#2", "#5", "#6", "#9", "#10", "#3", "#8", "#1"]  # records, patch, deps, the rest
    assert "the merge policy allows it" in out
    assert "held: the run ended tests-preexisting: read the report" in out
    assert "held: major bump: golang.org/x/net v0.60.0 -> v0.62.0" in out
    assert "held: upstream upgrade v1.0.0 -> v1.1.0 (minor): read upstream's release notes, then merge it by hand" in out


@needs_tools
def test_merge_takes_records_policy_allowed_patch_prs_and_dependencies(round_):
    # ready ones only: #7's checks run, #8's failed, #6 is a draft, #5, #9 and #10 are held by the policy, #1 is code
    assert round_("--merge")[1] == ["4", "2", "3"]


@needs_tools
def test_without_conftest_patch_prs_are_held(round_, tmp_path):
    bare = tmp_path / "bare"
    bare.mkdir()
    for tool in ("bash", "jq", "date", "grep", "head", "cat", "mktemp", "rm", "dirname"):
        (bare / tool).symlink_to(shutil.which(tool))
    env_path = f"{tmp_path / 'bin'}:{bare}"
    out = subprocess.run([str(ROOT / "scripts" / "merge-ready.sh"), "--merge"], capture_output=True, text=True, check=True,
                         env={"PATH": env_path, "GITHUB_REPOSITORY": "o/r", "HOME": str(tmp_path)}).stdout
    assert "held: conftest isn't installed" in out
    assert (tmp_path / "merged").read_text().split() == ["4", "3"]
