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
    assert '`loop_back`' in skill_text, 'Resumability table must list `loop_back` outcome — re-fire row missing.'
    # The documented action wording from SKILL.md.
    assert 'Re-fire (treat as no record — dispatch as fresh run)' in skill_text, (
        'Resumability table action text for loop_back must read "Re-fire (treat as no record — dispatch as fresh run)".'
    )


def test_pre_push_quality_gate_head_compare_unchanged():
    """The Resumability section retains the pre-push-quality-gate rows.

    SKILL.md Resumability documents a special case for ``pre-push-quality-gate``
    where the resumable check is augmented with a HEAD comparison. Two rows in
    the augmented table are load-bearing:

      * `done` + matches live HEAD  → Skip dispatch entirely (steady-state).
      * `done` + differs from live HEAD  → consult the verdict-currency classifier,
        which Step 3's table owns.

    The differing-SHA row is deliberately NOT pinned to an unconditional re-fire.
    It once read that way, and § Resumability was then a second, competing
    statement of a decision Step 3 had already narrowed: a step declaring a
    ``verdict_inputs`` surface the tree difference does not touch resolves
    ``preserved`` and SKIPs. Pinning the superseded wording here is what would
    hold that contradiction in place, so this test pins the DEFERRAL instead.

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
    assert 'differs from live HEAD' in skill_text, 'Resumability table missing the "differs from live HEAD" row.'
    assert 'Consult the verdict-currency classifier' in skill_text, (
        'Mismatched-HEAD row must DEFER to the verdict-currency classifier rather than '
        'prescribing an action of its own — Step 3 owns that decision, and a second '
        'statement of it here is what drifted last time.'
    )
    assert 'NOT an unconditional re-fire' in skill_text, (
        'The mismatched-HEAD row must say explicitly that the action is not an '
        'unconditional re-fire; without that, a reader takes the old reading from the '
        'row heading alone.'
    )

    # Membership is DERIVED, not listed: the hand-maintained literal must be
    # gone from SKILL.md and the fact must be declared on the step's own doc.
    assert _RETIRED_LITERAL not in skill_text, (
        f'SKILL.md still carries the retired {_RETIRED_LITERAL} literal. Membership '
        'is now the derived head_dependent frontmatter fact — a surviving literal is '
        'a second source of truth that can drift from the declarations, which is the '
        'exact defect this plan removed.'
    )
    assert 'head_dependent' in skill_text, (
        'SKILL.md must name the derived head_dependent fact as the membership source.'
    )


def test_verifier_non_close_states_route_to_the_loop_back_branch():
    """Every documented non-close state lands on loop_back, not done or failed.

    Both populations are derived from the section's own state-to-outcome table
    rather than pinned as a sentence, so rewording the routing prose does not
    break the test while changing a state's recorded outcome does. The routing
    assertion below runs over EVERY parsed row — a state whose table carries
    two AGREEING rows is asserted on both, so a pair that both record `done`
    or `failed` fails on its own row rather than being silently discarded by
    a dict collapse that keeps only the last row per state. A pair recording
    DIFFERING outcomes is caught earlier, by the conflicting-outcomes guard
    below, which reports the contradiction once rather than as a routing
    failure on one arbitrary row.
    """
    doc = _PRE_SUBMISSION_SELF_REVIEW_MD.read_text(encoding='utf-8')
    section = _section_after(doc, _VERIFIER_STEP_HEADING)

    assert section.strip(), (
        f'{_VERIFIER_STEP_HEADING!r} is absent from the self-review workflow, so '
        f'the verifier that takes the close decision is undocumented and every '
        f'assertion below would sweep nothing.'
    )

    rows = _non_close_state_outcome_rows(section)

    assert rows, (
        'The verifier section carries no state-to-outcome table row of the form '
        '`| `{state}` | ... | `{outcome}` |`, so this sweep would cover nothing.'
    )

    states = {state for state, _ in rows}
    missing = [state for state in _NON_CLOSE_STATES if state not in states]
    assert not missing, (
        f'The verifier section table no longer names these non-close state(s): '
        f'{missing}. A state that loses its row loses its documented routing with '
        f'it, and nothing then says where a round in that state lands.'
    )

    outcomes_by_state: dict[str, set[str]] = {}
    for state, outcome in rows:
        outcomes_by_state.setdefault(state, set()).add(outcome)

    conflicting = {state: sorted(outs) for state, outs in outcomes_by_state.items() if len(outs) > 1}
    assert not conflicting, (
        f'These state(s) carry rows with CONFLICTING recorded outcomes: {conflicting}. '
        f'A contradictory table is a documentation defect in its own right, reported '
        f'here rather than as a routing failure on one arbitrary row.'
    )

    for state, outcome in rows:
        assert outcome == 'loop_back', (
            f'State `{state}` records `{outcome}` in the verifier section table, not '
            f'`loop_back`. A round the verifier did not close must not record `done` '
            f'(closing a review a second party declined to close) or `failed` '
            f'(grading a working independence check as a broken step).'
        )
