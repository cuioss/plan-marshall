#!/usr/bin/env python3
# ruff: noqa: I001
"""Tests for manage-tasks.py loop-exit-guard subcommand.

Split from test_manage_tasks.py: covers the script-level enforcement of the
phase-5-execute "unfinished > 0 → must continue" invariant. The predicate
is the union of `pending` AND `in_progress` task buckets, both of which
block clean exit. Origin: lesson 2026-05-10-15-001 (pending-only predicate)
broadened by plan execute-phase-resume-dispatches-with-empty-pending
(in_progress added to the blocking set).

Contract:
  - pending > 0 OR in_progress > 0 → status: continue,
    {pending,in_progress}_count and {pending,in_progress}_ids reflect both
    axes.
  - pending == 0 AND in_progress == 0 → status: success, all four count/id
    fields present with zero values.

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
    _update_ns,
    add_basic_task,
    cmd_finalize_step,
    cmd_list,
    cmd_loop_exit_guard,
    cmd_update,
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
    assert result['in_progress_count'] == 0
    assert result['in_progress_ids'] == []
    assert 'pending' in result['message'].lower()


def test_loop_exit_guard_success_when_queue_empty(plan_context):
    """unfinished == 0 yields status: success with all four count/id fields zeroed."""
    result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-empty'))

    assert result['status'] == 'success'
    assert result['plan_id'] == 'guard-empty'
    assert result['pending_count'] == 0
    assert result['pending_ids'] == []
    assert result['in_progress_count'] == 0
    assert result['in_progress_ids'] == []


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
    assert result['in_progress_count'] == 0
    assert result['in_progress_ids'] == []


def test_loop_exit_guard_ignores_blocked_and_failed_status(plan_context):
    """`blocked`/`failed` are terminal non-unfinished states — they do not block clean exit."""
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
    assert result['in_progress_count'] == 0
    assert result['in_progress_ids'] == []


def test_loop_exit_guard_blocks_when_only_in_progress(plan_context):
    """in_progress > 0 with pending == 0 → status: continue (broadened predicate)."""
    add_basic_task(
        plan_id='guard-in-progress-only',
        title='Mid-flight',
        deliverable=1,
        steps=['src/main/java/Mid.java'],
    )
    cmd_update(_update_ns(plan_id='guard-in-progress-only', number=1, status='in_progress'))

    result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-in-progress-only'))

    assert result['status'] == 'continue'
    assert result['pending_count'] == 0
    assert result['pending_ids'] == []
    assert result['in_progress_count'] == 1
    assert result['in_progress_ids'] == [1]
    assert 'in_progress' in result['message'].lower()


def test_loop_exit_guard_emits_in_progress_fields_when_clean(plan_context):
    """status: success branch carries `in_progress_count: 0` and `in_progress_ids: []`."""
    result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-clean-fields'))

    assert result['status'] == 'success'
    assert result['pending_count'] == 0
    assert result['pending_ids'] == []
    assert 'in_progress_count' in result
    assert result['in_progress_count'] == 0
    assert 'in_progress_ids' in result
    assert result['in_progress_ids'] == []


def test_loop_exit_guard_blocks_when_pending_and_in_progress_both_present(plan_context):
    """Both buckets non-empty → status: continue, both counts > 0."""
    add_basic_task(
        plan_id='guard-both-buckets',
        title='Still pending',
        deliverable=1,
        steps=['src/main/java/P.java'],
    )
    add_basic_task(
        plan_id='guard-both-buckets',
        title='Mid-flight',
        deliverable=2,
        steps=['src/main/java/I.java'],
    )
    cmd_update(_update_ns(plan_id='guard-both-buckets', number=2, status='in_progress'))

    result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-both-buckets'))

    assert result['status'] == 'continue'
    assert result['pending_count'] == 1
    assert result['pending_ids'] == [1]
    assert result['in_progress_count'] == 1
    assert result['in_progress_ids'] == [2]
    assert 'pending' in result['message'].lower()
    assert 'in_progress' in result['message'].lower()


def test_loop_exit_guard_parity_with_list_status_pending(plan_context):
    """The guard's pending bucket reads the same on-disk state as `list --status pending`."""
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
    assert guard['in_progress_count'] == 0
    assert guard['in_progress_ids'] == []


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
    assert 'in_progress_count: 0' in result.stdout
