#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for manage-tasks.py add-step and remove-step subcommands.

Split from test_manage_tasks.py: covers step insertion (append + after),
step removal with renumbering, and the last-step-cannot-be-removed guard.
"""

import pytest

from _helpers import (
    _add_step_ns,
    _read_ns,
    _remove_step_ns,
    _update_step_ns,
    add_basic_task,
    cmd_add_step,
    cmd_read,
    cmd_remove_step,
    cmd_update_step,
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


# =============================================================================
# Tests: add-step required intent
# =============================================================================


@pytest.mark.parametrize('intent', ['read', 'write-new', 'write-replace', 'delete'])
def test_add_step_stores_intent(plan_context, intent):
    """add-step persists the supplied intent on the new step."""
    add_basic_task(
        plan_id=f'addstep-intent-{intent}',
        title='Task',
        deliverable=1,
        steps=['src/main/java/FileA.java'],
    )

    result = cmd_add_step(
        _add_step_ns(plan_id=f'addstep-intent-{intent}', task=1, target='src/main/java/New.java', intent=intent)
    )
    assert result['status'] == 'success'

    get_result = cmd_read(_read_ns(plan_id=f'addstep-intent-{intent}', number=1))
    assert get_result['task']['steps'][-1]['intent'] == intent


def test_add_step_rejects_missing_intent(plan_context):
    """add-step with no intent value is rejected by the handler."""
    add_basic_task(plan_id='addstep-no-intent', title='Task', deliverable=1, steps=['src/main/java/FileA.java'])

    result = cmd_add_step(
        _add_step_ns(plan_id='addstep-no-intent', task=1, target='src/main/java/New.java', intent=None)
    )
    assert result['status'] == 'error'
    assert 'intent' in result.get('message', '').lower()


def test_add_step_rejects_invalid_intent(plan_context):
    """add-step with an out-of-vocabulary intent is rejected by the handler."""
    add_basic_task(plan_id='addstep-bad-intent', title='Task', deliverable=1, steps=['src/main/java/FileA.java'])

    result = cmd_add_step(
        _add_step_ns(plan_id='addstep-bad-intent', task=1, target='src/main/java/New.java', intent='sideways')
    )
    assert result['status'] == 'error'
    assert 'intent' in result.get('message', '').lower()


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


# =============================================================================
# Tests: update-step (sanctioned intent-override escape hatch)
# =============================================================================


def test_update_step_changes_intent_and_records_audit(plan_context):
    """update-step changes the stored intent AND appends a {from, to, reason} record."""
    add_basic_task(plan_id='upd-intent', title='Task', deliverable=1, steps=['src/main/java/A.java'])

    result = cmd_update_step(
        _update_step_ns(plan_id='upd-intent', task=1, step_number=1, intent='write-new', reason='file was new')
    )
    assert result['status'] == 'success'
    assert result['from_intent'] == 'write-replace'
    assert result['to_intent'] == 'write-new'

    step = cmd_read(_read_ns(plan_id='upd-intent', number=1))['task']['steps'][0]
    assert step['intent'] == 'write-new'
    assert step['intent_override'] == [{'from': 'write-replace', 'to': 'write-new', 'reason': 'file was new'}]


def test_update_step_records_finding_id_when_supplied(plan_context):
    """--finding-id is persisted on the audit record for triage-driven overrides."""
    add_basic_task(plan_id='upd-finding', title='Task', deliverable=1, steps=['src/main/java/A.java'])

    result = cmd_update_step(
        _update_step_ns(
            plan_id='upd-finding', task=1, step_number=1, intent='read', reason='sonar said so', finding_id='F-42'
        )
    )
    assert result['status'] == 'success'

    step = cmd_read(_read_ns(plan_id='upd-finding', number=1))['task']['steps'][0]
    assert step['intent_override'][0]['finding_id'] == 'F-42'


def test_update_step_rejects_empty_reason(plan_context):
    """A missing/empty --reason is rejected."""
    add_basic_task(plan_id='upd-no-reason', title='Task', deliverable=1, steps=['src/main/java/A.java'])

    result = cmd_update_step(
        _update_step_ns(plan_id='upd-no-reason', task=1, step_number=1, intent='read', reason='   ')
    )
    assert result['status'] == 'error'
    assert 'reason' in result.get('message', '').lower()


def test_update_step_rejects_invalid_intent(plan_context):
    """An invalid --intent value is rejected."""
    add_basic_task(plan_id='upd-bad-intent', title='Task', deliverable=1, steps=['src/main/java/A.java'])

    result = cmd_update_step(
        _update_step_ns(plan_id='upd-bad-intent', task=1, step_number=1, intent='sideways', reason='x')
    )
    assert result['status'] == 'error'
    assert 'intent' in result.get('message', '').lower()


def test_update_step_rejects_unknown_step(plan_context):
    """An unknown --step-number is rejected."""
    add_basic_task(plan_id='upd-bad-step', title='Task', deliverable=1, steps=['src/main/java/A.java'])

    result = cmd_update_step(
        _update_step_ns(plan_id='upd-bad-step', task=1, step_number=99, intent='read', reason='x')
    )
    assert result['status'] == 'error'
    assert 'not found' in result.get('message', '').lower()


def test_never_overridden_step_has_no_intent_override_key(plan_context):
    """A step that was never overridden carries no intent_override key (clean shape)."""
    add_basic_task(plan_id='upd-clean', title='Task', deliverable=1, steps=['src/main/java/A.java'])

    step = cmd_read(_read_ns(plan_id='upd-clean', number=1))['task']['steps'][0]
    assert 'intent_override' not in step
