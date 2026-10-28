"""Regex version-pin edits (tool versions in scripts, `ENV REDIS_VERSION=...`), with derived
edits such as download URLs and checksums."""

from __future__ import annotations

import hashlib
import re
import urllib.request
from pathlib import Path

from ..config import render
from ..models import FileEdit, FilesEco, Level, Source, Line
from ..upstream import list_tags
from ..versions import InvalidVersion, level_between, parse_semver
from .base import Change, Ctx, Failure, Result, expand_files


def var_regex(name: str, group: str) -> re.Pattern[str]:
    # NAME=1.2.3 | NAME 1.2.3 | NAME: 1.2.3 | export NAME="1.2.3" | ENV/ARG NAME=1.2.3
    return re.compile(
        rf"(?m)^(?P<pre>[ \t]*(?:export[ \t]+|ENV[ \t]+|ARG[ \t]+)?{re.escape(name)}[ \t]*(?:=|:|[ \t])[ \t]*[\"']?)(?P<{group}>[^\"'\s]+)"
    )


def _pattern(edit_var: str | None, pattern: str | None, group: str) -> re.Pattern[str]:
    if edit_var:
        return var_regex(edit_var, group)
    rx = re.compile(pattern or "", re.M)
    if group not in rx.groupindex:
        raise ValueError(f"pattern {pattern!r} needs a named group `{group}`")
    return rx


def _sub_group(rx: re.Pattern[str], text: str, group: str, value: str) -> tuple[str, int]:
    def repl(m: re.Match[str]) -> str:
        s, e = m.span(group)
        return m.group(0)[: s - m.start()] + value + m.group(0)[e - m.start():]

    return rx.subn(repl, text)


def latest(edit: FileEdit, current: str) -> str | None:
    assert edit.source
    src = Source(repo=edit.source.git, lines=[Line(tagPattern=edit.source.tagPattern)])
    cur = parse_semver(current)
    want = Level.patch if edit.to == "latest-patch" else Level.minor
    best = None
    for tag in list_tags(src.url):
        if not re.search(edit.source.tagPattern, tag):
            continue
        try:
            v = parse_semver(tag)
        except InvalidVersion:
            continue
        if v <= cur or (want == Level.patch and level_between(cur, v) != Level.patch) or (want == Level.minor and v.major != cur.major):
            continue
        if best is None or v > best:
            best = v
    return best.raw if best else None


def _sha256_of(url: str) -> str:
    h = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=300) as resp:
        for chunk in iter(lambda: resp.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def apply(ctx: Ctx, eco: FilesEco) -> Result:
    res = Result()
    for edit in eco.edits:
        for path in expand_files(ctx.src, [edit.file]):
            res.extend(_apply_edit(ctx, edit, path))
    return res


def _apply_edit(ctx: Ctx, edit: FileEdit, path: Path) -> Result:
    res = Result()
    rel = path.relative_to(ctx.src).as_posix()
    label = edit.var or edit.pattern or ""
    text = path.read_text()
    rx = _pattern(edit.var, edit.pattern, "version")
    m = rx.search(text)
    if not m:
        res.failures.append(Failure("files", rel, label, edit.to, "pattern not found"))
        return res
    current = m.group("version")
    try:
        new = latest(edit, current) if edit.to.startswith("latest-") else edit.to
    except InvalidVersion:
        res.failures.append(Failure("files", rel, label, edit.to, f"current value {current!r} is not a version"))
        return res
    if not new:
        return res
    bare = new[1:] if new.startswith("v") else new
    new = f"v{bare}" if current.startswith("v") else bare
    if new == current:
        return res
    text, _ = _sub_group(rx, text, "version", new)
    tctx = {"version": bare, "version_v": f"v{bare}", "old_version": current.lstrip("v")}
    for d in edit.derived:
        drx = _pattern(d.var, d.pattern, "value")
        try:
            value = render(d.value, tctx) if d.value else _sha256_of(render(d.sha256Of or "", tctx))
        except Exception as e:  # network/template errors must not leave a half-edited file
            res.failures.append(Failure("files", rel, d.var or d.pattern or "", new, f"derived edit failed: {e}"))
            return res
        text, n = _sub_group(drx, text, "value", value)
        if n == 0:
            res.failures.append(Failure("files", rel, d.var or d.pattern or "", new, "derived pattern not found"))
            return res
    path.write_text(text)
    res.changes.append(Change("files", rel, label, current, new, f"{edit.to}"))
    return res
