"""Subprocess helpers: every command is echoed and optionally tee'd to a log file."""

from __future__ import annotations

import os
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


class CommandError(RuntimeError):
    def __init__(self, cmd: str, code: int, tail: str):
        super().__init__(f"command failed ({code}): {cmd}\n{tail}")
        self.cmd = cmd
        self.code = code
        self.tail = tail


@dataclass
class Result:
    code: int
    out: str
    seconds: float


def log(msg: str) -> None:
    print(f"[patcher] {msg}", file=sys.stderr, flush=True)


# The patcher's own configuration (its Trivy cache, registry, Copa address...). Upstream builds and
# tests must not see it: e.g. Trivy's own test suite reads TRIVY_* and fails on TRIVY_CACHE_DIR.
PIPELINE_ENV_PREFIXES = ("TRIVY_", "PATCHER_", "COPA_")


def _env(env: Mapping[str, str] | None, clean: bool = False) -> dict[str, str]:
    merged = {k: v for k, v in os.environ.items() if not (clean and k.startswith(PIPELINE_ENV_PREFIXES))}
    if env:
        merged.update({k: str(v) for k, v in env.items()})
    return merged


def run(
    cmd: Sequence[str] | str,
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    check: bool = True,
    capture: bool = True,
    log_file: Path | None = None,
    timeout: float | None = None,
    quiet: bool = False,
    input: str | None = None,
    clean: bool = False,
) -> Result:
    """Run a command. Strings run through `bash -euo pipefail -c`; lists run directly.

    With `capture=False` output streams to stderr (and `log_file`), which is what we want
    for long builds/tests so CI logs show progress.
    """
    shell = isinstance(cmd, str)
    argv = ["bash", "-euo", "pipefail", "-c", cmd] if shell else list(cmd)
    shown = cmd if shell else shlex.join(argv)
    if not quiet:
        log(f"$ {shown}" + (f"  (in {cwd})" if cwd else ""))
    start = time.monotonic()
    lf = log_file.open("a") if log_file else None
    try:
        if lf:
            lf.write(f"\n$ {shown}\n")
            lf.flush()
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=_env(env, clean),
            stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            # with a timeout, the command gets its own process group so the whole tree can be killed:
            # a hung test prints nothing, and its children keep the output pipe open
            start_new_session=timeout is not None,
        )
        timed_out = threading.Event()
        timer = None
        if timeout:
            timer = threading.Timer(timeout, _kill_group, (proc, timed_out))
            timer.daemon = True
            timer.start()
        if input is not None:
            assert proc.stdin
            proc.stdin.write(input)
            proc.stdin.close()
        chunks: list[str] = []
        assert proc.stdout
        try:
            for line in proc.stdout:
                chunks.append(line)
                if lf:
                    lf.write(line)
                if not capture:
                    sys.stderr.write(line)
            code = proc.wait()
        except KeyboardInterrupt:
            if timeout:  # not in our foreground group: stop it ourselves
                _kill_group(proc, timed_out)
            raise
        finally:
            if timer:
                timer.cancel()
    finally:
        if lf:
            lf.close()
    out = "".join(chunks)
    seconds = time.monotonic() - start
    if timed_out.is_set():
        raise CommandError(shown, -9, f"timed out after {timeout:.0f}s (killed with its child processes)\n"
                           + "\n".join(out.splitlines()[-60:]))
    if check and code != 0:
        tail = "\n".join(out.splitlines()[-60:])
        raise CommandError(shown, code, tail)
    return Result(code=code, out=out, seconds=seconds)


def first_error(text: str | None) -> str:
    """The line of a failure log most worth showing: the first one mentioning an error, else the last."""
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    for l in lines:
        if "error" in l.lower():
            return l[:160]
    return (lines[-1] if lines else "unknown error")[:160]


def _kill_group(proc: subprocess.Popen, flag: threading.Event) -> None:
    flag.set()
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def output(cmd: Sequence[str], *, cwd: Path | None = None, env: Mapping[str, str] | None = None, check: bool = True) -> str:
    """stdout only (stderr kept apart), for commands whose output is parsed: e.g. `go` prints
    "switching to go1.26.10" on stderr, which must not end up in JSON or a version string.
    `check=False` for tools that exit non-zero when they find something (osv-scanner, govulncheck)."""
    proc = subprocess.run(list(cmd), cwd=cwd, env=_env(env), stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise CommandError(shlex.join(cmd), proc.returncode, (proc.stderr or proc.stdout)[-4000:])
    return proc.stdout


# failures that come from fetching something over a flaky network, not from the work itself
NETWORK_ERRORS = re.compile(r"unexpected EOF|connection reset|i/o timeout|TLS handshake timeout|no such host|Could not resolve host|"
                            r"Temporary failure in name resolution|EAI_AGAIN|ECONNRESET|ETIMEDOUT|502 Bad Gateway|"
                            r"503 Service Unavailable|429 Too Many Requests", re.I)


def retry_on_network(call, *, attempts: int = 2, wait: int = 30, timeouts: bool = False):
    """call(), and call() again after `wait` seconds if it failed with a network error (DNS blips, EOFs from
    module proxies and registries), or with `timeouts`, if it hung and was killed; any other failure is raised at once."""
    for i in range(attempts):
        try:
            return call()
        except CommandError as e:
            m = NETWORK_ERRORS.search(e.tail)
            why = m.group(0) if m else ("hung, killed at the timeout" if timeouts and e.code == -9 else None)
            if not why or i == attempts - 1:
                raise
            log(f"{why}; retrying in {wait}s")
            time.sleep(wait)


def which(name: str) -> str | None:
    from shutil import which as _which

    return _which(name)
