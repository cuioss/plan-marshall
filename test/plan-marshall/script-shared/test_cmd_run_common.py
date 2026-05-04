"""Tests for cmd_run_common() shared logic.

Tests the centralized cmd_run routing that replaces duplicated code
across Maven, Gradle, npm, and Python build skills.
"""

# Tier 2 direct imports via importlib for uniform import style
import importlib.util  # noqa: E402
from pathlib import Path

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

# =============================================================================
# Fixtures
# =============================================================================


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


# =============================================================================
# Tests: Success path
# =============================================================================


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


# =============================================================================
# Tests: Timeout path
# =============================================================================


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


# =============================================================================
# Tests: Execution error path (exit_code == -1)
# =============================================================================


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


# =============================================================================
# Tests: Build failure path (parsing)
# =============================================================================


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


# =============================================================================
# Tests: parser_needs_command flag
# =============================================================================


class TestCmdRunCommonParserNeedsCommand:
    """Tests for parser_needs_command=True (npm-style parsers)."""

    def test_command_passed_to_parser(self, capsys):
        result = _make_result(status='error', exit_code=1, error='Build failed', command='npm run test')
        cmd_run_common(result, _command_parser, 'npm', parser_needs_command=True)
        stdout = capsys.readouterr().out
        assert 'error in npm run test' in stdout


# =============================================================================
# Tests: Output format selection
# =============================================================================


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


# =============================================================================
# Tests: Mode filtering
# =============================================================================


class TestCmdRunCommonModeFiltering:
    """Tests for mode-based warning filtering."""

    def test_errors_mode_suppresses_warnings(self, capsys):
        result = _make_result(status='error', exit_code=1, error='Build failed')
        cmd_run_common(result, _error_parser, 'maven', mode='errors')
        stdout = capsys.readouterr().out
        # Errors should be present, warnings should not
        assert 'cannot find symbol' in stdout
        assert 'deprecated API' not in stdout
