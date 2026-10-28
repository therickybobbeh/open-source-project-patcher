"""Subprocess helpers: every command is echoed and optionally tee'd to a log file."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
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
        )
        if input is not None:
            assert proc.stdin
            proc.stdin.write(input)
            proc.stdin.close()
        chunks: list[str] = []
        assert proc.stdout
        deadline = start + timeout if timeout else None
        for line in proc.stdout:
            chunks.append(line)
            if lf:
                lf.write(line)
            if not capture:
                sys.stderr.write(line)
            if deadline and time.monotonic() > deadline:
                proc.kill()
                raise CommandError(shown, -9, f"timed out after {timeout}s")
        code = proc.wait()
    finally:
        if lf:
            lf.close()
    out = "".join(chunks)
    seconds = time.monotonic() - start
    if check and code != 0:
        tail = "\n".join(out.splitlines()[-60:])
        raise CommandError(shown, code, tail)
    return Result(code=code, out=out, seconds=seconds)


def output(cmd: Sequence[str], *, cwd: Path | None = None, env: Mapping[str, str] | None = None) -> str:
    """stdout only (stderr kept apart), for commands whose output is parsed: e.g. `go` prints
    "switching to go1.26.10" on stderr, which must not end up in JSON or a version string."""
    proc = subprocess.run(list(cmd), cwd=cwd, env=_env(env), stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if proc.returncode != 0:
        raise CommandError(shlex.join(cmd), proc.returncode, (proc.stderr or proc.stdout)[-4000:])
    return proc.stdout


def which(name: str) -> str | None:
    from shutil import which as _which

    return _which(name)
