#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for _marshalld_supervisor (clean env, classification, run_job)."""

from __future__ import annotations

import asyncio
import sys

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-build-server', 'marshalld.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _marshalld_supervisor as supervisor  # noqa: E402


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
