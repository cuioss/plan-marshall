#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Supervisor terminal classification — exit 0 is necessary but not sufficient.

The daemon's build child is normally the build wrapper, which exits 0 even when
the build failed and reports its real verdict in the build-result TOON it emits.
These tests pin the narrowing that keeps a routed build's terminal status
truthful:

* the pure :func:`read_log_verdict` helper reads the emitted ``status:`` /
  ``exit_code:`` back from a job log, and degrades to ``None`` on a missing,
  unreadable, or TOON-less log;
* :func:`run_job` downgrades a ``success`` classification to ``failure``
  (carrying the TOON's exit code) only when the log verdict contradicts it;
* the ``timeout`` and ``killed`` legs are never reclassified by log content.

The helper tests spawn no process; the classification tests drive a real
``asyncio`` child through :func:`run_job` against trivial commands, matching the
supervisor module's own stated test strategy.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-build-server', 'manage_build_server.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _marshalld_supervisor as supervisor  # noqa: E402

# Child programs run through run_job. Each writes the shape of build-wrapper
# output the supervisor has to classify, then exits 0 (or is killed).
_EMIT_ERROR_TOON = "print('status: error'); print('exit_code: 3')"
_EMIT_SUCCESS_TOON = "print('status: success'); print('exit_code: 0')"
_EMIT_NO_TOON = "print('some build chatter with no build TOON at all')"
_EMIT_SUCCESS_THEN_HANG = "print('status: success', flush=True); import time; time.sleep(30)"
_EMIT_SUCCESS_THEN_SUICIDE = (
    "import os, signal; print('status: success', flush=True); os.kill(os.getpid(), signal.SIGKILL)"
)


def _run(code: str, tmp_path: Path, *, timeout: int = 30) -> dict:
    """Run one trivial child through run_job and return its terminal payload."""
    log_file = tmp_path / 'job.log'
    return asyncio.run(
        supervisor.run_job(
            [sys.executable, '-c', code],
            str(tmp_path),
            timeout=timeout,
            log_file=str(log_file),
        )
    )


# =============================================================================
# read_log_verdict — the pure helper
# =============================================================================


class TestReadLogVerdict:
    """The pure job-log verdict reader."""

    def test_parses_status_and_exit_code(self, tmp_path):
        log = tmp_path / 'job.log'
        log.write_text('[EXEC] ./pw verify\nstatus: error\nexit_code: 7\nduration_seconds: 3\n')

        verdict = supervisor.read_log_verdict(str(log))

        assert verdict is not None
        assert verdict.status == 'error'
        assert verdict.exit_code == 7

    def test_ignores_indented_toon_rows(self, tmp_path):
        # The errors[] table rows are indented; only the top-level keys count.
        log = tmp_path / 'job.log'
        log.write_text('status: success\nexit_code: 0\nerrors[1]{file,line}:\n  status: error\n')

        verdict = supervisor.read_log_verdict(str(log))

        assert verdict is not None
        assert verdict.status == 'success'
        assert verdict.exit_code == 0

    def test_unquotes_a_quoted_scalar(self, tmp_path):
        log = tmp_path / 'job.log'
        log.write_text('status: "error"\nexit_code: 2\n')

        verdict = supervisor.read_log_verdict(str(log))

        assert verdict is not None
        assert verdict.status == 'error'

    def test_unparseable_exit_code_degrades_to_none(self, tmp_path):
        log = tmp_path / 'job.log'
        log.write_text('status: error\nexit_code: -\n')

        verdict = supervisor.read_log_verdict(str(log))

        assert verdict is not None
        assert verdict.status == 'error'
        assert verdict.exit_code is None

    def test_log_without_status_line_returns_none(self, tmp_path):
        log = tmp_path / 'job.log'
        log.write_text('just some build chatter\n')

        assert supervisor.read_log_verdict(str(log)) is None

    def test_missing_log_returns_none(self, tmp_path):
        assert supervisor.read_log_verdict(str(tmp_path / 'absent.log')) is None


# =============================================================================
# run_job — the classification site
# =============================================================================


class TestRunJobTruthfulStatus:
    """Exit 0 is necessary but no longer sufficient for a ``success`` status."""

    def test_exit_zero_with_error_toon_is_failure_carrying_the_toon_exit_code(self, tmp_path):
        # The regression anchor: the wrapper exits 0 while reporting a failed
        # build, and the daemon must NOT render that as success.
        payload = _run(_EMIT_ERROR_TOON, tmp_path)

        assert payload['status'] == 'failure'
        assert payload['exit_code'] == 3

    def test_exit_zero_with_success_toon_is_success(self, tmp_path):
        payload = _run(_EMIT_SUCCESS_TOON, tmp_path)

        assert payload['status'] == 'success'
        assert payload['exit_code'] == 0

    def test_exit_zero_without_a_build_toon_is_success(self, tmp_path):
        # A non-wrapper command run through the daemon keeps the exit-code verdict.
        payload = _run(_EMIT_NO_TOON, tmp_path)

        assert payload['status'] == 'success'
        assert payload['exit_code'] == 0

    def test_timeout_outranks_a_contradicting_toon(self, tmp_path):
        payload = _run(_EMIT_SUCCESS_THEN_HANG, tmp_path, timeout=1)

        assert payload['status'] == 'timeout'

    def test_signal_kill_outranks_a_contradicting_toon(self, tmp_path):
        payload = _run(_EMIT_SUCCESS_THEN_SUICIDE, tmp_path)

        assert payload['status'] == 'killed'
