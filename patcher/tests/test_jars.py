"""Bundled jars: planning with the release-age rule and policy cap, Central downloads pinned by sha256, the overlay,
the report, and the release flow re-applying exactly the recorded swaps. No network: Maven Central is a fake fetch."""

import datetime as dt
import hashlib
import io
import json
import urllib.error

import pytest
from pydantic import ValidationError

from patcher import components, jars, releases
from patcher.models import ImageSpec, Recipe
from patcher.planner import Unresolved
from patcher.report import ImageOutcome, Summary, reason_for, render_markdown
from patcher.scan import Finding, ScanReport

NOW = dt.datetime(2026, 10, 28, tzinfo=dt.timezone.utc)
GUAVA = "https://repo1.maven.org/maven2/com/google/guava/guava"
JAR = b"PK guava 33.7.2-jre"
LIB = "usr/share/maven/lib/guava-33.7.1-jre.jar"
OLD = {"33.7.2-jre": "Tue, 29 Sep 2026 14:47:28 GMT", "34.0.0-jre": "Mon, 05 Oct 2026 10:00:00 GMT"}


def central(published=OLD, jar=JAR, sha256="ok", sha1="ok"):
    """A fake Maven Central for Guava: its version list, publish times (the POM's Last-Modified), the jar, and the
    checksums published next to it ("ok", a wrong value, or None for not published)."""
    calls = []
    sums = {"sha256": sha256, "sha1": sha1}

    def fetch(url, method="GET"):
        calls.append((method, url))
        if url == f"{GUAVA}/maven-metadata.xml":
            versions = "".join(f"<version>{v}</version>" for v in ("33.7.1-jre", "33.7.2-android", "33.7.2-jre", "34.0.0-jre"))
            return {}, f"<metadata><versioning><latest>34.0.0-jre</latest><versions>{versions}</versions></versioning></metadata>".encode()
        for v, when in published.items():
            if url == f"{GUAVA}/{v}/guava-{v}.pom":
                return {"last-modified": when}, b""
            if url == f"{GUAVA}/{v}/guava-{v}.jar":
                return {}, jar
            algo = url.rsplit(".", 1)[-1]
            if url.startswith(f"{GUAVA}/{v}/guava-{v}.jar.") and sums.get(algo):
                return {}, f"{hashlib.new(algo, jar).hexdigest() if sums[algo] == 'ok' else sums[algo]}  guava-{v}.jar\n".encode()
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO())

    return jars.Central(fetch=fetch), calls


def gate(c: jars.Central, kev=()):
    return releases.AgeGate(7, {"CRITICAL"}, set(kev), releases.ReleaseAges(fetch=c.fetch), now=NOW)


def recipe(**kw) -> Recipe:
    return Recipe.model_validate({"name": "maven", "source": {"repo": "o/r", "lines": [{"name": "m", "branch": "main",
                                  "versionFrom": {"file": "x", "var": "V"}}]}, **kw})


def spec(level="patch", jdk="21") -> dict:
    return {"name": "maven", "id": f"maven-{jdk}", "upstreamTag": f"{{{{version}}}}-temurin-{jdk}",
            "bundledJars": {"paths": ["usr/share/maven/"], "level": level}}


def image(**kw) -> ImageSpec:
    return ImageSpec.model_validate(spec(**kw))


def finding(fixed="33.7.2", vuln="CVE-2026-102554", severity="HIGH", path=LIB, name="com.google.guava:guava", installed="33.7.1-jre"):
    return Finding("Java", "jar", "jar", name, installed, fixed, vuln, severity, "fixed", pkg_path=path)


def scan(*findings) -> ScanReport:
    return ScanReport("img", findings=list(findings))


def swap(image_key="maven-21", **kw) -> jars.Swap:
    return jars.Swap(image_key, LIB, "com.google.guava:guava", "33.7.1-jre", "33.7.2-jre", ["CVE-2026-102554"],
                     url=f"{GUAVA}/33.7.2-jre/guava-33.7.2-jre.jar", sha256=hashlib.sha256(JAR).hexdigest(), old_sha256="0ld", **kw)


@pytest.fixture
def old_jars(monkeypatch):
    """The built image has the jars to replace (their sha256 is "0ld")."""
    monkeypatch.setattr(jars, "image_sha256", lambda image, platform, paths, work: {p: "0ld" for p in paths})


def test_model_needs_paths():
    with pytest.raises(ValidationError):
        ImageSpec.model_validate({"name": "maven", "bundledJars": {"paths": []}})
    assert ImageSpec(name="maven").bundledJars is None and image().bundledJars.level.value == "patch"


def test_fix_versions_are_central_releases_in_the_installed_flavor():
    guava = {"33.7.2-android", "33.7.2-jre", "32.0.0-jre", "32.0.0-android"}
    # Trivy says 33.7.2 (or another flavor); a -jre jar takes Central's -jre release
    assert jars.central_fixes("33.7.2", "33.7.1-jre", guava) == "33.7.2-jre"
    assert jars.central_fixes("32.0.0-android", "31.1-jre", guava) == "32.0.0-jre"
    assert jars.central_fixes("4.1.108", "4.1.100.Final", {"4.1.108.Final"}) == "4.1.108.Final"
    assert jars.central_fixes("9.4.54", "9.4.53.v20231009", {"9.4.54.v20240208", "9.4.55.v20240627"}) == "9.4.54.v20240208"
    assert jars.central_fixes("2.18.2, 2.19.0", "2.18.0", {"2.18.2", "2.19.0"}) == "2.18.2, 2.19.0"
    assert jars.central_fixes("33.8.0", "33.7.1-jre", guava) == ""  # not on Central: dropped
    assert jars.central_fixes("33.7.2", "33.7.1-jre", None) == "33.7.2-jre"  # no version list: the flavored guess
    assert jars._flavor("2.0.0-M1") == jars._flavor("1.0-rc") == "" and jars._flavor("5.3.9.RELEASE") == ".RELEASE"


def test_plan_swaps_the_jar_for_centrals_fixed_release():
    c, _ = central()
    swaps, unresolved = jars.plan(scan(finding(), finding(path="opt/app/guava-33.7.1-jre.jar")), image(), recipe(), gate(c), c)
    assert [(s.image, s.path, s.name, s.old, s.new, s.vuln_ids) for s in swaps] == [
        ("maven-21", LIB, "com.google.guava:guava", "33.7.1-jre", "33.7.2-jre", ["CVE-2026-102554"])]
    assert not unresolved  # the finding outside `paths` is not this feature's business


def test_release_age_rule_and_its_bypasses_apply():
    c, _ = central(published={"33.7.2-jre": "Mon, 26 Oct 2026 09:00:00 GMT"})
    swaps, unresolved = jars.plan(scan(finding()), image(), recipe(), gate(c), c)
    assert not swaps and unresolved[0].why == "cooldown: 33.7.2-jre released 1 day(s) ago (eligible 2026-11-02)"
    assert (unresolved[0].ecosystem, unresolved[0].target) == ("jar", LIB)
    assert [s.new for s in jars.plan(scan(finding(severity="CRITICAL")), image(), recipe(), gate(c), c)[0]] == ["33.7.2-jre"]
    assert [s.new for s in jars.plan(scan(finding()), image(), recipe(), gate(c, kev={"CVE-2026-102554"}), c)[0]] == ["33.7.2-jre"]
    assert [s.new for s in jars.plan(scan(finding()), image(), recipe(), None, c)[0]] == ["33.7.2-jre"]  # --no-cooldown


def test_withdrawn_releases_are_never_swapped_in(monkeypatch):
    c, _ = central()
    g = gate(c)
    # Central never withdraws a release, but the jar plan goes through the same check as npm, PyPI and crates.io bumps
    monkeypatch.setattr(g.ages, "releases", lambda eco, name: {"33.7.2-jre": "broke Maven"} if eco == "maven" else None)
    swaps, unresolved = jars.plan(scan(finding(severity="CRITICAL")), image(), recipe(), g, c)
    assert not swaps and unresolved[0].why == "33.7.2-jre was withdrawn by its registry: broke Maven"


def test_level_caps_the_swap_and_holds_apply():
    c, _ = central()
    major = finding(fixed="34.0.0", vuln="CVE-2026-2")
    swaps, unresolved = jars.plan(scan(finding(), major), image(), recipe(), gate(c), c)
    assert [s.new for s in swaps] == ["33.7.2-jre"]  # the patch-level fix still goes in
    assert [(u.vuln_id, u.why) for u in unresolved] == [("CVE-2026-2", "needs-human: fix requires a bump beyond `bundledJars.level: patch`")]
    assert [s.new for s in jars.plan(scan(major), image(level="major"), recipe(), gate(c), c)[0]] == ["34.0.0-jre"]
    held = recipe(holds={"maven": [{"name": "com.google.guava:*", "reason": "Maven 3.10 is tested with 33.7.1"}]})
    swaps, unresolved = jars.plan(scan(finding()), image(), held, gate(c), c)
    assert not swaps and unresolved[0].why == "held: Maven 3.10 is tested with 33.7.1"


def test_only_a_jar_that_is_the_artifact_itself_is_swapped():
    c, _ = central()
    shaded = finding(path="usr/share/maven/lib/maven-core-3.10.0.jar")
    swaps, unresolved = jars.plan(scan(shaded, finding(fixed="33.8.0")), image(), recipe(), gate(c), c)
    assert not swaps
    assert [u.why for u in unresolved] == [
        "`com.google.guava:guava` is packaged inside `maven-core-3.10.0.jar` (shaded or renamed), so it can't be swapped on its own",
        "the advisory's fix (33.8.0) is not a release of `com.google.guava:guava` on Maven Central"]
    assert jars._classifier("usr/share/maven/lib/guice-5.1.0-classes.jar", "com.google.inject:guice", "5.1.0") == "classes"


def test_prepare_pins_the_download_and_the_replaced_jar(old_jars, tmp_path):
    c, calls = central()
    (s,), unresolved = jars.prepare("img", "linux/arm64", image(), scan(finding()), recipe(), gate(c), tmp_path, c)
    assert not unresolved and s == swap(checksum="sha256")
    assert (tmp_path / s.context_file).read_bytes() == JAR
    assert ("GET", f"{GUAVA}/33.7.2-jre/guava-33.7.2-jre.jar.sha256") in calls


def test_downloads_are_checked_against_centrals_checksums(old_jars, tmp_path):
    c, _ = central(sha256="f" * 64)
    swaps, unresolved = jars.prepare("img", "linux/arm64", image(), scan(finding()), recipe(), gate(c), tmp_path, c)
    assert not swaps and unresolved[0].why.startswith("download of 33.7.2-jre from Maven Central failed: sha256 ")
    assert not (tmp_path / "jars").exists()
    c, _ = central(sha256=None)  # no published sha256: Central's sha1 is checked instead
    assert jars.prepare("img", "linux/arm64", image(), scan(finding()), recipe(), gate(c), tmp_path, c)[0][0].checksum == "sha1"


def test_overlay_copies_each_jar_over_the_old_path_and_labels_it():
    s = swap()
    df = components.overlay_dockerfile("patcher.local/maven:3.10.0-patched.dev", [], jars.copies([s]), jars.labels([s])).splitlines()
    assert df[:2] == ["FROM patcher.local/maven:3.10.0-patched.dev", f"COPY --chmod=0644 {s.context_file} /{LIB}"]
    key, value = df[2].removeprefix("LABEL ").split("=", 1)
    assert key == jars.LABEL and json.loads(json.loads(value)) == [
        {"path": f"/{LIB}", "name": "com.google.guava:guava", "from": "33.7.1-jre", "to": "33.7.2-jre", "sha256": s.sha256}]
    assert components.overlay_dockerfile("base", []) == "FROM base\n"


def test_report_lists_swaps_and_explains_what_is_left():
    s = Summary(recipe=recipe(), line="m", tag="3.10.0", commit="c", status="success")
    s.jars = [swap("maven-21"), swap("maven-17")]
    left = finding(fixed="34.0.0", vuln="CVE-2026-2", installed="33.7.2-jre")
    s.jar_unresolved = [Unresolved("jar", LIB, "com.google.guava:guava", "33.7.1-jre", "CVE-2026-2", "HIGH", "34.0.0-jre",
                                   "needs-human: fix requires a bump beyond `bundledJars.level: patch`")]
    s.images = [ImageOutcome("maven-21", "ref", None, None, scan(left))]
    md = render_markdown(s)
    assert "### Bundled jars swapped" in md
    assert (f"| maven-21, maven-17 | `{LIB}` | `com.google.guava:guava` | `33.7.1-jre` → `33.7.2-jre` | CVE-2026-102554 | "
            f"`{swap().sha256}` |") in md
    assert reason_for(left, s, {LIB}) == "bundled jar: needs-human: fix requires a bump beyond `bundledJars.level: patch`"
    assert reason_for(finding(vuln="CVE-2026-3"), s, {LIB}).startswith("bundled jar swapped for 33.7.2-jre, but the scan still reports")
    other = finding(path="usr/share/maven/lib/other-1.0.jar", name="o:other", installed="1.0")
    assert reason_for(other, s, {"usr/share/maven/lib/other-1.0.jar"}).startswith("in bundled artifact")


def test_image_planning_leaves_bundled_jars_to_the_swap():
    from patcher.pipeline import image_derived

    r = recipe(ecosystems=[{"type": "maven"}], build={"images": [spec()]})
    img = ImageOutcome("maven-21", "ref", None, None, scan(finding(), finding(path="app/lib/guava-33.7.1-jre.jar")))
    assert [f.location for f in image_derived(r, [img], None).findings] == ["app/lib/guava-33.7.1-jre.jar"]


def test_pr_flow_swaps_before_smoke_tests_and_copa(monkeypatch, tmp_path):
    from patcher import pipeline
    from patcher.adapters.base import Result
    from patcher.build import BuiltImage, template_ctx
    from patcher.config import Repo
    from patcher.planner import Plan

    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text("registry: ghcr.io/me\n")
    r = recipe(build={"images": [spec()]})
    att = pipeline.Attempt("full plan", tmp_path / "src", {}, Plan(), Result(), [], {}, None, "", None)
    summary = Summary(recipe=r, line="m", tag="3.10.0", commit="c", status="no-changes")  # only Maven's own jar is vulnerable
    calls = []
    monkeypatch.setattr(pipeline, "build_image", lambda src, b, spec, ref, platform, *a, push: calls.append("build")
                        or BuiltImage(spec, ref, platform))
    monkeypatch.setattr(pipeline, "scan_image", lambda ref, path, **k: calls.append(path.name) or scan(finding()))
    monkeypatch.setattr(jars, "prepare", lambda img, platform, spec, built, recipe, gate, ctx: calls.append(f"jars {built.artifact}")
                        or ([swap()], []))
    monkeypatch.setattr(components, "overlay", lambda base, comps, out, **k: calls.append(("overlay", base, k["files"])))
    monkeypatch.setattr(pipeline, "smoke_test", lambda img, log: calls.append("smoke") or True)
    monkeypatch.setattr(pipeline.copa, "for_image", lambda *a, **k: calls.append("copa"))
    opts = pipeline.RunOptions(workdir=tmp_path, out=tmp_path, platform="linux/arm64", cooldown=False)
    pipeline._build_and_scan(Repo(tmp_path), r, att, summary, tmp_path / "out", opts, template_ctx("3.10.0", "c"), {})
    built = "patcher.local/maven:3.10.0-temurin-21-patched.dev"
    assert calls == ["build", "scan-image-built-maven-21.json", "jars img", ("overlay", built, [(swap().context_file, f"/{LIB}")]),
                     "smoke", "copa", "scan-image-after-maven-21.json"]
    assert summary.jars == [swap()] and summary.status == "success"  # a swap is a change to release


def test_release_reapplies_exactly_the_recorded_swaps(old_jars, monkeypatch, tmp_path):
    c, _ = central()
    monkeypatch.setattr(jars, "_central", c)
    swaps, unresolved = jars.prepare("img", "linux/arm64", image(), scan(finding()), recipe(), gate(c), tmp_path / "pr")
    (tmp_path / "gen").mkdir()
    (tmp_path / "gen" / "jars.json").write_text(json.dumps(jars.to_json(swaps, unresolved)))
    recorded = jars.from_generated(tmp_path / "gen")
    assert recorded == {"maven-21": swaps} and jars.from_generated(tmp_path) == {}

    jars.restage("base", ["linux/amd64", "linux/arm64"], recorded["maven-21"], tmp_path / "release")
    assert (tmp_path / "release" / swaps[0].context_file).read_bytes() == JAR
    # Central now serves other bytes for that release (with matching checksums): the pin refuses them
    monkeypatch.setattr(jars, "_central", central(jar=b"republished")[0])
    with pytest.raises(RuntimeError, match="does not match the pin in jars.json"):
        jars.restage("base", ["linux/amd64"], recorded["maven-21"], tmp_path / "release")
    # the base no longer has the reviewed jar (a newer vendor tag, a changed build): refuse rather than add a second jar
    monkeypatch.setattr(jars, "image_sha256", lambda image, platform, paths, work: {p: None for p in paths})
    with pytest.raises(RuntimeError, match="is not the jar the reviewed patch set replaced"):
        jars.restage("base", ["linux/amd64"], recorded["maven-21"], tmp_path / "release")


def test_release_build_overlays_the_recorded_jars(monkeypatch, tmp_path):
    from patcher import pipeline
    from patcher.build import BuiltImage
    from patcher.config import Repo

    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text("registry: ghcr.io/me\n")
    r = recipe(build={"images": [spec(jdk="21"), {**spec(jdk="17"), "bundledJars": None}]})
    gen = tmp_path / "generated" / "maven" / "3.10.0"
    gen.mkdir(parents=True)
    (gen / "bump-plan.json").write_text(json.dumps({"line": "m", "tag": "3.10.0", "commit": "c", "status": "success"}))
    (gen / "jars.json").write_text(json.dumps(jars.to_json([swap()], [])))
    calls = []
    monkeypatch.setattr(pipeline, "prepare_release_source", lambda *a, **k: (tmp_path, {"tag": "3.10.0", "commit": "c"}, {}))
    monkeypatch.setattr(pipeline, "next_revision", lambda *a: 1)
    monkeypatch.setattr(pipeline, "build_image", lambda src, b, spec, ref, platform, *a, push: calls.append(("build", ref, push))
                        or BuiltImage(spec, ref, platform))
    monkeypatch.setattr(jars, "restage", lambda image, platforms, swaps, ctx: calls.append(("restage", image, platforms, swaps)))
    monkeypatch.setattr(components, "overlay", lambda base, comps, out, **k: calls.append(("overlay", base, k["tag_ref"], k["files"])))
    pushed = pipeline.release_build(Repo(tmp_path), r, "m", "linux/amd64", tmp_path / "w", tmp_path / "out")
    base = "patcher.local/maven:3.10.0-temurin-21-patched.1-base"
    assert calls == [
        ("build", base, False),
        ("restage", base, ["linux/amd64"], [swap()]),
        ("overlay", base, "ghcr.io/me/maven:3.10.0-temurin-21-patched.1-amd64", [(swap().context_file, f"/{LIB}")]),
        ("build", "ghcr.io/me/maven:3.10.0-temurin-17-patched.1-amd64", True)]  # nothing recorded for it: a plain build
    assert pushed[0]["jars"] == [f"/{LIB}: com.google.guava:guava 33.7.2-jre"] and pushed[1]["jars"] == []
