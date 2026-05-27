#!/usr/bin/env python3
# ruff: noqa: I001
"""Tests for manage-tasks.py list subcommand.

Split from test_manage_tasks.py: covers list, list --status, list --deliverable,
list --ready, the failed-count surfacing, and the progress calculation column.
"""

from argparse import Namespace

from _helpers import (
    _add_ns,
    _finalize_step_ns,
    _list_ns,
    add_basic_task,
    build_task_toon,
    cmd_add,
    cmd_finalize_step,
    cmd_list,
)


def test_list_empty(plan_context):
    """List with no tasks shows zero counts."""
    result = cmd_list(_list_ns(plan_id='list-empty'))

    assert result['status'] == 'success'
    assert result['counts']['total'] == 0


def test_list_with_tasks(plan_context):
    """List shows all tasks in table format with domain, profile and deliverables."""
    add_basic_task(plan_id='list-tasks', title='First', deliverable=1, steps=['src/main/java/File.java'])
    add_basic_task(
        plan_id='list-tasks',
        title='Second',
        deliverable=2,
        steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
    )

    result = cmd_list(_list_ns(plan_id='list-tasks'))

    assert result['status'] == 'success'
    assert result['counts']['total'] == 2
    assert len(result['tasks_table']) == 2
    assert result['tasks_table'][0]['number'] == 1
    assert result['tasks_table'][0]['title'] == 'First'
    assert result['tasks_table'][0]['domain'] == 'java'
    assert result['tasks_table'][0]['progress'] == '0/1'
    assert result['tasks_table'][1]['progress'] == '0/2'


def test_list_filter_by_status(plan_context):
    """List can filter by status."""
    add_basic_task(plan_id='list-status', title='First', deliverable=1, steps=['src/main/java/File.java'])
    add_basic_task(plan_id='list-status', title='Second', deliverable=2, steps=['src/main/java/File.java'])
    cmd_finalize_step(_finalize_step_ns(plan_id='list-status', task=1, step=1, outcome='done'))

    result = cmd_list(_list_ns(plan_id='list-status', status='pending'))

    assert result['status'] == 'success'
    assert len(result['tasks_table']) == 1
    assert result['tasks_table'][0]['title'] == 'Second'


def test_list_filter_by_deliverable(plan_context):
    """List can filter by deliverable number."""
    add_basic_task(plan_id='list-del', title='First', deliverable=1, steps=['src/main/java/File.java'])
    add_basic_task(plan_id='list-del', title='Second', deliverable=1, steps=['src/main/java/File.java'])
    add_basic_task(plan_id='list-del', title='Third', deliverable=2, steps=['src/main/java/File.java'])

    result = cmd_list(_list_ns(plan_id='list-del', deliverable=1))

    assert result['status'] == 'success'
    assert result['counts']['total'] == 2
    titles = [t['title'] for t in result['tasks_table']]
    assert 'First' in titles
    assert 'Second' in titles
    assert 'Third' not in titles


def test_list_filter_ready(plan_context):
    """List --ready shows only tasks with satisfied dependencies."""
    add_basic_task(plan_id='list-ready', title='First', deliverable=1, steps=['src/main/java/File.java'])

    toon = build_task_toon(
        title='Second',
        deliverable=2,
        domain='java',
        description='D2',
        steps=['src/main/java/File.java'],
        depends_on='TASK-1',
    )
    cmd_add(_add_ns(plan_id='list-ready', content=toon.replace('\n', '\\n')))

    result = cmd_list(_list_ns(plan_id='list-ready', ready=True))

    assert result['status'] == 'success'
    titles = [t['title'] for t in result['tasks_table']]
    assert 'First' in titles
    assert 'Second' not in titles


def test_list_surfaces_failed_count(plan_context):
    """List command includes failed count in counts."""
    add_basic_task(plan_id='list-fail-count', title='Task', deliverable=1, steps=['src/main/java/File.java'])
    cmd_finalize_step(
        _finalize_step_ns(plan_id='list-fail-count', task=1, step=1, outcome='failed', reason='Broke')
    )

    result = cmd_list(Namespace(plan_id='list-fail-count', status='all', deliverable=None, ready=False))

    assert result['counts']['failed'] == 1
    assert result['counts']['done'] == 0


def test_progress_calculation(plan_context):
    """Progress is correctly calculated in list output."""
    add_basic_task(
        plan_id='prog-calc',
        title='Task',
        deliverable=1,
        steps=['src/main/java/FileA.java', 'src/main/java/FileB.java', 'src/main/java/FileC.java'],
    )
    cmd_finalize_step(_finalize_step_ns(plan_id='prog-calc', task=1, step=1, outcome='done'))
    cmd_finalize_step(_finalize_step_ns(plan_id='prog-calc', task=1, step=2, outcome='skipped'))

    result = cmd_list(_list_ns(plan_id='prog-calc'))

    assert result['status'] == 'success'
    assert '2/3' in result['tasks_table'][0]['progress']
