import datetime as dt
import re
from pathlib import Path

import pytest

from patcher import pins
from patcher.versions import parse_semver

NOW = dt.datetime(2026, 10, 28, tzinfo=dt.timezone.utc)


def test_every_managed_tool_is_pinned_in_the_dockerfile():
    """tool-pins.yml updates exactly these ARGs: each tool needs a version and a sha256 per architecture."""
    pinned = pins.read_pins((Path(__file__).resolve().parents[1] / "Dockerfile").read_text())
    for tool in pins.TOOLS:
        assert parse_semver(pinned[f"{tool.arg}_VERSION"])
        for arch in pins.ARCHES:
            assert re.fullmatch(r"[0-9a-f]{64}", pinned[f"{tool.arg}_SHA256_{arch.upper()}"]), f"{tool.arg} {arch}"


def rel(tag: str, days_old: int) -> pins.Release:
    return pins.Release(tag, parse_semver(tag.lstrip("v")), NOW - dt.timedelta(days=days_old), f"https://x/{tag}")


def test_pick_highest_old_enough_stable_version():
    candidates = [rel("v0.76.1", 7), rel("v0.75.0", 27), rel("v0.74.3", 20), rel("v0.76.0-rc.1", 40)]
    # v0.76.1 is too new; v0.74.3 is a later-published backport but a lower version; -rc isn't stable
    assert pins.pick(candidates, 14, NOW).tag == "v0.75.0"
    assert pins.pick(candidates, 60, NOW) is None


def test_parse_sha256sum_variants():
    text = ("88aea77e41c2a3c45a9cbd64df9516ba887017442846213b3de178acbd3c9a46  ./mise-v2026.10.8-linux-arm64.tar.gz\n"
            "C6E65ABDDB348E25F10549DF887045629CF28CC72453CD1C63ACB717316B3F3F *trivy_0.75.0_Linux-64bit.tar.gz\n"
            "not a checksum line\n")
    assert pins.parse_sha256sum(text) == {
        "mise-v2026.10.8-linux-arm64.tar.gz": "88aea77e41c2a3c45a9cbd64df9516ba887017442846213b3de178acbd3c9a46",
        "trivy_0.75.0_Linux-64bit.tar.gz": "c6e65abddb348e25f10549df887045629cf28cc72453cd1c63acb717316b3f3f",
    }


def test_parse_yq_multi_hash_format():
    order = "MD5\nSHA-1\nSHA-256\nSHA-512\n"
    text = "yq_linux_amd64  md5aaa sha1bbb 8E34FC298390875DE416E6A4AFCB8CABECEB25D9AA8506C1A2F9353CF702EA5F sha512ccc\n"
    assert pins.parse_yq(text, order) == {"yq_linux_amd64": "8e34fc298390875de416e6a4afcb8cabeceb25d9aa8506c1a2f9353cf702ea5f"}


def test_read_and_write_pins():
    df = "FROM x\nARG TRIVY_VERSION=0.75.0\nARG TRIVY_SHA256_AMD64=aaa\nARG TRIVY_SHA256_ARM64=bbb\nRUN echo\n"
    assert pins.read_pins(df)["TRIVY_VERSION"] == "0.75.0"
    out = pins.write_pins(df, {"TRIVY_VERSION": "0.76.1", "TRIVY_SHA256_AMD64": "ccc", "TRIVY_SHA256_ARM64": "ddd"})
    assert out == "FROM x\nARG TRIVY_VERSION=0.76.1\nARG TRIVY_SHA256_AMD64=ccc\nARG TRIVY_SHA256_ARM64=ddd\nRUN echo\n"
    with pytest.raises(ValueError):
        pins.write_pins(df, {"COPA_VERSION": "1"})


def test_check_and_apply_end_to_end_with_fake_github(tmp_path, monkeypatch):
    tool = pins.Tool("COPA", "o/copa", {"amd64": "copa_{v}_linux_amd64.tar.gz", "arm64": "copa_{v}_linux_arm64.tar.gz"},
                     r"^copacetic_checksums\.txt$")
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("ARG COPA_VERSION=0.15.0\nARG COPA_SHA256_AMD64=old1\nARG COPA_SHA256_ARM64=old2\n")
    new = rel("v0.16.0", 20)
    new.assets = {"copacetic_checksums.txt": "https://dl/sums", "copa_0.16.0_linux_amd64.tar.gz": "u1",
                  "copa_0.16.0_linux_arm64.tar.gz": "u2"}
    monkeypatch.setattr(pins, "releases", lambda repo: [new, rel("v0.15.0", 60)])
    monkeypatch.setattr(pins, "pick", lambda c, age, now=None: max(c, key=lambda r: r.version))
    sums = f"{'1' * 64}  copa_0.16.0_linux_amd64.tar.gz\n{'2' * 64}  copa_0.16.0_linux_arm64.tar.gz\n"
    monkeypatch.setattr(pins, "_get", lambda url, api: sums.encode())
    updates = pins.check(dockerfile, 14, tools=(tool,))
    assert updates[0].changed and updates[0].sha256 == {"amd64": "1" * 64, "arm64": "2" * 64}
    pins.apply(dockerfile, updates)
    assert dockerfile.read_text() == f"ARG COPA_VERSION=0.16.0\nARG COPA_SHA256_AMD64={'1' * 64}\nARG COPA_SHA256_ARM64={'2' * 64}\n"
    assert "[`0.16.0`](https://x/v0.16.0)" in pins.summary(updates, 14)
