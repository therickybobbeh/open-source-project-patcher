"""The release gate: whether an image may be released with what it still contains.

The rules are Rego in policy/ (package `patcher.gate`), evaluated with conftest (OPA) on each image's final scan. Their
parameters are the recipe's `gate.failOn`, merged over _global.yaml's. Patch PRs report the verdict; with
`gate.enforce`, a release the gate denies stops before it is signed, and the patch PR opens as a draft. A gate that
can't be evaluated (no conftest, a broken policy) is an error, never a pass. docs/gate.md has the input contract."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import vex as vexmod
from .models import Gate, VexFile
from .proc import log
from .scan import ScanReport

NAMESPACE = "patcher.gate"


class GateError(RuntimeError):
    """The gate couldn't be evaluated: the stage fails rather than pass unchecked."""


class GateDenied(RuntimeError):
    """`gate.enforce` is on and the gate denied an image: the release stops before it is signed."""


@dataclass
class Verdict:
    deny: list[str] = field(default_factory=list)
    warn: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.deny

    def to_json(self) -> dict:
        return {"passed": self.passed, "deny": self.deny, "warn": self.warn}


def gate_input(stage: str, recipe: str, line: str, image: str, ref: str, report: ScanReport, gate: Gate,
               vex: VexFile) -> dict:
    """What the policy sees: one image's findings, each with its fix and the VEX status that explains it (or null)."""
    findings = []
    for f in report.findings:
        st = vexmod.match(vex, f)
        findings.append({"id": f.vuln_id, "severity": f.severity, "package": f.name, "installed": f.installed,
                         "fixed": f.fixed or "", "fixable": f.fixable, "ecosystem": f.ecosystem, "location": f.location,
                         "vex": st.status if st else None})
    return {"stage": stage, "recipe": recipe, "line": line, "image": image, "ref": ref,
            "params": gate.failOn.model_dump(), "findings": findings}


def evaluate(policy: Path, doc: dict) -> Verdict:
    """Run the policy (every .rego file in `policy`) on one input document."""
    exe = shutil.which("conftest")
    if not exe:
        raise GateError("conftest is not installed (the patcher image has it), so the release gate can't be evaluated")
    if not policy.is_dir():
        raise GateError(f"no policy directory {policy}, so the release gate can't be evaluated")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "input.json"
        path.write_text(json.dumps(doc))
        r = subprocess.run([exe, "test", "--no-color", "--output", "json", "--namespace", NAMESPACE, "--policy", str(policy),
                            str(path)], capture_output=True, text=True, timeout=300)
    try:
        result = next(iter(json.loads(r.stdout)), {})
    except (json.JSONDecodeError, TypeError):
        raise GateError(f"conftest failed (exit {r.returncode}): {(r.stderr or r.stdout)[-800:]}") from None
    if result.get("exceptions"):
        raise GateError(f"the gate policy raised: {result['exceptions']}")
    return Verdict(deny=sorted(m["msg"] for m in result.get("failures") or []),
                   warn=sorted(m["msg"] for m in result.get("warnings") or []))


def check(repo_root: Path, stage: str, recipe, line: str, images: list[tuple[str, str, ScanReport]], vex: VexFile) -> dict[str, Verdict]:
    """The verdict for each (image key, ref, final scan). Logged; the caller reports or enforces it."""
    verdicts = {}
    for key, ref, report in images:
        try:
            v = evaluate(repo_root / "policy", gate_input(stage, recipe.name, line, key, ref, report, recipe.gate, vex))
        except GateError as e:
            if recipe.gate.enforce:
                raise
            log(f"warning: release gate not evaluated ({e}); it only reports (gate.enforce: false), so this run goes on")
            return {}
        verdicts[key] = v
        log(f"gate {recipe.name} {line} {key}: " + ("passed" if v.passed else f"denied ({len(v.deny)})")
            + (f", {len(v.warn)} warning(s)" if v.warn else ""))
    return verdicts


def enforce(recipe, line: str, verdicts: dict[str, Verdict]) -> None:
    """With `gate.enforce`, raise if the gate denied any image (nothing is then signed or recorded)."""
    denied = {k: v for k, v in verdicts.items() if not v.passed}
    if recipe.gate.enforce and denied:
        reasons = "; ".join(f"{k}: {m}" for k, v in denied.items() for m in v.deny[:5])
        raise GateDenied(f"{recipe.name} {line}: the release gate denied {', '.join(denied)} ({reasons}). Nothing is "
                         "signed, promoted or recorded. Fix it, record a VEX decision, or change gate.failOn (docs/gate.md)")


def render_markdown(verdicts: dict[str, Verdict], enforced: bool) -> list[str]:
    """The report's section on the gate."""
    if not verdicts:
        return []
    mode = "enforced: a denied release stops before it is signed" if enforced else "reported only (`gate.enforce: false`)"
    out = [f"### Release gate ({mode})", ""]
    for key, v in verdicts.items():
        out.append(f"- image `{key}`: " + ("✅ passes" if v.passed else f"⛔ **denied** ({len(v.deny)})"))
        out += [f"  - {m}" for m in v.deny[:20]] + ([f"  - … {len(v.deny) - 20} more"] if len(v.deny) > 20 else [])
        out += [f"  - ⚠️ {m}" for m in v.warn[:10]]
    return out + [""]
