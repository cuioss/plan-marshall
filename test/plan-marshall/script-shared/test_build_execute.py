#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _build_execute.py shared execution module.

Tests execute_direct_base() with various capture strategies, timeout handling,
adaptive timeout learning, error conditions, and parameter injection.
"""

import subprocess
import tempfile
from unittest.mock import MagicMock, mock_open, patch

from _build_execute import CaptureStrategy, execute_direct_base


def _build_command_fn(wrapper, args, log_file):
    """Test build command function that returns predictable command parts."""
    cmd_parts = [wrapper] + args.split()
    command_str = f'{wrapper} {args}'
    return cmd_parts, command_str


def _scope_fn(args):
    """Test scope function that extracts first arg as scope."""
    parts = args.split()
    return parts[0] if parts else 'default'


def _call_execute(
    args='clean verify',
    command_key='test:verify',
    default_timeout=300,
    capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
    scope_fn=None,
    env_vars=None,
    working_dir=None,
    extra_result_fields=None,
    project_dir=None,
):
    """Call execute_direct_base with sensible test defaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pd = project_dir or tmpdir
        return execute_direct_base(
            args=args,
            command_key=command_key,
            default_timeout=default_timeout,
            project_dir=pd,
            tool_name='test',
            build_command_fn=_build_command_fn,
            wrapper='/usr/bin/test-tool',
            capture_strategy=capture_strategy,
            scope_fn=scope_fn,
            env_vars=env_vars,
            working_dir=working_dir,
            extra_result_fields=extra_result_fields,
        )


class TestStdoutRedirectSuccess:
    """Tests for successful execution with STDOUT_REDIRECT strategy."""

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_success_returns_status_success(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        result = _call_execute()

        assert result['status'] == 'success'
        assert result['exit_code'] == 0

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_success_includes_log_file(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        result = _call_execute()

        assert result['log_file'] == '/tmp/test.log'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_success_includes_command_string(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        result = _call_execute(args='clean verify')

        assert result['command'] == '/usr/bin/test-tool clean verify'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_success_records_timeout_used(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        result = _call_execute()

        assert result['timeout_used_seconds'] == 300

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_success_calls_timeout_set_with_duration(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        _call_execute(command_key='test:verify')

        mock_tset.assert_called_once()
        call_args = mock_tset.call_args
        assert call_args[0][0] == 'test:verify'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_stdout_redirect_opens_log_file(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        with patch('builtins.open', mock_open()) as mocked_open:
            _call_execute(capture_strategy=CaptureStrategy.STDOUT_REDIRECT)
            mocked_open.assert_called_once_with('/tmp/test.log', 'w')


class TestMavenLogFlagSuccess:
    """Tests for successful execution with TOOL_LOG_FLAG strategy."""

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_maven_flag_uses_capture_output_false(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        _call_execute(capture_strategy=CaptureStrategy.TOOL_LOG_FLAG)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['capture_output'] is False

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_maven_flag_does_not_open_log_file(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        with patch('builtins.open', mock_open()) as mocked_open:
            _call_execute(capture_strategy=CaptureStrategy.TOOL_LOG_FLAG)
            mocked_open.assert_not_called()

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_maven_flag_success_returns_status(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        result = _call_execute(capture_strategy=CaptureStrategy.TOOL_LOG_FLAG)

        assert result['status'] == 'success'
        assert result['exit_code'] == 0


class TestBuildFailure:
    """Tests for non-zero exit code handling."""

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_failure_returns_error_status(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=1)

        result = _call_execute()

        assert result['status'] == 'error'
        assert result['exit_code'] == 1

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_failure_includes_error_message(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=1)

        result = _call_execute()

        assert 'error' in result
        assert 'exit code 1' in result['error']

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_failure_still_records_duration(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=1)

        result = _call_execute()

        assert 'duration_seconds' in result
        mock_tset.assert_called_once()


class TestTimeoutHandling:
    """Tests for subprocess.TimeoutExpired handling."""

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='test', timeout=300))
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_timeout_returns_timeout_status(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute()

        assert result['status'] == 'timeout'
        assert result['exit_code'] == -1

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='test', timeout=300))
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_timeout_includes_error_message(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute()

        assert 'timed out after 300 seconds' in result['error']

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='test', timeout=300))
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_timeout_doubles_timeout_for_learning(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        _call_execute(command_key='test:verify')

        # Adaptive learning doubles the timeout on a timeout (300 -> 600).
        mock_tset.assert_called_once_with('test:verify', 600, mock_tset.call_args[0][2])

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='test', timeout=300))
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_timeout_logs_error(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        _call_execute()

        mock_log.assert_called_once()
        log_args = mock_log.call_args[0]
        assert log_args[2] == 'ERROR'
        assert 'Timeout' in log_args[3]


class TestFileNotFoundError:
    """Tests for missing wrapper/executable."""

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run', side_effect=FileNotFoundError())
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_file_not_found_returns_error(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute()

        assert result['status'] == 'error'
        assert result['exit_code'] == -1

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run', side_effect=FileNotFoundError())
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_file_not_found_error_message(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute()

        assert 'not found' in result['error']
        assert '/usr/bin/test-tool' in result['error']

    @patch('_build_execute.log_entry')
    @patch('_build_execute.subprocess.run', side_effect=FileNotFoundError())
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_file_not_found_does_not_set_timeout(self, mock_log_file, mock_tget, mock_run, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        with patch('_build_execute.timeout_set') as mock_tset:
            _call_execute()
            mock_tset.assert_not_called()

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run', side_effect=FileNotFoundError())
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_file_not_found_duration_is_zero(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute()

        assert result['duration_seconds'] == 0


class TestOSError:
    """Tests for general OS errors during execution."""

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run', side_effect=OSError('Permission denied'))
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_os_error_returns_error_status(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute()

        assert result['status'] == 'error'
        assert result['exit_code'] == -1

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run', side_effect=OSError('Permission denied'))
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_os_error_includes_message(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute()

        assert result['error'] == 'Permission denied'

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run', side_effect=OSError('Permission denied'))
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_os_error_logs_error(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        _call_execute()

        mock_log.assert_called_once()
        log_args = mock_log.call_args[0]
        assert 'OS error' in log_args[3]


class TestLogFileFailure:
    """Tests for log file creation failure."""

    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file', return_value=None)
    def test_log_file_failure_returns_error(self, mock_log_file, mock_tget):
        result = _call_execute()

        assert result['status'] == 'error'
        assert result['exit_code'] == -1

    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file', return_value=None)
    def test_log_file_failure_error_message(self, mock_log_file, mock_tget):
        result = _call_execute()

        assert result['error'] == 'Failed to create log file'

    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file', return_value=None)
    def test_log_file_failure_empty_log_path(self, mock_log_file, mock_tget):
        result = _call_execute()

        assert result['log_file'] == ''

    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file', return_value=None)
    def test_log_file_failure_empty_command(self, mock_log_file, mock_tget):
        result = _call_execute()

        assert result['command'] == ''


class TestCustomScopeFn:
    """Tests for custom scope function."""

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_custom_scope_fn_called_with_args(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        _call_execute(args='core-api verify', scope_fn=_scope_fn)

        mock_log_file.assert_called_once()
        call_args = mock_log_file.call_args[0]
        assert call_args[1] == 'core-api'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_default_scope_fn_returns_default(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        _call_execute(args='clean verify', scope_fn=None)

        mock_log_file.assert_called_once()
        call_args = mock_log_file.call_args[0]
        assert call_args[1] == 'default'


class TestEnvVarsInjection:
    """Tests for environment variable injection."""

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_env_vars_passed_to_subprocess(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        _call_execute(env_vars={'JAVA_HOME': '/usr/lib/jvm/java-17'})

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['env'] is not None
        assert call_kwargs['env']['JAVA_HOME'] == '/usr/lib/jvm/java-17'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_no_env_vars_passes_none(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        _call_execute(env_vars=None)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['env'] is None


class TestMinTimeoutEnforcement:
    """Tests for global minimum timeout floor (MIN_TIMEOUT=60)."""

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=30)
    @patch('_build_execute.create_log_file')
    def test_floor_enforced_when_learned_too_low(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        result = _call_execute()

        # Learned timeout 30 is below the global floor of 60, so 60 wins.
        assert result['timeout_used_seconds'] == 60

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=120)
    @patch('_build_execute.create_log_file')
    def test_floor_no_effect_when_learned_higher(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        result = _call_execute()

        # Learned timeout 120 is above the floor of 60, so 120 is used.
        assert result['timeout_used_seconds'] == 120


class TestExtraResultFields:
    """Tests for extra_result_fields injection into all result paths."""

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_extras_in_success_result(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        result = _call_execute(extra_result_fields={'wrapper': './mvnw', 'mode': 'full'})

        assert result['wrapper'] == './mvnw'
        assert result['mode'] == 'full'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_extras_in_error_result(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=1)

        result = _call_execute(extra_result_fields={'wrapper': './mvnw'})

        assert result['status'] == 'error'
        assert result['wrapper'] == './mvnw'

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='test', timeout=300))
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_extras_in_timeout_result(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute(extra_result_fields={'wrapper': './mvnw'})

        assert result['status'] == 'timeout'
        assert result['wrapper'] == './mvnw'

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run', side_effect=FileNotFoundError())
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_extras_in_file_not_found_result(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute(extra_result_fields={'wrapper': './mvnw'})

        assert result['status'] == 'error'
        assert result['wrapper'] == './mvnw'

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run', side_effect=OSError('denied'))
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_extras_in_os_error_result(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute(extra_result_fields={'wrapper': './mvnw'})

        assert result['status'] == 'error'
        assert result['wrapper'] == './mvnw'

    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file', return_value=None)
    def test_extras_in_log_file_failure_result(self, mock_log_file, mock_tget):
        result = _call_execute(extra_result_fields={'wrapper': './mvnw'})

        assert result['status'] == 'error'
        assert result['wrapper'] == './mvnw'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_no_extras_omits_extra_fields(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        result = _call_execute(extra_result_fields=None)

        assert 'wrapper' not in result


class TestCaptureStrategyEnum:
    """Tests for CaptureStrategy enum values."""

    def test_stdout_redirect_value(self):
        assert CaptureStrategy.STDOUT_REDIRECT.value == 'stdout_redirect'

    def test_tool_log_flag_value(self):
        assert CaptureStrategy.TOOL_LOG_FLAG.value == 'tool_log_flag'

    def test_enum_has_two_members(self):
        assert len(CaptureStrategy) == 2


class TestWorkingDir:
    """Tests for working directory override."""

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_custom_working_dir_passed_to_subprocess(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        _call_execute(working_dir='/custom/dir')

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['cwd'] == '/custom/dir'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_no_working_dir_uses_project_dir(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            execute_direct_base(
                args='verify',
                command_key='test:verify',
                default_timeout=300,
                project_dir=tmpdir,
                tool_name='test',
                build_command_fn=_build_command_fn,
                wrapper='/usr/bin/test-tool',
                capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
            )

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs['cwd'] == tmpdir


class TestProjectDirPropagation:
    """Tests verifying --project-dir propagates to subprocess cwd.

    These regression-proof the worktree handling: when a plan runs in an
    isolated worktree, callers pass --project-dir so subprocess.run uses the
    correct cwd instead of inheriting the agent's working directory.
    """

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_project_dir_propagates_to_subprocess_cwd(self, mock_log_file, mock_tget, mock_run, mock_tset):
        """The explicit project_dir must become subprocess.run's cwd."""
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            _call_execute(project_dir=tmpdir)

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs['cwd'] == tmpdir

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_project_dir_default_dot_propagates(self, mock_log_file, mock_tget, mock_run, mock_tset):
        """When CLI default '.' is passed, subprocess inherits '.' as cwd."""
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        execute_direct_base(
            args='verify',
            command_key='test:verify',
            default_timeout=300,
            project_dir='.',
            tool_name='test',
            build_command_fn=_build_command_fn,
            wrapper='/usr/bin/test-tool',
            capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
        )

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['cwd'] == '.'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_working_dir_overrides_project_dir_for_cwd(self, mock_log_file, mock_tget, mock_run, mock_tset):
        """Explicit working_dir should win over project_dir for subprocess cwd."""
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            _call_execute(project_dir=tmpdir, working_dir='/custom/override')

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs['cwd'] == '/custom/override'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute.subprocess.run')
    @patch('_build_execute.timeout_get', return_value=300)
    @patch('_build_execute.create_log_file')
    def test_project_dir_absolute_path_propagates(self, mock_log_file, mock_tget, mock_run, mock_tset):
        """Absolute worktree-style paths must round-trip to subprocess cwd unchanged."""
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = MagicMock(returncode=0)

        worktree_path = '/Users/test/.claude/worktrees/some-plan'
        execute_direct_base(
            args='verify',
            command_key='test:verify',
            default_timeout=300,
            project_dir=worktree_path,
            tool_name='test',
            build_command_fn=_build_command_fn,
            wrapper='/usr/bin/test-tool',
            capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
        )

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['cwd'] == worktree_path


# ``execute_direct_base`` itself is a Bucket B foundation primitive; it accepts
# the resolved ``project_dir`` as a string and uses it as the subprocess ``cwd``.
# The two-state contract is enforced by the layer above (``build_main`` via
# ``resolve_project_dir``), so these tests simply lock in that any path the
# resolver returns is honoured by execute_direct_base.


def test_execute_direct_base_honours_resolved_worktree_path(monkeypatch):
    """A ``project_dir`` resolved from --plan-id must propagate to subprocess cwd.

    Mirrors the production flow: build_main rewrites args.project_dir to
    the worktree path returned by resolve_project_dir, then the handler
    calls execute_direct_base with that value. The subprocess cwd must
    match exactly so the build runs against the worktree, not the main
    checkout.
    """
    import resolve_project_dir as _routing
    from resolve_project_dir import resolve_project_dir

    # Patch the manage-status helper to return a deterministic path.
    monkeypatch.setattr(_routing, '_query_worktree_path', lambda _pid: (True, '/tmp/wt-resolved'))
    resolved = resolve_project_dir('task-routing-canonical', '.', default='.')
    assert resolved.endswith('wt-resolved')

    with tempfile.TemporaryDirectory():
        with patch('subprocess.run') as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_run.return_value = mock_proc

            execute_direct_base(
                args='verify',
                command_key='test:routing',
                default_timeout=300,
                project_dir=resolved,
                tool_name='test',
                build_command_fn=_build_command_fn,
                wrapper='/usr/bin/test-tool',
                capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
            )

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs['cwd'] == resolved, (
                f'subprocess cwd must match the resolver output {resolved!r}, '
                f'got {call_kwargs["cwd"]!r}'
            )


def test_execute_direct_base_honours_main_checkout_fallback(monkeypatch):
    """When the resolver falls back to the main checkout, execute_direct_base honours it."""
    import resolve_project_dir as _routing
    from resolve_project_dir import resolve_project_dir

    monkeypatch.setattr(_routing, '_main_checkout_root', lambda: '/tmp/main-stub')
    resolved = resolve_project_dir(None, '.', default='.')
    assert resolved == '/tmp/main-stub'

    with tempfile.TemporaryDirectory():
        with patch('subprocess.run') as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_run.return_value = mock_proc

            execute_direct_base(
                args='verify',
                command_key='test:fallback',
                default_timeout=300,
                project_dir=resolved,
                tool_name='test',
                build_command_fn=_build_command_fn,
                wrapper='/usr/bin/test-tool',
                capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
            )

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs['cwd'] == '/tmp/main-stub'


def test_execute_direct_base_preserves_explicit_project_dir(monkeypatch):
    """Pre-existing --project-dir-only callers must keep working.

    The legacy escape-hatch flow: the caller supplies an explicit
    ``project_dir`` string, the resolver returns it verbatim, and the
    subprocess cwd uses it directly.
    """
    from resolve_project_dir import resolve_project_dir

    resolved = resolve_project_dir(None, '/tmp/explicit-cwd', default='.')
    assert resolved.endswith('explicit-cwd')

    with tempfile.TemporaryDirectory():
        with patch('subprocess.run') as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_run.return_value = mock_proc

            execute_direct_base(
                args='verify',
                command_key='test:explicit',
                default_timeout=300,
                project_dir=resolved,
                tool_name='test',
                build_command_fn=_build_command_fn,
                wrapper='/usr/bin/test-tool',
                capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
            )

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs['cwd'] == resolved
