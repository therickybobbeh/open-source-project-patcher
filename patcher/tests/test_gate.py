"""The release gate: the input the Rego policy sees, the policy itself (with conftest, when it is installed: the
patcher image and CI have it), and what a release does with a verdict. policy/gate_test.rego tests the rules alone."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from patcher import gate, pipeline
from patcher.config import Repo
from patcher.models import Gate, Recipe, VexFile
from patcher.scan import Finding, ScanReport

ROOT = Path(__file__).resolve().parents[2]
needs_conftest = pytest.mark.skipif(not shutil.which("conftest"), reason="conftest not installed (the patcher image has it)")


def finding(vuln: str, severity: str, fixed: str | None, name: str = "golang.org/x/net") -> Finding:
    return Finding(target="usr/local/bin/app", ecosystem="gomod", trivy_type="gobinary", name=name, installed="0.30.0",
                   fixed=fixed, vuln_id=vuln, severity=severity, status=None if fixed else "affected")


IMAGE = ScanReport("ghcr.io/me/app@sha256:d", [finding("CVE-1", "CRITICAL", "0.38.0"), finding("CVE-2", "HIGH", "0.38.0"),
                                               finding("CVE-3", "CRITICAL", None), finding("CVE-4", "LOW", "0.38.0")])


def recipe(**gate_fields) -> Recipe:
    return Recipe.model_validate({"name": "app", "source": {"repo": "o/app", "lines": [{"tagPattern": "x"}]},
                                  "build": {"images": [{"name": "app"}]}, "gate": gate_fields})


def test_the_input_names_each_finding_s_fix_and_the_vex_that_settles_it():
    vex = VexFile.model_validate({"statements": [{"vulnerability": "CVE-3", "status": "not_affected",
                                                  "justification": "vulnerable_code_not_in_execute_path"}]})
    doc = gate.gate_input("release", "app", "v1", "app", IMAGE.artifact, IMAGE, Gate.model_validate(
        {"failOn": {"fixable": ["CRITICAL", "HIGH"]}}), vex)
    assert doc["params"] == {"fixable": ["CRITICAL", "HIGH"], "unfixed": []} and doc["stage"] == "release"
    by_id = {f["id"]: f for f in doc["findings"]}
    assert by_id["CVE-1"] == {"id": "CVE-1", "severity": "CRITICAL", "package": "golang.org/x/net", "installed": "0.30.0",
                              "fixed": "0.38.0", "fixable": True, "ecosystem": "gomod", "location": "usr/local/bin/app",
                              "vex": None}
    assert by_id["CVE-3"]["fixable"] is False and by_id["CVE-3"]["vex"] == "not_affected"


@needs_conftest
@pytest.mark.parametrize("fail_on, denied", [
    ({}, []),  # nothing listed: nothing fails
    ({"fixable": ["CRITICAL"]}, ["CVE-1"]),  # the default in _global.yaml
    ({"fixable": ["CRITICAL", "HIGH"]}, ["CVE-1", "CVE-2"]),  # "stop on highs"
    ({"fixable": ["CRITICAL"], "unfixed": ["CRITICAL"]}, ["CVE-1", "CVE-3"]),  # and on criticals with no fix yet
], ids=["off", "critical", "high", "unfixed"])
def test_the_policy_denies_what_failOn_lists(fail_on, denied):
    doc = gate.gate_input("release", "app", "v1", "app", IMAGE.artifact, IMAGE, Gate.model_validate({"failOn": fail_on}), VexFile())
    verdict = gate.evaluate(ROOT / "policy", doc)
    assert sorted(m.split()[1] for m in verdict.deny) == denied and verdict.passed is (not denied)


@needs_conftest
def test_a_broken_policy_is_an_error_not_a_pass(tmp_path):
    (tmp_path / "gate.rego").write_text("package patcher.gate\n\ndeny contains msg if {\n")  # doesn't parse
    with pytest.raises(gate.GateError):
        gate.evaluate(tmp_path, {"findings": [], "params": {"fixable": [], "unfixed": []}})


def test_a_gate_that_cant_run_stops_only_an_enforced_release(monkeypatch, tmp_path):
    monkeypatch.setattr(gate.shutil, "which", lambda exe: None)  # no conftest
    images = [("app", IMAGE.artifact, IMAGE)]
    assert gate.check(tmp_path, "release", recipe(), "v1", images, VexFile()) == {}  # reported only: the run goes on
    with pytest.raises(gate.GateError, match="conftest is not installed"):
        gate.check(tmp_path, "release", recipe(enforce=True), "v1", images, VexFile())


def test_the_recipe_s_gate_fields_win_over_global(tmp_path):
    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text(yaml.safe_dump(
        {"registry": "ghcr.io/me", "gate": {"enforce": True, "failOn": {"fixable": ["CRITICAL"]}}}))
    doc = recipe(failOn={"unfixed": ["CRITICAL"]}).model_dump(exclude_unset=True)
    (tmp_path / "recipes" / "app.yaml").write_text(yaml.safe_dump(doc))
    g = Repo(tmp_path).load_recipe("app").gate
    assert g.enforce and g.failOn.fixable == ["CRITICAL"] and g.failOn.unfixed == ["CRITICAL"]


@pytest.mark.parametrize("enforce", [False, True])
def test_an_enforced_gate_stops_a_release_before_anything_is_recorded(tmp_path, monkeypatch, enforce):
    from test_release import app_recipe, fake_publish_tools, make_repo, registry, staging

    repo = make_repo(tmp_path, {**app_recipe(), "gate": {"enforce": enforce, "failOn": {"fixable": ["CRITICAL"]}}})
    registry(monkeypatch, staging(5, "amd64"), staging(5, "arm64"), staging(5, "amd64", True))
    fake_publish_tools(monkeypatch)
    seen = []
    monkeypatch.setattr(gate, "evaluate", lambda policy, doc: seen.append((doc["stage"], doc["image"]))
                        or gate.Verdict(deny=["CRITICAL CVE-1 in x 1 (y) is fixable: fixed in 2"] if doc["image"] == "app" else []))
    out = tmp_path / "out"
    if enforce:
        with pytest.raises(gate.GateDenied, match="the release gate denied app"):
            pipeline.publish(repo, repo.load_recipe("app"), "v1", None, out, revision=5)
        assert repo.state("app").lines["v1"].revision == 2 and not (out / "app" / "v1" / "release.json").exists()
    else:  # reported in the release record (the state PR's body), and released
        released = pipeline.publish(repo, repo.load_recipe("app"), "v1", None, out, revision=5)
        assert [r["gate"]["passed"] for r in released] == [False, True] and repo.state("app").lines["v1"].revision == 5
        assert json.loads((out / "app" / "v1" / "release.json").read_text())[0]["gate"]["deny"]
    assert seen == [("release", "app"), ("release", "app-debug")]  # every image's final scan, after Copa


@pytest.mark.parametrize("enforce", [False, True])
def test_the_patch_pr_shows_the_verdict_and_is_a_draft_if_the_release_would_stop(tmp_path, monkeypatch, enforce):
    from patcher.report import ImageOutcome, Summary

    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text("registry: ghcr.io/me\n")
    repo = Repo(tmp_path)
    s = Summary(recipe=recipe(enforce=enforce, failOn={"fixable": ["CRITICAL"]}), line="v1", tag="v1.2.3", commit="c0ffee",
                status="success", images=[ImageOutcome("app", "patcher.local/app:v1.2.3", None, None, IMAGE)])
    monkeypatch.setattr(gate, "evaluate", lambda policy, doc: gate.Verdict(deny=["CRITICAL CVE-1 in golang.org/x/net 0.30.0 "
                                                                                "(usr/local/bin/app) is fixable: fixed in 0.38.0"]))
    out = tmp_path / "out"
    out.mkdir()
    pipeline._write_outputs(repo, s, None, out)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["gate"]["app"]["passed"] is False and summary["draft"] is enforce
    report = (out / "pr-body.md").read_text()
    assert "### Release gate" in report and "⛔ **denied** (1)" in report and "CVE-1" in report
