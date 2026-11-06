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
apply_zero_test_guard = _maven_execute_mod.apply_zero_test_guard
TEST_SELECTOR_MATCHED_NOTHING = _maven_execute_mod.TEST_SELECTOR_MATCHED_NOTHING
TEST_LOG_UNREADABLE = _maven_execute_mod.TEST_LOG_UNREADABLE
TEST_RUN_EXECUTED_NOTHING = _maven_execute_mod.TEST_RUN_EXECUTED_NOTHING

_LOG_TEST_DATA = Path(__file__).parent / 'fixtures' / 'log-test-data'

_SELECTOR_COMMAND = 'mvnw test -Dtest=Awaits#runs'

#: The same run when the selector comes from `.mvn/maven.config`, `MAVEN_OPTS`
#: or a profile: Surefire still names the pattern, the command line does not.
_NO_COMMAND_SELECTOR = 'mvnw test -f ./pom.xml'

_COMPILER_ERROR = '/home/dev/probe/c/src/main/java/probe/c/Broken.java:[5,9] cannot find symbol'


def _run_result(log_name: str, *, status: str, exit_code: int, command: str = _SELECTOR_COMMAND) -> dict:
    """A build result shaped like the executor's, pointing at one log fixture."""
    return {
        'status': status,
        'exit_code': exit_code,
        'duration_seconds': 3,
        'log_file': str(_LOG_TEST_DATA / log_name),
        'command': command,
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


def test_fae_reactor_keeps_a_real_failure_beside_a_selector_miss():
    """A `-fae` reactor's compile failure is not dropped for another module's miss.

    The compile error `';' expected` matches no category pattern, so it is filed
    as `other` — a real failure all the same. Relabelling the whole run as a
    selector miss would hide it and the finding it produces.
    """
    result = _run_result('maven-fae-compile-failure-and-selector-miss.log', status='error', exit_code=1)

    guarded = apply_selector_miss_guard(result)

    assert guarded is result, 'the real failure keeps the build-failure path'
    assert guarded['status'] == 'error'
    issues, _, _ = _maven_execute_mod.parse_log(result['log_file'])
    assert any("';' expected" in issue.message for issue in issues), (
        'the compile error must survive as an issue, or the run keeps no row to report'
    )


def test_selector_miss_without_a_command_selector_names_the_pattern_from_the_log():
    """The reason names the pattern Surefire printed when the command shows none."""
    result = _run_result(
        'maven-maven-config-selector-miss.log', status='error', exit_code=1, command=_NO_COMMAND_SELECTOR
    )

    guarded = apply_selector_miss_guard(result)

    assert guarded['status'] == 'indeterminate'
    assert "'Awaits#runs'" in guarded['message'], guarded['message']


def test_reactor_selector_miss_beside_an_executed_module_says_what_the_run_did():
    """A partial reactor miss does not claim the run executed nothing."""
    result = _run_result('maven-reactor-selector-miss-one-module.log', status='success', exit_code=0)

    guarded = apply_selector_miss_guard(result)

    assert guarded['status'] == 'indeterminate'
    assert "'Awaits#runs'" in guarded['message']
    assert 'executed nothing' not in guarded['message'], (
        'module a ran three tests, so claiming the run executed nothing is untrue of it'
    )
    assert '3 test(s)' in guarded['message'], guarded['message']


def test_control_a_selector_miss_that_ran_nothing_still_says_so():
    """CONTROL: the lone exit-0 miss keeps its 'executed nothing' wording."""
    guarded = apply_selector_miss_guard(_run_result('maven-dtest-zero-executed.log', status='success', exit_code=0))

    assert guarded['status'] == 'indeterminate'
    assert 'executed nothing' in guarded['message']


def test_unreadable_log_on_a_zero_exit_dtest_run_is_indeterminate(tmp_path):
    """No readable log is no evidence, so a `-Dtest` run cannot be green."""
    result = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 2,
        'log_file': str(tmp_path / 'missing.log'),
        'command': _SELECTOR_COMMAND,
    }

    guarded = apply_selector_miss_guard(result)

    assert guarded['status'] == 'indeterminate'
    assert guarded['message'].startswith(TEST_LOG_UNREADABLE)


def test_control_unreadable_log_on_a_failed_build_keeps_its_failure(tmp_path):
    """CONTROL: a failed build stays failed when its log cannot be read."""
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 2,
        'log_file': str(tmp_path / 'missing.log'),
        'command': _SELECTOR_COMMAND,
    }

    assert apply_selector_miss_guard(result) is result


# =============================================================================
# A test-phase run that executed no test is never green
# =============================================================================


def test_zero_test_run_is_not_success():
    """A `test` run whose summary collected nothing is the named reason."""
    result = _run_result('maven-zero-tests-executed.log', status='success', exit_code=0, command='mvnw test')

    guarded = apply_zero_test_guard(result, 'test')

    assert guarded['status'] == 'indeterminate'
    assert guarded['message'].startswith(TEST_RUN_EXECUTED_NOTHING)


def test_test_run_with_no_summary_at_all_is_not_success():
    """A `test` run that produced no test summary collected and ran nothing.

    This is the shape a bare `pom` aggregator produces: `mvn test` there runs no
    Surefire execution at all and exits 0, which no gate may credit as a green
    test run.
    """
    result = _run_result('maven-test-no-summary.log', status='success', exit_code=0, command='mvnw test')

    guarded = apply_zero_test_guard(result, 'test')

    assert guarded['status'] == 'indeterminate'
    assert guarded['message'].startswith(TEST_RUN_EXECUTED_NOTHING)


def test_control_test_run_with_an_executed_test_stays_success():
    """CONTROL: a `test` run that executed tests keeps its success."""
    result = _run_result('maven-success-real.log', status='success', exit_code=0, command='mvnw test')

    assert apply_zero_test_guard(result, 'test') is result


def test_control_a_verify_run_without_a_test_summary_stays_success():
    """CONTROL: only a leading test-phase goal is a test run.

    A `verify` run also executes tests, but its purpose is the gate; a project
    that has no test to run there is legitimately green.
    """
    result = _run_result('maven-test-no-summary.log', status='success', exit_code=0, command='mvnw verify')

    assert apply_zero_test_guard(result, 'verify -Ppre-commit') is result


def test_control_a_package_run_without_a_test_summary_stays_success():
    """CONTROL: `package` without a summary is a build run that reported no tests.

    Only a `package` run whose log NAMES a zero population is evidence; the
    package phase is also the plain package canonical, not only the test ladder
    of a reactor-test-artifact consumer.
    """
    result = _run_result('maven-test-no-summary.log', status='success', exit_code=0, command='mvnw package')

    assert apply_zero_test_guard(result, 'package -pl consumer -am') is result


def test_control_a_skip_tests_run_reports_zero_tests_by_design():
    """CONTROL: `-DskipTests` asks for no test, so an empty population is expected."""
    result = _run_result(
        'maven-zero-tests-executed.log', status='success', exit_code=0, command='mvnw test -DskipTests'
    )

    assert apply_zero_test_guard(result, 'test -DskipTests') is result


def test_control_a_skip_stated_by_the_log_is_not_an_empty_population(tmp_path):
    """CONTROL: a run that SAYS it skipped is a requested skip, not a false green.

    `-DskipTests` set in `.mvn/maven.config` or `MAVEN_OPTS` is invisible on the
    command line this guard is handed, so the log's own skip marker is what keeps
    such a run from being reported as an empty population.
    """
    log_file = tmp_path / 'skipped.log'
    log_file.write_text(
        '[INFO] --- surefire:3.5.2:test (default-test) @ awaits ---\n[INFO] Tests are skipped.\n[INFO] BUILD SUCCESS\n',
        encoding='utf-8',
    )

    result = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 1,
        'log_file': str(log_file),
        'command': 'mvnw test',
    }

    assert apply_zero_test_guard(result, 'test') is result


def test_leading_goal_is_read_past_a_value_taking_option():
    """`mvn -pl core test` is a test run: the option's value is not the goal."""
    result = _run_result('maven-test-no-summary.log', status='success', exit_code=0, command='mvnw -pl core test')

    guarded = apply_zero_test_guard(result, '-pl core test')

    assert guarded['status'] == 'indeterminate'
    assert guarded['message'].startswith(TEST_RUN_EXECUTED_NOTHING)


def test_an_error_level_advisory_beside_a_miss_keeps_the_failure(tmp_path):
    """An `[ERROR]`-level javadoc failure is a real failure, not an advisory.

    The `javadoc` pattern files such a line under `javadoc_warning`, and a
    category-only back-off would drop it when another module reports a miss.
    Severity decides: an `[ERROR]` line is the build failure whatever its
    category.
    """
    log_file = tmp_path / 'miss-and-javadoc.log'
    log_file.write_text(
        '[ERROR] Failed to execute goal org.apache.maven.plugins:maven-surefire-plugin:3.5.2:test '
        '(default-test) on project b: No tests matching pattern "Awaits#runs" were executed!\n'
        '[ERROR] Failed to execute goal org.apache.maven.plugins:maven-javadoc-plugin:3.11.2:jar '
        '(attach-javadocs) on project a: Javadoc generation failed.\n'
        '[INFO] BUILD FAILURE\n',
        encoding='utf-8',
    )
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 4,
        'log_file': str(log_file),
        'command': _SELECTOR_COMMAND,
    }

    assert apply_selector_miss_guard(result) is result


def test_unmeasured_summary_does_not_claim_the_run_executed_nothing(tmp_path):
    """An unmeasured summary cannot answer how much ran, so nothing is claimed."""
    log_file = tmp_path / 'miss-and-unmeasured.log'
    log_file.write_text(
        '[INFO] No tests matching pattern "Awaits#runs" were executed!\n'
        '[ERROR] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0\n'
        '[INFO] BUILD SUCCESS\n',
        encoding='utf-8',
    )
    result = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 4,
        'log_file': str(log_file),
        'command': _SELECTOR_COMMAND,
    }

    guarded = apply_selector_miss_guard(result)

    assert guarded['status'] == 'indeterminate'
    assert 'executed nothing' not in guarded['message'], guarded['message']
    assert 'does not measure' in guarded['message'], guarded['message']


def test_execute_direct_is_wired_to_the_zero_test_guard(tmp_path, monkeypatch):
    """The zero-test guard is REACHED by the executor, not merely available beside it."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    (tmp_path / 'mvnw').write_text('#!/bin/sh\n')

    def _recorder(**kwargs):
        return {
            'status': 'success',
            'exit_code': 0,
            'duration_seconds': 1,
            'log_file': str(_LOG_TEST_DATA / 'maven-test-no-summary.log'),
            'command': './mvnw -l /tmp/maven.log test',
            'wrapper': './mvnw',
        }

    monkeypatch.setattr(_factory, 'execute_direct_base', _recorder)

    result = execute_direct(args='test', command_key='maven:test', project_dir=str(tmp_path), plan_id=_PLAN_ID)

    assert result['status'] == 'indeterminate'
    assert TEST_RUN_EXECUTED_NOTHING in result['message']
    assert result['wrapper'] == './mvnw'
