"""Upstream git operations: resolve the newest tag of a release line, check it out, diff it."""

from __future__ import annotations

import re
from pathlib import Path

from .models import Line, Source
from .proc import output, run
from .versions import InvalidVersion, parse_semver

GIT_ID = ["-c", "user.name=patcher", "-c", "user.email=patcher@localhost", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false"]


def list_tags(url: str) -> dict[str, str]:
    """tag -> commit sha (annotated tags are peeled)."""
    out = output(["git", "ls-remote", "--tags", url])
    tags: dict[str, str] = {}
    for line in out.splitlines():
        sha, _, ref = line.partition("\t")
        if not ref.startswith("refs/tags/"):
            continue
        name = ref[len("refs/tags/"):]
        if name.endswith("^{}"):
            tags[name[:-3]] = sha  # peeled commit wins
        else:
            tags.setdefault(name, sha)
    return tags


def _tag_version(tag: str):
    m = re.search(r"v?\d+(?:\.\d+)*(?:-[0-9A-Za-z.\-]+)?$", tag)
    if not m:
        return None
    try:
        return parse_semver(m.group(0))
    except InvalidVersion:
        return None


def newest_tag(tags: dict[str, str] | list[str], pattern: str, exclude: list[str] = ()) -> str | None:
    rx = re.compile(pattern)
    ex = [re.compile(e) for e in exclude]
    best = None
    for tag in tags:
        if not rx.search(tag) or any(e.search(tag) for e in ex):
            continue
        v = _tag_version(tag)
        if v is None:
            continue
        if best is None or v > best[0]:
            best = (v, tag)
    return best[1] if best else None


def branch_head(url: str, branch: str) -> str:
    out = output(["git", "ls-remote", url, f"refs/heads/{branch}"]).split()
    if not out:
        raise LookupError(f"no branch {branch!r} in {url}")
    return out[0]


def read_remote_file(source: Source, commit: str, path: str) -> str:
    """Read one file at a commit without cloning (GitHub raw endpoint)."""
    import urllib.request

    if not source.url.startswith("https://github.com/"):
        raise NotImplementedError("versionFrom needs a GitHub source")
    slug = source.url.removeprefix("https://github.com/").removesuffix(".git")
    with urllib.request.urlopen(f"https://raw.githubusercontent.com/{slug}/{commit}/{path}", timeout=60) as resp:
        return resp.read().decode()


def version_from_text(text: str, var: str | None, pattern: str | None) -> str:
    from .adapters.files import var_regex

    rx = var_regex(var, "version") if var else re.compile(pattern or "", re.M)
    m = rx.search(text)
    if not m:
        raise LookupError(f"version {var or pattern!r} not found")
    return m.group("version")


def resolve_line(source: Source, line: Line, tags: dict[str, str] | None = None) -> tuple[str, str]:
    """Return (tag, commit) for a release line. For branch lines the "tag" is the version read
    from `versionFrom` at the branch head."""
    if line.branch:
        commit = branch_head(source.url, line.branch)
        vf = line.versionFrom
        assert vf
        return version_from_text(read_remote_file(source, commit, vf.file), vf.var, vf.pattern), commit
    tags = tags if tags is not None else list_tags(source.url)
    tag = line.tag or newest_tag(tags, line.tagPattern or "", source.exclude)
    if not tag or tag not in tags:
        raise LookupError(f"no upstream tag in {source.url} matches {line.tag or line.tagPattern!r}")
    return tag, tags[tag]


def checkout(url: str, tag: str, dest: Path, expected_commit: str | None = None, by_commit: bool = False) -> str:
    """Shallow checkout of `tag` (or of `expected_commit` itself for branch lines) into `dest`;
    verifies the commit when `expected_commit` is given."""
    dest.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-q", str(dest)])
    run(["git", "-C", str(dest), "remote", "add", "origin", url])
    if by_commit:
        assert expected_commit
        run(["git", "-C", str(dest), "fetch", "-q", "--depth", "1", "origin", expected_commit])
        run(["git", "-C", str(dest), "-c", "advice.detachedHead=false", "checkout", "-q", "FETCH_HEAD"])
    else:
        run(["git", "-C", str(dest), "fetch", "-q", "--depth", "1", "origin", f"refs/tags/{tag}:refs/tags/{tag}"])
        run(["git", "-C", str(dest), "-c", "advice.detachedHead=false", "checkout", "-q", tag])
    commit = head(dest)
    if expected_commit and commit != expected_commit:
        raise RuntimeError(f"{url}@{tag} resolved to {commit}, expected {expected_commit} (tag moved?)")
    return commit


def head(src: Path) -> str:
    return output(["git", "-C", str(src), "rev-parse", "HEAD"]).strip()


def apply_patches(src: Path, patches: list[Path], files_dir: Path | None = None) -> None:
    """Apply `patches/<recipe>/*.patch`, then copy `patches/<recipe>/files/` over the checkout
    (extra Dockerfiles, test configs...)."""
    for p in patches:
        run(["git", "-C", str(src), "apply", "--whitespace=nowarn", str(p.resolve())])
    if files_dir and files_dir.is_dir():
        import shutil

        shutil.copytree(files_dir, src, dirs_exist_ok=True)


def changed_files(src: Path, base: str = "HEAD") -> list[str]:
    run(["git", "-C", str(src), "add", "-A", "--intent-to-add"], quiet=True, check=False)
    out = output(["git", "-C", str(src), "diff", "--name-only", base])
    return [l for l in out.splitlines() if l]


def commit_all(src: Path, message: str, retag: str | None = None) -> str:
    """Commit every change and (optionally) move `retag` to the new commit so upstream
    `git describe`-based version stamping still reports the upstream tag."""
    run(["git", "-C", str(src), "add", "-A"], quiet=True)
    run(["git", "-C", str(src), *GIT_ID, "commit", "-q", "--allow-empty", "-m", message], quiet=True)
    if retag:
        # annotated, so both `git describe` and `git describe --tags` find it
        run(["git", "-C", str(src), *GIT_ID, "tag", "-f", "-a", retag, "-m", f"patched {retag}", "HEAD"], quiet=True)
    return head(src)


def diff(src: Path, base_commit: str) -> str:
    return output(["git", "-C", str(src), "diff", "--binary", base_commit, "HEAD"])
