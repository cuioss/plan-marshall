#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _maven_execute.py.

Tests the Maven execution config and factory-generated functions.
"""

from pathlib import Path

from conftest import load_script_module

_maven_execute_mod = load_script_module('plan-marshall', 'build-maven', '_maven_execute.py', '_maven_execute')

import _build_execute_factory as _factory  # noqa: E402

_CONFIG = _maven_execute_mod._CONFIG
execute_direct = _maven_execute_mod.execute_direct

#: The plan these builds are attributed to. ``plan_id`` is keyword-only and
#: mandatory on the factory-generated ``execute_direct``.
_PLAN_ID = 'maven-execute-test-plan'

# =============================================================================
# Config Tests
# =============================================================================


def test_config_tool_name():
    """Config has correct tool name."""
    assert _CONFIG.tool_name == 'maven'


def test_config_wrapper_names():
    """Config has correct wrapper names for Maven."""
    assert _CONFIG.unix_wrapper == 'mvnw'
    assert _CONFIG.windows_wrapper == 'mvnw.cmd'
    assert _CONFIG.system_fallback == 'mvn'


def test_config_default_timeout():
    """Config has 300s default timeout (unified across all build skills)."""
    assert _CONFIG.default_timeout == 300


def test_config_declares_the_outer_floor_as_a_literal_300(tmp_path, monkeypatch):
    """Maven declares its own outer floor explicitly, and it reaches the executor.

    The floor is asserted as the LITERAL ``300`` rather than as an equality
    against ``DEFAULT_BUILD_TIMEOUT``: the two happen to coincide today, so an
    equality assertion would keep passing vacuously if that constant later
    moved, silently un-pinning the declared floor this case exists to guard.

    Both halves matter — declaring the constant is worthless if it never
    reaches ``execute_direct_base``, so the second half proves the wiring by
    capturing the ``min_timeout`` kwarg the executor actually receives.
    """
    assert _maven_execute_mod.MAVEN_OUTER_FLOOR_SECONDS == 300
    assert _CONFIG.min_timeout == 300

    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    calls = []

    def _recorder(**kwargs):
        calls.append(kwargs)
        return {'status': 'success', 'exit_code': 0, 'duration_seconds': 0, 'log_file': '', 'command': 'mvn verify'}

    monkeypatch.setattr(_factory, 'execute_direct_base', _recorder)

    execute_direct(args='verify', command_key='maven:verify', project_dir=str(tmp_path), plan_id=_PLAN_ID)

    assert calls[0]['min_timeout'] == 300


def test_config_capture_strategy():
    """Config uses Maven log flag strategy."""
    from _build_execute import CaptureStrategy

    assert _CONFIG.capture_strategy == CaptureStrategy.TOOL_LOG_FLAG


# =============================================================================
# Command Key Function
# =============================================================================


def test_command_key_fn_verify():
    """Extracts 'verify' from args."""
    assert _CONFIG.command_key_fn('verify') == 'verify'


def test_command_key_fn_clean_install():
    """Scope-aware: full args normalized to underscores."""
    assert _CONFIG.command_key_fn('clean install') == 'clean_install'


def test_command_key_fn_module_tests():
    """Scope-aware: module scope preserved in key to avoid cross-scope collisions."""
    assert _CONFIG.command_key_fn('test -pl core') == 'test__pl_core'


def test_command_key_fn_empty():
    """Returns 'default' for empty args."""
    assert _CONFIG.command_key_fn('') == 'default'


# =============================================================================
# Scope Function
# =============================================================================


def test_scope_fn_default_no_pl():
    """Scope is 'default' when no -pl argument."""
    assert _CONFIG.scope_fn('verify') == 'default'


def test_scope_fn_extracts_module():
    """Extracts module name from -pl argument."""
    assert _CONFIG.scope_fn('verify -pl core-api') == 'core-api'


def test_scope_fn_pl_equals():
    """Handles -pl=module form."""
    assert _CONFIG.scope_fn('verify -pl=my-module') == 'my-module'


# =============================================================================
# Build Command Function
# =============================================================================


def test_build_command_fn():
    """Builds command with -l flag for log file."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('./mvnw', 'verify', '/tmp/log.log')
    assert cmd_parts == ['./mvnw', '-l', '/tmp/log.log', 'verify']
    assert '-l' in cmd_str
    assert '/tmp/log.log' in cmd_str


def test_build_command_fn_with_module():
    """Includes module argument in command."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('./mvnw', 'test -pl core', '/tmp/log.log')
    assert cmd_parts == ['./mvnw', '-l', '/tmp/log.log', 'test', '-pl', 'core']


# =============================================================================
# Wrapper Resolution and Execution
# =============================================================================


def test_config_has_no_require_wrapper_knob():
    """The require_wrapper gate is removed — ExecuteConfig no longer carries it,
    so Maven auto-detects the wrapper and falls back to the system binary."""
    assert not hasattr(_CONFIG, 'require_wrapper')


def test_execute_direct_absent_wrapper_resolves_system_binary(tmp_path, monkeypatch):
    """execute_direct auto-resolves to the system 'mvn' binary when running in an
    empty directory: with the gate removed, an absent mvnw falls back to the
    system binary with no wrapper-not-found error and no FileNotFoundError during
    resolution."""
    # Pin PLAN_BASE_DIR so the shared learned-timeout machinery
    # (run_config.timeout_set) writes into tmp_path, not the real repo-local
    # run-configuration.json.
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

    calls = []

    def _recorder(**kwargs):
        calls.append(kwargs)
        return {'status': 'success', 'exit_code': 0, 'duration_seconds': 0, 'log_file': '', 'command': 'mvn verify'}

    monkeypatch.setattr(_factory, 'execute_direct_base', _recorder)

    # Empty tmp_path has no mvnw — resolution falls back to the system 'mvn'.
    result = execute_direct(
        args='verify',
        command_key='maven:verify',
        project_dir=str(tmp_path),
        plan_id=_PLAN_ID,
    )
    assert result['status'] == 'success'
    assert calls[0]['wrapper'] == 'mvn'


def test_execute_direct_resolves_present_wrapper(tmp_path, monkeypatch):
    """With a present mvnw, resolution prefers the project wrapper ./mvnw."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    (tmp_path / 'mvnw').write_text('#!/bin/sh\n')

    calls = []

    def _recorder(**kwargs):
        calls.append(kwargs)
        return {'status': 'success', 'exit_code': 0, 'duration_seconds': 0, 'log_file': '', 'command': './mvnw verify'}

    monkeypatch.setattr(_factory, 'execute_direct_base', _recorder)

    result = execute_direct(args='verify', command_key='maven:verify', project_dir=str(tmp_path), plan_id=_PLAN_ID)

    assert result['status'] == 'success'
    assert calls[0]['wrapper'] == './mvnw'


# =============================================================================
# A -Dtest selector that matched nothing is never green
# =============================================================================
#
# The decision lives on the RUN path, not in the parser alone: Surefire can end
# a selector miss with exit 0 (``-Dsurefire.failIfNoSpecifiedTests=false``), so
# a parser verdict that the emit choke point never reads would still let the run
# report ``success``.

apply_selector_miss_guard = _maven_execute_mod.apply_selector_miss_guard
TEST_SELECTOR_MATCHED_NOTHING = _maven_execute_mod.TEST_SELECTOR_MATCHED_NOTHING

_LOG_TEST_DATA = Path(__file__).parent / 'fixtures' / 'log-test-data'

_SELECTOR_COMMAND = 'mvnw test -Dtest=Awaits#runs'

_COMPILER_ERROR = '/home/dev/probe/c/src/main/java/probe/c/Broken.java:[5,9] cannot find symbol'


def _run_result(log_name: str, *, status: str, exit_code: int) -> dict:
    """A build result shaped like the executor's, pointing at one log fixture."""
    return {
        'status': status,
        'exit_code': exit_code,
        'duration_seconds': 3,
        'log_file': str(_LOG_TEST_DATA / log_name),
        'command': _SELECTOR_COMMAND,
    }


def test_dtest_run_with_zero_executed_tests_is_not_success():
    """A ``-Dtest`` run that executed no test is reported as the named reason, never green."""
    guarded = apply_selector_miss_guard(_run_result('maven-dtest-zero-executed.log', status='success', exit_code=0))

    assert guarded['status'] != 'success'
    assert guarded['status'] == 'indeterminate'
    assert guarded['message'].startswith(TEST_SELECTOR_MATCHED_NOTHING)


def test_control_dtest_run_with_an_executed_test_stays_success():
    """CONTROL: the same command beside a run that executed a test keeps its success."""
    result = _run_result('maven-dtest-one-executed.log', status='success', exit_code=0)

    assert apply_selector_miss_guard(result) is result


def test_selector_miss_goal_failure_becomes_the_named_reason_not_a_build_failure():
    """Surefire's own goal failure is carried as the named reason, not as a red build."""
    guarded = apply_selector_miss_guard(_run_result('maven-selector-miss.log', status='error', exit_code=1))

    assert guarded['status'] == 'indeterminate'
    assert TEST_SELECTOR_MATCHED_NOTHING in guarded['message']
    assert 'Awaits#runs' in guarded['message']


def test_control_a_real_failure_after_a_zero_test_module_keeps_its_failure(tmp_path):
    """CONTROL: a later real failure is not relabelled as a selector miss.

    The zero-collected shape is an exit-0 shape. In a reactor an earlier module
    can print `Tests run: 0` and a later one then fail to compile; only
    Surefire's explicit goal failure may claim a miss on a failed build, or the
    real failure — and its findings — would be hidden.
    """
    # Arrange
    log_file = tmp_path / 'zero-then-compile-failure.log'
    log_file.write_text(
        '[INFO] --- surefire:3.5.2:test (default-test) @ a ---\n'
        '[INFO] Results:\n'
        '[WARNING] Tests run: 0, Failures: 0, Errors: 0, Skipped: 0\n'
        f'[ERROR] {_COMPILER_ERROR}\n'
        '[INFO] BUILD FAILURE\n',
        encoding='utf-8',
    )
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 5,
        'log_file': str(log_file),
        'command': _SELECTOR_COMMAND,
    }

    # Act
    guarded = apply_selector_miss_guard(result)

    # Assert
    assert guarded is result
    assert guarded['status'] == 'error'


def test_control_a_mixed_reactor_keeps_the_other_modules_failure(tmp_path):
    """CONTROL: a selector miss beside another module's real failure does not claim the run.

    ``--fail-at-end`` lets a reactor finish other modules after one fails. When
    the log carries BOTH a selector miss and a real failure, converting the run
    to ``indeterminate`` would drop the other module's errors and findings.
    """
    # Arrange
    log_file = tmp_path / 'mixed-failure.log'
    log_file.write_text(
        '[ERROR] Failed to execute goal org.apache.maven.plugins:maven-surefire-plugin:3.5.2:test '
        '(default-test) on project b: No tests matching pattern "Awaits#runs" were executed! '
        '(Set -Dsurefire.failIfNoSpecifiedTests=false to ignore this error.)\n'
        '[ERROR] Tests run: 3, Failures: 1, Errors: 0, Skipped: 0, Time elapsed: 0.02 s <<< FAILURE! '
        '-- in probe.other.OtherTest\n'
        '[INFO] BUILD FAILURE\n',
        encoding='utf-8',
    )
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 5,
        'log_file': str(log_file),
        'command': _SELECTOR_COMMAND,
    }

    # Act
    guarded = apply_selector_miss_guard(result)

    # Assert — the real failure keeps the build-failure path.
    assert guarded is result
    assert guarded['status'] == 'error'


def test_execute_direct_is_wired_to_the_guard(tmp_path, monkeypatch):
    """The guard is REACHED by the executor, not merely available beside it.

    Every other case here calls ``apply_selector_miss_guard`` directly, so
    dropping ``wrap_execute_fn`` from the factory call would leave them all
    green while the guard went dead. This one drives the module's own
    ``execute_direct`` end to end.
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    (tmp_path / 'mvnw').write_text('#!/bin/sh\n')

    def _recorder(**kwargs):
        return {
            'status': 'success',
            'exit_code': 0,
            'duration_seconds': 1,
            'log_file': str(_LOG_TEST_DATA / 'maven-dtest-zero-executed.log'),
            'command': f'./mvnw -l /tmp/maven.log {_SELECTOR_COMMAND}',
            'wrapper': './mvnw',
            'command_key': 'maven:test',
            'project_dir': str(tmp_path),
            'timeout_used_seconds': 300,
        }

    monkeypatch.setattr(_factory, 'execute_direct_base', _recorder)

    result = execute_direct(
        args='test -Dtest=Awaits#runs',
        command_key='maven:test',
        project_dir=str(tmp_path),
        plan_id=_PLAN_ID,
    )

    assert result['status'] == 'indeterminate'
    assert TEST_SELECTOR_MATCHED_NOTHING in result['message']
    assert result['wrapper'] == './mvnw', 'the executor fields travel with the verdict'
    assert result['command_key'] == 'maven:test'
    assert result['project_dir'] == str(tmp_path)
    assert result['timeout_used_seconds'] == 300, 'fields the guard does not replace are carried'
