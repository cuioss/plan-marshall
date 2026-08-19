#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``manage status transition`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


import json
import sys as _sys
from argparse import Namespace
from pathlib import Path

import _handshake_commands as _cmds  # noqa: E402
import _invariants as _inv  # noqa: E402

from conftest import get_script_path, load_script_module

# Script path for CLI plumbing / subprocess tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')


_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_cmd_lifecycle')


_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_status_cmd_query')


cmd_archive = _lifecycle.cmd_archive


cmd_create = _lifecycle.cmd_create


cmd_delete_plan = _lifecycle.cmd_delete_plan


cmd_list = _query.cmd_list


cmd_list_orphans = _query.cmd_list_orphans


cmd_set_phase = _query.cmd_set_phase


cmd_transition = _lifecycle.cmd_transition


cmd_update_phase = _query.cmd_update_phase


# =============================================================================
# Regression Tests: cmd_transition(completed='5-execute') no longer seeds
# references.modified_files
# =============================================================================
#
# The worktree-single-source-of-truth plan deleted the modified_files ledger:
# the 5-execute transition used to run ``_collect_modified_files`` and write
# the result to ``references.modified_files``. That producer and its
# write-back are gone — the footprint is now derived on-demand from the live
# worktree diff (manage-references compute-footprint), never persisted. These
# tests pin that the transition is now footprint-free.


def _seed_execute_phase_plan(plan_dir, plan_id: str) -> None:
    """Create a plan with phases 1-4 done, 5-execute in_progress, and a
    references.json carrying base_branch. Returns nothing; mutates the
    fixture directory directly.
    """
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Transition Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    # Advance phases until 5-execute is the current (in_progress) phase.
    for phase in ('1-init', '2-refine', '3-outline', '4-plan'):
        cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))

    refs = {'base_branch': 'main', 'branch': f'feature/{plan_id}'}
    refs_path = plan_dir / 'references.json'
    refs_path.write_text(json.dumps(refs), encoding='utf-8')


# =============================================================================
# Regression Tests: cmd_archive atomically completes the active phase, and
# cmd_transition mirrors the same end-state when the LAST phase finishes.
# =============================================================================


def _seed_finalize_phase_plan(plan_id: str) -> None:
    """Create a plan whose phases 1..5 are done and 6-finalize is in_progress.

    Mirrors the end-of-execute state when phase-6-finalize is about to run
    its final step (archive-plan).
    """
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Atomic Archive Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    for phase in ('1-init', '2-refine', '3-outline', '4-plan', '5-execute'):
        cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='6-finalize'))


# =============================================================================
# Regression Tests: cmd_list discovers moved-in worktree plans (ADR-002)
# =============================================================================
#
# Per ADR-002 a plan's runtime state (its plan directory) MOVES into the
# plan's own worktree at phase-5 entry and back to main at finalize. A plan
# that is mid-flight in phase-5+ therefore no longer lives under the main
# checkout's plans_dir — a main-only walk is BLIND to it. cmd_list must scan
# get_worktree_root()'s child worktrees for moved-in plans and surface them
# with location='worktree'. These tests pin that discovery so a regression to
# the old main-only walk fails loudly.
#
# Worktree-resident plan layout probed by cmd_list:
#   {base_dir}/worktrees/{wt}/.plan/local/plans/{plan_id}/status.json
# Under the plan_context fixture, base_dir == PLAN_BASE_DIR == tmp_path, so
# the helper materializes that exact path inside the isolated fixture tree.


def _seed_worktree_resident_plan(
    fixture_dir: Path,
    plan_id: str,
    *,
    worktree_name: str | None = None,
    current_phase: str = '5-execute',
) -> Path:
    """Materialize a moved-in worktree plan and return its status.json path.

    Mirrors the ADR-002 phase-5 move-in: the plan directory lives under
    ``{fixture_dir}/worktrees/{worktree_name}/.plan/local/plans/{plan_id}/``
    (NOT under the main ``{fixture_dir}/plans/`` tree). ``worktree_name``
    defaults to ``plan_id`` — the canonical ``worktree-create`` layout where
    the worktree dir is named for the plan it hosts.
    """
    wt = worktree_name or plan_id
    wt_plan_dir = fixture_dir / 'worktrees' / wt / '.plan' / 'local' / 'plans' / plan_id
    wt_plan_dir.mkdir(parents=True, exist_ok=True)
    status_path = wt_plan_dir / 'status.json'
    status_path.write_text(
        json.dumps({'current_phase': current_phase, 'title': f'Worktree {plan_id}'}),
        encoding='utf-8',
    )
    return status_path


# =============================================================================
# Tests: cmd_list_orphans (orphan-dir cleanup pass)
# =============================================================================


def _seed_legitimate_plan(plan_id: str) -> None:
    """cmd_create a plan with a status.json so cmd_list_orphans skips it."""
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title=f'Legitimate {plan_id}',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


# =============================================================================
# Regression Tests: cmd_transition inline strict-verify guard for guarded
# boundaries (folded from the standalone phase_handshake verify --strict step
# that orchestrator workflow docs used to issue separately at 5-execute -> 6-finalize).
# =============================================================================

# Use STANDARD imports for handshake modules so the monkeypatch in the
# fixtures below hits the same module instance that ``_cmd_lifecycle.cmd_verify``
# reads at runtime.
_PLAN_HANDSHAKE_SCRIPTS_DIR = str(
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'plan-marshall'
    / 'scripts'
)


if _PLAN_HANDSHAKE_SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _PLAN_HANDSHAKE_SCRIPTS_DIR)


def _seed_plan_with_5_execute_capture(plan_id):
    """Create a plan, advance to 5-execute, capture the handshake row."""
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Transition Guard Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    for phase in ('1-init', '2-refine', '3-outline', '4-plan'):
        cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))
    _cmds.cmd_capture(
        Namespace(plan_id=plan_id, phase='5-execute', override=False, reason=None, strict=False)
    )


def _seed_plan_with_4_plan_capture(plan_id):
    """Create a plan, advance to 4-plan, capture the handshake row."""
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Transition Guard Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    for phase in ('1-init', '2-refine', '3-outline'):
        cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='4-plan'))
    _cmds.cmd_capture(
        Namespace(plan_id=plan_id, phase='4-plan', override=False, reason=None, strict=False)
    )


# =============================================================================
# Test: Hybrid loopback contract — `--loop-back-target` granularity flag
# =============================================================================

_cmd_mark_step = load_script_module('plan-marshall', 'manage-status', '_cmd_mark_step.py', '_cmd_mark_step')


cmd_mark_step_done = _cmd_mark_step.cmd_mark_step_done


def _mark_step_args(
    plan_id: str,
    phase: str,
    step: str,
    outcome: str,
    *,
    force: bool = False,
    display_detail: str | None = None,
    head_at_completion: str | None = None,
    loop_back_target: str | None = None,
) -> Namespace:
    """Build a Namespace for cmd_mark_step_done that mirrors the argparse layer."""
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


def _setup_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Loop-back Target Tests',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def _stub_finding_queries(monkeypatch, per_type: dict[str, int], qgate: int = 0) -> None:
    """Stub the per-type and qgate-aggregator query helpers."""
    monkeypatch.setattr(
        _inv, '_query_pending_count_for_type', lambda _pid, ft: per_type.get(ft, 0)
    )
    monkeypatch.setattr(
        _inv, '_query_pending_qgate_count_aggregated', lambda _pid: qgate
    )


# =============================================================================
# Regression Tests: persisted-title-state-write drive seam (Defects 1 & 2)
# =============================================================================
#
# Every current_phase write fires the shared _surface_drive seam AFTER
# write_status — one bind (session->plan, last-driven-wins; Defect 2) plus one
# repaint (icon-optional title push; Defect 1). cmd_transition is the phase-
# advance writer covered here; the seam internals (bind+repaint ordering, the
# no-icon repaint contract, delegation-failure swallowing, and the executor-
# absent no-op guard) are pinned directly on _status_core.

_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_status_core_drive')
