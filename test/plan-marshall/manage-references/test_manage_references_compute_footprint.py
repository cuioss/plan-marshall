#!/usr/bin/env python3
"""Tests for ``manage-references compute-footprint`` and the auto-routing
contract that computes its ``--worktree-path`` argument.

``compute-footprint`` derives the plan's actual footprint live from the
worktree git state — the union of the three-dot ``{base_ref}...HEAD`` diff
and the porcelain working-tree state — without consulting any persisted
ledger. The worktree is the single source of truth.

``manage-references`` is a **Bucket A** (cwd-agnostic) script, so it
does NOT declare ``--project-dir`` / ``--plan-id`` two-state routing —
Bucket A scripts inherit the executor's cwd. Instead, ``compute-footprint``
takes a separate ``--worktree-path`` flag that callers compute via the
shared ``resolve_project_dir`` helper.

This file pins:

* the ``compute-footprint`` argparse surface (``--plan-id`` + ``--worktree-path``
  required, ``--base-ref`` optional)
* the live-footprint contract: ``files`` equals the live
  ``{base}...HEAD`` ∪ porcelain set, with NO ledger-intersection /
  ``dropped`` / ``phantom`` / ``references_count`` drift-accounting fields
* the read-only invariant: ``compute-footprint`` never mutates references.json
* the shared error contract (``worktree_not_found``, ``references_not_found``,
  ``not_a_git_worktree``)
* the integration shape: the resolver's output (``resolve_project_dir``)
  is a string suitable for passing into ``--worktree-path``.

The Bucket B consumers that DO declare the two-state routing pair are
covered in their own test files (``test_pyproject_build``, ``test_maven``,
``test_ci``, etc.).
"""

from __future__ import annotations

import json
import subprocess
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

FOOTPRINT_PLAN_ID = 'compute-footprint-plan'


# =============================================================================
# Git fixture helpers
# =============================================================================


def _git(repo: Path, *args: str) -> str:
    """Run a git command in ``repo`` and return stdout (raising on failure)."""
    proc = subprocess.run(
        ['git', '-C', str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _init_repo(repo: Path) -> None:
    """Initialize a git repo with deterministic identity and a main branch."""
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, 'init', '--initial-branch=main')
    _git(repo, 'config', 'user.email', 'test@example.com')
    _git(repo, 'config', 'user.name', 'Test User')


def _commit(repo: Path, message: str, files: dict[str, str]) -> str:
    """Write ``files`` (rel path -> content), stage, commit, return the sha."""
    for rel, content in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    _git(repo, 'add', '-A')
    _git(repo, 'commit', '-m', message)
    return _git(repo, 'rev-parse', 'HEAD').strip()


def _build_absorb_scenario(repo: Path) -> None:
    """Construct a repo where the feature branch contains both a genuine plan
    change AND an absorbed-upstream commit.

    Layout:
        main:    base.txt
        feature: branches from main, adds plan_change.py (genuine plan work)
        main:    advances with upstream_only.py (a file the plan never touched)
        feature: merges main into itself (absorb) — now HEAD contains
                 upstream_only.py at/above the merge-base, but the three-dot
                 ``main...HEAD`` diff excludes it.
    """
    _init_repo(repo)
    _commit(repo, 'base', {'base.txt': 'base\n'})

    # Feature branch: genuine plan change.
    _git(repo, 'checkout', '-b', 'feature')
    _commit(repo, 'plan change', {'plan_change.py': 'print("plan")\n'})

    # Upstream advances on main with a file disjoint from the plan.
    _git(repo, 'checkout', 'main')
    _commit(repo, 'upstream only', {'upstream_only.py': 'print("upstream")\n'})

    # Absorb: merge main into feature. HEAD now contains upstream_only.py.
    _git(repo, 'checkout', 'feature')
    _git(repo, 'merge', 'main', '--no-edit')


def _write_references(base_dir: Path, plan_id: str, refs: dict) -> Path:
    """Write references.json into the PLAN_BASE_DIR fixture tree."""
    plan_dir = base_dir / 'plans' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    refs_path = plan_dir / 'references.json'
    refs_path.write_text(json.dumps(refs, indent=2))
    return refs_path


def _read_references(base_dir: Path, plan_id: str) -> dict:
    refs_path = base_dir / 'plans' / plan_id / 'references.json'
    return json.loads(refs_path.read_text())


def _run_footprint(base_dir: Path, plan_id: str, worktree: Path, *extra: str):
    return run_script(
        SCRIPT_PATH,
        'compute-footprint',
        '--plan-id',
        plan_id,
        '--worktree-path',
        str(worktree),
        *extra,
        env_overrides={'PLAN_BASE_DIR': str(base_dir)},
    )


# =============================================================================
# Argparse surface — compute-footprint accepts --plan-id + --worktree-path
# =============================================================================


def test_compute_footprint_help_shows_plan_id_and_worktree_path():
    """``compute-footprint --help`` must declare both --plan-id and --worktree-path."""
    result = run_script(SCRIPT_PATH, 'compute-footprint', '--help')
    assert result.success, f'--help failed: {result.stderr}'
    assert '--plan-id' in result.stdout, 'compute-footprint must declare --plan-id'
    assert '--worktree-path' in result.stdout, 'compute-footprint must declare --worktree-path'
    assert '--base-ref' in result.stdout, 'compute-footprint must declare --base-ref'


def test_compute_footprint_help_does_not_declare_project_dir():
    """``compute-footprint`` is Bucket A; --project-dir MUST NOT appear."""
    result = run_script(SCRIPT_PATH, 'compute-footprint', '--help')
    assert result.success, f'--help failed: {result.stderr}'
    assert '--project-dir' not in result.stdout, (
        'manage-references is Bucket A and must not declare --project-dir; '
        'two-state routing happens at the caller via resolve_project_dir.'
    )


def test_compute_footprint_requires_plan_id():
    """--plan-id is required; argparse exits 2 when omitted."""
    result = run_script(
        SCRIPT_PATH,
        'compute-footprint',
        '--worktree-path',
        '/tmp/nonexistent',
    )
    assert result.returncode == 2, f'Expected argparse exit 2, got {result.returncode}'


def test_compute_footprint_requires_worktree_path():
    """--worktree-path is required; argparse exits 2 when omitted."""
    result = run_script(
        SCRIPT_PATH,
        'compute-footprint',
        '--plan-id',
        CANONICAL_PLAN_ID,
    )
    assert result.returncode == 2, f'Expected argparse exit 2, got {result.returncode}'


def test_diff_files_verb_no_longer_registered():
    """The old ``diff-files`` verb must be gone — argparse rejects it (exit 2)."""
    result = run_script(SCRIPT_PATH, 'diff-files', '--help')
    assert result.returncode == 2, (
        f'diff-files must no longer be a registered subcommand; got {result.returncode}'
    )


def test_reconcile_files_verb_no_longer_registered():
    """The old ``reconcile-files`` verb must be gone — argparse rejects it (exit 2)."""
    result = run_script(SCRIPT_PATH, 'reconcile-files', '--help')
    assert result.returncode == 2, (
        f'reconcile-files must no longer be a registered subcommand; got {result.returncode}'
    )


# =============================================================================
# Live-footprint behaviour: files == live {base}...HEAD ∪ porcelain
# =============================================================================


def test_returns_live_plan_branch_footprint(tmp_path):
    """``files`` equals the live plan-branch-only set, sorted, derived purely
    from the worktree git state — independent of any ledger.

    In the absorb scenario the three-dot ``main...HEAD`` diff excludes the
    absorbed-upstream file, so the live footprint contains only the genuine
    plan change.
    """
    repo = tmp_path / 'worktree'
    _build_absorb_scenario(repo)
    base_dir = tmp_path / 'plan-base'
    # references.json carries only base_branch; no modified_files ledger exists.
    _write_references(base_dir, FOOTPRINT_PLAN_ID, {'base_branch': 'main'})

    result = _run_footprint(base_dir, FOOTPRINT_PLAN_ID, repo)
    assert result.returncode == 0, f'stderr={result.stderr!r} stdout={result.stdout!r}'
    data = result.toon()
    assert data['status'] == 'success'
    # Live footprint = sorted {base}...HEAD ∪ porcelain. The absorbed-upstream
    # file is at/below the merge-base and excluded from the three-dot range.
    assert data['files'] == ['plan_change.py']
    assert data['live_count'] == 1


def test_footprint_includes_uncommitted_working_tree_state(tmp_path):
    """An uncommitted (untracked) working-tree file is surfaced via the
    porcelain half of the union, even though it is not in any commit."""
    repo = tmp_path / 'worktree'
    _build_absorb_scenario(repo)
    # Add an untracked file that lives only in the working tree.
    (repo / 'scratch.txt').write_text('scratch\n')
    base_dir = tmp_path / 'plan-base'
    _write_references(base_dir, FOOTPRINT_PLAN_ID, {'base_branch': 'main'})

    result = _run_footprint(base_dir, FOOTPRINT_PLAN_ID, repo)
    data = result.toon()
    assert data['status'] == 'success'
    assert 'plan_change.py' in data['files']
    assert 'scratch.txt' in data['files']


def test_footprint_has_no_ledger_intersection_fields(tmp_path):
    """The drift-accounting fields from the old ledger-intersecting verb
    (``dropped``, ``phantom``, ``references_count``) must NOT appear — there
    is no ledger left to reconcile against."""
    repo = tmp_path / 'worktree'
    _build_absorb_scenario(repo)
    base_dir = tmp_path / 'plan-base'
    _write_references(base_dir, FOOTPRINT_PLAN_ID, {'base_branch': 'main'})

    result = _run_footprint(base_dir, FOOTPRINT_PLAN_ID, repo)
    data = result.toon()
    assert data['status'] == 'success'
    assert 'dropped' not in data
    assert 'phantom' not in data
    assert 'references_count' not in data


def test_footprint_is_read_only(tmp_path):
    """compute-footprint must NOT mutate references.json."""
    repo = tmp_path / 'worktree'
    _build_absorb_scenario(repo)
    base_dir = tmp_path / 'plan-base'
    original = {'base_branch': 'main'}
    _write_references(base_dir, FOOTPRINT_PLAN_ID, dict(original))

    before = _read_references(base_dir, FOOTPRINT_PLAN_ID)
    _run_footprint(base_dir, FOOTPRINT_PLAN_ID, repo)
    after = _read_references(base_dir, FOOTPRINT_PLAN_ID)
    assert before == after


# =============================================================================
# Error contract
# =============================================================================


def test_compute_footprint_worktree_not_found(tmp_path):
    """A non-existent --worktree-path yields a structured worktree_not_found error."""
    base_dir = tmp_path / 'plan-base'
    _write_references(base_dir, FOOTPRINT_PLAN_ID, {'base_branch': 'main'})
    result = _run_footprint(base_dir, FOOTPRINT_PLAN_ID, tmp_path / 'does-not-exist')
    # Operation failure exits 0 (not a script crash) per the operation-failure contract.
    assert result.returncode == 0, f'operation failure should exit 0: {result.stderr!r}'
    assert 'worktree_not_found' in result.stdout


def test_compute_footprint_references_not_found(tmp_path):
    """A missing references.json yields a structured references_not_found error."""
    repo = tmp_path / 'worktree'
    _build_absorb_scenario(repo)
    base_dir = tmp_path / 'plan-base'
    # No references.json written for this plan.
    (base_dir / 'plans' / FOOTPRINT_PLAN_ID).mkdir(parents=True, exist_ok=True)
    result = _run_footprint(base_dir, FOOTPRINT_PLAN_ID, repo)
    assert result.returncode == 0
    assert 'references_not_found' in result.stdout


def test_compute_footprint_not_a_git_worktree(tmp_path):
    """A real directory that is not a git worktree yields not_a_git_worktree."""
    non_repo = tmp_path / 'plain-dir'
    non_repo.mkdir(parents=True, exist_ok=True)
    base_dir = tmp_path / 'plan-base'
    _write_references(base_dir, FOOTPRINT_PLAN_ID, {'base_branch': 'main'})
    result = _run_footprint(base_dir, FOOTPRINT_PLAN_ID, non_repo)
    assert result.returncode == 0
    assert 'not_a_git_worktree' in result.stdout


# =============================================================================
# Integration: resolve_project_dir output is a valid --worktree-path argument
# =============================================================================


def test_resolve_project_dir_output_shape_matches_worktree_path_arg():
    """The resolver returns an absolute path string suitable for --worktree-path.

    Bucket A consumers like ``manage-references compute-footprint`` accept a
    ``--worktree-path`` argument whose value is computed by the caller via
    ``resolve_project_dir``. This test pins the contract that the resolver's
    output shape (absolute filesystem path string) matches what
    ``compute-footprint`` expects, so callers can wire the two together without
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

    This is the path used by ad-hoc ``manage-references compute-footprint``
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
