"""Release flow: the plan's platform matrix, the archives the credential-less build hands over, the push job that
pushes only the expected tags, revision selection (also with `rebuild: false`), and publish finishing a revision.
No registry or Docker: tags are a set, archives are tar files written here."""

import datetime as dt
import gzip
import io
import json
import tarfile
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from patcher import archive, pipeline
from patcher.build import BuiltImage
from patcher.config import Repo
from patcher.models import Build, LineState, State
from patcher.proc import CommandError, Result
from patcher.scan import ScanReport

REG = "ghcr.io/me/app"
DIGEST = "sha256:" + "d" * 64


def app_recipe(**build) -> dict:
    """Two images in one repository: `app` for every platform, `app-debug` for amd64 only."""
    return {"name": "app", "source": {"repo": "o/app", "lines": [{"name": "v1", "tagPattern": r"^v1\.\d+\.\d+$"}]},
            "build": {"images": [{"name": "app"},
                                 {"name": "app", "id": "app-debug", "upstreamTag": "{{tag}}-debug", "platforms": ["linux/amd64"]}],
                      **build}}


def make_repo(tmp_path: Path, *recipes: dict, released: int | None = 2, status: str = "success") -> Repo:
    """Recipes, the reviewed patch set of app v1.2.3, and state/ recording revision `released` of it."""
    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text("registry: ghcr.io/me\n")
    for r in recipes or (app_recipe(),):
        (tmp_path / "recipes" / f"{r['name']}.yaml").write_text(yaml.safe_dump(r))
    gen = tmp_path / "generated" / "app" / "v1.2.3"
    gen.mkdir(parents=True)
    (gen / "bump-plan.json").write_text(json.dumps({"recipe": "app", "line": "v1", "tag": "v1.2.3", "commit": "c0ffee",
                                                    "status": status}))
    repo = Repo(tmp_path)
    if released:
        repo.save_state("app", State(lines={"v1": LineState(upstreamTag="v1.2.3", commit="c0ffee", revision=released,
                                                             releasedAt=dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc))}))
    return repo


def registry(monkeypatch, *tags: str) -> set[str]:
    existing = set(tags)
    monkeypatch.setattr(pipeline, "_tag_exists", lambda ref: ref in existing)
    return existing


def staging(rev: int, arch: str, debug: bool = False) -> str:
    return f"{REG}:v1.2.3{'-debug' if debug else ''}-patched.{rev}-{arch}"


def save_archive(path: Path, arch: str = "amd64", *, images: int = 1, variant: str = "", drop_layer: bool = False,
                 compress: bool = False) -> Path:
    """A `docker save` archive (manifest.json, config and layer blobs) whose images claim `arch`."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        def add(name: str, data: bytes) -> None:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))

        manifest = []
        for i in range(images):
            add(f"blobs/sha256/config{i}", json.dumps({"os": "linux", "architecture": arch, **({"variant": variant} if variant else {})}).encode())
            if not drop_layer:
                add(f"blobs/sha256/layer{i}", b"layer")
            # names in the archive are never used: these would point anywhere
            manifest.append({"Config": f"blobs/sha256/config{i}", "RepoTags": [f"ghcr.io/me/other:{i}"], "Layers": [f"blobs/sha256/layer{i}"]})
        add("manifest.json", json.dumps(manifest).encode())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(buf.getvalue()) if compress else buf.getvalue())
    return path


# --- archives -----------------------------------------------------------------------------------


def test_an_archive_must_hold_one_image_of_the_expected_platform(tmp_path):
    assert archive.check(save_archive(tmp_path / "a.tar", "amd64"), "linux/amd64").layers == 1
    assert archive.check(save_archive(tmp_path / "v8.tar", "arm64", variant="v8"), "linux/arm64").platform == "linux/arm64/v8"
    with pytest.raises(ValueError, match="holds a linux/arm64 image, expected linux/amd64"):
        archive.check(save_archive(tmp_path / "b.tar", "arm64"), "linux/amd64")
    with pytest.raises(ValueError, match="exactly one image, found 2"):
        archive.check(save_archive(tmp_path / "c.tar", images=2), "linux/amd64")
    with pytest.raises(ValueError, match="layers missing"):
        archive.check(save_archive(tmp_path / "d.tar", drop_layer=True), "linux/amd64")
    with pytest.raises(ValueError, match="not an image archive"):  # docker save never compresses
        archive.check(save_archive(tmp_path / "e.tar", compress=True), "linux/amd64")
    with pytest.raises(ValueError, match="not an image archive"):
        archive.check(tmp_path / "missing.tar", "linux/amd64")
    (tmp_path / "f.tar").write_text("not a tar")
    with pytest.raises(ValueError, match="not an image archive"):
        archive.check(tmp_path / "f.tar", "linux/amd64")


def test_archives_are_pushed_with_crane_to_the_given_reference_only(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, **k):
        calls.append(cmd)
        Path(cmd[3]).write_text(f"{REG}@{DIGEST}\n")  # what crane writes to --image-refs

    monkeypatch.setattr(archive, "run", fake_run)
    path = save_archive(tmp_path / "app.tar")
    assert archive.push(path, f"{REG}:v1.2.3-patched.3-amd64") == DIGEST
    assert calls[0][:3] == ["crane", "push", "--image-refs"] and calls[0][4:] == [str(path), f"{REG}:v1.2.3-patched.3-amd64"]


def test_export_saves_the_local_image(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(archive, "run", lambda cmd, **k: calls.append(cmd))
    dest = archive.path_for(tmp_path / "images", "linux/arm64", "app-debug")
    archive.export("patcher.local/app:v1.2.3-release-arm64", dest)
    assert dest == tmp_path / "images" / "arm64" / "app-debug.tar"
    assert calls == [["docker", "save", "--output", str(dest), "patcher.local/app:v1.2.3-release-arm64"]]


# --- build: no credentials, nothing pushed ---------------------------------------------------------


def test_release_build_saves_archives_and_pushes_nothing(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    calls = []
    monkeypatch.setattr(pipeline, "prepare_release_source", lambda *a, **k: (tmp_path, {"tag": "v1.2.3", "commit": "c0ffee"}, {}))
    monkeypatch.setattr(pipeline, "build_image", lambda src, b, spec, ref, platform, *a, push: calls.append(("build", ref, platform, push))
                        or BuiltImage(spec, ref, platform))
    monkeypatch.setattr(pipeline.archive, "export", lambda ref, dest, log=None: calls.append(("save", ref, dest)))
    monkeypatch.setattr(pipeline, "_tag_exists", lambda ref: pytest.fail("the build job doesn't ask the registry"))
    out = tmp_path / "out"
    stale = save_archive(out / "app" / "v1" / "images" / "arm64" / "old.tar", "arm64")  # an earlier build's: not uploaded again
    built = pipeline.release_build(repo, repo.load_recipe("app"), "v1", "linux/arm64", tmp_path / "w", out)
    images = out / "app" / "v1" / "images" / "arm64"
    # app-debug is amd64-only: not built for arm64
    assert calls == [("build", "patcher.local/app:v1.2.3-release-arm64", "linux/arm64", False),
                     ("save", "patcher.local/app:v1.2.3-release-arm64", images / "app.tar")]
    assert [b["archive"] for b in built] == ["images/arm64/app.tar"] and not stale.exists()


# --- push: the trusted job pushes only what it computes itself ----------------------------------------


def archives(tmp_path: Path) -> Path:
    images = tmp_path / "out" / "app" / "v1" / "images"
    save_archive(images / "amd64" / "app.tar", "amd64")
    save_archive(images / "arm64" / "app.tar", "arm64")
    save_archive(images / "amd64" / "app-debug.tar", "amd64")
    return images


def fake_push(monkeypatch, images: Path) -> list:
    pushes = []
    monkeypatch.setattr(pipeline.archive, "push", lambda path, ref, log=None: pushes.append((path.relative_to(images).as_posix(), ref))
                        or DIGEST)
    return pushes


def test_push_takes_a_fresh_revision_and_pushes_only_the_expected_tags(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)  # state/ records revision 2
    # 3 is published (its state/ PR not merged yet); 4 is a failed attempt's leftover: neither is touched
    registry(monkeypatch, f"{REG}:v1.2.3-patched.3", staging(3, "amd64"), staging(3, "arm64"), staging(4, "arm64"))
    images = archives(tmp_path)
    save_archive(images / "arm64" / "app-debug.tar", "arm64")  # app-debug isn't released for arm64
    save_archive(images / "amd64" / "other.tar", "amd64")  # not an image of this recipe
    save_archive(images / "amd64" / "app.tar.extra", "amd64")
    pushes = fake_push(monkeypatch, images)
    result = pipeline.release_push(repo, repo.load_recipe("app"), "v1", tmp_path / "out")
    assert result["revision"] == 5
    assert pushes == [("amd64/app.tar", staging(5, "amd64")), ("arm64/app.tar", staging(5, "arm64")),
                      ("amd64/app-debug.tar", staging(5, "amd64", debug=True))]
    assert json.loads((tmp_path / "out" / "app" / "v1" / "pushed.json").read_text()) == result
    assert [p["ref"] for p in result["pushed"]] == [ref for _, ref in pushes]


@pytest.mark.parametrize("damage, error", [
    (lambda images: save_archive(images / "arm64" / "app.tar", "amd64"), "holds a linux/amd64 image, expected linux/arm64"),
    (lambda images: (images / "amd64" / "app-debug.tar").unlink(), "not an image archive"),
    (lambda images: save_archive(images / "amd64" / "app.tar", images=2), "exactly one image"),
])
def test_push_checks_every_archive_before_pushing_anything(tmp_path, monkeypatch, damage, error):
    repo = make_repo(tmp_path)
    registry(monkeypatch)
    images = archives(tmp_path)
    damage(images)
    pushes = fake_push(monkeypatch, images)
    with pytest.raises(ValueError, match=error):
        pipeline.release_push(repo, repo.load_recipe("app"), "v1", tmp_path / "out")
    assert pushes == []


def test_push_never_overwrites_a_tag(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    existing = registry(monkeypatch)
    images = archives(tmp_path)
    pushes = fake_push(monkeypatch, images)
    # another run pushes revision 3 between the revision check and the push
    monkeypatch.setattr(pipeline, "next_revision", lambda *a: existing.add(staging(3, "amd64")) or 3)
    with pytest.raises(RuntimeError, match="never overwritten"):
        pipeline.release_push(repo, repo.load_recipe("app"), "v1", tmp_path / "out")
    assert pushes == []


def test_push_refuses_a_patch_set_that_may_not_be_released(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, status="tests-failed")
    registry(monkeypatch)
    pushes = fake_push(monkeypatch, archives(tmp_path))
    with pytest.raises(RuntimeError, match="only successful runs are released"):
        pipeline.release_push(repo, repo.load_recipe("app"), "v1", tmp_path / "out")
    assert pushes == []


# --- revisions ------------------------------------------------------------------------------------


def test_revision_selection(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)  # state/ records revision 2
    r = repo.load_recipe("app")
    existing = registry(monkeypatch,
                        # 2 is recorded: never a candidate, whatever is left of it
                        staging(2, "amd64"), staging(2, "arm64"), staging(2, "amd64", True),
                        # 3: published, its state/ PR not merged yet
                        f"{REG}:v1.2.3-patched.3", staging(3, "amd64"), staging(3, "arm64"), staging(3, "amd64", True),
                        # 4: a push that failed half-way
                        staging(4, "amd64"),
                        # 5: pushed; publish failed before the final tags
                        staging(5, "amd64"), staging(5, "arm64"), staging(5, "amd64", True))
    assert pipeline.next_revision(repo, r, "v1", "v1.2.3") == 6  # never reuses a tag of 3, 4 or 5
    assert pipeline.built_revision(repo, r, "v1", "v1.2.3") == 5  # what `rebuild: false` finishes
    existing.discard(staging(5, "amd64", True))  # 5 is missing an image now: 3 is the newest complete one
    assert pipeline.built_revision(repo, r, "v1", "v1.2.3") == 3
    # a new upstream tag starts at revision 1, and has nothing to finish yet
    assert pipeline.next_revision(repo, r, "v1", "v1.3.0") == 1
    with pytest.raises(LookupError, match="rebuild: true"):
        pipeline.built_revision(repo, r, "v1", "v1.3.0")


def test_registry_probe_takes_only_not_found_as_missing(monkeypatch):
    result = {}
    monkeypatch.setattr(pipeline, "run", lambda cmd, **k: result["r"])
    result["r"] = Result(0, f"Name: {REG}:x\n", 0.1)
    assert pipeline._tag_exists(f"{REG}:x")
    result["r"] = Result(1, f"ERROR: {REG}:x: not found\n", 0.1)
    assert not pipeline._tag_exists(f"{REG}:x")
    # a registry that can't be asked is not an empty one: no revision is taken as free on an error
    result["r"] = Result(1, "ERROR: failed to authorize: failed to fetch anonymous token: 403 Forbidden\n", 0.1)
    with pytest.raises(CommandError):
        pipeline._tag_exists(f"{REG}:x")


# --- publish ------------------------------------------------------------------------------------


def fake_publish_tools(monkeypatch) -> list:
    cmds = []
    monkeypatch.setattr(pipeline, "run", lambda cmd, **k: cmds.append(cmd[4:] if cmd[:4] == ["docker", "buildx", "imagetools", "create"]
                                                                       else cmd))
    monkeypatch.setattr(pipeline.copa, "for_image", lambda spec, image, out_tag, out, **k: cmds.append(["copa", image, out_tag, k["platforms"]]))
    monkeypatch.setattr(pipeline, "image_digest", lambda ref: DIGEST)
    monkeypatch.setattr(pipeline, "scan_image", lambda ref, path, **k: ScanReport(ref))
    return cmds


def test_publish_merges_the_revision_push_pushed(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    registry(monkeypatch, staging(5, "amd64"), staging(5, "arm64"), staging(5, "amd64", True))
    cmds = fake_publish_tools(monkeypatch)
    released = pipeline.publish(repo, repo.load_recipe("app"), "v1", None, tmp_path / "out", revision=5)
    final, debug = f"{REG}:v1.2.3-patched.5", f"{REG}:v1.2.3-debug-patched.5"
    assert cmds == [
        ["-t", f"{final}-build", staging(5, "amd64"), staging(5, "arm64")],
        ["copa", f"{final}-build", "v1.2.3-patched.5", ["linux/amd64", "linux/arm64"]],
        ["-t", final, f"{final}-build"],  # Copa had nothing to patch
        ["-t", f"{REG}:v1.2.3-patched", final],
        ["-t", f"{debug}-build", staging(5, "amd64", True)],  # amd64 only
        ["copa", f"{debug}-build", "v1.2.3-debug-patched.5", ["linux/amd64"]],
        ["-t", debug, f"{debug}-build"],
        ["-t", f"{REG}:v1.2.3-debug-patched", debug]]
    assert [(r["tag"], r["copa"]) for r in released] == [("v1.2.3-patched.5", "disabled"), ("v1.2.3-debug-patched.5", "disabled")]
    st = repo.state("app").lines["v1"]
    assert (st.revision, st.platforms, [i.ref for i in st.images]) == (5, ["linux/amd64", "linux/arm64"], [final, debug])


def test_publish_without_a_build_finishes_the_newest_built_revision_as_it_is(tmp_path, monkeypatch):
    """`rebuild: false` after a publish that pushed revision 5's final tag of `app`, then failed."""
    repo = make_repo(tmp_path)
    registry(monkeypatch, staging(3, "amd64"), staging(3, "arm64"), staging(3, "amd64", True),  # an older attempt
             staging(4, "amd64"),  # a push that failed half-way
             staging(5, "amd64"), staging(5, "arm64"), staging(5, "amd64", True), f"{REG}:v1.2.3-patched.5")
    cmds = fake_publish_tools(monkeypatch)
    released = pipeline.publish(repo, repo.load_recipe("app"), "v1", None, tmp_path / "out")
    final, debug = f"{REG}:v1.2.3-patched.5", f"{REG}:v1.2.3-debug-patched.5"
    assert cmds == [
        ["-t", f"{REG}:v1.2.3-patched", final],  # app: kept as it is, no second merge or Copa
        ["-t", f"{debug}-build", staging(5, "amd64", True)],  # app-debug never got that far
        ["copa", f"{debug}-build", "v1.2.3-debug-patched.5", ["linux/amd64"]],
        ["-t", debug, f"{debug}-build"],
        ["-t", f"{REG}:v1.2.3-debug-patched", debug]]
    assert released[0]["copa"].startswith("unchanged") and repo.state("app").lines["v1"].revision == 5


def test_copa_refresh_takes_a_free_revision_and_each_image_s_platforms(tmp_path, monkeypatch):
    from patcher.copa import CopaResult
    from patcher.models import ReleasedImage

    repo = make_repo(tmp_path)  # state/ records revision 2
    st = repo.state("app")
    st.lines["v1"] = st.lines["v1"].model_copy(update={"platforms": ["linux/amd64", "linux/arm64"], "images": [
        ReleasedImage(name="app", ref=f"{REG}:v1.2.3-patched.2", digest=DIGEST),
        ReleasedImage(name="app-debug", ref=f"{REG}:v1.2.3-debug-patched.2", digest=DIGEST)]})
    repo.save_state("app", st)
    # 3 holds a release attempt's per-arch images: a refresh there would be taken for that release by `rebuild: false`
    existing = registry(monkeypatch, staging(3, "arm64"))
    calls = []
    monkeypatch.setattr(pipeline.copa, "for_image", lambda spec, image, out_tag, out, **k: calls.append((out_tag, k["platforms"]))
                        or CopaResult(f"{REG}:{out_tag}", 1))
    monkeypatch.setattr(pipeline, "run", lambda cmd, **k: calls.append(cmd[4:]))  # imagetools create -t <to> <from>
    monkeypatch.setattr(pipeline, "image_digest", lambda ref: DIGEST)
    monkeypatch.setattr(pipeline, "scan_image", lambda ref, path, **k: ScanReport(ref))
    pipeline.refresh(repo, repo.load_recipe("app"), "v1", None, tmp_path / "out")
    # Copa writes to a scratch tag, never to a release's own names; the result is then tagged as the revision
    assert calls == [("v1.2.3-patched.4-refresh", ["linux/amd64", "linux/arm64"]),
                     ["-t", f"{REG}:v1.2.3-patched.4", f"{REG}:v1.2.3-patched.4-refresh"],
                     ["-t", f"{REG}:v1.2.3-patched", f"{REG}:v1.2.3-patched.4"],
                     ("v1.2.3-debug-patched.4-refresh", ["linux/amd64"]),
                     ["-t", f"{REG}:v1.2.3-debug-patched.4", f"{REG}:v1.2.3-debug-patched.4-refresh"],
                     ["-t", f"{REG}:v1.2.3-debug-patched", f"{REG}:v1.2.3-debug-patched.4"]]
    assert repo.state("app").lines["v1"].revision == 4

    # a release takes the revision while Copa runs: the refresh stops, and nothing of the release is overwritten
    calls.clear()
    monkeypatch.setattr(pipeline.copa, "for_image", lambda spec, image, out_tag, out, **k: existing.add(staging(5, "amd64"))
                        or calls.append(out_tag) or CopaResult(f"{REG}:{out_tag}", 1))
    with pytest.raises(RuntimeError, match="revision 5 was taken while Copa ran"):
        pipeline.refresh(repo, repo.load_recipe("app"), "v1", None, tmp_path / "out")
    assert calls == ["v1.2.3-patched.5-refresh"] and repo.state("app").lines["v1"].revision == 4


def test_publish_only_keeps_an_existing_final_tag_when_finishing(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    final = f"{REG}:v1.2.3-patched.5"
    # push just took revision 5, and a Copa refresh has published it in the meantime
    registry(monkeypatch, staging(5, "amd64"), staging(5, "arm64"), staging(5, "amd64", True), final)
    cmds = fake_publish_tools(monkeypatch)
    with pytest.raises(RuntimeError, match="something else .* published it since"):
        pipeline.publish(repo, repo.load_recipe("app"), "v1", None, tmp_path / "out", revision=5)
    assert cmds == [] and repo.state("app").lines["v1"].revision == 2  # nothing published, nothing recorded
    # a re-run of the same publish job (--finish-existing) finishes what its first attempt pushed
    pipeline.publish(repo, repo.load_recipe("app"), "v1", None, tmp_path / "out", revision=5, finish_existing=True)
    assert cmds[0] == ["-t", f"{REG}:v1.2.3-patched", final] and repo.state("app").lines["v1"].revision == 5


def test_built_revision_asks_for_each_tag_once(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    existing = {staging(3, "amd64"), staging(3, "arm64"), staging(3, "amd64", True), staging(4, "amd64")}
    asked = []
    monkeypatch.setattr(pipeline, "_tag_exists", lambda ref: asked.append(ref) or ref in existing)
    assert pipeline.built_revision(repo, repo.load_recipe("app"), "v1", "v1.2.3") == 3
    assert len(asked) == len(set(asked))
    # revision 3 is complete after its three per-arch tags; 4 stops at its first missing one, then shows it was used; 5 is
    # empty, which ends the search
    assert asked[:3] == [staging(3, "amd64"), staging(3, "arm64"), staging(3, "amd64", True)]
    assert asked[3:5] == [staging(4, "amd64"), staging(4, "arm64")]


def test_publish_never_publishes_a_recorded_revision(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)  # state/ records revision 2
    registry(monkeypatch, staging(2, "amd64"), staging(2, "arm64"), staging(2, "amd64", True))
    cmds = fake_publish_tools(monkeypatch)
    with pytest.raises(ValueError, match="never published again"):
        pipeline.publish(repo, repo.load_recipe("app"), "v1", None, tmp_path / "out", revision=2)
    with pytest.raises(LookupError):  # and `rebuild: false` doesn't pick it either
        pipeline.publish(repo, repo.load_recipe("app"), "v1", None, tmp_path / "out")
    assert cmds == [] and repo.state("app").lines["v1"].revision == 2


# --- plan: one line, its platforms, their runners ---------------------------------------------------


def recipe(name: str, **kw) -> dict:
    return {"name": name, "source": {"repo": f"o/{name}", "lines": [{"name": "v1", "tagPattern": "x"}]}, **kw}


def test_release_plan_follows_the_recipe_platforms(tmp_path):
    repo = make_repo(tmp_path, app_recipe(),
                     recipe("amd", build={"platforms": ["linux/amd64"], "images": [{"name": "amd"}]}),
                     recipe("arm", build={"images": [{"name": "arm", "platforms": ["linux/arm64"]}]}),
                     recipe("vendor", mode="image-only", build={"images": [{"name": "vendor", "upstream": "docker.io/v/v"}]}),
                     recipe("private", mode="image-only", publish=False, build={"images": [{"name": "p", "upstream": "docker.io/v/p"}]}),
                     recipe("helm", mode="component", artifact={"build": "go build -o /out/helm .", "output": "/out/helm"}),
                     recipe("mainframe", build={"platforms": ["linux/s390x"], "images": [{"name": "m"}]}))
    plan = pipeline.release_plan(repo, [("app", "v1"), ("amd", "v1"), ("arm", "v1"), ("vendor", "v1"), ("private", "v1"),
                                        ("helm", "v1"), ("app", "v1")])
    rows = {r["recipe"]: r for r in plan["include"]}
    assert list(rows) == ["app", "amd", "arm", "vendor"] and plan["errors"] == []  # once each
    assert rows["app"]["platforms"] == ["linux/amd64", "linux/arm64"] and rows["app"]["build"]  # the default: both
    assert rows["app"]["arches"] == [{"platform": "linux/amd64", "arch": "amd64", "runner": "ubuntu-24.04"},
                                     {"platform": "linux/arm64", "arch": "arm64", "runner": "ubuntu-24.04-arm"}]
    assert rows["amd"]["platforms"] == ["linux/amd64"] and [a["runner"] for a in rows["amd"]["arches"]] == ["ubuntu-24.04"]
    assert rows["arm"]["platforms"] == ["linux/arm64"]  # its only image is arm64-only
    assert not rows["vendor"]["build"]  # image-only: publish overlays the vendor image itself
    assert [(s["recipe"], s["reason"]) for s in plan["skipped"]] == [("private", "publish: false"),
                                                                     ("helm", "a component: it ships inside its parents' images")]
    # what can't be released is an error of its own: the other lines of the same push still go out
    plan = pipeline.release_plan(repo, [("mainframe", "v1"), ("app", "v9"), ("gone", "v1"), ("amd", "v1")])
    assert [r["recipe"] for r in plan["include"]] == ["amd"]
    errors = {e["recipe"]: e["error"] for e in plan["errors"]}
    assert "no native runner for linux/s390x" in errors["mainframe"] and "no line 'v9'" in errors["app"]
    assert "no recipe 'gone'" in errors["gone"]


def test_release_targets_are_the_patch_sets_a_push_changed(tmp_path):
    repo = make_repo(tmp_path)
    comp = tmp_path / "generated" / "app" / "v1.2.3" / "components" / "helm"
    comp.mkdir(parents=True)
    (comp / "bump-plan.json").write_text(json.dumps({"recipe": "helm", "line": "helm-4.2.1"}))
    broken = tmp_path / "generated" / "other" / "1.0"
    broken.mkdir(parents=True)
    (broken / "bump-plan.json").write_text("{not json")
    changed = ["generated/app/v1.2.3/bump-plan.json", "generated/app/v1.2.3/report.md",
               "generated/app/v1.2.3/components/helm/bump-plan.json",  # a component's own plan is not a release
               "generated/app/v1.2.2/bump-plan.json",  # gone (the push deleted it again)
               "generated/other/1.0/bump-plan.json",  # unreadable: an error row, the others still count
               "generated/app/v1.2.3/bump-plan.json"]
    targets, errors = pipeline.release_targets(repo, changed)
    assert targets == [("app", "v1")]
    assert [e["recipe"] for e in errors] == ["other"] and "unreadable patch set" in errors[0]["error"]


def test_image_platforms_must_be_among_the_build_platforms():
    with pytest.raises(ValidationError, match="none of its platforms"):
        Build.model_validate({"platforms": ["linux/amd64"], "images": [{"name": "a", "platforms": ["linux/arm64"]}]})
    with pytest.raises(ValidationError):
        Build.model_validate({"platforms": [], "images": [{"name": "a"}]})
    assert Build.model_validate({"images": [{"name": "a"}]}).platforms == ["linux/amd64", "linux/arm64"]
