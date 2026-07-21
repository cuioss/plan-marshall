#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for the truthful-status structural guard.

The guard (``assert_truthful_status`` in ``_build_result``) is a fail-closed
invariant (ADR-009): a build result must never advertise ``status='success'``
while holding a non-zero ``exit_code``. These tests lock two things:

1. The pure guard rejects an inconsistent success result and passes a
   consistent one (or a non-success result).
2. The guard is actually WIRED into the success-emit choke points
   (``cmd_run_common`` / ``cmd_parse_common``) so a future caller that
   assembles an untruthful success fails loudly at emit time rather than
   printing green.
"""

import types

# _build_shared / _build_result live under script-shared/scripts/build/ and are
# importable directly via the conftest cross-skill PYTHONPATH.
import _build_shared
import pytest
from _build_result import (
    STATUS_SUCCESS,
    TruthfulStatusError,
    assert_truthful_status,
    error_result,
    success_result,
)


def _fake_parser(log_file, *args):
    """Minimal parser stub: no issues, no test summary, BUILD SUCCESS."""
    return ([], None, 'SUCCESS')


# =============================================================================
# Pure guard behaviour
# =============================================================================


def test_assert_truthful_status_raises_on_success_with_nonzero_exit():
    """A result reporting success while holding a non-zero exit code is rejected."""
    inconsistent = {'status': 'success', 'exit_code': 1, 'command': './pw verify'}
    with pytest.raises(TruthfulStatusError):
        assert_truthful_status(inconsistent)


def test_assert_truthful_status_passes_consistent_success():
    """A genuine success result (exit_code 0) passes silently."""
    ok = success_result(duration_seconds=1, log_file='/tmp/x.log', command='./pw verify')
    assert_truthful_status(ok)  # must not raise


def test_assert_truthful_status_ignores_error_result():
    """The guard targets untruthful success only — a non-zero error result passes."""
    err = error_result(
        error='build_failed', exit_code=1, duration_seconds=1, log_file='/tmp/x.log', command='./pw verify'
    )
    assert_truthful_status(err)  # must not raise


def test_assert_truthful_status_missing_exit_code_treated_as_zero():
    """A success result with no exit_code field is treated as exit_code 0 and passes."""
    assert_truthful_status({'status': STATUS_SUCCESS})  # must not raise


# =============================================================================
# Emit-path wiring (the guard is invoked before a success is printed)
# =============================================================================


def test_cmd_run_common_emit_path_is_guarded(monkeypatch):
    """cmd_run_common calls the guard: a success_result carrying a non-zero
    exit_code is rejected before it can be printed."""

    def _inconsistent_success(duration_seconds, log_file, command, **extra):
        return {
            'status': 'success',
            'exit_code': 1,
            'duration_seconds': duration_seconds,
            'log_file': log_file,
            'command': command,
        }

    monkeypatch.setattr(_build_shared, 'success_result', _inconsistent_success)

    result = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 1,
        'log_file': '/tmp/does-not-matter.log',
        'command': './pw verify',
    }
    with pytest.raises(TruthfulStatusError):
        _build_shared.cmd_run_common(result, _fake_parser, 'python')


def test_cmd_parse_common_invokes_guard(monkeypatch, tmp_path):
    """cmd_parse_common calls the guard before emitting the parse result."""
    calls = []

    def _spy(result):
        calls.append(result)

    monkeypatch.setattr(_build_shared, 'assert_truthful_status', _spy)

    log = tmp_path / 'x.log'
    log.write_text('[INFO] BUILD SUCCESS\n')
    args = types.SimpleNamespace(log=str(log), mode='structured', format='toon')

    _build_shared.cmd_parse_common(args, _fake_parser)

    assert calls, 'cmd_parse_common must call assert_truthful_status before emitting'
