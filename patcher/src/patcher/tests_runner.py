"""Run the upstream test suite with skip-file entries translated to the framework's own filters."""

from __future__ import annotations

import datetime as dt
import glob
import re
import shlex
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from .config import render
from .models import SkipEntry, SkipFile, Tests
from .proc import CommandError, log, run


@dataclass
class SkipRender:
    args: str = ""  # framework-specific CLI args
    regex: str = ""  # joined regex (go/nextest/generic)
    file: str = ""  # path to a generated skip/excludes file, if any
    env: dict[str, str] = field(default_factory=dict)
    unsupported: str = ""  # why this framework can't honour skips


FAILURE_PATTERNS = {
    "go": r"^\s*--- FAIL: |^FAIL\s|^panic: ",
    "nextest": r"^\s*FAIL \[|^\s*(TIMEOUT|SIGSEGV|SIGABRT) \[",
    "surefire": r"\[ERROR\] (Tests run:.*(Failures: [1-9]|Errors: [1-9])|  \S+[.#:]\S+)|^\[ERROR\] Failed tests|BUILD FAILURE",
    "redis": r"^\[err\]|^\[exception\]",
    "jest": r"^\s*(✕|●) ",
    "bats": r"^not ok ",
}


def failure_summary(framework: str, text: str, limit: int = 40) -> str:
    """The lines that say *what* failed (Go `--- FAIL`, bats `not ok`, ...), not just the log tail."""
    rx = re.compile(FAILURE_PATTERNS.get(framework, r"(?i)\b(fail|error)"), re.M)
    hits = [l.rstrip() for l in text.splitlines() if rx.search(l)]
    return "\n".join(dict.fromkeys(hits[:limit]))


@dataclass
class TestOutcome:
    ran: bool
    passed: bool
    seconds: float = 0.0
    command: str = ""
    skipped: list[SkipEntry] = field(default_factory=list)
    expired: list[SkipEntry] = field(default_factory=list)
    junit: list[str] = field(default_factory=list)
    tail: str = ""
    failures: str = ""
    note: str = ""


def check_expiry(skips: SkipFile, grace_days: int, today: dt.date | None = None) -> tuple[list[SkipEntry], list[SkipEntry]]:
    """Return (expired-warn, expired-fail) entries."""
    today = today or dt.date.today()
    warn, fail = [], []
    for e in skips.skips + skips.quarantine:
        if e.expires and e.expires < today:
            (fail if (today - e.expires).days > grace_days else warn).append(e)
    return warn, fail


def _join_regex(entries: list[SkipEntry]) -> str:
    if not entries:
        return ""
    if len(entries) == 1:
        return entries[0].match
    # plain groups, no `(?:`: the `?` is a glob char and some upstream scripts expand flags unquoted
    return "|".join(f"({e.match})" for e in entries)


def render_skips(framework: str, skips: SkipFile, workdir: Path) -> SkipRender:
    entries = skips.skips
    r = SkipRender(regex=_join_regex(entries))
    if not entries:
        return r
    if framework == "go":
        r.args = f"-skip={shlex.quote(r.regex)}"
    elif framework == "nextest":
        parts = [e.filter or f"test(/{e.match}/)" for e in entries]
        expr = " | ".join(f"({p})" for p in parts)
        r.args = f"-E {shlex.quote(f'not ({expr})')}"
    elif framework == "surefire":
        f = workdir / "surefire-excludes.txt"
        f.write_text("\n".join(e.match for e in entries) + "\n")
        r.file = str(f)
        r.args = f"-Dsurefire.excludesFile={shlex.quote(str(f))}"
    elif framework == "redis":
        f = workdir / "redis-skipfile.txt"
        f.write_text("\n".join(e.match for e in entries) + "\n")
        r.file = str(f)
        r.args = f"--skipfile {shlex.quote(str(f))}"
    elif framework == "jest":
        r.args = "--testPathIgnorePatterns " + " ".join(shlex.quote(e.match) for e in entries)
    elif framework == "bats":
        # bats --filter is a positive POSIX ERE (no lookahead) and 1.8 has no negative filter
        r.unsupported = "bats can only select tests, not exclude them; skip by tagging tests upstream or narrowing tests.command"
    else:  # generic: expose the regex; the command decides how to use it
        r.env["PATCHER_SKIP_REGEX"] = r.regex
    return r


TEST_USER, TEST_UID = "tester", 1001  # created in patcher/Dockerfile


def _as_test_user(command: str, src: Path, env: dict[str, str]) -> tuple[str, dict[str, str]]:
    """Wrap `command` to run as the unprivileged test user (only when we are root)."""
    import os

    if os.geteuid() != 0:
        return command, env
    # the test user needs the checkout and the shared Go/Cargo caches; Docker socket access via its group
    run(["chown", "-R", f"{TEST_UID}:{TEST_UID}", str(src)], quiet=True)
    for d in (env.get("GOPATH") or os.environ.get("GOPATH"), os.environ.get("CARGO_HOME")):
        if d and Path(d).exists():
            run(["chmod", "-R", "a+rwX", d], quiet=True, check=False)
    groups = [str(TEST_UID)]
    sock = Path("/var/run/docker.sock")
    if sock.exists():
        groups.append(str(sock.stat().st_gid))
    env = {**env, "HOME": f"/home/{TEST_USER}", "USER": TEST_USER, "GOCACHE": f"/home/{TEST_USER}/.cache/go-build"}
    wrapped = f"setpriv --reuid={TEST_UID} --regid={TEST_UID} --groups={','.join(groups)} bash -euo pipefail -c {shlex.quote(command)}"
    return wrapped, env


def run_tests(src: Path, tests: Tests, skips: SkipFile, out: Path, env: dict[str, str], *, grace_days: int) -> TestOutcome:
    if not tests.enabled:
        return TestOutcome(ran=False, passed=True, note="tests disabled in recipe")
    out.mkdir(parents=True, exist_ok=True)
    warn, fail = check_expiry(skips, grace_days)
    for e in warn:
        log(f"warning: skip {e.match!r} expired on {e.expires} (owner {e.owner})")
    if fail:
        return TestOutcome(ran=False, passed=False, expired=fail,
                           note=f"{len(fail)} skip(s) expired more than {grace_days} days ago; renew or remove them")
    sk = render_skips(tests.framework, skips, out)
    if sk.unsupported:
        return TestOutcome(ran=False, passed=False, note=f"skips/ has entries but {sk.unsupported}")
    consumes = any(f"{{{{{k}}}}}" in tests.command for k in ("skip_args", "skip_regex", "skip_file")) or tests.skipVia \
        or tests.framework == "generic"
    if skips.skips and not consumes:
        return TestOutcome(ran=False, passed=False, note="skips/ has entries but tests.command uses none of {{skip_args}}, "
                           "{{skip_regex}}, {{skip_file}} or skipVia, so they would be silently ignored")
    tctx = {"skip_args": sk.args, "skip_regex": sk.regex, "skip_file": sk.file, "src": str(src)}
    test_env = {**env, **{k: render(v, tctx) for k, v in tests.env.items()}, **sk.env}
    if tests.skipVia and tests.skipVia.env:
        test_env[tests.skipVia.env] = render(tests.skipVia.format, tctx) if sk.args or sk.regex else ""
        tctx["skip_args"] = ""
    command = render(tests.command, tctx)
    log_file = out / "tests.log"
    compose = None
    try:
        for cmd in tests.setup:
            run(render(cmd, tctx), cwd=src, env=test_env, log_file=log_file, capture=False, clean=True)
        if tests.services:
            compose = ["docker", "compose", "-f", str(src / tests.services.compose)]
            run([*compose, "up", "-d", "--wait", *tests.services.services], cwd=src, env=test_env, log_file=log_file, capture=False)
        run_cmd, run_env = _as_test_user(command, src, test_env) if tests.runAs == "nonroot" else (command, test_env)
        res = run(run_cmd, cwd=src, env=run_env, log_file=log_file, capture=False, check=False, timeout=tests.timeoutMinutes * 60,
                  clean=True)
        passed = res.code == 0
        tail = "\n".join(res.out.splitlines()[-80:])
        failures = "" if passed else failure_summary(tests.framework, res.out)
        seconds = res.seconds
    except CommandError as e:
        passed, tail, seconds, failures = False, e.tail, 0.0, ""
    finally:
        if compose:
            run([*compose, "down", "-v"], cwd=src, env=test_env, log_file=log_file, check=False)
    junit: list[Path] = []
    for pat in tests.junit:
        for i, f in enumerate(sorted(glob.glob(str(src / pat), recursive=True))):
            dest = out / f"junit-{i}-{Path(f).name}"
            shutil.copy(f, dest)
            junit.append(dest)
    note = ""
    if not passed and skips.quarantine and junit:
        failing = failed_cases(junit)
        if failing and all(_quarantined(c, skips.quarantine) for c in failing):
            passed, note = True, f"{len(failing)} failing test(s) are all quarantined: " + ", ".join(sorted(failing)[:20])
    return TestOutcome(ran=True, passed=passed, seconds=seconds, command=command, skipped=skips.skips,
                       junit=[j.name for j in junit], tail=tail, failures=failures, note=note)


def failed_cases(files: list[Path]) -> set[str]:
    """`Class/name` (or `name`) of every failed/errored JUnit testcase."""
    out: set[str] = set()
    for f in files:
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        for case in root.iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                cls, name = case.get("classname", ""), case.get("name", "")
                out.add(f"{cls}/{name}" if cls else name)
    return out


def _quarantined(case: str, entries: list[SkipEntry]) -> bool:
    name = case.rsplit("/", 1)[-1]
    return any(re.search(e.match, case) or re.search(e.match, name) for e in entries)
