#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for manage-tasks.py finalize-step subcommand.

Split from test_manage_tasks.py: covers finalize-step outcomes (done /
skipped / failed), task-status derivation from step outcomes, and the two
script-level emission contracts the task-closing call owns — [OUTCOME] and
[ARTIFACT].

The [ARTIFACT] status-code mapping, the baseline-capture rules, the object-id
validation and the diff form are pinned against a real git repository in
``test_manage_tasks_artifact_emission.py``; what this module adds is the
END-TO-END proof that the task-closing ``finalize-step`` call actually writes
those lines to the plan's work log.

It also pins that both of this handler's gates are TRANSITIONS rather than
states: a REPEATED closing call emits neither channel a second time, and a
finalize on a task the record already shows as opened — ``in_progress``,
``done`` or ``failed`` — stamps no late baseline. Both predicates were computed
from the post-mutation record, where a transition and a repeat are
indistinguishable.
"""

import json
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from _manage_tasks_fixtures import (
    _finalize_step_ns,
    _update_ns,
    add_basic_task,
    cmd_finalize_step,
    cmd_update,
)

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


def _head(root) -> str:
    completed = subprocess.run(
        ['git', '-C', str(root), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


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


# The baseline capture has TWO entry paths: the implicit `in_progress` flip
# inside `finalize-step`, covered above, and the explicit `update --status
# in_progress` verb. Covering only one leaves the other free to regress into the
# exact state the capture exists to prevent — a task opened through `update`
# carrying no baseline, so its artifact channel is silently inert while the
# other path's tests stay green. The two cases below are the matched pair.


def _persisted_task(plan_context, plan_id: str, number: int = 1) -> dict:
    """Read the PERSISTED task record straight off disk.

    ⛔ NOT through `cmd_read`: that verb returns a fixed projection of the task
    and does not surface `task_start_sha`, so a read-back through it cannot see
    the field this pair is about — it would report the baseline as absent on
    both the positive and the negative case, and the pair would agree for the
    wrong reason.
    """
    path = plan_context.plan_dir_for(plan_id) / 'tasks' / f'TASK-{number:03d}.json'
    record: dict = json.loads(path.read_text(encoding='utf-8'))
    return record


def test_update_to_in_progress_records_the_baseline(plan_context, _artifact_repo):
    """The explicit entry path lands the same baseline as its finalize-step sibling."""
    add_basic_task(
        plan_id='outcome-default',
        title='Opened Through Update',
        deliverable=1,
        steps=['src/main/java/A.java'],
    )

    cmd_update(_update_ns(plan_id='outcome-default', number=1, status='in_progress'))

    task = _persisted_task(plan_context, 'outcome-default')
    assert task[_artifacts.TASK_START_SHA_FIELD] == _head(_artifact_repo)


def test_update_to_a_non_opening_status_records_no_baseline(plan_context, _artifact_repo):
    """The negative control — only the `in_progress` transition captures.

    Without it the positive case above would pass against an `update` that
    captured on EVERY status change, which would move the base forward on the
    closing transition and shrink the artifact list to nothing.
    """
    add_basic_task(
        plan_id='outcome-default',
        title='Blocked Without Opening',
        deliverable=1,
        steps=['src/main/java/A.java'],
    )

    cmd_update(_update_ns(plan_id='outcome-default', number=1, status='blocked'))

    task = _persisted_task(plan_context, 'outcome-default')
    assert _artifacts.TASK_START_SHA_FIELD not in task


def _write_persisted_task(plan_context, plan_id: str, record: dict, number: int = 1) -> None:
    """Write a task record straight to disk, bypassing the handlers.

    The states below — a task already `in_progress` and carrying NO baseline —
    are reachable in production (the field shipped after those tasks were
    opened) but are not reachable through the verbs, which now capture on the
    opening transition. Constructing the state directly is what makes the
    already-open population testable at all.
    """
    path = plan_context.plan_dir_for(plan_id) / 'tasks' / f'TASK-{number:03d}.json'
    path.write_text(json.dumps(record, indent=2), encoding='utf-8')


# =============================================================================
# Tests: the emission and capture predicates are TRANSITIONS, not states
# =============================================================================
#
# Both predicates were computed from the POST-mutation record, where a
# transition and a repeat are indistinguishable — so a retry of the closing call
# re-emitted both channels, and a late call on an already-open task stamped a
# baseline AFTER that task's earlier edits had landed.


def test_a_repeated_closing_finalize_emits_exactly_one_outcome_and_one_artifact_set(
    plan_context, _artifact_repo
):
    """⛔ The retry path is reachable in normal operation.

    A re-dispatch after a lost context is exactly the scenario the script-level
    guard exists for, so the closing call genuinely gets repeated — and the
    duplicate records inflate anything derived from them.
    """
    add_basic_task(
        plan_id='outcome-default',
        title='Retried Task',
        deliverable=1,
        steps=['src/main/java/A.java'],
    )
    plan_dir = plan_context.plan_dir_for('outcome-default')
    (_artifact_repo / 'seed.txt').write_text('touched by the task\n', encoding='utf-8')

    first = cmd_finalize_step(_finalize_step_ns(plan_id='outcome-default', task=1, step=1, outcome='done'))
    retry = cmd_finalize_step(_finalize_step_ns(plan_id='outcome-default', task=1, step=1, outcome='done'))

    log_text = _read_work_log(plan_dir)
    assert first['artifact_lines'] == 1
    assert retry['artifact_lines'] == 0
    assert log_text.count('[OUTCOME]') == 1
    assert log_text.count('[ARTIFACT]') == 1
    # The retry is still a successful, task-closing call — the emission is what
    # is suppressed, not the operation.
    assert retry['task_complete'] is True
    assert retry['task_status'] == 'done'


def test_the_first_closing_finalize_still_emits_both_channels(plan_context, _artifact_repo):
    """The control — suppressing the repeat must not suppress the real close.

    Without it, a gate that never fired would satisfy the retry assertion above.
    """
    add_basic_task(
        plan_id='outcome-default',
        title='Closed Once',
        deliverable=1,
        steps=['src/main/java/A.java'],
    )
    plan_dir = plan_context.plan_dir_for('outcome-default')
    (_artifact_repo / 'seed.txt').write_text('touched by the task\n', encoding='utf-8')

    cmd_finalize_step(_finalize_step_ns(plan_id='outcome-default', task=1, step=1, outcome='done'))

    log_text = _read_work_log(plan_dir)
    assert log_text.count('[OUTCOME]') == 1
    assert log_text.count('[ARTIFACT]') == 1


def test_a_finalize_on_an_already_open_baseline_less_task_stamps_no_late_baseline(
    plan_context, _artifact_repo
):
    """A late capture would be taken AFTER the task's earlier edits landed.

    The diff would then silently omit them — defeating `emit_artifact_lines`'
    own honesty guard, which returns [] for a baseline-less task precisely
    because a guessed base is worse than none.
    """
    add_basic_task(
        plan_id='outcome-default',
        title='Already Open',
        deliverable=1,
        steps=['src/main/java/A.java'],
    )
    record = _persisted_task(plan_context, 'outcome-default')
    record['status'] = 'in_progress'
    record.pop(_artifacts.TASK_START_SHA_FIELD, None)
    _write_persisted_task(plan_context, 'outcome-default', record)

    result = cmd_finalize_step(_finalize_step_ns(plan_id='outcome-default', task=1, step=1, outcome='done'))

    assert _artifacts.TASK_START_SHA_FIELD not in _persisted_task(plan_context, 'outcome-default')
    assert result['artifact_lines'] == 0


def test_a_finalize_on_a_pending_task_still_stamps_the_baseline(plan_context, _artifact_repo):
    """The control — only the already-open case is exempt from the capture."""
    add_basic_task(
        plan_id='outcome-default',
        title='Opened By Finalize',
        deliverable=1,
        steps=['src/main/java/A.java', 'src/main/java/B.java'],
    )

    cmd_finalize_step(_finalize_step_ns(plan_id='outcome-default', task=1, step=1, outcome='done'))

    task = _persisted_task(plan_context, 'outcome-default')
    assert task[_artifacts.TASK_START_SHA_FIELD] == _head(_artifact_repo)


@pytest.mark.parametrize('persisted_status', ['done', 'failed'], ids=['done', 'failed'])
def test_a_finalize_retry_on_an_already_run_task_stamps_no_late_baseline(
    plan_context, _artifact_repo, persisted_status
):
    """⛔ `in_progress` was not the whole already-opened population.

    A persisted `done` (or `failed`) task carrying no baseline — closed before
    the field existed, or hand-edited — reached the capture on a RETRY of its
    closing call, where the `prior_task_status != 'done'` emission gate
    suppresses [OUTCOME]/[ARTIFACT] but the task write still persists the
    stamped SHA. The base recorded there is the current HEAD, i.e. taken AFTER
    every edit the task made, and the capture's idempotence then means a later
    `update --status in_progress` reopening KEEPS it instead of recording the
    real opening baseline.
    """
    add_basic_task(
        plan_id='outcome-default',
        title='Already Run',
        deliverable=1,
        steps=['src/main/java/A.java'],
    )
    record = _persisted_task(plan_context, 'outcome-default')
    record['status'] = persisted_status
    record['steps'][0]['status'] = persisted_status
    record.pop(_artifacts.TASK_START_SHA_FIELD, None)
    _write_persisted_task(plan_context, 'outcome-default', record)

    cmd_finalize_step(_finalize_step_ns(plan_id='outcome-default', task=1, step=1, outcome='done'))

    assert _artifacts.TASK_START_SHA_FIELD not in _persisted_task(plan_context, 'outcome-default')


def test_a_retry_cannot_pin_a_reopening_to_the_late_baseline(plan_context, _artifact_repo):
    """The consequence the assertion above prevents, observed end to end.

    Without the gate the retry writes a SHA, and `capture_task_start_sha` is
    idempotent — so the `update --status in_progress` that genuinely reopens the
    task would keep the retry's late base forever.

    ⛔ HEAD is ADVANCED between the retry and the reopening. Without that the two
    candidate baselines are the same commit and the assertion passes against the
    ungated predecessor too — the control would be vacuous.
    """
    add_basic_task(
        plan_id='outcome-default',
        title='Reopened After A Retry',
        deliverable=1,
        steps=['src/main/java/A.java'],
    )
    record = _persisted_task(plan_context, 'outcome-default')
    record['status'] = 'done'
    record['steps'][0]['status'] = 'done'
    record.pop(_artifacts.TASK_START_SHA_FIELD, None)
    _write_persisted_task(plan_context, 'outcome-default', record)
    retry_head = _head(_artifact_repo)
    cmd_finalize_step(_finalize_step_ns(plan_id='outcome-default', task=1, step=1, outcome='done'))

    (_artifact_repo / 'seed.txt').write_text('advanced\n', encoding='utf-8')
    subprocess.run(
        ['git', '-C', str(_artifact_repo), 'commit', '-q', '-am', 'advance'],
        check=True,
        capture_output=True,
        text=True,
    )
    cmd_update(_update_ns(plan_id='outcome-default', number=1, status='in_progress'))

    task = _persisted_task(plan_context, 'outcome-default')
    assert _head(_artifact_repo) != retry_head
    assert task[_artifacts.TASK_START_SHA_FIELD] == _head(_artifact_repo)


def test_a_repeated_update_to_in_progress_does_not_move_the_baseline(plan_context, _artifact_repo):
    """The explicit entry path's half of the same predicate, with HEAD advanced.

    Idempotence alone already protects a task that HAS a baseline; this pins
    that the second call does not re-derive one against the newer HEAD.
    """
    add_basic_task(
        plan_id='outcome-default',
        title='Reopened Through Update',
        deliverable=1,
        steps=['src/main/java/A.java'],
    )

    cmd_update(_update_ns(plan_id='outcome-default', number=1, status='in_progress'))
    first_baseline = _persisted_task(plan_context, 'outcome-default')[_artifacts.TASK_START_SHA_FIELD]

    (_artifact_repo / 'seed.txt').write_text('advanced\n', encoding='utf-8')
    subprocess.run(
        ['git', '-C', str(_artifact_repo), 'commit', '-q', '-am', 'advance'],
        check=True,
        capture_output=True,
        text=True,
    )
    cmd_update(_update_ns(plan_id='outcome-default', number=1, status='in_progress'))

    assert _head(_artifact_repo) != first_baseline
    assert (
        _persisted_task(plan_context, 'outcome-default')[_artifacts.TASK_START_SHA_FIELD]
        == first_baseline
    )


def test_an_update_reopening_a_baseline_less_task_stamps_no_late_baseline(
    plan_context, _artifact_repo
):
    """The `update` half of the already-open case, matching its finalize sibling."""
    add_basic_task(
        plan_id='outcome-default',
        title='Already Open Via Update',
        deliverable=1,
        steps=['src/main/java/A.java'],
    )
    record = _persisted_task(plan_context, 'outcome-default')
    record['status'] = 'in_progress'
    record.pop(_artifacts.TASK_START_SHA_FIELD, None)
    _write_persisted_task(plan_context, 'outcome-default', record)

    cmd_update(_update_ns(plan_id='outcome-default', number=1, status='in_progress'))

    assert _artifacts.TASK_START_SHA_FIELD not in _persisted_task(plan_context, 'outcome-default')


def test_a_file_created_after_the_first_finalize_is_reported_as_an_artifact(
    plan_context, _artifact_repo
):
    """⛔ A created file is in NO ``git diff`` output until it is staged.

    The end-to-end pair only exercised the tracked-MODIFY path (``seed.txt``), so
    a regression that dropped the untracked walk would leave the largest class of
    artifact an implementation task produces — the files it creates — unreported
    while every existing end-to-end assertion stayed green.
    """
    add_basic_task(
        plan_id='outcome-default',
        title='Creating Task',
        deliverable=1,
        steps=['src/main/java/A.java', 'src/main/java/B.java'],
    )
    plan_dir = plan_context.plan_dir_for('outcome-default')

    cmd_finalize_step(_finalize_step_ns(plan_id='outcome-default', task=1, step=1, outcome='done'))
    (_artifact_repo / 'created-by-the-task.txt').write_text('new\n', encoding='utf-8')

    result = cmd_finalize_step(_finalize_step_ns(plan_id='outcome-default', task=1, step=2, outcome='done'))

    assert result['artifact_lines'] == 1
    assert '[ARTIFACT] (plan-marshall:phase-5-execute:1) Wrote created-by-the-task.txt' in (
        _read_work_log(plan_dir)
    )
