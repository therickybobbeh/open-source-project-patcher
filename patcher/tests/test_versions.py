from patcher.models import Level
from patcher.versions import level_between, parse_maven, parse_semver, pick_fix, split_fixed


def test_semver_ordering_and_prefix():
    assert parse_semver("v1.2.3") == parse_semver("1.2.3")
    assert parse_semver("1.2.3-rc.1") < parse_semver("1.2.3")
    assert parse_semver("1.2.3-rc.2") < parse_semver("1.2.3-rc.10")
    assert parse_semver("0.0.0-20230101120000-abcdef") < parse_semver("0.0.0-20240101120000-abcdef")
    assert parse_semver("v28.5.2+incompatible") == parse_semver("v28.5.2")
    assert parse_semver("3.24") < parse_semver("3.24.1")


def test_maven_ordering():
    assert parse_maven("4.1.118.Final") > parse_maven("4.1.117.Final")
    assert parse_maven("1.0") == parse_maven("1.0.0.Final")
    assert parse_maven("1.0-rc1") < parse_maven("1.0")
    assert parse_maven("1.0.1") > parse_maven("1.0-sp1") > parse_maven("1.0")
    assert parse_maven("2.0-alpha1") < parse_maven("2.0-beta1") < parse_maven("2.0-SNAPSHOT") < parse_maven("2.0")
    assert parse_maven("33.4.0-jre") > parse_maven("33.3.1-jre")


def test_split_fixed():
    assert split_fixed("1.21.11, 1.22.4") == ["1.21.11", "1.22.4"]
    assert split_fixed(None) == []
    assert split_fixed(">= 2.0.1") == ["2.0.1"]


def test_pick_fix_prefers_same_line():
    v, lvl = pick_fix("gomod", "1.22.1", "1.21.11, 1.22.4")
    assert str(v) == "1.22.4" and lvl == Level.patch
    v, lvl = pick_fix("gomod", "v0.30.0", "0.38.0")
    assert str(v) == "0.38.0" and lvl == Level.minor
    assert pick_fix("gomod", "v1.9.0", "2.0.0", Level.minor) is None
    v, lvl = pick_fix("gomod", "v1.9.0", "2.0.0", Level.major)
    assert lvl == Level.major
    assert pick_fix("gomod", "v1.2.3", "1.2.0") is None  # already past the fix


def test_level_between():
    assert level_between(parse_semver("1.2.3"), parse_semver("1.2.9")) == Level.patch
    assert level_between(parse_semver("1.2.3"), parse_semver("1.3.0")) == Level.minor
    assert level_between(parse_semver("1.2.3"), parse_semver("2.0.0")) == Level.major


def test_go_spec_never_lowers_the_recipe_toolchain():
    from patcher.toolchain import go_spec

    assert go_spec("1.27", "1.26.0") == "1.27"   # a sub-module's raised `go` line is below the recipe
    assert go_spec("1.27", "1.27.5") == "1.27"   # same minor: newest patch already satisfies it
    assert go_spec("1.27", "1.28.1") == "1.28"   # a bump needs a newer minor
    assert go_spec(None, "1.27.5") == "1.27"
    assert go_spec("1.27", None) == "1.27"


def test_zero_major_minor_bump_is_major_for_npm_and_cargo():
    a, b = parse_semver("0.18.20"), parse_semver("0.25.0")
    assert level_between(a, b, "pnpm") == Level.major
    assert level_between(a, b, "cargo") == Level.major
    assert level_between(a, b, "gomod") == Level.minor   # golang.org/x/* v0 bumps stay routine
    assert pick_fix("npm", "0.18.20", "0.25.0", Level.minor) is None


def test_collapse_keeps_separate_version_lines():
    from patcher.adapters.base import Change
    from patcher.pipeline import _collapse

    rows = _collapse([
        Change("pnpm", "ui/pnpm-lock.yaml", "brace-expansion", "1.1.14", "1.1.15", "CVE-1"),
        Change("pnpm", "ui/pnpm-lock.yaml", "brace-expansion", "2.0.1", "2.1.7", "CVE-2"),
        Change("gomod", "go.mod", "x/net", "v0.57.0", "v0.58.0", "CVE-3"),
        Change("gomod", "go.mod", "x/net", "v0.58.0", "v0.60.0", "CVE-4"),
    ])
    assert [(r.name, r.old, r.new) for r in rows] == [
        ("brace-expansion", "1.1.14", "1.1.15"), ("brace-expansion", "2.0.1", "2.1.7"), ("x/net", "v0.57.0", "v0.60.0")]
    assert rows[2].note == "CVE-3, CVE-4"
