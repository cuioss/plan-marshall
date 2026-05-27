#!/usr/bin/env python3
# ruff: noqa: I001
"""Tests for manage-tasks.py finalize-step subcommand.

Split from test_manage_tasks.py: covers finalize-step outcomes (done /
skipped / failed), task-status derivation from step outcomes, progress
indicator, and the script-level [OUTCOME] emission contract pinned by
lesson 2026-05-08-14-001.
"""

from argparse import Namespace
from pathlib import Path

from _helpers import _finalize_step_ns, add_basic_task, cmd_finalize_step


# =============================================================================
# Tests: finalize-step
# =============================================================================


def test_finalize_step_done_marks_completed(plan_context):
    """finalize-step --outcome done marks step as done."""
    add_basic_task(
        plan_id='fin-done',
        title='Task',
        deliverable=1,
        steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
    )

    result = cmd_finalize_step(_finalize_step_ns(plan_id='fin-done', task=1, step=1, outcome='done'))

    assert result['status'] == 'success'
    assert result['finalized']['outcome'] == 'done'
    assert result['next_step'] is not None
    assert result['next_step']['number'] == 2


def test_finalize_step_done_completes_task(plan_context):
    """finalize-step --outcome done on last step marks task as done."""
    add_basic_task(plan_id='fin-complete', title='Task', deliverable=1, steps=['src/main/java/File.java'])

    result = cmd_finalize_step(_finalize_step_ns(plan_id='fin-complete', task=1, step=1, outcome='done'))

    assert result['status'] == 'success'
    assert result['task_complete'] is True
    assert result['task_status'] == 'done'
    assert result['next_step'] is None


def test_finalize_step_skipped_marks_skipped(plan_context):
    """finalize-step --outcome skipped marks step as skipped."""
    add_basic_task(
        plan_id='fin-skip',
        title='Task',
        deliverable=1,
        steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
    )

    result = cmd_finalize_step(
        _finalize_step_ns(
            plan_id='fin-skip',
            task=1,
            step=1,
            outcome='skipped',
            reason='Already done',
        )
    )

    assert result['status'] == 'success'
    assert result['finalized']['outcome'] == 'skipped'
    assert result['next_step'] is not None
    assert result['next_step']['number'] == 2


def test_finalize_step_skipped_completes_task(plan_context):
    """Skipping last step via finalize-step marks task as done."""
    add_basic_task(plan_id='fin-skip-last', title='Task', deliverable=1, steps=['src/main/java/File.java'])

    result = cmd_finalize_step(_finalize_step_ns(plan_id='fin-skip-last', task=1, step=1, outcome='skipped'))

    assert result['status'] == 'success'
    assert result['task_complete'] is True
    assert result['task_status'] == 'done'


def test_finalize_step_invalid_step(plan_context):
    """finalize-step with invalid step number fails."""
    add_basic_task(plan_id='fin-invalid', title='Task', deliverable=1, steps=['src/main/java/File.java'])

    result = cmd_finalize_step(_finalize_step_ns(plan_id='fin-invalid', task=1, step=99, outcome='done'))

    assert result['status'] == 'error'
    assert 'Step 99 not found' in result.get('message', '')


def test_finalize_step_returns_progress(plan_context):
    """finalize-step returns progress indicator."""
    add_basic_task(
        plan_id='fin-prog',
        title='Task',
        deliverable=1,
        steps=['src/main/java/FileA.java', 'src/main/java/FileB.java', 'src/main/java/FileC.java'],
    )

    result = cmd_finalize_step(_finalize_step_ns(plan_id='fin-prog', task=1, step=1, outcome='done'))

    assert result['status'] == 'success'
    assert result['progress'] == '1/3'


# =============================================================================
# Tests: finalize-step --outcome failed
# =============================================================================


def test_finalize_step_failed_marks_failed(plan_context):
    """finalize-step --outcome failed marks step as failed."""
    add_basic_task(
        plan_id='fin-fail',
        title='Task',
        deliverable=1,
        steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
    )

    result = cmd_finalize_step(
        _finalize_step_ns(
            plan_id='fin-fail',
            task=1,
            step=1,
            outcome='failed',
            reason='Verification failed',
        )
    )

    assert result['status'] == 'success'
    assert result['finalized']['outcome'] == 'failed'
    assert result['finalized']['reason'] == 'Verification failed'
    assert result['next_step'] is not None
    assert result['next_step']['number'] == 2


def test_finalize_step_failed_completes_task_as_failed(plan_context):
    """Failing last step via finalize-step marks task as failed (not done)."""
    add_basic_task(plan_id='fin-fail-last', title='Task', deliverable=1, steps=['src/main/java/File.java'])

    result = cmd_finalize_step(
        _finalize_step_ns(plan_id='fin-fail-last', task=1, step=1, outcome='failed', reason='Build broke')
    )

    assert result['status'] == 'success'
    assert result['task_complete'] is True
    assert result['task_status'] == 'failed'


def test_finalize_step_mixed_done_and_failed_marks_task_failed(plan_context):
    """Task with mix of done and failed steps gets status 'failed'."""
    add_basic_task(
        plan_id='fin-mixed',
        title='Task',
        deliverable=1,
        steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
    )

    cmd_finalize_step(_finalize_step_ns(plan_id='fin-mixed', task=1, step=1, outcome='done'))
    result = cmd_finalize_step(
        _finalize_step_ns(plan_id='fin-mixed', task=1, step=2, outcome='failed', reason='Test failed')
    )

    assert result['status'] == 'success'
    assert result['task_complete'] is True
    assert result['task_status'] == 'failed'


def test_finalize_step_all_done_no_failed_marks_task_done(plan_context):
    """Task with all done steps (no failed) still gets status 'done'."""
    add_basic_task(
        plan_id='fin-all-done',
        title='Task',
        deliverable=1,
        steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
    )

    cmd_finalize_step(_finalize_step_ns(plan_id='fin-all-done', task=1, step=1, outcome='done'))
    result = cmd_finalize_step(_finalize_step_ns(plan_id='fin-all-done', task=1, step=2, outcome='done'))

    assert result['task_status'] == 'done'


# =============================================================================
# Tests: finalize-step script-level [OUTCOME] emission
# =============================================================================
#
# Lesson 2026-05-08-14-001: phase-5-execute lost log coverage on agent-initiated
# re-dispatch because [OUTCOME] emissions lived in skill prose. The cure was to
# move [OUTCOME] emission into manage-tasks finalize-step itself, where it
# fires unconditionally inside the script boundary on the task-closing call.
# These four tests pin down the contract.


def _read_work_log(plan_dir: Path) -> str:
    """Read the plan-scoped work.log file as text (empty string if missing)."""
    log_path = plan_dir / 'logs' / 'work.log'
    if not log_path.exists():
        return ''
    return log_path.read_text(encoding='utf-8')


def test_emits_outcome_with_defaults_on_task_close(plan_context):
    """[OUTCOME] is emitted with default caller/title/count when the
    closing call uses --outcome done and supplies no overrides."""
    add_basic_task(
        plan_id='outcome-default',
        title='My Closing Task',
        deliverable=1,
        steps=['src/main/java/A.java', 'src/main/java/B.java'],
    )

    plan_dir = plan_context.plan_dir_for('outcome-default')

    cmd_finalize_step(_finalize_step_ns(plan_id='outcome-default', task=1, step=1, outcome='done'))
    log_after_intermediate = _read_work_log(plan_dir)
    assert '[OUTCOME]' not in log_after_intermediate, (
        'Script-level [OUTCOME] must not fire on intermediate task-not-yet-done step finalization'
    )

    cmd_finalize_step(_finalize_step_ns(plan_id='outcome-default', task=1, step=2, outcome='done'))
    log_after_close = _read_work_log(plan_dir)

    assert '[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-001: My Closing Task (2 steps)' in (
        log_after_close
    )


def test_emits_outcome_with_overrides(plan_context):
    """When --outcome-task-title / --outcome-step-count / --outcome-caller
    are supplied, the rendered [OUTCOME] line uses them verbatim."""
    add_basic_task(
        plan_id='outcome-overrides',
        title='Original Disk Title',
        deliverable=1,
        steps=['src/main/java/A.java'],
    )

    ns = Namespace(
        plan_id='outcome-overrides',
        task_number=1,
        step=1,
        outcome='done',
        reason=None,
        outcome_task_title='Overridden Title',
        outcome_step_count=42,
        outcome_caller='custom-bundle:custom-skill',
    )
    cmd_finalize_step(ns)

    log_text = _read_work_log(plan_context.plan_dir_for('outcome-overrides'))
    assert (
        '[OUTCOME] (custom-bundle:custom-skill) Completed TASK-001: Overridden Title (42 steps)'
        in log_text
    )
    assert 'plan-marshall:phase-5-execute' not in log_text.split('[OUTCOME]', 1)[1], (
        'Default caller leaked into [OUTCOME] line despite override'
    )
    assert 'Original Disk Title' not in log_text.split('[OUTCOME]', 1)[1], (
        'Default title leaked into [OUTCOME] line despite override'
    )


def test_no_outcome_on_intermediate_done_step(plan_context):
    """An intermediate --outcome done call (task still in_progress)
    must not emit any [OUTCOME] line."""
    add_basic_task(
        plan_id='outcome-intermediate',
        title='Multi Step Task',
        deliverable=1,
        steps=[
            'src/main/java/A.java',
            'src/main/java/B.java',
            'src/main/java/C.java',
        ],
    )

    cmd_finalize_step(_finalize_step_ns(plan_id='outcome-intermediate', task=1, step=1, outcome='done'))
    cmd_finalize_step(_finalize_step_ns(plan_id='outcome-intermediate', task=1, step=2, outcome='done'))

    log_text = _read_work_log(plan_context.plan_dir_for('outcome-intermediate'))
    assert '[OUTCOME]' not in log_text, (
        'No [OUTCOME] line should be emitted while the task is still in_progress'
    )


def test_no_outcome_on_failed_close(plan_context):
    """When the closing finalize uses --outcome failed (task ends in
    status=failed), no [OUTCOME] line is emitted — only the existing
    WARNING marker fires."""
    add_basic_task(
        plan_id='outcome-failed',
        title='Doomed Task',
        deliverable=1,
        steps=['src/main/java/A.java'],
    )

    cmd_finalize_step(
        _finalize_step_ns(
            plan_id='outcome-failed',
            task=1,
            step=1,
            outcome='failed',
            reason='Verification broke',
        )
    )

    log_text = _read_work_log(plan_context.plan_dir_for('outcome-failed'))
    assert '[OUTCOME]' not in log_text, (
        '[OUTCOME] must not be emitted on a failed-status closing finalize'
    )
