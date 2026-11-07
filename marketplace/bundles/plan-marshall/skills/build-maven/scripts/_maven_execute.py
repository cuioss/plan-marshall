#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Maven command execution — config-driven via execute handler factory.

Provides:
- execute_direct(): Foundation API for Maven command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)
- apply_selector_miss_guard(): the run-path truth check for a ``-Dtest`` miss

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
    TEST_SELECTOR_MATCHED_NOTHING,
    dtest_selector,
    parse_log,
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
    # A failed build is suspect whatever the command says (Surefire's own goal
    # failure). A successful one is only suspect when a selector was in play.
    if status == STATUS_SUCCESS and dtest_selector(command) is None:
        return result
    try:
        log_text = read_log_text(result['log_file'])
    except (KeyError, OSError):
        # No readable log means no evidence; the run's own status stands.
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
    # run when it is the ONLY failure in the log.
    if status != STATUS_SUCCESS:
        issues, _, _ = parse_log(str(result.get('log_file') or ''))
        if any(issue.category in ('test_failure', 'compilation_error') for issue in issues):
            return result

    selector = dtest_selector(command)
    named = f"'{selector}'" if selector else 'the -Dtest selector'
    # Everything the execution established travels with the verdict — the
    # executor's optional fields included — so a consumer reading `wrapper`, a
    # bound or a future field off this result does not find it absent although
    # the build did run. Only the keys `indeterminate_result` sets itself (plus
    # the failure-renderer inputs that no longer apply) are excluded.
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
        f'{TEST_SELECTOR_MATCHED_NOTHING}: {named} matched no test, so the run executed nothing — '
        'not a failure and not a green. Surefire prints "No tests matching pattern ... were '
        'executed" unless -Dsurefire.failIfNoSpecifiedTests=false suppresses it.',
        int(result.get('duration_seconds') or 0),
        str(result.get('log_file') or ''),
        command,
        exit_code=int(result.get('exit_code') or 0),
        **carried,
    )


def _selector_miss_guard(inner):
    """Wrap the factory's execute so the selector guard runs on every route.

    A routed build re-enters this factory inside the daemon child, so the guard
    applies there too; the wrapper names ``explicit_timeout`` and ``plan_id``
    explicitly and forwards BOTH on its single inner call, as the factory's
    wrapper contract requires.
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
        return apply_selector_miss_guard(result)

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
