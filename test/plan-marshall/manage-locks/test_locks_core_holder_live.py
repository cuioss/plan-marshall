#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-locks ``_locks_core.py`` shared coordination primitives."""


from __future__ import annotations

import json

import pytest
from _locks_core_fixtures import (
    _atomic_write_json,
    _mod,
    _read_json_or_empty,
    holder_has_live_worktree,
    holder_is_dead,
    holder_staleness,
)


def test_holder_has_live_worktree_false_when_worktree_dir_absent(plan_context):
    # No worktree directory on disk → False.
    assert holder_has_live_worktree('lc-no-worktree-dir') is False


def test_holder_has_live_worktree_empty_string_is_false(plan_context):
    # An empty holder has no worktree → False (distinct from holder_is_dead('')
    # which is True — the two predicates answer different questions).
    assert holder_has_live_worktree('') is False


def test_holder_has_live_worktree_whitespace_only_is_false(plan_context):
    # Whitespace is stripped to empty → no worktree → False.
    assert holder_has_live_worktree('   ') is False


def test_mid_recovery_holder_is_dead_by_plan_dir_but_has_live_worktree(plan_context):
    # The guard scenario: an interrupted finalize move-back leaves the worktree on
    # disk WITH its git plumbing intact (a `.git` marker) but the plan dir has been
    # moved out of BOTH main and the worktree's .plan. holder_is_dead is True
    # (plan-dir absent everywhere) while holder_has_live_worktree is True (the
    # genuine git-worktree marker is still present), so the acquire guard refuses to
    # auto-reclaim it.
    base = plan_context.fixture_dir
    worktree = base / 'worktrees' / 'lc-mid-recovery'
    worktree.mkdir(parents=True, exist_ok=True)
    (worktree / '.git').write_text(
        'gitdir: /main/.git/worktrees/lc-mid-recovery\n', encoding='utf-8'
    )

    assert holder_is_dead('lc-mid-recovery') is True
    assert holder_has_live_worktree('lc-mid-recovery') is True


@pytest.mark.parametrize(
    'malicious_holder',
    [
        '../evil',
        '../../evil',
        'a/../evil',
        'sub/evil',
        'sub\\evil',
        '..',
        'foo\x00bar',
    ],
)
def test_holder_has_live_worktree_rejects_traversal_holder(plan_context, malicious_holder):
    # holder is a plan-id joined DIRECTLY onto the worktrees root to build a
    # filesystem path. A holder bearing a path separator, a `..` parent segment,
    # or an embedded NUL must be rejected as having no live worktree BEFORE the
    # path is constructed — otherwise a crafted holder could escape the worktrees
    # root, resolve to an unrelated existing dir, and permanently block lock
    # reclamation (a DoS).
    assert holder_has_live_worktree(malicious_holder) is False


def test_holder_has_live_worktree_traversal_does_not_escape_worktrees_root(plan_context):
    # Concrete escape scenario: `../evil` would resolve `worktrees/../evil` to a
    # sibling dir of the worktrees root. Stage that sibling so, absent the guard,
    # the predicate would report the holder "alive". The guard must reject the
    # traversal and return False rather than resolving the escaped path.
    base = plan_context.fixture_dir
    (base / 'evil').mkdir(parents=True, exist_ok=True)  # worktrees/../evil target

    assert holder_has_live_worktree('../evil') is False


# =============================================================================
# holder_staleness — main-anchored three-valued verdict (D1)
# =============================================================================
#
# holder_staleness composes the two main-anchored predicates into a fresh / stale
# / unknown verdict, consulting ONLY main-anchored paths — never a cwd-scoped
# plan/worktree enumeration. It is the guard the manual-release recovery path
# lacked (the #948 sibling-worktree misjudgement). fresh = alive or mid-recovery;
# stale = main-anchored-dead AND no live worktree; unknown = the main-anchored
# .plan/local base could not be resolved (ADR-009: evidence-absent is surfaced
# explicitly, NEVER collapsed into stale).


def test_holder_staleness_fresh_when_alive_on_main(plan_context):
    # A holder whose plan dir lives on main (phases 1-4 / post-finalize) is alive
    # → fresh (must NOT be force-released).
    plan_context.plan_dir_for('lc-fresh-main')

    assert holder_staleness('lc-fresh-main') == 'fresh'


def test_holder_staleness_fresh_when_alive_in_worktree(plan_context):
    # While executing, the plan dir is MOVED into the worktree (absent on main).
    # The worktree-resident plan dir keeps the holder alive → fresh. This is the
    # exact #948 shape: a holder live in a (sibling) worktree is never stale.
    base = plan_context.fixture_dir
    wt_plan = base / 'worktrees' / 'lc-fresh-wt' / '.plan' / 'local' / 'plans' / 'lc-fresh-wt'
    wt_plan.mkdir(parents=True, exist_ok=True)

    assert holder_staleness('lc-fresh-wt') == 'fresh'


def test_holder_staleness_fresh_when_mid_recovery_live_worktree(plan_context):
    # dead-by-plan-dir (plan dir absent on main AND in the worktree's .plan) BUT a
    # genuine git-worktree marker is present → mid-recovery → fresh. An interrupted
    # finalize move-back must never be force-released.
    base = plan_context.fixture_dir
    worktree = base / 'worktrees' / 'lc-midrec'
    worktree.mkdir(parents=True, exist_ok=True)
    (worktree / '.git').write_text(
        'gitdir: /main/.git/worktrees/lc-midrec\n', encoding='utf-8'
    )

    # Precondition: dead by plan-dir absence, yet a live worktree marker exists.
    assert holder_is_dead('lc-midrec') is True
    assert holder_has_live_worktree('lc-midrec') is True
    # Composed verdict: the live worktree wins → fresh.
    assert holder_staleness('lc-midrec') == 'fresh'


def test_holder_staleness_stale_when_dead_and_no_worktree(plan_context):
    # No plan dir on main, no plan dir in a worktree, no live worktree marker →
    # the holder is provably dead → stale (the only force-releasable verdict).
    assert holder_staleness('lc-genuinely-dead') == 'stale'


def test_holder_staleness_stale_for_empty_holder(plan_context):
    # An empty/corrupt holder is dead-by-shape with no worktree → stale, mirroring
    # holder_is_dead('') is True (the corrupt-lock-file-reclaimable intent).
    assert holder_staleness('') == 'stale'


def test_holder_staleness_unknown_when_base_unresolvable(plan_context, monkeypatch):
    # When the main-anchored .plan/local base cannot be resolved, the underlying
    # liveness predicate raises RuntimeError (a real resolution failure, propagated
    # loudly). holder_staleness converts THAT — and only that — into the explicit
    # 'unknown' verdict, NEVER swallowing a resolution failure as 'stale' (ADR-009:
    # absence of evidence fails closed, it is not proof of death).
    def _boom():
        raise RuntimeError('main-anchored base unresolvable')

    monkeypatch.setattr(_mod, '_main_plan_local_base', _boom)

    assert holder_staleness('lc-any-holder') == 'unknown'


# =============================================================================
# _read_json_or_empty — missing / corrupt / non-dict / valid
# =============================================================================


def test_read_json_missing_file_returns_empty(tmp_path):
    missing = tmp_path / 'state.json'

    assert _read_json_or_empty(missing) == {}


def test_read_json_corrupt_content_returns_empty(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text('{not valid json', encoding='utf-8')

    assert _read_json_or_empty(path) == {}


def test_read_json_non_dict_list_returns_empty(tmp_path):
    # A valid-JSON but non-dict top-level shape is also treated as empty so a
    # malformed file cannot corrupt a dict-expecting consumer.
    path = tmp_path / 'state.json'
    path.write_text('[1, 2, 3]', encoding='utf-8')

    assert _read_json_or_empty(path) == {}


def test_read_json_scalar_returns_empty(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text('42', encoding='utf-8')

    assert _read_json_or_empty(path) == {}


def test_read_json_valid_dict_is_returned(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'slots': {'a': 1}}), encoding='utf-8')

    assert _read_json_or_empty(path) == {'slots': {'a': 1}}


# =============================================================================
# _atomic_write_json — round-trip / overwrite / no temp residue
# =============================================================================


def test_atomic_write_round_trips(tmp_path):
    path = tmp_path / 'state.json'

    _atomic_write_json(path, {'held_by': 'plan-x'})

    assert json.loads(path.read_text(encoding='utf-8')) == {'held_by': 'plan-x'}


def test_atomic_write_overwrites_existing(tmp_path):
    path = tmp_path / 'state.json'
    _atomic_write_json(path, {'v': 1})

    _atomic_write_json(path, {'v': 2})

    assert json.loads(path.read_text(encoding='utf-8')) == {'v': 2}
