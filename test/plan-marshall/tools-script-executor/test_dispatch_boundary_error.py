#!/usr/bin/env python3
"""
Unit tests for the executor's dispatch-boundary non-zero-exit guard.

Background
----------
The executor (``.plan/execute-script.py``) emits a single
``[ERROR] (plan-marshall:execute-script:{exit_code})`` line to the plan's
``work.log`` every time a dispatched script exits non-zero. The emission is
implemented by ``emit_dispatch_failure_work_log`` in the executor template
and is guarded by three rules:

1. Successful dispatches (exit_code == 0) never call the function — that
   is enforced at the call site in ``main()`` and is exercised by
   ``test_execute_script.py``. These tests focus on the function's own
   behaviour.
2. Dispatching ``plan-marshall:manage-logging:manage-logging`` itself MUST
   be a no-op — otherwise a manage-logging failure that tried to log itself
   would recurse forever.
3. Exit code 2 is classified as ``argparse_rejection`` (Python's argparse
   convention) and every other non-zero exit code is classified as
   ``script_internal_failure``.

Approach
--------
The executor module is loaded via the helper from
``test_execute_script.py``. We replace ``executor.log_entry`` with a
``MagicMock`` so the function records each call without touching the file
system, then exercise the boundary function directly with synthetic
inputs (notation, exit code, stderr, args, audit-plan-id).

This keeps the tests fully hermetic — no temp directories, no subprocess,
no real plan structure — and pins down exactly which arguments
``log_entry`` would receive in production. The wider subprocess-level
behaviour is already covered by ``test_execute_script.py``;
this file is the unit-level guard around the boundary's three rules.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Import the executor-module loader from the sibling subprocess-test file.
sys.path.insert(0, str(Path(__file__).parent))
from test_execute_script import load_executor_module  # noqa: E402

# Notation used as a generic "normal" failing script in the tests below.
TEST_NOTATION = 'plan-marshall:manage-files:manage-files'

# Notation that MUST trigger the recursion guard in the boundary function.
MANAGE_LOGGING_NOTATION = 'plan-marshall:manage-logging:manage-logging'

# Stderr blob used by the happy-path failure tests. Kept short so the
# truncation rule is exercised by a dedicated test below rather than by
# every test in the file.
DEFAULT_STDERR = 'boom: something went wrong'

# Plan id forwarded as ``--plan-id`` in the dispatched-script args. Picked
# arbitrarily — the boundary function only cares that it can be extracted.
DEFAULT_PLAN_ID = 'unit-test-plan'


@pytest.fixture
def executor_with_mock_log_entry():
    """
    Load the executor module and swap out ``log_entry`` for a MagicMock.

    The fixture yields a tuple ``(executor, mock_log_entry)`` so each test
    can drive the boundary function via the real module API and then
    inspect the recorded calls without involving any disk I/O.
    """
    executor = load_executor_module()
    mock_log_entry = MagicMock()
    executor.log_entry = mock_log_entry
    return executor, mock_log_entry


def test_emit_records_script_internal_failure_for_exit_code_1(executor_with_mock_log_entry):
    """
    Exit code 1 lands a single ``log_entry`` call with
    ``failure_kind=script_internal_failure`` and the notation embedded
    verbatim into the message.
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    executor.emit_dispatch_failure_work_log(
        notation=TEST_NOTATION,
        exit_code=1,
        stdout='',
        stderr=DEFAULT_STDERR,
        script_args=['read', '--plan-id', DEFAULT_PLAN_ID, '--file', 'foo.json'],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 1, (
        f'Expected exactly one log_entry call for exit_code=1, got {mock_log_entry.call_count}'
    )

    call_args = mock_log_entry.call_args
    positional = call_args.args
    assert positional[0] == 'work', f"Expected log_type='work', got {positional[0]!r}"
    assert positional[1] == DEFAULT_PLAN_ID, f"Expected plan_id={DEFAULT_PLAN_ID!r}, got {positional[1]!r}"
    assert positional[2] == 'ERROR', f"Expected level='ERROR', got {positional[2]!r}"

    message = positional[3]
    assert '[ERROR] (plan-marshall:execute-script:1)' in message, (
        f'Caller-prefix line did not embed exit code 1 in tag: {message!r}'
    )
    assert f'notation={TEST_NOTATION}' in message, f'Notation missing from message: {message!r}'
    assert 'exit_code=1' in message, f'exit_code=1 missing from message: {message!r}'
    assert 'failure_kind=script_internal_failure' in message, (
        f'Expected failure_kind=script_internal_failure in: {message!r}'
    )
    # With empty stdout, the detail field falls back to stderr (precedence 3).
    assert f'detail={DEFAULT_STDERR}' in message, f'stderr-derived detail missing from message: {message!r}'


def test_emit_records_script_internal_failure_for_unusual_exit_code(executor_with_mock_log_entry):
    """
    Any non-zero exit code that is NOT 2 maps to
    ``script_internal_failure``. Picks 42 as a representative non-1
    non-2 value to make sure the branch is not hard-coded to ``== 1``.
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    executor.emit_dispatch_failure_work_log(
        notation=TEST_NOTATION,
        exit_code=42,
        stdout='',
        stderr=DEFAULT_STDERR,
        script_args=['--plan-id', DEFAULT_PLAN_ID],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 1
    message = mock_log_entry.call_args.args[3]
    assert 'exit_code=42' in message, f'exit_code=42 missing from: {message!r}'
    assert 'failure_kind=script_internal_failure' in message, (
        f'Unusual exit codes must still map to script_internal_failure: {message!r}'
    )
    assert '[ERROR] (plan-marshall:execute-script:42)' in message, (
        f'Caller-prefix line did not embed exit code 42: {message!r}'
    )


def test_emit_records_argparse_rejection_for_exit_code_2(executor_with_mock_log_entry):
    """
    Exit code 2 — Python's argparse convention for parse failures — maps
    to ``failure_kind=argparse_rejection`` and lands a single
    ``log_entry`` call with the canonical message shape.
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    argparse_stderr = (
        "usage: manage-files.py [-h] ...\n"
        "manage-files.py: error: unrecognized arguments: --bogus"
    )

    executor.emit_dispatch_failure_work_log(
        notation=TEST_NOTATION,
        exit_code=2,
        stdout='',
        stderr=argparse_stderr,
        script_args=['read', '--plan-id', DEFAULT_PLAN_ID, '--bogus'],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 1, (
        f'Expected exactly one log_entry call for exit_code=2, got {mock_log_entry.call_count}'
    )

    positional = mock_log_entry.call_args.args
    assert positional[0] == 'work'
    assert positional[1] == DEFAULT_PLAN_ID
    assert positional[2] == 'ERROR'

    message = positional[3]
    assert 'exit_code=2' in message, f'exit_code=2 missing from message: {message!r}'
    assert 'failure_kind=argparse_rejection' in message, (
        f'Exit code 2 must classify as argparse_rejection: {message!r}'
    )
    assert '[ERROR] (plan-marshall:execute-script:2)' in message, (
        f'Caller-prefix line did not embed exit code 2: {message!r}'
    )
    # Newlines in the captured stderr must be collapsed so the work.log
    # entry stays single-line — this is part of the boundary's contract
    # and the most natural place to assert it.
    assert '\n' not in message, (
        f'Boundary message must be single-line; embedded newline found: {message!r}'
    )


def test_emit_suppresses_log_for_manage_logging_recursion_target(executor_with_mock_log_entry):
    """
    Dispatching ``plan-marshall:manage-logging:manage-logging`` itself
    with a non-zero exit code MUST NOT call ``log_entry`` — that would
    recurse into the executor and loop until the OS killed the process.

    This is the only suppression case: the notation is in
    ``_DISPATCH_FAILURE_SUPPRESS_NOTATIONS`` and the function returns
    before extracting the plan id.
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    executor.emit_dispatch_failure_work_log(
        notation=MANAGE_LOGGING_NOTATION,
        exit_code=1,
        stdout='',
        stderr='manage-logging failed: bad arg',
        script_args=['work', '--plan-id', DEFAULT_PLAN_ID, '--level', 'INFO', '--message', 'x'],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 0, (
        f'manage-logging dispatch must NEVER call log_entry from the boundary '
        f'(recursion guard). Got {mock_log_entry.call_count} call(s).'
    )


def test_emit_suppresses_log_for_manage_logging_recursion_even_with_argparse_exit(
    executor_with_mock_log_entry,
):
    """
    The recursion guard fires independent of failure kind — exit code 2
    (argparse) on manage-logging is still suppressed. This pins the
    guard to the notation list, not to a particular exit-code class.
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    executor.emit_dispatch_failure_work_log(
        notation=MANAGE_LOGGING_NOTATION,
        exit_code=2,
        stdout='',
        stderr="argparse: error",
        script_args=['work', '--plan-id', DEFAULT_PLAN_ID, '--bogus'],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 0, (
        f'manage-logging argparse failure must also be suppressed; got '
        f'{mock_log_entry.call_count} call(s).'
    )


def test_emit_uses_audit_plan_id_when_script_args_lack_plan_id(executor_with_mock_log_entry):
    """
    When the dispatched script's args do not carry ``--plan-id``, the
    boundary falls back to the executor's own ``--audit-plan-id`` flag.
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    executor.emit_dispatch_failure_work_log(
        notation=TEST_NOTATION,
        exit_code=1,
        stdout='',
        stderr=DEFAULT_STDERR,
        script_args=['read', '--file', 'foo.json'],
        audit_plan_id='audit-fallback-plan',
    )

    assert mock_log_entry.call_count == 1
    positional = mock_log_entry.call_args.args
    assert positional[1] == 'audit-fallback-plan', (
        f"Expected audit_plan_id fallback to be used, got plan_id={positional[1]!r}"
    )


def test_emit_drops_entry_when_no_plan_id_available(executor_with_mock_log_entry):
    """
    When neither the dispatched-script args nor ``audit_plan_id`` carry
    a plan id, work.log is plan-scoped and unwritable — the entry is
    dropped silently. The script-execution.log entry (handled elsewhere
    by ``log_script_execution``) still records the failure globally.
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    executor.emit_dispatch_failure_work_log(
        notation=TEST_NOTATION,
        exit_code=1,
        stdout='',
        stderr=DEFAULT_STDERR,
        script_args=['read', '--file', 'foo.json'],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 0, (
        f'Boundary must drop the entry when no plan_id is available; got '
        f'{mock_log_entry.call_count} call(s).'
    )


def test_emit_truncates_long_detail_to_configured_limit(executor_with_mock_log_entry):
    """
    Detail text longer than ``_DISPATCH_FAILURE_DETAIL_LIMIT`` is
    truncated with the ``...[truncated]`` sentinel so a single failed
    dispatch can't dominate the plan's work.log. Here stdout is empty, so
    the oversized stderr is the chosen detail stream (precedence 3).
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    limit = executor._DISPATCH_FAILURE_DETAIL_LIMIT
    oversized = 'A' * (limit + 200)

    executor.emit_dispatch_failure_work_log(
        notation=TEST_NOTATION,
        exit_code=1,
        stdout='',
        stderr=oversized,
        script_args=['--plan-id', DEFAULT_PLAN_ID],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 1
    message = mock_log_entry.call_args.args[3]
    assert '...[truncated]' in message, f'Truncation sentinel missing from oversized detail: {message!r}'
    # The retained detail slice should be exactly the configured limit.
    # The message also embeds non-detail fragments (notation, exit_code, ...)
    # so we assert the slice length indirectly: the run of leading 'A's
    # preceding the sentinel equals ``limit``.
    a_run = 'A' * limit
    assert a_run in message, f'Expected exactly {limit} A characters before the truncation sentinel'
    assert ('A' * (limit + 1)) not in message, (
        f'detail appears longer than the configured limit of {limit} characters: {message!r}'
    )
