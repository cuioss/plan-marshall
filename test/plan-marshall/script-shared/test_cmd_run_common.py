"""Tests for cmd_run_common() shared logic.

Tests the centralized cmd_run routing that replaces duplicated code
across Maven, Gradle, npm, and Python build skills.
"""

import importlib.util
from pathlib import Path
from unittest.mock import patch

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'script-shared'
    / 'scripts'
    / 'build'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_build_parse_mod = _load_module('_build_parse', '_build_parse.py')
_build_shared_mod = _load_module('_build_shared', '_build_shared.py')

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
    """A green build run terminalizes any pending build findings from a prior
    failing run.

    ``cmd_run_common`` delegates the bulk-resolve to
    ``_reconcile_pending_build_findings`` (which itself calls
    ``resolve_findings_by_type``). These tests pin the routing contract at the
    ``cmd_run_common`` boundary: reconciliation fires on the green path when a
    ``plan_id`` is supplied, never fires on a failing build, and is a clean
    no-op when nothing is pending. The reconciler's internals (the actual
    ``resolve_findings_by_type`` integration) are covered end-to-end against the
    real findings store in ``test_build_findings_store.py``.
    """

    def test_green_build_with_plan_id_terminalizes_pending_findings(self):
        """Build succeeds + pending findings present → reconciliation runs and
        bulk-resolves the pending findings (mocked reconciler reports a non-zero
        resolved count)."""
        result = _make_result(status='success', command='./pw verify')

        with patch.object(_build_shared_mod, '_reconcile_pending_build_findings') as mock_reconcile:
            mock_reconcile.return_value = 3  # three stale findings terminalized
            rc = cmd_run_common(result, _noop_parser, 'python', plan_id='my-plan')

        assert rc == 0
        mock_reconcile.assert_called_once_with(plan_id='my-plan', command_str='./pw verify')

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
        result = _make_result(status='success', command='./pw verify')

        with patch.object(_build_shared_mod, '_reconcile_pending_build_findings') as mock_reconcile:
            mock_reconcile.return_value = 0  # nothing was pending
            rc = cmd_run_common(result, _noop_parser, 'python', plan_id='my-plan')

        assert rc == 0
        mock_reconcile.assert_called_once_with(plan_id='my-plan', command_str='./pw verify')

    def test_green_build_without_plan_id_skips_reconciliation(self):
        """No plan_id supplied → reconciliation is skipped entirely (preserves
        the historical non-plan silent behaviour on the green path)."""
        result = _make_result(status='success', command='./pw verify')

        with patch.object(_build_shared_mod, '_reconcile_pending_build_findings') as mock_reconcile:
            rc = cmd_run_common(result, _noop_parser, 'python', plan_id=None)

        assert rc == 0
        mock_reconcile.assert_not_called()
