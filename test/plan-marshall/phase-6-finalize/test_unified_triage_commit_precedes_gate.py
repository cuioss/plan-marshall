#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The unified-triage hook commits the triage's edits before it evaluates any gate.

The unified triage applies its inline edits in the worktree and commits nothing;
``phase-6-finalize`` item 7c step (4) commits, pushes and stamps them. The same
step routes a ``loop_back`` return through item 7b, which has two paths that
stop: the ceiling refusal and the ``loop_back_without_asking: false`` halt. A
commit block that runs only on the way back into the loop is skipped by both, so
the edit stays uncommitted and the reply to its finding is never sent.

This suite pins the order in the document: the commit block comes first, runs on
every return, and the admission gate is named only after it. The order detector
is exercised against two synthetic texts first, one in each order, so a detector
that silently reports "in order" cannot make the real assertion pass.

It also pins what a failed commit or push leaves behind. With HEAD unchanged the
re-entry check skips both wait-region producers, so a hook that merely stops is
never fired again and the edit stays uncommitted. The hook therefore records the
producer that fired it as ``failed``, which the re-entry check retries, and reads
the pending tasks on a ``success`` return so a fix task an earlier firing
allocated still reaches the execute phase.
"""

from __future__ import annotations

from conftest import get_skill_dir

_FINALIZE_SKILL = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'SKILL.md'

_ITEM_7C_START = '  7c. Wait-region unified triage hook'
_ITEM_7C_END = '\nEND FOR'

_STEP_0_START = '      (0) **Stamp the pushed fix commits'
_STEP_4_START = '      (4) Consume the return'
_STEP_4_END = 'This hook is dispatcher-owned and produces NO'

#: The commit the hook makes for the triage's edits, by its commit message.
_COMMIT_MARKER = 'fix(review): apply inline review dispositions'

#: The item-7b admission gate, by the call that decides it.
_GATE_MARKER = 'loop-back admit'

#: The knob item 7b reads after the gate.
_KNOB_MARKER = '`loop_back_without_asking` knob'

#: Where the hook states what it does when its commit or its push fails.
_FAILURE_START = 'When the commit or the push fails'
_ROUTE_START = '**(4b) Route the return'

#: The two calls the failure handling and the routing rest on, as script subcommands.
#: Matching the bare words would also take a logging call whose message names them.
_MARK_STEP_VERB = ':manage-status mark-step-done '
_TASK_LIST_VERB = ':manage-tasks list '


def _between(text: str, start: str, end: str) -> str:
    """Return ``text`` from the single ``start`` marker up to the next ``end`` marker.

    An absent marker returns the empty string, and so does a repeated ``start``.
    """
    if text.count(start) != 1:
        return ''
    begin = text.index(start)
    stop = text.find(end, begin)
    if stop == -1:
        return ''
    return text[begin:stop]


def _commit_precedes_gate(step: str) -> bool:
    """Whether ``step`` names the commit before the gate and before the knob.

    All three markers must be present. A text that lacks one is not "in order":
    it is a text the detector cannot judge, and it is reported as out of order.
    """
    positions = [step.find(marker) for marker in (_COMMIT_MARKER, _GATE_MARKER, _KNOB_MARKER)]
    if -1 in positions:
        return False
    commit, gate, knob = positions
    return commit < gate and commit < knob


def _commands(text: str) -> list[str]:
    """Every ``execute-script.py`` invocation in ``text``, one string per call.

    A call starts on a line naming ``execute-script.py`` and runs on while the line
    ends in a backslash. Only the part before ``--message`` is kept, so a verb or a
    flag that a log message merely mentions is not read as part of a call.
    """
    calls: list[str] = []
    current: list[str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if current is None:
            if 'execute-script.py' not in stripped:
                continue
            current = []
        current.append(stripped.removesuffix('\\').strip())
        if stripped.endswith('\\'):
            continue
        calls.append(' '.join(current).split(' --message ', 1)[0] + ' ')
        current = None
    return calls


def _marks_a_step_failed(text: str) -> bool:
    """Whether ``text`` issues a ``mark-step-done`` call that records ``failed``."""
    return any(_MARK_STEP_VERB in call and '--outcome failed ' in call for call in _commands(text))


def _reads_pending_tasks(text: str) -> bool:
    """Whether ``text`` issues a ``manage-tasks list`` call filtered to pending tasks."""
    return any(_TASK_LIST_VERB in call and '--status pending ' in call for call in _commands(text))


def _item_7c() -> str:
    return _between(_FINALIZE_SKILL.read_text(encoding='utf-8'), _ITEM_7C_START, _ITEM_7C_END)


def _failure_handling() -> str:
    return _between(_step_4(), _FAILURE_START, _ROUTE_START)


def _routing() -> str:
    """Step (4) from its (4b) part to its end; empty when the marker is absent or repeated."""
    step = _step_4()
    return step[step.index(_ROUTE_START) :] if step.count(_ROUTE_START) == 1 else ''


def _step_4() -> str:
    return _between(_item_7c(), _STEP_4_START, _STEP_4_END)


#: Step (4) with the gate first and the commit on the way back into the loop.
_SYNTHETIC_GATE_FIRST = """\
      (4) Consume the return. On `status: loop_back`, run the item-7b admission gate
          (`loop-back admit --source wait-region-unified-triage`), then apply the
          symmetric `loop_back_without_asking` knob. Re-enter per the granularity branch.

          **Before re-entering** — commit with the message
          `fix(review): apply inline review dispositions`, then push and stamp.
"""

#: Step (4) with the commit first and the gate after it.
_SYNTHETIC_COMMIT_FIRST = """\
      (4) Consume the return, in two parts.

          **(4a) On every return** — commit with the message
          `fix(review): apply inline review dispositions`, then push and stamp.

          **(4b) Route the return.** Run the item-7b admission gate
          (`loop-back admit --source wait-region-unified-triage`), then apply the
          symmetric `loop_back_without_asking` knob.
"""

#: A failure that is logged and stopped on, with no record for the next entry to act on.
_SYNTHETIC_FAILURE_ONLY_STOPS = """\
          When the commit or the push fails, log the failure at ERROR and STOP here.
"""

#: The same, where only a log message names the call that would record the failure.
_SYNTHETIC_FAILURE_NAMED_IN_A_MESSAGE = """\
          When the commit or the push fails, log the failure at ERROR and STOP here:

          python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \\
            work --plan-id {plan_id} --level ERROR \\
            --message "run plan-marshall:manage-status:manage-status mark-step-done --outcome failed by hand"
"""

#: A failure that records the producer as failed before it stops.
_SYNTHETIC_FAILURE_MARKS_FAILED = """\
          When the commit or the push fails, mark the producer failed and STOP here:

          python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \\
            --plan-id {plan_id} --phase 6-finalize --step {step_id} --outcome failed \\
            --display-detail "unified triage: commit of the inline review edits failed"
"""


# ---------------------------------------------------------------------------
# The detector, against synthetic text
# ---------------------------------------------------------------------------


def test_the_order_detector_reports_a_gate_that_comes_first():
    """Positive control: the shape that skips the commit on a halting path is caught."""
    assert _commit_precedes_gate(_SYNTHETIC_GATE_FIRST) is False


def test_the_order_detector_accepts_a_commit_that_comes_first():
    assert _commit_precedes_gate(_SYNTHETIC_COMMIT_FIRST) is True


def test_the_order_detector_does_not_accept_a_text_missing_a_marker():
    assert _commit_precedes_gate('Consume the return and continue the FOR loop.') is False
    assert _commit_precedes_gate(_SYNTHETIC_COMMIT_FIRST.replace(_GATE_MARKER, 'admission')) is False


# ---------------------------------------------------------------------------
# phase-6-finalize item 7c step (4): the real document
# ---------------------------------------------------------------------------


def test_step_4_of_the_hook_is_found():
    """Vacuity guard: every assertion below reads a slice, and an empty slice proves nothing."""
    assert _item_7c().strip(), f'item 7c not found in {_FINALIZE_SKILL}'
    assert _step_4().strip(), f'step (4) of item 7c not found in {_FINALIZE_SKILL}'


def test_the_commit_block_precedes_the_admission_gate_and_the_knob():
    assert _commit_precedes_gate(_step_4())


def test_the_commit_block_runs_on_every_return():
    step = _step_4()

    assert '(4a) runs on EVERY return of the unified triage' in step
    assert '`status: loop_back` and `status: success` alike' in step
    assert 'BEFORE (4b) evaluates anything' in step
    assert 'Before re-entering' not in step


def test_both_halting_paths_of_item_7b_are_named_as_reached_after_the_commit():
    step = _step_4()

    assert 'the ceiling refusal at its (i)' in step
    assert 'the `loop_back_without_asking: false` halt at its (ii)' in step
    assert "both halt with the triage's edits already committed and pushed" in step


def test_a_success_return_that_edited_a_file_is_not_continued_past():
    step = _step_4()

    assert 'A `status: success` return on which (4a) committed an edit is NOT continued past' in step
    assert 'with `loop_back_target: 6-finalize`' in step


# ---------------------------------------------------------------------------
# A failed commit or push: the detector, then the real document
# ---------------------------------------------------------------------------


def test_the_failure_detector_reports_a_hook_that_only_stops():
    """Positive control: a stop with no record is the shape the next entry never acts on."""
    assert _marks_a_step_failed(_SYNTHETIC_FAILURE_ONLY_STOPS) is False


def test_the_failure_detector_ignores_a_call_named_inside_a_log_message():
    assert _marks_a_step_failed(_SYNTHETIC_FAILURE_NAMED_IN_A_MESSAGE) is False


def test_the_failure_detector_accepts_a_real_failed_record():
    assert _marks_a_step_failed(_SYNTHETIC_FAILURE_MARKS_FAILED) is True


def test_a_failed_commit_or_push_marks_the_producer_failed():
    handling = _failure_handling()

    assert handling.strip(), f'the failure handling of step (4a) not found in {_FINALIZE_SKILL}'
    assert _marks_a_step_failed(handling)
    assert 'a `failed` step is retried there whatever HEAD is' in handling
    assert 'commits every tracked edit the worktree holds' in handling


def test_a_success_return_reads_the_pending_tasks_before_it_continues():
    """A fix task an earlier firing allocated is routed to the execute phase."""
    routing = _routing()

    assert routing.strip(), f'part (4b) of step (4) not found in {_FINALIZE_SKILL}'
    assert _reads_pending_tasks(routing)
    assert _reads_pending_tasks(_SYNTHETIC_FAILURE_MARKS_FAILED) is False
    assert '`loop_back_target: 5-execute`' in routing
    assert 'A task count that could not be read is not a count of zero' in routing


def test_step_0_agrees_that_every_firing_commits_before_any_gate():
    step_0 = _between(_item_7c(), _STEP_0_START, '      (1) Resolve the level-bound target')

    assert step_0.strip(), f'step (0) of item 7c not found in {_FINALIZE_SKILL}'
    assert 'did not commit its edit' not in step_0
    assert 'Every firing runs (4a) on every return of the triage, before it evaluates any gate' in step_0
