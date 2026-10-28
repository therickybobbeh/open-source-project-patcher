"""Version parsing/ordering for the ecosystems we patch.

* semver-ish (Go modules, Cargo, npm, Docker tags, Redis, Go stdlib): `v` prefix optional,
  any number of numeric components, semver prerelease ordering, build metadata ignored
  for ordering (Go's `+incompatible` is kept in the original string).
* maven: an approximation of Maven's ComparableVersion (qualifier ordering
  alpha < beta < milestone < rc < snapshot < release(""/ga/final) < sp < unknown).
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass, field

from .models import Level

_SEMVER = re.compile(r"^v?(?P<nums>\d+(?:\.\d+)*)(?:-(?P<pre>[0-9A-Za-z.\-]+))?(?:\+(?P<build>[0-9A-Za-z.\-]+))?$")


class InvalidVersion(ValueError):
    pass


@functools.total_ordering
@dataclass(frozen=True)
class Version:
    raw: str
    nums: tuple[int, ...]
    key: tuple = field(compare=False, repr=False)

    def __lt__(self, other: "Version") -> bool:
        return self.key < other.key

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Version) and self.key == other.key

    def __hash__(self) -> int:
        return hash(self.key)

    @property
    def major(self) -> int:
        return self.nums[0] if self.nums else 0

    @property
    def minor(self) -> int:
        return self.nums[1] if len(self.nums) > 1 else 0

    @property
    def patch(self) -> int:
        return self.nums[2] if len(self.nums) > 2 else 0

    def __str__(self) -> str:
        return self.raw


def _pre_key(pre: str | None) -> tuple:
    if pre is None:
        return (1,)  # a release sorts after any prerelease
    ids = []
    for ident in pre.split("."):
        ids.append((0, int(ident), "") if ident.isdigit() else (1, 0, ident))
    return (0, tuple(ids))


def parse_semver(s: str) -> Version:
    s = s.strip()
    m = _SEMVER.match(s)
    if not m:
        raise InvalidVersion(s)
    nums = tuple(int(x) for x in m.group("nums").split("."))
    padded = nums + (0,) * max(0, 4 - len(nums))
    return Version(raw=s, nums=nums, key=(padded, _pre_key(m.group("pre"))))


_MAVEN_QUALIFIERS = {"alpha": 0, "a": 0, "beta": 1, "b": 1, "milestone": 2, "m": 2, "rc": 3, "cr": 3, "snapshot": 4, "": 5, "ga": 5, "final": 5, "release": 5, "sp": 6}


def parse_maven(s: str) -> Version:
    s = s.strip()
    tokens = re.findall(r"\d+|[A-Za-z]+", s)
    if not tokens or not tokens[0].isdigit():
        raise InvalidVersion(s)
    items: list[tuple] = []
    for i, tok in enumerate(tokens):
        if tok.isdigit():
            items.append((2, int(tok), ""))
        else:
            q = tok.lower()
            # single-letter a/b/m are only qualifiers when followed by a number (e.g. 1.0a1)
            if q in ("a", "b", "m") and not (i + 1 < len(tokens) and tokens[i + 1].isdigit()):
                items.append((1, 7, q))
            elif q in _MAVEN_QUALIFIERS:
                items.append((1, _MAVEN_QUALIFIERS[q], ""))
            else:
                items.append((1, 7, q))
    # trim trailing "null" items (0 / release qualifier) so 1.0 == 1 == 1.0.0.Final
    while items and items[-1] in ((2, 0, ""), (1, 5, "")):
        items.pop()
    nums = tuple(int(t) for t in tokens if t.isdigit())[:4]
    key = tuple(items)
    return Version(raw=s, nums=nums, key=_MavenKey(key))  # type: ignore[arg-type]


@functools.total_ordering
class _MavenKey:
    """Compare item lists with Maven padding semantics: a missing item acts as `release` vs a
    qualifier and as `0` vs a number."""

    __slots__ = ("items",)

    def __init__(self, items: tuple):
        self.items = items

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _MavenKey) and self._cmp(other) == 0

    def __lt__(self, other: "_MavenKey") -> bool:
        return self._cmp(other) < 0

    def __hash__(self) -> int:
        return hash(self.items)

    def _cmp(self, other: "_MavenKey") -> int:
        a, b = self.items, other.items
        for i in range(max(len(a), len(b))):
            x = a[i] if i < len(a) else None
            y = b[i] if i < len(b) else None
            if x is None:
                x = (2, 0, "") if y and y[0] == 2 else (1, 5, "")
            if y is None:
                y = (2, 0, "") if x[0] == 2 else (1, 5, "")
            if x != y:
                return -1 if x < y else 1
        return 0


def parse(ecosystem: str, s: str) -> Version:
    if ecosystem in ("maven", "pom", "jar", "gradle"):
        return parse_maven(s)
    if ecosystem == "gomod" and s.startswith("go"):  # toolchain directive "go1.27.3"
        s = s[2:]
    return parse_semver(s)


def try_parse(ecosystem: str, s: str | None) -> Version | None:
    if not s:
        return None
    try:
        return parse(ecosystem, s)
    except InvalidVersion:
        return None


# package managers whose caret ranges treat a 0.x minor bump as breaking (^0.18 excludes 0.25)
ZERO_MAJOR_STRICT = {"npm", "pnpm", "yarn", "cargo"}


def level_between(old: Version, new: Version, ecosystem: str | None = None) -> Level:
    if new.major != old.major:
        return Level.major
    if new.minor != old.minor:
        return Level.major if (old.major == 0 and ecosystem in ZERO_MAJOR_STRICT) else Level.minor
    return Level.patch


def split_fixed(fixed: str | None) -> list[str]:
    """Trivy joins one fixed version per release line with ", " (e.g. "1.21.11, 1.22.4")."""
    if not fixed:
        return []
    out = []
    for part in re.split(r"\s*,\s*|\s*\|\|\s*", fixed):
        part = part.strip().lstrip(">=~^ ").strip()
        if part:
            out.append(part)
    return out


def pick_fix(ecosystem: str, installed: str, fixed: str | None, cap: Level | None = None) -> tuple[Version, Level] | None:
    """Smallest fixed version above `installed`, preferring the same major.minor, then the same
    major, then anything. If `cap` is set, candidates beyond the cap are ignored."""
    cur = try_parse(ecosystem, installed)
    if cur is None:
        return None
    cands = sorted(v for v in (try_parse(ecosystem, f) for f in split_fixed(fixed)) if v is not None and v > cur)
    if not cands:
        return None
    for want in (Level.patch, Level.minor, Level.major):
        if cap is not None and want.rank > cap.rank:
            break
        for c in cands:
            if level_between(cur, c, ecosystem) == want:
                return c, want
    return None


def with_style(version: str, like: str) -> str:
    """Render `version` with the same `v` prefix convention as `like`."""
    bare = version[1:] if version.startswith("v") else version
    return f"v{bare}" if like.startswith("v") else bare
