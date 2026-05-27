#!/usr/bin/env python3
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
    add_basic_task,
    build_task_toon,
    cmd_add,
    cmd_finalize_step,
    cmd_next,
)


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
