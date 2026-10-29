"""Trivy wrapper: run scans and parse the JSON into findings/packages."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from .ecosystems import ARTIFACT_TYPES, ECOSYSTEMS
from .proc import CommandError, log, run

# Trivy `Type` -> our ecosystem key. Anything not listed is treated as an OS package type.
# Trivy result type -> ecosystem (source manifests per ecosystems.py; built artifacts keep their own type)
LANG_TYPES = {t: e.key for e in ECOSYSTEMS.values() for t in e.trivy} | {t: t for t in ARTIFACT_TYPES}


@dataclass
class Package:
    target: str
    ecosystem: str
    name: str
    version: str
    id: str
    relationship: str | None = None
    purl: str | None = None
    file_path: str | None = None  # jars: Trivy groups them under one "Java" result

    @property
    def location(self) -> str:
        return self.file_path or self.target


@dataclass
class Finding:
    target: str
    ecosystem: str  # our key (gomod, maven, ...) or `os`
    trivy_type: str
    name: str
    installed: str
    fixed: str | None
    vuln_id: str
    severity: str
    status: str | None
    pkg_id: str | None = None
    pkg_path: str | None = None
    relationship: str | None = None
    purl: str | None = None
    title: str | None = None

    @property
    def fixable(self) -> bool:
        return bool(self.fixed) and (self.status in (None, "fixed"))

    @property
    def location(self) -> str:
        """Where the package lives: the binary/jar inside an image, or the manifest in a source tree."""
        return self.pkg_path or self.target

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.vuln_id, self.name, self.location)


@dataclass
class ScanReport:
    artifact: str
    findings: list[Finding] = field(default_factory=list)
    packages: list[Package] = field(default_factory=list)
    os: str | None = None
    degraded: str = ""  # why this scan saw less than usual (shown in the report)

    def fixable(self) -> list[Finding]:
        return [f for f in self.findings if f.fixable]

    def by_ecosystem(self, ecosystems: Iterable[str]) -> list[Finding]:
        wanted = set(ecosystems)
        return [f for f in self.findings if f.ecosystem in wanted]

    def to_json(self) -> dict:
        return {"artifact": self.artifact, "os": self.os, "findings": [asdict(f) for f in self.findings]}


def parse_report(data: dict) -> ScanReport:
    report = ScanReport(artifact=data.get("ArtifactName", ""))
    md = data.get("Metadata") or {}
    if md.get("OS"):
        report.os = f"{md['OS'].get('Family', '')} {md['OS'].get('Name', '')}".strip()
    for res in data.get("Results") or []:
        target = res.get("Target", "")
        ttype = res.get("Type", "")
        eco = LANG_TYPES.get(ttype, "os" if res.get("Class") == "os-pkgs" else ttype)
        rel_by_id: dict[str, str] = {}
        for p in res.get("Packages") or []:
            pid = p.get("ID") or f"{p.get('Name')}@{p.get('Version')}"
            rel = p.get("Relationship")
            if rel:
                rel_by_id[pid] = rel
            report.packages.append(
                Package(
                    target=target,
                    ecosystem=eco,
                    name=p.get("Name", ""),
                    version=p.get("Version", ""),
                    id=pid,
                    relationship=rel,
                    purl=(p.get("Identifier") or {}).get("PURL"),
                    file_path=p.get("FilePath"),
                )
            )
        for v in res.get("Vulnerabilities") or []:
            pid = v.get("PkgID")
            report.findings.append(
                Finding(
                    target=target,
                    ecosystem=eco,
                    trivy_type=ttype,
                    name=v.get("PkgName", ""),
                    installed=v.get("InstalledVersion", ""),
                    fixed=v.get("FixedVersion") or None,
                    vuln_id=v.get("VulnerabilityID", ""),
                    severity=v.get("Severity", "UNKNOWN"),
                    status=v.get("Status"),
                    pkg_id=pid,
                    pkg_path=v.get("PkgPath"),
                    relationship=rel_by_id.get(pid or ""),
                    purl=(v.get("PkgIdentifier") or {}).get("PURL"),
                    title=v.get("Title"),
                )
            )
    return report


def load_report(path: Path) -> ScanReport:
    return parse_report(json.loads(path.read_text()))


_db_ready = False


def ensure_db(attempts: int = 3) -> None:
    """Download Trivy's vulnerability and Java DBs once per process, retrying flaky registry pulls. Later
    scans skip DB updates, so every before/after comparison in a run uses the same advisories."""
    global _db_ready
    if _db_ready:
        return
    for what in ("--download-db-only", "--download-java-db-only"):
        for i in range(attempts):
            try:
                run(["trivy", "image", what, "--quiet", "--timeout", "15m"])
                break
            except CommandError as e:
                if i == attempts - 1:
                    raise
                wait = 30 * (i + 1)
                log(f"trivy {what} failed ({e.tail.strip().splitlines()[-1][:160] if e.tail.strip() else e}); retrying in {wait}s")
                time.sleep(wait)
    _db_ready = True


def _common(severities: list[str], extra: list[str] | None = None) -> list[str]:
    ensure_db()
    args = ["--scanners", "vuln", "--format", "json", "--list-all-pkgs", "--quiet", "--skip-db-update", "--skip-java-db-update"]
    if severities:
        args += ["--severity", ",".join(severities)]
    return args + (extra or [])


def scan_fs(path: Path, out: Path, *, severities: list[str], skip_dirs: list[str] = (), skip_files: list[str] = (), vex: Path | None = None,
            offline: bool = False) -> ScanReport:
    args = ["trivy", "fs", *_common(severities), "--output", str(out)]
    if offline:
        args.append("--offline-scan")
    for d in skip_dirs:
        args += ["--skip-dirs", d]
    for f in skip_files:
        args += ["--skip-files", f]
    if vex:
        args += ["--vex", str(vex)]
    try:
        run([*args, str(path)])
    except CommandError as e:
        if offline or "429" not in e.tail:
            raise
        # Maven Central rate-limits by IP (shared CI runners hit it): wait once, then scan offline
        log("trivy fs: Maven Central answered 429 (rate limited); retrying in 60s")
        time.sleep(60)
        try:
            run([*args, str(path)])
        except CommandError as e2:
            if "429" not in e2.tail:
                raise
            log("trivy fs: still rate limited; scanning with --offline-scan")
            run([*args, "--offline-scan", str(path)])
            report = load_report(out)
            report.degraded = ("Maven Central rate-limited the source scan (HTTP 429), so it ran offline: POMs not in the local "
                               "~/.m2 weren't resolved and transitive Maven dependencies may be missing. Consider `scan.offline` "
                               "with a `prepare` step that fills ~/.m2")
            return report
    return load_report(out)


def scan_image(ref: str, out: Path, *, severities: list[str], platform: str | None = None, pkg_types: str | None = None,
               ignore_unfixed: bool = False, vex: Path | None = None, src: str | None = None) -> ScanReport:
    args = ["trivy", "image", *_common(severities), "--output", str(out)]
    if platform:
        args += ["--platform", platform]
    if pkg_types:
        args += ["--pkg-types", pkg_types]
    if ignore_unfixed:
        args += ["--ignore-unfixed"]
    if vex:
        args += ["--vex", str(vex)]
    if src:
        args += ["--image-src", src]
    run([*args, ref])
    return load_report(out)
