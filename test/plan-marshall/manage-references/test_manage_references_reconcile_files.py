#!/usr/bin/env python3
"""Tests for ``manage-references reconcile-files`` — the write-back counterpart
of the read-only ``diff-files`` verb.

``reconcile-files`` recomputes ``references.modified_files`` from the
plan-branch-only diff (``{base_ref}...HEAD`` three-dot ∪ porcelain working-tree
state) and PERSISTS the reconciled set, dropping absorbed-upstream entries that
pollute the ledger after an absorb merge. This module pins:

* the argparse surface (``--plan-id`` + ``--worktree-path`` required,
  ``--base-ref`` optional) and the Bucket-A no-``--project-dir`` contract
* the core anti-pollution assertion: a ledger entry that is NOT in the live
  plan-branch diff (an absorbed-upstream file) is REMOVED from the persisted
  ledger
* the persist contract: ``reconcile-files`` mutates ``references.json``;
  ``diff-files`` does NOT
* shared-primitive parity: the ``live`` set ``reconcile-files`` persists is the
  same one ``diff-files`` reports
* the shared error contract (``worktree_not_found``, ``references_not_found``,
  ``not_a_git_worktree``)
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-references', 'manage-references.py')

CANONICAL_PLAN_ID = 'reconcile-files-plan'


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


def _run_reconcile(base_dir: Path, plan_id: str, worktree: Path, *extra: str):
    return run_script(
        SCRIPT_PATH,
        'reconcile-files',
        '--plan-id',
        plan_id,
        '--worktree-path',
        str(worktree),
        *extra,
        env_overrides={'PLAN_BASE_DIR': str(base_dir)},
    )


def _run_diff(base_dir: Path, plan_id: str, worktree: Path, *extra: str):
    return run_script(
        SCRIPT_PATH,
        'diff-files',
        '--plan-id',
        plan_id,
        '--worktree-path',
        str(worktree),
        *extra,
        env_overrides={'PLAN_BASE_DIR': str(base_dir)},
    )


# =============================================================================
# Argparse surface
# =============================================================================


class TestReconcileFilesArgparse:
    def test_help_shows_plan_id_and_worktree_path(self):
        result = run_script(SCRIPT_PATH, 'reconcile-files', '--help')
        assert result.success, f'--help failed: {result.stderr}'
        assert '--plan-id' in result.stdout
        assert '--worktree-path' in result.stdout
        assert '--base-ref' in result.stdout

    def test_help_does_not_declare_project_dir(self):
        result = run_script(SCRIPT_PATH, 'reconcile-files', '--help')
        assert result.success
        assert '--project-dir' not in result.stdout, (
            'manage-references is Bucket A and must not declare --project-dir'
        )

    def test_requires_plan_id(self):
        result = run_script(
            SCRIPT_PATH, 'reconcile-files', '--worktree-path', '/tmp/nonexistent'
        )
        assert result.returncode == 2

    def test_requires_worktree_path(self):
        result = run_script(
            SCRIPT_PATH, 'reconcile-files', '--plan-id', CANONICAL_PLAN_ID
        )
        assert result.returncode == 2


# =============================================================================
# Core behaviour: anti-pollution write-back
# =============================================================================


class TestReconcileFilesWriteBack:
    def test_persists_plan_branch_only_intersection(self, tmp_path):
        """reconcile-files persists the plan-branch-only set to references.json."""
        repo = tmp_path / 'worktree'
        _build_absorb_scenario(repo)
        base_dir = tmp_path / 'plan-base'
        _write_references(
            base_dir,
            CANONICAL_PLAN_ID,
            {'base_branch': 'main', 'modified_files': ['plan_change.py']},
        )

        result = _run_reconcile(base_dir, CANONICAL_PLAN_ID, repo)
        assert result.returncode == 0, f'stderr={result.stderr!r} stdout={result.stdout!r}'
        data = result.toon()
        assert data['status'] == 'success'

        persisted = _read_references(base_dir, CANONICAL_PLAN_ID)
        assert 'plan_change.py' in persisted['modified_files']

    def test_removes_absorbed_upstream_file_from_ledger(self, tmp_path):
        """Core anti-pollution assertion: an absorbed-upstream file present in
        the ledger (but absent from the plan-branch-only diff) is REMOVED."""
        repo = tmp_path / 'worktree'
        _build_absorb_scenario(repo)
        base_dir = tmp_path / 'plan-base'
        # Ledger has been polluted: it contains the absorbed-upstream file.
        _write_references(
            base_dir,
            CANONICAL_PLAN_ID,
            {
                'base_branch': 'main',
                'modified_files': ['plan_change.py', 'upstream_only.py'],
            },
        )

        result = _run_reconcile(base_dir, CANONICAL_PLAN_ID, repo)
        assert result.returncode == 0, f'stderr={result.stderr!r}'
        data = result.toon()
        assert data['status'] == 'success'

        persisted = _read_references(base_dir, CANONICAL_PLAN_ID)
        # The genuine plan change is retained.
        assert 'plan_change.py' in persisted['modified_files']
        # The absorbed-upstream file is dropped — it is at/below the merge-base
        # and therefore excluded from the three-dot main...HEAD diff range.
        assert 'upstream_only.py' not in persisted['modified_files']

    def test_reports_removed_files(self, tmp_path):
        """The structured result surfaces the dropped absorbed-upstream files."""
        repo = tmp_path / 'worktree'
        _build_absorb_scenario(repo)
        base_dir = tmp_path / 'plan-base'
        _write_references(
            base_dir,
            CANONICAL_PLAN_ID,
            {
                'base_branch': 'main',
                'modified_files': ['plan_change.py', 'upstream_only.py'],
            },
        )

        result = _run_reconcile(base_dir, CANONICAL_PLAN_ID, repo)
        data = result.toon()
        assert data['status'] == 'success'
        assert 'upstream_only.py' in (data.get('removed') or [])
        assert data['before_count'] == 2
        assert data['after_count'] == 1


# =============================================================================
# Shared-primitive parity and read-only invariant
# =============================================================================


class TestSharedPrimitiveParity:
    def test_reconcile_live_set_matches_diff_files(self, tmp_path):
        """The plan-branch-only set reconcile-files persists equals the live set
        diff-files reports (shared compute_plan_branch_diff primitive)."""
        repo = tmp_path / 'worktree'
        _build_absorb_scenario(repo)
        base_dir = tmp_path / 'plan-base'
        _write_references(
            base_dir,
            CANONICAL_PLAN_ID,
            {
                'base_branch': 'main',
                'modified_files': ['plan_change.py', 'upstream_only.py'],
            },
        )

        diff_result = _run_diff(base_dir, CANONICAL_PLAN_ID, repo)
        diff_data = diff_result.toon()
        # diff-files: 'files' is ledger ∩ live (in ledger order). The genuine
        # plan change is in live; the absorbed-upstream file is not.
        assert diff_data['files'] == ['plan_change.py']

        _run_reconcile(base_dir, CANONICAL_PLAN_ID, repo)
        persisted = _read_references(base_dir, CANONICAL_PLAN_ID)
        # The reconciled ledger contains exactly the same intersection.
        assert persisted['modified_files'] == ['plan_change.py']

    def test_diff_files_is_read_only(self, tmp_path):
        """diff-files must NOT mutate references.json."""
        repo = tmp_path / 'worktree'
        _build_absorb_scenario(repo)
        base_dir = tmp_path / 'plan-base'
        original = {
            'base_branch': 'main',
            'modified_files': ['plan_change.py', 'upstream_only.py'],
        }
        _write_references(base_dir, CANONICAL_PLAN_ID, dict(original))

        before = _read_references(base_dir, CANONICAL_PLAN_ID)
        _run_diff(base_dir, CANONICAL_PLAN_ID, repo)
        after = _read_references(base_dir, CANONICAL_PLAN_ID)
        # diff-files is read-only: the ledger is unchanged, still polluted.
        assert before == after
        assert 'upstream_only.py' in after['modified_files']


# =============================================================================
# Error contract (mirrors diff-files)
# =============================================================================


class TestReconcileFilesErrors:
    def test_worktree_not_found(self, tmp_path):
        base_dir = tmp_path / 'plan-base'
        _write_references(
            base_dir, CANONICAL_PLAN_ID, {'base_branch': 'main', 'modified_files': []}
        )
        result = _run_reconcile(
            base_dir, CANONICAL_PLAN_ID, tmp_path / 'does-not-exist'
        )
        assert result.returncode == 0, f'operation failure should exit 0: {result.stderr!r}'
        assert 'worktree_not_found' in result.stdout

    def test_references_not_found(self, tmp_path):
        repo = tmp_path / 'worktree'
        _build_absorb_scenario(repo)
        base_dir = tmp_path / 'plan-base'
        # No references.json written for this plan.
        (base_dir / 'plans' / CANONICAL_PLAN_ID).mkdir(parents=True, exist_ok=True)
        result = _run_reconcile(base_dir, CANONICAL_PLAN_ID, repo)
        assert result.returncode == 0
        assert 'references_not_found' in result.stdout

    def test_not_a_git_worktree(self, tmp_path):
        non_repo = tmp_path / 'plain-dir'
        non_repo.mkdir(parents=True, exist_ok=True)
        base_dir = tmp_path / 'plan-base'
        _write_references(
            base_dir, CANONICAL_PLAN_ID, {'base_branch': 'main', 'modified_files': []}
        )
        result = _run_reconcile(base_dir, CANONICAL_PLAN_ID, non_repo)
        assert result.returncode == 0
        assert 'not_a_git_worktree' in result.stdout
