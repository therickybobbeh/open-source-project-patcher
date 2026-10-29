"""Run the upstream test suite with skip-file entries translated to the framework's own filters."""

from __future__ import annotations

import datetime as dt
import glob
import re
import shlex
import shutil
import time
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
    "gradle": r"^\S.* > .* FAILED$|^FAILURE: |^\d+ tests? completed, \d+ failed",
    "pytest": r"^FAILED |^ERROR |^=+ .*(failed|error)",
    "vitest": r"^\s*(×|FAIL) ",
    "mocha": r"^\s+\d+\) ",
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
    __test__ = False  # not a pytest test class
    ran: bool
    passed: bool
    seconds: float = 0.0
    command: str = ""
    skipped: list[SkipEntry] = field(default_factory=list)
    expired: list[SkipEntry] = field(default_factory=list)
    junit: list[str] = field(default_factory=list)
    tail: str = ""
    failures: str = ""
    failed: list[str] = field(default_factory=list)  # failing test ids (JUnit, else parsed from the log)
    preexisting: list[str] = field(default_factory=list)  # failing tests that also fail on the unpatched source
    note: str = ""
    oom: bool = False  # the Go toolchain was killed while building the tests (out of memory)


# the kernel's OOM killer stopping the Go toolchain mid-build ("…/compile: signal: killed"): the packages it hits
# differ from run to run, so the "failures" say nothing about the bumps
_TOOLCHAIN_KILLED = re.compile(r"^.*/(?:compile|link|asm|cgo): signal: killed$", re.M)


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
    elif framework == "gradle":
        # an init script excludes the tests in every Test task (Gradle filters can't be negated on the CLI)
        from .adapters.gradle import init_script_for_skips

        f = workdir / "gradle-skips.init.gradle"
        f.write_text(init_script_for_skips([e.match for e in entries]))
        r.file = str(f)
        r.args = f"--init-script {shlex.quote(str(f))}"
    elif framework == "pytest":
        # node ids (path::Class::test) are deselected exactly; anything else is a -k keyword expression
        ids = [e.match for e in entries if "::" in e.match]
        exprs = [e.match for e in entries if "::" not in e.match]
        parts = [f"--deselect {shlex.quote(i)}" for i in ids]
        if exprs:
            parts.append("-k " + shlex.quote("not (" + " or ".join(f"({x})" for x in exprs) + ")"))
        r.args = " ".join(parts)
    elif framework in ("jest", "vitest"):
        # `match` = test-name regex (JS regex: negative lookahead works), `filter` = test-path pattern
        names = [e.match for e in entries if not e.filter]
        paths = [e.filter for e in entries if e.filter]
        parts = []
        if names:
            parts.append("--testNamePattern " + shlex.quote("^(?!.*(" + "|".join(f"(?:{n})" for n in names) + "))"))
        if paths and framework == "jest":
            parts.append("--testPathIgnorePatterns " + " ".join(shlex.quote(x) for x in paths))
        elif paths:
            parts += [f"--exclude {shlex.quote(x)}" for x in paths]
        r.args = " ".join(parts)
    elif framework == "mocha":
        r.args = f"--grep {shlex.quote(r.regex)} --invert"
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
    # `go install` (Argo CD's test script installs go-junit-report) must land in the shared, writable $GOPATH/bin,
    # never in a toolchain's root-owned install dir that a GOBIN might point at
    env.pop("GOBIN", None)
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
    started = time.monotonic()
    timeout_note = ""
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
        passed, tail, seconds, failures = False, e.tail, time.monotonic() - started, ""
        if e.code == -9:  # killed at tests.timeoutMinutes: the last output line usually names the test that hung
            last = next((l.strip() for l in reversed(e.tail.splitlines()) if l.strip() and not l.startswith("timed out")), "")
            timeout_note = (f"The suite timed out after {tests.timeoutMinutes} min (tests.timeoutMinutes) and was stopped; "
                            f"last output: {last[:160]}")
    finally:
        if compose:
            run([*compose, "down", "-v"], cwd=src, env=test_env, log_file=log_file, check=False)
    junit: list[Path] = []
    for pat in tests.junit:
        for i, f in enumerate(sorted(glob.glob(str(src / pat), recursive=True))):
            dest = out / f"junit-{i}-{Path(f).name}"
            shutil.copy(f, dest)
            junit.append(dest)
    note = timeout_note
    killed = None if passed or not log_file.is_file() else _TOOLCHAIN_KILLED.search(log_file.read_text(errors="replace"))
    if killed:
        note = (f"The Go toolchain was killed while building the tests ({killed.group(0).strip()[:160]}), most likely out of "
                "memory: the failures say nothing about the bumps. Lower the parallelism (tests.env GOFLAGS: \"-p=2\") or use a "
                "bigger runner.")
    if not passed and skips.quarantine and junit:
        failing = failed_cases(junit)
        if failing and all(_quarantined(c, skips.quarantine) for c in failing):
            passed, note = True, f"{len(failing)} failing test(s) are all quarantined: " + ", ".join(sorted(failing)[:20])
    failed = [] if passed else (sorted(failed_cases(junit)) if junit else failed_ids(tests.framework, failures))
    return TestOutcome(ran=True, passed=passed, seconds=seconds, command=command, skipped=skips.skips,
                       junit=[j.name for j in junit], tail=tail, failures=failures, failed=failed, note=note, oom=bool(killed))


def failed_ids(framework: str, failure_lines: str) -> list[str]:
    """Stable ids from the failure summary when there's no JUnit, comparable between the patched and the
    baseline run: test names without durations, counts, numbering or panic addresses."""
    return sorted({i for i in (_stable_id(framework, line.strip()) for line in failure_lines.splitlines()) if i})


def _stable_id(framework: str, s: str) -> str | None:
    if framework == "go":
        m = re.match(r"--- FAIL: (\S+)", s)
        if m:
            return m.group(1)
        m = re.match(r"FAIL\s+(\S+)", s)  # "FAIL\tpkg\t1.2s", gotestsum "FAIL pkg.TestX (0.01s)"
        return f"FAIL {m.group(1)}" if m else None  # bare FAIL / panic lines: the package line identifies them
    if framework == "pytest":
        m = re.match(r"(FAILED|ERROR) (\S+)", s)  # node id, without the assertion message
        return f"{m.group(1)} {m.group(2)}" if m else None
    if framework == "nextest":
        m = re.match(r"(FAIL|TIMEOUT|SIGSEGV|SIGABRT) \[[^\]]*\]\s*(.+)", s)
        return f"{m.group(1)} {m.group(2)}" if m else None
    if re.search(r"\d+ tests? completed, \d+ failed|Tests run: \d+", s):
        return None  # counts change whenever anything else fails
    s = re.sub(r"^(not ok)\s+\d+\s+", r"\1 ", s)  # bats numbering
    s = re.sub(r"^\d+\)\s+", "", s)  # mocha numbering
    s = re.sub(r"\s*\(?\d+(?:\.\d+)?\s?m?s\)?$", "", s)  # trailing durations (jest, vitest)
    return s or None


def error_signature(text: str) -> list[str]:
    """The error lines of a failed run without what differs between two checkouts of the same code (checkout dirs,
    temp dirs, numbers), so the same setup failure in the patched and the baseline run compares equal."""
    sig = []
    for line in text.splitlines():
        if not re.search(r"(?i)\b(error|fatal|denied|panic|not found|no such file)", line):
            continue
        s = re.sub(r"/(?:src(?:-[\w-]+)?|baseline-src)(?=/|\s|$)", "/SRC", line)
        s = re.sub(r"/tmp/[^\s/]+", "/tmp/X", s)
        sig.append(re.sub(r"\d+", "N", s).strip())
    return sig[-10:]


def setup_error(text: str) -> str:
    """The most specific error line of a run that failed before any test: the cause, not `make: *** … Error 1`."""
    lines = [l.strip() for l in text.splitlines() if re.search(r"(?i)\b(error|fatal|denied|panic|not found|no such file)", l)]
    specific = [l for l in lines if not l.startswith("make: ***")]
    return (specific or lines or ["unknown error"])[0][:200]


def same_setup_failure(patched: TestOutcome | None, baseline: TestOutcome | None) -> bool:
    """Both runs failed before any test failed by name (the suite didn't start), with the same errors."""
    if not (patched and baseline and patched.ran and baseline.ran and not patched.passed and not baseline.passed):
        return False
    if patched.failed or baseline.failed:
        return False
    sig = error_signature(patched.tail)
    return bool(sig) and sig == error_signature(baseline.tail)


def only_preexisting(patched: TestOutcome | None, baseline: TestOutcome | None) -> bool:
    """Every failing test of the patched run also fails on the unpatched source."""
    return bool(patched and baseline and patched.ran and baseline.ran and not patched.passed and not baseline.passed
                and patched.failed and set(patched.failed) <= set(baseline.failed))


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
