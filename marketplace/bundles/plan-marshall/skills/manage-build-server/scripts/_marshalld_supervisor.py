#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Subprocess supervisor for the marshalld build server (clean env, classify).

The supervisor runs one build child per admitted job and owns four
responsibilities:

* **Clean server-side baseline env (S2)** — the child's environment is built
  from a fixed server-side whitelist, NEVER forwarded from the client and NEVER
  carrying provider secrets. A submit cannot smuggle credentials or override
  ``PATH`` into the build.
* **Stream capture** — the child's combined stdout/stderr is streamed to a log
  file as it is produced, so a long build's output is durable even if the wait
  is reaped.
* **Liveness tracking** — every output chunk marks progress, so the daemon can
  answer a bound-expiry ``wait`` with a live running-status TOON
  (``elapsed`` / ``idle_seconds``) rather than a timeout-shaped body.
* **Terminal classification** — the child's exit is classified into
  ``success | failure | timeout | killed``, reusing the shared
  :mod:`_build_result` shape. ``killed`` (the child died by a signal the
  supervisor did NOT send) is its own terminal state — "externally killed — not
  flaky, do not blind-retry" — and is NEVER folded into ``failure``.

The classification and env helpers are pure and unit-testable without spawning a
process; :func:`run_job` drives a real ``asyncio`` subprocess and is exercised
against trivial commands.

Usage:
    from _marshalld_supervisor import run_job, JobProgress, build_baseline_env

    progress = JobProgress()
    payload = await run_job(command, cwd, timeout=300, log_file=log, progress=progress)
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import IO, Any

from _build_result import (
    ERROR_BUILD_FAILED,
    error_result,
    success_result,
    timeout_result,
)
from _build_server_protocol import (
    STATUS_KILLED,
    status_from_result,
    status_payload,
)

# The fixed server-side env whitelist. Everything not listed here is dropped, so
# no client-forwarded variable and no provider secret reaches the build child.
BASELINE_ENV_KEYS = (
    'PATH',
    'HOME',
    'LANG',
    'LC_ALL',
    'LC_CTYPE',
    'TERM',
    'TMPDIR',
    'USER',
    'SHELL',
    'PLAN_MARSHALL_HOME',
)

_READ_CHUNK = 4096


def build_baseline_env(source: dict[str, str] | None = None) -> dict[str, str]:
    """Build a clean build-child environment from the server-side whitelist.

    Args:
        source: The environment to filter (defaults to ``os.environ``).

    Returns:
        A new dict containing only the whitelisted keys that are present in the
        source — no client env, no provider secrets.
    """
    src = dict(os.environ) if source is None else source
    return {key: src[key] for key in BASELINE_ENV_KEYS if key in src}


def classify_terminal(returncode: int | None, *, timed_out: bool) -> str:
    """Classify a finished child into a terminal wire status.

    Args:
        returncode: The child's exit code (negative ``-N`` when killed by signal
            ``N``); may be ``None`` only for a never-started child.
        timed_out: ``True`` when the supervisor terminated the child for
            exceeding its timeout.

    Returns:
        One of ``timeout`` / ``killed`` / ``success`` / ``failure``. A timeout
        outranks the signal exit (the supervisor sent that signal); a negative
        exit the supervisor did NOT cause is ``killed`` — never ``failure``.
    """
    if timed_out:
        return 'timeout'
    if returncode is None:
        return STATUS_KILLED
    if returncode < 0:
        return STATUS_KILLED
    return 'success' if returncode == 0 else 'failure'


@dataclass
class JobProgress:
    """Liveness tracker for a running job.

    Attributes:
        start: Monotonic start timestamp.
        last_activity: Monotonic timestamp of the last output chunk.
    """

    start: float = field(default_factory=time.monotonic)
    last_activity: float = field(default_factory=time.monotonic)

    def mark(self) -> None:
        """Record output activity (resets the idle timer)."""
        self.last_activity = time.monotonic()

    def elapsed(self) -> float:
        """Return seconds since the job started."""
        return time.monotonic() - self.start

    def idle_seconds(self) -> float:
        """Return seconds since the last output chunk (``last_progress``)."""
        return time.monotonic() - self.last_activity


async def _pump(stream: asyncio.StreamReader | None, sink: IO[bytes], progress: JobProgress | None) -> None:
    """Stream a child pipe to the log sink, marking progress on each chunk."""
    if stream is None:
        return
    while True:
        chunk = await stream.read(_READ_CHUNK)
        if not chunk:
            return
        sink.write(chunk)
        if progress is not None:
            progress.mark()


def _terminal_payload(
    status: str,
    *,
    returncode: int | None,
    duration: int,
    log_file: str,
    command_str: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Render a terminal status payload reusing the _build_result shape."""
    if status == 'timeout':
        return status_from_result(
            timeout_result(timeout_seconds, duration, log_file, command_str)
        )
    if status == STATUS_KILLED:
        return status_payload(
            STATUS_KILLED,
            duration_seconds=duration,
            log_file=log_file,
            exit_code=returncode if returncode is not None else -1,
        )
    if status == 'success':
        return status_from_result(success_result(duration, log_file, command_str))
    return status_from_result(
        error_result(ERROR_BUILD_FAILED, returncode or 1, duration, log_file, command_str)
    )


async def run_job(
    command: list[str],
    cwd: str,
    *,
    timeout: int,
    log_file: str,
    env: dict[str, str] | None = None,
    progress: JobProgress | None = None,
) -> dict[str, Any]:
    """Run one build child and return its terminal status payload.

    Args:
        command: The executor-form argv to run (already verified).
        cwd: The working directory (the submitted tree).
        timeout: Wall-clock timeout in seconds; on expiry the child is killed
            and the status is ``timeout``.
        log_file: Path to stream combined stdout/stderr into.
        env: The child environment; defaults to :func:`build_baseline_env`.
        progress: Optional liveness tracker updated on each output chunk.

    Returns:
        The terminal status payload (``success | failure | timeout | killed``)
        in the shared result shape.
    """
    child_env = env if env is not None else build_baseline_env()
    command_str = ' '.join(command)
    if progress is None:
        progress = JobProgress()

    proc = await asyncio.create_subprocess_exec(
        *command,
        cwd=cwd,
        env=child_env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    timed_out = False
    with open(log_file, 'wb') as sink:
        pumps = [
            asyncio.create_task(_pump(proc.stdout, sink, progress)),
            asyncio.create_task(_pump(proc.stderr, sink, progress)),
        ]
        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout)
        except TimeoutError:
            timed_out = True
            proc.kill()
            await proc.wait()
        finally:
            await asyncio.gather(*pumps, return_exceptions=True)

    duration = int(progress.elapsed())
    status = classify_terminal(proc.returncode, timed_out=timed_out)
    return _terminal_payload(
        status,
        returncode=proc.returncode,
        duration=duration,
        log_file=log_file,
        command_str=command_str,
        timeout_seconds=timeout,
    )
