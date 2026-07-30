#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``_references_core.resolve_live_worktree``.

``resolve_live_worktree`` is the single shared entry point every footprint
consumer uses to reach a plan's live working tree. Before it existed each
consumer reconstructed the worktree by reading ``status.metadata.worktree_path``
out of the plan's own ``status.json`` — a hand-rolled re-derivation of the
worktree face that ``file_ops.resolve_plan_context`` owns.

Every branch of the helper is a deliberate ``None`` answer with a distinct
cause, and each cause is pinned here because collapsing any of them would
silently change what its callers treat as "no worktree":

* ``plan_id is None`` (an ARCHIVED plan) — answered ``None`` WITHOUT resolving,
  since an archived plan's recorded path names a directory finalize removed.
* ``has_worktree`` false — the gate is the flag, NOT the truthiness of the
  resolved path. The resolver falls back to the main checkout for a plan that
  binds no worktree, so gating on the path would hand callers a main-checkout
  footprint where they previously got "no worktree". This is the branch most
  likely to regress, so it is asserted against a resolver that returns a REAL,
  existing directory alongside ``has_worktree=False``.
* ``WorktreeResolutionError`` — resolution failed; callers fall through a tier.
* the resolved path is not a directory — a stale or removed worktree.
"""

from __future__ import annotations

from pathlib import Path

from conftest import load_script_module

_core = load_script_module(
    'plan-marshall', 'manage-references', '_references_core.py', '_references_core_rlw'
)

resolve_live_worktree = _core.resolve_live_worktree
WorktreeResolutionError = _core.WorktreeResolutionError


class _Context:
    """Minimal stand-in for the resolver's returned plan context."""

    def __init__(self, has_worktree: bool, worktree_path: str) -> None:
        self.has_worktree = has_worktree
        self.worktree_path = worktree_path


class TestArchivedPlanShortCircuit:
    """A falsy ``plan_id`` is answered without consulting the resolver."""

    def test_none_plan_id_returns_none_without_resolving(self, monkeypatch):
        asked = []

        def _resolve(plan_id, ensure=True):
            asked.append(plan_id)
            raise AssertionError('archived mode must not reach the resolver')

        monkeypatch.setattr(_core, 'resolve_plan_context', _resolve)

        assert resolve_live_worktree(None) is None
        assert asked == []

    def test_empty_plan_id_returns_none_without_resolving(self, monkeypatch):
        def _resolve(plan_id, ensure=True):
            raise AssertionError('an empty plan id must not reach the resolver')

        monkeypatch.setattr(_core, 'resolve_plan_context', _resolve)

        assert resolve_live_worktree('') is None


class TestHasWorktreeGate:
    """``has_worktree`` is the gate, not the truthiness of the resolved path."""

    def test_worktree_bound_plan_returns_the_directory(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            _core,
            'resolve_plan_context',
            lambda plan_id, ensure=True: _Context(True, str(tmp_path)),
        )

        assert resolve_live_worktree('demo-plan') == Path(tmp_path)

    def test_resolver_is_asked_not_to_create(self, monkeypatch, tmp_path):
        """Resolution must be a read: ``ensure=False``, never a create."""
        seen = {}

        def _resolve(plan_id, ensure=True):
            seen['plan_id'] = plan_id
            seen['ensure'] = ensure
            return _Context(True, str(tmp_path))

        monkeypatch.setattr(_core, 'resolve_plan_context', _resolve)

        resolve_live_worktree('demo-plan')
        assert seen == {'plan_id': 'demo-plan', 'ensure': False}

    def test_main_checkout_plan_returns_none_despite_real_path(
        self, monkeypatch, tmp_path
    ):
        """``has_worktree=False`` wins even though ``worktree_path`` is a real dir.

        The resolver falls back to the main checkout for a plan that binds no
        worktree. A truthiness test on the path would therefore return the MAIN
        CHECKOUT here, silently turning "no worktree" into a whole-repo
        footprint. The fixture supplies an existing directory precisely so that
        a regression to path-truthiness fails this test.
        """
        assert tmp_path.is_dir()
        monkeypatch.setattr(
            _core,
            'resolve_plan_context',
            lambda plan_id, ensure=True: _Context(False, str(tmp_path)),
        )

        assert resolve_live_worktree('demo-plan') is None


class TestFailureBranches:
    """Resolution failure and a stale path are both answered ``None``."""

    def test_resolution_error_returns_none(self, monkeypatch):
        def _resolve(plan_id, ensure=True):
            raise WorktreeResolutionError('cannot resolve')

        monkeypatch.setattr(_core, 'resolve_plan_context', _resolve)

        assert resolve_live_worktree('demo-plan') is None

    def test_nonexistent_resolved_path_returns_none(self, monkeypatch, tmp_path):
        missing = tmp_path / 'removed-worktree'
        assert not missing.exists()
        monkeypatch.setattr(
            _core,
            'resolve_plan_context',
            lambda plan_id, ensure=True: _Context(True, str(missing)),
        )

        assert resolve_live_worktree('demo-plan') is None

    def test_resolved_path_that_is_a_file_returns_none(self, monkeypatch, tmp_path):
        not_a_dir = tmp_path / 'a-file'
        not_a_dir.write_text('x', encoding='utf-8')
        monkeypatch.setattr(
            _core,
            'resolve_plan_context',
            lambda plan_id, ensure=True: _Context(True, str(not_a_dir)),
        )

        assert resolve_live_worktree('demo-plan') is None
