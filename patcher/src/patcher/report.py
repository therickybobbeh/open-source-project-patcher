"""Before/after comparison and the Markdown report that becomes the PR body."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .adapters.base import Change, Failure
from .models import Recipe, SkipEntry, VexFile
from .planner import Unresolved
from .scan import Finding, ScanReport
from .tests_runner import TestOutcome
from . import vex as vexmod

SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
MAX_ROWS = 60
BUNDLED = {"gobinary", "rustbinary", "jar", "node-pkg", "python-pkg"}


@dataclass
class ImageOutcome:
    name: str
    ref: str
    upstream_ref: str | None
    before: ScanReport | None
    after: ScanReport | None
    smoke: list[dict] = field(default_factory=list)
    copa: str = ""
    own_binaries: list[str] = field(default_factory=list)


def bundled_paths(img: ImageOutcome, fs_after: ScanReport | None) -> set[str]:
    """Binary/jar paths in the image that were NOT built from the patched source.

    Uses `ownBinaries` from the recipe when given; otherwise a binary counts as ours when most of
    its (non-stdlib) modules match the patched source tree's packages at the same version."""
    if not img.after:
        return set()
    paths: dict[str, list] = {}
    for p in img.after.packages:
        if p.ecosystem in BUNDLED:
            paths.setdefault(p.location, []).append(p)
    if img.own_binaries:
        own = {o.strip("/") for o in img.own_binaries}
        return {t for t in paths if t.strip("/") not in own}
    src = {(p.name, p.version.lstrip("v")) for p in (fs_after.packages if fs_after else [])}
    bundled = set()
    for target, pkgs in paths.items():
        deps = [p for p in pkgs if p.name != "stdlib" and p.relationship not in ("root", "workspace")]
        if not deps:
            continue
        matched = sum((p.name, p.version.lstrip("v")) in src for p in deps)
        if matched / len(deps) < 0.8:
            bundled.add(target)
    return bundled


@dataclass
class Summary:
    recipe: Recipe
    line: str
    tag: str
    commit: str
    status: str  # success | tests-failed | build-failed | apply-failed | no-changes
    fs_before: ScanReport | None = None
    fs_after: ScanReport | None = None
    images: list[ImageOutcome] = field(default_factory=list)
    changes: list[Change] = field(default_factory=list)
    failures: list[Failure] = field(default_factory=list)
    unresolved: list[Unresolved] = field(default_factory=list)
    tests: TestOutcome | None = None
    attempts: list[str] = field(default_factory=list)
    vex: VexFile = field(default_factory=VexFile)
    notes: list[str] = field(default_factory=list)


def _fixable_keys(r: ScanReport | None) -> dict[tuple[str, str], Finding]:
    if not r:
        return {}
    return {f.key: f for f in r.findings if f.fixable}


def _sev_counts(findings) -> str:
    c = Counter(f.severity for f in findings)
    return " / ".join(str(c.get(s, 0)) for s in SEVERITIES[:4])


def reason_for(f: Finding, s: Summary, bundled: set[str] = frozenset(), copa: str = "") -> str:
    st = vexmod.match(s.vex, f)
    if st:
        return f"VEX {st.status}: {st.impact or st.justification or st.action or ''}".strip()
    if f.ecosystem in BUNDLED and f.location in bundled:
        return f"in bundled artifact `{f.location}` (not built from this source)"
    for u in s.unresolved:
        if u.vuln_id == f.vuln_id and u.name == f.name:
            return u.why
    for fl in s.failures:
        if fl.name == f.name:
            return f"bump failed: {fl.error.splitlines()[0][:160] if fl.error else ''}"
    if f.name == "stdlib":
        return "the Go toolchain used for the build is older than the fix (no newer patch release of that Go line yet?)"
    if f.ecosystem == "os":
        if copa.startswith("failed"):
            return f"Copa {copa}"
        return f"OS package not patched (Copa: {copa or 'not run'})"
    return "not addressed - investigate"


def render_markdown(s: Summary) -> str:
    icon = {"success": "✅", "no-changes": "➖"}.get(s.status, "❌")
    out = [f"## {icon} {s.recipe.name} `{s.tag}` — {s.status}", ""]
    out.append(f"Upstream: {s.recipe.source.url if s.recipe.source else 'n/a'} @ `{s.commit[:12]}` (line `{s.line}`)")
    if s.attempts:
        out.append(f"Attempts: {' → '.join(s.attempts)}")
    out.append("")

    # --- headline table
    out += ["### Fixable vulnerabilities (critical / high / medium / low)", "", "| Artifact | Before | After | Fixed | New |", "|---|---|---|---|---|"]
    rows = [("source (`trivy fs`)", s.fs_before, s.fs_after)] + [(f"image `{i.name}`", i.before, i.after) for i in s.images]
    copa_by_label = {f"image `{i.name}`": i.copa for i in s.images}
    for label, before, after in rows:
        b, a = _fixable_keys(before), _fixable_keys(after)
        if label.startswith("source"):  # Go stdlib is judged on the built image, not go.mod's `go` line
            b = {k: v for k, v in b.items() if v.name != "stdlib"}
            a = {k: v for k, v in a.items() if v.name != "stdlib"}
        fixed = [b[k] for k in b.keys() - a.keys()]
        new = [a[k] for k in a.keys() - b.keys()]
        out.append(f"| {label} | {_sev_counts(b.values()) if before else 'n/a'} | {_sev_counts(a.values()) if after else 'n/a'} | {len(fixed)} | {len(new)} |")
    out.append("")

    # --- applied changes
    if s.changes:
        out += ["### Changes applied", "", "| Ecosystem | File | Package | From | To | Why |", "|---|---|---|---|---|---|"]
        for c in s.changes[:MAX_ROWS]:
            out.append(f"| {c.ecosystem} | `{c.target}` | `{c.name}` | `{c.old}` | `{c.new}` | {c.note[:120]} |")
        if len(s.changes) > MAX_ROWS:
            out.append(f"| … | | | | | {len(s.changes) - MAX_ROWS} more in `bump-plan.json` |")
        out.append("")

    # --- remaining
    remaining: list[tuple[str, Finding]] = []
    bundled: set[str] = set()
    for i in s.images:
        bundled |= bundled_paths(i, s.fs_after)
    seen = set()
    for label, _, after in rows:
        for f in _fixable_keys(after).values():
            if label.startswith("source") and f.name == "stdlib":
                continue
            if (label, f.key) in seen:
                continue
            seen.add((label, f.key))
            remaining.append((label, f))
    if remaining:
        sev_rank = {k: i for i, k in enumerate(SEVERITIES)}
        remaining.sort(key=lambda x: (sev_rank.get(x[1].severity, 9), x[1].name))
        out += ["### Still fixable after patching", "", "| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |", "|---|---|---|---|---|---|---|"]
        for label, f in remaining[:MAX_ROWS]:
            out.append(f"| {f.severity} | {f.vuln_id} | `{f.name}` | `{f.installed}` | `{f.fixed}` | {label} | {reason_for(f, s, bundled, copa_by_label.get(label, ''))[:160]} |")
        if len(remaining) > MAX_ROWS:
            out.append(f"| | | | | | | {len(remaining) - MAX_ROWS} more in `summary.json` |")
        out.append("")

    if s.failures:
        out += ["### Bumps that could not be applied", ""]
        uniq = list({(fl.ecosystem, fl.target, fl.name, fl.wanted, fl.error): fl for fl in s.failures}.values())
        for fl in uniq[:MAX_ROWS]:
            first = (fl.error or "").strip().splitlines()
            out.append(f"- `{fl.name}` → `{fl.wanted}` in `{fl.target}`: {first[-1][:200] if first else ''}")
        out.append("")

    # --- tests
    t = s.tests
    out += ["### Upstream tests", ""]
    if not t:
        out.append("Not run.")
    elif not t.ran:
        out.append(f"Not run: {t.note}")
    else:
        out.append(f"{'✅ passed' if t.passed else '❌ failed'} in {t.seconds / 60:.1f} min — `{t.command[:300]}`")
        if t.note:
            out.append(f"\n> {t.note}")
        if not t.passed and t.failures:
            out += ["", "Failing tests:", "", "```", t.failures[-6000:], "```"]
        if not t.passed and t.tail:
            out += ["", "<details><summary>last lines of the test log</summary>", "", "```", t.tail[-6000:], "```", "</details>"]
    if t and (t.skipped or t.expired):
        out += ["", "Skipped tests (from `skips/" + s.recipe.name + ".yaml`):", "", "| Match | Reason | Owner | Expires |", "|---|---|---|---|"]
        for e in t.skipped:
            out.append(_skip_row(e))
        for e in t.expired:
            out.append(_skip_row(e, expired=True))
    out.append("")

    # --- images
    if s.images:
        out += ["### Images", "", "| Image | Ref | Smoke | Copa |", "|---|---|---|---|"]
        for i in s.images:
            smoke = ", ".join(("✅ " if x["ok"] else "❌ ") + f"`{x['cmd']}`" for x in i.smoke) or "-"
            out.append(f"| {i.name} | `{i.ref}` | {smoke} | {i.copa or '-'} |")
        out.append("")

    notes = s.recipe.notes + s.notes
    if notes:
        out += ["### Notes", ""] + [f"- {n}" for n in notes] + [""]
    return "\n".join(out)


def _skip_row(e: SkipEntry, expired: bool = False) -> str:
    exp = f"**{e.expires} (expired)**" if expired else (str(e.expires) if e.expires else "-")
    return f"| `{e.match}` | {e.reason} | {e.owner} | {exp} |"
