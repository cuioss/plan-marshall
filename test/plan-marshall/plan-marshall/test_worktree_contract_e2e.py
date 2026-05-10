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

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
from conftest import (  # type: ignore[import-not-found]
    PROJECT_ROOT,
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

_SYNC_PY = PROJECT_ROOT / '.claude' / 'skills' / 'sync-plugin-cache' / 'scripts' / 'sync.py'
_PHASE_6_SKILL = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'SKILL.md'
)


# =============================================================================
# Helpers
# =============================================================================


def _set_mtime(path: Path, mtime: float) -> None:
    os.utime(path, (mtime, mtime))


def _write(path: Path, content: str = '') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


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

    monkeypatch.setattr(inv, '_repo_root', lambda: fake_repo)

    result = inv._capture_worktree_orphan(plan_id, {'use_worktree': False}, '5-execute')
    assert result is None


# =============================================================================
# C. sync-plugin-cache staleness guard
# =============================================================================
#
# End-to-end scenario: drive sync.py via subprocess on a synthetic project
# tree, then assert the rewritten staleness walk ignores transient
# artifacts but trips on tracked source-file drift.


def _make_marketplace(cwd: Path, bundles: dict[str, str]) -> None:
    for name, version in bundles.items():
        plugin_doc = json.dumps({'name': name, 'version': version}, indent=2) + '\n'
        _write(
            cwd / 'marketplace' / 'bundles' / name / '.claude-plugin' / 'plugin.json',
            plugin_doc,
        )
        _write(cwd / 'marketplace' / 'bundles' / name / 'README.md', f'# {name}\n')


def _make_target(cwd: Path, bundles: dict[str, str]) -> None:
    for name, version in bundles.items():
        plugin_doc = json.dumps({'name': name, 'version': version}, indent=2) + '\n'
        _write(
            cwd / 'target' / 'claude' / name / '.claude-plugin' / 'plugin.json',
            plugin_doc,
        )
        _write(cwd / 'target' / 'claude' / name / 'README.md', f'# {name}\n')


def _git_init(cwd: Path) -> None:
    subprocess.run(['git', 'init', '-q'], cwd=cwd, check=True)
    subprocess.run(['git', 'config', 'user.email', 't@t.test'], cwd=cwd, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=cwd, check=True)
    subprocess.run(['git', 'config', 'commit.gpgsign', 'false'], cwd=cwd, check=True)
    subprocess.run(['git', 'add', '-A'], cwd=cwd, check=True)
    subprocess.run(['git', 'commit', '-q', '-m', 'init'], cwd=cwd, check=True)


def _run_sync(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SYNC_PY), *args],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=cwd,
    )


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_c_staleness_guard_ignores_transient_pycache(tmp_path: Path) -> None:
    """Pytest-style ``__pycache__/*.pyc`` newer than target MUST NOT trip the guard.

    Reproduces the original failure mode: an operator runs ``pytest`` then
    ``/sync-plugin-cache`` and the guard refused even though no source
    drift occurred. The fix filters via the git-ignored probe AND the
    transient denylist; this regression locks both paths in.
    """
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _write(cwd / '.gitignore', '__pycache__/\n*.pyc\n')
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _make_target(cwd, {'demo': '0.1.0'})
    _git_init(cwd)

    old = time.time() - 86400
    new = time.time()
    for path in (cwd / 'marketplace').rglob('*'):
        if path.is_file():
            _set_mtime(path, old)
    for path in (cwd / 'target').rglob('*'):
        if path.is_file():
            _set_mtime(path, new)

    # Drop a fresh .pyc inside __pycache__/.
    pyc = cwd / 'marketplace' / 'bundles' / 'demo' / '__pycache__' / 'demo.cpython-311.pyc'
    _write(pyc, 'fake bytecode')
    _set_mtime(pyc, new + 60)

    cache = tmp_path / 'cache'
    result = _run_sync('--cache-root', str(cache), cwd=cwd)
    assert result.returncode == 0, (
        f'guard tripped on transient artifact (rc={result.returncode}): {result.stdout}'
    )


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_c_staleness_guard_trips_on_tracked_source_drift(tmp_path: Path) -> None:
    """Tracked ``.md`` source newer than target MUST trip the guard.

    Belt-and-suspenders: filtering must NOT mask legitimate source-file
    edits. Operators expect the staleness guard to refuse so they
    regenerate before sync.
    """
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _write(cwd / '.gitignore', '__pycache__/\n*.pyc\n')
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _make_target(cwd, {'demo': '0.1.0'})
    _git_init(cwd)

    old = time.time() - 86400
    new = time.time()
    for path in (cwd / 'target').rglob('*'):
        if path.is_file():
            _set_mtime(path, old)
    # Tracked source file gets a fresh mtime → drift.
    tracked = cwd / 'marketplace' / 'bundles' / 'demo' / 'README.md'
    _set_mtime(tracked, new)

    result = _run_sync(cwd=cwd)
    assert result.returncode == 2, (
        f'guard failed to trip on tracked source change (rc={result.returncode}): {result.stdout}'
    )


# =============================================================================
# D. phase-6-finalize Step 6 done-title path routing
# =============================================================================
#
# The deliverable replaced the hard-coded source-tree path with the
# canonical executor notation. We assert the SKILL.md no longer
# references the old path and DOES reference the new one.


def test_d_phase_6_step_6_uses_executor_notation_for_done_title() -> None:
    """phase-6-finalize Step 6 invokes set_terminal_title via executor notation.

    The previous form ``python3 ~/.claude/plugins/cache/.../set_terminal_title.py``
    referenced the source-tree layout that does not exist in the deployed
    cache and silently failed with ``Errno 2``. The fix routes the call
    through ``.plan/execute-script.py
    plan-marshall:plan-marshall:set_terminal_title`` so the executor mapping
    resolves the deployed cache path at generation time.
    """
    body = _PHASE_6_SKILL.read_text(encoding='utf-8')

    canonical = (
        'python3 .plan/execute-script.py plan-marshall:plan-marshall:set_terminal_title '
        'done --plan-label'
    )
    assert canonical in body, (
        f'Expected canonical executor notation for set_terminal_title in '
        f'{_PHASE_6_SKILL.relative_to(PROJECT_ROOT)} but did not find it. '
        f'Step 6 must route through .plan/execute-script.py, not a hard-coded '
        f'source-tree path.'
    )

    # The defunct source-tree path MUST NOT appear in skill prose. The
    # cache-relative form (``~/.claude/plugins/cache/...``) is still
    # legitimate inside settings.json hook configuration written by
    # /marshall-steward — we narrow the assertion to the source-tree
    # ``marketplace/bundles/...`` shape which never resolved in the
    # deployed cache.
    forbidden = (
        '~/.claude/plugins/cache/plan-marshall/marketplace/bundles/'
        'plan-marshall/skills/plan-marshall/scripts/set_terminal_title.py'
    )
    assert forbidden not in body, (
        f'Defunct source-tree path still present in '
        f'{_PHASE_6_SKILL.relative_to(PROJECT_ROOT)}: {forbidden!r}. '
        f'Replace with the canonical executor notation.'
    )
