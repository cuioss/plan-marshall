#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""The capture-time refusal of a self-contradictory handshake row.

Two SHA columns exist on the handshake row because they describe two different
trees. A worktree-backed plan whose ``main_sha`` equals its ``worktree_sha`` is
therefore reporting one tree under two names — a capture bug, not a valid row —
so ``capture_all`` raises and ``cmd_capture`` refuses to persist.

The refusal is one-sided by construction: a plan genuinely running on main
captures no ``worktree_sha`` at all, so it can never be blocked by this rule.
Its ``same_tree`` field carries the diagnosis, derived from the two resolved
paths rather than from the equal values.

The main-anchored resolution these columns depend on is pinned by the sibling
``test_invariants_main_resolution.py``.
"""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')
SCRIPTS_DIR = SCRIPT_PATH.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _handshake_commands as hc
import _invariants as inv


def _narrow_to_sha_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restrict the registry to the two SHA columns the refusal compares.

    Keeps ``capture_all`` off the ten plan-state captures that would shell out
    through ``_run_script``, so the test asserts the cross-field rule alone.
    """
    monkeypatch.setattr(
        inv,
        'INVARIANTS',
        [
            ('main_sha', inv._always, inv._capture_main_sha),
            ('worktree_sha', inv._worktree_in_use, inv._capture_worktree_sha),
        ],
    )


def test_capture_all_refuses_equal_shas_on_a_worktree_backed_plan(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An equal pair under a worktree-backed plan is refused, not persisted."""
    _narrow_to_sha_columns(monkeypatch)
    monkeypatch.setattr(inv, 'git_head', lambda _tree: 'cafebabe1234')
    metadata = {'use_worktree': True, 'worktree_path': str(tmp_path / 'wt')}

    with pytest.raises(inv.WorktreeShaEqualsMainSha) as excinfo:
        inv.capture_all('p', metadata, '5-execute')

    assert excinfo.value.sha == 'cafebabe1234'
    assert excinfo.value.phase == '5-execute'


def test_capture_all_permits_equal_shas_for_a_plan_running_on_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A plan genuinely on main captures no ``worktree_sha``, so nothing refuses.

    The other direction of the assertion: without this, an on-main run whose
    single tree is trivially "equal to itself" would be blocked at every
    boundary.
    """
    _narrow_to_sha_columns(monkeypatch)
    monkeypatch.setattr(inv, 'git_head', lambda _tree: 'cafebabe1234')

    captured = inv.capture_all('p', {'use_worktree': False}, '5-execute')

    assert captured == {'main_sha': 'cafebabe1234'}


def test_refusal_reports_same_tree_when_the_resolution_regressed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Both columns read from one directory → ``same_tree`` is True.

    This is the capture-bug diagnosis: the main-scoped resolution fell back to
    the worktree.
    """
    _narrow_to_sha_columns(monkeypatch)
    worktree = tmp_path / 'wt'
    worktree.mkdir()
    monkeypatch.setattr(inv, 'git_head', lambda _tree: 'deadbeef9999')
    monkeypatch.setattr(inv, '_main_repo_root', lambda: worktree)

    with pytest.raises(inv.WorktreeShaEqualsMainSha) as excinfo:
        inv.capture_all('p', {'worktree_path': str(worktree)}, '5-execute')

    assert excinfo.value.same_tree is True
    assert 'SAME tree' in str(excinfo.value)


def test_refusal_reports_distinct_trees_when_two_checkouts_share_a_commit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Two distinct trees holding one commit → ``same_tree`` is False.

    The reachable cause is a feature branch with no commit of its own yet. The
    refusal still stands — two columns that cannot be told apart carry no
    signal — but the operator is told which cause applies.
    """
    _narrow_to_sha_columns(monkeypatch)
    main_root = tmp_path / 'main'
    worktree = tmp_path / 'wt'
    main_root.mkdir()
    worktree.mkdir()
    monkeypatch.setattr(inv, 'git_head', lambda _tree: 'deadbeef9999')
    monkeypatch.setattr(inv, '_main_repo_root', lambda: main_root)

    with pytest.raises(inv.WorktreeShaEqualsMainSha) as excinfo:
        inv.capture_all('p', {'worktree_path': str(worktree)}, '5-execute')

    assert excinfo.value.same_tree is False
    assert 'no commit yet' in str(excinfo.value)


def test_cmd_capture_returns_structured_refusal_and_writes_no_row(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``cmd_capture`` surfaces the refusal as TOON error and persists nothing."""
    _narrow_to_sha_columns(monkeypatch)
    monkeypatch.setattr(inv, 'git_head', lambda _tree: 'cafebabe1234')
    monkeypatch.setattr(
        hc,
        '_load_status_metadata',
        lambda _plan_id: {'use_worktree': True, 'worktree_path': str(tmp_path / 'wt')},
    )
    monkeypatch.setattr(hc, '_resolve_worktree_assertion', lambda _md, _phase: None)
    written: list[object] = []
    monkeypatch.setattr(hc, 'upsert_row', lambda *a, **k: written.append(a))

    result = hc.cmd_capture(
        Namespace(plan_id='p', phase='5-execute', override=False, reason='')
    )

    assert result['status'] == 'error'
    assert result['error'] == 'worktree_sha_equals_main_sha'
    assert result['sha'] == 'cafebabe1234'
    assert result['same_tree'] is False
    assert written == [], 'a self-contradictory row must not be persisted'


def test_refusal_error_code_is_a_verify_refusal_that_blocks_transition() -> None:
    """The refusal is never bypassed by the loop-back auto-override marker.

    Quantified over the shipped ``VERIFY_REFUSAL_ERRORS`` set rather than a
    hard-coded copy of it.
    """
    lifecycle = load_script_module(
        'plan-marshall', 'manage-status', '_cmd_lifecycle.py', 'lifecycle_refusal_mod'
    )

    assert 'worktree_sha_equals_main_sha' in lifecycle.VERIFY_REFUSAL_ERRORS
