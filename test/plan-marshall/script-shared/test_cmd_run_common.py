# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for cmd_run_common() shared logic.

Tests the centralized cmd_run routing that replaces duplicated code
across Maven, Gradle, npm, and Python build skills.
"""

from unittest.mock import patch

import _build_parse as _build_parse_mod
import _build_shared as _build_shared_mod
import pytest

Issue = _build_parse_mod.Issue
UnitTestSummary = _build_parse_mod.UnitTestSummary
cmd_run_common = _build_shared_mod.cmd_run_common


def _make_result(
    status='success',
    exit_code=0,
    duration=10,
    log_file='/tmp/test.log',
    command='./mvnw verify',
    error=None,
    timeout_used=300,
):
    """Create a DirectCommandResult-like dict."""
    result = {
        'status': status,
        'exit_code': exit_code,
        'duration_seconds': duration,
        'log_file': log_file,
        'command': command,
        'timeout_used_seconds': timeout_used,
    }
    if error:
        result['error'] = error
    return result


def _noop_parser(log_file):
    """Parser that returns no issues."""
    return [], None, 'FAILURE'


def _error_parser(log_file):
    """Parser that returns compilation errors."""
    issues = [
        Issue(
            file='src/Main.java', line=10, message='cannot find symbol', severity='error', category='compilation_error'
        ),
        Issue(
            file='src/Main.java', line=20, message='deprecated API', severity='warning', category='deprecation_warning'
        ),
    ]
    return issues, UnitTestSummary(passed=5, failed=1, skipped=0, total=6), 'FAILURE'


def _tests_ran_parser(log_file):
    """Parser for a green build that actually executed tests (total > 0)."""
    return [], UnitTestSummary(passed=5, failed=0, skipped=0, total=5), 'success'


def _command_parser(log_file, command):
    """Parser that needs command string (npm-style)."""
    issues = [
        Issue(file='src/app.js', line=5, message=f'error in {command}', severity='error', category='compilation_error'),
    ]
    return issues, None, 'FAILURE'


def _broken_parser(log_file):
    """Parser that raises — the routing must survive it and still report."""
    raise RuntimeError('parser crashed')


#: The three build outcomes the routing distinguishes, built once and shared by
#: the exit-code and stdout tables so the two read as views of the same set.
_SUCCESS_RESULT = _make_result(status='success')
_TIMEOUT_RESULT = _make_result(status='timeout', exit_code=-1, error='timed out', timeout_used=300)
_WRAPPER_MISSING_RESULT = _make_result(status='error', exit_code=-1, error='Maven wrapper not found')
_LOG_FILE_FAILED_RESULT = _make_result(status='error', exit_code=-1, error='Failed to create log file')
_BUILD_FAILED_RESULT = _make_result(status='error', exit_code=1, error='Build failed')


#: ``(result, parser, exit code)``. Only an EXECUTION error — the build never
#: ran — exits non-zero; a timeout and a red build are modelled in the emitted
#: output, so the caller's exit code stays 0.
_EXIT_CODE_CASES = [
    (_SUCCESS_RESULT, _noop_parser, 0),
    (_TIMEOUT_RESULT, _noop_parser, 0),
    (_WRAPPER_MISSING_RESULT, _noop_parser, 1),
    (_BUILD_FAILED_RESULT, _error_parser, 0),
    (_BUILD_FAILED_RESULT, _broken_parser, 0),
]

_EXIT_CODE_IDS = [
    'green-build',
    'timed-out-build',
    'execution-error-the-build-never-ran',
    'red-build-with-a-parseable-log',
    'red-build-whose-parser-raised',
]


@pytest.mark.parametrize('result,parser,expected_rc', _EXIT_CODE_CASES, ids=_EXIT_CODE_IDS)
def test_cmd_run_common_exit_code(result, parser, expected_rc):
    # A copy per row: the result dicts are shared between the tables below, and
    # the routing enriches the payload it is handed.
    assert cmd_run_common(dict(result), parser, 'maven') == expected_rc


#: ``(result, parser, extra keyword arguments, fragments stdout must carry,
#: fragments stdout must NOT carry)``. Every row is the same call and the same
#: two-way substring check; only the build being reported and what its emitted
#: output must say vary.
_STDOUT_CASES = [
    (_SUCCESS_RESULT, _noop_parser, {}, ['success'], []),
    (_TIMEOUT_RESULT, _noop_parser, {}, ['timeout'], []),
    (_LOG_FILE_FAILED_RESULT, _noop_parser, {}, ['log_file'], []),
    (_BUILD_FAILED_RESULT, _error_parser, {}, ['cannot find symbol'], []),
    (_BUILD_FAILED_RESULT, _error_parser, {}, ['passed', '5'], []),
    (_BUILD_FAILED_RESULT, _broken_parser, {}, ['build_failed'], []),
    (
        _make_result(status='error', exit_code=1, error='Build failed', command='npm run test'),
        _command_parser,
        {'parser_needs_command': True},
        ['error in npm run test'],
        [],
    ),
    (_SUCCESS_RESULT, _noop_parser, {'output_format': 'json'}, ['"status"', '"success"'], []),
    (_SUCCESS_RESULT, _noop_parser, {'output_format': 'toon'}, ['status: success'], []),
    (
        _BUILD_FAILED_RESULT,
        _error_parser,
        {'mode': 'errors'},
        ['cannot find symbol'],
        ['deprecated API'],
    ),
]

_STDOUT_IDS = [
    'green-build-reports-success',
    'timeout-reports-its-status',
    'log-file-failure-names-the-field',
    'red-build-carries-the-parsed-error',
    'red-build-carries-the-test-summary',
    'a-raising-parser-still-reports-build_failed',
    'a-command-taking-parser-receives-the-command',
    'json-format',
    'toon-format',
    'errors-mode-suppresses-warnings',
]


@pytest.mark.parametrize('result,parser,kwargs,present,absent', _STDOUT_CASES, ids=_STDOUT_IDS)
def test_cmd_run_common_stdout(capsys, result, parser, kwargs, present, absent):
    cmd_run_common(dict(result), parser, 'maven', **kwargs)

    stdout = capsys.readouterr().out
    for fragment in present:
        assert fragment in stdout, stdout
    for fragment in absent:
        assert fragment not in stdout, stdout


def test_success_prints_exec_to_stderr(capsys):
    """The command line itself is echoed to stderr, not into the result payload."""
    result = _make_result(status='success', command='./mvnw clean verify')

    cmd_run_common(result, _noop_parser, 'maven')

    assert '[EXEC] ./mvnw clean verify' in capsys.readouterr().err


#: ``(result, parser, cmd_run_common kwargs, the reconciler's mocked resolved
#: count, the keyword arguments it must be called with — ``None`` meaning it must
#: not be called at all)``. The two ``None`` rows are the guards: a red build's
#: findings are still live, and a plan-less build has no store to reconcile.
_RECONCILIATION_CASES = [
    (
        _make_result(status='success', command='./pw verify'),
        _noop_parser,
        {'plan_id': 'my-plan', 'command_args': 'verify'},
        3,
        {
            'plan_id': 'my-plan',
            'command_str': './pw verify',
            'analyses': frozenset({'compile', 'lint', 'test'}),
            'tests_run': None,
        },
    ),
    (
        _make_result(status='success', command='./pw verify'),
        _noop_parser,
        {'plan_id': 'my-plan'},
        0,
        {
            'plan_id': 'my-plan',
            'command_str': './pw verify',
            'analyses': None,
            'tests_run': None,
        },
    ),
    (
        _make_result(status='success', command='./pw compile'),
        _noop_parser,
        {'plan_id': 'my-plan', 'command_args': 'compile'},
        0,
        {
            'plan_id': 'my-plan',
            'command_str': './pw compile',
            'analyses': frozenset({'compile'}),
            'tests_run': 0,
        },
    ),
    (
        _make_result(status='success', command='./pw verify'),
        _tests_ran_parser,
        {'plan_id': 'my-plan', 'command_args': 'verify'},
        1,
        {
            'plan_id': 'my-plan',
            'command_str': './pw verify',
            'analyses': frozenset({'compile', 'lint', 'test'}),
            'tests_run': 5,
        },
    ),
    (_BUILD_FAILED_RESULT, _error_parser, {'plan_id': 'my-plan'}, 0, None),
    (
        _make_result(status='success', command='./pw verify'),
        _noop_parser,
        {'plan_id': None},
        0,
        None,
    ),
]

_RECONCILIATION_IDS = [
    'test-bearing-gate-with-no-summary-reports-an-unknown-count',
    'no-command-args-reports-an-unknown-analysis-population',
    'non-test-gate-with-no-summary-reports-a-measured-zero',
    'a-gate-that-ran-tests-reports-the-executed-count',
    'a-red-build-reconciles-nothing',
    'a-plan-less-build-reconciles-nothing',
]


class TestCmdRunCommonGreenBuildReconciliation:
    """A green build run terminalizes the pending build findings it was ENTITLED
    to clear, passing the examined-analysis population and the executed-test
    count so the reconciler can decide what that entitlement covers.

    ``cmd_run_common`` delegates the bulk-resolve to
    ``_reconcile_pending_build_findings`` (which itself calls
    ``resolve_findings_by_type``). These tests pin the routing contract at the
    ``cmd_run_common`` boundary: reconciliation fires on the green path when a
    ``plan_id`` is supplied, carries BOTH population facts derived from
    ``command_args``, never fires on a failing build, and is a clean no-op when
    nothing is pending. The reconciler's own entitlement rule — a type is cleared
    only when the run performed an analysis that reaches it — is covered against
    the real findings store in ``test_build_findings_store.py``, and the pure
    derivation in ``test_build_examined_population.py``.
    """

    @pytest.mark.parametrize(
        'result,parser,kwargs,reconciled_count,expected_call',
        _RECONCILIATION_CASES,
        ids=_RECONCILIATION_IDS,
    )
    def test_reconciliation_routing(self, result, parser, kwargs, reconciled_count, expected_call):
        with patch.object(_build_shared_mod, '_reconcile_pending_build_findings') as mock_reconcile:
            mock_reconcile.return_value = reconciled_count
            rc = cmd_run_common(dict(result), parser, 'python', **kwargs)

        assert rc == 0
        if expected_call is None:
            mock_reconcile.assert_not_called()
        else:
            mock_reconcile.assert_called_once_with(**expected_call)


#: ``(canonical command args, fragments stdout must carry, fragments it must
#: NOT)``. The absent ``tests_run`` in the middle row is the load-bearing one:
#: absence is what stops a consumer reading "tested nothing" off a run whose
#: count was never measured.
_POPULATION_STDOUT_CASES = [
    (
        'compile',
        ['tests_population: measured', 'tests_run: 0', 'analyses_examined: compile'],
        [],
    ),
    ('module-tests', ['tests_population: unmeasured'], ['tests_run']),
    (
        'publish',
        ['analyses_examined: unknown', 'tests_population: unmeasured'],
        [],
    ),
]

_POPULATION_STDOUT_IDS = [
    'non-test-gate-publishes-a-measured-zero',
    'test-bearing-gate-with-no-summary-omits-the-count',
    'unrecognised-command-publishes-an-unknown-population',
]


class TestCmdRunCommonPublishesItsPopulation:
    """The emitted success result names what the run examined — and OMITS the
    executed-test count when it was never measured, so a consumer reading
    ``tests_run`` cannot read an unmeasured run as one that tested nothing."""

    @pytest.mark.parametrize('command_args,present,absent', _POPULATION_STDOUT_CASES, ids=_POPULATION_STDOUT_IDS)
    def test_the_published_population(self, capsys, command_args, present, absent):
        result = _make_result(status='success', command=f'./pw {command_args}')

        cmd_run_common(result, _noop_parser, 'python', command_args=command_args)

        stdout = capsys.readouterr().out
        for fragment in present:
            assert fragment in stdout, stdout
        for fragment in absent:
            assert fragment not in stdout, stdout

    def test_stderr_names_the_refusal_cause_when_nothing_is_clearable(self, capsys):
        result = _make_result(status='success', command='./pw publish')
        cmd_run_common(result, _noop_parser, 'python', command_args='publish')
        stderr = capsys.readouterr().err

        assert 'no pending finding cleared (population_unknown)' in stderr

    def test_stderr_carries_no_refusal_note_when_something_is_clearable(self, capsys):
        # Matched positive: the same line, a build that IS entitled to clear —
        # so the refusal note above is shown to be conditional, not boilerplate.
        result = _make_result(status='success', command='./pw compile')
        cmd_run_common(result, _noop_parser, 'python', command_args='compile')
        stderr = capsys.readouterr().err

        assert 'analyses examined: compile' in stderr
        assert 'no pending finding cleared' not in stderr
