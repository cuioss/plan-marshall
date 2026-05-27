#!/usr/bin/env python3
# ruff: noqa: I001
"""Tests for manage-tasks.py add-step and remove-step subcommands.

Split from test_manage_tasks.py: covers step insertion (append + after),
step removal with renumbering, and the last-step-cannot-be-removed guard.
"""

from _helpers import (
    _add_step_ns,
    _read_ns,
    _remove_step_ns,
    add_basic_task,
    cmd_add_step,
    cmd_read,
    cmd_remove_step,
)


# =============================================================================
# Tests: add-step
# =============================================================================


def test_add_step_appends(plan_context):
    """Add-step appends to end by default."""
    add_basic_task(
        plan_id='addstep-app',
        title='Task',
        deliverable=1,
        steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
    )

    result = cmd_add_step(_add_step_ns(plan_id='addstep-app', task=1, target='New Step'))

    assert result['status'] == 'success'
    assert result['step'] == 3

    get_result = cmd_read(_read_ns(plan_id='addstep-app', number=1))
    assert len(get_result['task']['steps']) == 3


def test_add_step_after(plan_context):
    """Add-step inserts after specified position."""
    add_basic_task(
        plan_id='addstep-aft',
        title='Task',
        deliverable=1,
        steps=['src/main/java/FileA.java', 'src/main/java/FileC.java'],
    )

    result = cmd_add_step(
        _add_step_ns(
            plan_id='addstep-aft',
            task=1,
            target='src/main/java/FileB.java',
            after=1,
        )
    )

    assert result['status'] == 'success'
    assert result['step'] == 2

    get_result = cmd_read(_read_ns(plan_id='addstep-aft', number=1))
    steps = get_result['task']['steps']
    assert steps[0]['target'] == 'src/main/java/FileA.java'
    assert steps[1]['target'] == 'src/main/java/FileB.java'
    assert steps[2]['target'] == 'src/main/java/FileC.java'


# =============================================================================
# Tests: remove-step
# =============================================================================


def test_remove_step(plan_context):
    """Remove-step removes and renumbers."""
    add_basic_task(
        plan_id='rmstep',
        title='Task',
        deliverable=1,
        steps=['src/main/java/FileA.java', 'src/main/java/FileB.java', 'src/main/java/FileC.java'],
    )

    result = cmd_remove_step(_remove_step_ns(plan_id='rmstep', task=1, step=2))

    assert result['status'] == 'success'
    assert 'Step 2 removed' in result.get('message', '')

    get_result = cmd_read(_read_ns(plan_id='rmstep', number=1))
    steps = get_result['task']['steps']
    assert len(steps) == 2
    assert steps[0]['target'] == 'src/main/java/FileA.java'
    assert steps[1]['target'] == 'src/main/java/FileC.java'


def test_remove_step_last_fails(plan_context):
    """Cannot remove the last step."""
    add_basic_task(plan_id='rmstep-last', title='Task', deliverable=1, steps=['src/main/java/File.java'])

    result = cmd_remove_step(_remove_step_ns(plan_id='rmstep-last', task=1, step=1))

    assert result['status'] == 'error'
    assert 'Cannot remove the last step' in result.get('message', '')
