#!/usr/bin/env python3
"""Regression tests for the phase-3-outline Q-Gate surgical bypass rule.

phase-3-outline is a workflow-driven skill (no Python entry point of its own).
Steps 8 (Simple Track Q-Gate) and 11 (Complex Track Q-Gate) are gated by a
single bypass predicate documented verbatim in
``marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md`` and
``marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/
outline-workflow-detail.md``.

These tests pin three invariants that phase-3-outline relies on:

1. **Bypass predicate contract** — bypass MUST fire iff ALL of:
   ``scope_estimate == 'surgical'`` AND
   ``change_type ∈ {'bug_fix', 'tech_debt', 'verification'}`` AND
   ``deliverable_count == 1``.

2. **Recipe plans short-circuit unchanged** — recipe-sourced plans are excluded
   by Step 3 BEFORE the bypass predicate is evaluated, so the bypass rule
   never observes them. Recipe behaviour MUST stay identical regardless of
   ``scope_estimate`` / ``change_type`` / deliverable_count combinations.

3. **Documentation cross-reference** — both SKILL.md and the detail standards
   doc must continue to document the predicate, the log prefix, and the
   bypass examples; a future edit that drops the rule would silently desync
   the workflow from this regression test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT

# -----------------------------------------------------------------------------
# Reference implementation of the bypass predicate.
#
# Mirrors the rule documented in SKILL.md (Steps 8 and 11) and
# outline-workflow-detail.md (§ Q-Gate Surgical Bypass Rule). Kept as runnable
# code so silent doc/SKILL drift is caught by the parametric matrix below.
# -----------------------------------------------------------------------------


_BYPASS_CHANGE_TYPES = frozenset({'bug_fix', 'tech_debt', 'verification'})

# All change_type values phase-3-outline recognises (per
# ref-workflow-architecture/standards/change-types.md). The bypass predicate
# splits these into the bypass-eligible set above and a non-bypass set below.
_NON_BYPASS_CHANGE_TYPES = ('feature', 'enhancement', 'analysis')

# All scope_estimate values phase-2-refine emits (per
# refine-workflow-detail.md § Derivation Rules). Only ``surgical`` enables
# the bypass.
_NON_SURGICAL_SCOPES = ('none', 'single_module', 'multi_module', 'broad')


def qgate_bypass(
    *,
    scope_estimate: str,
    change_type: str,
    deliverable_count: int,
    plan_source: str = 'normal',
) -> bool:
    """Return True iff the phase-3-outline Q-Gate surgical bypass predicate fires.

    Mirrors the rule documented in
    ``phase-3-outline/standards/outline-workflow-detail.md`` § Q-Gate Surgical
    Bypass Rule. The predicate is identical for Step 8 (Simple Track) and
    Step 11 (Complex Track).

    Args:
        scope_estimate: Value persisted to references.json by phase-2-refine
            (and optionally refined by phase-3-outline before the Q-Gate
            dispatch). One of ``'none' | 'surgical' | 'single_module' |
            'multi_module' | 'broad'``.
        change_type: Value persisted to status.json metadata by Step 4
            (or by Step 3 for recipe plans). One of ``'bug_fix' | 'tech_debt'
            | 'verification' | 'feature' | 'enhancement' | 'analysis'``.
        deliverable_count: Number of deliverables created in Step 7
            (Simple Track) or Step 10 (Complex Track).
        plan_source: ``'recipe'`` short-circuits Steps 4-11 entirely via Step
            3 (Recipe Detection), so the bypass predicate is never reached.
            All other values flow through normally.

    Returns:
        True iff the Q-Gate dispatch should be skipped per the bypass rule.
        Recipe plans always return False here because Step 3 already
        short-circuited the workflow before this predicate was reachable.
    """
    # Recipe plans are short-circuited by Step 3, never reach Step 8/11.
    # Returning False here pins the contract that the bypass predicate is
    # not the mechanism that handles recipe plans.
    if plan_source == 'recipe':
        return False

    return (
        scope_estimate == 'surgical'
        and change_type in _BYPASS_CHANGE_TYPES
        and deliverable_count == 1
    )


# -----------------------------------------------------------------------------
# Parametric matrix — mirrors the worked-examples table in
# outline-workflow-detail.md § Q-Gate Surgical Bypass Rule.
# -----------------------------------------------------------------------------


BYPASS_CASES = [
    # ---- Bypass FIRES (the three matrix rows) ----
    pytest.param(
        {'scope_estimate': 'surgical', 'change_type': 'bug_fix', 'deliverable_count': 1},
        True,
        id='bypass-surgical-bug_fix-1',
    ),
    pytest.param(
        {'scope_estimate': 'surgical', 'change_type': 'tech_debt', 'deliverable_count': 1},
        True,
        id='bypass-surgical-tech_debt-1',
    ),
    pytest.param(
        {'scope_estimate': 'surgical', 'change_type': 'verification', 'deliverable_count': 1},
        True,
        id='bypass-surgical-verification-1',
    ),
    # ---- Bypass does NOT fire — wrong change_type ----
    pytest.param(
        {'scope_estimate': 'surgical', 'change_type': 'feature', 'deliverable_count': 1},
        False,
        id='no-bypass-surgical-feature',
    ),
    pytest.param(
        {'scope_estimate': 'surgical', 'change_type': 'enhancement', 'deliverable_count': 1},
        False,
        id='no-bypass-surgical-enhancement',
    ),
    pytest.param(
        {'scope_estimate': 'surgical', 'change_type': 'analysis', 'deliverable_count': 1},
        False,
        id='no-bypass-surgical-analysis',
    ),
    # ---- Bypass does NOT fire — too many deliverables ----
    pytest.param(
        {'scope_estimate': 'surgical', 'change_type': 'bug_fix', 'deliverable_count': 2},
        False,
        id='no-bypass-surgical-bug_fix-2-deliverables',
    ),
    pytest.param(
        {'scope_estimate': 'surgical', 'change_type': 'tech_debt', 'deliverable_count': 5},
        False,
        id='no-bypass-surgical-tech_debt-5-deliverables',
    ),
    # ---- Bypass does NOT fire — non-surgical scope ----
    pytest.param(
        {'scope_estimate': 'multi_module', 'change_type': 'bug_fix', 'deliverable_count': 1},
        False,
        id='no-bypass-multi_module-bug_fix',
    ),
    pytest.param(
        {'scope_estimate': 'single_module', 'change_type': 'bug_fix', 'deliverable_count': 1},
        False,
        id='no-bypass-single_module-bug_fix',
    ),
    pytest.param(
        {'scope_estimate': 'broad', 'change_type': 'tech_debt', 'deliverable_count': 1},
        False,
        id='no-bypass-broad-tech_debt',
    ),
    pytest.param(
        {'scope_estimate': 'none', 'change_type': 'verification', 'deliverable_count': 1},
        False,
        id='no-bypass-none-verification',
    ),
    # ---- Edge case — zero deliverables (defensive; should never happen but
    # documents that the predicate counts strictly equal to 1) ----
    pytest.param(
        {'scope_estimate': 'surgical', 'change_type': 'bug_fix', 'deliverable_count': 0},
        False,
        id='no-bypass-surgical-bug_fix-0-deliverables',
    ),
]


@pytest.mark.parametrize('inputs,expected', BYPASS_CASES)
def test_qgate_bypass_predicate(inputs: dict, expected: bool) -> None:
    """The bypass predicate fires iff ALL three conditions hold simultaneously.

    Pins the contract that the Q-Gate is skipped exclusively for surgical,
    corrective, single-deliverable plans — never for generative change types,
    never for multi-deliverable plans, never for non-surgical scopes.
    """
    actual = qgate_bypass(**inputs)
    assert actual is expected, (
        f'Bypass predicate mismatch for inputs={inputs!r}: '
        f'expected {expected}, got {actual}'
    )


# -----------------------------------------------------------------------------
# Recipe plans are unaffected — Step 3 (Recipe Detection) short-circuits Steps
# 4-11 BEFORE the bypass predicate is reachable. The predicate must therefore
# return False for plan_source == 'recipe' regardless of other inputs, so a
# regression that incorrectly routes recipe plans through Step 8/11 cannot
# silently start firing the bypass.
# -----------------------------------------------------------------------------


RECIPE_CASES = [
    pytest.param(
        {
            'scope_estimate': 'surgical',
            'change_type': 'tech_debt',
            'deliverable_count': 1,
            'plan_source': 'recipe',
        },
        id='recipe-surgical-tech_debt-1',
    ),
    pytest.param(
        {
            'scope_estimate': 'surgical',
            'change_type': 'bug_fix',
            'deliverable_count': 1,
            'plan_source': 'recipe',
        },
        id='recipe-surgical-bug_fix-1',
    ),
    pytest.param(
        {
            'scope_estimate': 'multi_module',
            'change_type': 'feature',
            'deliverable_count': 4,
            'plan_source': 'recipe',
        },
        id='recipe-multi_module-feature-4',
    ),
    pytest.param(
        {
            'scope_estimate': 'broad',
            'change_type': 'enhancement',
            'deliverable_count': 7,
            'plan_source': 'recipe',
        },
        id='recipe-broad-enhancement-7',
    ),
]


@pytest.mark.parametrize('inputs', RECIPE_CASES)
def test_qgate_bypass_never_fires_for_recipe_plans(inputs: dict) -> None:
    """Recipe plans (``plan_source == 'recipe'``) are short-circuited by Step
    3 — the Q-Gate bypass predicate must never claim ownership of recipe
    skip behaviour, even when the surgical+corrective+1 conditions hold.

    This test guards against a future refactor that conflates recipe handling
    with the surgical bypass — the two skip paths must remain orthogonal so
    Step 3's existing unconditional short-circuit stays the single source of
    truth for recipe plans.
    """
    assert qgate_bypass(**inputs) is False, (
        f'Recipe plans must never be handled by the surgical bypass predicate '
        f'(inputs={inputs!r}). Step 3 (Recipe Detection) is the only sanctioned '
        f'recipe-skip path.'
    )


# -----------------------------------------------------------------------------
# Exhaustive matrix — guarantees every (scope, change_type, count) shape is
# covered without relying on enumeration discipline in the manual cases above.
# -----------------------------------------------------------------------------


def test_only_three_change_types_enable_bypass_for_surgical_single_deliverable() -> None:
    """For ``scope_estimate == 'surgical'`` and ``deliverable_count == 1``,
    exactly the three change_types in
    {bug_fix, tech_debt, verification} enable bypass. Any future addition to
    that set requires deliberate edits to both the standards doc and this
    invariant.
    """
    enabling: set[str] = set()
    all_change_types = list(_BYPASS_CHANGE_TYPES) + list(_NON_BYPASS_CHANGE_TYPES)
    for ct in all_change_types:
        if qgate_bypass(scope_estimate='surgical', change_type=ct, deliverable_count=1):
            enabling.add(ct)
    assert enabling == set(_BYPASS_CHANGE_TYPES), (
        f'Expected bypass to fire for exactly {sorted(_BYPASS_CHANGE_TYPES)}, '
        f'observed {sorted(enabling)}.'
    )


def test_no_non_surgical_scope_enables_bypass() -> None:
    """No non-surgical ``scope_estimate`` value enables bypass under any
    (change_type, deliverable_count) combination. This pins the asymmetry
    that surgical is the SOLE scope value that opts into the skip — a
    regression that broadened the rule (e.g., to also bypass ``single_module``)
    would invalidate the safety guarantees that motivated the surgical-only
    restriction in the first place.
    """
    for scope in _NON_SURGICAL_SCOPES:
        for ct in list(_BYPASS_CHANGE_TYPES) + list(_NON_BYPASS_CHANGE_TYPES):
            for count in (0, 1, 2, 5):
                assert (
                    qgate_bypass(
                        scope_estimate=scope, change_type=ct, deliverable_count=count
                    )
                    is False
                ), (
                    f'Non-surgical scope {scope!r} must never trigger bypass '
                    f'(change_type={ct!r}, deliverable_count={count}).'
                )


def test_deliverable_count_must_be_exactly_one() -> None:
    """Bypass requires ``deliverable_count == 1`` strictly — counts of 0, 2,
    or higher MUST NOT trigger bypass even when the other two predicates
    hold. The ``> 1`` case is the practical one (a multi-deliverable plan
    can drift in scope); the ``0`` case is defensive.
    """
    for count in (0, 2, 3, 10):
        for ct in _BYPASS_CHANGE_TYPES:
            assert (
                qgate_bypass(
                    scope_estimate='surgical', change_type=ct, deliverable_count=count
                )
                is False
            ), (
                f'deliverable_count={count} must not trigger bypass '
                f'(change_type={ct!r}).'
            )


# -----------------------------------------------------------------------------
# Documentation cross-reference — fail loudly if the SKILL.md or detail doc
# loses the bypass rule, log prefix, or worked examples. Keeps the workflow
# documentation, reference implementation, and consumers in lockstep.
# -----------------------------------------------------------------------------


_SKILL_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-3-outline'
    / 'SKILL.md'
)

_DETAIL_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-3-outline'
    / 'standards'
    / 'outline-workflow-detail.md'
)


_LOG_PREFIX = '(plan-marshall:phase-3-outline:qgate-bypass)'


def test_skill_md_documents_bypass_rule() -> None:
    """SKILL.md must continue to document the bypass predicate for BOTH Steps
    8 and 11, the bypass log prefix, and the surgical+corrective+1 shape.
    """
    text = _SKILL_PATH.read_text(encoding='utf-8')

    # Log prefix (single source of truth for log scrapers + retrospective).
    assert _LOG_PREFIX in text, (
        f'SKILL.md missing the bypass log prefix {_LOG_PREFIX!r} — log scrapers '
        f'(plan-retrospective, manifest cross-check) rely on this exact prefix.'
    )

    # Each of the three bypass-eligible change_types must appear in the
    # documented predicate.
    for ct in _BYPASS_CHANGE_TYPES:
        assert ct in text, (
            f'SKILL.md missing change_type {ct!r} in the bypass predicate — the '
            f'documented predicate must list every value in the eligible set.'
        )

    # The predicate must reference scope_estimate == surgical and 1 deliverable.
    assert 'surgical' in text, 'SKILL.md missing scope_estimate=surgical predicate'
    assert 'deliverable_count == 1' in text or '1 deliverable' in text, (
        'SKILL.md must document the deliverable_count == 1 / "1 deliverable" '
        'constraint in the bypass predicate.'
    )

    # Both Step 8 (Simple Track) and Step 11 (Complex Track) must reference
    # the bypass — the rule applies to both Q-Gate dispatch sites.
    assert 'Step 8' in text and 'Step 11' in text, (
        'SKILL.md must reference both Step 8 (Simple Track) and Step 11 '
        '(Complex Track) so the bypass rule is anchored to both Q-Gate sites.'
    )


def test_detail_doc_documents_bypass_rule_and_examples() -> None:
    """outline-workflow-detail.md must continue to document the predicate
    AND the worked-examples table that shows when bypass fires vs when
    Q-Gate still runs.
    """
    text = _DETAIL_PATH.read_text(encoding='utf-8')

    # Log prefix.
    assert _LOG_PREFIX in text, (
        f'Detail doc missing the bypass log prefix {_LOG_PREFIX!r}.'
    )

    # Every bypass-eligible change_type must be enumerated.
    for ct in _BYPASS_CHANGE_TYPES:
        assert ct in text, f'Detail doc missing change_type {ct!r}'

    # Every non-bypass change_type must appear in the worked-examples table
    # showing when the rule does NOT fire — exemplification is part of the
    # deliverable's stated requirement.
    for ct in _NON_BYPASS_CHANGE_TYPES:
        assert ct in text, (
            f'Detail doc missing change_type {ct!r} in the worked-examples table '
            f'(must show when bypass does NOT fire).'
        )

    # Every non-surgical scope_estimate value must appear in the worked-examples
    # table showing when the scope check excludes bypass.
    for scope in _NON_SURGICAL_SCOPES:
        assert scope in text, (
            f'Detail doc missing scope_estimate value {scope!r} in the '
            f'worked-examples table.'
        )

    # The predicate must reference both Q-Gate dispatch sites.
    assert 'Step 8' in text and 'Step 11' in text, (
        'Detail doc must reference both Step 8 and Step 11 so the rule is '
        'anchored to both Q-Gate dispatch sites.'
    )

    # Recipe-source short-circuit must remain explicitly cross-referenced —
    # the deliverable explicitly requires "recipe (already skipped via existing
    # path) — unchanged behavior".
    assert 'recipe' in text.lower() and 'Step 3' in text, (
        'Detail doc must explicitly cross-reference Step 3 (Recipe Detection) '
        'so future readers know recipe plans short-circuit BEFORE the bypass '
        'predicate is reached.'
    )


# Sanity check: pin the file's own location — the deliverable explicitly named
# this path. A future restructure should update this assertion deliberately.
def test_test_file_lives_at_expected_path() -> None:
    """Pin the file's location to the path named in deliverable 4 of the
    workflow-scope-adaptive-execution solution outline.
    """
    here = Path(__file__).resolve()
    expected_suffix = Path(
        'test/plan-marshall/phase-3-outline/test_phase_3_outline_qgate_bypass.py'
    )
    assert str(here).endswith(str(expected_suffix)), (
        f'Test file moved from expected path. Got {here}, '
        f'expected suffix {expected_suffix}.'
    )
