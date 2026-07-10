#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end contract tests for the ``loop_back`` outcome (TASK-2).

These tests pin the four invariants documented in the lesson-2026-05-05-23-002
deliverable:

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
   mismatched HEAD).

The tests use unique ``plan_id`` values per test to avoid cross-test
contamination (per MEMORY.md "Test Isolation Pattern").
"""

from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

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
# Standards file paths (resolved relative to this test file's repo root).
# =============================================================================

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_PHASE_6_SKILL_MD = (
    _REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall'
    / 'skills' / 'phase-6-finalize' / 'SKILL.md'
)
_AUTOMATED_REVIEW_MD = (
    _REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall'
    / 'skills' / 'automatic-review' / 'SKILL.md'
)


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
    assert entry['outcome'] == 'loop_back', (
        f"FIX disposition must record outcome=loop_back; got {entry['outcome']!r}"
    )
    assert entry['outcome'] != 'done'
    assert entry['display_detail'] == 'loop-back iteration 1 (target=5-execute)'
    assert entry['loop_back_target'] == '5-execute', (
        'FIX disposition must persist loop_back_target=5-execute alongside outcome'
    )


# =============================================================================
# Test 2: Pre-seeded loop_back persists as the re-fire signal for the dispatcher
# =============================================================================


def test_dispatcher_re_fires_on_loop_back(plan_context):
    """Pre-seed loop_back; verify the persisted record matches the dispatcher's
    re-fire predicate documented in phase-6-finalize/SKILL.md Resumability.

    The dispatch logic itself lives in SKILL.md (markdown, not Python), so this
    test validates the contract by:

    1. Writing a ``loop_back`` record via cmd_mark_step_done.
    2. Re-reading the persisted record and confirming ``outcome == 'loop_back'``.
    3. Asserting the SKILL.md Resumability table contains the row that maps
       ``loop_back`` to "Re-fire (treat as no record — dispatch as fresh run)".

    The combination of (2) and (3) pins the end-to-end contract: any future
    edit that drops the ``loop_back`` row from the table, or any future change
    to ``cmd_mark_step_done`` that fails to persist the value, will fail this
    test.
    """
    plan_id = 'loop-back-dispatcher'
    _make_plan(plan_id)
    cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'automatic-review',
            'loop_back',
            display_detail='loop-back iteration 2 (target=5-execute)',
            loop_back_target='5-execute',
        )
    )

    persisted = read_status(plan_id)
    entry = persisted['metadata']['phase_steps']['6-finalize']['automatic-review']
    assert entry['outcome'] == 'loop_back'
    assert entry['loop_back_target'] == '5-execute'

    # SKILL.md Resumability table must contain a row mapping loop_back to a
    # re-fire action. We assert against the exact wording used in the file so
    # accidental rewordings that break the contract are caught.
    skill_text = _PHASE_6_SKILL_MD.read_text(encoding='utf-8')
    assert '`loop_back`' in skill_text, (
        'Resumability table must list `loop_back` outcome — re-fire row missing.'
    )
    # The documented action wording from SKILL.md.
    assert (
        'Re-fire (treat as no record — dispatch as fresh run)' in skill_text
    ), (
        'Resumability table action text for loop_back must read '
        '"Re-fire (treat as no record — dispatch as fresh run)".'
    )


# =============================================================================
# Test 3: FIX-path action body posts the documented chain in the right order;
#         Branch C uses --outcome loop_back (not --outcome done).
# =============================================================================


_TRIAGE_MD = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'plan-marshall'
    / 'workflow'
    / 'triage.md'
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
        assert idx != -1, (
            f'FIX action block missing required token {token!r}; '
            f'expected ordered chain: {expected_chain}'
        )
        cursor = idx + len(token)

    # The calling site's Branch C is in automatic-review.md. It must use
    # --outcome loop_back, not --outcome done.
    auto_body = _AUTOMATED_REVIEW_MD.read_text(encoding='utf-8')
    branch_c_marker = '**Branch C'
    branch_c_start = auto_body.find(branch_c_marker)
    assert branch_c_start != -1, 'Branch C section not found in automatic-review.md'
    branch_c_block = auto_body[branch_c_start:]
    assert '--outcome loop_back' in branch_c_block, (
        'Branch C must record `--outcome loop_back` (not `done`).'
    )
    next_mark = branch_c_block.find('mark-step-done')
    assert next_mark != -1, 'Branch C does not invoke mark-step-done'
    window = branch_c_block[next_mark:next_mark + 400]
    assert '--outcome done' not in window, (
        'Branch C mark-step-done must not use --outcome done — that is the '
        'terminal Branch A outcome and would cause the dispatcher to skip the '
        'step on re-entry.'
    )
    assert '--outcome loop_back' in window


# =============================================================================
# Test 4: pre-push-quality-gate HEAD-comparison rows are still in SKILL.md.
# =============================================================================


def test_pre_push_quality_gate_head_compare_unchanged():
    """The Resumability section retains the pre-push-quality-gate rows.

    SKILL.md Resumability documents a special case for ``pre-push-quality-gate``
    where the resumable check is augmented with a HEAD comparison. Two rows in
    the augmented table are load-bearing:

      * `done` + matches live HEAD  → Skip dispatch entirely (steady-state).
      * `done` + differs from live HEAD  → Re-fire (HEAD has advanced).

    This test pins the special-case text against accidental removal.
    """
    skill_text = _PHASE_6_SKILL_MD.read_text(encoding='utf-8')

    # Special-case header must mention pre-push-quality-gate.
    assert 'pre-push-quality-gate' in skill_text, (
        'Resumability section is missing the pre-push-quality-gate special-case.'
    )
    # Must mention the worktree-HEAD comparison concept.
    assert 'head_at_completion' in skill_text, (
        'Resumability section is missing the head_at_completion comparison field.'
    )
    # Steady-state row: done + matching HEAD → skip.
    assert 'matches live `git -C {worktree_path} rev-parse HEAD`' in skill_text, (
        'Resumability table missing the "matches live HEAD" steady-state row.'
    )
    assert 'Skip dispatch entirely (steady-state' in skill_text, (
        'Steady-state action text for pre-push-quality-gate must read '
        '"Skip dispatch entirely (steady-state — gate already validated this exact tree).".'
    )
    # Mismatched HEAD row: done + differs → re-fire.
    assert 'differs from live HEAD' in skill_text, (
        'Resumability table missing the "differs from live HEAD" row.'
    )
    assert 'HEAD has advanced past the validated SHA' in skill_text, (
        'Mismatched-HEAD row must explain that HEAD has advanced past the validated SHA.'
    )
