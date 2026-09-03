#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for manage-tasks.py finalize-step subcommand.

Split from test_manage_tasks.py: covers finalize-step outcomes (done /
skipped / failed), task-status derivation from step outcomes, and the two
script-level emission contracts the task-closing call owns — [OUTCOME] and
[ARTIFACT].

The [ARTIFACT] status-code mapping, the baseline-capture rules and the diff
form are pinned against a real git repository in
``test_manage_tasks_artifact_emission.py``; what this module adds is the
END-TO-END proof that the task-closing ``finalize-step`` call actually writes
those lines to the plan's work log.
"""

import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from _manage_tasks_fixtures import _finalize_step_ns, add_basic_task, cmd_finalize_step

from conftest import add_skill_scripts_to_path

add_skill_scripts_to_path('plan-marshall', 'manage-tasks')

# ⛔ Imported PLAINLY, not through ``load_script_module``. The monkeypatch below
# must land on the SAME module object ``_cmd_step`` imported its helpers from; a
# separately-loaded copy would be patched while the handler kept calling the
# original, and the end-to-end assertions would then run against the real
# repository instead of the fixture one.
import _task_artifacts as _artifacts  # noqa: E402


@pytest.fixture(autouse=True)
def _seed_status_sentinel(plan_context, monkeypatch):
    """Seed a ``status.json`` sentinel into the plan dirs used by the positive
    [OUTCOME]-emission tests so the script-level [OUTCOME] line lands in the
    plan-scoped work log rather than falling back to the global log.

    ``finalize-step``'s [OUTCOME] emission resolves plan-scoped logging only when
    the plan dir carries a ``status.json`` sentinel (gated by ``get_log_path``).
    Two seeding paths are needed:

    * Wrap ``plan_context.plan_dir_for`` so any test that resolves its plan dir
      through it (e.g. ``outcome-default``, which calls ``plan_dir_for`` before
      its closing finalize) gets the sentinel in time.
    * Eagerly seed the positive-test plan dirs whose [OUTCOME] write happens
      BEFORE ``plan_dir_for`` is read (``outcome-overrides`` reads the log only
      after the emitting finalize call), so the wrap alone would seed too late.

    The negative tests (``outcome-intermediate``, ``outcome-failed``, and the
    intermediate-step assertion in ``outcome-default``) assert the ABSENCE of an
    [OUTCOME] line; seeding is harmless for them because the line is absent for a
    different reason (intermediate step / failed status), not because of log
    routing.
    """

    def _seed(plan_dir: Path) -> None:
        sentinel = plan_dir / 'status.json'
        if not sentinel.exists():
            sentinel.write_text('{}', encoding='utf-8')

    _orig = plan_context.plan_dir_for

    def _seeding(plan_id):
        d = _orig(plan_id)
        _seed(d)
        return d

    monkeypatch.setattr(plan_context, 'plan_dir_for', _seeding)

    # Positive [OUTCOME] tests whose emitting finalize call precedes the
    # plan_dir_for read — seed eagerly so the [OUTCOME] line lands plan-scoped.
    for plan_id in ('outcome-default', 'outcome-overrides'):
        d = plan_context.plans_dir / plan_id
        d.mkdir(parents=True, exist_ok=True)
        _seed(d)


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
# phase-5-execute loses log coverage on agent-initiated re-dispatch when
# [OUTCOME] emissions live in skill prose. The remedy is to
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
    # Scope the leak assertions to the [OUTCOME] LINE, which is what they claim
    # to be about. Splitting on the marker and keeping the whole tail also swept
    # in the [ARTIFACT] lines that follow it — those legitimately carry the
    # default caller, so the assertion failed on a line it was never about.
    outcome_line = next(line for line in log_text.splitlines() if '[OUTCOME]' in line)
    assert 'plan-marshall:phase-5-execute' not in outcome_line, (
        'Default caller leaked into [OUTCOME] line despite override'
    )
    assert 'Original Disk Title' not in outcome_line, (
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


# =============================================================================
# Tests: finalize-step script-level [ARTIFACT] emission (end-to-end)
# =============================================================================
#
# The prose-instructed [ARTIFACT] channel inherited the same loss the [OUTCOME]
# move was made to stop: a caller-side emission disappears when the caller
# envelope is re-fired before it writes. These two cases prove the channel is
# now driven by the closing `finalize-step` call itself — against a REAL git
# baseline the same call recorded, because a channel whose base has no writer
# lands script-owned and still inert.


@pytest.fixture
def _artifact_repo(tmp_path, monkeypatch):
    """Point the artifact differ at a throwaway repository with one commit."""
    root = tmp_path / 'artifact-repo'
    root.mkdir()
    for argv in (
        ['init', '-q'],
        ['config', 'user.email', 'test@example.com'],
        ['config', 'user.name', 'Test'],
    ):
        subprocess.run(['git', '-C', str(root), *argv], check=True, capture_output=True, text=True)
    (root / 'seed.txt').write_text('seed\n', encoding='utf-8')
    subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True, capture_output=True, text=True)
    subprocess.run(
        ['git', '-C', str(root), 'commit', '-q', '-m', 'seed'], check=True, capture_output=True, text=True
    )
    monkeypatch.setattr(_artifacts, 'cwd_checkout_root', lambda: str(root))
    return root


def test_task_close_emits_artifact_lines_from_the_script(plan_context, _artifact_repo):
    """The closing call records a baseline, diffs it, and writes the lines itself."""
    add_basic_task(
        plan_id='outcome-default',
        title='Artifact Task',
        deliverable=1,
        steps=['src/main/java/A.java', 'src/main/java/B.java'],
    )
    plan_dir = plan_context.plan_dir_for('outcome-default')

    # The first call captures the baseline; the file change lands after it, so
    # the diff is genuinely computed from the RECORDED base rather than from a
    # base chosen once the answer was already known.
    cmd_finalize_step(_finalize_step_ns(plan_id='outcome-default', task=1, step=1, outcome='done'))
    (_artifact_repo / 'seed.txt').write_text('touched by the task\n', encoding='utf-8')

    result = cmd_finalize_step(
        _finalize_step_ns(plan_id='outcome-default', task=1, step=2, outcome='done')
    )

    assert result['artifact_lines'] == 1
    assert '[ARTIFACT] (plan-marshall:phase-5-execute:1) Wrote seed.txt' in _read_work_log(plan_dir)


def test_task_close_with_an_empty_diff_emits_no_artifact_line(plan_context, _artifact_repo):
    """The negative control — an empty artifact list is a valid, measured outcome."""
    add_basic_task(
        plan_id='outcome-default',
        title='Untouched Task',
        deliverable=1,
        steps=['src/main/java/A.java'],
    )

    result = cmd_finalize_step(
        _finalize_step_ns(plan_id='outcome-default', task=1, step=1, outcome='done')
    )

    assert result['artifact_lines'] == 0
    assert '[ARTIFACT]' not in _read_work_log(plan_context.plan_dir_for('outcome-default'))
