#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``[STEP] … Completed step:`` line is FUSED to the mark-step-done handshake.

Recording a finalize step's terminal outcome and emitting its completion line used
to be TWO obligations: the ``mark-step-done`` write PLUS a separate, hand-written
``manage-logging work "[STEP] …"`` step in the phase-6-finalize dispatcher prose. A
step could satisfy the handshake and still leave no operational-log trace, because
the prose instruction was easy to skip and nothing read the log back to confirm it
— the invariant and the line could drift, and only ever toward silence.

These tests pin the fusion (``_cmd_mark_step.py::_emit_completion_marker``):

- a ``6-finalize`` terminal write emits the completion line ONCE, from the write;
- it fires for every terminal outcome (``done`` / ``skipped`` / ``failed``), since
  each settles the step;
- ``--no-completion-log`` (the item-5f re-stamp path) suppresses the second emit so
  a re-stamped ``done`` produces exactly one line;
- the emission is SCOPED to the finalize phase, so every other phase's
  ``mark-step-done`` writes no such line (the dispatch audit's completion_count is
  unchanged for them);
- an unchanged idempotent re-call performs no write, so it does not re-emit.

Steps are named with synthetic keys (``step-a`` …) that are absent from the
finalize-step registry, so the head-dependence fail-closed guard never fires and a
``done`` needs no ``--head-at-completion`` — the emission is scoped by PHASE, not by
step identity, so the step name is immaterial to what is under test.
"""

from argparse import Namespace

from plan_logging import read_work_log

from conftest import load_script_module

_lifecycle = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_emit_lifecycle'
)
_mark_step = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_mark_step.py', '_emit_mark_step'
)

cmd_create = _lifecycle.cmd_create
cmd_mark_step_done = _mark_step.cmd_mark_step_done

_COMPLETION_PREFIX = '[STEP] (plan-marshall:phase-6-finalize) Completed step:'


def _make_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Completion Emission Test',
            phases='1-init,5-execute,6-finalize',
            force=False,
        )
    )


def _mark(
    plan_id: str,
    phase: str,
    step: str,
    outcome: str,
    *,
    head_at_completion: str | None = None,
    display_detail: str | None = None,
    no_completion_log: bool = False,
    force: bool = False,
) -> dict:
    # cmd_mark_step_done is Any (loaded via load_script_module), so bind its result
    # to a typed local before returning — a bare return trips mypy's no-any-return.
    result: dict = cmd_mark_step_done(
        Namespace(
            plan_id=plan_id,
            phase=phase,
            step=step,
            outcome=outcome,
            force=force,
            display_detail=display_detail,
            head_at_completion=head_at_completion,
            loop_back_target=None,
            fact=None,
            no_completion_log=no_completion_log,
        )
    )
    return result


def _completion_lines(plan_id: str) -> list[str]:
    result = read_work_log(plan_id)
    assert result['status'] == 'success', result
    return [
        entry['message']
        for entry in result['entries']
        if entry['message'].startswith('[STEP]') and 'Completed step:' in entry['message']
    ]


def test_finalize_mark_step_done_emits_the_fused_completion_line(plan_context):
    plan_id = 'fuse-emit'
    _make_plan(plan_id)

    result = _mark(plan_id, '6-finalize', 'step-a', 'done')

    assert result['status'] == 'success', result
    lines = _completion_lines(plan_id)
    assert len(lines) == 1, f'expected exactly one fused completion line, got {lines}'
    assert lines[0].startswith(_COMPLETION_PREFIX), lines[0]
    assert 'step-a' in lines[0]


def test_fused_line_fires_for_every_terminal_outcome(plan_context):
    # skipped and failed settle a step just as done does; each must emit its line.
    plan_id = 'fuse-outcomes'
    _make_plan(plan_id)

    assert _mark(plan_id, '6-finalize', 'step-b', 'skipped')['status'] == 'success'
    assert _mark(plan_id, '6-finalize', 'step-c', 'failed')['status'] == 'success'

    lines = _completion_lines(plan_id)
    assert len(lines) == 2, f'skipped + failed must each emit, got {lines}'


def test_no_completion_log_suppresses_the_re_stamp_emission(plan_context):
    # The item-5f shape: a done, then a re-stamp of the same done with a changed
    # head_at_completion. The re-stamp carries --no-completion-log, so exactly one
    # completion line survives rather than one per mark-step-done call.
    plan_id = 'fuse-suppress'
    _make_plan(plan_id)

    assert _mark(plan_id, '6-finalize', 'step-d', 'done')['status'] == 'success'
    restamp = _mark(
        plan_id,
        '6-finalize',
        'step-d',
        'done',
        head_at_completion='def456',
        no_completion_log=True,
    )
    assert restamp['status'] == 'success'
    assert restamp['changed'] is True, 'the re-stamp must be a real write (head changed)'

    lines = _completion_lines(plan_id)
    assert len(lines) == 1, f're-stamp with --no-completion-log must not re-emit, got {lines}'


def test_emission_is_scoped_to_the_finalize_phase(plan_context):
    # A non-finalize phase writes NO completion line — the marker is a finalize
    # observable, and scoping keeps the dispatch audit's completion_count unchanged
    # for every other phase.
    plan_id = 'fuse-scope'
    _make_plan(plan_id)

    assert _mark(plan_id, '5-execute', 'step-e', 'done')['status'] == 'success'

    assert _completion_lines(plan_id) == []


def test_unchanged_recall_does_not_re_emit(plan_context):
    # An idempotent re-call (identical outcome/detail/head) performs no write, so it
    # must not emit a second completion line.
    plan_id = 'fuse-idempotent'
    _make_plan(plan_id)

    assert _mark(plan_id, '6-finalize', 'step-f', 'done')['status'] == 'success'
    recall = _mark(plan_id, '6-finalize', 'step-f', 'done')
    assert recall['changed'] is False, 'an identical re-call must be a no-op write'

    lines = _completion_lines(plan_id)
    assert len(lines) == 1, f'an unchanged re-call must not re-emit, got {lines}'


# ---------------------------------------------------------------------------
# The line says HOW a step finished, not merely THAT it did
# ---------------------------------------------------------------------------


def test_a_failed_firing_and_a_done_firing_are_distinguishable(plan_context):
    """Matched control: the outcome is what tells the two firings apart.

    RED before the widening. The marker named only the step, so a ``failed``
    settlement and a ``done`` settlement of the same step emitted BYTE-IDENTICAL
    lines: a reader counting completions in the work log could see that a step had
    settled but not whether it had succeeded, and had to re-open
    ``status.metadata.phase_steps`` to find out. The writer held the outcome the
    whole time.

    The two firings use the SAME step key in two plans, so the step name is held
    constant and the outcome is the ONLY thing that can distinguish the lines —
    two different step names would have differed before the widening too, and the
    control would have proved nothing.
    """
    _make_plan('fuse-outcome-done')
    _make_plan('fuse-outcome-failed')

    assert _mark('fuse-outcome-done', '6-finalize', 'step-z', 'done')['status'] == 'success'
    assert _mark('fuse-outcome-failed', '6-finalize', 'step-z', 'failed')['status'] == 'success'

    done_lines = _completion_lines('fuse-outcome-done')
    failed_lines = _completion_lines('fuse-outcome-failed')

    # Count parity: the widening changed the line's CONTENT, never how many are
    # emitted. The dispatch audit's completion_count is derived from this count.
    assert len(done_lines) == 1, f'expected one done line, got {done_lines}'
    assert len(failed_lines) == 1, f'expected one failed line, got {failed_lines}'

    done_line, failed_line = done_lines[0], failed_lines[0]

    assert done_line != failed_line, (
        f'a done firing and a failed firing of the same step emitted identical '
        f'lines ({done_line!r}), so the work log records THAT the step settled but '
        f'not HOW — the defect this widening closes.'
    )
    assert 'outcome=done' in done_line, done_line
    assert 'outcome=failed' in failed_line, failed_line

    # ...and the outcome is the ONLY difference. Were anything else to vary, the
    # inequality above could hold for a reason that has nothing to do with the
    # outcome, and this control would be passing by accident.
    assert done_line.replace('outcome=done', '<O>') == failed_line.replace(
        'outcome=failed', '<O>'
    ), (
        f'the two lines differ somewhere other than the outcome:\n'
        f'  done:   {done_line}\n  failed: {failed_line}'
    )
