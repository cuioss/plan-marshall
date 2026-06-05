#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for phase_handshake worktree assertions.

Split from test_phase_handshake.py: covers the metadata→disk direction
(``_resolve_worktree_assertion``) and the phase-keyed relaxation of the
worktree-state drift invariants.

Under the no-sentinel B-strip model phases 1-4 persist only ``use_worktree``
and the worktree (with its ``worktree_path``) is materialized at phase-5
Step 2.5. An empty ``worktree_path`` while ``use_worktree==true`` is therefore
the legitimate pre-materialization state for the on-main planning phases
(1-init / 2-refine / 3-outline / 4-plan) and the assertion passes there; from
phase-5 onward — and whenever the boundary phase is unknown — an empty path is
``worktree_unresolved`` (fail-closed). A *set-but-broken* path (missing dir,
non-worktree, stale toplevel) is ``worktree_unresolved`` at every phase. The
inverse-direction orphan invariant was removed entirely.
"""

from __future__ import annotations

import pytest

from _handshake_fixtures import cmds, inv


_PLANNING_PHASES_FOR_TEST = ('1-init', '2-refine', '3-outline', '4-plan')
_POST_MATERIALIZATION_PHASES_FOR_TEST = ('5-execute', '6-finalize')
_ALL_PHASES_FOR_TEST = _PLANNING_PHASES_FOR_TEST + _POST_MATERIALIZATION_PHASES_FOR_TEST


class TestWorktreeAssertion:
    """Pin the contract of ``_resolve_worktree_assertion`` (metadata→disk)."""

    @pytest.mark.parametrize('phase', _PLANNING_PHASES_FOR_TEST)
    def test_empty_path_passes_at_planning_phases(self, phase: str) -> None:
        """use_worktree=true + worktree_path='' → None at phases 1-4 (pre-materialization)."""
        metadata = {'use_worktree': True, 'worktree_path': ''}
        assert cmds._resolve_worktree_assertion(metadata, phase) is None

    @pytest.mark.parametrize('phase', _PLANNING_PHASES_FOR_TEST)
    def test_missing_path_passes_at_planning_phases(self, phase: str) -> None:
        """use_worktree=true + no worktree_path key → None at phases 1-4."""
        metadata = {'use_worktree': True}
        assert cmds._resolve_worktree_assertion(metadata, phase) is None

    @pytest.mark.parametrize('phase', _POST_MATERIALIZATION_PHASES_FOR_TEST)
    def test_empty_path_unresolved_post_materialization(self, phase: str) -> None:
        """use_worktree=true + worktree_path='' → worktree_unresolved at phases 5-6."""
        metadata = {'use_worktree': True, 'worktree_path': ''}
        result = cmds._resolve_worktree_assertion(metadata, phase)
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'worktree_unresolved'
        assert result['reason'] == 'worktree_path_missing'

    @pytest.mark.parametrize('phase', _POST_MATERIALIZATION_PHASES_FOR_TEST)
    def test_missing_path_unresolved_post_materialization(self, phase: str) -> None:
        """use_worktree=true + no worktree_path key → worktree_unresolved at phases 5-6."""
        metadata = {'use_worktree': True}
        result = cmds._resolve_worktree_assertion(metadata, phase)
        assert result is not None
        assert result['error'] == 'worktree_unresolved'
        assert result['reason'] == 'worktree_path_missing'

    def test_empty_path_unresolved_when_phase_unknown(self) -> None:
        """Default phase=None is fail-closed: empty path → worktree_unresolved."""
        metadata = {'use_worktree': True, 'worktree_path': ''}
        result = cmds._resolve_worktree_assertion(metadata)
        assert result is not None
        assert result['error'] == 'worktree_unresolved'
        assert result['reason'] == 'worktree_path_missing'

    def test_use_worktree_false_passes(self) -> None:
        """use_worktree=false → None (main-checkout pass-through)."""
        metadata = {'use_worktree': False, 'worktree_path': ''}
        result = cmds._resolve_worktree_assertion(metadata)
        assert result is None

    def test_use_worktree_absent_passes(self) -> None:
        """No use_worktree key → None (plan not routed through a worktree)."""
        result = cmds._resolve_worktree_assertion({})
        assert result is None


class TestWorktreeStateDriftBlockingScopeRelaxation:
    """Pin the phase-keyed relaxation of the worktree-state drift invariants.

    Under the cwd-pinned move model (Option 5' / ADR-002) the worktree-state
    drift checks (``main_dirty_files`` layer-D leak guard + the sideways
    ``worktree_sha`` / ``worktree_dirty`` invariants) are RELAXED for the
    ``5-execute → 6-finalize`` boundary and RETAINED for the planning-phase
    boundaries (1-init / 2-refine / 3-outline / 4-plan). The discriminator is
    the boundary phase, asserted here directly against
    ``is_invariant_blocking_at_phase``.
    """

    _RELAXED_INVARIANTS = (
        'main_dirty_files',
        'worktree_sha',
        'worktree_dirty',
    )

    @pytest.mark.parametrize('invariant', _RELAXED_INVARIANTS)
    @pytest.mark.parametrize('phase', _PLANNING_PHASES_FOR_TEST)
    def test_blocking_at_planning_boundaries(self, invariant: str, phase: str) -> None:
        """Retained: drift in these invariants is blocking at phases 1-4."""
        assert inv.is_invariant_blocking_at_phase(invariant, phase) is True

    @pytest.mark.parametrize('invariant', _RELAXED_INVARIANTS)
    def test_not_blocking_at_phase_5_boundary(self, invariant: str) -> None:
        """Relaxed: drift in these invariants is NOT blocking at 5-execute."""
        assert inv.is_invariant_blocking_at_phase(invariant, '5-execute') is False
