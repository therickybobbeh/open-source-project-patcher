"""VEX: apply our `vex/<project>.yaml` decisions to findings and emit OpenVEX for consumers."""

from __future__ import annotations

import datetime as dt
import fnmatch
import hashlib
import json
from pathlib import Path

from .models import VexFile, VexStatement
from .scan import Finding

CONTEXT = "https://openvex.dev/ns/v0.2.0"


def match(vex: VexFile, f: Finding, today: dt.date | None = None) -> VexStatement | None:
    today = today or dt.date.today()
    for s in vex.statements:
        if s.vulnerability != f.vuln_id:
            continue
        if s.expires and s.expires < today:
            continue
        if s.packages and not any(fnmatch.fnmatchcase(f.name, p) or (f.purl and fnmatch.fnmatchcase(f.purl, p)) for p in s.packages):
            continue
        return s
    return None


def _statement(s: VexStatement, product_id: str, subcomponents: list[str]) -> dict:
    st: dict = {
        "vulnerability": {"name": s.vulnerability},
        "products": [{"@id": product_id, **({"subcomponents": [{"@id": c} for c in subcomponents]} if subcomponents else {})}],
        "status": s.status,
    }
    if s.justification:
        st["justification"] = s.justification
    if s.impact:
        st["impact_statement"] = s.impact
    if s.action:
        st["action_statement"] = s.action
    return st


def openvex(vex: VexFile, product_id: str, findings: list[Finding], extra_docs: list[Path] = (), author: str = "support-images/patcher") -> dict:
    """OpenVEX document for one image. `product_id` is the image PURL
    (`pkg:oci/<name>@<digest>?repository_url=...`) or a tag ref when no digest exists yet."""
    statements = []
    for s in vex.statements:
        comps = sorted({f.purl for f in findings if f.vuln_id == s.vulnerability and f.purl and match(vex, f) is s})
        statements.append(_statement(s, product_id, comps))
    for doc in extra_docs:  # e.g. Copa's OpenVEX for the OS packages it patched
        try:
            statements += json.loads(doc.read_text()).get("statements", [])
        except (OSError, json.JSONDecodeError):
            continue
    body = json.dumps(statements, sort_keys=True).encode()
    return {
        "@context": CONTEXT,
        "@id": f"https://openvex.dev/docs/patcher/{hashlib.sha256(body).hexdigest()[:16]}",
        "author": author,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "version": 1,
        "statements": statements,
    }


def oci_purl(repo: str, digest: str) -> str:
    """pkg:oci/<name>@<digest>?repository_url=<registry>/<path> (OpenVEX/Trivy convention)."""
    name = repo.rsplit("/", 1)[-1]
    from urllib.parse import quote

    return f"pkg:oci/{name}@{quote(digest, safe='')}?repository_url={quote(repo, safe='')}"
