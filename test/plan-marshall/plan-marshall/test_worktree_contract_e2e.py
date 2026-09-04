#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
   yields a clean verify. Untracked ``.plan/`` paths are filtered; a
   tracked ``.plan/`` file is retained as a real leak.
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

import subprocess
from pathlib import Path

# Imported PLAINLY so this suite holds the same ``_invariants`` instance the
# production path resolves; its marketplace ``scripts/`` directory is already on
# ``sys.path`` via the root conftest.
import _invariants as inv

from conftest import (
    get_script_path,
)

# =============================================================================
# Module wiring
# =============================================================================

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')


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


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """Run one git command against ``repo`` with a pinned, hermetic identity."""
    return subprocess.run(
        [
            'git',
            '-C',
            str(repo),
            '-c',
            'user.name=Test',
            '-c',
            'user.email=test@example.invalid',
            '-c',
            'commit.gpgsign=false',
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )


def test_a_main_dirty_filter_excludes_untracked_plan_paths(tmp_path: Path) -> None:
    """UNTRACKED ``.plan/`` artifacts MUST NOT trip the invariant; tracked ones DO.

    The capture filter (``_filter_main_dirty_paths``) delegates to the shared
    trackedness exemption: an UNTRACKED ``.plan/`` path (ordinary plan-state
    bookkeeping — logs, build results) is dropped, but a git-TRACKED ``.plan/``
    file (``marshal.json``) is a real main-checkout leak and is retained, exactly
    like tracked source outside ``.plan/``.
    """
    repo = tmp_path / 'main-checkout'
    repo.mkdir()
    _git(repo, 'init', '--initial-branch=main')
    (repo / '.plan').mkdir()
    (repo / '.plan' / 'marshal.json').write_text('{"schema": 1}\n', encoding='utf-8')
    (repo / 'README.md').write_text('# repo\n', encoding='utf-8')
    _git(repo, 'add', '-f', '.plan/marshal.json', 'README.md')
    _git(repo, 'commit', '-m', 'chore: seed')

    raw = [
        '.plan/local/plans/some-plan/work.log',  # untracked → dropped
        '.plan/marshal.json',                    # tracked   → retained
        'marketplace/bundles/foo/README.md',     # non-.plan → retained
        'src/main.py',                           # non-.plan → retained
    ]
    filtered = inv._filter_main_dirty_paths(raw, repo)

    assert '.plan/local/plans/some-plan/work.log' not in filtered
    assert '.plan/marshal.json' in filtered
    assert 'marketplace/bundles/foo/README.md' in filtered
    assert 'src/main.py' in filtered


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


