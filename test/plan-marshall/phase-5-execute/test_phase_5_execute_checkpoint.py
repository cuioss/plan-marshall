#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for the phase-5-execute deterministic-exit clause.

phase-5-execute is workflow-driven (no Python entry point); the continue-vs-
yield decision is documented in SKILL.md. Under the budget-bounded envelope
model the decision is **pre-computed at plan time** by the bin-packer
(`manage-tasks pack-envelopes`): each task is stamped with an ``envelope_id``,
and at runtime the executor only READS that grouping. The deterministic-exit
clause therefore reduces to a trivial equality check:

  1. Small-plan short-circuit  (tasks_total <= 2 — informational only)
  2. Final-task long-running-verify short-circuit  (informational only)
  3. Envelope-group read  (yield when the next pending task's envelope_id
     differs from the assigned group, or the queue is empty)

These tests pin the SKILL.md narrative so cross-edits cannot silently revert
to the unevaluable runtime sentinel, and they pin a thin behavioural simulator
of the envelope-group read so the contract is provable beyond prose. They also
pin that the checkpoint reads ``envelope_id`` off the ``manage-tasks next``
result and that the orchestrator records the yield with
``termination_cause=budget_yield``.
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
# Behavioural simulator of the SKILL.md envelope-group read
# ---------------------------------------------------------------------------


def should_yield(
    tasks_total: int,
    task_index: int,
    verify_command: str,
    assigned_envelope_id: int,
    next_envelope_id: int | None,
) -> bool:
    """Mirror the SKILL.md deterministic-exit clause (envelope-group read).

    Returns True when the loop should yield (cannot start the next task),
    False when it should continue.

    ``next_envelope_id`` is the ``envelope_id`` of the next pending task as
    surfaced on the ``manage-tasks next`` result dict, or ``None`` when the
    queue is empty.
    """
    # 1. Small-plan short-circuit (informational — a small plan packs to one
    #    envelope, so the envelope-group read would never yield mid-plan anyway).
    if tasks_total <= 2:
        return False
    # 2. Final-task long-running-verify short-circuit (informational — the final
    #    task is already inside the last envelope).
    final = task_index + 1 == tasks_total
    cmd = (verify_command or '').strip().split()[0] if verify_command else ''
    if final and cmd in LONG_RUNNING:
        return False
    # 3. Envelope-group read: yield when the next pending task belongs to a
    #    different envelope, or when the queue is empty.
    if next_envelope_id is None:
        return True
    return next_envelope_id != assigned_envelope_id


# ---------------------------------------------------------------------------
# Pinning tests for SKILL.md narrative
# ---------------------------------------------------------------------------


def _skill_text() -> str:
    return str(SKILL_PATH.read_text())


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


def test_skill_md_documents_envelope_group_read():
    """The runtime sentinel was replaced by a plan-time-packed envelope-group read."""
    txt = _skill_text()
    assert 'Envelope-group read' in txt
    # The decision is a pure equality check on envelope_id, surfaced via next.
    assert 'envelope_id' in txt
    assert 'pack-envelopes' in txt
    # The read peeks the next pending task and compares its envelope_id.
    assert 'manage-tasks next' in txt


def test_skill_md_documents_budget_yield_signal():
    """The one legitimate yield is budget_yield, with both observable signals."""
    txt = _skill_text()
    assert 'budget_yield' in txt
    # The yield carries a wrapped terminal TOON with tasks_remaining > 0.
    assert 'budget_yield: true' in txt
    assert 'tasks_remaining' in txt


def test_skill_md_no_longer_documents_unevaluable_runtime_sentinel():
    """The replaced budget-vs-N runtime comparand must be gone.

    The old clause compared a runtime ``remaining_budget`` against ``N`` — but a
    subagent cannot measure its own mid-turn context, so the comparand was
    unevaluable. The envelope-group read replaces it entirely.
    """
    txt = _skill_text()
    assert 'Budget-vs-N comparison' not in txt
    assert 'remaining_budget > N' not in txt


# ---------------------------------------------------------------------------
# Behavioural test cases for the envelope-group read
# ---------------------------------------------------------------------------


def test_next_task_same_envelope_continues():
    """The next pending task in the SAME envelope -> continue (no yield)."""
    assert not should_yield(
        tasks_total=6,
        task_index=1,
        verify_command='lint --quick',
        assigned_envelope_id=1,
        next_envelope_id=1,
    )


def test_next_task_different_envelope_yields():
    """The next pending task in a DIFFERENT envelope -> yield to the orchestrator."""
    assert should_yield(
        tasks_total=6,
        task_index=2,
        verify_command='lint --quick',
        assigned_envelope_id=1,
        next_envelope_id=2,
    )


def test_empty_queue_yields():
    """No next pending task (queue empty) -> yield (the group ran to completion)."""
    assert should_yield(
        tasks_total=6,
        task_index=5,
        verify_command='lint --quick',
        assigned_envelope_id=2,
        next_envelope_id=None,
    )


def test_envelope_read_ignores_runtime_budget():
    """The decision is independent of any runtime budget — only envelope_id matters.

    Two identical scenarios that would have diverged under the old budget-vs-N
    clause now converge: when the next task is in the same envelope the loop
    continues regardless of how much work has been done.
    """
    assert not should_yield(
        tasks_total=10,
        task_index=8,  # deep into the run — old clause would likely yield
        verify_command='lint',
        assigned_envelope_id=3,
        next_envelope_id=3,
    )


@pytest.mark.parametrize('cmd', sorted(LONG_RUNNING))
def test_final_task_long_running_verify_suppresses_yield(cmd):
    """Final task + long-running verify -> continue and finish in-dispatch."""
    assert not should_yield(
        tasks_total=5,
        task_index=4,
        verify_command=f'{cmd} plan-marshall',
        assigned_envelope_id=2,
        next_envelope_id=None,  # queue empty, but final-task short-circuit wins
    )


def test_small_plan_short_circuit_preserved():
    """Existing small-plan short-circuit (<=2 tasks) still wins over all."""
    # A different next envelope would yield, but small-plan suppresses it.
    assert not should_yield(
        tasks_total=2,
        task_index=0,
        verify_command='lint',
        assigned_envelope_id=1,
        next_envelope_id=2,
    )
    assert not should_yield(
        tasks_total=1,
        task_index=0,
        verify_command='lint',
        assigned_envelope_id=1,
        next_envelope_id=None,
    )
