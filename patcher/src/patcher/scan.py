"""Trivy wrapper: run scans and parse the JSON into findings/packages."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from .proc import run

# Trivy `Type` -> our ecosystem key. Anything not listed is treated as an OS package type.
LANG_TYPES = {
    "gomod": "gomod",
    "gobinary": "gobinary",
    "cargo": "cargo",
    "rustbinary": "rustbinary",
    "pom": "maven",
    "jar": "jar",
    "gradle": "gradle",
    "npm": "npm",
    "pnpm": "pnpm",
    "yarn": "yarn",
    "node-pkg": "node-pkg",
    "pip": "pip",
    "python-pkg": "python-pkg",
    "conan": "conan",
}


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


def _common(severities: list[str], extra: list[str] | None = None) -> list[str]:
    args = ["--scanners", "vuln", "--format", "json", "--list-all-pkgs", "--quiet"]
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
    run([*args, str(path)])
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
