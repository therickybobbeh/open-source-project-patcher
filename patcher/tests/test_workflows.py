"""Guards on .github/: actions pinned to commits, and the release's trust boundary. Jobs that run upstream code hold
no credentials; jobs that can write (push images, sign, open PRs) read no cache, because any job on the branch can
write those, including the ones that run upstream code."""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
ACTIONS = sorted((ROOT / ".github" / "actions").glob("*/action.yml"))
UPSTREAM_CODE = ("run ", "release-build ")  # patcher commands that build or test upstream code
RUN_PATCHER = "./.github/actions/run-patcher"


def jobs(path: Path) -> list[tuple[str, dict, dict]]:
    """(name, job, effective permissions) for each job of a workflow."""
    doc = yaml.safe_load(path.read_text())
    out = []
    for name, job in doc.get("jobs", {}).items():
        perms = job.get("permissions", doc.get("permissions", {}))
        if isinstance(perms, str):  # read-all / write-all
            perms = {"all": perms.split("-")[0]}
        out.append((name, job, perms))
    return out


def steps(job: dict) -> list[dict]:
    return job.get("steps", [])


def patcher_args(job: dict) -> list[str]:
    return [" ".join(s["with"]["args"].split()) for s in steps(job) if s.get("uses") == RUN_PATCHER]


def writes(perms: dict) -> bool:
    return "write" in perms.values()


def logs_in(job: dict) -> bool:
    return any("login-action" in s.get("uses", "") for s in steps(job)) or "secrets." in yaml.safe_dump(job)


@pytest.mark.parametrize("path", WORKFLOWS + ACTIONS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_actions_are_pinned_to_a_commit(path):
    doc = yaml.safe_load(path.read_text())
    all_steps = [s for j in doc.get("jobs", {}).values() for s in steps(j)] + doc.get("runs", {}).get("steps", [])
    for s in all_steps:
        uses = s.get("uses", "")
        if uses and not uses.startswith("./"):
            assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", uses), f"{uses}: pin it to a full commit SHA (# vX.Y.Z comment)"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_jobs_that_run_upstream_code_hold_no_credentials(path):
    for name, job, perms in jobs(path):
        if any(a.startswith(UPSTREAM_CODE) for a in patcher_args(job)):
            assert not writes(perms) and not logs_in(job), f"{path.name}/{name} runs upstream code: no write permission, no login"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_jobs_that_can_write_read_no_cache(path):
    for name, job, perms in jobs(path):
        if not writes(perms):
            continue
        for s in steps(job):
            if s.get("uses") == RUN_PATCHER:
                assert s["with"].get("image-cache") == "false" and not s["with"].get("cache-key"), f"{path.name}/{name}"
            assert "actions/cache@" not in s.get("uses", ""), f"{path.name}/{name}"


def test_release_jobs():
    release = {name: (job, perms) for name, job, perms in jobs(ROOT / ".github" / "workflows" / "release.yml")}
    by_command = {}
    for name, (job, _) in release.items():
        for a in patcher_args(job):
            by_command.setdefault(a.split()[0], []).append(name)
    assert by_command == {"release-build": ["build"], "release-push": ["push"], "publish": ["publish"]}
    build, perms = release["build"]
    assert perms == {"contents": "read"}
    # what it builds is released: it reads no cache another project's job could have written either
    assert all(s["with"].get("image-cache") == "false" and not s["with"].get("cache-key") for s in steps(build) if s.get("uses") == RUN_PATCHER)
    assert release["push"][1] == {"contents": "read", "packages": "write"}
