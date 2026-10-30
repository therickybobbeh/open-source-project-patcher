"""Which lines need a run, and how much of one: settled lines, merged patch sets, rebuild-only patch sets."""

import json

import pytest
import yaml

from patcher import pipeline, upstream
from patcher.adapters.base import Result
from patcher.config import Repo
from patcher.models import Recipe
from patcher.planner import Plan, Unresolved
from patcher.report import ImageOutcome
from patcher.scan import parse_report

XNET = {"VulnerabilityID": "CVE-2026-1", "PkgName": "golang.org/x/net", "InstalledVersion": "v0.61.0", "FixedVersion": "0.62.0",
        "Status": "fixed", "Severity": "UNKNOWN"}
DEPS = [{"Name": "golang.org/x/net", "Version": "v0.61.0"}, {"Name": "golang.org/x/text", "Version": "v0.42.0"}]
SOURCE = parse_report({"Results": [{"Target": "go.mod", "Class": "lang-pkgs", "Type": "gomod", "Packages": DEPS}]})
DEFERRED = [Unresolved("gomod", "go.mod", "golang.org/x/net", "v0.61.0", "CVE-2026-1", "UNKNOWN", "0.62.0",
                       "cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03)")]


def image(*results):
    return parse_report({"Results": list(results)})


def gobinary(path, vulns=(), deps=DEPS):
    return {"Target": path, "Class": "lang-pkgs", "Type": "gobinary", "Packages": deps, "Vulnerabilities": list(vulns)}


def app(**spec) -> Recipe:
    return Recipe.model_validate({"name": "app", "source": {"repo": "o/app", "lines": [{"tagPattern": r"^v1\.2\.\d+$"}]},
                                  "build": {"images": [{"name": "app", "upstream": "ghcr.io/o/app", **spec}]}})


def settled(recipe, scan, changes=(), unresolved=DEFERRED):
    return pipeline._settled(recipe, {"app": ("ghcr.io/o/app:v1.2.3", scan)}, list(changes), {}, list(unresolved), SOURCE)


def test_a_line_is_settled_when_its_image_only_has_what_the_source_plan_left():
    # external-secrets v2.14.0: the x/net fix in its own binary is younger than the release-age rule, so a rebuild
    # would ship the same finding again
    assert settled(app(), image(gobinary("usr/bin/app", [XNET])))
    assert settled(app(), image(gobinary("usr/bin/app")))
    openssl = {"Target": "app (alpine 3.22)", "Class": "os-pkgs", "Type": "alpine", "Packages": [],
               "Vulnerabilities": [{**XNET, "PkgName": "openssl", "InstalledVersion": "3.5.1-r0", "FixedVersion": "3.5.2-r0"}]}
    stdlib = {**XNET, "PkgName": "stdlib", "InstalledVersion": "v1.25.1", "FixedVersion": "1.25.2"}
    helm = gobinary("usr/local/bin/helm", [XNET], deps=DEPS[:1] + [{"Name": "helm.sh/helm/v4", "Version": "v4.2.1"}])
    assert not settled(app(), image(gobinary("usr/bin/app", [XNET]), openssl))  # Copa or a newer base may fix it
    assert not settled(app(), image(gobinary("usr/bin/app", [stdlib])),  # a newer Go toolchain may fix it
                       unresolved=DEFERRED + [Unresolved("gomod", "go.mod", "stdlib", "v1.25.1", "CVE-2026-1", "", "", "")])
    assert not settled(app(), image(helm))  # a bundled binary: a component may replace it
    assert not settled(app(copa={"libraries": True}), image(gobinary("usr/bin/app", [XNET])))
    assert not settled(app(), image(gobinary("usr/bin/app", [XNET])), unresolved=[])  # not one the plan left
    assert not settled(app(), image(gobinary("usr/bin/app", [{**XNET, "InstalledVersion": "v0.60.0"}])))  # another copy
    assert not settled(app(), image(gobinary("usr/bin/app", [XNET])), changes=["a bump"])
    assert not settled(app(), None)  # upstream's image couldn't be scanned


def test_a_settled_line_stops_after_the_scans(tmp_path, monkeypatch):
    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text("registry: ghcr.io/me\n")
    recipe = app()
    monkeypatch.setattr(upstream, "resolve_line", lambda source, line: ("v1.2.3", "c0ffee"))
    monkeypatch.setattr(pipeline, "scan_image", lambda ref, out, **k: image(gobinary("usr/bin/app", [XNET])))
    seen = {}

    def attempt(repo, recipe, tag, commit, out, opts, fs_before, extra=None, upstream_images=None):
        seen["images"] = upstream_images
        att = pipeline.Attempt("full plan", tmp_path / "src", {}, Plan(), Result(), DEFERRED, {}, SOURCE, "", None, settled=True)
        return att, SOURCE, ["full plan: tests not run"]

    monkeypatch.setattr(pipeline, "_attempt_with_retry", attempt)
    monkeypatch.setattr(pipeline, "_build_and_scan", lambda *a, **k: pytest.fail("a settled line must not be built"))
    opts = pipeline.RunOptions(workdir=tmp_path / "work", out=tmp_path / "out")
    s = pipeline.run_line(Repo(tmp_path), recipe, recipe.source.lines[0], opts)
    assert list(seen["images"]) == ["app"]
    assert s.status == "no-changes" and "the tests and the image build were skipped" in s.notes[-1]
    summary = json.loads((tmp_path / "out" / "app" / "v1.2" / "summary.json").read_text())
    assert summary["status"] == "no-changes" and summary["images"][0]["ref"] == "ghcr.io/o/app:v1.2.3"


def test_a_rebuild_that_fixes_image_findings_is_worth_a_release():
    theirs = image(gobinary("usr/bin/app", [XNET]))
    assert pipeline._rebuild_delta([ImageOutcome("app", "ours", "theirs", theirs, image(gobinary("usr/bin/app")))]) == (1, 0)
    # the same binary at another path is different, not better
    moved = image(gobinary("bin/app", [XNET]))
    assert pipeline._rebuild_delta([ImageOutcome("app", "ours", "theirs", theirs, moved)]) == (1, 1)
    assert pipeline._rebuild_delta([ImageOutcome("app", "ours", None, None, moved)]) == (0, 0)  # no upstream image


AMD64 = {"platform": "linux/amd64", "arch": "amd64"}  # where a patch run builds unless PATCHER_PLATFORMS says otherwise


def test_the_nightly_run_skips_a_tag_whose_patch_set_is_merged(tmp_path, monkeypatch):
    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text("registry: ghcr.io/me\n")
    for name in ("app", "other"):
        (tmp_path / "recipes" / f"{name}.yaml").write_text(yaml.safe_dump(
            {"name": name, "source": {"repo": f"o/{name}", "lines": [{"tagPattern": r"^v1\.2\.\d+$"}]},
             "build": {"images": [{"name": name}]}}))
    merged = tmp_path / "generated" / "app" / "v1.2.3"
    merged.mkdir(parents=True)
    (merged / "bump-plan.json").write_text(json.dumps({"recipe": "app", "line": "v1.2", "tag": "v1.2.3", "commit": "c0ffee"}))
    repo = Repo(tmp_path)
    monkeypatch.setattr(upstream, "list_tags", lambda url: {"v1.2.3": "c0ffee"})
    # released or not (a failed release, `publish: false`), the merged patch set is done: no second PR for it
    assert pipeline.plan_matrix(repo) == [{"recipe": "other", "line": "v1.2", **AMD64}]
    monkeypatch.setattr(upstream, "list_tags", lambda url: {"v1.2.3": "c0ffee", "v1.2.4": "decade"})
    assert pipeline.plan_matrix(repo) == [{"recipe": "app", "line": "v1.2", **AMD64}, {"recipe": "other", "line": "v1.2", **AMD64}]


def test_one_recipe_that_cant_be_planned_doesnt_stop_the_others(tmp_path, monkeypatch):
    from patcher.proc import CommandError

    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text("registry: ghcr.io/me\n")
    for name in ("app", "gone", "other"):
        (tmp_path / "recipes" / f"{name}.yaml").write_text(yaml.safe_dump(
            {"name": name, "source": {"repo": f"o/{name}", "lines": [{"tagPattern": r"^v1\.2\.\d+$"}]},
             "build": {"images": [{"name": name}]}}))
    (tmp_path / "recipes" / "broken.yaml").write_text("name: broken\nbogus: 1\n")  # not a valid recipe
    repo = Repo(tmp_path)

    def list_tags(url):
        if "/gone" in url:
            raise CommandError(f"git ls-remote --tags {url}", 128, "fatal: repository not found")
        return {"v1.2.3": "c0ffee"}

    monkeypatch.setattr(upstream, "list_tags", list_tags)
    errors = []
    assert pipeline.plan_matrix(repo, errors=errors) == [{"recipe": "app", "line": "v1.2", **AMD64},
                                                         {"recipe": "other", "line": "v1.2", **AMD64}]
    assert [e["recipe"] for e in errors] == ["broken", "gone"]
    assert errors[1]["error"].endswith("fatal: repository not found")  # the command and why it failed
    # a push: the recipe it changed is planned, though another recipe file is broken
    errors.clear()
    assert pipeline.plan_matrix(repo, changed_files=["recipes/app.yaml"], errors=errors) == [{"recipe": "app", "line": "v1.2", **AMD64}]
    assert [e["recipe"] for e in errors] == ["broken"]
    with pytest.raises(Exception, match="broken|bogus"):  # without `errors`, the first error is raised
        pipeline.plan_matrix(repo)


def test_an_edit_to_comments_or_prose_runs_nothing(tmp_path):
    import subprocess

    def git(*args):
        return subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                              check=True, capture_output=True, text=True).stdout.strip()

    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text("registry: ghcr.io/me\n")
    recipe = {"name": "app", "description": "an app", "source": {"repo": "o/app", "lines": [{"tagPattern": r"^v1\.2\.\d+$"}]},
              "build": {"images": [{"name": "app"}]}}
    (tmp_path / "recipes" / "app.yaml").write_text(yaml.safe_dump(recipe))
    git("init", "-q")
    git("add", "-A")
    git("commit", "-qm", "one")
    before = git("rev-parse", "HEAD")
    (tmp_path / "recipes" / "app.yaml").write_text("# why we track this\n" + yaml.safe_dump(
        {**recipe, "description": "the app", "notes": ["a note"]}))
    (tmp_path / "recipes" / "_global.yaml").write_text("# org-wide policy\nregistry: ghcr.io/me\n")  # would re-run every line
    repo = Repo(tmp_path)
    assert pipeline.plan_matrix(repo, changed_files=["recipes/app.yaml", "recipes/_global.yaml"], before=before) == []
    # without the commit before the push, every change counts
    assert pipeline.plan_matrix(repo, changed_files=["recipes/app.yaml"]) == [{"recipe": "app", "line": "v1.2", **AMD64}]
    (tmp_path / "recipes" / "app.yaml").write_text(yaml.safe_dump({**recipe, "build": {"images": [{"name": "app", "target": "prod"}]}}))
    assert pipeline.plan_matrix(repo, changed_files=["recipes/app.yaml"], before=before) == [{"recipe": "app", "line": "v1.2", **AMD64}]
