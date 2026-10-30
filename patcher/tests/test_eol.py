import datetime as dt
import types
import urllib.error

import pytest
import yaml

from patcher import eol, upstream
from patcher.config import Repo

TODAY = dt.date(2026, 10, 30)
PRODUCTS = {
    "nodejs": {"label": "Node.js", "releases": [
        {"name": "24", "eolFrom": "2028-04-30", "isEol": False},
        {"name": "22", "eolFrom": "2027-01-15", "isEol": False},  # 77 days away
        {"name": "20", "eolFrom": "2026-04-30", "isEol": True}]},
    "go": {"label": "Go", "releases": [
        {"name": "1.26", "eolFrom": None, "isEol": False},
        {"name": "1.25", "eolFrom": "2026-08-19", "isEol": True}]},
    "alpine-linux": {"label": "Alpine Linux", "releases": [
        {"name": "3.24", "eolFrom": "2028-06-01", "isEol": False},
        {"name": "3.17", "eolFrom": "2024-11-22", "isEol": True}]},
    "debian": {"label": "Debian", "releases": [
        {"name": "13", "codename": "Trixie", "eolFrom": "2030-06-30", "isEol": False},
        {"name": "11", "codename": "Bullseye", "eolFrom": "2026-08-31", "isEol": True}]},
    "ubuntu": {"label": "Ubuntu", "releases": [
        {"name": "24.04", "codename": "Noble Numbat", "eolFrom": "2029-05-31", "isEol": False}]},
}
UPSTREAM = {
    "Dockerfile": (
        "ARG REPO=docker.io\n"
        "FROM node:20-alpine AS ui\n"
        "FROM golang:1.26.10-bullseye AS build\n"
        "FROM ${REPO}/alpine:3.17.0 AS stage\n"  # below the recipe's alpine line: checked at 3.24
        "FROM build AS test\n"
        "FROM node:27 AS next\n"  # a release endoflife.date doesn't list yet
        "FROM gcr.io/distroless/static-debian11:nonroot\n"
        "FROM scratch\n"
    ),
    "tools/Dockerfile": "FROM alpine:3.17.0\n",  # an image's Dockerfile without an ecosystem: built as written
}


def _repo(tmp_path) -> Repo:
    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text("registry: ghcr.io/me\n")
    (tmp_path / "recipes" / "app.yaml").write_text(yaml.safe_dump({
        "name": "app",
        "source": {"repo": "o/app", "lines": [{"name": "v1", "tagPattern": r"^v1\.\d+\.\d+$"}]},
        "toolchain": {"go": "1.25", "node": "22"},
        "ecosystems": [{"type": "dockerfile", "files": ["Dockerfile", "ours.Dockerfile", "gone.Dockerfile"],
                        "minVersions": {"alpine": "3.24"}}],
        "build": {"images": [{"name": "app"}, {"name": "tool", "dockerfile": "tools/Dockerfile"}]},
    }))
    (tmp_path / "patches" / "app" / "files").mkdir(parents=True)
    (tmp_path / "patches" / "app" / "files" / "ours.Dockerfile").write_text("FROM ubuntu:noble\nFROM debian:bullseye-slim\n")
    return Repo(tmp_path)


def _check(repo, within_days=90):
    return eol.check(repo, within_days, today=TODAY, fetch=lambda p: PRODUCTS[p],
                     read=lambda source, commit, path: UPSTREAM.get(path), resolve=lambda source, line: ("v1.2.3", "c0ffee"))


def test_flags_end_of_life_and_soon_end_of_life_runtimes(tmp_path):
    repo = _repo(tmp_path)
    found = {(r.product, r.release): r for r in _check(repo)}
    assert sorted(found) == [("alpine-linux", "3.17"), ("debian", "11"), ("go", "1.25"), ("nodejs", "20"), ("nodejs", "22")]
    assert found["nodejs", "22"].days == 77 and found["nodejs", "22"].uses == ["toolchain `node: 22`"]
    assert found["nodejs", "20"].uses == ["v1 `Dockerfile` (stage ui): `node:20-alpine`"]
    assert found["go", "1.25"].label == "Go" and found["go", "1.25"].days == -72
    # one runtime, every place it is used: a codename in a tag, a release in an image name, our own overlay file
    assert found["debian", "11"].uses == ["v1 `Dockerfile` (stage build): `golang:1.26.10-bullseye`",
                                          "v1 `Dockerfile`: `gcr.io/distroless/static-debian11:nonroot`",
                                          "v1 `ours.Dockerfile`: `debian:bullseye-slim`"]
    # the stage minVersions raises is checked at 3.24 (fine); the image Dockerfile no ecosystem covers is not raised
    assert found["alpine-linux", "3.17"].uses == ["v1 `tools/Dockerfile`: `alpine:3.17.0`"]

    assert [(r.product, r.release) for r in _check(repo, within_days=30)] == [
        ("alpine-linux", "3.17"), ("debian", "11"), ("go", "1.25"), ("nodejs", "20")]  # node 22 is 77 days away
    assert "| app | Node.js 20 | 2026-04-30 (183 days ago) |" in eol.render_markdown(_check(repo), 90)


def test_release_names():
    assert eol._release("1.26.10-alpine3.23", 2) == "1.26"
    assert eol._release("24.04", 2) == "24.04" and eol._release("v1.36.3", 2) == "1.36"
    assert eol._release("20-alpine", 1) == "20"
    assert eol._release("3", 2) is None and eol._release("latest", 1) is None  # floating: the newest anyway


SOURCE = types.SimpleNamespace(url="https://github.com/o/app")


def test_a_file_that_cannot_be_read_fails_the_run(monkeypatch):
    calls = []

    def flaky(source, commit, path):
        calls.append(path)
        raise urllib.error.URLError("connection reset")

    monkeypatch.setattr(eol.time, "sleep", lambda s: None)
    monkeypatch.setattr(upstream, "read_remote_file", flaky)
    with pytest.raises(RuntimeError, match="connection reset"):
        eol._read(SOURCE, "c0ffee", "Dockerfile")  # issues would otherwise close as if nothing used the runtime
    assert len(calls) == 3

    def missing(source, commit, path):
        raise urllib.error.HTTPError("https://raw.githubusercontent.com/o/app/c0ffee/Dockerfile", 404, "Not Found", None, None)

    monkeypatch.setattr(upstream, "read_remote_file", missing)
    assert eol._read(SOURCE, "c0ffee", "Dockerfile") is None  # not in this release: nothing to check
