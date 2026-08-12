#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Result construction and log file management utilities.

Shared infrastructure for build command result handling across build systems.
Used by domain extensions (pm-dev-java, pm-dev-frontend) for consistent result formatting.

A build that does not finish produces two conditions that are NOT failures and
are NOT each other — an outer-budget ``timeout`` and an external ``killed`` — and
each has its own constructor here. Neither is ever folded into ``error``: an
externally-killed build is not evidence that the build is broken, and presenting
it as one manufactures a failure the build never reported.

Usage:
    from build_result import (
        create_log_file, success_result, error_result, timeout_result,
        killed_result,
        DirectCommandResult,
        STATUS_SUCCESS, STATUS_ERROR, STATUS_TIMEOUT, STATUS_KILLED
    )

    # Create log file for build output, under the resolving plan's directory
    log_file = create_log_file("maven", "core-api", plan_id="my-plan")

    # Build success result
    result = success_result(
        duration_seconds=45,
        log_file=log_file,
        command="./mvnw clean verify"
    )

    # Type hint for {build_system}_execute.py implementations
    def execute_direct(...) -> DirectCommandResult:
        ...
"""

from datetime import UTC, datetime
from typing import Literal, TypedDict

from file_ops import get_build_results_dir

# =============================================================================
# Type Definitions
# =============================================================================


class DirectCommandResult(TypedDict, total=False):
    """Standard return structure for {build_system}_execute.py implementations.

    This TypedDict defines the contract for the low-level command execution
    layer used by build system extensions (maven_execute.py, gradle_execute.py,
    npm_execute.py).

    Note: total=False because optional fields vary by build system. Required
    fields are enforced at runtime via validate_result() and REQUIRED_FIELDS,
    not via the type system. This avoids needing Python 3.11+ NotRequired.

    Required fields (always present):
        status: Execution outcome. ``killed`` is a NON-FINISH, distinct from
            ``error`` (the build ran and failed) and from ``timeout`` (the
            build exceeded its own outer budget) — see :func:`killed_result`.
        exit_code: Process exit code (-1 for timeout/execution failure;
            the negative ``-N`` signal code for ``killed``).
        duration_seconds: Actual execution time.
        log_file: Path to captured output (per R1 requirement).
        command: Full command that was executed.

    Optional fields (build-system specific):
        timeout_used_seconds: Timeout that was applied.
        wrapper: Maven/Gradle/Python wrapper path used.
        command_type: npm command type ("npm" or "npx").
        error: Error message (on error/timeout only).

    Example (success):
        {
            "status": "success",
            "exit_code": 0,
            "duration_seconds": 45,
            "log_file": ".plan/local/plans/my-plan/build-results/default/maven-2026-01-06.log",
            "command": "./mvnw clean verify",
            "wrapper": "./mvnw"
        }

    Example (error):
        {
            "status": "error",
            "exit_code": 1,
            "duration_seconds": 23,
            "log_file": ".plan/local/plans/my-plan/build-results/default/npm-2026-01-06.log",
            "command": "npm run test",
            "command_type": "npm",
            "error": "Build failed with exit code 1"
        }
    """

    # Required fields
    status: Literal['success', 'error', 'timeout', 'killed', 'indeterminate']
    exit_code: int
    duration_seconds: int
    log_file: str
    command: str
    # Optional fields
    timeout_used_seconds: int
    wrapper: str  # Maven/Gradle/Python: wrapper path used
    command_type: str  # npm: "npm" or "npx"
    error: str  # Error message (on error/timeout/killed only)
    message: str  # Operator-facing detail (on killed only)


# =============================================================================
# Constants
# =============================================================================


TIMESTAMP_FORMAT = '%Y-%m-%d-%H%M%S'
"""Timestamp format for log file names."""

# Status values
STATUS_SUCCESS = 'success'
"""Build completed with exit code 0."""

STATUS_ERROR = 'error'
"""Build failed or execution error occurred."""

STATUS_TIMEOUT = 'timeout'
"""Build exceeded timeout limit."""

STATUS_KILLED = 'killed'
"""Build child was terminated by a signal nobody in this stack sent.

Distinct from :data:`STATUS_ERROR` (the build ran to completion and reported a
failure) and from :data:`STATUS_TIMEOUT` (the build exceeded the outer budget
this stack applied, so the kill signal WAS ours). A ``killed`` build reported
nothing at all — its log is a truncation, not a verdict — so no consumer may
read it as a red build, and none may read it as a timeout either.
"""

STATUS_INDETERMINATE = 'indeterminate'
"""The outcome could not be determined — it is NOT any of the four above.

This is the value for a case no branch resolves: a producer reported something
this layer cannot interpret (e.g. a daemon speaking a terminal status a
version-skewed client does not know — the condition ``manage-build-server
status`` flags as ``binary_diverges``). Folding it into ``error`` would claim a
failure nobody observed; folding it into ``success`` would be a green nothing
substantiates. It is neither, and it must stay neither.

**Deliberately NOT wrapper-claimable at the ledger boundary.**
``_ledger_core.WRAPPER_CLAIMABLE_BUILD_STATUSES`` excludes it, so
``_derive_build_status`` falls through to its own derived-only ``unknown`` — the
ledger's name for the same condition. That is the intended route, not an
oversight: a wrapper may report that it could not determine the outcome, but the
boundary derives the verdict of record itself rather than accepting the claim.
Do NOT "fix" this by adding ``indeterminate`` to the claimable set.
"""

# Error type identifiers
ERROR_BUILD_FAILED = 'build_failed'
"""Build process returned non-zero exit code."""

ERROR_TIMEOUT = 'timeout'
"""Build exceeded timeout limit."""

ERROR_KILLED = 'killed'
"""Build child died by a signal this stack did not send."""

ERROR_INDETERMINATE = 'indeterminate'
"""The outcome could not be determined at all — see :data:`STATUS_INDETERMINATE`."""

KILLED_MESSAGE = 'externally killed — not flaky, do not blind-retry'
"""Operator-facing detail carried by every ``killed`` result.

The literal is shared with the daemon-side kill path
(``_marshalld_supervisor`` / ``manage-change-ledger classify-outcome``) so the
in-process and routed legs render the same sentence for the same condition.
"""

ERROR_EXECUTION_FAILED = 'execution_failed'
"""Failed to execute build command (e.g., subprocess error)."""

ERROR_WRAPPER_NOT_FOUND = 'wrapper_not_found'
"""Build wrapper (mvnw, gradlew) not found."""

ERROR_LOG_FILE_FAILED = 'log_file_failed'
"""Failed to create log file for build output."""


# =============================================================================
# Required Result Fields
# =============================================================================

REQUIRED_FIELDS = {'status', 'exit_code', 'duration_seconds', 'log_file', 'command'}
"""Fields that must be present in every result dict."""


# =============================================================================
# Log File Management
# =============================================================================


def create_log_file(build_system: str, scope: str = 'default', *, plan_id: str) -> str | None:
    """Create a timestamped log file for build output.

    Creates the directory structure if needed and returns the absolute path
    to a new log file. The log lands in the build-results directory of the
    plan that caused the build, resolved by the single owner of that path,
    :func:`file_ops.get_build_results_dir`.

    Args:
        build_system: Build system name (maven, gradle, npm).
        scope: Module scope or "default" for root builds.
        plan_id: Plan identifier the build is attributed to, or the
            ``NO_PLAN`` sentinel for a genuinely plan-less build. Required
            keyword — a build result with no owning plan is not a valid
            state, so no call site may omit the attribution.

    Returns:
        Absolute path to log file, or None if creation failed.

    Pattern:
        {plan_dir}/build-results/{scope}/{build_system}-{timestamp}.log

    Example:
        >>> log_file = create_log_file("maven", "core-api", plan_id="my-plan")
        >>> log_file
        '/home/user/project/.plan/local/plans/my-plan/build-results/core-api/maven-2026-01-04-141523.log'
    """
    try:
        timestamp = datetime.now(UTC).strftime(TIMESTAMP_FORMAT)
        log_filename = f'{build_system}-{timestamp}.log'

        # Constrain the resolved log dir to the sanctioned base: reject a
        # scope that escapes the base via .. segments or an absolute path.
        unresolved_base = get_build_results_dir(plan_id)
        base = unresolved_base.resolve()
        candidate = (base / scope).resolve()
        if candidate != base and base not in candidate.parents:
            return None

        log_dir = unresolved_base / scope
        log_dir.mkdir(parents=True, exist_ok=True)

        log_path = log_dir / log_filename
        # Touch the file to ensure it exists
        log_path.touch()

        return str(log_path)
    except (OSError, PermissionError):
        return None


# =============================================================================
# Result Construction
# =============================================================================


def success_result(duration_seconds: int, log_file: str, command: str, **extra) -> dict:
    """Build success result dict.

    Args:
        duration_seconds: Actual execution time in seconds.
        log_file: Path to captured output file.
        command: Full command that was executed.
        **extra: Additional fields to include (e.g., wrapper, command_type).

    Returns:
        Result dict with status="success" and exit_code=0.

    Example:
        >>> result = success_result(45, "/path/to/log", "./mvnw clean verify")
        >>> result["status"]
        'success'
        >>> result["exit_code"]
        0
    """
    result = {
        'status': STATUS_SUCCESS,
        'exit_code': 0,
        'duration_seconds': duration_seconds,
        'log_file': log_file,
        'command': command,
    }
    result.update(extra)
    return result


def error_result(error: str, exit_code: int, duration_seconds: int, log_file: str, command: str, **extra) -> dict:
    """Build error result dict.

    Args:
        error: Error type identifier (e.g., ERROR_BUILD_FAILED).
        exit_code: Process exit code (non-zero, or -1 for execution failures).
        duration_seconds: Actual execution time in seconds.
        log_file: Path to captured output file.
        command: Full command that was executed.
        **extra: Additional fields to include (e.g., errors, warnings, tests).

    Returns:
        Result dict with status="error" and specified error details.

    Example:
        >>> result = error_result(
        ...     ERROR_BUILD_FAILED, 1, 23, "/path/to/log", "./mvnw clean verify"
        ... )
        >>> result["status"]
        'error'
        >>> result["error"]
        'build_failed'
    """
    result = {
        'status': STATUS_ERROR,
        'error': error,
        'exit_code': exit_code,
        'duration_seconds': duration_seconds,
        'log_file': log_file,
        'command': command,
    }
    result.update(extra)
    return result


def timeout_result(timeout_used_seconds: int, duration_seconds: int, log_file: str, command: str, **extra) -> dict:
    """Build timeout result dict.

    Args:
        timeout_used_seconds: Timeout that was applied.
        duration_seconds: Actual execution time before timeout.
        log_file: Path to captured output file.
        command: Full command that was executed.
        **extra: Additional fields to include.

    Returns:
        Result dict with status="timeout", error="timeout", and exit_code=-1.

    Example:
        >>> result = timeout_result(300, 300, "/path/to/log", "./mvnw clean verify")
        >>> result["status"]
        'timeout'
        >>> result["exit_code"]
        -1
    """
    result = {
        'status': STATUS_TIMEOUT,
        'error': ERROR_TIMEOUT,
        'exit_code': -1,
        'timeout_used_seconds': timeout_used_seconds,
        'duration_seconds': duration_seconds,
        'log_file': log_file,
        'command': command,
    }
    result.update(extra)
    return result


def killed_result(exit_code: int, duration_seconds: int, log_file: str, command: str, **extra) -> dict:
    """Build an externally-killed result dict.

    A ``killed`` result records that the build child died by a signal that
    neither this stack's outer timeout nor the build itself produced. It is a
    NON-FINISH, and it is deliberately its own status rather than an ``error``
    or a ``timeout``:

    * NOT ``error`` — an ``error`` asserts the build ran and reported a
      failure. A killed build reported nothing; its log is truncated evidence,
      so presenting it as a failure manufactures one.
    * NOT ``timeout`` — a ``timeout`` asserts the build exceeded a budget THIS
      stack set and that this stack sent the kill. An external kill says
      nothing about the budget, so folding it into ``timeout`` would blame a
      bound that never fired.

    Args:
        exit_code: The observed exit code — the negative ``-N`` signal code
            when available; ``-1`` when the code could not be recovered.
        duration_seconds: Wall-clock time before the kill. This is a
            TRUNCATION, not a measurement of the command (see
            :mod:`_build_execute`, which therefore never feeds it to the
            adaptive-timeout learner).
        log_file: Path to the partial captured output.
        command: Full command that was executed.
        **extra: Additional fields to include.

    Returns:
        Result dict with status="killed", error="killed", and the shared
        no-blind-retry :data:`KILLED_MESSAGE`.

    Example:
        >>> result = killed_result(-9, 42, "/path/to/log", "./pw verify")
        >>> result["status"]
        'killed'
        >>> result["exit_code"]
        -9
    """
    result = {
        'status': STATUS_KILLED,
        'error': ERROR_KILLED,
        'message': KILLED_MESSAGE,
        'exit_code': exit_code,
        'duration_seconds': duration_seconds,
        'log_file': log_file,
        'command': command,
    }
    result.update(extra)
    return result


def indeterminate_result(
    reason: str, duration_seconds: int, log_file: str, command: str, exit_code: int = -1, **extra
) -> dict:
    """Build a result whose outcome could not be determined.

    The escape hatch that keeps an unresolvable case from being folded into its
    nearest neighbour. Use it where a branch genuinely cannot decide — never as a
    catch-all for a case that simply was not enumerated, because an
    ``indeterminate`` result blocks every gate that requires ``success`` and
    tells the operator only that nothing could be concluded.

    Args:
        reason: Why the outcome could not be determined, specific enough to act
            on (name the unrecognised value, not just its category).
        duration_seconds: Wall-clock time observed, if any.
        log_file: Path to whatever output exists.
        command: Full command that was executed.
        exit_code: Observed exit code; ``-1`` when none is meaningful.
        **extra: Additional fields to include.

    Returns:
        Result dict with status="indeterminate" and the reason as ``message``.

    Example:
        >>> result = indeterminate_result("daemon reported 'quiesced'", 3, "/l", "./pw verify")
        >>> result["status"]
        'indeterminate'
    """
    result = {
        'status': STATUS_INDETERMINATE,
        'error': ERROR_INDETERMINATE,
        'message': reason,
        'exit_code': exit_code,
        'duration_seconds': duration_seconds,
        'log_file': log_file,
        'command': command,
    }
    result.update(extra)
    return result


def validate_result(result: dict) -> tuple[bool, list]:
    """Validate result dict has required fields.

    Checks that all required fields are present in the result dictionary.

    Args:
        result: Result dict to validate.

    Returns:
        Tuple of (is_valid, list_of_missing_fields).
        is_valid is True if all required fields are present.

    Example:
        >>> valid, missing = validate_result({"status": "success"})
        >>> valid
        False
        >>> missing
        ['command', 'duration_seconds', 'exit_code', 'log_file']
    """
    if not isinstance(result, dict):
        return False, sorted(REQUIRED_FIELDS)

    missing = sorted(field for field in REQUIRED_FIELDS if field not in result)
    return len(missing) == 0, missing


class TruthfulStatusError(AssertionError):
    """Raised when a result claims success while holding a non-zero exit code.

    Fail-closed invariant (ADR-009): a build result must never advertise
    ``status='success'`` while carrying a non-zero ``exit_code``. That
    combination is the exact "reports success while holding a non-zero return
    code" reintroduction the truthful-status guard exists to prevent.
    """


def assert_truthful_status(result: dict) -> None:
    """Assert a result never claims success over a non-zero exit code.

    Pure invariant check on a constructed result dict — it inspects, never
    mutates. Raises :class:`TruthfulStatusError` when ``result['status']`` is
    ``'success'`` while ``result['exit_code']`` is a non-zero integer, so any
    caller that assembles an untruthful success result fails loudly at the emit
    choke point rather than reporting green. A non-success result, a success
    result with ``exit_code == 0``, an absent ``exit_code`` key, or an explicit
    ``exit_code`` of ``None`` (an indeterminate value, treated safely) all pass
    silently. Mirrors the PLAN-13 #950 D4 fail-closed provisioning-write pattern.

    Args:
        result: The constructed result dict about to be emitted.

    Raises:
        TruthfulStatusError: When status is success but exit_code != 0.
    """
    exit_code = result.get('exit_code')
    if result.get('status') == STATUS_SUCCESS and exit_code is not None and exit_code != 0:
        raise TruthfulStatusError(
            f"truthful-status violation: result reports status='success' with "
            f"exit_code={result.get('exit_code')!r} (expected 0); "
            f"command={result.get('command')!r}"
        )
