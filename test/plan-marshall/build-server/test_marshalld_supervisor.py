#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for _marshalld_supervisor (clean env, classification, run_job).

Terminal classification carries one subtlety worth stating up front: the daemon's
build child is normally the build wrapper, which exits 0 even when the build
failed and reports its real verdict in the build-result TOON it emits. A zero
exit is therefore NECESSARY but not SUFFICIENT for ``success`` — the emitted
verdict must agree. The ``timeout`` and ``killed`` legs are never reclassified by
log content.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-build-server', 'marshalld.py')
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
# classify_terminal
# =============================================================================


def test_classify_success():
    assert supervisor.classify_terminal(0, timed_out=False) == 'success'


def test_classify_failure():
    assert supervisor.classify_terminal(3, timed_out=False) == 'failure'


def test_classify_timeout_outranks_signal_exit():
    # A timeout kill leaves a negative returncode, but the timed_out flag wins.
    assert supervisor.classify_terminal(-9, timed_out=True) == 'timeout'


def test_classify_killed_is_not_failure():
    # A negative exit the supervisor did NOT cause is 'killed', never 'failure'.
    assert supervisor.classify_terminal(-9, timed_out=False) == 'killed'


def test_classify_none_returncode_is_killed():
    assert supervisor.classify_terminal(None, timed_out=False) == 'killed'


# =============================================================================
# build_baseline_env
# =============================================================================


def test_baseline_env_filters_to_whitelist():
    source = {'PATH': '/bin', 'HOME': '/home/u', 'SECRET_TOKEN': 'nope', 'AWS_KEY': 'nope'}

    env = supervisor.build_baseline_env(source)

    assert env == {'PATH': '/bin', 'HOME': '/home/u'}
    assert 'SECRET_TOKEN' not in env
    assert 'AWS_KEY' not in env


def test_baseline_env_omits_missing_keys():
    env = supervisor.build_baseline_env({'PATH': '/bin'})

    assert env == {'PATH': '/bin'}


# =============================================================================
# JobProgress
# =============================================================================


def test_job_progress_mark_resets_idle():
    progress = supervisor.JobProgress()
    before = progress.last_activity
    progress.mark()

    assert progress.last_activity >= before
    assert progress.elapsed() >= 0
    assert progress.idle_seconds() >= 0


# =============================================================================
# run_job (real subprocess)
# =============================================================================


def test_run_job_success(tmp_path):
    log_file = str(tmp_path / 'ok.log')

    payload = asyncio.run(
        supervisor.run_job(
            [sys.executable, '-c', 'print("hello")'],
            str(tmp_path),
            timeout=30,
            log_file=log_file,
        )
    )

    assert payload['status'] == 'success'
    assert payload['exit_code'] == 0
    assert payload['log_file'] == log_file


def test_run_job_failure(tmp_path):
    log_file = str(tmp_path / 'fail.log')

    payload = asyncio.run(
        supervisor.run_job(
            [sys.executable, '-c', 'import sys; sys.exit(3)'],
            str(tmp_path),
            timeout=30,
            log_file=log_file,
        )
    )

    assert payload['status'] == 'failure'
    assert payload['exit_code'] == 3


def test_run_job_timeout(tmp_path):
    log_file = str(tmp_path / 'to.log')

    payload = asyncio.run(
        supervisor.run_job(
            # Block indefinitely on signal.pause() rather than sleeping a fixed
            # 10 s: the child is killed by the supervisor's timeout=1, so the
            # test never depends on a wall-clock duration outrunning the timeout.
            [sys.executable, '-c', 'import signal; signal.pause()'],
            str(tmp_path),
            timeout=1,
            log_file=log_file,
        )
    )

    assert payload['status'] == 'timeout'


def test_run_job_clean_env_excludes_secret(tmp_path):
    log_file = str(tmp_path / 'env.log')
    # SECRET_TOKEN is NOT in the whitelist, so build_baseline_env drops it: the
    # child prints an empty string for it.
    code = 'import os; print("SECRET=" + os.environ.get("SECRET_TOKEN", ""))'

    payload = asyncio.run(
        supervisor.run_job(
            [sys.executable, '-c', code],
            str(tmp_path),
            timeout=30,
            log_file=log_file,
            env=supervisor.build_baseline_env({'PATH': '/usr/bin:/bin', 'SECRET_TOKEN': 'leak'}),
        )
    )

    assert payload['status'] == 'success'
    captured = (tmp_path / 'env.log').read_text()
    assert 'SECRET=leak' not in captured
    assert 'SECRET=' in captured  # the var resolved to empty, proving it was dropped


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
# run_job — exit 0 is necessary but not sufficient
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
