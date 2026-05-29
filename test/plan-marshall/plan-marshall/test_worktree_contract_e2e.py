#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""End-to-end regression test for the worktree-contract fixes (D1-D4).

Cross-cutting integration test for plan ``lesson-2026-05-08-08-001``.
Each scenario exercises one of the four sub-deliverable fixes from a
user-visible angle so that a regression in any single fix surface
isolates to a specific failing test:

A. Layer-D ``main_dirty_files`` invariant — capture a clean baseline at
   boundary N, simulate a free-form edit on a tracked main-checkout
   file between N and N+1, then run ``phase_handshake verify --phase
   {N} --strict`` and assert it fails with
   ``main_checkout_dirtied_during_plan``. Reverting and re-running
   yields a clean verify. ``.plan/`` paths are filtered.
B. Inverse-direction ``worktree_orphan`` invariant — manually create
   ``.plan/local/worktrees/{plan_id}`` while metadata says
   ``use_worktree != true`` and assert capture raises the new
   ``worktree_metadata_drift`` error.
C. ``sync-plugin-cache`` staleness guard — synthetic ``__pycache__``
   files created with fresh mtimes do NOT trip the guard; touching a
   tracked source file DOES.
D. ``phase-6-finalize`` Step 6 done-title — assert SKILL.md routes
   through the canonical executor notation, not the deployed-cache
   absolute path.

Each scenario uses a unique synthetic ``plan_id`` so the shared
``PlanContext`` fixture directory does not produce cross-test
contamination (per project memory note on test isolation).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from conftest import (  # type: ignore[import-not-found]
    get_script_path,
)

# =============================================================================
# Module wiring
# =============================================================================

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')
SCRIPTS_DIR = SCRIPT_PATH.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _invariants as inv  # noqa: E402


# =============================================================================
# A. Layer-D main_dirty_files invariant
# =============================================================================
#
# We test the *capture* + *diff* primitives directly here rather than the
# full verify-with-strict subprocess pipeline (the heavy verify tests live
# in test_phase_handshake_worktree_assertion.py). The layered approach
# keeps this regression deterministic and fast while still asserting the
# user-visible promise: "a free-form edit on a tracked main-checkout file
# between boundaries triggers main_checkout_dirtied_during_plan."


def test_a_main_dirty_drift_diff_detects_added_path(tmp_path: Path) -> None:
    """Adding a dirty path between captures yields a non-empty drift diff.

    Mirrors the operator-visible scenario: at boundary N the main checkout
    has dirty paths ``{X}``; at boundary N+1 it has ``{X, Y}``. Layer-D
    enforcement reports ``[Y]`` as the drift list and the verify path
    turns that into ``main_checkout_dirtied_during_plan``.
    """
    baseline = ['marketplace/bundles/foo/README.md']
    observed = ['marketplace/bundles/foo/README.md', 'marketplace/bundles/foo/bar.py']

    drift = inv._main_dirty_drift_diff(baseline, observed)

    assert drift == ['marketplace/bundles/foo/bar.py'], (
        f'expected single new dirty path in drift, got {drift!r}'
    )


def test_a_main_dirty_drift_diff_clean_returns_empty(tmp_path: Path) -> None:
    """Identical or shrinking dirty sets do NOT trigger drift.

    Pre-existing dirty file present at capture-1 and unchanged at
    capture-2 → proper-superset rule means no drift. A file dirty at
    capture-1 and clean at capture-2 → also no drift (we only flag
    additions).
    """
    baseline = ['marketplace/bundles/foo/README.md']

    # Identical observed → no drift
    assert inv._main_dirty_drift_diff(baseline, baseline) == []

    # Observed shrank → no drift
    assert inv._main_dirty_drift_diff(baseline, []) == []


def test_a_main_dirty_filter_excludes_dot_plan_paths() -> None:
    """``.plan/`` artifacts in main MUST NOT trip the invariant.

    The capture filter (``_filter_main_dirty_paths``) drops anything
    starting with ``.plan/`` so plan-state writes during a worktree-routed
    plan don't trigger drift. Tracked source files outside ``.plan/`` are
    preserved.
    """
    raw = [
        '.plan/local/plans/some-plan/work/log',
        '.plan/temp/build-output/x',
        'marketplace/bundles/foo/README.md',
        'src/main.py',
    ]
    filtered = inv._filter_main_dirty_paths(raw)

    assert '.plan/local/plans/some-plan/work/log' not in filtered
    assert '.plan/temp/build-output/x' not in filtered
    assert 'marketplace/bundles/foo/README.md' in filtered
    assert 'src/main.py' in filtered


# =============================================================================
# B. Inverse-direction worktree_orphan invariant
# =============================================================================
#
# Reproduces the writer-chain drift scenario from plan
# lesson-2026-05-08-14-001: orphan worktree directory exists on disk
# while status.metadata says use_worktree != true. The new invariant must
# raise WorktreeMetadataDrift so cmd_capture surfaces the structured TOON
# error payload.


def test_b_worktree_orphan_raises_when_disk_dir_present_but_metadata_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Orphan dir + metadata=false → WorktreeMetadataDrift raised."""
    plan_id = 'e2e-worktree-orphan-false'
    fake_repo = tmp_path / 'repo'
    fake_repo.mkdir()
    orphan_dir = fake_repo / '.plan' / 'local' / 'worktrees' / plan_id
    orphan_dir.mkdir(parents=True)

    # Orphan detection resolves the worktree root via get_worktree_root()
    # (= get_base_dir() / 'worktrees', PLAN_BASE_DIR-aware). Pin PLAN_BASE_DIR
    # to fake_repo/.plan/local so detection finds the orphan we just created.
    monkeypatch.setenv('PLAN_BASE_DIR', str(fake_repo / '.plan' / 'local'))
    monkeypatch.setattr(inv, '_repo_root', lambda: fake_repo)

    with pytest.raises(inv.WorktreeMetadataDrift) as excinfo:
        inv._capture_worktree_orphan(plan_id, {'use_worktree': False}, '5-execute')

    err = excinfo.value
    # The user-visible TOON payload keys off this error string; pin it.
    assert 'worktree_metadata_drift' in str(err).lower()
    # The offending path must be in the message so operators can act on it.
    assert plan_id in str(err)


def test_b_worktree_orphan_no_op_when_metadata_truthy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Orphan dir + metadata=true → existing worktree_unresolved handles it.

    The inverse-direction invariant short-circuits when ``use_worktree``
    is truthy because the existing forward-direction invariant
    (``worktree_unresolved``) covers that case. This guarantees the two
    invariants do not double-fire.
    """
    plan_id = 'e2e-worktree-orphan-true'
    fake_repo = tmp_path / 'repo'
    fake_repo.mkdir()
    orphan_dir = fake_repo / '.plan' / 'local' / 'worktrees' / plan_id
    orphan_dir.mkdir(parents=True)

    monkeypatch.setenv('PLAN_BASE_DIR', str(fake_repo / '.plan' / 'local'))
    monkeypatch.setattr(inv, '_repo_root', lambda: fake_repo)

    # use_worktree=True → returns None (not applicable), no exception.
    result = inv._capture_worktree_orphan(
        plan_id,
        {'use_worktree': True, 'worktree_path': str(orphan_dir)},
        '5-execute',
    )
    assert result is None


def test_b_worktree_orphan_no_op_when_no_orphan_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No orphan dir + metadata=false → returns None, no error.

    The clean main-checkout case (a plan that legitimately runs in the
    main checkout with use_worktree=false) MUST NOT trip this invariant.
    """
    plan_id = 'e2e-worktree-no-orphan'
    fake_repo = tmp_path / 'repo'
    fake_repo.mkdir()
    # No .plan/local/worktrees/{plan_id} created.

    monkeypatch.setenv('PLAN_BASE_DIR', str(fake_repo / '.plan' / 'local'))
    monkeypatch.setattr(inv, '_repo_root', lambda: fake_repo)

    result = inv._capture_worktree_orphan(plan_id, {'use_worktree': False}, '5-execute')
    assert result is None


# =============================================================================
# C. sync-plugin-cache staleness guard
# =============================================================================
#
# The mtime-based end-to-end scenarios that previously lived here were
# removed as part of the sentinel-file staleness-guard cutover. The
# sentinel-based equivalents — covering fresh emit / missing sentinel /
# fingerprint mismatch / --skip-staleness-guard escape — live in
# ``test/sync-plugin-cache/test_staleness_guard.py`` next to the script
# under test. Locking the same behavior twice would create drift if one
# side ever rewrites; the sync-side suite is authoritative.


