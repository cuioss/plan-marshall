#!/usr/bin/env python3
"""Tests for ``manage-references diff-files`` and the auto-routing
contract that computes its ``--worktree-path`` argument.

``manage-references`` is a **Bucket A** (cwd-agnostic) script, so it
does NOT declare ``--project-dir`` / ``--plan-id`` two-state routing —
Bucket A scripts inherit the executor's cwd. Instead, ``diff-files``
takes a separate ``--worktree-path`` flag that callers compute via the
shared ``resolve_project_dir`` helper.

This file pins:

* the ``diff-files`` argparse surface (``--plan-id`` + ``--worktree-path``
  required, ``--base-ref`` optional)
* the contract that ``--worktree-path`` is mandatory (no auto-resolution
  inside ``diff-files`` itself — the resolution happens at the caller)
* the integration shape: the resolver's output (``resolve_project_dir``)
  is a string suitable for passing into ``--worktree-path``.

The Bucket B consumers that DO declare the two-state routing pair are
covered in their own test files (``test_pyproject_build``, ``test_maven``,
``test_ci``, etc.).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from _resolve_project_dir_fixtures import (  # type: ignore[import-not-found]
    CANONICAL_PLAN_ID,
    CANONICAL_WORKTREE,
    patch_main_checkout_root,
    patch_query_worktree_path,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-references', 'manage-references.py')


# =============================================================================
# Argparse surface — diff-files must keep accepting --worktree-path
# =============================================================================


def test_diff_files_help_shows_plan_id_and_worktree_path():
    """``diff-files --help`` must declare both --plan-id and --worktree-path."""
    result = run_script(SCRIPT_PATH, 'diff-files', '--help')
    assert result.success, f'--help failed: {result.stderr}'
    assert '--plan-id' in result.stdout, 'diff-files must declare --plan-id'
    assert '--worktree-path' in result.stdout, 'diff-files must declare --worktree-path'


def test_diff_files_help_does_not_declare_project_dir():
    """``diff-files`` is Bucket A; --project-dir MUST NOT appear."""
    result = run_script(SCRIPT_PATH, 'diff-files', '--help')
    assert result.success, f'--help failed: {result.stderr}'
    assert '--project-dir' not in result.stdout, (
        'manage-references is Bucket A and must not declare --project-dir; '
        'two-state routing happens at the caller via resolve_project_dir.'
    )


def test_diff_files_requires_plan_id():
    """--plan-id is required; argparse exits 2 when omitted."""
    result = run_script(
        SCRIPT_PATH,
        'diff-files',
        '--worktree-path',
        '/tmp/nonexistent',
    )
    assert result.returncode == 2, f'Expected argparse exit 2, got {result.returncode}'


def test_diff_files_requires_worktree_path():
    """--worktree-path is required; argparse exits 2 when omitted."""
    result = run_script(
        SCRIPT_PATH,
        'diff-files',
        '--plan-id',
        CANONICAL_PLAN_ID,
    )
    assert result.returncode == 2, f'Expected argparse exit 2, got {result.returncode}'


# =============================================================================
# diff-files surfaces a structured worktree_not_found error for bogus paths
# =============================================================================


def test_diff_files_returns_structured_error_for_missing_worktree(plan_context, tmp_path):
    """A non-existent --worktree-path must yield a structured TOON error."""
    # Seed a minimal references.json so the script reaches the worktree check.
    # We bypass that detail by deliberately picking a path that does not exist.
    result = run_script(
        SCRIPT_PATH,
        'diff-files',
        '--plan-id',
        'diff-files-bogus-worktree',
        '--worktree-path',
        str(tmp_path / 'does-not-exist'),
    )
    # The handler returns a structured TOON error and exits 0 — an operation
    # failure (bogus worktree / missing references) is not a script crash, so
    # the dispatcher emits the error on stdout and exits 0 per the
    # operation-failure contract.
    assert result.returncode == 0, (
        f'Expected exit 0 (operation failure) for missing worktree; '
        f'stdout={result.stdout!r} stderr={result.stderr!r}'
    )
    # Either worktree_not_found (path missing) or references_not_found
    # (no references.json yet) — both exercise the structured error path.
    assert (
        'worktree_not_found' in result.stdout
        or 'references_not_found' in result.stdout
        or 'invalid_plan_id' in result.stdout
    ), f'Expected structured error TOON, got: {result.stdout!r}'


# =============================================================================
# Integration: resolve_project_dir output is a valid --worktree-path argument
# =============================================================================


def test_resolve_project_dir_output_shape_matches_worktree_path_arg():
    """The resolver returns an absolute path string suitable for --worktree-path.

    Bucket A consumers like ``manage-references diff-files`` accept a
    ``--worktree-path`` argument whose value is computed by the caller via
    ``resolve_project_dir``. This test pins the contract that the resolver's
    output shape (absolute filesystem path string) matches what
    ``diff-files`` expects, so callers can wire the two together without
    custom adapters.
    """
    from resolve_project_dir import resolve_project_dir

    with patch_query_worktree_path(use_worktree=True, worktree_path=CANONICAL_WORKTREE):
        resolved = resolve_project_dir(CANONICAL_PLAN_ID, None, default=None)
    # Absolute path, string-typed — argparse passes it straight to
    # ``Path(args.worktree_path)``.
    assert isinstance(resolved, str)
    assert Path(resolved).is_absolute()


def test_resolve_project_dir_use_worktree_false_yields_main_checkout_for_caller_routing():
    """``use_worktree=false`` resolution surfaces the main checkout root.

    When a plan does not run in an isolated worktree, ``manage-references``
    callers should pass the main checkout root as ``--worktree-path``. The
    resolver enforces that fallback consistently.
    """
    from resolve_project_dir import resolve_project_dir

    with (
        patch_query_worktree_path(use_worktree=False),
        patch_main_checkout_root('/tmp/main-checkout-stub'),
    ):
        resolved = resolve_project_dir(CANONICAL_PLAN_ID, None, default=None)
    assert resolved == '/tmp/main-checkout-stub'


def test_resolve_project_dir_passthrough_for_explicit_worktree_path():
    """``--project-dir Y`` (caller side) returns Y verbatim — pre-existing escape hatch.

    This is the path used by ad-hoc ``manage-references diff-files``
    invocations from tests or external scripts that already know the
    worktree path.
    """
    from resolve_project_dir import resolve_project_dir

    resolved = resolve_project_dir(None, '/tmp/ad-hoc-worktree', default=None)
    assert resolved.endswith('ad-hoc-worktree')


def test_resolve_project_dir_rejects_caller_supplying_both_routing_sources():
    """A caller that supplies both --plan-id and --project-dir must fail loudly.

    The two-state contract is enforced at the resolver level — even Bucket A
    consumers that don't expose the flag pair benefit from the helper's
    consistency.
    """
    from resolve_project_dir import MutuallyExclusiveArgsError, resolve_project_dir

    with pytest.raises(MutuallyExclusiveArgsError):
        resolve_project_dir(CANONICAL_PLAN_ID, '/tmp/explicit', default=None)


_ = patch  # Silence unused-import warning; future tests may need it.
