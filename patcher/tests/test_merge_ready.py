"""scripts/merge-ready.sh, the daily merge round, against a stand-in `gh`: what it merges, and in which order."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
OK = [{"__typename": "CheckRun", "name": "test", "status": "COMPLETED", "conclusion": "SUCCESS"},
      {"__typename": "CheckRun", "name": "image", "status": "COMPLETED", "conclusion": "SKIPPED"}]


def pr(n, head, title, checks=OK, draft=False, mergeable="MERGEABLE"):
    return {"number": n, "headRefName": head, "headRefOid": f"{n:040d}", "title": title, "isDraft": draft,
            "mergeable": mergeable, "statusCheckRollup": checks}


PRS = [
    pr(1, "fix/thing", "Fix a thing"),                                                   # code: a person merges it
    pr(2, "patch/dex/v2", "[dex] v2.46.1: dependency updates (success)"),
    pr(3, "deps/tool-pins", "deps(tools): update pinned tool downloads in patcher/Dockerfile"),
    pr(4, "state/dex/v2", "[dex] record release of v2"),
    pr(5, "patch/maven/maven3", "[maven] 3.10.0: dependency updates (tests-preexisting)"),
    pr(6, "patch/trivy/v0", "[trivy] v0.76.1: dependency updates (tests-failed)", draft=True),
    pr(7, "state/strimzi/1-refresh", "[strimzi] copa refresh of 1",
       checks=[{"__typename": "CheckRun", "name": "test", "status": "IN_PROGRESS", "conclusion": None}]),
    pr(8, "dependabot/docker/patcher/x", "deps(image): bump uv",
       checks=[{"__typename": "CheckRun", "name": "test", "status": "COMPLETED", "conclusion": "FAILURE"}]),
]


@pytest.fixture
def gh(tmp_path):
    if not shutil.which("jq"):
        pytest.skip("jq not installed")
    (tmp_path / "prs.json").write_text(json.dumps(PRS))
    fake = tmp_path / "bin" / "gh"
    fake.parent.mkdir()
    fake.write_text(f"""#!/usr/bin/env bash
case "$1 $2" in
  "pr list") cat {tmp_path}/prs.json ;;
  "run list") echo "2026-11-03 completed" ;;
  "pr merge") echo "$3 $*" >> {tmp_path}/merged ;;
  *) echo "unexpected: gh $*" >&2; exit 1 ;;
esac
""")
    fake.chmod(0o755)

    def run(*args):
        env = {**os.environ, "PATH": f"{fake.parent}:{os.environ['PATH']}", "GITHUB_REPOSITORY": "o/r"}
        env.pop("DRY_RUN", None)
        out = subprocess.run([str(ROOT / "scripts" / "merge-ready.sh"), *args], env=env, capture_output=True, text=True, check=True)
        log = tmp_path / "merged"
        merged = [line.split()[0] for line in log.read_text().splitlines()] if log.exists() else []
        log.unlink(missing_ok=True)
        return out.stdout, merged
    return run


def test_listing_merges_nothing(gh):
    out, merged = gh()
    assert merged == []
    lines = [line.split()[:2] for line in out.splitlines()]
    assert [n for _, n in lines] == ["#4", "#7", "#2", "#5", "#6", "#3", "#8", "#1"]  # records, patch, deps, the rest


def test_merge_takes_records_and_dependencies_and_patch_prs_only_when_asked(gh):
    assert gh("--merge")[1] == ["4", "3"]  # ready ones only: #7 runs, #8 failed, #1 is code
    out, merged = gh("--merge", "--patch")
    assert merged == ["4", "2", "3"]  # #5's run says tests-preexisting and #6 is a draft: a person reads those
    assert "--match-head-commit" in (ROOT / "scripts" / "merge-ready.sh").read_text()
    assert "read the report" in out and "draft" in out
