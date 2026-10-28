"""Maven: bump explicit declarations/properties with versions-maven-plugin, then pin the rest via
<dependencyManagement> in the reactor root that contains the finding (dependency management beats
mediation for transitives)."""

from __future__ import annotations

import posixpath
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from ..models import MavenEco
from ..proc import CommandError, run
from .base import Change, Ctx, Failure, Result, expand_files

VERSIONS_PLUGIN = "org.codehaus.mojo:versions-maven-plugin:2.23.0"
NS = {"m": "http://maven.apache.org/POM/4.0.0"}


def _root_for(target: str, roots: list[str]) -> str | None:
    """Deepest reactor root (dir of a `poms` entry) that contains the finding's pom.xml."""
    tdir = posixpath.dirname(target)
    for r in sorted(roots, key=lambda r: len(posixpath.dirname(r)), reverse=True):
        rdir = posixpath.dirname(r)
        if rdir == "" or tdir == rdir or tdir.startswith(rdir + "/"):
            return r
    return None


def apply(ctx: Ctx, eco: MavenEco) -> Result:
    res = Result()
    bumps = ctx.plan.for_ecosystem("maven")
    if not bumps:
        return res
    roots = [p.relative_to(ctx.src).as_posix() for p in expand_files(ctx.src, eco.poms)]
    per_root: dict[str, dict[str, tuple[str, list[str], str]]] = {}  # root pom -> g:a -> (version, reasons, installed)
    for b in bumps:
        root = _root_for(b.target, roots)
        if root is None:
            res.failures.append(Failure("maven", b.target, b.name, b.to, f"{b.target} is not under any of maven.poms {eco.poms}"))
            continue
        wanted = per_root.setdefault(root, {})
        cur = wanted.get(b.name)
        if cur is None or _newer(b.to, cur[0]):
            wanted[b.name] = (b.to, sorted(set(b.reasons) | set(cur[1] if cur else [])), b.installed)
    for root, wanted in per_root.items():
        pom = ctx.src / root
        for ga, (to, reasons, installed) in wanted.items():
            # 1) explicit declarations (and the properties they use) anywhere in this reactor
            try:
                run(["mvn", "-B", "-q", "-ntp", f"{VERSIONS_PLUGIN}:use-dep-version", f"-Dincludes={ga}", f"-DdepVersion={to}",
                     "-DforceVersion=true", "-DprocessProperties=true", "-DprocessDependencyManagement=true",
                     "-DprocessParent=false", "-DgenerateBackupPoms=false", "-f", str(pom)],
                    env=ctx.env, log_file=ctx.log)
            except CommandError as e:
                res.failures.append(Failure("maven", root, ga, to, f"versions:use-dep-version failed: {e.tail[-1200:]}"))
                continue
            # 2) transitive (or undeclared) deps: pin in the reactor root's <dependencyManagement>
            pin_dependency_management(pom, ga, to, reasons)
            res.changes.append(Change("maven", root, ga, installed, to, ", ".join(reasons)))
    return res


def _newer(a: str, b: str) -> bool:
    from ..versions import parse_maven

    return parse_maven(a) > parse_maven(b)


def _top_level_spans(text: str, tag: str) -> list[tuple[int, int]]:
    """Spans of <tag>...</tag> that are not inside <profiles> or <build> (text-level, keeps formatting)."""
    excluded = [(m.start(), m.end()) for m in re.finditer(r"<(profiles|build)>.*?</\1>", text, re.S)]
    spans = []
    for m in re.finditer(rf"<{tag}>(.*?)</{tag}>", text, re.S):
        if not any(s <= m.start() < e for s, e in excluded):
            spans.append((m.start(), m.end()))
    return spans


def _indent_of_line_at(text: str, pos: int) -> str:
    line_start = text.rfind("\n", 0, pos) + 1
    return re.match(r"[ \t]*", text[line_start:]).group(0)


def _block(ind: str, unit: str, group: str, artifact: str, version: str, note: str) -> str:
    return (f"{ind}<!-- patcher: {note} -->\n{ind}<dependency>\n{ind}{unit}<groupId>{group}</groupId>\n"
            f"{ind}{unit}<artifactId>{artifact}</artifactId>\n{ind}{unit}<version>{version}</version>\n{ind}</dependency>\n")


def pin_dependency_management(pom: Path, ga: str, version: str, reasons: list[str]) -> None:
    group, artifact = ga.split(":", 1)
    text = pom.read_text()
    root = ET.fromstring(text.encode())
    ns = NS if root.tag.startswith("{") else {}
    p = "m:" if ns else ""
    dm = root.find(f"{p}dependencyManagement/{p}dependencies", ns)
    if dm is not None:
        for dep in dm.findall(f"{p}dependency", ns):
            if dep.findtext(f"{p}groupId", "", ns) == group and dep.findtext(f"{p}artifactId", "", ns) == artifact:
                return  # already managed; use-dep-version updated it (or its property)
    note = ", ".join(reasons)[:200]
    # indentation unit of this file: the indent of a direct child of <project>
    m = re.search(r"^([ \t]+)<modelVersion>", text, re.M)
    unit = m.group(1) if m else "    "
    spans = _top_level_spans(text, "dependencyManagement")
    if spans:
        s, e = spans[0]
        dm_ind = _indent_of_line_at(text, s)
        m = re.search(r"<dependencies>[ \t]*\n", text[s:e])
        if m:
            pos = s + m.end()
            child = re.match(r"[ \t]*", text[pos:]).group(0) or dm_ind + unit * 2
            text = text[:pos] + _block(child, unit, group, artifact, version, note) + text[pos:]
        else:
            pos = s + len("<dependencyManagement>")
            deps_ind = dm_ind + unit
            text = (text[:pos] + f"\n{deps_ind}<dependencies>\n" + _block(deps_ind + unit, unit, group, artifact, version, note)
                    + f"{deps_ind}</dependencies>" + text[pos:])
    else:
        deps = _top_level_spans(text, "dependencies")
        pos = deps[0][0] if deps else text.rindex("</project>")
        line_start = text.rfind("\n", 0, pos) + 1
        new = (f"{unit}<dependencyManagement>\n{unit * 2}<dependencies>\n"
               + _block(unit * 3, unit, group, artifact, version, note)
               + f"{unit * 2}</dependencies>\n{unit}</dependencyManagement>\n\n")
        text = text[:line_start] + new + text[line_start:]
    pom.write_text(text)
