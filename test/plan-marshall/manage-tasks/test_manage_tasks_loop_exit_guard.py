#!/usr/bin/env python3
# ruff: noqa: I001
"""Tests for manage-tasks.py loop-exit-guard subcommand.

Split from test_manage_tasks.py: covers the script-level enforcement of the
phase-5-execute "pending > 0 → must continue" invariant pinned by lesson
2026-05-10-15-001.

Contract:
  - pending > 0 → status: continue, pending_count > 0, pending_ids non-empty
  - pending == 0 → status: success, pending_count == 0, pending_ids == []

Behaviour parity is checked against `cmd_list --status pending` over the
same fixtures (both reads target the same on-disk machinery via
`get_all_tasks`).
"""

from argparse import Namespace

from conftest import run_script

from _helpers import (
    SCRIPT_PATH,
    _finalize_step_ns,
    _list_ns,
    add_basic_task,
    cmd_finalize_step,
    cmd_list,
    cmd_loop_exit_guard,
)


def _loop_exit_guard_ns(plan_id='test-plan'):
    """Build Namespace for cmd_loop_exit_guard (single --plan-id field)."""
    return Namespace(plan_id=plan_id)


def test_loop_exit_guard_continue_when_pending_tasks_remain(plan_context):
    """pending > 0 yields status: continue with pending_count and pending_ids set."""
    add_basic_task(
        plan_id='guard-continue',
        title='First',
        deliverable=1,
        steps=['src/main/java/File.java'],
    )
    add_basic_task(
        plan_id='guard-continue',
        title='Second',
        deliverable=2,
        steps=['src/main/java/File.java'],
    )

    result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-continue'))

    assert result['status'] == 'continue'
    assert result['plan_id'] == 'guard-continue'
    assert result['pending_count'] == 2
    assert sorted(result['pending_ids']) == [1, 2]
    assert 'pending' in result['message'].lower()


def test_loop_exit_guard_success_when_queue_empty(plan_context):
    """pending == 0 yields status: success with pending_count: 0 and empty list."""
    result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-empty'))

    assert result['status'] == 'success'
    assert result['plan_id'] == 'guard-empty'
    assert result['pending_count'] == 0
    assert result['pending_ids'] == []


def test_loop_exit_guard_success_when_only_done_tasks_remain(plan_context):
    """All tasks done → status: success even when total > 0."""
    add_basic_task(
        plan_id='guard-all-done',
        title='Only',
        deliverable=1,
        steps=['src/main/java/File.java'],
    )
    cmd_finalize_step(_finalize_step_ns(plan_id='guard-all-done', task=1, step=1, outcome='done'))

    result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-all-done'))

    assert result['status'] == 'success'
    assert result['pending_count'] == 0
    assert result['pending_ids'] == []


def test_loop_exit_guard_ignores_blocked_and_failed_status(plan_context):
    """Only `pending` status counts towards the guard — `blocked`/`failed` are not pending."""
    add_basic_task(
        plan_id='guard-mixed',
        title='Pending one',
        deliverable=1,
        steps=['src/main/java/A.java'],
    )
    add_basic_task(
        plan_id='guard-mixed',
        title='Will be failed',
        deliverable=2,
        steps=['src/main/java/B.java'],
    )
    cmd_finalize_step(
        _finalize_step_ns(plan_id='guard-mixed', task=2, step=1, outcome='failed', reason='intentional')
    )

    result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-mixed'))

    assert result['status'] == 'continue'
    assert result['pending_count'] == 1
    assert result['pending_ids'] == [1]


def test_loop_exit_guard_parity_with_list_status_pending(plan_context):
    """The guard reads the same on-disk state as `list --status pending`."""
    add_basic_task(plan_id='guard-parity', title='A', deliverable=1, steps=['src/A.java'])
    add_basic_task(plan_id='guard-parity', title='B', deliverable=2, steps=['src/B.java'])
    add_basic_task(plan_id='guard-parity', title='C', deliverable=3, steps=['src/C.java'])
    cmd_finalize_step(_finalize_step_ns(plan_id='guard-parity', task=1, step=1, outcome='done'))

    guard = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-parity'))
    listed = cmd_list(_list_ns(plan_id='guard-parity', status='pending'))

    listed_ids = sorted(row['number'] for row in listed['tasks_table'])
    assert guard['status'] == 'continue'
    assert guard['pending_count'] == len(listed_ids) == listed['counts']['pending']
    assert sorted(guard['pending_ids']) == listed_ids


def test_loop_exit_guard_cli_subcommand_registered(plan_context):
    """End-to-end subprocess invocation surfaces the guard via the CLI."""
    add_basic_task(plan_id='guard-cli', title='One', deliverable=1, steps=['src/X.java'])

    result = run_script(
        SCRIPT_PATH,
        'loop-exit-guard',
        '--plan-id',
        'guard-cli',
    )

    assert result.returncode == 0
    assert 'status: continue' in result.stdout
    assert 'pending_count: 1' in result.stdout
