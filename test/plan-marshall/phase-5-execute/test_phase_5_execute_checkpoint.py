#!/usr/bin/env python3
"""Regression tests for the phase-5-execute deterministic-exit clause.

phase-5-execute is workflow-driven (no Python entry point); the
voluntary-checkpoint sentinel is documented in SKILL.md as a deterministic
clause with two short-circuits ahead of the budget-vs-N comparison:

  1. Small-plan short-circuit  (tasks_total <= 2)
  2. Final-task long-running-verify short-circuit  (new, deliverable 5)
  3. Budget-vs-N comparison    (default branch)

These tests pin the SKILL.md narrative so cross-edits cannot silently
remove the short-circuits. They also pin a thin behavioural simulator of
the dispatcher decision so the contract is provable beyond prose.
"""

from __future__ import annotations

import pytest

from conftest import MARKETPLACE_ROOT

SKILL_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-5-execute'
    / 'SKILL.md'
)

LONG_RUNNING = {'verify', 'coverage', 'quality-gate'}


# ---------------------------------------------------------------------------
# Behavioural simulator of the SKILL.md decision
# ---------------------------------------------------------------------------


def should_yield(
    tasks_total: int,
    task_index: int,
    verify_command: str,
    remaining_budget: int,
    per_task_reserve: int,
) -> bool:
    """Mirror the SKILL.md deterministic-exit clause.

    Returns True when the loop should yield (cannot start the next task),
    False when it should continue.
    """
    # 1. Small-plan short-circuit
    if tasks_total <= 2:
        return False
    # 2. Final-task long-running-verify short-circuit
    final = task_index + 1 == tasks_total
    cmd = (verify_command or '').strip().split()[0] if verify_command else ''
    if final and cmd in LONG_RUNNING:
        return False
    # 3. Budget-vs-N comparison
    return remaining_budget <= per_task_reserve


# ---------------------------------------------------------------------------
# Pinning tests for SKILL.md narrative
# ---------------------------------------------------------------------------


def _skill_text() -> str:
    return SKILL_PATH.read_text()


def test_skill_md_documents_small_plan_short_circuit():
    txt = _skill_text()
    assert 'Small-plan short-circuit' in txt
    assert 'tasks_total <= 2' in txt


def test_skill_md_documents_final_task_short_circuit():
    txt = _skill_text()
    assert 'Final-task long-running-verify short-circuit' in txt
    # The predicate must reference the queue-tail check and the long-running set.
    assert 'task_index + 1 == tasks_total' in txt
    for cmd in ('verify', 'coverage', 'quality-gate'):
        assert cmd in txt


def test_skill_md_documents_budget_vs_n_branch():
    txt = _skill_text()
    assert 'Budget-vs-N comparison' in txt
    assert 'remaining_budget > N' in txt


# ---------------------------------------------------------------------------
# Behavioural test cases (matching the four solution_outline scenarios)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('cmd', sorted(LONG_RUNNING))
def test_final_task_long_running_verify_suppresses_yield(cmd):
    """Case (a): final task + long-running verify -> never yield, regardless of budget."""
    assert not should_yield(
        tasks_total=5,
        task_index=4,
        verify_command=f'{cmd} plan-marshall',
        remaining_budget=1,  # tiny budget — would yield without suppression
        per_task_reserve=50000,
    )


def test_final_task_short_verify_uses_budget_branch():
    """Case (b): final task + short verify -> falls through to budget comparison."""
    # Budget exhausted -> yield
    assert should_yield(
        tasks_total=5,
        task_index=4,
        verify_command='lint --quick',
        remaining_budget=100,
        per_task_reserve=50000,
    )
    # Budget plentiful -> continue
    assert not should_yield(
        tasks_total=5,
        task_index=4,
        verify_command='lint --quick',
        remaining_budget=100000,
        per_task_reserve=50000,
    )


def test_non_final_task_long_running_verify_uses_budget_branch():
    """Case (c): non-final + long-running verify -> still bound by budget."""
    assert should_yield(
        tasks_total=5,
        task_index=2,
        verify_command='verify plan-marshall',
        remaining_budget=100,
        per_task_reserve=50000,
    )


def test_small_plan_short_circuit_preserved():
    """Case (d): existing small-plan short-circuit (<=2 tasks) still wins over all."""
    # Tiny budget would yield, but small-plan suppresses unconditionally.
    assert not should_yield(
        tasks_total=2,
        task_index=0,
        verify_command='lint',
        remaining_budget=1,
        per_task_reserve=50000,
    )
    assert not should_yield(
        tasks_total=1,
        task_index=0,
        verify_command='lint',
        remaining_budget=1,
        per_task_reserve=50000,
    )
