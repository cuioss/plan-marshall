#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _build_execute.py shared execution module.

Tests execute_direct_base() with various capture strategies, timeout handling,
adaptive timeout learning, the explicit-timeout override (and the engine floor
that still binds it), error conditions, and parameter injection.
"""

import contextlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from unittest.mock import MagicMock, call, mock_open, patch

import _build_execute
import pytest
from _build_execute import MAX_TIMEOUT, MIN_TIMEOUT, CaptureStrategy, execute_direct_base
from _resolve_project_dir_fixtures import worktree_query_result
from marketplace_paths import NO_PLAN_SENTINEL

from conftest import load_script_module


def _build_command_fn(wrapper, args, log_file):
    """Test build command function that returns predictable command parts."""
    cmd_parts = [wrapper] + args.split()
    command_str = f'{wrapper} {args}'
    return cmd_parts, command_str


def _scope_fn(args):
    """Test scope function that extracts first arg as scope."""
    parts = args.split()
    return parts[0] if parts else 'default'


#: Plan id the shared helper attributes its builds to. Every result the
#: primitive produces belongs to a plan, so the helper names one explicitly
#: rather than defaulting the attribution away.
_PLAN_ID = 'build-execute-test-plan'

#: The path every mocked ``create_log_file`` hands back.
_LOG_FILE = '/tmp/test.log'


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
    explicit_timeout=None,
    min_timeout=MIN_TIMEOUT,
    plan_id=_PLAN_ID,
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
            plan_id=plan_id,
            capture_strategy=capture_strategy,
            scope_fn=scope_fn,
            env_vars=env_vars,
            working_dir=working_dir,
            extra_result_fields=extra_result_fields,
            explicit_timeout=explicit_timeout,
            min_timeout=min_timeout,
        )


#: ``(result key, expected value)`` for ONE successful STDOUT_REDIRECT run. The
#: invocation is identical for every row — only the field of the result being
#: read varies — so the table replaces four copies of the same call.
_SUCCESS_RESULT_FIELDS = [
    ('status', 'success'),
    ('exit_code', 0),
    ('log_file', _LOG_FILE),
    ('command', '/usr/bin/test-tool clean verify'),
    ('timeout_used_seconds', 300),
]

_SUCCESS_RESULT_FIELD_IDS = [key for key, _expected in _SUCCESS_RESULT_FIELDS]


class TestStdoutRedirectSuccess:
    """Tests for successful execution with STDOUT_REDIRECT strategy."""

    @pytest.mark.parametrize('key,expected', _SUCCESS_RESULT_FIELDS, ids=_SUCCESS_RESULT_FIELD_IDS)
    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_success_result_carries_the_field(self, mock_log_file, mock_tget, mock_run, mock_tset, key, expected):
        mock_log_file.return_value = _LOG_FILE
        mock_run.return_value = 0

        result = _call_execute(args='clean verify')

        assert result[key] == expected

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_success_calls_timeout_set_with_duration(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        _call_execute(command_key='test:verify')

        mock_tset.assert_called_once()
        call_args = mock_tset.call_args
        assert call_args[0][0] == 'test:verify'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_stdout_redirect_opens_log_file(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        with patch('builtins.open', mock_open()) as mocked_open:
            _call_execute(capture_strategy=CaptureStrategy.STDOUT_REDIRECT)
            mocked_open.assert_called_once_with('/tmp/test.log', 'w')


class TestMavenLogFlagSuccess:
    """Tests for successful execution with TOOL_LOG_FLAG strategy."""

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_maven_flag_leaves_output_uncaptured(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        _call_execute(capture_strategy=CaptureStrategy.TOOL_LOG_FLAG)

        # The tool writes its own log, so the child inherits both streams.
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['stdout'] is None
        assert call_kwargs['stderr'] is None

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_maven_flag_does_not_open_log_file(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        with patch('builtins.open', mock_open()) as mocked_open:
            _call_execute(capture_strategy=CaptureStrategy.TOOL_LOG_FLAG)
            mocked_open.assert_not_called()

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_maven_flag_success_returns_status(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        result = _call_execute(capture_strategy=CaptureStrategy.TOOL_LOG_FLAG)

        assert result['status'] == 'success'
        assert result['exit_code'] == 0


class TestBuildFailure:
    """Tests for non-zero exit code handling."""

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_failure_returns_error_status(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 1

        result = _call_execute()

        assert result['status'] == 'error'
        assert result['exit_code'] == 1

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_failure_includes_error_message(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 1

        result = _call_execute()

        assert 'error' in result
        assert 'exit code 1' in result['error']

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_failure_still_records_duration(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 1

        result = _call_execute()

        assert 'duration_seconds' in result
        mock_tset.assert_called_once()


class TestTimeoutHandling:
    """Tests for subprocess.TimeoutExpired handling."""

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded', side_effect=subprocess.TimeoutExpired(cmd='test', timeout=300))
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_timeout_returns_timeout_status(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute()

        assert result['status'] == 'timeout'
        assert result['exit_code'] == -1

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded', side_effect=subprocess.TimeoutExpired(cmd='test', timeout=300))
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_timeout_includes_error_message(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute()

        assert 'timed out after 300 seconds' in result['error']

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded', side_effect=subprocess.TimeoutExpired(cmd='test', timeout=300))
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_timeout_doubles_timeout_for_learning(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        _call_execute(command_key='test:verify')

        # Adaptive learning doubles the timeout on a timeout (300 -> 600).
        mock_tset.assert_called_once_with('test:verify', 600, mock_tset.call_args[0][2])

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded', side_effect=subprocess.TimeoutExpired(cmd='test', timeout=300))
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
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
    @patch('_build_execute._run_bounded', side_effect=FileNotFoundError())
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_file_not_found_returns_error(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute()

        assert result['status'] == 'error'
        assert result['exit_code'] == -1

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded', side_effect=FileNotFoundError())
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_file_not_found_error_message(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute()

        assert 'not found' in result['error']
        assert '/usr/bin/test-tool' in result['error']

    @patch('_build_execute.log_entry')
    @patch('_build_execute._run_bounded', side_effect=FileNotFoundError())
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_file_not_found_does_not_set_timeout(self, mock_log_file, mock_tget, mock_run, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        with patch('_build_execute.timeout_set') as mock_tset:
            _call_execute()
            mock_tset.assert_not_called()

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded', side_effect=FileNotFoundError())
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_file_not_found_duration_is_zero(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute()

        assert result['duration_seconds'] == 0


class TestOSError:
    """Tests for general OS errors during execution."""

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded', side_effect=OSError('Permission denied'))
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_os_error_returns_error_status(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute()

        assert result['status'] == 'error'
        assert result['exit_code'] == -1

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded', side_effect=OSError('Permission denied'))
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_os_error_includes_message(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        result = _call_execute()

        assert result['error'] == 'Permission denied'

    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded', side_effect=OSError('Permission denied'))
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_os_error_logs_error(self, mock_log_file, mock_tget, mock_run, mock_tset, mock_log):
        mock_log_file.return_value = '/tmp/test.log'

        _call_execute()

        mock_log.assert_called_once()
        log_args = mock_log.call_args[0]
        assert 'OS error' in log_args[3]


#: ``(result key, expected value)`` for the early return taken when the log file
#: could not be created. The empty ``log_file`` and ``command`` are the two that
#: say the build never started, rather than started and produced nothing.
_LOG_FILE_FAILURE_RESULT_FIELDS = [
    ('status', 'error'),
    ('exit_code', -1),
    ('error', 'Failed to create log file'),
    ('log_file', ''),
    ('command', ''),
]

_LOG_FILE_FAILURE_RESULT_FIELD_IDS = [key for key, _expected in _LOG_FILE_FAILURE_RESULT_FIELDS]


class TestLogFileFailure:
    """Tests for log file creation failure."""

    @pytest.mark.parametrize(
        'key,expected',
        _LOG_FILE_FAILURE_RESULT_FIELDS,
        ids=_LOG_FILE_FAILURE_RESULT_FIELD_IDS,
    )
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file', return_value=None)
    def test_log_file_failure_result_carries_the_field(self, mock_log_file, mock_tget, key, expected):
        result = _call_execute()

        assert result[key] == expected


class TestCustomScopeFn:
    """Tests for custom scope function."""

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_custom_scope_fn_called_with_args(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        _call_execute(args='core-api verify', scope_fn=_scope_fn)

        mock_log_file.assert_called_once()
        call_args = mock_log_file.call_args[0]
        assert call_args[1] == 'core-api'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_default_scope_fn_returns_default(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        _call_execute(args='clean verify', scope_fn=None)

        mock_log_file.assert_called_once()
        call_args = mock_log_file.call_args[0]
        assert call_args[1] == 'default'


class TestPlanIdReachesCreateLogFile:
    """``plan_id`` threads from the primitive's signature into ``create_log_file``.

    This is the lower of the two layers the attribution has to survive: the
    caller hands ``execute_direct_base`` a plan id, and the log placement call
    must receive that exact id as a keyword. Asserting on the constructed call
    (rather than on a resulting path) pins the forwarding itself, so a layer
    that silently drops the id cannot pass by coincidence of a shared default.
    """

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_plan_id_forwarded_as_keyword(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        _call_execute(plan_id='owning-plan')

        mock_log_file.assert_called_once()
        assert mock_log_file.call_args.kwargs['plan_id'] == 'owning-plan'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_sentinel_plan_id_is_forwarded_unchanged(self, mock_log_file, mock_tget, mock_run, mock_tset):
        """A plan-less build forwards the sentinel, never an empty string."""
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        _call_execute(plan_id=NO_PLAN_SENTINEL)

        assert mock_log_file.call_args.kwargs['plan_id'] == NO_PLAN_SENTINEL

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_plan_id_is_independent_of_project_dir(self, mock_log_file, mock_tget, mock_run, mock_tset):
        """Attribution follows the plan, not the directory the build runs in.

        The relocation's whole point: ``project_dir`` still selects the
        subprocess cwd, while ``plan_id`` alone selects where the result lands.
        """
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            _call_execute(project_dir=tmpdir, plan_id='owning-plan')

        assert mock_log_file.call_args.kwargs['plan_id'] == 'owning-plan'
        assert tmpdir not in str(mock_log_file.call_args)

    def test_plan_id_is_required(self):
        """Omitting ``plan_id`` is a TypeError — the attribution has no default."""
        with pytest.raises(TypeError):
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


class TestEnvVarsInjection:
    """Tests for environment variable injection."""

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_env_vars_passed_to_subprocess(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        _call_execute(env_vars={'JAVA_HOME': '/usr/lib/jvm/java-17'})

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['env'] is not None
        assert call_kwargs['env']['JAVA_HOME'] == '/usr/lib/jvm/java-17'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_no_env_vars_passes_none(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        _call_execute(env_vars=None)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['env'] is None


class TestMinTimeoutEnforcement:
    """Tests for global minimum timeout floor (MIN_TIMEOUT=60)."""

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(30, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_floor_enforced_when_learned_too_low(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        result = _call_execute()

        # Learned timeout 30 is below the global floor of 60, so 60 wins.
        assert result['timeout_used_seconds'] == 60

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(120, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_floor_no_effect_when_learned_higher(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        result = _call_execute()

        # Learned timeout 120 is above the floor of 60, so 120 is used.
        assert result['timeout_used_seconds'] == 120


class TestExplicitTimeoutOverride:
    """The ``explicit_timeout`` override at the ``execute_direct_base`` seam.

    An explicitly-supplied bound is a true override of the persisted learned
    value: it reaches the launch helper's ``timeout_seconds`` argument, and no
    learned value may reduce it. It does NOT waive the engine's declared ``min_timeout`` floor.
    """

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(1800, 'explicit'))
    @patch('_build_execute.create_log_file')
    def test_explicit_override_is_forwarded_to_the_resolver(self, mock_log_file, mock_tget, mock_run, mock_tset):
        """The explicit bound is handed to timeout_resolve as the override argument."""
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        _call_execute(command_key='test:verify', default_timeout=300, explicit_timeout=1800)

        # (command_key, default, project_dir, explicit)
        assert mock_tget.call_args[0][0] == 'test:verify'
        assert mock_tget.call_args[0][1] == 300
        assert mock_tget.call_args[0][3] == 1800

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(1800, 'explicit'))
    @patch('_build_execute.create_log_file')
    def test_explicit_override_reaches_the_subprocess_timeout_argument(
        self, mock_log_file, mock_tget, mock_run, mock_tset
    ):
        """The resolved override is the value the build launch is bounded by."""
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        result = _call_execute(explicit_timeout=1800)

        assert mock_run.call_args[1]['timeout_seconds'] == 1800
        assert result['timeout_used_seconds'] == 1800

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_absent_override_still_consults_the_resolver(self, mock_log_file, mock_tget, mock_run, mock_tset):
        """Without an override the learned path is unchanged (explicit stays None)."""
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        result = _call_execute(command_key='test:verify', default_timeout=300)

        mock_tget.assert_called_once()
        assert mock_tget.call_args[0][3] is None
        assert mock_run.call_args[1]['timeout_seconds'] == 300
        assert result['timeout_used_seconds'] == 300

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(120, 'explicit'))
    @patch('_build_execute.create_log_file')
    def test_engine_floor_still_binds_a_below_floor_explicit_override(
        self, mock_log_file, mock_tget, mock_run, mock_tset
    ):
        """A below-floor explicit request resolves UP to the engine floor.

        The floor protects against under-specification, so the override wins over
        the learned value but never below ``min_timeout``.
        """
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        result = _call_execute(explicit_timeout=120, min_timeout=600)

        assert mock_run.call_args[1]['timeout_seconds'] == 600
        assert result['timeout_used_seconds'] == 600


class TestExplicitOverrideAgainstRealRunConfig:
    """End-to-end: the override beats a REAL persisted learned value.

    ``timeout_resolve`` is NOT mocked here — the persisted value is written into an
    isolated ``run-configuration.json`` so the property under test is the actual
    resolution the production path performs. This is the case that is red against
    the pre-change code, where a persisted value discarded the caller's bound.
    """

    @staticmethod
    def _isolate_run_config(tmp_path, monkeypatch, persisted_seconds):
        """Point run-configuration.json at ``tmp_path`` with one persisted value."""
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        monkeypatch.setenv('PLAN_DIR_NAME', '.plan')
        import file_ops

        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        config = {'version': 1, 'commands': {'test:verify': {'timeout_seconds': persisted_seconds}}}
        (tmp_path / 'run-configuration.json').write_text(json.dumps(config))

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.create_log_file')
    def test_explicit_override_beats_a_real_persisted_value(
        self, mock_log_file, mock_run, mock_tset, tmp_path, monkeypatch
    ):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0
        # Persisted 240 resolves to 240 * 1.25 = 300 on the learned path.
        self._isolate_run_config(tmp_path, monkeypatch, 240)

        result = _call_execute(command_key='test:verify', default_timeout=300, explicit_timeout=1800)

        assert mock_run.call_args[1]['timeout_seconds'] == 1800
        assert result['timeout_used_seconds'] == 1800

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.create_log_file')
    def test_no_override_resolves_the_real_learned_value(
        self, mock_log_file, mock_run, mock_tset, tmp_path, monkeypatch
    ):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0
        self._isolate_run_config(tmp_path, monkeypatch, 240)

        result = _call_execute(command_key='test:verify', default_timeout=300)

        # 240 * 1.25 = 300 — the learned path is unchanged.
        assert result['timeout_used_seconds'] == 300


#: ``(subprocess returncode, subprocess side effect, create_log_file return,
#: expected status)`` — one row per result path ``execute_direct_base`` can
#: take. Extras must survive every one of them, so the set is an ENUMERATION of
#: the paths rather than a sample: a path added without a row here would return
#: a result the injection was never checked against.
_RESULT_PATHS = [
    (0, None, _LOG_FILE, 'success'),
    (1, None, _LOG_FILE, 'error'),
    (-signal.SIGKILL, None, _LOG_FILE, 'killed'),
    (None, subprocess.TimeoutExpired(cmd='test', timeout=300), _LOG_FILE, 'timeout'),
    (None, FileNotFoundError(), _LOG_FILE, 'error'),
    (None, OSError('denied'), _LOG_FILE, 'error'),
    (0, None, None, 'error'),
]

_RESULT_PATH_IDS = [
    'build-succeeded',
    'build-exited-non-zero',
    'build-killed-by-signal',
    'build-timed-out',
    'wrapper-executable-not-found',
    'os-error-during-execution',
    'log-file-could-not-be-created',
]


class TestExtraResultFields:
    """Tests for extra_result_fields injection into all result paths."""

    @pytest.mark.parametrize(
        'returncode,side_effect,log_file,expected_status',
        _RESULT_PATHS,
        ids=_RESULT_PATH_IDS,
    )
    @patch('_build_execute.log_entry')
    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_extras_reach_every_result_path(
        self,
        mock_log_file,
        mock_tget,
        mock_run,
        mock_tset,
        mock_log,
        returncode,
        side_effect,
        log_file,
        expected_status,
    ):
        mock_log_file.return_value = log_file
        if side_effect is None:
            mock_run.return_value = returncode
        else:
            mock_run.side_effect = side_effect

        result = _call_execute(extra_result_fields={'wrapper': './mvnw', 'mode': 'full'})

        assert result['status'] == expected_status
        assert result['wrapper'] == './mvnw'
        assert result['mode'] == 'full'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_no_extras_omits_extra_fields(self, mock_log_file, mock_tget, mock_run, mock_tset):
        """Matched control: the fields appear only because a caller supplied them."""
        mock_log_file.return_value = _LOG_FILE
        mock_run.return_value = 0

        result = _call_execute(extra_result_fields=None)

        assert 'wrapper' not in result


#: ``(member, wire value)``. The values are what a persisted result records, so
#: they are pinned as literals rather than derived from the member names.
_CAPTURE_STRATEGY_VALUES = [
    (CaptureStrategy.STDOUT_REDIRECT, 'stdout_redirect'),
    (CaptureStrategy.TOOL_LOG_FLAG, 'tool_log_flag'),
]

_CAPTURE_STRATEGY_IDS = ['stdout-redirect', 'tool-log-flag']


class TestCaptureStrategyEnum:
    """Tests for CaptureStrategy enum values."""

    @pytest.mark.parametrize('member,expected_value', _CAPTURE_STRATEGY_VALUES, ids=_CAPTURE_STRATEGY_IDS)
    def test_member_carries_its_wire_value(self, member, expected_value):
        assert member.value == expected_value

    def test_enum_has_two_members(self):
        assert len(CaptureStrategy) == 2


class TestWorkingDir:
    """Tests for working directory override."""

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_custom_working_dir_passed_to_subprocess(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        _call_execute(working_dir='/custom/dir')

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['cwd'] == '/custom/dir'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_no_working_dir_uses_project_dir(self, mock_log_file, mock_tget, mock_run, mock_tset):
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            execute_direct_base(
                args='verify',
                command_key='test:verify',
                default_timeout=300,
                project_dir=tmpdir,
                tool_name='test',
                build_command_fn=_build_command_fn,
                wrapper='/usr/bin/test-tool',
                plan_id=_PLAN_ID,
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
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_project_dir_propagates_to_subprocess_cwd(self, mock_log_file, mock_tget, mock_run, mock_tset):
        """The explicit project_dir must become subprocess.run's cwd."""
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            _call_execute(project_dir=tmpdir)

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs['cwd'] == tmpdir

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_project_dir_default_dot_propagates(self, mock_log_file, mock_tget, mock_run, mock_tset):
        """When CLI default '.' is passed, subprocess inherits '.' as cwd."""
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        execute_direct_base(
            args='verify',
            command_key='test:verify',
            default_timeout=300,
            project_dir='.',
            tool_name='test',
            build_command_fn=_build_command_fn,
            wrapper='/usr/bin/test-tool',
            plan_id=_PLAN_ID,
            capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
        )

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['cwd'] == '.'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_working_dir_overrides_project_dir_for_cwd(self, mock_log_file, mock_tget, mock_run, mock_tset):
        """Explicit working_dir should win over project_dir for subprocess cwd."""
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            _call_execute(project_dir=tmpdir, working_dir='/custom/override')

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs['cwd'] == '/custom/override'

    @patch('_build_execute.timeout_set')
    @patch('_build_execute._run_bounded')
    @patch('_build_execute.timeout_resolve', return_value=(300, 'learned'))
    @patch('_build_execute.create_log_file')
    def test_project_dir_absolute_path_propagates(self, mock_log_file, mock_tget, mock_run, mock_tset):
        """Absolute worktree-style paths must round-trip to subprocess cwd unchanged."""
        mock_log_file.return_value = '/tmp/test.log'
        mock_run.return_value = 0

        worktree_path = '/home/dev/.claude/worktrees/some-plan'
        execute_direct_base(
            args='verify',
            command_key='test:verify',
            default_timeout=300,
            project_dir=worktree_path,
            tool_name='test',
            build_command_fn=_build_command_fn,
            wrapper='/usr/bin/test-tool',
            plan_id=_PLAN_ID,
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
    import file_ops as _resolver_core
    from resolve_project_dir import resolve_project_dir

    # Patch the manage-status shell-out seam, which now lives in file_ops —
    # resolve_project_dir delegates the worktree face to resolve_plan_context.
    monkeypatch.setattr(
        _resolver_core, '_query_worktree_path', lambda _pid: worktree_query_result(True, '/tmp/wt-resolved')
    )
    resolved = resolve_project_dir('task-routing-canonical', '.', default='.')
    assert resolved.endswith('wt-resolved')

    with tempfile.TemporaryDirectory():
        with patch('_build_execute._run_bounded', return_value=0) as mock_run:
            execute_direct_base(
                args='verify',
                command_key='test:routing',
                default_timeout=300,
                project_dir=resolved,
                tool_name='test',
                build_command_fn=_build_command_fn,
                wrapper='/usr/bin/test-tool',
                plan_id=_PLAN_ID,
                capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
            )

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs['cwd'] == resolved, (
                f'subprocess cwd must match the resolver output {resolved!r}, got {call_kwargs["cwd"]!r}'
            )


def test_execute_direct_base_honours_main_checkout_fallback(monkeypatch):
    """When the resolver falls back to the main checkout, execute_direct_base honours it."""
    import resolve_project_dir as _routing
    from resolve_project_dir import resolve_project_dir

    monkeypatch.setattr(_routing, 'cwd_checkout_root', lambda: '/tmp/main-stub')
    resolved = resolve_project_dir(None, '.', default='.')
    assert resolved == '/tmp/main-stub'

    with tempfile.TemporaryDirectory():
        with patch('_build_execute._run_bounded', return_value=0) as mock_run:
            execute_direct_base(
                args='verify',
                command_key='test:fallback',
                default_timeout=300,
                project_dir=resolved,
                tool_name='test',
                build_command_fn=_build_command_fn,
                wrapper='/usr/bin/test-tool',
                plan_id=_PLAN_ID,
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
        with patch('_build_execute._run_bounded', return_value=0) as mock_run:
            execute_direct_base(
                args='verify',
                command_key='test:explicit',
                default_timeout=300,
                project_dir=resolved,
                tool_name='test',
                build_command_fn=_build_command_fn,
                wrapper='/usr/bin/test-tool',
                plan_id=_PLAN_ID,
                capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
            )

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs['cwd'] == resolved


# =============================================================================
# The launch helper stops the build process group
# =============================================================================
#
# These cases run REAL processes: the property under test is which processes are
# still alive afterwards, and a mocked launch cannot say.

_POSIX_ONLY = pytest.mark.skipif(os.name == 'nt', reason='process groups and os.killpg are POSIX-only')

# The grandchild ignores SIGTERM, announces that the handler is installed, and
# blocks. It only ever ends by SIGKILL, so its exit proves the group SIGKILL.
_GRANDCHILD_CODE = (
    'import signal, sys\n'
    'signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
    "open(sys.argv[1], 'w').close()\n"
    'while True:\n'
    '    signal.pause()\n'
)

# The build child spawns that grandchild with its streams detached, publishes
# both pids once the grandchild is ready, and blocks until it is stopped.
_SPAWN_GRANDCHILD_THEN_BLOCK = (
    'import os, signal, subprocess, sys, time\n'
    'ready, pid_file = sys.argv[1], sys.argv[2]\n'
    'grandchild = subprocess.Popen(\n'
    '    [sys.executable, "-c", sys.argv[3], ready],\n'
    '    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,\n'
    ')\n'
    'while not os.path.exists(ready):\n'
    '    time.sleep(0.01)\n'
    "with open(pid_file + '.tmp', 'w') as handle:\n"
    "    handle.write(f'{os.getpid()} {grandchild.pid}')\n"
    "os.replace(pid_file + '.tmp', pid_file)\n"
    'signal.pause()\n'
)

# A stand-in for the build wrapper process: it runs the launch helper on the
# build argv it is handed and records every log_entry call to a file, so a test
# can signal a real wrapper pid without signalling the pytest process itself.
_WRAPPER_CODE = (
    'import json, os, subprocess, sys\n'
    'import _build_execute\n'
    'captured, build_argv, cwd = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]\n'
    'def _capture(*entry):\n'
    "    with open(captured, 'a') as handle:\n"
    "        handle.write(json.dumps(entry) + '\\n')\n"
    '_build_execute.log_entry = _capture\n'
    "with open(os.devnull, 'w') as sink:\n"
    '    _build_execute._run_bounded(\n'
    '        build_argv, timeout_seconds=120, stdout=sink, stderr=subprocess.STDOUT,\n'
    "        cwd=cwd, env=None, log_prefix='TEST', command_str='wrapper build',\n"
    '    )\n'
)

_TREE_START_DEADLINE_SECONDS = 30
_TREE_EXIT_DEADLINE_SECONDS = 15


def _tree_build_argv(tmp_path):
    """Return ``(argv, pid_file)`` for a build child that spawns the grandchild."""
    pid_file = tmp_path / 'tree.pids'
    argv = [
        sys.executable,
        '-c',
        _SPAWN_GRANDCHILD_THEN_BLOCK,
        str(tmp_path / 'grandchild.ready'),
        str(pid_file),
        _GRANDCHILD_CODE,
    ]
    return argv, pid_file


def _read_tree_pids(pid_file):
    """Return ``(child_pid, grandchild_pid)`` published by the build child."""
    child_pid, grandchild_pid = (int(token) for token in pid_file.read_text().split())
    # Guards the teardown: a pid of 0 or 1 would address this process's own group or init.
    assert child_pid > 1 and grandchild_pid > 1
    return child_pid, grandchild_pid


def _pid_alive(pid):
    """Report whether ``pid`` is a running process; an unreaped zombie is not."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # A zombie still answers signal 0: it has exited and only awaits reaping.
    try:
        with open(f'/proc/{pid}/stat') as handle:
            return handle.read().rpartition(')')[2].split()[0] != 'Z'
    except OSError:
        # No procfs (macOS) or the process vanished mid-read: trust the signal probe.
        return True


def _pid_is_gone(pid):
    """Report whether ``pid`` stops existing before the exit deadline passes."""
    deadline = time.monotonic() + _TREE_EXIT_DEADLINE_SECONDS
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return True
        time.sleep(0.05)
    return False


def _reap_build_tree(child_pid, grandchild_pid):
    """Kill whatever is left of a build tree so no test leaks a process."""
    # The build child leads its own group, so the group id is its pid.
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(child_pid, signal.SIGKILL)
    for pid in (child_pid, grandchild_pid):
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, signal.SIGKILL)


def _start_wrapper(tmp_path):
    """Start a wrapper process running the tree build; return ``(wrapper, child_pid, grandchild_pid)``.

    The wrapper leads its own process group, so a test can address that group
    without addressing the pytest process.
    """
    build_argv, pid_file = _tree_build_argv(tmp_path)
    stderr_path = tmp_path / 'wrapper.stderr'
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(entry for entry in sys.path if entry)
    with open(stderr_path, 'w') as stderr_sink:
        wrapper = subprocess.Popen(
            [
                sys.executable,
                '-c',
                _WRAPPER_CODE,
                str(tmp_path / 'log-entries.jsonl'),
                json.dumps(build_argv),
                str(tmp_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=stderr_sink,
            env=env,
            process_group=0,
        )
    deadline = time.monotonic() + _TREE_START_DEADLINE_SECONDS
    while not pid_file.exists():
        if wrapper.poll() is not None or time.monotonic() > deadline:
            wrapper.kill()
            wrapper.wait()
            raise AssertionError(f'the wrapper never started its build tree: {stderr_path.read_text()}')
        time.sleep(0.02)
    child_pid, grandchild_pid = _read_tree_pids(pid_file)
    return wrapper, child_pid, grandchild_pid


def _stop_wrapper(wrapper):
    """Make sure a wrapper process is dead and reaped."""
    if wrapper.poll() is None:
        wrapper.kill()
    wrapper.wait()


@_POSIX_ONLY
class TestTimeoutStopsTheBuildTree:
    """An expired bound stops the build's process group, not only its child."""

    def test_timed_out_build_leaves_no_grandchild_and_teaches_the_learner(self, tmp_path):
        build_argv, pid_file = _tree_build_argv(tmp_path)
        bound = 5

        with (
            patch('_build_execute.create_log_file', return_value=str(tmp_path / 'build.log')),
            patch('_build_execute.timeout_resolve', return_value=(bound, 'learned')),
            patch('_build_execute.timeout_set') as mock_tset,
            patch('_build_execute.log_entry'),
        ):
            result = execute_direct_base(
                args='verify',
                command_key='test:verify',
                default_timeout=bound,
                project_dir=str(tmp_path),
                tool_name='test',
                build_command_fn=lambda wrapper, args, log_file: (build_argv, 'tree build'),
                wrapper='unused',
                plan_id=_PLAN_ID,
                min_timeout=1,
            )

        assert pid_file.exists(), 'the build child never published its tree before the bound expired'
        child_pid, grandchild_pid = _read_tree_pids(pid_file)
        try:
            assert result['status'] == 'timeout'
            assert _pid_is_gone(grandchild_pid), f'grandchild {grandchild_pid} outlived the timeout'
            assert _pid_is_gone(child_pid)
            assert mock_tset.call_args_list == [call('test:verify', min(bound * 2, MAX_TIMEOUT), str(tmp_path))]
        finally:
            _reap_build_tree(child_pid, grandchild_pid)


#: ``(resolved bound, value the learner must be fed)`` — the doubling, and the cap.
_TIMEOUT_LEARNER_CASES = [(300, 600), (1000, MAX_TIMEOUT)]

_TIMEOUT_LEARNER_IDS = ['bound-doubled', 'doubling-capped-at-max-timeout']


class TestTimeoutLearnerCallIsUnchanged:
    """The learner call on the timeout path keeps its exact argument shape."""

    @pytest.mark.parametrize('bound,expected', _TIMEOUT_LEARNER_CASES, ids=_TIMEOUT_LEARNER_IDS)
    def test_learner_receives_three_positional_arguments_and_nothing_else(self, bound, expected):
        with (
            tempfile.TemporaryDirectory() as project_dir,
            patch('_build_execute.create_log_file', return_value=_LOG_FILE),
            patch('_build_execute.timeout_resolve', return_value=(bound, 'learned')),
            patch('_build_execute.timeout_set') as mock_tset,
            patch('_build_execute.log_entry'),
            patch(
                '_build_execute._run_bounded',
                side_effect=subprocess.TimeoutExpired(cmd='test', timeout=bound),
            ),
        ):
            _call_execute(command_key='test:verify', project_dir=project_dir)

        # ``call`` equality covers positional and keyword arguments alike.
        assert mock_tset.call_args_list == [call('test:verify', expected, project_dir)]


# Module-level on purpose: pytest rejects a class-scoped fixture declared as an
# instance method. The class scope still shares one run between the tests of the
# class that requests it.
@pytest.fixture(scope='class')
def sigterm_run(tmp_path_factory):
    """Start a wrapper, SIGTERM it once its build tree is up, and collect the outcome."""
    tmp_path = tmp_path_factory.mktemp('forwarded-sigterm')
    wrapper, child_pid, grandchild_pid = _start_wrapper(tmp_path)
    try:
        os.kill(wrapper.pid, signal.SIGTERM)
        wrapper.wait(timeout=_TREE_EXIT_DEADLINE_SECONDS)
        log_path = tmp_path / 'log-entries.jsonl'
        entries = [json.loads(line) for line in log_path.read_text().splitlines()] if log_path.exists() else []
        yield {
            'returncode': wrapper.returncode,
            'child_pid': child_pid,
            'grandchild_pid': grandchild_pid,
            'entries': entries,
        }
    finally:
        _stop_wrapper(wrapper)
        _reap_build_tree(child_pid, grandchild_pid)


@_POSIX_ONLY
class TestForwardedSignalStopsTheBuildTree:
    """A SIGTERM delivered to the wrapper is forwarded and ends the build tree."""

    def test_wrapper_survives_the_forwarded_signal_and_returns(self, sigterm_run):
        assert sigterm_run['returncode'] == 0

    def test_sigterm_to_the_wrapper_ends_the_grandchild(self, sigterm_run):
        assert _pid_is_gone(sigterm_run['grandchild_pid'])
        assert _pid_is_gone(sigterm_run['child_pid'])

    def test_forwarded_signal_writes_one_error_line_naming_the_signal(self, sigterm_run):
        error_messages = [entry[3] for entry in sigterm_run['entries'] if entry[2] == 'ERROR']

        assert len(error_messages) == 1
        assert 'SIGTERM' in error_messages[0]
        assert 'SIGKILL of this wrapper cannot be forwarded' in error_messages[0]


#: The pid the mocked build child reports. ``os.killpg`` is mocked wherever this
#: is used, so the value is only ever compared, never signalled.
_TRAPPING_CHILD_PID = 424242

#: ``(exit code the child chooses, status that code yields when no signal was
#: forwarded)``. The first is the shell convention for "ended by SIGTERM", the
#: second a clean exit — the two shapes a child that traps the signal can take.
_TRAPPED_EXITS = [(128 + signal.SIGTERM, 'error'), (0, 'success')]

_TRAPPED_EXIT_IDS = ['child-exits-non-zero', 'child-exits-zero']


def _execute_against_trapping_child(tmp_path, exit_code, *, forward):
    """Run ``execute_direct_base`` against a mocked child that exits with ``exit_code``.

    With ``forward`` set, the SIGTERM handler the launch helper installed is run
    while the child is first waited for — what a SIGTERM delivered to the wrapper
    does — and the child then ends with ``exit_code`` instead of dying by the
    signal. Returns ``(result, learner mock, killpg mock)``.
    """
    child = MagicMock()
    child.pid = _TRAPPING_CHILD_PID
    pending = iter([forward])

    def _wait(timeout=None):
        if next(pending, False):
            handler = signal.getsignal(signal.SIGTERM)
            assert callable(handler), 'the launch helper installed no SIGTERM handler to forward with'
            handler(signal.SIGTERM, None)
        return exit_code

    child.wait.side_effect = _wait
    with (
        patch('_build_execute.create_log_file', return_value=str(tmp_path / 'build.log')),
        patch('_build_execute.timeout_resolve', return_value=(300, 'learned')),
        patch('_build_execute.timeout_set') as mock_tset,
        patch('_build_execute.log_entry'),
        patch.object(_build_execute.subprocess, 'Popen', return_value=child),
        patch.object(_build_execute.os, 'killpg') as mock_killpg,
    ):
        result = _call_execute(project_dir=str(tmp_path))
    return result, mock_tset, mock_killpg


@_POSIX_ONLY
class TestForwardedStopIsANonFinishWhateverTheChildExitsWith:
    """A forwarded signal makes the run ``killed`` even when the child exits by itself."""

    @pytest.mark.parametrize(('exit_code', '_finish_status'), _TRAPPED_EXITS, ids=_TRAPPED_EXIT_IDS)
    def test_forwarded_stop_is_killed_and_does_not_teach_the_learner(self, tmp_path, exit_code, _finish_status):
        result, mock_tset, mock_killpg = _execute_against_trapping_child(tmp_path, exit_code, forward=True)

        assert mock_killpg.call_args_list[0] == call(_TRAPPING_CHILD_PID, signal.SIGTERM)
        assert result['status'] == 'killed'
        assert result['exit_code'] == -signal.SIGTERM
        mock_tset.assert_not_called()

    @pytest.mark.parametrize(('exit_code', 'finish_status'), _TRAPPED_EXITS, ids=_TRAPPED_EXIT_IDS)
    def test_control_same_exit_code_with_no_forwarded_signal_is_a_finish(self, tmp_path, exit_code, finish_status):
        """CONTROL: the exit code alone does not make a run ``killed``."""
        result, mock_tset, mock_killpg = _execute_against_trapping_child(tmp_path, exit_code, forward=False)

        mock_killpg.assert_not_called()
        assert result['status'] == finish_status
        assert result['exit_code'] == exit_code
        mock_tset.assert_called_once()


@_POSIX_ONLY
class TestSigkillOfTheWrapperIsNotForwarded:
    """A SIGKILL cannot be caught, so the wrapper cannot forward it."""

    def test_sigkill_of_the_wrapper_pid_leaves_exactly_the_build_tree(self, tmp_path):
        """The survivors are the build child and its grandchild, and nothing else.

        That is the set a wrapper killed this way has always left behind: the
        launch helper neither removes a survivor nor adds one.
        """
        wrapper, child_pid, grandchild_pid = _start_wrapper(tmp_path)
        try:
            os.kill(wrapper.pid, signal.SIGKILL)
            wrapper.wait(timeout=_TREE_EXIT_DEADLINE_SECONDS)
            time.sleep(0.2)

            survivors = {pid for pid in (wrapper.pid, child_pid, grandchild_pid) if _pid_alive(pid)}

            assert wrapper.returncode == -signal.SIGKILL
            assert survivors == {child_pid, grandchild_pid}
        finally:
            _stop_wrapper(wrapper)
            _reap_build_tree(child_pid, grandchild_pid)

    def test_sigkill_of_the_wrapper_process_group_leaves_the_build_group_running(self, tmp_path):
        """Characterization of the accepted case, not a defect to fix.

        Operator decision (kill mechanism, settled): the build runs in its own
        process group with signal forwarding, and the group-addressed SIGKILL
        case is accepted and recorded rather than designed around. A SIGKILL
        addressed to the wrapper's process group therefore does not reach the
        build group, which keeps running. The teardown reaps that group.
        """
        wrapper, child_pid, grandchild_pid = _start_wrapper(tmp_path)
        try:
            wrapper_group = os.getpgid(wrapper.pid)
            assert wrapper_group == wrapper.pid
            assert wrapper_group != os.getpgrp()

            os.killpg(wrapper_group, signal.SIGKILL)
            wrapper.wait(timeout=_TREE_EXIT_DEADLINE_SECONDS)
            time.sleep(0.2)

            assert wrapper.returncode == -signal.SIGKILL
            assert _pid_alive(child_pid)
            assert _pid_alive(grandchild_pid)
            assert os.getpgid(child_pid) != wrapper_group
        finally:
            _stop_wrapper(wrapper)
            _reap_build_tree(child_pid, grandchild_pid)


def _run_bounded_with_mocked_launch(*, timeout_seconds=60, wait=None):
    """Call the launch helper against a mocked ``Popen``; return ``(outcome, popen, child)``.

    ``outcome`` is the returncode, or the ``TimeoutExpired`` instance raised.
    """
    child = MagicMock()
    child.wait.side_effect = wait if wait is not None else [0]
    with patch.object(_build_execute.subprocess, 'Popen', return_value=child) as mock_popen:
        try:
            outcome = _build_execute._run_bounded(
                ['tool'],
                timeout_seconds=timeout_seconds,
                stdout=None,
                stderr=None,
                cwd='.',
                env=None,
                log_prefix='TEST',
                command_str='tool',
            )
        except subprocess.TimeoutExpired as expired:
            outcome = expired
    return outcome, mock_popen, child


class TestWindowsLaunchKeepsTheSingleProcessBehaviour:
    """On Windows the command is a plain child: no group, and a one-process kill."""

    def test_windows_launch_passes_no_process_group_argument(self, monkeypatch):
        monkeypatch.setattr(_build_execute, 'IS_WINDOWS', True)

        outcome, mock_popen, child = _run_bounded_with_mocked_launch()

        assert outcome == 0
        assert 'process_group' not in mock_popen.call_args.kwargs
        assert 'start_new_session' not in mock_popen.call_args.kwargs
        child.wait.assert_called_once_with(timeout=60)

    def test_windows_timeout_kills_the_child_alone_and_raises(self, monkeypatch):
        monkeypatch.setattr(_build_execute, 'IS_WINDOWS', True)
        expired = subprocess.TimeoutExpired(cmd='tool', timeout=60)

        with patch.object(_build_execute.os, 'killpg', create=True) as mock_killpg:
            outcome, _mock_popen, child = _run_bounded_with_mocked_launch(wait=[expired, 0])

        assert outcome is expired
        child.kill.assert_called_once_with()
        mock_killpg.assert_not_called()

    @_POSIX_ONLY
    def test_control_posix_launch_starts_the_command_in_its_own_group(self, monkeypatch):
        """CONTROL: the argument is absent on Windows because the branch omits it."""
        monkeypatch.setattr(_build_execute, 'IS_WINDOWS', False)

        outcome, mock_popen, _child = _run_bounded_with_mocked_launch()

        assert outcome == 0
        assert mock_popen.call_args.kwargs['process_group'] == 0


@_POSIX_ONLY
def test_launch_helper_restores_the_signal_handlers_it_replaced():
    """The forwarding handlers live only for the duration of the run."""
    forwarded = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
    before = {signum: signal.getsignal(signum) for signum in forwarded}

    returncode = _build_execute._run_bounded(
        [sys.executable, '-c', 'pass'],
        timeout_seconds=60,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd='.',
        env=None,
        log_prefix='TEST',
        command_str='noop',
    )

    assert returncode == 0
    assert {signum: signal.getsignal(signum) for signum in forwarded} == before


def test_wrapper_grace_is_strictly_below_the_supervisor_grace():
    """The wrapper must finish stopping its build group before the supervisor SIGKILLs it."""
    supervisor = load_script_module('plan-marshall', 'manage-build-server', '_marshalld_supervisor.py', register=False)

    assert _build_execute._GROUP_KILL_GRACE_SECONDS < supervisor._JOB_KILL_GRACE_SECONDS
