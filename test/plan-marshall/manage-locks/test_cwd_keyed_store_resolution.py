#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the D3 CWD-keyed store-resolution scope-qualifier sweep.

The D3 audit (``manage-locks/standards/cwd-keyed-store-resolution-audit.md``) FIXES
the two authority-bearing plan-census sites so a cwd-scoped enumeration cannot be
silently read as a global census (the #948 sibling-worktree shape):

* ``manage-status`` ``cmd_list`` surfaces a first-class ``scope`` field
  (``main`` / ``worktree_local`` / ``unknown``, from ``_resolution_scope``): from
  the main checkout the census is comprehensive (``main``); from a pinned worktree
  its resolvers anchor there and it is BLIND to sibling worktrees
  (``worktree_local``); an unresolvable base fails closed to ``unknown``.
* ``workflow-integration-git`` ``cmd_worktree_list`` PROPAGATES that ``scope``
  verbatim from the underlying ``manage-status list`` output (single-sourced, never
  re-derived; a malformed/scope-less output fails closed to ``unknown``).

These tests exercise the fixed behaviour at both sites.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module

status_query = load_script_module(
    'plan-marshall', 'manage-status', '_status_query.py', '_status_query_cwd_scope_under_test'
)
git_workflow = load_script_module(
    'plan-marshall', 'workflow-integration-git', 'git-workflow.py', 'git_workflow_cwd_scope_under_test'
)


# =============================================================================
# _status_query._resolution_scope — main / worktree_local / unknown
# =============================================================================


class TestResolutionScope:
    def test_scope_is_main_when_base_is_main_anchored(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Under a PLAN_BASE_DIR override BOTH get_base_dir() and
        # resolve_main_anchored_path('') resolve to the override, so the current base
        # IS the main-anchored base → the census is comprehensive → 'main'.
        base = tmp_path / 'main' / '.plan' / 'local'
        base.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))

        assert status_query._resolution_scope() == 'main'

    def test_scope_is_worktree_local_when_base_differs_from_main_anchor(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Simulate a pinned worktree: get_base_dir() anchors at the worktree's own
        # .plan/local while resolve_main_anchored_path('') still resolves to main.
        # The two differ → the census is cwd-scoped and blind to siblings →
        # 'worktree_local' (an absent plan here is unknown, NOT authoritative absence).
        base = tmp_path / 'main' / '.plan' / 'local'
        base.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))
        worktree_base = base / 'worktrees' / 'wt-x' / '.plan' / 'local'

        monkeypatch.setattr(status_query, 'get_base_dir', lambda: worktree_base)

        assert status_query._resolution_scope() == 'worktree_local'

    def test_scope_is_unknown_when_base_unresolvable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # An unresolvable base (get_base_dir raises RuntimeError) fails closed to
        # 'unknown' — neither authoritative — per ADR-009, never a vacuous 'main'.
        base = tmp_path / 'main' / '.plan' / 'local'
        base.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))

        def _boom() -> Path:
            raise RuntimeError('base unresolvable')

        monkeypatch.setattr(status_query, 'get_base_dir', _boom)

        assert status_query._resolution_scope() == 'unknown'


# =============================================================================
# _status_query.cmd_list — surfaces the scope field
# =============================================================================


class TestCmdListScopeField:
    def test_cmd_list_carries_scope_main_from_main_checkout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The census output carries a first-class 'scope' field; from the main-anchored
        # base it is 'main'. An empty plans dir still reports the scope.
        base = tmp_path / 'main' / '.plan' / 'local'
        (base / 'plans').mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))

        result = status_query.cmd_list(Namespace(filter=None))

        assert result['status'] == 'success'
        assert result['scope'] == 'main'
        assert result['plans'] == []

    def test_cmd_list_carries_scope_worktree_local_when_base_differs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # When get_base_dir() anchors at a worktree (differs from the main anchor),
        # the census reports 'worktree_local' so a consumer cannot read an absent
        # plan as authoritative absence.
        base = tmp_path / 'main' / '.plan' / 'local'
        (base / 'plans').mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))
        worktree_base = base / 'worktrees' / 'wt-x' / '.plan' / 'local'
        monkeypatch.setattr(status_query, 'get_base_dir', lambda: worktree_base)

        result = status_query.cmd_list(Namespace(filter=None))

        assert result['scope'] == 'worktree_local'


# =============================================================================
# git-workflow.cmd_worktree_list — propagates the scope field
# =============================================================================


class TestWorktreeListScopePropagation:
    def test_propagates_worktree_local_scope_from_list_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # cmd_worktree_list reads `manage-status list` and INHERITS its cwd-scoped
        # blindness — it must propagate the scope verbatim. Stub the status call so
        # the underlying census reports 'worktree_local' with no plan rows.
        base = tmp_path / 'main' / '.plan' / 'local'
        base.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))

        canned = 'status: success\ntotal: 0\nscope: worktree_local\nplans[0]:\n'
        monkeypatch.setattr(git_workflow, '_manage_status_call', lambda *_a, **_k: (0, canned, ''))

        result = git_workflow.cmd_worktree_list(Namespace())

        assert result['status'] == 'success'
        assert result['scope'] == 'worktree_local'
        assert result['count'] == 0

    def test_propagates_main_scope_from_list_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        base = tmp_path / 'main' / '.plan' / 'local'
        base.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))

        canned = 'status: success\ntotal: 0\nscope: main\nplans[0]:\n'
        monkeypatch.setattr(git_workflow, '_manage_status_call', lambda *_a, **_k: (0, canned, ''))

        result = git_workflow.cmd_worktree_list(Namespace())

        assert result['scope'] == 'main'

    def test_scope_fails_closed_to_unknown_when_list_output_lacks_scope(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A scope-less (e.g. older) list output fails closed to 'unknown' rather than
        # a vacuous 'main' — the consumer must not be told the census is global.
        base = tmp_path / 'main' / '.plan' / 'local'
        base.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))

        canned = 'status: success\ntotal: 0\nplans[0]:\n'  # no scope key
        monkeypatch.setattr(git_workflow, '_manage_status_call', lambda *_a, **_k: (0, canned, ''))

        result = git_workflow.cmd_worktree_list(Namespace())

        assert result['scope'] == 'unknown'
