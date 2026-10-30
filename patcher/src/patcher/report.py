"""Before/after comparison and the Markdown report that becomes the PR body."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field

from .adapters.base import Change, Failure
from .models import RELEASABLE_STATUSES, Recipe, SkipEntry, VexFile
from .planner import Unresolved
from .scan import Finding, ScanReport
from .tests_runner import TestOutcome
from . import vex as vexmod

SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
MAX_ROWS = 60
BUNDLED = {"gobinary", "rustbinary", "jar", "node-pkg", "python-pkg"}
# packaging tools that come with a language base image, not with the project's dependencies
BASE_TOOLING = {"python-pkg": {"pip", "setuptools", "wheel"}}
GLOBAL_NODE_PREFIX = "usr/local/lib/node_modules/"


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
        own = [o.strip("/") for o in img.own_binaries]  # paths or directory prefixes
        return {t for t in paths if not any(t.strip("/") == o or t.strip("/").startswith(o + "/") for o in own)}
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
    malicious: list[dict] = field(default_factory=list)
    vex_suggestions: list[dict] = field(default_factory=list)
    components: list[dict] = field(default_factory=list)
    component_runs: list = field(default_factory=list)  # Component objects (their generated/ is copied into ours)
    jars: list = field(default_factory=list)  # jars.Swap: bundled jars swapped in, per image (written to jars.json)
    jar_unresolved: list[Unresolved] = field(default_factory=list)  # findings in bundled jars that weren't swapped, and why
    src: str = ""  # the kept attempt's checkout (components build from it)
    image_tags: dict[str, str] = field(default_factory=dict)  # image-only: each image's upstream tag, which the release publishes


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
    comp = _component_reason(f, s) or _jar_reason(f, s)
    if comp:
        return comp
    if f.name in BASE_TOOLING.get(f.ecosystem, set()) or f.location.startswith(GLOBAL_NODE_PREFIX):
        return f"base-image tooling (`{f.name}` ships with the base image): newer base, or Copa `copa: {{libraries: true}}`"
    if f.ecosystem in BUNDLED and f.location in bundled:
        return f"in bundled artifact `{f.location}` (not built from this source)"
    for u in s.unresolved:
        if u.vuln_id == f.vuln_id and u.name == f.name:
            return u.why
    if f.ecosystem in BUNDLED:  # an image finding we did bump: the build didn't pick the new version up
        for c in s.changes:
            if c.name == f.name and c.old.lstrip("v") == f.installed.lstrip("v"):
                return (f"bumped to {c.new} in `{c.target}`, but the image still has {f.installed}: the build didn't use "
                        "the new version (check how the build resolves it)")
    failed = [fl for fl in s.failures if fl.name == f.name and not fl.hint]
    for fl in sorted(failed, key=lambda fl: fl.target != f.location):  # the failure for this file first
        return f"bump failed: {fl.error.splitlines()[0][:160] if fl.error else ''}"
    if f.name == "stdlib":
        return "the Go toolchain used for the build is older than the fix (no newer patch release of that Go line yet?)"
    if f.ecosystem == "os":
        if copa.startswith("failed"):
            return f"Copa {copa}"
        return f"OS package not patched (Copa: {copa or 'not run'})"
    return "not addressed - investigate"


def _component_reason(f: Finding, s: Summary) -> str | None:
    """Findings in a bundled binary that a component replaces: why the rebuilt one still has them."""
    loc = f.location.strip("/")
    for row in s.components:
        if row["path"].strip("/") != loc:
            continue
        if row["status"] not in RELEASABLE_STATUSES:
            return f"component `{row['recipe']}` not swapped in ({row['status']}): the original binary is still shipped"
        for c in s.component_runs:
            if c.ref.recipe == row["recipe"] and c.out and (c.out / "generated" / "bump-plan.json").exists():
                doc = json.loads((c.out / "generated" / "bump-plan.json").read_text())
                for u in doc.get("unresolved", []):
                    if u.get("vuln_id") == f.vuln_id and u.get("name") == f.name:
                        return f"component `{row['recipe']}` (rebuilt from source): {u.get('why')}"
        return f"component `{row['recipe']}` (rebuilt from source): not fixed there, see `components/{row['recipe']}/report.md`"
    return None


def _jar_reason(f: Finding, s: Summary) -> str | None:
    """Findings in a `bundledJars` jar: why it wasn't swapped. A swapped jar keeps its path, so a finding still
    reported there after the swap gets its own reason."""
    loc = f.location.strip("/")
    for u in s.jar_unresolved:
        if u.vuln_id == f.vuln_id and u.name == f.name and u.target == loc:
            return f"bundled jar: {u.why}"
    for sw in s.jars:
        if sw.path == loc and sw.name == f.name:
            return (f"bundled jar swapped for {sw.new}, but the scan still reports {f.installed}: check how the scanner "
                    "identifies this jar")
    return None


def render_markdown(s: Summary) -> str:
    icon = {"success": "✅", "no-changes": "➖", "tests-preexisting": "⚠️"}.get(s.status, "❌")
    out = [f"## {icon} {s.recipe.name} `{s.tag}` — {s.status}", ""]
    out.append(f"Upstream: {s.recipe.source.url if s.recipe.source else 'n/a'} @ `{s.commit[:12]}` (line `{s.line}`)")
    if not s.recipe.publish:
        out += ["", "> **Not published** (`publish: false` in the recipe): merging records this patch set, but the release "
                    "workflow pushes no image for this recipe."]
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

    if s.malicious:
        out += ["### ⛔ Malicious-package advisories for bumped versions", "",
                "The run stopped before tests and build. Hold or override these versions:", ""]
        out += [f"- `{m['package']}` {m['version']} in `{m['lockfile']}`: {m['id']}" for m in s.malicious] + [""]

    # --- applied changes
    if s.changes:
        out += ["### Changes applied", "", "| Ecosystem | File | Package | From | To | Why |", "|---|---|---|---|---|---|"]
        for c in s.changes[:MAX_ROWS]:
            out.append(f"| {c.ecosystem} | `{c.target}` | `{c.name}` | `{c.old}` | `{c.new}` | {c.note[:120]} |")
        if len(s.changes) > MAX_ROWS:
            out.append(f"| … | | | | | {len(s.changes) - MAX_ROWS} more in `bump-plan.json` |")
        out.append("")

    if s.jars:
        out += ["### Bundled jars swapped", "",
                "Replaced with the fixed release from Maven Central, pinned by sha256 (`jars.json`; the release re-applies exactly "
                "these). Each jar keeps its old file name, with the new release as its content.", "",
                "| Image | Jar | Coordinates | From → To | Fixes | sha256 |", "|---|---|---|---|---|---|"]
        swapped: dict[tuple, list[str]] = {}
        for sw in s.jars:  # the same swap in several images of the line is one row
            swapped.setdefault((sw.path, sw.name + (f" ({sw.classifier})" if sw.classifier else ""), sw.old, sw.new,
                                ", ".join(sw.vuln_ids), sw.sha256), []).append(sw.image)
        out += [f"| {', '.join(images)} | `{path}` | `{name}` | `{old}` → `{new}` | {vulns} | `{sha}` |"
                for (path, name, old, new, vulns, sha), images in swapped.items()]
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
            where = f"{label}: `{f.location}`" if label.startswith("source") and f.location else label
            out.append(f"| {f.severity} | {f.vuln_id} | `{f.name}` | `{f.installed}` | `{f.fixed}` | {where} | {reason_for(f, s, bundled, copa_by_label.get(label, ''))[:160]} |")
        if len(remaining) > MAX_ROWS:
            out.append(f"| | | | | | | {len(remaining) - MAX_ROWS} more in `summary.json` |")
        out.append("")

    for title, rows in (("Bumps that could not be applied", [fl for fl in s.failures if not fl.hint]),
                        ("Newer releases beyond the policy (not applied)", [fl for fl in s.failures if fl.hint])):
        if not rows:
            continue
        out += [f"### {title}", ""]
        uniq = list({(fl.ecosystem, fl.target, fl.name, fl.wanted, fl.error): fl for fl in rows}.values())
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
        if t.preexisting:
            out += ["", f"⚠️ All {len(t.preexisting)} failing test(s) **also fail on the unpatched source**, so they are "
                    "upstream's, not caused by these bumps:", "", "```", "\n".join(t.preexisting[:50]), "```"]
        elif not t.passed and t.failures:
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

    if s.vex_suggestions:
        out += ["### VEX suggestions (govulncheck reachability)", "",
                f"Draft statements in `vex-suggestions.yaml`; review, then copy what you accept into `vex/{s.recipe.name}.yaml`.", "",
                "| Vulnerability | Package | Suggested | Evidence |", "|---|---|---|---|"]
        out += [f"| {v['vulnerability']} | `{v['packages'][0]}` | {v['justification']} | {v['impact']} |" for v in s.vex_suggestions[:MAX_ROWS]]
        out.append("")

    if s.components:
        out += ["### Bundled components (rebuilt from source and swapped in)", "",
                "| Image | Component | Path | Version | Status | Bumps | Tests | Notes |", "|---|---|---|---|---|---|---|---|"]
        out += [f"| {c.get('image', '')} | {c['recipe']} | `{c['path']}` | {c['version'] or '-'} | {c['status']} | {c['changes']} | "
                f"{c['tests'] or '-'} | {c['note']} |" for c in s.components]
        out.append("")

    notes = s.recipe.notes + s.notes
    if notes:
        out += ["### Notes", ""] + [f"- {n}" for n in notes] + [""]
    return "\n".join(out)


def _skip_row(e: SkipEntry, expired: bool = False) -> str:
    exp = f"**{e.expires} (expired)**" if expired else (str(e.expires) if e.expires else "-")
    return f"| `{e.match}` | {e.reason} | {e.owner} | {exp} |"
