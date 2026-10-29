"""Shared adapter types."""

from __future__ import annotations

import glob
from dataclasses import dataclass, field
from pathlib import Path

from ..models import Recipe
from ..planner import Plan


@dataclass
class Change:
    ecosystem: str
    target: str
    name: str
    old: str
    new: str
    note: str = ""


@dataclass
class Failure:
    ecosystem: str
    target: str
    name: str
    wanted: str
    error: str
    hint: bool = False  # not a failed bump: a newer release exists beyond the policy (reported separately)


@dataclass
class Result:
    changes: list[Change] = field(default_factory=list)
    failures: list[Failure] = field(default_factory=list)
    flags: set[str] = field(default_factory=set)

    def extend(self, other: "Result") -> None:
        self.changes += other.changes
        self.failures += other.failures
        self.flags |= other.flags


@dataclass
class Ctx:
    src: Path
    recipe: Recipe
    plan: Plan
    env: dict[str, str]
    log: Path
    # minimum toolchain versions the build must use (e.g. {"go": "1.27.5"}), filled by the
    # planner (stdlib CVEs) and by adapters (raised `go` directives)
    requires: dict[str, str] = field(default_factory=dict)


def expand_dirs(src: Path, patterns: list[str], marker: str) -> list[str]:
    """Expand dir globs relative to `src`, keeping only dirs that contain `marker`."""
    out: list[str] = []
    for pat in patterns:
        for match in sorted(glob.glob(str(src / pat))):
            p = Path(match)
            if (p / marker).exists():
                rel = p.relative_to(src).as_posix() or "."
                if rel not in out:
                    out.append(rel)
    return out


def expand_files(src: Path, patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pat in patterns:
        for match in sorted(glob.glob(str(src / pat), recursive=True)):
            p = Path(match)
            if p.is_file() and p not in out:
                out.append(p)
    return out
