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


def _item_7c() -> str:
    return _between(_FINALIZE_SKILL.read_text(encoding='utf-8'), _ITEM_7C_START, _ITEM_7C_END)


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


def test_step_0_agrees_that_every_firing_commits_before_any_gate():
    step_0 = _between(_item_7c(), _STEP_0_START, '      (1) Resolve the level-bound target')

    assert step_0.strip(), f'step (0) of item 7c not found in {_FINALIZE_SKILL}'
    assert 'did not commit its edit' not in step_0
    assert 'Every firing runs (4a) on every return of the triage, before it evaluates any gate' in step_0
