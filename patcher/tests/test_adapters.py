import datetime as dt
from pathlib import Path

import pytest

from patcher import registry
from patcher.adapters import dockerfile, files, maven
from patcher.adapters.base import Ctx
from patcher.config import line_key, render
from patcher.models import DockerfileEco, FileEdit, FilesEco, Level, Line, Recipe, SkipFile
from patcher.planner import Plan
from patcher.tests_runner import check_expiry, render_skips


def ctx(src: Path, **kw) -> Ctx:
    r = Recipe.model_validate({"name": "demo", "source": {"repo": "o/r", "lines": [{"tagPattern": "x"}]}})
    return Ctx(src=src, recipe=r, plan=Plan(), env={}, log=src / "log.txt", **kw)


GOLANG_TAGS = ("1.26.8-alpine3.23", "1.26.9-alpine3.23", "1.27.3-alpine3.24", "1.27.5-alpine3.24", "1.27.5-alpine3.23",
               "1.28rc1-alpine3.24", "1.27-alpine3.24", "1.27.4", "latest")
ALPINE_TAGS = ("3.23.4", "3.24.2", "3.24.3", "3.25.0", "edge")


@pytest.fixture
def fake_registry(monkeypatch):
    tags = {"golang": GOLANG_TAGS, "alpine": ALPINE_TAGS}
    monkeypatch.setattr(registry, "list_tags", lambda image: tags[registry.parse_ref(image).repository.split("/")[-1]])
    monkeypatch.setattr(registry, "digest", lambda image, tag: "sha256:" + "a" * 64)


def test_best_tag_patch_level(fake_registry):
    assert dockerfile.best_tag("golang:1.27.3-alpine3.24", "1.27.3-alpine3.24", Level.patch) == "1.27.5-alpine3.24"
    assert dockerfile.best_tag("alpine:3.24.2", "3.24.2", Level.patch) == "3.24.3"
    assert dockerfile.best_tag("alpine:3.24.2", "3.24.2", Level.minor) == "3.25.0"


def test_dockerfile_rewrite_and_go_requirement(tmp_path, fake_registry):
    (tmp_path / "Dockerfile").write_text(
        "ARG BASE=alpine\n"
        "FROM --platform=$BUILDPLATFORM golang:1.26.8-alpine3.23@sha256:" + "b" * 64 + " AS builder\n"
        "RUN go build\n"
        "FROM builder AS test\n"
        "FROM alpine:3.24.2\n"
    )
    c = ctx(tmp_path, requires={"go": "1.27.5"})  # a bump raised the go directive to 1.27
    res = dockerfile.apply(c, DockerfileEco(type="dockerfile"))
    text = (tmp_path / "Dockerfile").read_text()
    # the go requirement allows moving to the 1.27 line (same alpine suffix shape)
    assert "FROM --platform=$BUILDPLATFORM golang:1.27.5-alpine3.23@sha256:" in text
    assert "FROM builder AS test" in text
    assert f"FROM alpine:3.24.3@sha256:{'a' * 64}" in text
    assert {c.name for c in res.changes} == {"golang", "alpine"}


def test_dockerfile_arg_bump(tmp_path, fake_registry):
    (tmp_path / "Dockerfile").write_text("ARG GO_VERSION=1.26.8\nFROM golang:${GO_VERSION}-alpine3.23 AS b\n")
    res = dockerfile.apply(ctx(tmp_path), DockerfileEco(type="dockerfile", pinDigest=False))
    assert (tmp_path / "Dockerfile").read_text().startswith("ARG GO_VERSION=1.26.9\n")
    assert res.changes[0].name == "ARG GO_VERSION"


def test_dockerfile_two_args(tmp_path, fake_registry):
    (tmp_path / "Dockerfile").write_text("ARG GO_VERSION=1.26.8\nARG ALPINE_VERSION=3.23\nFROM golang:${GO_VERSION}-alpine${ALPINE_VERSION} AS b\n")
    res = dockerfile.apply(ctx(tmp_path), DockerfileEco(type="dockerfile", pinDigest=False))
    assert (tmp_path / "Dockerfile").read_text().startswith("ARG GO_VERSION=1.26.9\nARG ALPINE_VERSION=3.23\n")
    assert [c.name for c in res.changes] == ["ARG GO_VERSION"]


def test_dockerfile_whole_ref_arg(tmp_path, fake_registry):
    (tmp_path / "Dockerfile").write_text("ARG BASE_IMAGE=docker.io/library/alpine:3.24.2@sha256:" + "c" * 64 + "\nFROM $BASE_IMAGE AS base\n")
    dockerfile.apply(ctx(tmp_path), DockerfileEco(type="dockerfile"))
    assert (tmp_path / "Dockerfile").read_text().startswith("ARG BASE_IMAGE=docker.io/library/alpine:3.24.3@sha256:" + "a" * 64 + "\n")


def test_files_var_edit_with_derived(tmp_path, monkeypatch):
    (tmp_path / "Dockerfile").write_text("ENV REDIS_VERSION=8.10.3\nENV REDIS_DOWNLOAD_URL=https://x/8.10.3/redis.tar.gz\n"
                                         "ENV REDIS_DOWNLOAD_SHA=abc\n")
    monkeypatch.setattr(files, "_sha256_of", lambda url: "f" * 64)
    eco = FilesEco(type="files", edits=[FileEdit(file="Dockerfile", var="REDIS_VERSION", to="8.10.4", derived=[
        {"var": "REDIS_DOWNLOAD_URL", "value": "https://x/{{version}}/redis.tar.gz"},
        {"var": "REDIS_DOWNLOAD_SHA", "sha256Of": "https://x/{{version}}/redis.tar.gz"},
    ])])
    res = files.apply(ctx(tmp_path), eco)
    text = (tmp_path / "Dockerfile").read_text()
    assert "REDIS_VERSION=8.10.4" in text and "https://x/8.10.4/redis.tar.gz" in text and "REDIS_DOWNLOAD_SHA=" + "f" * 64 in text
    assert res.changes[0].old == "8.10.3"


def test_files_shell_var_keeps_v_prefix(tmp_path):
    (tmp_path / "tool-versions.sh").write_text('#!/bin/bash\nhelm3_version=v4.3.1\nkustomize5_version=5.8.3\n')
    files.apply(ctx(tmp_path), FilesEco(type="files", edits=[FileEdit(file="tool-versions.sh", var="helm3_version", to="4.3.2")]))
    assert "helm3_version=v4.3.2\n" in (tmp_path / "tool-versions.sh").read_text()


def test_maven_dependency_management_pin(tmp_path):
    pom = tmp_path / "pom.xml"
    pom.write_text("""<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <dependencyManagement>
    <dependencies>
      <dependency>
        <groupId>io.netty</groupId>
        <artifactId>netty-bom</artifactId>
        <version>4.1.117.Final</version>
        <type>pom</type>
        <scope>import</scope>
      </dependency>
    </dependencies>
  </dependencyManagement>
  <profiles><profile><dependencyManagement><dependencies></dependencies></dependencyManagement></profile></profiles>
</project>
""")
    maven.pin_dependency_management(pom, "io.netty:netty-codec-http", "4.1.118.Final", ["CVE-2025-24970"])
    text = pom.read_text()
    first = text.index("<artifactId>netty-codec-http</artifactId>")
    assert first < text.index("<artifactId>netty-bom</artifactId>")  # pinned before the BOM import
    assert text.count("netty-codec-http") == 1
    maven.pin_dependency_management(pom, "io.netty:netty-codec-http", "4.1.118.Final", ["again"])
    assert pom.read_text().count("netty-codec-http") == 1  # idempotent


def test_skip_rendering():
    skips = SkipFile.model_validate({"skips": [
        {"match": "^TestIndex$", "reason": "network", "owner": "me"},
        {"match": "^Test_nativeHelmChart_ExtractChart$", "reason": "network", "owner": "me"},
    ]})
    go = render_skips("go", skips, Path("/tmp"))
    assert go.regex == "(^TestIndex$)|(^Test_nativeHelmChart_ExtractChart$)"
    assert go.args.startswith("-skip=")
    nx = render_skips("nextest", skips, Path("/tmp"))
    assert nx.args.startswith("-E 'not ((test(/^TestIndex$/))")


def test_skip_expiry():
    skips = SkipFile.model_validate({"skips": [
        {"match": "a", "reason": "r", "owner": "o", "expires": "2026-10-01"},
        {"match": "b", "reason": "r", "owner": "o", "expires": "2026-06-01"},
        {"match": "c", "reason": "r", "owner": "o"},
    ]})
    warn, fail = check_expiry(skips, 30, today=dt.date(2026, 10, 27))
    assert [e.match for e in warn] == ["a"] and [e.match for e in fail] == ["b"]


def test_line_key_and_render():
    assert line_key(Line(tagPattern=r"^v3\.5\.\d+$")) == "v3.5"
    assert line_key(Line(tagPattern=r"^\d+\.\d+\.\d+$", name="all")) == "all"
    assert render("{{tag}}-distroless", {"tag": "v2.46.1"}) == "v2.46.1-distroless"
    with pytest.raises(KeyError):
        render("{{nope}}", {})


def test_upstream_tag_of_inverts_final_tag(tmp_path):
    from patcher.config import Repo
    from patcher.pipeline import final_tag, upstream_tag_of

    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text("registry: ghcr.io/x\n")
    r = Repo(tmp_path)
    for up in ("v2.46.1", "v2.46.1-distroless", "0.4.3", "3.10.0-eclipse-temurin-21-noble"):
        assert upstream_tag_of(r, final_tag(r, up, 7)) == up


def test_gomod_replace_group_moves_once_to_the_highest_fix(tmp_path, monkeypatch):
    from patcher.adapters import gomod
    from patcher.models import GoModEco
    from patcher.planner import Bump, Plan

    (tmp_path / "go.mod").write_text("module x\n")
    info = {
        "Go": "1.26.0",
        "Require": [{"Path": "k8s.io/api", "Version": "v0.36.1"}, {"Path": "k8s.io/apimachinery", "Version": "v0.36.1"},
                    {"Path": "k8s.io/client-go", "Version": "v0.36.1"}, {"Path": "k8s.io/utils", "Version": "v0.0.0-2026"},
                    {"Path": "golang.org/x/net", "Version": "v0.59.0"}],
        "Replace": [{"Old": {"Path": p}, "New": {"Path": p, "Version": "v0.36.1"}}
                    for p in ("k8s.io/api", "k8s.io/apimachinery", "k8s.io/client-go")],
    }
    monkeypatch.setattr(gomod, "mod_info", lambda src, d, env: info)
    calls = []
    monkeypatch.setattr(gomod, "run", lambda cmd, **kw: calls.append(cmd))
    monkeypatch.setattr(gomod, "_go_get", lambda cwd, gets, env, ctx, res, target: calls.append(["go", "get", *sorted(gets)]))
    plan = Plan(bumps=[Bump("gomod", "go.mod", "k8s.io/apimachinery", "v0.36.1", "v0.36.2", "patch", ["CVE-A"]),
                       Bump("gomod", "go.mod", "k8s.io/api", "v0.36.1", "v0.36.3", "patch", ["CVE-B"]),
                       Bump("gomod", "go.mod", "golang.org/x/net", "v0.59.0", "v0.60.0", "minor", ["CVE-C"])])
    c = ctx(tmp_path)
    c.plan = plan
    res = gomod.apply(c, GoModEco(type="gomod", replaceGroups=[{"pattern": r"^k8s\.io/"}]))
    edit = next(cmd for cmd in calls if cmd[:3] == ["go", "mod", "edit"])
    assert sorted(a for a in edit if a.startswith("-replace")) == [
        f"-replace={p}={p}@v0.36.3" for p in ("k8s.io/api", "k8s.io/apimachinery", "k8s.io/client-go")]
    assert ["go", "get", "golang.org/x/net"] in calls
    moved = [ch for ch in res.changes if ch.name.startswith("k8s.io/")]
    assert sorted(ch.name for ch in moved) == ["k8s.io/api", "k8s.io/apimachinery", "k8s.io/client-go"]  # once each, utils untouched
    assert all(ch.new == "v0.36.3" for ch in moved)
    assert "replaceGroupMoved" in res.flags


def test_pnpm_overrides_move_existing_pins(tmp_path, monkeypatch):
    import json
    from patcher.adapters import node
    from patcher.models import NodeEco
    from patcher.planner import Bump, Plan

    (tmp_path / "ui").mkdir()
    (tmp_path / "ui" / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n")
    (tmp_path / "ui" / "package.json").write_text(json.dumps({"name": "ui", "pnpm": {"overrides": {"dompurify": "3.4.13"}}}, indent=2) + "\n")
    monkeypatch.setattr(node, "run", lambda *a, **k: None)
    monkeypatch.setattr(node, "_pnpm_major", lambda env: 10)
    c = ctx(tmp_path)
    c.plan = Plan(bumps=[Bump("pnpm", "ui/pnpm-lock.yaml", "dompurify", "3.4.13", "3.4.17", "patch", ["GHSA-1"]),
                         Bump("pnpm", "ui/pnpm-lock.yaml", "qs", "6.15.2", "6.16.1", "minor", ["CVE-2"])])
    node.apply(c, NodeEco(type="pnpm", dirs=["ui"]))
    ov = json.loads((tmp_path / "ui" / "package.json").read_text())["pnpm"]["overrides"]
    assert ov == {"dompurify": "3.4.17", "qs@6.15.2": "6.16.1"}


def test_failure_summary_and_clean_env(monkeypatch):
    from patcher import proc
    from patcher.tests_runner import failure_summary

    log = "=== RUN   TestA\n--- PASS: TestA (0.00s)\n--- FAIL: TestFlag_IsSet (0.00s)\n    --- FAIL: TestFlag_IsSet/x (0.00s)\nFAIL\tgithub.com/x/pkg/flag\t0.1s\nok  \tgithub.com/x/other\n"
    assert failure_summary("go", log).splitlines() == ["--- FAIL: TestFlag_IsSet (0.00s)", "    --- FAIL: TestFlag_IsSet/x (0.00s)",
                                                       "FAIL\tgithub.com/x/pkg/flag\t0.1s"]
    assert failure_summary("bats", "ok 1 a\nnot ok 2 b\n") == "not ok 2 b"
    monkeypatch.setenv("TRIVY_CACHE_DIR", "/opt/trivy-cache")
    assert "TRIVY_CACHE_DIR" not in proc._env({}, clean=True)
    assert proc._env({"TRIVY_X": "1"}, clean=True)["TRIVY_X"] == "1"   # explicit recipe env still wins
    assert "TRIVY_CACHE_DIR" in proc._env({})


def test_maven_pins_follow_file_indentation_and_reactor_roots(tmp_path):
    from patcher.adapters.maven import _root_for

    pom = tmp_path / "pom.xml"
    pom.write_text("""<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <dependencyManagement>
        <dependencies>
            <!-- Runtime -->
            <dependency>
                <groupId>a</groupId>
                <artifactId>b</artifactId>
                <version>1</version>
            </dependency>
        </dependencies>
    </dependencyManagement>
</project>
""")
    maven.pin_dependency_management(pom, "org.x:y", "2.0", ["CVE-1"])
    text = pom.read_text()
    assert ("        <dependencies>\n            <!-- patcher: CVE-1 -->\n            <dependency>\n"
            "                <groupId>org.x</groupId>\n") in text
    assert "            <!-- Runtime -->" in text  # following line keeps its indentation
    roots = ["pom.xml", "docker-images/artifacts/kafka-thirdparty-libs/4.3.x/pom.xml"]
    assert _root_for("cluster-operator/pom.xml", roots) == "pom.xml"
    assert _root_for("docker-images/artifacts/kafka-thirdparty-libs/4.3.x/pom.xml", roots) == roots[1]
    assert _root_for("x/pom.xml", ["sub/pom.xml"]) is None
