#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for manage-tasks.py next subcommand.

Split from test_manage_tasks.py: covers next (with/without context), dependency
satisfaction, in_progress prioritization, blocked-task surfacing, and the
--ignore-deps escape.
"""

from _helpers import (
    _add_ns,
    _finalize_step_ns,
    _next_ns,
    _core,
    add_basic_task,
    build_task_toon,
    cmd_add,
    cmd_finalize_step,
    cmd_next,
)


def _stamp_cost_fields(plan_id, task_number, **fields):
    """Write cost-sizing fields directly onto a stored task file.

    The three cost-sizing fields (cost_size, predicted_cost_tokens,
    envelope_id) are stamped onto a task record by upstream phase-4-plan
    producers (derive-cost-size / pack-envelopes), not by the add flow. To
    exercise the ``next`` surfacing of these fields deterministically, this
    helper reads the persisted task JSON, sets the supplied fields, and writes
    it back — mirroring the on-disk shape the producers leave behind.
    """
    task_dir = _core.get_tasks_dir(plan_id)
    task_file = _core.find_task_file(task_dir, task_number)
    assert task_file is not None, f'task file for {plan_id}/{task_number} not found'
    task = _core.parse_task_file(task_file.read_text(encoding='utf-8'))
    task.update(fields)
    task_file.write_text(_core.format_task_file(task), encoding='utf-8')


def test_next_returns_first_pending(plan_context):
    """Next returns first pending task and step."""
    toon = build_task_toon(
        title='First Task',
        deliverable=1,
        domain='java',
        description='D1',
        steps=['src/main/java/One.java', 'src/main/java/Two.java'],
    )
    cmd_add(_add_ns(plan_id='next-first', content=toon.replace('\n', '\\n')))

    result = cmd_next(_next_ns(plan_id='next-first'))

    assert result['status'] == 'success'
    assert result['next']['task_number'] == 1
    assert result['next']['task_title'] == 'First Task'
    assert result['next']['step_number'] == 1
    assert 'One.java' in result['next']['step_target']


def test_next_returns_in_progress_task(plan_context):
    """Next prioritizes in_progress tasks."""
    add_basic_task(
        plan_id='next-inprog',
        title='First',
        deliverable=1,
        steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
    )
    add_basic_task(plan_id='next-inprog', title='Second', deliverable=2, steps=['src/main/java/File.java'])
    cmd_finalize_step(_finalize_step_ns(plan_id='next-inprog', task=1, step=1, outcome='done'))

    result = cmd_next(_next_ns(plan_id='next-inprog'))

    assert result['status'] == 'success'
    assert result['next']['task_number'] == 1
    assert result['next']['step_number'] == 2


def test_next_returns_null_when_all_done(plan_context):
    """Next returns null when all tasks complete."""
    add_basic_task(plan_id='next-done', title='Only Task', deliverable=1, steps=['src/main/java/File.java'])
    cmd_finalize_step(_finalize_step_ns(plan_id='next-done', task=1, step=1, outcome='done'))

    result = cmd_next(_next_ns(plan_id='next-done'))

    assert result['status'] == 'success'
    assert result['next'] is None
    assert 'All tasks completed' in result['context']['message']


def test_next_empty_plan(plan_context):
    """Next on empty plan returns null."""
    result = cmd_next(_next_ns(plan_id='next-empty'))

    assert result['status'] == 'success'
    assert result['next'] is None


def test_next_respects_dependencies(plan_context):
    """Next skips tasks with unmet dependencies."""
    add_basic_task(plan_id='next-deps', title='First', deliverable=1, steps=['src/main/java/File.java'])

    toon = build_task_toon(
        title='Second',
        deliverable=2,
        domain='java',
        description='D2',
        steps=['src/main/java/File.java'],
        depends_on='TASK-1',
    )
    cmd_add(_add_ns(plan_id='next-deps', content=toon.replace('\n', '\\n')))

    result = cmd_next(_next_ns(plan_id='next-deps'))

    assert result['status'] == 'success'
    assert result['next']['task_number'] == 1
    assert result['next']['task_title'] == 'First'


def test_next_shows_blocked_tasks(plan_context):
    """Next shows blocked tasks when all available are blocked."""
    toon = build_task_toon(
        title='Blocked',
        deliverable=1,
        domain='java',
        description='D1',
        steps=['src/main/java/File.java'],
        depends_on='TASK-99',
    )
    cmd_add(_add_ns(plan_id='next-blocked', content=toon.replace('\n', '\\n')))

    result = cmd_next(_next_ns(plan_id='next-blocked'))

    assert result['status'] == 'success'
    assert result['next'] is None
    assert 'blocked_tasks' in result
    assert any('TASK-99' in str(bt.get('waiting_for', '')) for bt in result['blocked_tasks'])


def test_next_ignore_deps(plan_context):
    """Next with --ignore-deps ignores dependency constraints."""
    toon = build_task_toon(
        title='Blocked',
        deliverable=1,
        domain='java',
        description='D1',
        steps=['src/main/java/File.java'],
        depends_on='TASK-99',
    )
    cmd_add(_add_ns(plan_id='next-igdeps', content=toon.replace('\n', '\\n')))

    result = cmd_next(_next_ns(plan_id='next-igdeps', ignore_deps=True))

    assert result['status'] == 'success'
    assert result['next']['task_number'] == 1
    assert result['next']['task_title'] == 'Blocked'


def test_next_include_context(plan_context):
    """Next with --include-context includes deliverable details."""
    toon = build_task_toon(
        title='Feature task',
        deliverable=1,
        domain='java',
        description='Task description',
        steps=['src/main/java/One.java', 'src/main/java/Two.java'],
    )
    cmd_add(_add_ns(plan_id='next-ctx', content=toon.replace('\n', '\\n')))

    result = cmd_next(_next_ns(plan_id='next-ctx', include_context=True))

    assert result['status'] == 'success'
    assert result['next']['task_number'] == 1
    assert result['next']['deliverable'] == 1
    assert 'deliverable_source' in result['next']


# =============================================================================
# Cost-sizing fields: cost_size, predicted_cost_tokens, envelope_id
# =============================================================================


def test_next_surfaces_all_cost_fields_when_stamped(plan_context):
    """Next surfaces cost_size, predicted_cost_tokens, and envelope_id when stamped."""
    add_basic_task(plan_id='next-cost-all', title='Sized', deliverable=1, steps=['src/main/java/File.java'])
    _stamp_cost_fields(
        'next-cost-all',
        1,
        cost_size='M',
        predicted_cost_tokens=60000,
        envelope_id=2,
    )

    result = cmd_next(_next_ns(plan_id='next-cost-all'))

    assert result['status'] == 'success'
    assert result['next']['cost_size'] == 'M'
    assert result['next']['predicted_cost_tokens'] == 60000
    assert result['next']['envelope_id'] == 2


def test_next_cost_fields_null_when_absent(plan_context):
    """Next surfaces all three cost fields as None when not yet stamped."""
    add_basic_task(plan_id='next-cost-none', title='Unsized', deliverable=1, steps=['src/main/java/File.java'])

    result = cmd_next(_next_ns(plan_id='next-cost-none'))

    assert result['status'] == 'success'
    # Keys are always present in the next payload, surfaced as null when unstamped.
    assert 'cost_size' in result['next']
    assert 'predicted_cost_tokens' in result['next']
    assert 'envelope_id' in result['next']
    assert result['next']['cost_size'] is None
    assert result['next']['predicted_cost_tokens'] is None
    assert result['next']['envelope_id'] is None


def test_next_cost_fields_surfaced_independently(plan_context):
    """Each cost field is surfaced independently of the others (partial stamping)."""
    add_basic_task(plan_id='next-cost-partial', title='Partial', deliverable=1, steps=['src/main/java/File.java'])
    # Only cost_size is stamped; predicted_cost_tokens and envelope_id remain absent.
    _stamp_cost_fields('next-cost-partial', 1, cost_size='XL')

    result = cmd_next(_next_ns(plan_id='next-cost-partial'))

    assert result['status'] == 'success'
    assert result['next']['cost_size'] == 'XL'
    assert result['next']['predicted_cost_tokens'] is None
    assert result['next']['envelope_id'] is None


def test_next_cost_fields_present_with_include_context(plan_context):
    """Cost fields are still surfaced when --include-context is requested."""
    add_basic_task(plan_id='next-cost-ctx', title='SizedCtx', deliverable=1, steps=['src/main/java/File.java'])
    _stamp_cost_fields(
        'next-cost-ctx',
        1,
        cost_size='S',
        predicted_cost_tokens=20000,
        envelope_id=1,
    )

    result = cmd_next(_next_ns(plan_id='next-cost-ctx', include_context=True))

    assert result['status'] == 'success'
    assert result['next']['cost_size'] == 'S'
    assert result['next']['predicted_cost_tokens'] == 20000
    assert result['next']['envelope_id'] == 1
    # include_context augmentation does not drop the cost fields.
    assert 'deliverable_source' in result['next']
