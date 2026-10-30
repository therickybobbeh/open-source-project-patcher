"""Dockerfiles: move `FROM` base images to the newest tag of the same shape (same suffix,
same major.minor for `patch` level) and pin the digest. Go builder images are additionally
raised to the Go version the plan requires (stdlib CVEs / raised `go` directives), and images
below a `minVersions` release line (an end-of-life Node, say) are raised into that line."""

from __future__ import annotations

import re
from pathlib import Path

from .. import registry
from ..models import DockerfileEco, Level
from ..proc import log
from ..versions import InvalidVersion, Version, parse_semver
from .base import Change, Ctx, Failure, Result, expand_files

FROM_RE = re.compile(r"^(?P<lead>\s*FROM\s+)(?P<flags>(?:--\S+\s+)*)(?P<image>\S+)(?P<rest>.*)$", re.I)
ARG_RE = re.compile(r"^\s*ARG\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>\S+)\s*$", re.I)
STAGE_RE = re.compile(r"\bAS\s+(?P<stage>\S+)", re.I)
TAG_RE = re.compile(r"^(?P<prefix>[A-Za-z]*?)(?P<ver>\d+(?:\.\d+)*)(?P<suffix>(?:[-_.][A-Za-z0-9._-]*)?)$")
GO_IMAGES = re.compile(r"(^|/)golang$")


def _shape(tag: str):
    m = TAG_RE.match(tag)
    if not m:
        return None
    try:
        ver = parse_semver(m.group("ver"))
    except InvalidVersion:
        return None
    return m.group("prefix"), ver, m.group("suffix"), m.group("ver").count(".") + 1


def _in_line(v: Version, line: str) -> int:
    """-1, 0 or 1: `v` is below, in or above the release line `line` ("24", "3.24"), compared at the precision both
    give (a floating `3` is in the 3.24 line: it is the newest 3.x)."""
    want = tuple(int(p) for p in line.split("."))
    k = min(len(v.nums), len(want))
    return (v.nums[:k] > want[:k]) - (v.nums[:k] < want[:k])


def below_line(tag: str, line: str | None) -> bool:
    shape = _shape(tag)
    return bool(line and shape and _in_line(shape[1], line) < 0)


def best_tag(image: str, tag: str, level: Level, min_version: Version | None = None, line: str | None = None) -> str | None:
    """Newest tag with the same prefix/suffix/precision; `level` bounds the move. A tag below `line` (from
    `minVersions`) moves to the newest tag in that line instead, whatever the level."""
    shape = _shape(tag)
    if not shape:
        return None
    prefix, cur, suffix, parts = shape
    floor = cur
    if min_version and min_version > cur:
        floor = min_version
    raise_to = line if line and _in_line(floor, line) < 0 else None  # a Go requirement above the line wins
    best: tuple[Version, str] | None = None
    for t in registry.list_tags(image):
        s = _shape(t)
        if not s or s[0] != prefix or s[2] != suffix or s[3] != parts:
            continue
        v = s[1]
        if v < cur:
            continue
        if raise_to:
            allowed = _in_line(v, raise_to) == 0
        elif level == Level.patch:
            allowed = (v.major, v.minor) in ((floor.major, floor.minor), (cur.major, cur.minor))
        else:
            allowed = level != Level.minor or v.major == cur.major
        if not allowed:
            continue
        if best is None or v > best[0]:
            best = (v, t)
    if best and min_version and best[0] < min_version:
        log(f"warning: newest {image} tag {best[1]} is below the required {min_version}")
    if raise_to and not best:
        log(f"warning: {image}: no tag shaped like {tag} in the {raise_to} line (minVersions); left at {tag}")
    return best[1] if best else None


def min_line(eco: DockerfileEco, ref: registry.ImageRef) -> str | None:
    """The `minVersions` release line for this image, if any (`node` matches library/node)."""
    return next((line for name, line in eco.minVersions.items() if re.search(rf"(^|/){re.escape(name)}$", ref.repository)), None)


def _beyond_policy(image: str, tag: str, level: Level) -> str | None:
    """For `patch` level: the newest tag of the next minor(s) within the same major, for the report
    (e.g. gomplate v5.2.0 -> v5.3.1). Major jumps are never hinted: for many images the major is
    the variant (eclipse-temurin 17 vs 26, debian 12 vs 13)."""
    if level != Level.patch:
        return None
    try:
        wider = best_tag(image, tag, Level.minor)
    except registry.RegistryError:
        return None
    return wider if wider and wider != tag else None


def _tag_in_line(image: str) -> bool:
    """`${REGISTRY}/alpine:3.24`: a tag written out, though ARGs build the name."""
    last = image.split("@")[0].rsplit("/", 1)[-1]
    return ":" in last and "$" not in last.split(":", 1)[1]


def _note(old: str, new: str, line: str | None) -> str:
    if new == old:
        return "base image refresh"
    return f"{old} -> {new}" + (f" (minVersions: the {line} line)" if below_line(old, line) else "")


def apply(ctx: Ctx, eco: DockerfileEco) -> Result:
    res = Result()
    ignore = [re.compile(p) for p in eco.ignore]
    for path in expand_files(ctx.src, eco.files):
        res.extend(_apply_file(ctx, eco, path, ignore))
    return res


def _apply_file(ctx: Ctx, eco: DockerfileEco, path: Path, ignore) -> Result:
    res = Result()
    rel = path.relative_to(ctx.src).as_posix()
    lines = path.read_text().splitlines(keepends=True)
    stages: set[str] = set()
    args: dict[str, tuple[int, str]] = {}  # ARG name -> (line index, default)
    go_req = ctx.requires.get("go")
    for i, line in enumerate(lines):
        am = ARG_RE.match(line)
        if am:
            args[am.group("name")] = (i, am.group("value"))
            continue
        m = FROM_RE.match(line)
        if not m:
            continue
        image_str = m.group("image")
        sm = STAGE_RE.search(m.group("rest"))
        if image_str in stages or image_str.lower() == "scratch":
            if sm:
                stages.add(sm.group("stage"))
            continue
        if sm:
            stages.add(sm.group("stage"))
        var = re.search(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?", image_str)
        lookup = image_str
        if var and _tag_in_line(image_str):  # `FROM ${REGISTRY}/alpine:3.17.0`: the ARGs name it, the tag is moved here
            if any(n not in args for n in VAR_RE.findall(image_str)):
                continue
            lookup = VAR_RE.sub(lambda v: args[v.group(1)][1], image_str)
        elif var:
            res.extend(_bump_arg(ctx, eco, rel, lines, args, image_str, var, ignore))
            continue
        ref = registry.parse_ref(lookup)
        if not ref.tag or any(rx.search(ref.original_name) for rx in ignore):
            continue
        min_v = parse_semver(go_req) if go_req and GO_IMAGES.search(ref.repository) else None
        line_floor = min_line(eco, ref)
        try:
            new_tag = best_tag(lookup, ref.tag, eco.level, min_v, line_floor) or ref.tag
            digest = registry.digest(lookup, new_tag) if (eco.pinDigest or ref.digest) else None
        except registry.RegistryError as e:
            res.failures.append(Failure("dockerfile", rel, ref.original_name, ref.tag, str(e)))
            continue
        beyond = _beyond_policy(lookup, new_tag, eco.level)
        if beyond:
            res.failures.append(Failure("dockerfile", rel, ref.original_name, beyond,
                                        f"newer tag {beyond} exists beyond the `{eco.level.value}` level for base images "
                                        f"(set `level: minor` on this dockerfile ecosystem, or bump it in patches/)", hint=True))
        new_ref = ref.with_tag(new_tag, digest)
        if var:  # keep the ARG-built name as written
            new_ref = image_str.split("@")[0].rsplit(":", 1)[0] + new_ref[len(ref.original_name):]
        if new_ref != image_str:
            lines[i] = f"{m.group('lead')}{m.group('flags')}{new_ref}{m.group('rest')}" + ("\n" if line.endswith("\n") else "")
            res.changes.append(Change("dockerfile", rel, ref.original_name, image_str.split("/")[-1], new_ref.split("/")[-1],
                                      _note(ref.tag, new_tag, line_floor)))
    path.write_text("".join(lines))
    return res


VAR_RE = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")


def _bump_arg(ctx: Ctx, eco: DockerfileEco, rel: str, lines: list[str], args, image_str: str, var: re.Match, ignore) -> Result:
    """`ARG GO_VERSION=1.26.8` + `FROM golang:${GO_VERSION}-alpine${ALPINE_VERSION}`: resolve every ARG,
    pick the new tag, then write the changed pieces back into the ARG defaults."""
    res = Result()
    names = VAR_RE.findall(image_str)
    if any(n not in args for n in names):
        return res  # a build-time-only ARG: nothing to bump statically
    if len(names) == 1 and var.group(0) == image_str:
        # `ARG BASE_IMAGE=ubuntu:26.04@sha256:...` + `FROM $BASE_IMAGE`: the ARG holds the whole ref
        name = names[0]
        idx, default = args[name]
        ref = registry.parse_ref(default)
        if not ref.tag or any(rx.search(ref.original_name) for rx in ignore):
            return res
        return _bump_whole_ref_arg(ctx, eco, rel, lines, args, name, idx, default, ref)
    resolved = VAR_RE.sub(lambda m: args[m.group(1)][1], image_str)
    ref = registry.parse_ref(resolved)
    if not ref.tag or ref.digest or any(rx.search(ref.original_name) for rx in ignore):
        return res
    go_req = ctx.requires.get("go")
    min_v = parse_semver(go_req) if go_req and GO_IMAGES.search(ref.repository) else None
    line_floor = min_line(eco, ref)
    try:
        new_tag = best_tag(resolved, ref.tag, eco.level, min_v, line_floor)
    except registry.RegistryError as e:
        res.failures.append(Failure("dockerfile", rel, ref.original_name, ref.tag, str(e)))
        return res
    if not new_tag or new_tag == ref.tag:
        return res
    # template -> regex with one group per ARG; match it against the new ref to read the new values
    pattern, seen = "", set()
    pos = 0
    for m in VAR_RE.finditer(image_str):
        pattern += re.escape(image_str[pos:m.start()])
        n = m.group(1)
        pattern += f"(?P={n})" if n in seen else f"(?P<{n}>[A-Za-z0-9._-]+?)"
        seen.add(n)
        pos = m.end()
    pattern += re.escape(image_str[pos:])
    mm = re.fullmatch(pattern, ref.with_tag(new_tag))
    if not mm:
        return res
    for n in seen:
        idx, default = args[n]
        value = mm.group(n)
        if value == default:
            continue
        lines[idx] = re.sub(rf"({re.escape(n)}=)\S+", lambda m, v=value: m.group(1) + v, lines[idx], count=1)
        args[n] = (idx, value)
        res.changes.append(Change("dockerfile", rel, f"ARG {n}", default, value, f"{ref.original_name}:{_note(ref.tag, new_tag, line_floor)}"))
    return res


def _bump_whole_ref_arg(ctx: Ctx, eco: DockerfileEco, rel: str, lines: list[str], args, name: str, idx: int, default: str,
                        ref: registry.ImageRef) -> Result:
    res = Result()
    go_req = ctx.requires.get("go")
    min_v = parse_semver(go_req) if go_req and GO_IMAGES.search(ref.repository) else None
    line_floor = min_line(eco, ref)
    try:
        new_tag = best_tag(default, ref.tag, eco.level, min_v, line_floor) or ref.tag
        digest = registry.digest(default, new_tag) if (eco.pinDigest or ref.digest) else None
    except registry.RegistryError as e:
        res.failures.append(Failure("dockerfile", rel, ref.original_name, ref.tag or "", str(e)))
        return res
    new_ref = ref.with_tag(new_tag, digest)
    if new_ref == default:
        return res
    lines[idx] = re.sub(rf"({re.escape(name)}=)\S+", lambda m: m.group(1) + new_ref, lines[idx], count=1)
    args[name] = (idx, new_ref)
    res.changes.append(Change("dockerfile", rel, f"ARG {name}", default.split("/")[-1], new_ref.split("/")[-1],
                              _note(ref.tag, new_tag, line_floor)))
    return res
