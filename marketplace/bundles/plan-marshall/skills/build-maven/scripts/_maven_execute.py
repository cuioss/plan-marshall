#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Maven command execution — config-driven via execute handler factory.

Provides:
- execute_direct(): Foundation API for Maven command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)
- apply_selector_miss_guard(): the run-path truth check for a ``-Dtest`` miss
- apply_zero_test_guard(): the run-path truth check for a test run that ran none

Usage:
    from _maven_execute import execute_direct, cmd_run
"""

import re

from _build_execute import CaptureStrategy
from _build_execute_factory import ExecuteConfig, create_execute_handlers, default_command_key_fn
from _build_parse import read_log_text
from _build_result import STATUS_ERROR, STATUS_SUCCESS, indeterminate_result
from _build_shared import DEFAULT_BUILD_TIMEOUT
from _maven_cmd_parse import (
    TEST_LOG_UNREADABLE,
    TEST_RUN_EXECUTED_NOTHING,
    TEST_SELECTOR_MATCHED_NOTHING,
    collected_test_count,
    dtest_selector,
    executed_test_count,
    is_selector_miss_message,
    parse_log,
    selector_miss_pattern,
    selector_miss_reason,
)

# Outer timeout floor (seconds) for Maven builds. Maven resolves dependencies
# and downloads plugins on a cold local repository before a single module
# compiles, so a learned duration measured against a warm repository
# under-specifies the next cold run. This declared floor protects against that
# under-specification: no learned value can drop the outer wrapper bound below
# it, so a cold-cache resolve is never killed mid-download and reported as a
# build failure. Peer of ``_pyproject_execute.PYTEST_OUTER_FLOOR_SECONDS`` —
# every engine declares its own floor rather than inheriting ``MIN_TIMEOUT``.
MAVEN_OUTER_FLOOR_SECONDS = 300

#: Issue categories that describe no build failure — the advisory patterns
#: :data:`_build_jvm_patterns.JVM_BASE_PATTERNS` declares as ``javadoc_warning``,
#: ``deprecation_warning``, ``unchecked_warning`` and ``openrewrite_info`` (the
#: last as extended for Maven by ``_maven_cmd_parse.MAVEN_PATTERNS``). Every
#: other category — ``compilation_error``, ``test_failure``, ``dependency_error``
#: and ``other``, the default ``categorize_issue`` returns for a diagnostic no
#: pattern matches — names a real failure. The set is read from the category
#: vocabulary's meaning, not inferred from a severity, because Maven prints
#: real failures at ``[WARNING]`` on some plugins.
_INFORMATIONAL_ISSUE_CATEGORIES = frozenset(
    {'javadoc_warning', 'deprecation_warning', 'unchecked_warning', 'openrewrite_info'}
)

#: The Maven phases whose run is a test run: the module-tests canonical of a
#: normal module is ``test``, and the one of a module consuming a reactor test
#: artifact is ``package`` (see ``_maven_cmd_discover._build_commands``).
_TEST_PHASE_GOALS = ('test', 'package')

#: Flags that make a test-phase invocation skip its tests, so an empty test
#: population is what the command asked for rather than a surprise.
_TEST_SKIP_FLAGS = ('-DskipTests', '-Dmaven.test.skip')


def _maven_scope_fn(args: str) -> str:
    """Extract scope from Maven -pl argument.

    Handles both '-pl module' and '-pl=module' forms.
    """
    match = re.search(r'-pl[=\s]+(\S+)', args)
    if match:
        return match.group(1)
    return 'default'


def _maven_build_command_fn(wrapper: str, args: str, log_file: str) -> tuple[list[str], str]:
    """Build Maven command with -l flag for log file output."""
    cmd_parts = [wrapper, '-l', log_file] + args.split()
    command_str = ' '.join(cmd_parts)
    return cmd_parts, command_str


def _indeterminate(result: dict, message: str) -> dict:
    """Render ``result`` as ``indeterminate``, carrying everything it established.

    Everything the execution established travels with the verdict — the
    executor's optional fields included — so a consumer reading ``wrapper``, a
    bound or a future field off this result does not find it absent although
    the build did run. Only the keys ``indeterminate_result`` sets itself (plus
    the failure-renderer inputs that no longer apply) are excluded.
    """
    replaced = {
        'status',
        'error',
        'message',
        'exit_code',
        'duration_seconds',
        'log_file',
        'command',
        'errors',
        'routed_errors',
        'routed_tests_run',
    }
    carried = {name: value for name, value in result.items() if name not in replaced}
    return indeterminate_result(
        message,
        int(result.get('duration_seconds') or 0),
        str(result.get('log_file') or ''),
        str(result.get('command') or ''),
        exit_code=int(result.get('exit_code') or 0),
        **carried,
    )


def apply_selector_miss_guard(result: dict) -> dict:
    """Refuse to call a run green when its Surefire selector matched nothing.

    A ``-Dtest`` selector that matches no test is a wrong command, not a
    passing run and not a failing test. Surefire ends such a run non-zero by
    default and green with ``-Dsurefire.failIfNoSpecifiedTests=false``; both
    shapes are turned into one ``indeterminate`` result naming
    ``TEST_SELECTOR_MATCHED_NOTHING``.

    ``indeterminate`` rather than ``error`` is the recorded choice: an ``error``
    result with a zero exit code reaches the build-failure path, which stores
    every parsed issue and manufactures a synthetic failure row — a verdict out
    of a run that ran no test. Indeterminate stores no finding, synthesises no
    ``errors[]`` row, and still blocks every gate that requires ``success``.

    Args:
        result: A finished execution result (``execute_direct``'s dict).

    Returns:
        The same result unchanged when no selector miss was detected — the
        identity is preserved so a control case can assert it — or an
        ``indeterminate`` result naming the reason.
    """
    status = result.get('status')
    if status not in (STATUS_SUCCESS, STATUS_ERROR):
        return result
    command = str(result.get('command') or '')
    selector = dtest_selector(command)
    # A failed build is suspect whatever the command says (Surefire's own goal
    # failure). A successful one is only suspect when a selector was in play.
    if status == STATUS_SUCCESS and selector is None:
        return result
    try:
        log_text = read_log_text(result['log_file'])
    except (KeyError, OSError):
        # No readable log means no evidence. For an exit-0 selector run that is
        # the whole question — a green would claim the selector ran tests — so
        # the run is named unreadable instead of being trusted.
        if status == STATUS_SUCCESS:
            return _indeterminate(
                result,
                f'{TEST_LOG_UNREADABLE}: the -Dtest run exited 0 but its log could not be read, so '
                'nothing establishes that a test ran — not a green.',
            )
        # A failed build is already not green; its own failure stands.
        return result
    # The zero-collected shape is an EXIT-0 shape. On a failed build only
    # Surefire's explicit "No tests matching pattern" counts, because a reactor
    # can print a zero-test summary for an earlier module and then fail later —
    # and that real failure must not be relabelled as a wrong selector.
    reason = selector_miss_reason(log_text, command if status == STATUS_SUCCESS else None)
    if reason is None:
        return result
    # A reactor run with `--fail-at-end` can carry this selector miss AND a real
    # failure in another module. Converting the whole run to `indeterminate`
    # would drop that module's errors and findings, so the miss only claims the
    # run when every other issue in the log is informational. The miss's own
    # goal-failure line is evidence OF the miss, not a failure beside it.
    if status != STATUS_SUCCESS:
        try:
            issues, _, _ = parse_log(str(result.get('log_file') or ''))
        except (KeyError, OSError):
            return result
        if any(
            issue.category not in _INFORMATIONAL_ISSUE_CATEGORIES and not is_selector_miss_message(issue.message)
            for issue in issues
        ):
            return result

    # Name the selector the log carries when the command line does not show it:
    # a selector set through `.mvn/maven.config`, `MAVEN_OPTS` or a profile, or
    # a Failsafe `-Dit.test` miss, is still printed by the runner.
    pattern = selector or selector_miss_pattern(log_text)
    named = f"'{pattern}'" if pattern else 'the -Dtest selector'
    executed = executed_test_count(log_text)
    if executed:
        # The selector matched in one module and missed in another; claiming the
        # run executed nothing would be false of the modules that did run.
        claim = (
            f'{named} matched no test in at least one module, while the modules that did match '
            f'executed {executed} test(s) — so the run is not a green.'
        )
    else:
        claim = f'{named} matched no test, so the run executed nothing — not a failure and not a green.'
    return _indeterminate(
        result,
        f'{TEST_SELECTOR_MATCHED_NOTHING}: {claim} Surefire prints "No tests matching pattern ... '
        'were executed" unless -Dsurefire.failIfNoSpecifiedTests=false suppresses it.',
    )


def _leading_goal(args: str) -> str | None:
    """Return the first Maven goal of an invocation, or None when it names none."""
    for token in args.split():
        if not token.startswith('-'):
            return token
    return None


def _test_phase_goal(args: str) -> str | None:
    """Return the test-phase goal an invocation leads with, or None.

    Only the LEADING goal decides: a ``clean install`` or a ``verify
    -Ppre-commit`` run also executes tests, but its purpose is the build or the
    gate, and a project that has no test to run there is legitimately green.
    """
    goal = _leading_goal(args)
    if goal not in _TEST_PHASE_GOALS:
        return None
    if any(flag in args for flag in _TEST_SKIP_FLAGS):
        return None
    return goal


def apply_zero_test_guard(result: dict, args: str) -> dict:
    """Refuse to credit a green test-phase run that executed no test.

    A green exit code from ``mvn test`` reads as "the tests passed" to every
    consumer, but a run whose Surefire selector excluded every module — or a
    reactor root that builds no test module — executes nothing and says exactly
    that. Such a run is neither a failure nor a green:

    - a parsed summary reporting zero COLLECTED tests is evidence of an empty
      population;
    - no summary at all on a leading ``test`` goal is the same population: a
      collected test is a summary line, so no summary means nothing was
      collected. A leading ``package`` goal without a summary is a compile and
      package run that reported no tests — only a summary naming a zero
      population is evidence there;
    - an unreadable log is no evidence either, and no evidence never becomes a
      green for a run whose truth lives in its log.

    Args:
        result: A finished execution result (``execute_direct``'s dict).
        args: The Maven arguments the invocation carried.

    Returns:
        The same result unchanged when the run collected a test, when it is no
        test-phase run, or when it was not green — otherwise an
        ``indeterminate`` result naming ``TEST_RUN_EXECUTED_NOTHING``.
    """
    if result.get('status') != STATUS_SUCCESS:
        return result
    goal = _test_phase_goal(args)
    if goal is None:
        return result
    try:
        log_text = read_log_text(result['log_file'])
    except (KeyError, OSError):
        return _indeterminate(
            result,
            f'{TEST_LOG_UNREADABLE}: the {goal} run exited 0 but its log could not be read, so '
            'nothing establishes that a test ran — not a green.',
        )
    collected = collected_test_count(log_text)
    if collected:
        return result
    if collected == 0:
        evidence = "the run's log reports zero collected tests, so nothing executed"
    elif goal == 'test':
        evidence = 'the log carries no Surefire or Failsafe test summary, so the run collected and executed nothing'
    else:
        return result
    return _indeterminate(
        result,
        f'{TEST_RUN_EXECUTED_NOTHING}: {evidence} — not a failure and not a green, because a test '
        'run that executed no test credits no gate.',
    )


def _selector_miss_guard(inner):
    """Wrap the factory's execute so the run-path truth guards run on every route.

    A routed build re-enters this factory inside the daemon child, so both guards
    apply there too — which is also why they must not read a routed job log: this
    wrapper only ever sees the in-process result. The wrapper names
    ``explicit_timeout`` and ``plan_id`` explicitly and forwards BOTH on its
    single inner call, as the factory's wrapper contract requires.
    """

    def execute_direct(
        args: str,
        command_key: str,
        default_timeout: int = DEFAULT_BUILD_TIMEOUT,
        project_dir: str = '.',
        env_vars: dict[str, str] | None = None,
        working_dir: str | None = None,
        explicit_timeout: int | None = None,
        *,
        plan_id: str,
    ):
        result = inner(
            args=args,
            command_key=command_key,
            default_timeout=default_timeout,
            project_dir=project_dir,
            env_vars=env_vars,
            working_dir=working_dir,
            explicit_timeout=explicit_timeout,
            plan_id=plan_id,
        )
        guarded = apply_selector_miss_guard(result)
        return apply_zero_test_guard(guarded, args)

    return execute_direct


_CONFIG = ExecuteConfig(
    tool_name='maven',
    unix_wrapper='mvnw',
    windows_wrapper='mvnw.cmd',
    system_fallback='mvn',
    capture_strategy=CaptureStrategy.TOOL_LOG_FLAG,
    build_command_fn=_maven_build_command_fn,
    scope_fn=_maven_scope_fn,
    command_key_fn=default_command_key_fn,
    default_timeout=DEFAULT_BUILD_TIMEOUT,
    min_timeout=MAVEN_OUTER_FLOOR_SECONDS,
)

execute_direct, cmd_run = create_execute_handlers(_CONFIG, parse_log, wrap_execute_fn=_selector_miss_guard)
