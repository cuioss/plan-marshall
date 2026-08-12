#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Regression coverage: a timeout is not a red test, and a kill is not a timeout.

A build that does not finish produces three distinguishable conditions — an
external **kill**, an outer-budget **timeout**, and a genuinely **failing
build** — and every consuming gate must act differently on each. This module
pins that discrimination end to end, and every case here carries its **matched
control**: for each property asserted of a non-finish, the same property is
asserted of a real failing build in the opposite direction.

The controls are the point. Every other case here confirms a gate stopped
failing on a non-failure; only the red-test controls confirm it still fails on
a failure. Without them this whole module would be satisfied by a change that
made every non-green build benign — a far worse gate than the one it replaced.

Four seams are driven, none of them re-implemented here:

1. ``_build_execute.execute_direct_base`` — the in-process classifier: a
   negative ``subprocess`` returncode is an external kill, a positive one is a
   failure, and only the finish teaches the adaptive learner.
2. ``_build_shared.cmd_run_common`` — the emit choke point: neither non-finish
   may reach the build-failure path, which stores findings and synthesises an
   ``errors[]`` row.
3. ``_build_execute_factory._daemon_result_to_direct`` — the routed leg: the
   daemon's own ``killed`` verdict must survive into the wrapper shape.
4. ``_ledger_core`` + the executor boundary's ``_derive_build_status`` — the
   status must reach the ledger, because that row is what the consuming gates
   read.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from conftest import load_script_module

from _build_parse import Issue, UnitTestSummary
from _build_result import KILLED_MESSAGE, STATUS_INDETERMINATE, STATUS_KILLED
from _build_shared import cmd_run_common

import _build_shared as _build_shared_mod
import _ledger_core


# ---------------------------------------------------------------------------
# The three conditions under test, as the wrapper-shaped results that reach the
# emit choke point. Held as a table so a new condition cannot be added without
# declaring what each property below expects of it.
# ---------------------------------------------------------------------------

_KILLED = 'killed'
_TIMEOUT = 'timeout'
_RED = 'error'


def _make_result(status, exit_code, *, error=None, message=None):
    """Build the DirectCommandResult shape ``cmd_run_common`` consumes."""
    result = {
        'status': status,
        'exit_code': exit_code,
        'duration_seconds': 42,
        'log_file': '/tmp/non-finish-test.log',
        'command': './pw verify',
        'timeout_used_seconds': 330,
    }
    if error is not None:
        result['error'] = error
    if message is not None:
        result['message'] = message
    return result


_INDETERMINATE = 'indeterminate'

_CONDITIONS = {
    _KILLED: _make_result('killed', -9, error='killed', message=KILLED_MESSAGE),
    _TIMEOUT: _make_result('timeout', -1, error='timeout'),
    _RED: _make_result('error', 1, error='build_failed'),
    _INDETERMINATE: _make_result(
        'indeterminate', -1, error='indeterminate', message="daemon reported 'quiesced'"
    ),
}

#: The two NON-FINISHES. Neither reported a verdict, so neither may be
#: presented as the other and neither may be presented as a failing build.
_NON_FINISHES = (_KILLED, _TIMEOUT)

#: Every status that must be kept OFF the build-failure path. The two
#: non-finishes plus the undetermined outcome: none of the three carries a
#: verdict, so none may have findings stored or an ``errors[]`` row synthesised
#: on its behalf.
_NOT_A_FAILURE = (_KILLED, _TIMEOUT, _INDETERMINATE)


def _failing_parser(log_file):
    """A parser that finds real test failures in the log."""
    issues = [
        Issue(
            file='test/test_thing.py',
            line=10,
            message='assert 1 == 2',
            severity='error',
            category='test_failure',
        ),
    ]
    return issues, UnitTestSummary(passed=5, failed=1, skipped=0, total=6), 'FAILURE'


def _empty_parser(log_file):
    """A parser that extracts nothing — the truncated-log case."""
    return [], None, 'FAILURE'


def _green_suite_parser(log_file):
    """A parser whose log shows the suite finished green before the kill."""
    return [], UnitTestSummary(passed=6, failed=0, skipped=0, total=6), 'SUCCESS'


# ===========================================================================
# Seam 1 — the in-process classifier
# ===========================================================================


class TestExecuteClassifiesSignalDeath:
    """``execute_direct_base`` separates a signal death from a failing build."""

    @staticmethod
    def _run(returncode, run_config_mock):
        """Drive ``execute_direct_base`` against a child with ``returncode``."""
        _build_execute = load_script_module(
            'plan-marshall',
            'script-shared',
            'build/_build_execute.py',
            '_build_execute_for_non_finish',
        )
        run_config_mock.timeout_get.return_value = 330

        completed = MagicMock()
        completed.returncode = returncode

        with (
            patch.object(_build_execute, 'timeout_get', run_config_mock.timeout_get),
            patch.object(_build_execute, 'timeout_set', run_config_mock.timeout_set),
            patch.object(_build_execute, 'create_log_file', return_value='/tmp/kill-test.log'),
            patch.object(_build_execute, 'log_entry'),
            patch.object(_build_execute, 'subprocess') as subprocess_mock,
        ):
            subprocess_mock.run.return_value = completed
            return _build_execute.execute_direct_base(
                args='verify',
                command_key='python:verify',
                default_timeout=300,
                project_dir='.',
                tool_name='python',
                build_command_fn=lambda w, a, lf: ([w, a], f'{w} {a}'),
                wrapper='./pw',
                plan_id='non-finish-test-plan',
            )

    @pytest.mark.parametrize('signal_number', [9, 15, 2])
    def test_negative_returncode_is_killed_not_error(self, signal_number):
        """A child killed by a signal is ``killed`` — never a red build."""
        run_config = MagicMock()
        result = self._run(-signal_number, run_config)

        assert result['status'] == STATUS_KILLED
        assert result['status'] != 'error'
        assert result['exit_code'] == -signal_number
        assert result['message'] == KILLED_MESSAGE

    def test_killed_run_does_not_teach_the_adaptive_learner(self):
        """A truncated elapsed is not a measurement, so it is never persisted."""
        run_config = MagicMock()
        self._run(-9, run_config)

        run_config.timeout_set.assert_not_called()

    # --- matched control: a genuinely failing build ------------------------

    def test_control_positive_returncode_is_still_error(self):
        """CONTROL: a build that ran and failed must still report ``error``."""
        run_config = MagicMock()
        result = self._run(1, run_config)

        assert result['status'] == 'error'
        assert result['status'] != STATUS_KILLED
        assert result['exit_code'] == 1

    def test_control_failing_build_still_teaches_the_learner(self):
        """CONTROL: a failing build DID finish, so its duration is a measurement."""
        run_config = MagicMock()
        self._run(1, run_config)

        run_config.timeout_set.assert_called_once()

    def test_control_successful_build_still_teaches_the_learner(self):
        """CONTROL: the success path is untouched by the kill carve-out."""
        run_config = MagicMock()
        result = self._run(0, run_config)

        assert result['status'] == 'success'
        run_config.timeout_set.assert_called_once()


# ===========================================================================
# Seam 2 — the emit choke point
# ===========================================================================


class TestEmitChokePointKeepsTheThreeApart:
    """``cmd_run_common`` renders each condition as itself."""

    @pytest.mark.parametrize('condition', [_KILLED, _TIMEOUT, _RED, _INDETERMINATE])
    def test_status_is_rendered_verbatim(self, condition, capsys):
        """Each condition's own status reaches stdout — none is folded away."""
        cmd_run_common(_CONDITIONS[condition], _empty_parser, 'python')
        stdout = capsys.readouterr().out

        assert f'status: {condition}' in stdout

    def test_indeterminate_carries_its_reason(self, capsys):
        """The only actionable content an undetermined result has is WHY."""
        cmd_run_common(_CONDITIONS[_INDETERMINATE], _empty_parser, 'python')
        stdout = capsys.readouterr().out

        assert 'status: indeterminate' in stdout
        assert 'quiesced' in stdout

    def test_kill_is_not_presented_as_a_timeout(self, capsys):
        """The two non-finishes are not interchangeable."""
        cmd_run_common(_CONDITIONS[_KILLED], _empty_parser, 'python')
        stdout = capsys.readouterr().out

        assert 'status: killed' in stdout
        assert 'status: timeout' not in stdout

    def test_timeout_is_not_presented_as_a_kill(self, capsys):
        """The discrimination holds in the other direction too."""
        cmd_run_common(_CONDITIONS[_TIMEOUT], _empty_parser, 'python')
        stdout = capsys.readouterr().out

        assert 'status: timeout' in stdout
        assert 'status: killed' not in stdout

    def test_kill_carries_the_no_blind_retry_message(self, capsys):
        """The kill's remedy must reach the consumer, not just its status."""
        cmd_run_common(_CONDITIONS[_KILLED], _empty_parser, 'python')
        stdout = capsys.readouterr().out

        assert 'not flaky, do not blind-retry' in stdout

    @pytest.mark.parametrize('condition', _NOT_A_FAILURE)
    def test_non_failure_synthesises_no_error_row(self, condition, capsys):
        """A log that proves nothing must not be turned into a fabricated failure."""
        cmd_run_common(_CONDITIONS[condition], _empty_parser, 'python')
        stdout = capsys.readouterr().out

        assert 'errors[' not in stdout
        assert 'no structured errors were parsed' not in stdout

    @pytest.mark.parametrize('condition', _NOT_A_FAILURE)
    def test_non_failure_stores_no_findings(self, condition):
        """No verdict was reported, so no findings are produced."""
        with patch.object(_build_shared_mod, '_store_build_findings') as store:
            cmd_run_common(
                _CONDITIONS[condition],
                _failing_parser,
                'python',
                plan_id='non-finish-test-plan',
            )

        store.assert_not_called()

    @pytest.mark.parametrize('condition', _NOT_A_FAILURE)
    def test_non_failure_drops_a_failure_carrying_summary(self, condition, capsys):
        """Partial failures from an interrupted run are not the suite's verdict."""
        cmd_run_common(_CONDITIONS[condition], _failing_parser, 'python')
        stdout = capsys.readouterr().out

        assert 'tests:' not in stdout

    def test_kill_preserves_the_bound_that_did_not_fire(self, capsys):
        """`timeout_used_seconds` is diagnostic on a kill: how much headroom was left."""
        cmd_run_common(_CONDITIONS[_KILLED], _empty_parser, 'python')
        stdout = capsys.readouterr().out

        assert 'timeout_used_seconds: 330' in stdout

    @pytest.mark.parametrize('condition', _NON_FINISHES)
    def test_non_finish_keeps_a_zero_failure_summary(self, condition, capsys):
        """A suite that finished green before the kill is diagnosable evidence."""
        cmd_run_common(_CONDITIONS[condition], _green_suite_parser, 'python')
        stdout = capsys.readouterr().out

        assert 'tests:' in stdout
        assert 'passed: 6' in stdout

    # --- matched control: a genuinely failing build ------------------------

    def test_control_red_build_still_reports_its_errors(self, capsys):
        """CONTROL: a real failure still surfaces its parsed errors."""
        cmd_run_common(_CONDITIONS[_RED], _failing_parser, 'python')
        stdout = capsys.readouterr().out

        assert 'status: error' in stdout
        assert 'errors[' in stdout
        assert 'assert 1 == 2' in stdout

    def test_control_red_build_still_synthesises_a_row_when_parsing_finds_none(self, capsys):
        """CONTROL: the safety net that keeps status and errors[] consistent stands."""
        cmd_run_common(_CONDITIONS[_RED], _empty_parser, 'python')
        stdout = capsys.readouterr().out

        assert 'status: error' in stdout
        assert 'no structured errors were parsed' in stdout

    def test_control_red_build_still_stores_findings(self):
        """CONTROL: the producer-side finding store still fires on a real failure."""
        with patch.object(
            _build_shared_mod, '_store_build_findings', return_value=(1, 1, [])
        ) as store:
            cmd_run_common(
                _CONDITIONS[_RED],
                _failing_parser,
                'python',
                plan_id='non-finish-test-plan',
            )

        store.assert_called_once()


# ===========================================================================
# Seam 3 — the routed (daemon) leg
# ===========================================================================


class TestDaemonVerdictSurvivesTheMapping:
    """The daemon already classifies correctly; the client must not undo it."""

    @staticmethod
    def _map(job_status, **extra):
        factory = load_script_module(
            'plan-marshall',
            'script-shared',
            'build/_build_execute_factory.py',
            '_build_execute_factory_for_non_finish',
        )
        waited = {
            'job_status': job_status,
            'log_file': '/tmp/routed.log',
            'duration_seconds': 42,
            'exit_code': -9 if job_status == 'killed' else 1,
        }
        waited.update(extra)
        return factory._daemon_result_to_direct(waited, './pw verify')

    def test_daemon_killed_maps_to_killed(self):
        """A daemon-side kill arrives as ``killed``, not as a build failure."""
        result = self._map('killed')

        assert result['status'] == STATUS_KILLED
        assert result['status'] != 'error'
        assert result['message'] == KILLED_MESSAGE

    def test_daemon_message_wins_over_the_shared_default(self):
        """The daemon's own wording is preserved when it supplied one."""
        result = self._map('killed', message='reaped by the harness')

        assert result['message'] == 'reaped by the harness'

    def test_daemon_timeout_maps_to_timeout(self):
        """The timeout leg is unchanged and still distinct from the kill leg."""
        result = self._map('timeout')

        assert result['status'] == 'timeout'
        assert result['status'] != STATUS_KILLED

    def test_unrecognised_job_status_is_indeterminate_not_error(self):
        """A version-skewed daemon is not evidence that the build failed."""
        result = self._map('quiesced')

        assert result['status'] == STATUS_INDETERMINATE
        assert result['status'] != 'error'
        assert 'quiesced' in result['message']

    # --- matched control: a genuinely failing routed build -----------------

    def test_control_daemon_failure_still_maps_to_error(self):
        """CONTROL: only the daemon's ``failure`` becomes a red build."""
        result = self._map('failure')

        assert result['status'] == 'error'
        assert result['error'] == 'build_failed'


class TestCrossCheckPreservesTheLogVerdict:
    """The `job_status: success` cross-check must not flatten what it catches.

    The daemon can report `success` while the job log says otherwise — that is
    the whole reason the cross-check exists. What the log says is one of the
    wrapper's three non-green values, and returning a flat `error` for all three
    would make the backstop itself the collapse: a routed timeout and a routed
    INNER kill (the wrapper survived, its build child was signalled) would both
    arrive at every gate as a red build, through the very code that exists to
    catch a routed false signal.
    """

    @staticmethod
    def _map_with_log_verdict(verdict_status, exit_code=-9):
        factory = load_script_module(
            'plan-marshall',
            'script-shared',
            'build/_build_execute_factory.py',
            '_build_execute_factory_for_non_finish',
        )
        verdict = None
        if verdict_status is not None:
            verdict = SimpleNamespace(status=verdict_status, exit_code=exit_code)
        with patch.object(factory, 'read_log_verdict', return_value=verdict):
            return factory._daemon_result_to_direct(
                {
                    'job_status': 'success',
                    'log_file': '/tmp/routed.log',
                    'duration_seconds': 42,
                    'exit_code': 0,
                },
                './pw verify',
            )

    def test_log_killed_survives_the_cross_check(self):
        result = self._map_with_log_verdict('killed')

        assert result['status'] == STATUS_KILLED
        assert result['status'] != 'error'
        assert result['message'] == KILLED_MESSAGE

    def test_log_timeout_survives_the_cross_check(self):
        result = self._map_with_log_verdict('timeout', exit_code=-1)

        assert result['status'] == 'timeout'
        assert result['status'] != 'error'

    def test_log_status_outside_the_vocabulary_is_indeterminate(self):
        result = self._map_with_log_verdict('speculative')

        assert result['status'] == STATUS_INDETERMINATE
        assert 'speculative' in result['message']

    # --- matched controls --------------------------------------------------

    def test_control_log_error_still_fails_the_build(self):
        """CONTROL: the cross-check still catches a genuinely failing build."""
        result = self._map_with_log_verdict('error', exit_code=2)

        assert result['status'] == 'error'
        assert result['error'] == 'build_failed'
        assert result['exit_code'] == 2

    def test_control_agreeing_verdict_keeps_success(self):
        """CONTROL: a log that agrees does not downgrade a green build."""
        result = self._map_with_log_verdict('success', exit_code=0)

        assert result['status'] == 'success'

    def test_control_absent_verdict_keeps_success(self):
        """CONTROL: a non-wrapper command with no parseable TOON stays green."""
        result = self._map_with_log_verdict(None)

        assert result['status'] == 'success'


class TestDaemonNarrowingPreservesTheLogVerdict:
    """`run_job`'s exit-0-not-sufficient narrowing must keep WHICH non-green.

    Server-side mirror of the class above. The wrapper running inside the daemon
    child exits 0 and reports its verdict in the TOON, so `classify_terminal`
    says `success` and the narrowing decides the wire status. Hard-coding
    `failure` there re-collapses at the daemon exactly what the wrapper
    distinguished.
    """

    @staticmethod
    def _narrow(verdict_status, exit_code=-9):
        supervisor = load_script_module(
            'plan-marshall',
            'manage-build-server',
            '_marshalld_supervisor.py',
            '_marshalld_supervisor_for_non_finish',
        )
        verdict = SimpleNamespace(status=verdict_status, exit_code=exit_code)
        # Exercise the narrowing arithmetic directly: classify_terminal(0) is
        # `success`, and the wire status is the verdict's own, translated.
        assert supervisor.classify_terminal(0, timed_out=False) == 'success'
        return supervisor.wire_status_from_result(verdict.status)

    def test_log_killed_narrows_to_wire_killed(self):
        assert self._narrow('killed') == 'killed'

    def test_log_timeout_narrows_to_wire_timeout(self):
        assert self._narrow('timeout') == 'timeout'

    # --- matched control ---------------------------------------------------

    def test_control_log_error_still_narrows_to_wire_failure(self):
        """CONTROL: a real failure still becomes the wire `failure`."""
        assert self._narrow('error') == 'failure'

    def test_control_supervisor_own_kill_outranks_log_content(self):
        """CONTROL: the supervisor's OWN legs are not subject to the narrowing."""
        supervisor = load_script_module(
            'plan-marshall',
            'manage-build-server',
            '_marshalld_supervisor.py',
            '_marshalld_supervisor_for_non_finish',
        )
        assert supervisor.classify_terminal(-9, timed_out=False) == 'killed'
        assert supervisor.classify_terminal(0, timed_out=True) == 'timeout'
        assert supervisor.classify_terminal(1, timed_out=False) == 'failure'


# ===========================================================================
# Seam 4 — the ledger, which is what the consuming gates actually read
# ===========================================================================


class TestKilledReachesTheLedger:
    """A wrapper-observed kill must be stampable, or no gate can ever see it."""

    def test_killed_is_wrapper_claimable(self):
        """The wrapper reaped the child first-hand, exactly as for ``timeout``."""
        assert 'killed' in _ledger_core.WRAPPER_CLAIMABLE_BUILD_STATUSES

    def test_unknown_stays_derived_only(self):
        """``unknown`` records an ABSENCE of evidence — a wrapper cannot claim it."""
        assert 'unknown' in _ledger_core.DERIVED_ONLY_BUILD_STATUSES
        assert 'unknown' not in _ledger_core.WRAPPER_CLAIMABLE_BUILD_STATUSES

    def test_the_vocabulary_is_unchanged(self):
        """Widening what is claimable must not widen the vocabulary itself."""
        assert _ledger_core.BUILD_STATUSES == {
            'success',
            'error',
            'timeout',
            'killed',
            'unknown',
        }

    # --- matched control ---------------------------------------------------

    def test_control_success_and_error_remain_claimable(self):
        """CONTROL: the pre-existing claimable statuses are untouched."""
        assert 'success' in _ledger_core.WRAPPER_CLAIMABLE_BUILD_STATUSES
        assert 'error' in _ledger_core.WRAPPER_CLAIMABLE_BUILD_STATUSES
        assert 'timeout' in _ledger_core.WRAPPER_CLAIMABLE_BUILD_STATUSES
