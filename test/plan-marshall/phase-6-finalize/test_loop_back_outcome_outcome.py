#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end contract tests for the ``loop_back`` outcome.

These tests pin four invariants:

1. The producer-consumer FIX path records ``--outcome loop_back`` (not
   ``done``) on the ``automatic-review`` step, and the persisted shape on
   disk matches the contract.
2. The phase-6-finalize Step 3 dispatcher table treats a pre-seeded
   ``loop_back`` record as a re-fire (not a skip). Since the dispatcher
   logic lives in markdown, we validate the contract by exercising
   ``manage-status`` directly and verifying the persisted record.
3. The FIX action body in ``automatic-review.md`` posts the
   ``prepare-add → commit-add → prepare-comment → thread-reply →
   resolve-thread → manage-findings resolve`` chain (regression-guard
   against future re-orderings) and Branch C still records
   ``--outcome loop_back``.
4. The Resumability section in ``phase-6-finalize/SKILL.md`` retains the
   ``pre-push-quality-gate`` HEAD-comparison rows (steady-state vs.
   mismatched HEAD), and membership in that comparison is read from the
   **derived** ``head_dependent`` frontmatter fact rather than the removed
   ``HEAD_DEPENDENT_STEPS`` literal.
5. A loop-back commit that advances HEAD past a recorded ``done`` on
   ``pre-submission-self-review`` re-fires the step instead of skipping it.
   That step reviews the plan's DIFF, so a ``done`` carried across a
   loop-back would stand as green for a diff no check ever ran against —
   the defect that motivated deriving membership in the first place.
6. A self-review round the VERIFIER declined to close records ``loop_back``
   with ``loop_back_target: 6-finalize`` — never ``done`` and never
   ``failed``. The close decision belongs to the party that did not write
   the verdict, so this pins the other side of that decision: ``done``
   there would close a review a second party declined to close, and
   ``failed`` would grade a working independence check as a broken step.

The tests use unique ``plan_id`` values per test to avoid cross-test
contamination (per MEMORY.md "Test Isolation Pattern").
"""

import re
from argparse import Namespace
from pathlib import Path

from conftest import get_skill_dir, load_script_module

# =============================================================================
# Module loading (mirrors test_mark_step_done.py / test_manage_status.py)
# =============================================================================


_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_loop_back_lifecycle')
_mark_step = load_script_module('plan-marshall', 'manage-status', '_cmd_mark_step.py', '_loop_back_mark_step')
_status_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_loop_back_status_core')

cmd_create = _lifecycle.cmd_create
cmd_mark_step_done = _mark_step.cmd_mark_step_done
read_status = _status_core.read_status

# =============================================================================
# Standards file paths, resolved through the shipped skill-directory accessor.
# =============================================================================

_PHASE_6_DIR = get_skill_dir('plan-marshall', 'phase-6-finalize')
_PHASE_6_SKILL_MD = _PHASE_6_DIR / 'SKILL.md'
_AUTOMATED_REVIEW_MD = get_skill_dir('plan-marshall', 'automatic-review') / 'SKILL.md'
_PRE_SUBMISSION_SELF_REVIEW_MD = _PHASE_6_DIR / 'workflow' / 'pre-submission-self-review.md'

#: The removed hand-maintained literal. Its ABSENCE from SKILL.md is what makes
#: membership derived rather than listed, so it is asserted absent by name.
_RETIRED_LITERAL = 'HEAD_DEPENDENT_STEPS'

#: The self-review section where the verifier's two answers are collected and
#: routed. Test 6 reads it for the states that do NOT close the round.
_VERIFIER_STEP_HEADING = '### Step 3b: Independent verification (dispatch)'

#: The state names the verifier's non-closing outcomes are filed under. A
#: population FLOOR, not the sweep's population: the assertion below derives
#: the actual per-state routing from the section's own state-to-outcome table,
#: and only checks that these three still appear among the derived rows — so a
#: state that loses its row loses its documented routing, and this floor
#: notices the loss even if the whole table were somehow removed.
_NON_CLOSE_STATES = ('verdict_refused', 'further_round_owed', 'verifier_unavailable')

#: One row of the section's `` | `{state}` | ... | `{outcome}` | `` state-to-outcome
#: table. Captures the state token and its recorded outcome; the middle
#: "Verifier situation" column is read and discarded.
_STATE_OUTCOME_ROW = re.compile(r'^\|\s*`([a-z_]+)`\s*\|.*\|\s*`([a-z_]+)`\s*\|\s*$', re.MULTILINE)


def _non_close_state_outcome_rows(section: str) -> list[tuple[str, str]]:
    """Return every ``(state, recorded_outcome)`` row from the section's own table.

    Every parsed row, not a deduped ``{state: outcome}`` view: collapsing into
    a dict keeps only the LAST row per state, so a duplicate row for the same
    state would be silently discarded before any routing assertion saw it. A
    row whose state token is not a real state name (e.g. the header's
    ``{state}`` placeholder) never matches ``[a-z_]+`` against a literal `{`,
    so the header and separator rows are excluded by construction rather than
    by position.
    """
    return _STATE_OUTCOME_ROW.findall(section)


def _section_after(text: str, heading: str) -> str:
    """Return the text between ``heading`` and the next ``### `` heading line.

    Deliberately local and tiny: this module reads whole documents everywhere
    else, and the one section it needs is bounded by a heading it can name. An
    absent heading yields the empty string, which every caller asserts against —
    a relocated section then fails loudly instead of sweeping nothing.
    """
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line.strip() == heading), None)
    if start is None:
        return ''
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith('### '):
            break
        body.append(line)
    return '\n'.join(body)


def _declares_head_dependent(doc_path: Path) -> bool:
    """True when a step doc declares the derived ``head_dependent: true`` fact."""
    for line in doc_path.read_text(encoding='utf-8').splitlines():
        if line.strip() == 'head_dependent: true':
            return True
    return False


def _make_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Loop-back Outcome Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def _args(
    plan_id: str,
    phase: str,
    step: str,
    outcome: str,
    force: bool = False,
    display_detail: str | None = None,
    head_at_completion: str | None = None,
    loop_back_target: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        step=step,
        outcome=outcome,
        force=force,
        display_detail=display_detail,
        head_at_completion=head_at_completion,
        loop_back_target=loop_back_target,
    )


# =============================================================================
# Test 1: FIX disposition path records --outcome loop_back (not done)
# =============================================================================


_TRIAGE_MD = get_skill_dir('plan-marshall', 'plan-marshall') / 'workflow' / 'triage.md'


def test_iteration_1_fix_records_loop_back_outcome(plan_context):
    """Driving the FIX-disposition path records ``loop_back`` on disk.

    The producer-consumer flow (see automatic-review.md "Mark Step Complete"
    Branch C) calls ``manage-status mark-step-done`` with ``--outcome loop_back``
    when one or more pr-comment findings resolve to FIX. The simplest way to
    validate this contract is to invoke the underlying ``cmd_mark_step_done``
    with the same arguments Branch C documents and assert that
    ``phase_steps["6-finalize"]["automatic-review"].outcome`` on disk is
    ``loop_back`` — not ``done``.
    """
    plan_id = 'loop-back-fix-iter1'
    _make_plan(plan_id)
    result = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'automatic-review',
            'loop_back',
            display_detail='loop-back iteration 1 (target=5-execute)',
            loop_back_target='5-execute',
        )
    )

    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['outcome'] == 'loop_back'
    assert result['display_detail'] == 'loop-back iteration 1 (target=5-execute)'
    # The hybrid-loopback contract: every loop_back outcome carries an
    # explicit granularity target. FIX dispositions allocate fix tasks and
    # roll back to phase-5-execute.
    assert result['loop_back_target'] == '5-execute'

    persisted = read_status(plan_id)
    entry = persisted['metadata']['phase_steps']['6-finalize']['automatic-review']
    # On-disk contract: outcome is loop_back, NOT done; loop_back_target is
    # persisted alongside outcome and display_detail.
    assert entry['outcome'] == 'loop_back', f'FIX disposition must record outcome=loop_back; got {entry["outcome"]!r}'
    assert entry['outcome'] != 'done'
    assert entry['display_detail'] == 'loop-back iteration 1 (target=5-execute)'
    assert entry['loop_back_target'] == '5-execute', (
        'FIX disposition must persist loop_back_target=5-execute alongside outcome'
    )


def test_fix_path_posts_thread_reply_before_terminal_done():
    """Regression-guard the FIX action ordering and the loop-back outcome.

    Under the consolidated find/ingest/one-triage/one-respond flow, triage
    RECORDS the disposition; the reviewer-facing transmission (thread-reply +
    resolve-thread) is owned by the single RESPOND loop (`post_responses`), NOT
    inline in the FIX body. So the FIX action body in
    ``plan-marshall/workflow/triage.md`` must invoke (in order):

        prepare-add  →  commit-add  →  manage-findings resolve

    and the calling step's Branch C ("loop-back recorded") in
    ``phase-6-finalize/workflow/automatic-review.md`` must record
    ``--outcome loop_back``, NOT ``--outcome done``. This test reads
    both files and asserts both invariants. It is a structural
    regression-guard against future edits that accidentally re-order
    the chain, re-inline the provider transmission into FIX, or downgrade
    Branch C to ``done``.
    """
    triage_body = _TRIAGE_MD.read_text(encoding='utf-8')

    # Locate the FIX action block in triage.md. The "FIX" bullet starts
    # with "- **FIX**" and runs until the next top-level disposition
    # bullet ("- **SUPPRESS**").
    fix_marker = '- **FIX**'
    suppress_marker = '- **SUPPRESS**'
    fix_start = triage_body.find(fix_marker)
    suppress_start = triage_body.find(suppress_marker, fix_start)
    assert fix_start != -1, 'FIX action block not found in triage.md'
    assert suppress_start != -1, 'SUPPRESS marker not found after FIX block'
    fix_block = triage_body[fix_start:suppress_start]

    # The chain must appear in the FIX block in the exact order. The provider
    # transmission (thread-reply / resolve-thread) is deliberately absent — it
    # moved to the RESPOND loop — so it is NOT part of this ordered chain.
    expected_chain = [
        'prepare-add',
        'commit-add',
        'manage-findings resolve',
    ]
    cursor = 0
    for token in expected_chain:
        idx = fix_block.find(token, cursor)
        assert idx != -1, f'FIX action block missing required token {token!r}; expected ordered chain: {expected_chain}'
        cursor = idx + len(token)

    # The calling site's Branch C is in automatic-review.md. It must use
    # --outcome loop_back, not --outcome done.
    auto_body = _AUTOMATED_REVIEW_MD.read_text(encoding='utf-8')
    branch_c_marker = '**Branch C'
    branch_c_start = auto_body.find(branch_c_marker)
    assert branch_c_start != -1, 'Branch C section not found in automatic-review.md'
    branch_c_block = auto_body[branch_c_start:]
    assert '--outcome loop_back' in branch_c_block, 'Branch C must record `--outcome loop_back` (not `done`).'
    next_mark = branch_c_block.find('mark-step-done')
    assert next_mark != -1, 'Branch C does not invoke mark-step-done'
    window = branch_c_block[next_mark : next_mark + 400]
    assert '--outcome done' not in window, (
        'Branch C mark-step-done must not use --outcome done — that is the '
        'terminal Branch A outcome and would cause the dispatcher to skip the '
        'step on re-entry.'
    )
    assert '--outcome loop_back' in window


def test_loop_back_commit_re_fires_pre_submission_self_review(plan_context):
    """A loop-back HEAD advance invalidates a recorded self-review verdict.

    ``pre-submission-self-review`` is one of the three members the retired
    hand-maintained literal OMITTED. Its verdict is a structural review of the
    plan's DIFF, so a ``done`` record carried across a loop-back commit stands
    as green for a diff no check ever examined — the motivating defect.

    The dispatcher's re-entry decision lives in markdown, so (mirroring test 2's
    approach for markdown-resident dispatcher logic) this test exercises the
    persisted record through ``manage-status`` and asserts the two inputs the
    documented table branches on: the step IS head-dependent (derived fact), and
    the terminal ``done`` record actually persists the SHA its verdict was
    computed against — without which the table has nothing to compare a later
    HEAD against and degrades to an unconditional SKIP.
    """
    plan_id = 'loopback-d4a-self-review'
    _make_plan(plan_id)

    head_at_verdict = 'a' * 40

    cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'pre-submission-self-review',
            'done',
            display_detail='self-review clean: 12 candidates examined, no check matched',
            head_at_completion=head_at_verdict,
        )
    )

    persisted = read_status(plan_id)
    entry = persisted['metadata']['phase_steps']['6-finalize']['pre-submission-self-review']

    assert entry['outcome'] == 'done'
    assert entry['head_at_completion'] == head_at_verdict, (
        'The terminal done record must persist the SHA the verdict was computed '
        'against — without it the dispatcher has nothing to compare and the '
        're-entry check degrades to an unconditional skip.'
    )

    # The step must be IN scope for the HEAD-comparison table at all. Membership
    # is the derived frontmatter fact — this is the assertion that would have
    # failed while the step was missing from the hand-maintained literal.
    assert _declares_head_dependent(_PRE_SUBMISSION_SELF_REVIEW_MD), (
        'pre-submission-self-review must declare head_dependent: true. Its verdict '
        'is a function of the plan diff, so without the declaration a loop-back '
        'commit leaves a stale done record standing as green for an unreviewed diff.'
    )


def test_a_verifier_declined_round_persists_as_an_inline_fixable_loop_back(plan_context):
    """Driving the declined-round path records loop_back with the 6-finalize target.

    The behavioural half, in this module's established shape: invoke the same
    ``mark-step-done`` arguments Step 4 Branch B documents for a round the
    verifier declined, and assert the persisted record. The target is
    ``6-finalize`` rather than ``5-execute`` because a declined round is resolved
    by amending the diff in hand — no fix task is allocated, so rolling back to
    phase-5-execute would send the round somewhere it has no work to do.
    """
    plan_id = 'loopback-verifier-declined'
    _make_plan(plan_id)

    result = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'pre-submission-self-review',
            'loop_back',
            display_detail='self-review found 1 issues in 1 classes',
            loop_back_target='6-finalize',
        )
    )

    assert result['status'] == 'success'
    assert result['outcome'] == 'loop_back'

    persisted = read_status(plan_id)
    entry = persisted['metadata']['phase_steps']['6-finalize']['pre-submission-self-review']

    assert entry['outcome'] == 'loop_back', (
        f'A round the verifier declined to close must record loop_back; got {entry["outcome"]!r}'
    )
    assert entry['loop_back_target'] == '6-finalize', (
        'A declined round is resolved by amending the diff in hand, so it re-enters '
        'the finalize step loop rather than rolling back to phase-5-execute.'
    )
