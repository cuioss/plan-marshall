#!/usr/bin/env python3
"""Regression tests pinning the read-only manage-config contract for phase-2-refine.

These tests demonstrate the failure mode documented in lesson 2026-05-28-23-001:
a refine agent that invokes a mutating manage-config verb (e.g., ``plan
phase-2-refine set --field simplicity --value lean``) writes to the tracked
``.plan/marshal.json`` in the main git checkout, making it dirty and
corrupting configuration intended for the current plan's marshal state.

The post-refine orchestrator catches this via ``git status --porcelain``.
These tests pin both the mutation detection path and the recovery path so
a future regression is caught before it reaches code review.

Two test cases:

1. ``test_manage_config_set_dirties_marshal_json`` — calling
   ``manage-config plan phase-2-refine set --field simplicity --value lean``
   via subprocess produces a dirty ``.plan/marshal.json`` detectable by
   ``git status --porcelain``.

2. ``test_marshal_json_restored_after_checkout`` — ``git checkout --
   .plan/marshal.json`` restores clean state after the mutation.

These tests run against the real repository's tracked ``.plan/marshal.json``
file (not an isolated fixture) because the mutation only surfaces through the
git working-tree tracking mechanism. They are self-restoring: each test
performs cleanup via ``git checkout --`` so subsequent runs and other tests
are not affected by any leftover dirty state.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

# conftest.py sets MARKETPLACE_SCRIPT_DIRS and PROJECT_ROOT in sys.path
# so the conftest-exported symbol is available for import.
from conftest import PROJECT_ROOT


def _resolve_main_checkout_root() -> Path:
    """Return the main git checkout root, worktree-safe.

    Uses ``git rev-parse --path-format=absolute --git-common-dir`` (same
    strategy as ``marketplace_paths.git_main_checkout_root()``) so that
    tests run from a worktree still point at the shared ``.plan/marshal.json``
    in the primary working tree — the exact file that a phase-2-refine agent
    subprocess would mutate.

    Returns:
        Absolute path to the main checkout root.

    Raises:
        RuntimeError: If git is unavailable or not inside a repo.
    """
    result = subprocess.run(
        ['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'],
        capture_output=True,
        text=True,
        check=True,
        cwd=PROJECT_ROOT,
        timeout=10,
    )
    common_dir = result.stdout.strip()
    if not common_dir:
        raise RuntimeError('git rev-parse --git-common-dir returned empty output')
    return Path(common_dir).parent


def _build_env() -> dict[str, str]:
    """Build subprocess environment with PYTHONPATH for marketplace scripts.

    Mirrors the PYTHONPATH that the executor sets so manage-config can
    resolve cross-skill imports (``file_ops``, ``_config_core``, etc.).
    """
    # conftest._MARKETPLACE_SCRIPT_DIRS is built by _setup_marketplace_pythonpath()
    # and injected into sys.path; we mirror it here for subprocess calls.
    env = os.environ.copy()
    # Filter sys.path entries that live inside the marketplace bundles tree,
    # since conftest already added them. For robustness, collect the script
    # dirs from sys.path that contain a parent named 'scripts'.
    marketplace_dirs = [
        d for d in sys.path
        if 'marketplace' in d and 'scripts' in d
    ]
    if marketplace_dirs:
        extra = os.pathsep.join(marketplace_dirs)
        existing = env.get('PYTHONPATH', '')
        env['PYTHONPATH'] = f'{extra}{os.pathsep}{existing}' if existing else extra
    return env


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _restore_marshal_json():
    """Ensure ``.plan/marshal.json`` is restored to its pre-test git-committed
    state after each test in this module.

    Uses ``git checkout -- .plan/marshal.json`` (the same recovery command
    the post-refine orchestrator applies) so the restore path is itself
    exercised. This fixture runs for all tests in this module via
    ``autouse=True`` — it is the safety net that makes the tests safe to
    run repeatedly without manual cleanup.

    The restore is applied to **both** the git-common-dir checkout root and
    ``PROJECT_ROOT``. When the suite runs inside a git worktree these two
    paths diverge: the worktree owns an independent checked-out copy of the
    tracked ``.plan/marshal.json``, while ``--git-common-dir`` resolves to
    the primary checkout. Restoring only one tree leaves the other polluted —
    the exact failure mode lesson 2026-05-28-23-001 guards against. Restoring
    both (a no-op when they coincide, as in CI's plain checkout) keeps the
    test hermetic regardless of execution model.

    Restoration is done after ``yield`` so test failures do not leave the
    working tree dirty for subsequent tests or CI runs.
    """
    main_root = _resolve_main_checkout_root()
    yield
    # Always restore — even if the test itself never dirtied the file.
    # ``git checkout --`` on an already-clean file is a no-op. Restore both
    # the common-dir root and PROJECT_ROOT so a worktree run cannot leave
    # either checkout's copy dirty (the two paths coincide outside worktrees).
    seen: set[Path] = set()
    for root in (main_root, PROJECT_ROOT):
        resolved = root.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        subprocess.run(
            ['git', 'checkout', '--', '.plan/marshal.json'],
            cwd=root,
            capture_output=True,
            check=False,  # Non-fatal: if restoration fails, subsequent tests will detect via pollution guard.
            timeout=10,
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_manage_config_set_dirties_marshal_json() -> None:
    """Calling ``manage-config plan phase-2-refine set`` writes to tracked
    ``.plan/marshal.json`` and produces a dirty working tree.

    This pins the mutation path: the refine agent has access to a mutating
    manage-config verb and accidentally invoking it produces a detectable
    git dirty state — exactly the post-refine orchestrator assertion that
    caught the original regression (lesson 2026-05-28-23-001).

    Arrange: confirm ``marshal.json`` is clean before the call.
    Act:     invoke ``manage-config plan phase-2-refine set
             --field simplicity --value lean`` via subprocess.
    Assert:  ``git status --porcelain .plan/marshal.json`` reports the file
             as modified (`` M .plan/marshal.json``).
    """
    main_root = _resolve_main_checkout_root()
    marshal_path = main_root / '.plan' / 'marshal.json'

    # Arrange — pre-condition: the file must be tracked and clean.
    assert marshal_path.is_file(), (
        f'marshal.json not found at {marshal_path}. '
        'The test requires a fully-initialized repository with marshal.json tracked.'
    )
    pre_status = subprocess.run(
        ['git', 'status', '--porcelain', '.plan/marshal.json'],
        capture_output=True,
        text=True,
        check=True,
        cwd=main_root,
        timeout=10,
    )
    assert pre_status.stdout.strip() == '', (
        f'marshal.json is already dirty before the test: {pre_status.stdout.strip()!r}. '
        'A prior test may not have restored it. Run: '
        'git checkout -- .plan/marshal.json'
    )

    # Act — invoke the mutating manage-config verb via the executor.
    executor = PROJECT_ROOT / '.plan' / 'execute-script.py'
    result = subprocess.run(
        [
            sys.executable,
            str(executor),
            'plan-marshall:manage-config:manage-config',
            'plan',
            'phase-2-refine',
            'set',
            '--field',
            'simplicity',
            '--value',
            'lean',
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env=_build_env(),
        timeout=30,
    )
    assert result.returncode == 0, (
        f'manage-config set exited with code {result.returncode}.\n'
        f'stdout: {result.stdout}\nstderr: {result.stderr}'
    )

    # Assert — the tracked file must now be dirty.
    post_status = subprocess.run(
        ['git', 'status', '--porcelain', '.plan/marshal.json'],
        capture_output=True,
        text=True,
        check=True,
        cwd=main_root,
        timeout=10,
    )
    dirty_output = post_status.stdout.strip()
    assert dirty_output != '', (
        'marshal.json was NOT dirtied by manage-config set. '
        'The mutation contract is broken — either the script did not write '
        'to the tracked file, or the PLAN_BASE_DIR override was active '
        'and redirected the write to a fixture directory.'
    )
    assert '.plan/marshal.json' in dirty_output, (
        f'git status --porcelain output did not reference .plan/marshal.json: '
        f'{dirty_output!r}'
    )


def test_marshal_json_restored_after_checkout() -> None:
    """``git checkout -- .plan/marshal.json`` restores clean working-tree state.

    This pins the recovery path: after the mutation is detected, the
    post-refine orchestrator runs ``git checkout -- .plan/marshal.json`` to
    undo the change. Verifies clean state is restored.

    Arrange: dirty ``marshal.json`` via the same mutating verb as above.
    Act:     run ``git checkout -- .plan/marshal.json``.
    Assert:  ``git status --porcelain .plan/marshal.json`` is empty.
    """
    main_root = _resolve_main_checkout_root()

    # Arrange — dirty the file first (same as test_manage_config_set_dirties_marshal_json).
    executor = PROJECT_ROOT / '.plan' / 'execute-script.py'
    set_result = subprocess.run(
        [
            sys.executable,
            str(executor),
            'plan-marshall:manage-config:manage-config',
            'plan',
            'phase-2-refine',
            'set',
            '--field',
            'simplicity',
            '--value',
            'lean',
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env=_build_env(),
        timeout=30,
    )
    assert set_result.returncode == 0, (
        f'Arrange step failed — manage-config set returned code {set_result.returncode}.\n'
        f'stdout: {set_result.stdout}\nstderr: {set_result.stderr}'
    )

    # Confirm dirty before restore.
    pre_restore_status = subprocess.run(
        ['git', 'status', '--porcelain', '.plan/marshal.json'],
        capture_output=True,
        text=True,
        check=True,
        cwd=main_root,
        timeout=10,
    )
    assert pre_restore_status.stdout.strip() != '', (
        'marshal.json was not dirty after the arrange step — cannot test the restore path.'
    )

    # Act — run the orchestrator recovery command.
    checkout_result = subprocess.run(
        ['git', 'checkout', '--', '.plan/marshal.json'],
        capture_output=True,
        text=True,
        check=True,
        cwd=main_root,
        timeout=10,
    )
    assert checkout_result.returncode == 0, (
        f'git checkout -- .plan/marshal.json failed: {checkout_result.stderr}'
    )

    # Assert — clean state must be restored.
    post_restore_status = subprocess.run(
        ['git', 'status', '--porcelain', '.plan/marshal.json'],
        capture_output=True,
        text=True,
        check=True,
        cwd=main_root,
        timeout=10,
    )
    assert post_restore_status.stdout.strip() == '', (
        f'marshal.json is still dirty after git checkout --: '
        f'{post_restore_status.stdout.strip()!r}. '
        'The checkout-based recovery mechanism is broken.'
    )
