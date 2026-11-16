#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract tests for the conflicting-baseline-drift recovery.

Plan ``live-blockers/PLAN-LB-154``.

The recovery for ``error: baseline_drift`` with ``conflict_count > 0`` re-cycled
phase-2-refine and then re-entered execute. Refine never moves the branch — its
own § Conflict Handling states that the fetch/compare path is read-only — so the
branch stayed on the old base, execute re-ran its Step 3 gate against the same
upstream commits, and the identical drift came back. The loop was bounded at
three returns but never converged on its own, and the branch was rebased by hand.

These tests pin the two repairs in the prose the orchestrator executes:

* D1 — a reconcile step between refine's return and the execute re-entry that
  brings the branch onto the new base through the ``git-workflow`` verb and
  remaps the change ledger for the commits that rebase rewrote.
* D2 — a drift return whose probe equals the previous return's stops at once
  with the named reason ``drift_unchanged`` instead of spending the rest of the
  three-return cap.
* D3 — the deferral statements in the refine and sync-with-main documents name
  the new step for the conflicting case and keep phase-5 self-absorption for the
  non-conflicting one.

Every assertion reads the documents the orchestrator loads, not a copy of them,
so a later edit that moves the step or drops the stop fails here.
"""

from __future__ import annotations

import pytest

from conftest import MARKETPLACE_ROOT

PLAN_MARSHALL_SKILLS = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'

#: The orchestrator-side recovery document that carries the step-by-step branch.
RECOVERY_DOC = PLAN_MARSHALL_SKILLS / 'plan-marshall' / 'standards' / 'execution-recovery.md'

#: Refine's baseline-reconciliation detail; § Conflict Handling states who
#: performs the actual git reconcile for each drift class.
REFINE_DOC = PLAN_MARSHALL_SKILLS / 'phase-2-refine' / 'standards' / 'refine-workflow-detail.md'

#: Phase-5's fast-path gate; the drift-abort contract names the recovery branch
#: the orchestrator runs next.
SYNC_DOC = PLAN_MARSHALL_SKILLS / 'phase-5-execute' / 'standards' / 'sync-with-main.md'

#: The recovery section heading the orchestrator loads on a drift return.
RECOVERY_HEADING = 'Baseline drift recovery (non-zero overlap)'

#: Refine's conflict-handling heading, the deferral statement's home.
REFINE_HEADING = '### Conflict Handling'


def _section(text: str, heading: str) -> str:
    """Return the body of ``heading`` up to the next heading of the same level.

    The slice is deliberately bounded: an assertion that searched the whole
    document would pass on a sentence that lives in an unrelated section, which
    is exactly the "the contract says X somewhere" failure this file avoids.
    """
    marker = f'## {heading}' if not heading.startswith('#') else heading
    start = text.find(marker)
    assert start != -1, f'heading {marker!r} is absent; the contract moved or was renamed'
    level = len(marker) - len(marker.lstrip('#'))
    body_start = text.index('\n', start) + 1
    next_heading = text.find('\n' + '#' * level + ' ', body_start)
    return text[body_start:] if next_heading == -1 else text[body_start:next_heading]


@pytest.fixture(scope='module')
def recovery_section() -> str:
    section = _section(RECOVERY_DOC.read_text(encoding='utf-8'), RECOVERY_HEADING)
    # Non-vacuity: the bounded slice must cover the procedure, not a stray line.
    assert len(section) > 1500, 'the recovery section is too short to carry its procedure'
    return section


@pytest.fixture(scope='module')
def refine_section() -> str:
    text: str = REFINE_DOC.read_text(encoding='utf-8')
    start = text.find(REFINE_HEADING)
    assert start != -1, 'refine-workflow-detail.md has no § Conflict Handling'
    body_start = text.index('\n', start) + 1
    end = text.find('\n### ', body_start)
    section: str = text[body_start : end if end != -1 else len(text)]
    assert len(section) > 200, 'the conflict-handling paragraph is missing its body'
    return section


def test_reconcile_step_runs_between_refine_return_and_execute_reentry(recovery_section: str) -> None:
    """D1: the branch is brought onto the new base before execute is re-entered."""
    body = recovery_section

    assert 'On refine return' in body, "the procedure no longer marks refine's return as a step"
    assert 'worktree-rebase-to' in body, (
        'the recovery names no git-workflow verb that brings the branch onto the new base'
    )
    assert 'Re-enter phase-5-execute' in body, 'the procedure no longer re-enters execute'

    refine_return = body.index('On refine return')
    reconcile = body.index('worktree-rebase-to')
    reentry = body.index('Re-enter phase-5-execute')
    assert refine_return < reconcile < reentry, (
        "the reconcile step must sit between refine's return and the execute re-entry; "
        f'found refine_return={refine_return}, reconcile={reconcile}, reentry={reentry}'
    )

    assert 'git -C {worktree_path} fetch origin {base_branch}' in body, (
        'the reconcile step must refresh the base ref it reconciles against'
    )
    assert '--base {base_branch}' in body, (
        'worktree-rebase-to takes the bare branch name; it fetches origin/{base} itself'
    )
    assert '--base origin/' not in body, (
        'passing origin/{base} to the verb makes its own fetch target a non-existent remote ref'
    )
    assert 'git rebase origin/' not in body, (
        'the base reconcile must go through worktree-rebase-to, never a raw rebase of the base'
    )


def test_every_reconcile_outcome_is_named_with_its_stop(recovery_section: str) -> None:
    """D1: conflict and error returns stop the recovery instead of re-entering execute."""
    body = recovery_section

    assert 'status: conflict' in body, 'the conflict return of worktree-rebase-to is not handled'
    assert 'git rebase --continue' in body, 'a conflict has no continuation path'
    assert 'git rebase --abort' in body, 'a conflict has no abandonment path'
    assert 'drift_reconcile_conflict' in body, (
        'an unresolvable conflict must stop with a named reason, not re-enter execute'
    )
    assert 'force-push-with-lease' in body, (
        'the rewritten branch must be published through the git-workflow branch verb'
    )
    assert 'git push --force' not in body, 'a bare force push is forbidden by the standing constraint'


def test_ledger_remap_is_tied_to_a_rewriting_rebase(recovery_section: str) -> None:
    """D1: the change ledger is remapped for exactly the commits the rebase rewrote."""
    body = recovery_section

    assert 'manage-change-ledger:manage-change-ledger remap' in body, (
        'the reconcile step rewrites commit SHAs without remapping the change ledger'
    )
    assert '--old-head {pre_sha}' in body, 'the remap is not narrowed to the pre-rebase head'
    assert '--emit-map' in body and '--dry-run' in body, 'the remap must emit the old-to-new map before consuming it'

    assert 'action: rebased' in body and 'action: noop' in body, (
        'the remap must be gated on the rebase action, not on the detected state'
    )
    assert 'replayed nothing' in body, 'the procedure must state that an action: noop rebase skips the remap'
    assert body.index('worktree-rebase-to') < body.index('manage-change-ledger:manage-change-ledger remap'), (
        'the remap must follow the rebase that produced the rewritten SHAs'
    )


def test_unchanged_probe_stops_on_the_first_repeat(recovery_section: str) -> None:
    """D2: an identical drift probe stops the loop instead of spending the 3-return cap."""
    body = recovery_section

    assert 'drift_unchanged' in body, 'the identical-probe stop has no named reason'
    assert 'divergent_commits' in body, 'the probe comparison does not read the divergent commits'
    assert 'conflict_count' in body, 'the probe comparison does not read the conflict set'

    assert 'status.metadata' in body, (
        'the counter and the probe must be persisted where a resumed orchestrator reads them'
    )
    assert 'baseline_drift_probe' in body, 'the persisted probe signature is not named'
    assert 'baseline_drift_count' in body, 'the persisted loop counter is not named'

    assert body.index('drift_unchanged') < body.index('drift_loop_cap_exceeded'), (
        'the unchanged-probe stop must be stated before the cap, since it fires on the first repeat'
    )
    assert body.index('Unchanged-probe stop') < body.index('Recovery procedure'), (
        'the probe is compared BEFORE the procedure runs; otherwise the stop leaves the phase '
        'reset to 2-refine with no refine dispatched'
    )
    assert 'reset' in body, 'the procedure no longer states when the counter and probe are cleared'


def test_refine_conflict_handling_names_the_reconcile_step(refine_section: str) -> None:
    """D3: the conflicting drift is reconciled by the new step, not deferred to phase-6."""
    section = refine_section

    assert 'execution-recovery.md' in section, (
        "refine's Conflict Handling does not name the recovery step that reconciles the branch"
    )
    assert 'self-absorb' in section, 'the non-conflicting case must still self-absorb in phase 5'
    assert 'happens later, in' not in section, (
        'the deferral phrasing that made phase-6 branch-cleanup the sole reconcile actor must be gone'
    )


def test_sync_with_main_names_the_reconcile_step() -> None:
    """D3: the drift-abort contract names the reconcile step after refine returns."""
    text: str = SYNC_DOC.read_text(encoding='utf-8')

    assert 'execution-recovery.md' in text, (
        'sync-with-main.md names no step that brings the branch onto the new base after refine'
    )
    assert 'self-absorb' in text, 'the non-conflicting case must still self-absorb in phase 5'
    assert 'the iterate-to-confidence loop absorbs the overlap' not in text, (
        "refine can only re-author the plan; the branch reconcile is the recovery step's work"
    )
