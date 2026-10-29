"""Release-age gate, baseline test classification."""

import datetime as dt
import json

from patcher import releases
from patcher.models import Recipe
from patcher.planner import build_plan
from patcher.scan import parse_report
from patcher.tests_runner import TestOutcome, failed_ids, only_preexisting

NOW = dt.datetime(2026, 10, 28, tzinfo=dt.timezone.utc)


def recipe(**kw) -> Recipe:
    return Recipe.model_validate({"name": "demo", "source": {"repo": "o/r", "lines": [{"tagPattern": "x"}]}, **kw})


def report(severity="HIGH", vuln="CVE-2026-1", fixed="0.33.0, 0.34.0"):
    return parse_report({"Results": [{"Target": "go.mod", "Class": "lang-pkgs", "Type": "gomod", "Packages": [], "Vulnerabilities": [
        {"VulnerabilityID": vuln, "PkgName": "golang.org/x/net", "InstalledVersion": "v0.30.0", "FixedVersion": fixed,
         "Status": "fixed", "Severity": severity}]}]})


def gate(published: dict, kev=()):
    def fetch(url, method="GET"):
        for version, when in published.items():
            if url.endswith(f"/@v/{version}.info"):
                return {}, json.dumps({"Version": version, "Time": when}).encode()
        raise OSError("not found")

    return releases.AgeGate(7, {"CRITICAL"}, set(kev), releases.ReleaseAges(fetch=fetch), now=NOW)


def test_too_new_fix_is_deferred_and_older_candidate_used():
    g = gate({"v0.33.0": "2026-10-26T00:00:00Z", "v0.34.0": "2026-09-01T00:00:00Z"})
    plan = build_plan(report(), recipe(), gate=g)
    # 0.33.0 is two days old: the next fixed version that is old enough wins
    assert [b.to for b in plan.bumps] == ["v0.34.0"]


def test_all_fixes_too_new_reports_cooldown():
    g = gate({"v0.33.0": "2026-10-26T00:00:00Z", "v0.34.0": "2026-10-27T00:00:00Z"})
    plan = build_plan(report(), recipe(), gate=g)
    assert not plan.bumps
    assert plan.unresolved[0].why == "cooldown: v0.33.0 released 2 day(s) ago (eligible 2026-11-02)"


def test_critical_and_kev_bypass_the_wait():
    fresh = {"v0.33.0": "2026-10-27T00:00:00Z"}
    assert [b.to for b in build_plan(report(severity="CRITICAL", fixed="0.33.0"), recipe(), gate=gate(fresh)).bumps] == ["v0.33.0"]
    assert [b.to for b in build_plan(report(vuln="CVE-KEV", fixed="0.33.0"), recipe(), gate=gate(fresh, kev={"CVE-KEV"})).bumps] == ["v0.33.0"]


def test_unknown_release_date_is_allowed_with_a_note():
    plan = build_plan(report(fixed="0.33.0"), recipe(), gate=gate({}))
    assert [b.to for b in plan.bumps] == ["v0.33.0"]
    assert plan.notes and "unknown" in plan.notes[0]


def test_go_module_path_escaping():
    assert releases.go_escape("github.com/BurntSushi/toml") == "github.com/!burnt!sushi/toml"


def test_preexisting_classification():
    patched = TestOutcome(ran=True, passed=False, failed=["TestA", "TestB"])
    base = TestOutcome(ran=True, passed=False, failed=["TestA", "TestB", "TestC"])
    assert only_preexisting(patched, base)
    assert not only_preexisting(TestOutcome(ran=True, passed=False, failed=["TestA", "TestNew"]), base)
    assert not only_preexisting(TestOutcome(ran=True, passed=False, failed=[]), base)   # unidentifiable failures
    assert not only_preexisting(patched, TestOutcome(ran=True, passed=True))
    assert failed_ids("go", "--- FAIL: TestX (0.00s)\n    --- FAIL: TestX/sub (0.00s)\nFAIL\tpkg\t0.1s") == ["FAIL pkg", "TestX", "TestX/sub"]


def test_failure_ids_ignore_timing_and_noise():
    # the same failure in the patched and the baseline run must produce the same ids
    patched = "--- FAIL: TestConsul (20.44s)\npanic: runtime error: invalid memory address [recovered]\nFAIL\tgithub.com/x/integration\t24.062s\nFAIL"
    baseline = "--- FAIL: TestConsul (20.51s)\npanic: runtime error: invalid memory address [recovered]\nFAIL\tgithub.com/x/integration\t23.9s\nFAIL"
    assert failed_ids("go", patched) == failed_ids("go", baseline) == ["FAIL github.com/x/integration", "TestConsul"]
    assert failed_ids("go", "FAIL workflow/http.TestLoad/Found (32.94s)") == ["FAIL workflow/http.TestLoad/Found"]
    assert failed_ids("pytest", "FAILED tests/test_a.py::test_x - AssertionError: port 51234\n=== 1 failed, 9 passed in 3.2s ===") == [
        "FAILED tests/test_a.py::test_x"]
    assert failed_ids("jest", "  ✕ renders the page (12 ms)") == ["✕ renders the page"]
    assert failed_ids("bats", "not ok 12 builds the image") == ["not ok builds the image"]
    assert failed_ids("gradle", "OwnerTests > findAll() FAILED\n12 tests completed, 1 failed") == ["OwnerTests > findAll() FAILED"]


def test_govulncheck_stream_and_suggestions(monkeypatch, tmp_path):
    from patcher import reach
    from patcher.scan import Finding

    stream = (json.dumps({"config": {}}, indent=2) + "\n" +
              json.dumps({"osv": {"id": "GO-2026-1", "aliases": ["CVE-2026-11", "GHSA-a"]}}, indent=2) +
              json.dumps({"osv": {"id": "GO-2026-2", "aliases": ["CVE-2026-22"]}}) +
              json.dumps({"finding": {"osv": "GO-2026-1", "trace": [{"module": "m", "package": "m/p"}]}}) +
              json.dumps({"finding": {"osv": "GO-2026-2", "trace": [{"module": "m", "package": "m/q", "function": "F"}]}}))
    monkeypatch.setattr(reach, "output", lambda *a, **k: stream)
    levels = reach.go_reachability(tmp_path, ["."], {})
    assert levels["CVE-2026-11"] == "imported" and levels["CVE-2026-22"] == "called"
    f = lambda vid: Finding("go.mod", "gomod", "gomod", "github.com/docker/docker", "v28.5.2", None, vid, "MEDIUM", "affected")
    sugg = reach.vex_suggestions([f("CVE-2026-11"), f("CVE-2026-22"), f("CVE-unknown")], levels)
    assert [(s["vulnerability"], s["justification"]) for s in sugg] == [("CVE-2026-11", "vulnerable_code_not_in_execute_path")]


def test_malicious_check_only_flags_mal_advisories(monkeypatch, tmp_path):
    from patcher import reach

    osv = {"results": [{"source": {"path": "ui/package-lock.json"}, "packages": [
        {"package": {"name": "evil-pkg", "version": "1.0.1"}, "vulnerabilities": [{"id": "MAL-2026-123"}]},
        {"package": {"name": "lodash", "version": "4.17.20"}, "vulnerabilities": [{"id": "GHSA-xyz"}]}]}]}
    monkeypatch.setattr(reach, "which", lambda n: "/usr/bin/osv-scanner")
    monkeypatch.setattr(reach, "output", lambda *a, **k: json.dumps(osv))
    hits, note = reach.malicious(tmp_path, ["ui/package-lock.json", "README.md"], {})
    assert hits == [{"id": "MAL-2026-123", "package": "evil-pkg", "version": "1.0.1", "lockfile": "ui/package-lock.json"}] and not note
    assert reach.malicious(tmp_path, ["README.md"], {}) == ([], "")


def test_install_cutoff_for_test_environments():
    released = dt.datetime(2026, 10, 20, 19, 49, tzinfo=dt.timezone.utc)
    # an old release: installs see nothing from the last 7 days
    assert releases.install_cutoff_env(7, released, now=NOW) == {"UV_EXCLUDE_NEWER": "2026-10-21T00:00:00Z",
                                                                "PIP_UPLOADED_PRIOR_TO": "2026-10-21T00:00:00Z",
                                                                "npm_config_before": "2026-10-21T00:00:00Z"}
    # a fresh release: its own lockfiles must still resolve, so the cutoff is the release time
    fresh = dt.datetime(2026, 10, 27, 8, 0, tzinfo=dt.timezone.utc)
    assert releases.install_cutoff_env(7, fresh, now=NOW)["UV_EXCLUDE_NEWER"] == "2026-10-27T08:00:00Z"
    g = gate({"v0.33.0": "2026-10-27T00:00:00Z"})
    build_plan(report(severity="HIGH", fixed="0.33.0"), recipe(), gate=g)
    assert not g.bypassed_fresh
    build_plan(report(severity="CRITICAL", fixed="0.33.0"), recipe(), gate=g)
    assert g.bypassed_fresh  # a 1-day-old CRITICAL fix: test installs must be able to see it


def test_trivy_db_is_fetched_once_with_retries(monkeypatch):
    from patcher import scan
    from patcher.proc import CommandError

    calls, sleeps = [], []

    def fake_run(args, **k):
        calls.append(args[2])
        if len(calls) < 3:  # the vuln DB pull breaks off twice
            raise CommandError(" ".join(args), 1, "FATAL failed to download vulnerability DB: unexpected EOF")

    monkeypatch.setattr(scan, "run", fake_run)
    monkeypatch.setattr(scan.time, "sleep", sleeps.append)
    monkeypatch.setattr(scan, "_db_ready", False)
    scan.ensure_db()
    scan.ensure_db()  # once per process
    assert calls == ["--download-db-only"] * 3 + ["--download-java-db-only"] and sleeps == [30, 60]
    assert "--skip-db-update" in scan._common(["HIGH"])


def test_run_timeout_kills_a_silent_process_tree():
    import time

    import pytest

    from patcher.proc import CommandError, run

    start = time.monotonic()
    with pytest.raises(CommandError) as e:
        # prints once, then hangs silently in a child that holds the output pipe (like a stuck test)
        run("echo started; sleep 30 & wait", timeout=1, capture=True)
    assert time.monotonic() - start < 10
    assert "timed out after 1s" in e.value.tail and "started" in e.value.tail


def test_same_setup_failure_on_both_sides_is_an_environment_problem():
    from patcher.tests_runner import same_setup_failure

    def failed_run(tail):
        return TestOutcome(ran=True, passed=False, failed=[], tail=tail)

    patched = failed_run("go: copying /tmp/go-build2206174378/b001/exe/a.out: open /opt/mise/installs/go/1.26.10/bin/x: "
                         "permission denied\nmake: *** [Makefile:449: test-local] Error 1")
    baseline = failed_run("go: copying /tmp/go-build99/b001/exe/a.out: open /opt/mise/installs/go/1.26.10/bin/x: "
                          "permission denied\nmake: *** [Makefile:449: test-local] Error 1")
    assert same_setup_failure(patched, baseline)
    from patcher.tests_runner import setup_error

    assert setup_error(patched.tail).endswith("permission denied")  # the cause, not make's summary line
    # a compile error only the bumps cause is a different signature
    broken = failed_run("/work/argo-cd/v3.5/src/util/x.go:12: undefined: jose.Foo\nmake: *** [Makefile:449: test-local] Error 1")
    assert not same_setup_failure(broken, baseline)
    assert not same_setup_failure(TestOutcome(ran=True, passed=False, failed=["TestA"], tail="x error"), baseline)


def test_withdrawn_fix_versions_are_replaced():
    # lodash 4.18.0 was marked "Bad release" on npm the day after it shipped; 4.18.1 fixed it
    doc = {"versions": {"4.17.21": {}, "4.18.0": {"deprecated": "Bad release. Please use lodash@4.17.21 instead."},
                        "4.18.1": {}, "5.0.0-beta.1": {}},
           "time": {"4.17.21": "2021-02-20T15:42:16Z", "4.18.0": "2026-03-31T18:18:42Z", "4.18.1": "2026-04-01T21:01:20Z"}}

    def fetch(url, method="GET"):
        assert url == "https://registry.npmjs.org/lodash"
        return {}, json.dumps(doc).encode()

    g = releases.AgeGate(7, {"CRITICAL"}, set(), releases.ReleaseAges(fetch=fetch), now=NOW)
    rep = parse_report({"Results": [{"Target": "ui/pnpm-lock.yaml", "Class": "lang-pkgs", "Type": "pnpm", "Packages": [],
                                     "Vulnerabilities": [{"VulnerabilityID": "CVE-2026-4800", "PkgName": "lodash",
                                                          "InstalledVersion": "4.17.21", "FixedVersion": "4.18.0",
                                                          "Status": "fixed", "Severity": "CRITICAL"}]}]})
    plan = build_plan(rep, recipe(ecosystems=[{"type": "pnpm", "dirs": ["ui"]}]), gate=g)
    assert [(b.name, b.to) for b in plan.bumps] == [("lodash", "4.18.1")]  # even CRITICAL never gets the withdrawn one
    assert any("withdrawn" in n and "4.18.1" in n for n in plan.notes)
    assert g.check("pnpm", "lodash", "4.18.0", "CRITICAL", "CVE-2026-4800")[1].startswith("4.18.0 was withdrawn by its registry")


def test_timed_out_suite_reports_duration_and_last_output(tmp_path):
    from patcher.models import SkipFile, Tests
    from patcher.tests_runner import run_tests

    tests = Tests(framework="pytest", command="echo 'tests/test_pages.py::test_token_page'; sleep 30 & wait", timeoutMinutes=1)
    tests.timeoutMinutes = 0.02  # ~1 second, for the test
    out = run_tests(tmp_path, tests, SkipFile(), tmp_path / "out", {}, grace_days=30)
    assert not out.passed and out.seconds >= 1
    assert out.note.startswith("The suite timed out after") and "test_token_page" in out.note


def test_an_out_of_memory_test_build_is_an_environment_problem(tmp_path):
    from patcher.models import SkipFile, Tests
    from patcher.tests_runner import run_tests

    # what Splunk's `go test -race` printed in an 8 GB VM: the compiler killed, in a different package each run
    killed = "github.com/aws/aws-sdk-go-v2/service/ec2: /opt/go/pkg/tool/linux_arm64/compile: signal: killed"
    tests = Tests(framework="go", command=f"echo '{killed}'; echo 'FAIL github.com/x/baseline [build failed]'; exit 1")
    out = run_tests(tmp_path, tests, SkipFile(), tmp_path / "out", {}, grace_days=30)
    assert not out.passed and out.oom
    assert "out of memory" in out.note and "service/ec2" in out.note
    plain = run_tests(tmp_path, Tests(framework="go", command="echo '--- FAIL: TestX (0.00s)'; exit 1"), SkipFile(),
                      tmp_path / "out2", {}, grace_days=30)
    assert not plain.oom and plain.note == ""
