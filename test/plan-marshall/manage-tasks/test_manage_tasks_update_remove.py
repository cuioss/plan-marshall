#!/usr/bin/env python3
# ruff: noqa: I001
"""Tests for manage-tasks.py update and remove subcommands.

Split from test_manage_tasks.py: covers update (title, depends_on,
clear depends), remove (file deletion, gap preservation), and the
TASK-NNN filename invariants (special-character / length agnosticism)
plus task-file content schema and arbitrary-domain acceptance via
the add path.
"""

import json

import pytest

from _helpers import (
    _add_ns,
    _read_ns,
    _remove_ns,
    _update_ns,
    add_basic_task,
    build_task_toon,
    cmd_add,
    cmd_read,
    cmd_remove,
    cmd_update,
)


# =============================================================================
# Tests: update
# =============================================================================


def test_update_title_keeps_filename(plan_context):
    """Updating title does NOT rename file (TASK-NNN format is stable)."""
    add_basic_task(plan_id='upd-title', title='Old Title', deliverable=1, steps=['src/main/java/File.java'])

    task_dir = plan_context.plan_dir_for('upd-title') / 'tasks'
    initial_files = list(task_dir.glob('TASK-001.json'))
    assert len(initial_files) == 1, 'Should have TASK-001.json'

    result = cmd_update(_update_ns(plan_id='upd-title', number=1, title='New Title'))

    assert result['status'] == 'success'
    assert result['file'] == 'TASK-001.json'

    final_files = list(task_dir.glob('TASK-001.json'))
    assert len(final_files) == 1, 'File should still be TASK-001.json'


def test_update_depends_on(plan_context):
    """Update depends_on field."""
    add_basic_task(plan_id='upd-deps', title='Task', deliverable=1, steps=['src/main/java/File.java'])

    result = cmd_update(_update_ns(plan_id='upd-deps', number=1, depends_on=['TASK-5', 'TASK-6']))

    assert result['status'] == 'success'

    get_result = cmd_read(_read_ns(plan_id='upd-deps', number=1))
    assert 'TASK-5' in get_result['task']['depends_on']
    assert 'TASK-6' in get_result['task']['depends_on']


def test_update_clear_depends_on(plan_context):
    """Update depends_on to none clears dependencies."""
    toon = build_task_toon(
        title='Task',
        deliverable=1,
        domain='java',
        description='D',
        steps=['src/main/java/File.java'],
        depends_on='TASK-1',
    )
    cmd_add(_add_ns(plan_id='upd-clear-deps', content=toon.replace('\n', '\\n')))

    result = cmd_update(_update_ns(plan_id='upd-clear-deps', number=1, depends_on=['none']))

    assert result['status'] == 'success'

    get_result = cmd_read(_read_ns(plan_id='upd-clear-deps', number=1))
    assert get_result['task']['depends_on'] == []


# =============================================================================
# Tests: remove
# =============================================================================


def test_remove_deletes_file(plan_context):
    """Remove deletes the task file."""
    add_basic_task(plan_id='rm-del', title='To Delete', deliverable=1, steps=['src/main/java/File.java'])

    result = cmd_remove(_remove_ns(plan_id='rm-del', number=1))

    assert result['status'] == 'success'
    assert result['total_tasks'] == 0

    task_dir = plan_context.plan_dir_for('rm-del') / 'tasks'
    files = list(task_dir.glob('TASK-*.json'))
    assert len(files) == 0


def test_remove_preserves_gaps(plan_context):
    """Removing a task preserves number gaps."""
    add_basic_task(plan_id='rm-gaps', title='First', deliverable=1, steps=['src/main/java/File.java'])
    add_basic_task(plan_id='rm-gaps', title='Second', deliverable=2, steps=['src/main/java/File.java'])
    add_basic_task(plan_id='rm-gaps', title='Third', deliverable=3, steps=['src/main/java/File.java'])

    cmd_remove(_remove_ns(plan_id='rm-gaps', number=2))

    result = add_basic_task(plan_id='rm-gaps', title='Fourth', deliverable=4, steps=['src/main/java/File.java'])

    assert result['file'] == 'TASK-004.json'


# =============================================================================
# Tests: file content verification
# =============================================================================


def test_file_contains_new_fields(plan_context):
    """Created file contains all new fields (JSON format)."""
    toon = build_task_toon(
        title='Test task',
        deliverable=1,
        domain='java',
        description='Test description',
        steps=['src/main/java/File1.java', 'src/main/java/File2.java'],
        depends_on='none',
        verification_commands=['mvn test'],
        verification_criteria='Tests pass',
    )
    cmd_add(_add_ns(plan_id='file-fields', content=toon.replace('\n', '\\n')))

    task_dir = plan_context.plan_dir_for('file-fields') / 'tasks'
    files = list(task_dir.glob('TASK-001.json'))
    content = files[0].read_text(encoding='utf-8')

    task = json.loads(content)
    assert task['number'] == 1
    assert task['status'] == 'pending'
    assert task['deliverable'] == 1
    assert task['depends_on'] == []
    assert task['domain'] == 'java'
    assert 'verification' in task
    assert task['verification']['criteria'] == 'Tests pass'
    assert len(task['steps']) == 2
    assert task['steps'][0]['target'] == 'src/main/java/File1.java'
    assert task['steps'][0]['status'] == 'pending'
    assert task['current_step'] == 1


def test_deliverable_is_single_number_not_array(plan_context):
    """Deliverable field is a single integer, not an array (1:1 constraint)."""
    toon = build_task_toon(
        title='Test task',
        deliverable=1,
        domain='java',
        description='Test description',
        steps=['src/main/java/File1.java'],
    )
    cmd_add(_add_ns(plan_id='del-single', content=toon.replace('\n', '\\n')))

    task_dir = plan_context.plan_dir_for('del-single') / 'tasks'
    files = list(task_dir.glob('TASK-001.json'))
    content = files[0].read_text(encoding='utf-8')

    task = json.loads(content)
    assert 'deliverable' in task
    assert 'deliverables' not in task
    assert isinstance(task['deliverable'], int), f'Expected int, got {type(task["deliverable"])}'
    assert task['deliverable'] == 1


# =============================================================================
# Tests: numbered filename format
# =============================================================================


def test_numbered_filename_ignores_title_special_chars(plan_context):
    """Filename uses TASK-NNN format regardless of special characters in title."""
    add_basic_task(plan_id='fname-special', title='Test@#$%Special!!!Characters', deliverable=1)

    task_dir = plan_context.plan_dir_for('fname-special') / 'tasks'
    files = list(task_dir.glob('TASK-001.json'))
    assert len(files) == 1, f'Expected TASK-001.json, found: {list(task_dir.glob("TASK-*.json"))}'


def test_numbered_filename_ignores_title_length(plan_context):
    """Filename uses TASK-NNN format regardless of title length."""
    long_title = 'A' * 100
    add_basic_task(plan_id='fname-long', title=long_title, deliverable=1)

    task_dir = plan_context.plan_dir_for('fname-long') / 'tasks'
    files = list(task_dir.glob('TASK-001.json'))
    assert len(files) == 1, f'Expected TASK-001.json, found: {list(task_dir.glob("TASK-*.json"))}'


# =============================================================================
# Tests: domain validation
# =============================================================================


@pytest.mark.parametrize('domain', ['java', 'my-custom-domain', 'frontend-react', 'backend-api', 'devops'])
def test_arbitrary_domains_accepted(plan_context, domain):
    """Arbitrary domain strings are accepted (config-driven, not hardcoded)."""
    toon = build_task_toon(
        title=f'Task {domain}',
        deliverable=1,
        domain=domain,
        description=f'Test {domain}',
        steps=['src/main/java/File.java'],
    )

    result = cmd_add(_add_ns(plan_id=f'arb-domains-{domain}', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success', f'Domain {domain} failed'
