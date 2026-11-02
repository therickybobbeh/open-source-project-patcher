"""Bundled-binary components, Copa library patching, component routing in the plan."""

import pytest
import yaml
from pydantic import ValidationError

from patcher import components
from patcher.models import ComponentRef, Recipe
from patcher.proc import Result
from patcher.scan import Package, ScanReport


def comp_recipe(**kw) -> Recipe:
    return Recipe.model_validate({"name": "helm", "mode": "component", "source": {"repo": "helm/helm", "lines": [{"tagPattern": "x"}]},
                                  "artifact": {"build": "go build -o /out/helm ./cmd/helm", "output": "/out/helm"}, **kw})


def test_component_recipe_validation():
    with pytest.raises(ValidationError):
        Recipe.model_validate({"name": "x", "mode": "component", "source": {"repo": "o/r", "lines": [{"tagPattern": "x"}]}})
    assert comp_recipe().artifact.output == "/out/helm"


def test_version_detection_order(tmp_path, monkeypatch):
    scan = ScanReport("img", packages=[Package("usr/local/bin/helm", "gobinary", "helm.sh/helm/v4", "v4.2.1", "1", relationship="root"),
                                       Package("usr/local/bin/kustomize", "gobinary", "sigs.k8s.io/kustomize/kustomize/v5", "(devel)", "2",
                                               relationship="root")])
    (tmp_path / "hack").mkdir()
    (tmp_path / "hack" / "tool-versions.sh").write_text("kustomize5_version=5.8.1\ngit_lfs_version=3.7.1\n")
    ref = lambda **kw: ComponentRef(recipe="x", **kw)
    assert components.find_version(ref(path="/usr/local/bin/helm", version="4.0.0"), scan, tmp_path, None, "linux/arm64") == ("4.0.0", "pinned")
    assert components.find_version(ref(path="/usr/local/bin/helm"), scan, tmp_path, None, "linux/arm64") == ("4.2.1", "Go build info")
    kz = ref(path="/usr/local/bin/kustomize", versionFrom={"file": "hack/tool-versions.sh", "var": "kustomize5_version"})
    assert components.find_version(kz, scan, tmp_path, None, "linux/arm64") == ("5.8.1", "hack/tool-versions.sh")
    # (devel) build info is ignored; versionCommand runs the binary in the image
    monkeypatch.setattr("patcher.build.run", lambda *a, **k: Result(0, "git-lfs/3.7.1 (GitHub; linux arm64; go 1.24.4)\n", 0.1))
    pulls = []
    monkeypatch.setattr(components, "run", lambda cmd, **k: pulls.append(cmd) or Result(0, "", 0.1))
    lfs = ref(path="/usr/local/bin/git-lfs", versionCommand=["version"])
    assert components.find_version(lfs, scan, None, "img:ref", "linux/arm64") == ("3.7.1", "`/usr/local/bin/git-lfs version`")
    assert pulls[0][:3] == ["docker", "pull", "--quiet"]  # pulled first, so pull messages can't be mistaken for the version
    assert components.find_version(ref(path="/usr/local/bin/kustomize"), scan, None, None, "linux/arm64") == (None, "")


def test_overlay_dockerfile(tmp_path):
    (tmp_path / "go.mod").write_text("module helm.sh/helm/v4\n\ngo 1.25.3\n")
    c = components.Component(ComponentRef(recipe="helm", path="/usr/local/bin/helm"), comp_recipe(
        artifact={"build": "go build -ldflags '-X v={{tag}}' -o /out/helm ./cmd/helm", "output": "/out/helm"}),
        version="4.2.1", tag="v4.2.1", status="success", src=tmp_path)
    df = components.overlay_dockerfile("patcher.local/argocd:v3.5.6-patched.dev", [c])
    assert df.splitlines() == [
        "FROM --platform=$BUILDPLATFORM golang:1.25 AS comp0", "WORKDIR /src", "COPY --from=comp0-src . .",
        "ARG TARGETOS TARGETARCH", "RUN go build -ldflags '-X v=v4.2.1' -o /out/helm ./cmd/helm", "",
        "FROM patcher.local/argocd:v3.5.6-patched.dev", "COPY --from=comp0 /out/helm /usr/local/bin/helm"]
    assert c.usable and not components.Component(c.ref, c.recipe, status="tests-failed", src=tmp_path).usable


def test_applicable_filters_by_image():
    r = Recipe.model_validate({"name": "op", "mode": "image-only", "source": {"repo": "x", "lines": [{"tagPattern": "x"}]},
                               "components": [{"recipe": "a", "path": "/a", "images": ["op"]}, {"recipe": "b", "path": "/b"}]})
    assert [c.recipe for c in components.applicable(r, "op")] == ["a", "b"]
    assert [c.recipe for c in components.applicable(r, "loader")] == ["b"]


def test_copa_options_and_library_args(monkeypatch, tmp_path):
    from patcher import copa
    from patcher.models import ImageSpec

    assert ImageSpec(name="a").copa_enabled and not ImageSpec(name="a").copa_options.libraries
    assert not ImageSpec(name="a", copa=False).copa_enabled
    opts = ImageSpec.model_validate({"name": "a", "copa": {"libraries": True, "level": "minor"}}).copa_options
    assert opts.libraries and opts.level.value == "minor"

    calls = []

    class Rep:
        def fixable(self):
            return ["one"]

    def fake_scan(image, path, **k):
        calls.append(("scan", k["pkg_types"]))
        path.write_text("{}")
        return Rep()

    monkeypatch.setattr(copa, "scan_image", fake_scan)
    monkeypatch.setattr(copa, "which", lambda n: "/usr/local/bin/copa")
    monkeypatch.setattr(copa, "run", lambda args, env=None, **k: calls.append(("copa", args, env)))
    res = copa.patch("ghcr.io/x/app:1.0", "1.0-copa", tmp_path / "a", platforms=["linux/amd64"], severities=["HIGH"],
                     libraries=True, level="minor")
    assert res.patched_ref == "ghcr.io/x/app:1.0-copa"
    (_, pkg_types), (_, args, env) = calls
    assert pkg_types == "os,library" and env == {"COPA_EXPERIMENTAL": "1"}
    assert args[args.index("--pkg-types") + 1] == "os,library" and args[args.index("--library-patch-level") + 1] == "minor"
    calls.clear()
    copa.patch("ghcr.io/x/app:1.0", "1.0-copa", tmp_path / "b", platforms=["linux/amd64"], severities=["HIGH"])
    assert calls[0] == ("scan", "os") and "--pkg-types" not in calls[1][1] and calls[1][2] == {}


def test_component_changes_route_to_parents(tmp_path):
    from patcher.config import Repo
    from patcher.pipeline import plan_matrix

    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text("registry: ghcr.io/me\n")
    src = lambda repo: {"repo": repo, "lines": [{"tagPattern": r"^v1\.2\.\d+$"}]}
    docs = {
        "parent": {"source": src("o/parent"), "build": {"images": [{"name": "parent"}]},
                   "components": [{"recipe": "helm", "path": "/usr/local/bin/helm"}]},
        "other": {"source": src("o/other"), "build": {"images": [{"name": "other"}]}},
        "helm": {"mode": "component", "source": src("helm/helm"), "artifact": {"build": "go build -o /out/helm ./cmd/helm",
                                                                              "output": "/out/helm"}},
    }
    for name, doc in docs.items():
        (tmp_path / "recipes" / f"{name}.yaml").write_text(yaml.safe_dump({"name": name, **doc}))
    repo = Repo(tmp_path)
    parent = [{"recipe": "parent", "line": "v1.2", "platform": "linux/amd64", "arch": "amd64"}]
    assert plan_matrix(repo, changed_files=["recipes/helm.yaml"]) == parent
    assert plan_matrix(repo, changed_files=["skips/helm.yaml", "patches/helm/files/x.go"]) == parent
    assert plan_matrix(repo, recipes=["helm"]) == []  # never on its own


def test_copa_note_uses_copas_own_summary(monkeypatch, tmp_path):
    from patcher import copa

    class Rep:
        def fixable(self):
            return ["one"]

    def fake_scan(image, path, **k):
        path.write_text("{}")
        return Rep()

    def fake_run(args, env=None, log_file=None, **k):
        log_file.write_text('time="t" level=info msg="Patch Summary: 65 total, 59 patched, 6 skipped"\n')

    monkeypatch.setattr(copa, "scan_image", fake_scan)
    monkeypatch.setattr(copa, "which", lambda n: "/usr/local/bin/copa")
    monkeypatch.setattr(copa, "run", fake_run)
    res = copa.patch("quay.io/x/app:1.0", "1.0-copa", tmp_path, platforms=["linux/arm64"], severities=["HIGH"], libraries=True)
    assert res.note() == "patched (OS + library): 65 total, 59 patched, 6 skipped"
    assert copa.CopaResult(None, 0, skipped="no fixable OS packages").note() == "no fixable OS packages"
    assert copa.CopaResult(None, 3, error="#5 ERROR: dpkg: error processing package ca-certificates").note().startswith("failed: #5 ERROR")
    from patcher.models import ImageSpec

    assert copa.for_image(ImageSpec(name="a", copa=False), "img", "t", tmp_path, platforms=["linux/amd64"], severities=[]) is None


def test_report_explains_findings_left_in_components(tmp_path):
    import json

    from patcher.report import Summary, reason_for
    from patcher.scan import Finding

    out = tmp_path / "gomplate"
    (out / "generated").mkdir(parents=True)
    (out / "generated" / "bump-plan.json").write_text(json.dumps({"unresolved": [
        {"vuln_id": "CVE-1", "name": "golang.org/x/net", "why": "cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03)"}]}))
    ref = ComponentRef(recipe="gomplate", path="/usr/local/bin/gomplate")
    s = Summary(recipe=comp_recipe(), line="v2", tag="v2.46.1", commit="c", status="success")
    s.components = [{"image": "dex", **components.Component(ref, None, "5.2.0", "v5.2.0", "success").row()}]
    s.component_runs = [components.Component(ref, None, "5.2.0", "v5.2.0", "success", src=tmp_path, out=out)]
    f = lambda vid: Finding("usr/local/bin/gomplate", "gobinary", "gobinary", "golang.org/x/net", "v0.60.0", "0.62.0", vid, "HIGH",
                            "fixed")
    assert reason_for(f("CVE-1"), s) == "component `gomplate` (rebuilt from source): cooldown: v0.62.0 released 1 day(s) ago (eligible 2026-11-03)"
    assert "see `components/gomplate/report.md`" in reason_for(f("CVE-2"), s)
    s.components[0]["status"] = "tests-failed"
    assert reason_for(f("CVE-1"), s).startswith("component `gomplate` not swapped in (tests-failed)")


def test_release_skips_components_the_pr_kept_original(tmp_path):
    import json

    from patcher.config import Repo

    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text("registry: ghcr.io/me\n")
    (tmp_path / "recipes" / "helm.yaml").write_text(yaml.safe_dump({
        "name": "helm", "mode": "component", "source": {"repo": "helm/helm", "lines": [{"tagPattern": "x"}]},
        "artifact": {"build": "go build -o /out/helm ./cmd/helm", "output": "/out/helm"}}))
    parent = Recipe.model_validate({"name": "app", "source": {"repo": "o/app", "lines": [{"tagPattern": "x"}]},
                                    "build": {"images": [{"name": "app"}]},
                                    "components": [{"recipe": "helm", "path": "/usr/local/bin/helm"}]})
    gen = tmp_path / "gen"
    (gen / "components" / "helm").mkdir(parents=True)
    (gen / "components" / "helm" / "bump-plan.json").write_text(json.dumps(
        {"recipe": "helm", "tag": "v4.2.1", "commit": "abc", "status": "tests-failed"}))
    # not usable in the PR run, so the release must not check it out or overlay it
    assert components.from_generated(Repo(tmp_path), parent, gen, tmp_path / "work") == {}


def test_one_component_version_per_line(tmp_path):
    ref = ComponentRef(recipe="helm", path="/usr/local/bin/helm")
    a = components.Component(ref, comp_recipe(), "4.2.1", "v4.2.1", "success", src=tmp_path)
    b = components.Component(ref, comp_recipe(), "4.1.0", "v4.1.0", "success", src=tmp_path)
    chosen, notes = {}, []
    assert components.swappable([a], chosen, "argocd", notes) == [a]
    assert components.swappable([b], chosen, "argocd-alt", notes) == []  # keeps its own helm
    assert components.swappable([a], chosen, "argocd-ha", notes) == [a] and len(notes) == 1 and "4.1.0" in notes[0]
    assert components.image_row(b, "argocd-alt", [])["status"] == "kept-original"
    assert components.image_row(a, "argocd", [a])["status"] == "success"


def test_report_flags_bumps_the_image_did_not_pick_up():
    from patcher.adapters.base import Change
    from patcher.report import Summary, reason_for
    from patcher.scan import Finding

    s = Summary(recipe=comp_recipe(), line="main", tag="1.0", commit="c", status="success")
    s.changes = [Change("gradle", "gradle/patcher-constraints.gradle", "org.apache.tomcat.embed:tomcat-embed-core", "11.0.22",
                        "11.0.25", "CVE-1")]
    f = Finding("app/app.jar", "jar", "jar", "org.apache.tomcat.embed:tomcat-embed-core", "11.0.22", "11.0.25", "CVE-1", "CRITICAL",
                "fixed")
    assert reason_for(f, s).startswith("bumped to 11.0.25 in `gradle/patcher-constraints.gradle`, but the image still has 11.0.22")


def test_report_matches_failures_by_file():
    from patcher.adapters.base import Failure
    from patcher.report import Summary, reason_for
    from patcher.scan import Finding

    s = Summary(recipe=comp_recipe(), line="v5", tag="v5.8.3", commit="c", status="no-changes")
    s.failures = [Failure("gomod", "cmd/a/go.mod", "golang.org/x/net", "v0.60.0", "module dir 'cmd/a' is not listed"),
                  Failure("gomod", "fn/b/go.mod", "golang.org/x/net", "v0.60.0", "module dir 'fn/b' is not listed")]
    f = Finding("fn/b/go.mod", "gomod", "gomod", "golang.org/x/net", "v0.58.0", "0.60.0", "CVE-1", "HIGH", "fixed")
    assert reason_for(f, s) == "bump failed: module dir 'fn/b' is not listed"


def test_image_build_retries_once_on_network_errors(monkeypatch, tmp_path):
    from patcher import build
    from patcher.models import Build
    from patcher.proc import CommandError

    calls = []

    def fake_run(cmd, **k):
        calls.append(cmd)
        if len(calls) == 1:
            raise CommandError("docker buildx build", 1, 'go: read "https://proxy.golang.org/x/@v/v1.zip": unexpected EOF')

    monkeypatch.setattr(build, "run", fake_run)
    monkeypatch.setattr("patcher.proc.time.sleep", lambda s: None)
    spec = Build.model_validate({"images": [{"name": "app"}]})
    build.build_image(tmp_path, spec, spec.images[0], "local/app:1", "linux/arm64", {"commit": "c", "tag": "v1"}, {},
                      tmp_path / "build.log", push=False)
    assert len(calls) == 2
    calls.clear()

    def compile_error(cmd, **k):
        calls.append(cmd)
        raise CommandError("docker buildx build", 1, "main.go:3: undefined: foo")

    monkeypatch.setattr(build, "run", compile_error)
    with pytest.raises(CommandError):
        build.build_image(tmp_path, spec, spec.images[0], "local/app:1", "linux/arm64", {"commit": "c", "tag": "v1"}, {},
                          tmp_path / "build.log", push=False)
    assert len(calls) == 1  # real failures aren't retried


def test_hung_build_is_killed_and_retried_once(monkeypatch, tmp_path):
    from patcher import build
    from patcher.models import Build
    from patcher.proc import CommandError

    calls = []

    def fake_run(cmd, **k):
        calls.append(k.get("timeout"))
        if len(calls) == 1:
            raise CommandError("docker buildx build", -9, "timed out after 3600s (killed with its child processes)")

    monkeypatch.setattr(build, "run", fake_run)
    monkeypatch.setattr("patcher.proc.time.sleep", lambda s: None)
    spec = Build.model_validate({"images": [{"name": "app"}]})
    build.build_image(tmp_path, spec, spec.images[0], "local/app:1", "linux/arm64", {"commit": "c", "tag": "v1"}, {},
                      tmp_path / "build.log", push=False)
    assert calls == [3600, 3600]  # default build.timeoutMinutes, then one retry


def test_collect_keeps_one_patch_set_per_line(tmp_path):
    import json

    from patcher.config import Repo
    from patcher.pipeline import collect

    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text("registry: ghcr.io/me\n")
    gen = tmp_path / "generated" / "argo-cd"
    for tag, line in (("v3.5.5", "v3.5"), ("v3.4.12", "v3.4")):  # an older patch set of v3.5, and another line
        (gen / tag).mkdir(parents=True)
        (gen / tag / "bump-plan.json").write_text(json.dumps({"line": line, "tag": tag}))
    out = tmp_path / "out" / "argo-cd" / "v3.5"
    (out / "generated").mkdir(parents=True)
    (out / "generated" / "bump-plan.json").write_text(json.dumps({"line": "v3.5", "tag": "v3.5.6"}))
    (out / "summary.json").write_text(json.dumps({"recipe": "argo-cd", "line": "v3.5", "tag": "v3.5.6", "status": "success",
                                                  "draft": False}))
    (out / "pr-body.md").write_text("report")
    items = collect(Repo(tmp_path), tmp_path / "out")
    assert [i["tag"] for i in items] == ["v3.5.6"]
    assert sorted(p.name for p in gen.iterdir()) == ["v3.4.12", "v3.5.6"]  # v3.5.5 replaced; the v3.4 line untouched


def test_publish_false_never_pushes(tmp_path):
    from patcher.config import Repo
    from patcher.models import Recipe
    from patcher.pipeline import publish, refresh, release_build
    from patcher.report import Summary, render_markdown

    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text("registry: ghcr.io/me\n")
    r = Recipe.model_validate({"name": "vendor", "mode": "image-only", "publish": False,
                               "source": {"repo": "https://hub.docker.com/r/x/y", "lines": [{"name": "v1", "tagPattern": "x"}]},
                               "build": {"images": [{"name": "vendor", "upstream": "docker.io/x/y"}]}})
    repo = Repo(tmp_path)
    # no registry, git or docker access happens: the functions return before any of it
    assert release_build(repo, r, "v1", "linux/amd64", tmp_path / "w", tmp_path / "out") == []
    assert publish(repo, r, "v1", ["linux/amd64"], tmp_path / "out") == []
    assert (tmp_path / "out" / "vendor" / "v1" / "release.json").read_text() == "[]\n"
    assert refresh(repo, r, "v1", ["linux/amd64"], tmp_path / "out") == []
    md = render_markdown(Summary(recipe=r, line="v1", tag="1.6.0", commit="n/a", status="success"))
    assert "**Not published** (`publish: false`" in md


def test_smoke_commands_get_the_images_smoke_env(monkeypatch, tmp_path):
    from patcher import build
    from patcher.build import BuiltImage
    from patcher.models import ImageSpec

    seen = []
    monkeypatch.setattr(build, "run", lambda cmd, **k: seen.append(cmd) or Result(0, "otelcol version v0.163.1", 0.1))
    spec = ImageSpec(name="splunk-otel-collector", smoke=["components"], smokeEnv={"SPLUNK_REALM": "us0"})
    img = BuiltImage(spec=spec, ref="img:dev", platform="linux/amd64")
    assert build.smoke_test(img, tmp_path / "log")
    cmd = seen[0]
    assert cmd[cmd.index("-e") + 1] == "SPLUNK_REALM=us0" and cmd.index("-e") < cmd.index("img:dev") < cmd.index("components")
