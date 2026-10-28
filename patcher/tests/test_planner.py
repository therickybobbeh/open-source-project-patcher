import json
from pathlib import Path

from patcher.models import Hold, Level, Override, Policy, Recipe
from patcher.planner import build_plan
from patcher.scan import parse_report

FIXTURES = Path(__file__).parent / "fixtures"


def recipe(**kw) -> Recipe:
    base = {"name": "demo", "source": {"repo": "o/r", "lines": [{"tagPattern": "^v1\\."}]}}
    base.update(kw)
    return Recipe.model_validate(base)


def report():
    return parse_report(json.loads((FIXTURES / "trivy-fs-gomod.json").read_text()))


def test_plan_picks_lowest_fix_per_package_and_max_across_cves():
    plan = build_plan(report(), recipe())
    by = {(b.target, b.name): b for b in plan.bumps}
    net = by[("go.mod", "golang.org/x/net")]
    # two CVEs: fixed in 0.33.0 and 0.36.0 -> max of the lowest picks, with Go's `v` prefix
    assert net.to == "v0.36.0"
    assert net.level == "minor"
    assert net.reasons == ["CVE-2024-45338", "CVE-2025-22870"]
    assert net.direct is False
    # nested module keeps its own target
    assert ("api/v2/go.mod", "google.golang.org/grpc") in by


def test_stdlib_becomes_toolchain_requirement():
    plan = build_plan(report(), recipe())
    assert plan.toolchain == {"go": "1.27.5"}
    assert not any(b.name == "stdlib" for b in plan.bumps)


def test_policy_cap_marks_major_bumps_needs_human():
    plan = build_plan(report(), recipe(policy=Policy(default=Level.patch)))
    names = {b.name for b in plan.bumps}
    assert "golang.org/x/net" not in names  # needs a minor bump
    assert any(u.name == "golang.org/x/net" and u.why.startswith("needs-human") for u in plan.unresolved)


def test_hold_and_override():
    r = recipe(
        holds={"gomod": [Hold(name="google.golang.org/*", reason="upstream pin")]},
        overrides={"gomod": [Override(name="golang.org/x/crypto", min="v0.40.0", reason="org baseline")]},
    )
    plan = build_plan(report(), r)
    names = {b.name for b in plan.bumps}
    assert "google.golang.org/grpc" not in names
    assert any(u.name == "google.golang.org/grpc" and u.why.startswith("held") for u in plan.unresolved)
    crypto = next(b for b in plan.bumps if b.name == "golang.org/x/crypto")
    assert crypto.to == "v0.40.0" and crypto.reasons == ["override: org baseline"]


def test_unfixed_findings_are_reported_not_planned():
    plan = build_plan(report(), recipe())
    assert any(u.vuln_id == "CVE-2099-0001" and u.why == "no fixed version" for u in plan.unresolved)


def test_bundled_binary_detection():
    from patcher.report import ImageOutcome, bundled_paths
    from patcher.scan import Package, ScanReport

    fs_after = ScanReport("src", packages=[Package("go.mod", "gomod", "golang.org/x/net", "v0.60.0", "x"),
                                           Package("go.mod", "gomod", "github.com/a/b", "v1.0.0", "y")])
    after = ScanReport("img", packages=[
        Package("usr/local/bin/app", "gobinary", "golang.org/x/net", "v0.60.0", "1"),
        Package("usr/local/bin/app", "gobinary", "github.com/a/b", "v1.0.0", "2"),
        Package("usr/local/bin/app", "gobinary", "stdlib", "v1.27.3", "3"),
        Package("usr/local/bin/tool", "gobinary", "golang.org/x/net", "v0.56.0", "4"),
        Package("usr/local/bin/tool", "gobinary", "github.com/c/d", "v2.0.0", "5"),
    ])
    img = ImageOutcome("app", "ref", None, None, after)
    assert bundled_paths(img, fs_after) == {"usr/local/bin/tool"}
    img.own_binaries = ["/usr/local/bin/tool"]
    assert bundled_paths(img, fs_after) == {"usr/local/bin/app"}
