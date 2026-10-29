"""Evidence for the findings we couldn't fix.

* Go reachability (govulncheck): when the vulnerable function isn't called, or the vulnerable package
  isn't imported at all, a draft VEX statement is suggested for a human to review. Never applied
  automatically.
* Malicious packages (osv-scanner): the lockfiles our bumps changed are checked against OSV's
  malicious-package advisories (`MAL-*`); a hit fails the run."""

from __future__ import annotations

import json
from pathlib import Path

from .ecosystems import ECOSYSTEMS
from .proc import CommandError, log, output, which
from .scan import Finding

GOVULNCHECK = "golang.org/x/vuln/cmd/govulncheck@v1.9.0"  # pinned (>= 14 days old when chosen)

LOCKFILES = tuple(f for e in ECOSYSTEMS.values() for f in e.lockfiles)


def _json_stream(text: str):
    dec, i = json.JSONDecoder(), 0
    while True:
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            return
        obj, i = dec.raw_decode(text, i)
        yield obj


def go_reachability(src: Path, dirs: list[str], env: dict[str, str]) -> dict[str, str]:
    """{vulnerability id or alias: called | imported | required} for the modules in `dirs`."""
    levels: dict[str, str] = {}
    rank = {"required": 0, "imported": 1, "called": 2}
    for d in dirs:
        log(f"govulncheck reachability ({GOVULNCHECK.rsplit('@', 1)[1]}) in {d}")
        try:
            text = output(["go", "run", GOVULNCHECK, "-format", "json", "./..."], cwd=src / d,
                          env={**env, "GOFLAGS": "-mod=mod", "GOWORK": "off"}, check=False)
        except (CommandError, OSError) as e:
            log(f"govulncheck failed in {d}: {str(e)[:200]}")
            continue
        aliases: dict[str, list[str]] = {}
        try:
            objects = list(_json_stream(text))
        except json.JSONDecodeError:
            log(f"govulncheck output in {d} was not JSON")
            continue
        for obj in objects:
            if "osv" in obj:
                osv = obj["osv"]
                aliases[osv["id"]] = [osv["id"], *osv.get("aliases", [])]
        for obj in objects:
            f = obj.get("finding")
            if not f:
                continue
            frame = (f.get("trace") or [{}])[0]
            level = "called" if frame.get("function") else "imported" if frame.get("package") else "required"
            for vid in aliases.get(f["osv"], [f["osv"]]):
                if vid not in levels or rank[level] > rank[levels[vid]]:  # keep the strongest evidence
                    levels[vid] = level
    return levels


def vex_suggestions(findings: list[Finding], levels: dict[str, str]) -> list[dict]:
    """Draft VEX statements for Go findings whose vulnerable code govulncheck says isn't reached."""
    out, seen = [], set()
    for f in findings:
        level = levels.get(f.vuln_id)
        if level in (None, "called") or (f.vuln_id, f.name) in seen:
            continue
        seen.add((f.vuln_id, f.name))
        out.append({
            "vulnerability": f.vuln_id,
            "status": "not_affected",
            "justification": "vulnerable_code_not_in_execute_path" if level == "imported" else "vulnerable_code_not_present",
            "impact": (f"govulncheck ({GOVULNCHECK.rsplit('@', 1)[1]}): {f.name} is imported but the vulnerable function is never called"
                       if level == "imported" else
                       f"govulncheck ({GOVULNCHECK.rsplit('@', 1)[1]}): the vulnerable package of {f.name} is not imported"),
            "packages": [f.name],
        })
    return out


def malicious(src: Path, changed: list[str], env: dict[str, str]) -> tuple[list[dict], str]:
    """OSV `MAL-*` advisories for packages in the lockfiles our bumps changed; (hits, note)."""
    lockfiles = [c for c in changed if Path(c).name in LOCKFILES or (Path(c).name.startswith("requirements") and c.endswith(".txt"))]
    if not lockfiles:
        return [], ""
    if not which("osv-scanner"):
        return [], "osv-scanner not installed: malicious-package check skipped"
    args = ["osv-scanner", "scan", "source", "--format", "json"] + [f"--lockfile={f}" for f in lockfiles]
    log(f"malicious-package check (osv-scanner, MAL-* advisories): {', '.join(lockfiles)}")
    try:
        text = output(args, cwd=src, env=env, check=False)
        data = json.loads(text or "{}")
    except (CommandError, OSError, json.JSONDecodeError) as e:
        return [], f"malicious-package check failed to run: {str(e)[:200]}"
    hits = []
    for result in data.get("results") or []:
        path = (result.get("source") or {}).get("path", "")
        for pkg in result.get("packages") or []:
            for v in pkg.get("vulnerabilities") or []:
                if str(v.get("id", "")).startswith("MAL-"):
                    p = pkg.get("package") or {}
                    hits.append({"id": v["id"], "package": p.get("name"), "version": p.get("version"), "lockfile": path})
    log(f"malicious-package check: {len(hits)} hit(s)")
    return hits, ""
