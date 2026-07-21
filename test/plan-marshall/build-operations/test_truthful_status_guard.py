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
3. The sibling truthfulness obligation on the timeout branch: a run killed by
   the outer timeout reports the zero-failure test evidence its log proves
   (``tests`` + ``tool_duration_seconds``), attaches nothing when the parsed
   summary carries failures, and degrades to the historical bare timeout
   result — with a stderr warning, never an exception — when the log cannot
   be parsed.
"""

import json
import types

# _build_shared / _build_result live under script-shared/scripts/build/ and are
# importable directly via the conftest cross-skill PYTHONPATH.
import _build_shared
import pytest
from _build_parse import UnitTestSummary
from _build_result import (
    STATUS_SUCCESS,
    DirectCommandResult,
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


# =============================================================================
# Timeout evidence (a killed run still reports what its log proves)
# =============================================================================


def _timeout_result_input() -> DirectCommandResult:
    """The DirectCommandResult shape cmd_run_common receives for a killed run."""
    result: DirectCommandResult = {
        'status': 'timeout',
        'exit_code': -1,
        'duration_seconds': 600,
        'timeout_used_seconds': 600,
        'log_file': '/tmp/does-not-matter.log',
        'command': './pw module-tests',
    }
    return result


def _emit_timeout(capsys, parser) -> dict:
    """Run cmd_run_common over a timeout result and return the emitted JSON."""
    exit_code = _build_shared.cmd_run_common(
        _timeout_result_input(), parser, 'python', output_format='json'
    )
    assert exit_code == 0, 'a timeout is modeled in the output, not the exit code'
    emitted: dict = json.loads(capsys.readouterr().out)
    return emitted


def test_timeout_attaches_zero_failure_evidence(capsys):
    """A killed run whose log parses green reports its test evidence."""

    def _green_parser(log_file, *args):
        return ([], UnitTestSummary(passed=42, failed=0, skipped=1, total=43, duration_seconds=412.87), 'SUCCESS')

    emitted = _emit_timeout(capsys, _green_parser)

    assert emitted['status'] == 'timeout'
    assert emitted['tests'] == {
        'passed': 42,
        'failed': 0,
        'skipped': 1,
        'total': 43,
        'duration_seconds': 412.87,
    }
    assert emitted['tool_duration_seconds'] == 412.87


def test_timeout_omits_tool_duration_when_parser_reports_none(capsys):
    """A parser with no duration still attaches tests, without tool_duration_seconds."""

    def _no_duration_parser(log_file, *args):
        return ([], UnitTestSummary(passed=5, failed=0, skipped=0, total=5), 'SUCCESS')

    emitted = _emit_timeout(capsys, _no_duration_parser)

    assert emitted['status'] == 'timeout'
    assert emitted['tests']['passed'] == 5
    assert 'duration_seconds' not in emitted['tests']
    assert 'tool_duration_seconds' not in emitted


def test_timeout_attaches_no_evidence_when_tests_failed(capsys):
    """A summary carrying failures is not proof the suite completed — not attached."""

    def _failing_parser(log_file, *args):
        return ([], UnitTestSummary(passed=10, failed=2, skipped=0, total=12, duration_seconds=9.5), 'FAILURE')

    emitted = _emit_timeout(capsys, _failing_parser)

    assert emitted['status'] == 'timeout'
    assert 'tests' not in emitted
    assert 'tool_duration_seconds' not in emitted


def test_timeout_degrades_to_bare_result_when_parser_raises(capsys):
    """An unparseable log warns on stderr and emits the historical bare result."""

    def _raising_parser(log_file, *args):
        raise OSError('log file vanished')

    exit_code = _build_shared.cmd_run_common(
        _timeout_result_input(), _raising_parser, 'python', output_format='json'
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    emitted = json.loads(captured.out)
    assert emitted['status'] == 'timeout'
    assert emitted['timeout_used_seconds'] == 600
    assert 'tests' not in emitted
    assert 'tool_duration_seconds' not in emitted
    assert '[WARNING] Timeout evidence parse failed' in captured.err
