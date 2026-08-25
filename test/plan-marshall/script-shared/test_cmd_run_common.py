# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for cmd_run_common() shared logic.

Tests the centralized cmd_run routing that replaces duplicated code
across Maven, Gradle, npm, and Python build skills.
"""

from unittest.mock import patch

import _build_parse as _build_parse_mod
import _build_shared as _build_shared_mod

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


class TestCmdRunCommonSuccess:
    """Tests for successful build result routing."""

    def test_success_returns_zero(self):
        result = _make_result(status='success')
        rc = cmd_run_common(result, _noop_parser, 'maven')
        assert rc == 0

    def test_success_prints_toon_output(self, capsys):
        result = _make_result(status='success')
        cmd_run_common(result, _noop_parser, 'maven')
        stdout = capsys.readouterr().out
        assert 'success' in stdout

    def test_success_prints_exec_to_stderr(self, capsys):
        result = _make_result(status='success', command='./mvnw clean verify')
        cmd_run_common(result, _noop_parser, 'maven')
        stderr = capsys.readouterr().err
        assert '[EXEC] ./mvnw clean verify' in stderr


class TestCmdRunCommonTimeout:
    """Tests for timeout result routing."""

    def test_timeout_returns_zero(self):
        """Timeout is modeled in TOON output, not exit code."""
        result = _make_result(status='timeout', exit_code=-1, error='timed out', timeout_used=300)
        rc = cmd_run_common(result, _noop_parser, 'maven')
        assert rc == 0

    def test_timeout_prints_timeout_status(self, capsys):
        result = _make_result(status='timeout', exit_code=-1, error='timed out', timeout_used=300)
        cmd_run_common(result, _noop_parser, 'maven')
        stdout = capsys.readouterr().out
        assert 'timeout' in stdout


class TestCmdRunCommonExecutionError:
    """Tests for execution error routing (wrapper not found, log file failed)."""

    def test_execution_error_returns_one(self):
        result = _make_result(status='error', exit_code=-1, error='Maven wrapper not found')
        rc = cmd_run_common(result, _noop_parser, 'maven')
        assert rc == 1

    def test_log_file_error_detected(self, capsys):
        result = _make_result(status='error', exit_code=-1, error='Failed to create log file')
        cmd_run_common(result, _noop_parser, 'maven')
        stdout = capsys.readouterr().out
        assert 'log_file' in stdout


class TestCmdRunCommonBuildFailure:
    """Tests for build failure with log parsing."""

    def test_build_failure_returns_zero(self):
        """Build failure is modeled in TOON output, not exit code."""
        result = _make_result(status='error', exit_code=1, error='Build failed')
        rc = cmd_run_common(result, _error_parser, 'maven')
        assert rc == 0

    def test_build_failure_includes_errors_in_output(self, capsys):
        result = _make_result(status='error', exit_code=1, error='Build failed')
        cmd_run_common(result, _error_parser, 'maven')
        stdout = capsys.readouterr().out
        assert 'cannot find symbol' in stdout

    def test_build_failure_includes_test_summary(self, capsys):
        result = _make_result(status='error', exit_code=1, error='Build failed')
        cmd_run_common(result, _error_parser, 'maven')
        stdout = capsys.readouterr().out
        assert 'passed' in stdout
        assert '5' in stdout

    def test_parser_exception_still_returns_zero(self):
        """If parser raises, cmd_run_common still returns 0 — status modeled in output."""

        def broken_parser(log_file):
            raise RuntimeError('parser crashed')

        result = _make_result(status='error', exit_code=1, error='Build failed')
        rc = cmd_run_common(result, broken_parser, 'maven')
        assert rc == 0

    def test_parser_exception_prints_error_output(self, capsys):
        """If parser raises, output still contains build_failed."""

        def broken_parser(log_file):
            raise RuntimeError('parser crashed')

        result = _make_result(status='error', exit_code=1, error='Build failed')
        cmd_run_common(result, broken_parser, 'maven')
        stdout = capsys.readouterr().out
        assert 'build_failed' in stdout


class TestCmdRunCommonParserNeedsCommand:
    """Tests for parser_needs_command=True (npm-style parsers)."""

    def test_command_passed_to_parser(self, capsys):
        result = _make_result(status='error', exit_code=1, error='Build failed', command='npm run test')
        cmd_run_common(result, _command_parser, 'npm', parser_needs_command=True)
        stdout = capsys.readouterr().out
        assert 'error in npm run test' in stdout


class TestCmdRunCommonOutputFormat:
    """Tests for output format selection (toon vs json)."""

    def test_json_format_produces_json(self, capsys):
        result = _make_result(status='success')
        cmd_run_common(result, _noop_parser, 'maven', output_format='json')
        stdout = capsys.readouterr().out
        assert '"status"' in stdout
        assert '"success"' in stdout

    def test_toon_format_produces_colon_space(self, capsys):
        result = _make_result(status='success')
        cmd_run_common(result, _noop_parser, 'maven', output_format='toon')
        stdout = capsys.readouterr().out
        assert 'status: success' in stdout


class TestCmdRunCommonModeFiltering:
    """Tests for mode-based warning filtering."""

    def test_errors_mode_suppresses_warnings(self, capsys):
        result = _make_result(status='error', exit_code=1, error='Build failed')
        cmd_run_common(result, _error_parser, 'maven', mode='errors')
        stdout = capsys.readouterr().out
        assert 'cannot find symbol' in stdout
        assert 'deprecated API' not in stdout


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

    def test_green_build_with_plan_id_terminalizes_pending_findings(self):
        """Build succeeds + pending findings present → reconciliation runs and
        bulk-resolves the pending findings (mocked reconciler reports a non-zero
        resolved count)."""
        result = _make_result(status='success', command='./pw verify')

        with patch.object(_build_shared_mod, '_reconcile_pending_build_findings') as mock_reconcile:
            mock_reconcile.return_value = 3  # three stale findings terminalized
            rc = cmd_run_common(
                result, _noop_parser, 'python', plan_id='my-plan', command_args='verify'
            )

        assert rc == 0
        # `verify` performs all three analyses; _noop_parser reports no test
        # summary, so the count for a TEST-BEARING gate is unknown — not zero.
        mock_reconcile.assert_called_once_with(
            plan_id='my-plan',
            command_str='./pw verify',
            analyses=frozenset({'compile', 'lint', 'test'}),
            tests_run=None,
        )

    def test_green_build_without_command_args_reports_an_unknown_population(self):
        """The fail-closed default. A caller that supplies no canonical args
        hands the reconciler an UNKNOWN population — never a silently
        full-entitlement one — so nothing is cleared on no evidence."""
        result = _make_result(status='success', command='./pw verify')

        with patch.object(_build_shared_mod, '_reconcile_pending_build_findings') as mock_reconcile:
            mock_reconcile.return_value = 0
            rc = cmd_run_common(result, _noop_parser, 'python', plan_id='my-plan')

        assert rc == 0
        mock_reconcile.assert_called_once_with(
            plan_id='my-plan', command_str='./pw verify', analyses=None, tests_run=None
        )

    def test_failing_build_does_not_terminalize_findings(self):
        """Build fails → pending findings are NOT terminalized (the failure they
        recorded is still live)."""
        result = _make_result(status='error', exit_code=1, error='Build failed')

        with patch.object(_build_shared_mod, '_reconcile_pending_build_findings') as mock_reconcile:
            rc = cmd_run_common(result, _error_parser, 'python', plan_id='my-plan')

        assert rc == 0
        mock_reconcile.assert_not_called()

    def test_green_build_with_no_pending_findings_is_noop(self):
        """Build succeeds + nothing pending → reconciliation is invoked but
        resolves zero findings (no-op), and cmd_run_common still returns 0
        cleanly."""
        result = _make_result(status='success', command='./pw compile')

        with patch.object(_build_shared_mod, '_reconcile_pending_build_findings') as mock_reconcile:
            mock_reconcile.return_value = 0  # nothing was pending
            rc = cmd_run_common(
                result, _noop_parser, 'python', plan_id='my-plan', command_args='compile'
            )

        assert rc == 0
        # A non-test gate with no summary genuinely executed zero tests: this
        # zero is MEASURED, and is the matched half of the unknown above.
        mock_reconcile.assert_called_once_with(
            plan_id='my-plan',
            command_str='./pw compile',
            analyses=frozenset({'compile'}),
            tests_run=0,
        )

    def test_green_build_that_ran_tests_passes_executed_count(self):
        """A green build whose parser reports executed tests routes the non-zero
        executed-test count into the reconciler — the evidence that lets it clear
        a test-failure finding (see test_build_findings_store.py for the split)."""
        result = _make_result(status='success', command='./pw verify')

        with patch.object(_build_shared_mod, '_reconcile_pending_build_findings') as mock_reconcile:
            mock_reconcile.return_value = 1
            rc = cmd_run_common(
                result, _tests_ran_parser, 'python', plan_id='my-plan', command_args='verify'
            )

        assert rc == 0
        mock_reconcile.assert_called_once_with(
            plan_id='my-plan',
            command_str='./pw verify',
            analyses=frozenset({'compile', 'lint', 'test'}),
            tests_run=5,
        )

    def test_green_build_without_plan_id_skips_reconciliation(self):
        """No plan_id supplied → reconciliation is skipped entirely (preserves
        the historical non-plan silent behaviour on the green path)."""
        result = _make_result(status='success', command='./pw verify')

        with patch.object(_build_shared_mod, '_reconcile_pending_build_findings') as mock_reconcile:
            rc = cmd_run_common(result, _noop_parser, 'python', plan_id=None)

        assert rc == 0
        mock_reconcile.assert_not_called()


class TestCmdRunCommonPublishesItsPopulation:
    """The emitted success result names what the run examined — and OMITS the
    executed-test count when it was never measured, so a consumer reading
    ``tests_run`` cannot read an unmeasured run as one that tested nothing."""

    def test_measured_zero_publishes_the_count_and_the_discriminator(self, capsys):
        result = _make_result(status='success', command='./pw compile')
        cmd_run_common(result, _noop_parser, 'python', command_args='compile')
        stdout = capsys.readouterr().out

        assert 'tests_population: measured' in stdout
        assert 'tests_run: 0' in stdout
        assert 'analyses_examined: compile' in stdout

    def test_unmeasured_count_omits_the_key_entirely(self, capsys):
        # The matched negative: a TEST-bearing gate whose summary did not parse.
        # `tests_run` must be absent, not zero — absence is what stops a consumer
        # from reading "tested nothing" off an unmeasured run.
        result = _make_result(status='success', command='./pw module-tests')
        cmd_run_common(result, _noop_parser, 'python', command_args='module-tests')
        stdout = capsys.readouterr().out

        assert 'tests_population: unmeasured' in stdout
        assert 'tests_run' not in stdout

    def test_unknown_command_publishes_an_unknown_analysis_population(self, capsys):
        result = _make_result(status='success', command='./pw publish')
        cmd_run_common(result, _noop_parser, 'python', command_args='publish')
        stdout = capsys.readouterr().out

        assert 'analyses_examined: unknown' in stdout
        assert 'tests_population: unmeasured' in stdout

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
