#!/usr/bin/env python3
"""Regression tests pinning the read-only manage-config contract for phase-2-refine.

These tests demonstrate the failure mode documented in lesson 2026-05-28-23-001:
a refine agent that invokes a mutating manage-config verb (e.g., ``plan
phase-2-refine set --field simplicity --value lean``) writes to the tracked
``.plan/marshal.json``, making the working tree dirty and corrupting
configuration intended for the current plan's marshal state.

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

Both tests run against a synthetic ``tmp_path`` git repository with its own
committed ``.plan/marshal.json``: ``manage-config set`` is invoked with
``cwd`` set to the tmp repo and ``PLAN_BASE_DIR`` pointing into the tmp
repo's ``.plan`` directory, so the mutation lands on the synthetic file and
never touches the real checkout's tracked ``.plan/marshal.json``. This keeps
the tests hermetic (no real-tree pollution, no cross-worker TOCTOU window)
while preserving the exact mutation/recovery contract they pin. Because the
tests no longer touch the real file, they rely on the autouse
``PLAN_BASE_DIR`` sandbox and do NOT opt out via ``allow_pollution``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# conftest.py sets MARKETPLACE_SCRIPT_DIRS and PROJECT_ROOT in sys.path
# so the conftest-exported symbols are available for import.
from conftest import PROJECT_ROOT, create_marshal_json


def _build_env(plan_base_dir: Path) -> dict[str, str]:
    """Build subprocess environment for the synthetic-repo manage-config call.

    Mirrors the PYTHONPATH that the executor sets so manage-config can
    resolve cross-skill imports (``file_ops``, ``_config_core``, etc.), and
    points ``PLAN_BASE_DIR`` at the synthetic repo's ``.plan`` directory so
    ``get_marshal_path()`` resolves to ``{tmp_repo}/.plan/marshal.json`` —
    never the real checkout's tracked file.

    Args:
        plan_base_dir: The synthetic repo's ``.plan`` directory; the value
            ``get_marshal_path()`` resolves against (it appends
            ``marshal.json``).

    Returns:
        A copy of the current environment with PYTHONPATH and PLAN_BASE_DIR
        set for the subprocess.
    """
    env = os.environ.copy()
    # conftest._MARKETPLACE_SCRIPT_DIRS is built by _setup_marketplace_pythonpath()
    # and injected into sys.path; we mirror it here for subprocess calls.
    # Collect the script dirs from sys.path that live inside the marketplace
    # bundles tree.
    marketplace_dirs = [
        d for d in sys.path
        if 'marketplace' in d and 'scripts' in d
    ]
    if marketplace_dirs:
        extra = os.pathsep.join(marketplace_dirs)
        existing = env.get('PYTHONPATH', '')
        env['PYTHONPATH'] = f'{extra}{os.pathsep}{existing}' if existing else extra
    # Redirect marshal.json resolution into the synthetic repo. The autouse
    # sandbox already set PLAN_BASE_DIR to a tmp dir; override it here so the
    # write lands on the committed synthetic file we can assert against.
    env['PLAN_BASE_DIR'] = str(plan_base_dir)
    return env


def _init_synthetic_repo(repo: Path) -> Path:
    """Create a git repo on ``main`` with a committed ``.plan/marshal.json``.

    Mirrors the synthetic-git-repo pattern in
    ``test_manage_status_transition.py::_init_collection_repo``: a fresh
    ``git init`` plus a baseline commit so a subsequent working-tree edit of
    ``.plan/marshal.json`` surfaces under ``git status --porcelain``.

    Args:
        repo: The (empty) directory to initialize as a git repo.

    Returns:
        Absolute path to the committed ``.plan/marshal.json``.
    """
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True, timeout=10)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 't@t.test'], check=True, timeout=10)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True, timeout=10)
    # Seed a schema-valid marshal.json under {repo}/.plan/ and commit it so
    # the file is tracked and clean before the mutation under test.
    marshal_path = create_marshal_json(repo)
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True, timeout=10)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'init'], check=True, timeout=10)
    return marshal_path


def _run_manage_config_set(repo: Path) -> subprocess.CompletedProcess[str]:
    """Invoke the mutating ``manage-config plan phase-2-refine set`` verb.

    Runs the real executor with ``cwd`` set to the synthetic repo and
    ``PLAN_BASE_DIR`` redirected into ``{repo}/.plan`` so the write targets
    the synthetic marshal.json.

    Args:
        repo: The synthetic git repo root.

    Returns:
        The completed subprocess for the ``set`` invocation.
    """
    executor = PROJECT_ROOT / '.plan' / 'execute-script.py'
    return subprocess.run(
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
        cwd=repo,
        env=_build_env(repo / '.plan'),
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_manage_config_set_dirties_marshal_json(tmp_path) -> None:
    """Calling ``manage-config plan phase-2-refine set`` writes to the tracked
    ``.plan/marshal.json`` and produces a dirty working tree.

    This pins the mutation path: the refine agent has access to a mutating
    manage-config verb and accidentally invoking it produces a detectable
    git dirty state — exactly the post-refine orchestrator assertion that
    caught the original regression (lesson 2026-05-28-23-001). Exercised
    against a synthetic tmp_path repo so the real checkout is never touched.

    Arrange: synthetic repo with a committed, clean ``.plan/marshal.json``.
    Act:     invoke ``manage-config plan phase-2-refine set
             --field simplicity --value lean`` against the synthetic repo.
    Assert:  ``git status --porcelain .plan/marshal.json`` reports the file
             as modified.
    """
    marshal_path = _init_synthetic_repo(tmp_path)

    # Arrange — pre-condition: the file must be tracked and clean.
    assert marshal_path.is_file(), (
        f'synthetic marshal.json not found at {marshal_path}'
    )
    pre_status = subprocess.run(
        ['git', 'status', '--porcelain', '.plan/marshal.json'],
        capture_output=True,
        text=True,
        check=True,
        cwd=tmp_path,
        timeout=10,
    )
    assert pre_status.stdout.strip() == '', (
        f'synthetic marshal.json is dirty before the test: {pre_status.stdout.strip()!r}. '
        'The baseline commit in _init_synthetic_repo did not produce a clean tree.'
    )

    # Act — invoke the mutating manage-config verb against the synthetic repo.
    result = _run_manage_config_set(tmp_path)
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
        cwd=tmp_path,
        timeout=10,
    )
    dirty_output = post_status.stdout.strip()
    assert dirty_output != '', (
        'marshal.json was NOT dirtied by manage-config set. '
        'The mutation contract is broken — either the script did not write '
        'to the tracked file, or the PLAN_BASE_DIR redirect did not point '
        'at the synthetic repo.'
    )
    assert '.plan/marshal.json' in dirty_output, (
        f'git status --porcelain output did not reference .plan/marshal.json: '
        f'{dirty_output!r}'
    )


def test_marshal_json_restored_after_checkout(tmp_path) -> None:
    """``git checkout -- .plan/marshal.json`` restores clean working-tree state.

    This pins the recovery path: after the mutation is detected, the
    post-refine orchestrator runs ``git checkout -- .plan/marshal.json`` to
    undo the change. Verifies clean state is restored. Exercised against a
    synthetic tmp_path repo so the real checkout is never touched.

    Arrange: dirty ``marshal.json`` via the same mutating verb as above.
    Act:     run ``git checkout -- .plan/marshal.json`` in the synthetic repo.
    Assert:  ``git status --porcelain .plan/marshal.json`` is empty.
    """
    _init_synthetic_repo(tmp_path)

    # Arrange — dirty the file first (same as test_manage_config_set_dirties_marshal_json).
    set_result = _run_manage_config_set(tmp_path)
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
        cwd=tmp_path,
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
        cwd=tmp_path,
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
        cwd=tmp_path,
        timeout=10,
    )
    assert post_restore_status.stdout.strip() == '', (
        f'marshal.json is still dirty after git checkout --: '
        f'{post_restore_status.stdout.strip()!r}. '
        'The checkout-based recovery mechanism is broken.'
    )
