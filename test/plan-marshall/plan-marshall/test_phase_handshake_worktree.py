#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for phase_handshake worktree tri-state assertions.

Split from test_phase_handshake.py: covers the metadata→disk direction
(``_resolve_worktree_assertion``) and the inverse disk→metadata direction
(``_capture_worktree_orphan``) — full 6-phase × 2-metadata-state matrix
plus the canonical-path bypass scenarios.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _handshake_fixtures import cmds, inv


_PRE_MATERIALIZATION_PHASES_FOR_TEST = ('1-init', '2-refine', '3-outline', '4-plan')
_POST_MATERIALIZATION_PHASES_FOR_TEST = ('5-execute', '6-finalize')
_ALL_PHASES_FOR_TEST = _PRE_MATERIALIZATION_PHASES_FOR_TEST + _POST_MATERIALIZATION_PHASES_FOR_TEST


class TestTriStateWorktreeAssertion:
    """Pin the full tri-state contract of ``_resolve_worktree_assertion``."""

    @pytest.mark.parametrize('phase', _PRE_MATERIALIZATION_PHASES_FOR_TEST)
    def test_deferred_pending_returns_none_for_pre_materialization_phases(
        self, phase: str
    ) -> None:
        """use_worktree=true + worktree_path='' + pre-materialization phase → None."""
        metadata = {'use_worktree': True, 'worktree_path': ''}
        result = cmds._resolve_worktree_assertion(metadata, phase)
        assert result is None, (
            f'Tri-state regressed for phase {phase!r}: expected None, got {result!r}.'
        )

    @pytest.mark.parametrize('phase', _POST_MATERIALIZATION_PHASES_FOR_TEST)
    def test_worktree_unresolved_error_for_post_materialization_phases(
        self, phase: str
    ) -> None:
        """use_worktree=true + worktree_path='' + post-materialization phase → error."""
        metadata = {'use_worktree': True, 'worktree_path': ''}
        result = cmds._resolve_worktree_assertion(metadata, phase)
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'worktree_unresolved'
        assert result['reason'] == 'worktree_path_missing'

    @pytest.mark.parametrize('phase', _ALL_PHASES_FOR_TEST)
    def test_use_worktree_false_passes_for_every_phase(self, phase: str) -> None:
        """use_worktree=false → None for every phase (main-checkout pass-through)."""
        metadata = {'use_worktree': False, 'worktree_path': ''}
        result = cmds._resolve_worktree_assertion(metadata, phase)
        assert result is None

    def test_legacy_single_arg_caller_preserves_strict_empty_path_failure(self) -> None:
        """phase=None (legacy callers) → strict pre-tri-state behaviour."""
        metadata = {'use_worktree': True, 'worktree_path': ''}
        result = cmds._resolve_worktree_assertion(metadata, None)
        assert result is not None
        assert result['error'] == 'worktree_unresolved'
        assert result['reason'] == 'worktree_path_missing'


class TestOrphanCanonicalBypass:
    """Pin the inverse-direction (disk→metadata) tri-state contract."""

    @pytest.fixture
    def isolated_repo(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        # Orphan detection resolves the worktree root via
        # ``file_ops.get_worktree_root()`` → ``get_base_dir() / 'worktrees'``,
        # which honours ``PLAN_BASE_DIR``. Pin it to ``tmp_path/.plan/local`` so
        # the canonical orphan path the helper materialises
        # (``tmp_path/.plan/local/worktrees/{plan_id}``) is exactly what
        # ``get_worktree_root()`` resolves — keeping detection isolated to
        # ``tmp_path``. ``_repo_root`` is pinned alongside for invariants that
        # consult it directly.
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path / '.plan' / 'local'))
        monkeypatch.setattr(inv, '_repo_root', lambda: tmp_path)
        return tmp_path

    @staticmethod
    def _create_canonical_orphan(repo_root: Path, plan_id: str) -> Path:
        orphan = repo_root / '.plan' / 'local' / 'worktrees' / plan_id
        orphan.mkdir(parents=True, exist_ok=True)
        return orphan

    @pytest.mark.parametrize('phase', _ALL_PHASES_FOR_TEST)
    def test_bypass_when_use_worktree_true_and_canonical_path_present(
        self, isolated_repo: Path, phase: str
    ) -> None:
        """use_worktree=true + canonical orphan path → None (no drift) for any phase."""
        plan_id = 'orphan-bypass-true'
        self._create_canonical_orphan(isolated_repo, plan_id)
        metadata = {'use_worktree': True}
        result = inv._capture_worktree_orphan(plan_id, metadata, phase)
        assert result is None

    @pytest.mark.parametrize('phase', _ALL_PHASES_FOR_TEST)
    def test_raises_writer_chain_drift_when_use_worktree_false(
        self, isolated_repo: Path, phase: str
    ) -> None:
        """use_worktree=false + canonical orphan path → WorktreeMetadataDrift."""
        plan_id = 'orphan-drift-false'
        orphan = self._create_canonical_orphan(isolated_repo, plan_id)
        metadata = {'use_worktree': False}
        with pytest.raises(inv.WorktreeMetadataDrift) as exc_info:
            inv._capture_worktree_orphan(plan_id, metadata, phase)
        assert exc_info.value.plan_id == plan_id
        assert exc_info.value.worktree_dir == str(orphan)
        assert exc_info.value.use_worktree is False

    @pytest.mark.parametrize('phase', _ALL_PHASES_FOR_TEST)
    def test_raises_writer_chain_drift_when_use_worktree_missing(
        self, isolated_repo: Path, phase: str
    ) -> None:
        """No use_worktree key + canonical orphan path → WorktreeMetadataDrift."""
        plan_id = 'orphan-drift-missing'
        self._create_canonical_orphan(isolated_repo, plan_id)
        metadata: dict[str, object] = {}
        with pytest.raises(inv.WorktreeMetadataDrift):
            inv._capture_worktree_orphan(plan_id, metadata, phase)

    @pytest.mark.parametrize('phase', _ALL_PHASES_FOR_TEST)
    def test_returns_none_when_orphan_directory_absent(
        self, isolated_repo: Path, phase: str
    ) -> None:
        """No orphan dir → None for every (phase, metadata-state) combination."""
        plan_id = 'orphan-absent'
        for use_worktree_value in (True, False, None):
            metadata = {'use_worktree': use_worktree_value} if use_worktree_value is not None else {}
            result = inv._capture_worktree_orphan(plan_id, metadata, phase)
            assert result is None
