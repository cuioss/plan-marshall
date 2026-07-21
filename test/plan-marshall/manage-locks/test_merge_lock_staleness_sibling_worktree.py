#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-cutting regression test for the #948 sibling-worktree staleness shape.

The #948 incident: a merge-lock holder (``steward-provisioning-fail-closed``) was
judged stale from a WORKTREE-SCOPED view and its lock released while it was live in
another session's sibling worktree. The manual-release recovery path inferred death
from a cwd-scoped enumeration (``manage-status list`` / ``worktree-list``) which,
from a session pinned to its OWN worktree, structurally cannot observe a holder
living in a SIBLING worktree — so the empty result was mistaken for proof of death.

This test reproduces that shape end-to-end and asserts the D1 fix closes it:

* A holder whose live plan dir sits in a SIBLING worktree, with the staleness query
  / ``release --require-stale`` issued from a DIFFERENT worktree cwd, is judged
  ``fresh`` (NOT stale) and the lock is NOT removed — regardless of the querying
  cwd. This is the cwd-INDEPENDENCE property: the verdict is computed from the
  main-anchored resolution, never the caller's cwd-scoped store.
* The positive contrast: a genuinely-dead holder (no plan dir on main, no live
  worktree) is judged ``stale`` and the conditional release proceeds.

It drives the REAL ``merge_lock`` entry points (``run_release`` / ``run_check``)
against REAL main-anchored resolution (a PLAN_BASE_DIR test override standing in for
the main checkout) — NOT a mocked ``holder_staleness`` predicate — so the assertion
genuinely exercises the cwd-independence of the resolution. To make the
cwd-independence load-bearing, each query runs with cwd pinned (``monkeypatch.chdir``)
into a THIRD worktree that does NOT contain the holder's plan dir: a cwd-scoped
resolver would see nothing there, yet the main-anchored verdict still sees the
holder's real sibling-worktree plan dir.

Pre-D1 discrimination: the test targets ``release --require-stale`` and the
``staleness`` verdict, neither of which existed before D1 — against the pre-D1 code
path the ``--require-stale`` conditional (fail-closed on a live sibling holder) is
absent, so the sibling holder's lock would be force-removed. After D1 it is refused.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module

merge_lock = load_script_module(
    'plan-marshall', 'manage-locks', 'merge_lock.py', 'merge_lock_sibling_wt_under_test'
)


@pytest.fixture
def sibling_worktree_scene(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage the #948 topology under a PLAN_BASE_DIR main stand-in.

    Layout::

        tmp/main/.plan/local/                              (PLAN_BASE_DIR — main)
        tmp/main/.plan/local/merge.lock                    (the O_EXCL lock)
        tmp/main/.plan/local/worktrees/{holder}/...        (a holder's SIBLING worktree)
        tmp/main/.plan/local/worktrees/querier-wt/.plan/   (a THIRD worktree — the caller's cwd)

    The holder's live plan dir lives ONLY in its sibling worktree (absent on main).
    The caller is pinned (cwd) to ``querier-wt``, which holds NO holder plan dir — so
    a cwd-scoped resolver would see the holder as absent, while the main-anchored
    resolution sees its real sibling-worktree plan dir.
    """
    base = tmp_path / 'main' / '.plan' / 'local'
    (base / 'plans').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))

    # The caller's OWN worktree — a third tree that does NOT contain the holder.
    querier_wt = base / 'worktrees' / 'querier-wt'
    (querier_wt / '.plan' / 'local' / 'plans').mkdir(parents=True)

    # Stub the best-effort title-token seams so the release path never spawns the
    # real executor subprocess (out-of-scope for the correctness assertion).
    monkeypatch.setattr(merge_lock, '_set_title_token', lambda _p, _state: None)
    monkeypatch.setattr(merge_lock, '_clear_title_token', lambda _p: None)
    monkeypatch.setattr(merge_lock, '_push_title_token', lambda _p, icon=None: None)

    return {
        'base': base,
        'lock_path': base / 'merge.lock',
        'querier_wt': querier_wt,
    }


def _write_lock(lock_path: Path, holder: str) -> None:
    lock_path.write_text(holder + '\n', encoding='utf-8')


def _make_sibling_worktree_live_plan(base: Path, holder: str) -> None:
    """Place the holder's live plan dir ONLY in its sibling worktree (#948 shape)."""
    (base / 'worktrees' / holder / '.plan' / 'local' / 'plans' / holder).mkdir(parents=True)


def test_sibling_worktree_holder_is_not_released_from_a_foreign_worktree_cwd(
    sibling_worktree_scene: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    # #948 reproduction: the holder is live in its SIBLING worktree; the caller is
    # pinned to a DIFFERENT worktree. A cwd-scoped view from the caller's worktree
    # would see the holder absent (its plan dir is not there) and wrongly infer
    # death. The main-anchored verdict must see the live sibling-worktree plan dir
    # and refuse the release fail-closed.
    scene = sibling_worktree_scene
    holder = 'steward-provisioning-fail-closed'  # the real #948 holder id shape
    _make_sibling_worktree_live_plan(scene['base'], holder)
    _write_lock(scene['lock_path'], holder)

    # Pin cwd into the caller's OWN (foreign) worktree — the property under test is
    # that this cwd does NOT influence the verdict.
    monkeypatch.chdir(scene['querier_wt'])

    result = merge_lock.run_release(Namespace(plan_id=holder, require_stale=True))

    assert result['status'] == 'refused'
    assert result['reason'] == 'holder_not_provably_dead'
    assert result['staleness'] == 'fresh'
    # The live sibling holder's lock is NOT removed — the #948 mis-release is closed.
    assert scene['lock_path'].is_file()
    assert scene['lock_path'].read_text(encoding='utf-8').strip() == holder


def test_check_reports_fresh_for_sibling_worktree_holder_from_foreign_cwd(
    sibling_worktree_scene: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The non-mutating check surfaces the same main-anchored verdict regardless of
    # cwd: fresh for a holder live in a sibling worktree, queried from a third tree.
    scene = sibling_worktree_scene
    holder = 'sibling-live-holder'
    _make_sibling_worktree_live_plan(scene['base'], holder)
    _write_lock(scene['lock_path'], holder)
    monkeypatch.chdir(scene['querier_wt'])

    result = merge_lock.run_check(Namespace(plan_id='some-querier'))

    assert result['status'] == 'held'
    assert result['holder_plan_id'] == holder
    assert result['staleness'] == 'fresh'


def test_genuinely_dead_holder_is_released_from_a_foreign_worktree_cwd(
    sibling_worktree_scene: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Positive contrast: a holder with NO plan dir on main AND no live worktree is
    # genuinely dead → stale → the conditional release proceeds and removes the lock,
    # even when the query is issued from a foreign worktree cwd. This proves the
    # refusal above is discriminating (stale-vs-fresh), not a blanket refusal.
    scene = sibling_worktree_scene
    holder = 'genuinely-dead-holder'
    _write_lock(scene['lock_path'], holder)  # no sibling worktree, no plan dir
    monkeypatch.chdir(scene['querier_wt'])

    result = merge_lock.run_release(Namespace(plan_id=holder, require_stale=True))

    assert result['status'] == 'success'
    assert result['action'] == 'released'
    assert result['staleness'] == 'stale'
    assert not scene['lock_path'].exists()
