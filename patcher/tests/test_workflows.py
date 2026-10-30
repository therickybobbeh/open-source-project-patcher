"""Guards on .github/: actions pinned to commits, and the release's trust boundary. Jobs that run upstream code hold
no credentials; jobs that can write (push images, sign, open PRs) read no cache, because any job on the branch can
write those, including the ones that run upstream code."""

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
ACTIONS = sorted((ROOT / ".github" / "actions").glob("*/action.yml"))
UPSTREAM_CODE = ("run ", "release-build ")  # patcher commands that build or test upstream code
RUN_PATCHER = "./.github/actions/run-patcher"
TRUSTED_POOL = re.compile(r"vars\.PATCHER_RUNS_ON(?:_ARM64)?(?![A-Z0-9_])")  # not the _UPSTREAM ones


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
        if not (writes(perms) or logs_in(job)):  # a write permission, a registry login or a secret (the App's key)
            continue
        for s in steps(job):
            uses, opts = s.get("uses", ""), s.get("with") or {}
            if uses == RUN_PATCHER:
                assert opts.get("image-cache") == "false" and not opts.get("cache-key"), f"{path.name}/{name}"
            if "/setup-uv@" in uses:
                assert opts.get("enable-cache") in (False, "false"), f"{path.name}/{name}: setup-uv needs enable-cache: false"
            assert "actions/cache@" not in uses, f"{path.name}/{name}"
            assert "type=gha" not in s.get("run", ""), f"{path.name}/{name}: no BuildKit cache from GitHub Actions"


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
    # `push` is skipped when a run builds nothing; a job after it with a plain condition would be skipped as well
    for name in ("publish", "attest", "state"):
        assert "!cancelled()" in str(release[name][0]["if"]), name
    # the state PR is made from publish's outputs, never from an artifact (any job of the run can write those)
    assert not any("download-artifact" in s.get("uses", "") for s in steps(release["state"][0]))


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_runners_come_from_the_runs_on_variables(path):
    """Self-hosted setups set PATCHER_RUNS_ON* (a runner group, labels or a scale set); unset means GitHub-hosted. Jobs
    that run code we don't vet (upstream builds and tests, PR code) use only the upstream pool: never the trusted one,
    which holds registry, signing and GitHub App credentials, not even as a fallback (check-runner-pools.sh)."""
    for name, job, _ in jobs(path):
        runs_on = str(job.get("runs-on", ""))
        assert "vars.PATCHER_RUNS_ON" in runs_on, f"{path.name}/{name}: take runs-on from vars.PATCHER_RUNS_ON*"
        if any(a.startswith(UPSTREAM_CODE) for a in patcher_args(job)):
            assert "PATCHER_RUNS_ON_UPSTREAM" in runs_on, f"{path.name}/{name} runs upstream code: PATCHER_RUNS_ON_UPSTREAM"
        if "PATCHER_RUNS_ON_UPSTREAM" in runs_on:
            assert not TRUSTED_POOL.search(runs_on), f"{path.name}/{name}: an upstream job must not fall back to the trusted pool"


def test_runner_pool_check_runs_before_upstream_work():
    for wf, job in [("patch.yml", "plan"), ("release.yml", "plan"), ("patcher-image.yml", "test")]:
        j = {n: jb for n, jb, _ in jobs(ROOT / ".github" / "workflows" / wf)}[job]
        assert any(s.get("run", "").strip() == "scripts/check-runner-pools.sh" for s in steps(j)), f"{wf}/{job}"


@pytest.mark.parametrize("env, ok, says", [
    ({}, True, ""),  # all GitHub-hosted
    ({"PATCHER_RUNS_ON": '{"group": "patcher"}'}, False, "PATCHER_RUNS_ON_UPSTREAM is not"),
    ({"PATCHER_RUNS_ON": '{"group": "patcher"}', "PATCHER_RUNS_ON_UPSTREAM": '{"group": "sandbox"}'}, True, ""),
    ({"PATCHER_RUNS_ON": '{"group": "patcher"}', "PATCHER_RUNS_ON_UPSTREAM": '"ubuntu-24.04"'}, True, ""),
    ({"PATCHER_RUNS_ON": '{"group": "patcher"}', "PATCHER_RUNS_ON_UPSTREAM": '{"group": "patcher"}'}, True, "::warning::"),
    ({"PATCHER_RUNS_ON_ARM64": '["arm64"]'}, False, "PATCHER_RUNS_ON_UPSTREAM_ARM64 is not"),
], ids=["unset", "trusted-only", "separate", "hosted-upstream", "same-pool", "arm64-only"])
def test_runner_pool_check(env, ok, says):
    r = subprocess.run([str(ROOT / "scripts" / "check-runner-pools.sh")], env={"PATH": os.environ["PATH"], **env},
                       capture_output=True, text=True)
    assert (r.returncode == 0) == ok and says in r.stdout, r.stdout


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_job_sets_a_timeout(path):
    """GitHub's default is 6 hours: a hung Sigstore call or registry would hold a runner (and the line's concurrency
    group) that long."""
    for name, job, _ in jobs(path):
        limit = job.get("timeout-minutes")
        assert isinstance(limit, int) and 0 < limit <= 360, f"{path.name}/{name}: set timeout-minutes (at most 360)"


def test_release_builds_default_to_the_native_runners():
    from patcher.pipeline import RUNNERS

    build = {name: job for name, job, _ in jobs(ROOT / ".github" / "workflows" / "release.yml")}["build"]
    for runner in RUNNERS.values():
        assert f'"{runner}"' in build["runs-on"], runner


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_host_changing_steps_run_only_on_github_hosted_runners(path):
    for name, job, _ in jobs(path):
        for s in steps(job):
            if re.search(r"systemctl|daemon\.json|rm -rf /(usr|opt)", s.get("run", "")):
                assert "runner.environment == 'github-hosted'" in str(s.get("if", "")), f"{path.name}/{name}: {s.get('name')}"
