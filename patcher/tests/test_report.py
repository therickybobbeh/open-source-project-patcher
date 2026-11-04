"""The patch PR's report: what counts as fixed."""

from patcher.models import Recipe
from patcher.report import ImageOutcome, Summary, render_markdown
from patcher.scan import Finding, ScanReport


def finding(name, vuln="GO-2026-5932", fixed="0.58.1-0.20261009181718-2f1f834330b2", status=None, installed="v0.57.0"):
    return Finding(target="usr/local/bin/app", ecosystem="gobinary", trivy_type="gobinary", name=name, installed=installed,
                   fixed=fixed, vuln_id=vuln, severity="HIGH", status=status, pkg_path="usr/local/bin/app")


def test_a_vulnerability_still_in_the_file_under_another_module_is_not_counted_as_fixed():
    """x/crypto carved openpgp out into a module of its own: bumping x/crypto moves GO-2026-5932 to
    golang.org/x/crypto/openpgp, which has no fix, and the binary still has the code."""
    r = Recipe.model_validate({"name": "app", "source": {"repo": "o/app", "lines": [{"tagPattern": "x"}]}})
    before = ScanReport("upstream", [finding("golang.org/x/crypto"), finding("golang.org/x/net", vuln="CVE-1", fixed="0.62.0")])
    after = ScanReport("ours", [finding("golang.org/x/crypto/openpgp", fixed=None, status="affected", installed="v0.1.0-deprecated")])
    s = Summary(recipe=r, line="v1", tag="v1.0.0", commit="c0ffee", status="success",
                images=[ImageOutcome("app", "patcher.local/app:v1.0.0-patched.dev", "upstream", before, after)])
    md = render_markdown(s)
    assert "| image `app` | 0 / 2 / 0 / 0 | 0 / 0 / 0 / 0 | 1 | 0 |" in md  # x/net's fix only
    assert ("- `GO-2026-5932` is still in image `app` (`usr/local/bin/app`), in `golang.org/x/crypto/openpgp` "
            "v0.1.0-deprecated (no fix): not counted as fixed") in md


def test_the_report_says_what_each_image_runs_as():
    from patcher.report import runs_as
    from patcher.scan import ScanReport, parse_report

    image = lambda user: parse_report({"ArtifactName": "img", "Metadata": {"ImageConfig": {"config": {"User": user}}}})
    assert image("999").user == "999" and parse_report({"Metadata": {"ImageConfig": {"config": {}}}}).user == ""
    assert parse_report({"ArtifactName": ".", "Metadata": {}}).user is None  # a source scan: no image, no user
    assert [runs_as(image(u)) for u in ("999", "", "0", "dex:dex")] == ["`999`", "root (no `USER`)", "`0` (root)", "`dex:dex` (a name)"]
    assert runs_as(None) == runs_as(ScanReport("src")) == "-"
