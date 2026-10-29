"""Turn scan findings + recipe overrides/holds into a bump plan.

Rules (see README "How versions are chosen"):
1. Only findings with a fixed version are actionable.
2. For each CVE pick the smallest fixed version > installed, preferring the same
   major.minor, then the same major (bounded by the policy cap for the ecosystem).
3. Per package take the max of those picks.
4. Holds remove a package from the plan (or cap it at `max`).
5. Overrides force `min`/`version` whenever a lower version is present - even without a CVE.
6. Go `stdlib` findings become a toolchain requirement (Go version used to build), not a go.mod bump.
"""

from __future__ import annotations

import fnmatch
import posixpath
from dataclasses import asdict, dataclass, field

from .ecosystems import CVE_ECOSYSTEMS
from .models import Hold, Level, Override, Recipe
from .scan import Finding, Package, ScanReport
from .versions import Version, level_between, pick_fix, split_fixed, try_parse, with_style

# ecosystems the source adapters can change (others are reported only)
PATCHABLE = set(CVE_ECOSYSTEMS)


@dataclass
class Bump:
    ecosystem: str
    target: str  # manifest/lockfile the finding came from, e.g. api/v2/go.mod
    name: str
    installed: str
    to: str
    level: str
    reasons: list[str] = field(default_factory=list)
    direct: bool | None = None

    @property
    def dir(self) -> str:
        return posixpath.dirname(self.target) or "."


@dataclass
class Unresolved:
    ecosystem: str
    target: str
    name: str
    installed: str
    vuln_id: str
    severity: str
    fixed: str | None
    why: str


@dataclass
class Plan:
    bumps: list[Bump] = field(default_factory=list)
    unresolved: list[Unresolved] = field(default_factory=list)
    toolchain: dict[str, str] = field(default_factory=dict)  # e.g. {"go": "1.27.5"}
    notes: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.bumps and not self.toolchain

    def to_json(self) -> dict:
        return {
            "bumps": [asdict(b) | {"dir": b.dir} for b in self.bumps],
            "unresolved": [asdict(u) for u in self.unresolved],
            "toolchain": self.toolchain,
        }

    def for_ecosystem(self, *ecos: str) -> list[Bump]:
        return [b for b in self.bumps if b.ecosystem in ecos]


def _match(rules: list, name: str):
    for r in rules:
        if fnmatch.fnmatchcase(name, r.name):
            return r
    return None


def _unresolved(f: Finding, why: str) -> Unresolved:
    return Unresolved(f.ecosystem, f.target, f.name, f.installed, f.vuln_id, f.severity, f.fixed, why)


def build_plan(report: ScanReport, recipe: Recipe, ecosystems: set[str] | None = None, gate=None) -> Plan:
    plan = Plan()
    active = (ecosystems or PATCHABLE) & PATCHABLE
    stdlib_picks: list[Version] = []

    # one group per installed version: lockfiles can hold several versions of a package
    groups: dict[tuple[str, str, str, str], list[Finding]] = {}
    for f in report.findings:
        if f.ecosystem == "gomod" and f.name == "stdlib":
            if not f.fixable:
                plan.unresolved.append(_unresolved(f, "no fixed version"))
                continue
            cap = recipe.policy.for_ecosystem("go-toolchain")
            pick = pick_fix("gomod", f.installed, f.fixed, cap)
            if pick:
                stdlib_picks.append(pick[0])
            else:
                plan.unresolved.append(_unresolved(f, f"needs-human: Go toolchain fix exceeds `{cap.value}` policy"))
            continue
        if f.ecosystem not in active:
            continue
        groups.setdefault((f.ecosystem, f.target, f.name, f.installed), []).append(f)

    if stdlib_picks:
        plan.toolchain["go"] = str(max(stdlib_picks)).lstrip("v")

    bumps: dict[tuple[str, str, str, str], Bump] = {}
    for (eco, target, name, installed), findings in groups.items():
        cur = try_parse(eco, installed)
        if cur is None:
            for f in findings:
                plan.unresolved.append(_unresolved(f, f"unparseable installed version {installed!r}"))
            continue
        hold: Hold | None = _match(recipe.holds.get(eco, []), name)
        cap = recipe.policy.for_ecosystem(eco)
        hold_max = try_parse(eco, hold.max) if hold and hold.max else None
        picks: list[tuple[Version, Level, Finding]] = []
        for f in findings:
            if not f.fixable:
                plan.unresolved.append(_unresolved(f, "no fixed version"))
                continue
            if hold and not hold.max:
                plan.unresolved.append(_unresolved(f, f"held: {hold.reason}"))
                continue
            allow = None
            if gate is not None:
                allow = lambda v, f=f, eco=eco, name=name, installed=installed: gate.check(
                    eco, name, _styled(eco, v.raw, installed), f.severity, f.vuln_id)[0]
            fixed = f.fixed
            if gate is not None:  # a withdrawn fix version (npm-deprecated, yanked) is replaced by the next good one
                subs = [s for v in split_fixed(f.fixed) if (s := gate.replacement(eco, name, v))]
                if subs:
                    fixed = ", ".join([*split_fixed(f.fixed), *subs])
            pick = pick_fix(eco, installed, fixed, cap, allow)
            if pick is None:
                why = "needs-human: fix requires a bump beyond the `%s` policy" % cap.value
                capped = pick_fix(eco, installed, fixed, cap)
                if capped is not None and gate is not None:
                    why = gate.check(eco, name, _styled(eco, capped[0].raw, installed), f.severity, f.vuln_id)[1]
                elif pick_fix(eco, installed, f.fixed, None) is None:
                    why = f"no fixed version above installed (fixed: {f.fixed})"
                plan.unresolved.append(_unresolved(f, why))
                continue
            if hold_max and pick[0] > hold_max:
                plan.unresolved.append(_unresolved(f, f"held at <= {hold.max}: {hold.reason}"))
                continue
            picks.append((pick[0], pick[1], f))
        if not picks:
            continue
        best = max(p[0] for p in picks)
        bumps[(eco, target, name, installed)] = Bump(
            ecosystem=eco,
            target=target,
            name=name,
            installed=installed,
            to=_styled(eco, best.raw, installed),
            level=level_between(cur, best, eco).value,
            reasons=sorted({p[2].vuln_id for p in picks}),
            direct=_is_direct(findings[0].relationship),
        )

    _apply_overrides(report.packages, recipe, active, bumps)
    plan.bumps = sorted(bumps.values(), key=lambda b: (b.ecosystem, b.target, b.name))
    if gate is not None:
        plan.notes = sorted(gate.notes)
    return plan


def _styled(eco: str, version: str, like: str) -> str:
    # Go module versions always carry a `v`; Trivy's FixedVersion often omits it
    if eco == "gomod":
        return version if version.startswith("v") else f"v{version}"
    return with_style(version, like) if eco != "maven" else version


def _is_direct(rel: str | None) -> bool | None:
    if rel is None:
        return None
    return rel in ("direct", "root", "workspace")


def _apply_overrides(packages: list[Package], recipe: Recipe, active: set[str], bumps: dict) -> None:
    for pkg in packages:
        eco = pkg.ecosystem
        if eco not in active or pkg.relationship in ("root", "workspace"):
            continue
        rule: Override | None = _match(recipe.overrides.get(eco, []), pkg.name)
        if not rule:
            continue
        cur = try_parse(eco, pkg.version)
        if cur is None:
            continue
        key = (eco, pkg.target, pkg.name, pkg.version)
        existing = bumps.get(key)
        planned = try_parse(eco, existing.to) if existing else cur
        if rule.version:
            want = try_parse(eco, rule.version)
            if want is None or want == cur:
                continue
        else:
            want = try_parse(eco, rule.min)
            if want is None or planned >= want:
                continue
        reason = f"override: {rule.reason}"
        to = _styled(eco, want.raw, pkg.version)
        if existing:
            existing.to = to
            existing.level = level_between(cur, want, eco).value
            existing.reasons.append(reason)
        else:
            bumps[key] = Bump(eco, pkg.target, pkg.name, pkg.version, to, level_between(cur, want, eco).value, [reason], _is_direct(pkg.relationship))
