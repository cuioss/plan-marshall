#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _cmd_switch_and_pull.py — switch-and-pull verb.

Tier 2 (direct import) tests covering:
* _resolve_project_dir — --project-dir escape-hatch path
* _verify_git_repo     — non-git path detection
* cmd_switch_and_pull  — remote branch not found, merge_conflict on checkout,
                         pull failure, success path with commits_pulled, and
                         success path with zero commits_pulled

Tier 3 (subprocess CLI plumbing) tests:
* Missing --base arg is rejected
* --project-dir with --base produces a structured error (non-git path)

Resolver-migration note
-----------------------
The private ``_find_executor`` helper this file used to exercise is GONE, along
with the hand-rolled ``manage-status get-worktree-path`` shell-out it served.
``_resolve_project_dir`` KEEPS its name — it is the CLI argument adapter that
owns this verb's ``--project-dir`` escape hatch — but under ``--plan-id`` the
plan id is a VALIDITY GATE rather than a path source: the plan is resolved
through ``file_ops.resolve_plan_context`` so an unresolvable id fails loudly,
and the returned path is the MAIN checkout root, resolved main-anchored by
``marketplace_paths.main_checkout_root``. ``TestResolveProjectDirViaResolver``
below pins both halves — the gate-not-source distinction, and that the path is
main-anchored rather than cwd-relative.
"""

from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from _resolve_project_dir_fixtures import (
    CANONICAL_WORKTREE,
    MAIN_CHECKOUT_ROOT,
    NO_PLAN_SENTINEL,
    patch_worktree_faces,
)
from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, run_script

# ---------------------------------------------------------------------------
# Load module under test
# ---------------------------------------------------------------------------

_SWITCH_AND_PULL_PATH = get_script_path('plan-marshall', 'workflow-integration-git', '_cmd_switch_and_pull.py')
_SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

_mod = load_script_module(
    'plan-marshall', 'workflow-integration-git', '_cmd_switch_and_pull.py', '_cmd_switch_and_pull'
)

cmd_switch_and_pull = _mod.cmd_switch_and_pull
_resolve_project_dir = _mod._resolve_project_dir
_verify_git_repo = _mod._verify_git_repo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_repo(path: Path) -> str:
    """Initialise a minimal git repo on main, return the initial HEAD SHA."""
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(path)], check=True)
    subprocess.run(['git', '-C', str(path), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(path), 'config', 'user.name', 'Test'], check=True)
    (path / 'README.md').write_text('initial\n')
    subprocess.run(['git', '-C', str(path), 'add', 'README.md'], check=True)
    subprocess.run(['git', '-C', str(path), 'commit', '-m', 'init'], check=True)
    result = subprocess.run(
        ['git', '-C', str(path), 'rev-parse', 'HEAD'],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _init_repo_with_linked_worktree(root: Path) -> tuple[Path, Path]:
    """Create a main checkout plus a linked worktree; return ``(main, worktree)``.

    Reproduces the phase-5+ topology this verb actually runs in: the plan's
    working directory is a LINKED worktree while the tree the verb must act on
    is the main checkout.
    """
    main = root / 'main-checkout'
    main.mkdir()
    _init_repo(main)
    worktree = root / 'linked-worktree'
    subprocess.run(
        ['git', '-C', str(main), 'worktree', 'add', '-q', '-b', 'feature/probe', str(worktree)],
        check=True,
    )
    return main, worktree


# ---------------------------------------------------------------------------
# Tier 2: _verify_git_repo
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Tier 2: _verify_git_repo
# ---------------------------------------------------------------------------


class TestVerifyGitRepo:
    def test_returns_none_for_valid_git_repo(self, tmp_path: Path) -> None:
        """Returns None when path is a valid git working tree."""
        _init_repo(tmp_path)

        result = _verify_git_repo(tmp_path)

        assert result is None

    def test_returns_error_string_for_non_git_path(self, outside_repo_dir: Path) -> None:
        """Returns an error string when path is not a git repo."""
        # Must be OUTSIDE the repo: pytest's tmp_path now roots under the
        # repo-local --basetemp, which IS a valid git working tree.
        result = _verify_git_repo(outside_repo_dir)

        assert result is not None
        assert 'working tree' in result



# ---------------------------------------------------------------------------
# Tier 2: _resolve_project_dir — escape-hatch path
# ---------------------------------------------------------------------------


class TestResolveProjectDir:
    def test_project_dir_returns_path(self) -> None:
        """--project-dir escape-hatch resolves to a Path object."""
        args = Namespace(plan_id=None, project_dir='/some/path')

        path, error = _resolve_project_dir(args)

        assert error is None
        assert path == Path('/some/path')

    def test_missing_both_args_returns_error(self) -> None:
        """Neither --plan-id nor --project-dir → missing_required_arg."""
        args = Namespace(plan_id=None, project_dir=None)

        path, error = _resolve_project_dir(args)

        assert path is None
        assert error is not None
        assert error['error_type'] == 'missing_required_arg'



# ---------------------------------------------------------------------------
# Tier 2: cmd_switch_and_pull — project-dir escape-hatch
# ---------------------------------------------------------------------------


class TestCmdSwitchAndPullEscapeHatch:
    def test_non_git_project_dir_returns_error(self, outside_repo_dir: Path) -> None:
        """--project-dir that is not a git repo → project_dir_not_a_git_repo."""
        # Must be OUTSIDE the repo: pytest's tmp_path now roots under the
        # repo-local --basetemp, which IS a git repo (would surface a later
        # pull_failed instead of project_dir_not_a_git_repo).
        args = Namespace(plan_id=None, project_dir=str(outside_repo_dir), base='main')

        result = cmd_switch_and_pull(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'project_dir_not_a_git_repo'
        assert result['operation'] == 'switch-and-pull'

    def test_remote_branch_not_found_returns_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When ls-remote returns empty output, error_type is branch_not_found."""
        _init_repo(tmp_path)
        orig = _mod.run_git

        def fake_run_git(args, **kwargs):
            if 'ls-remote' in args:
                return (0, '', '')  # empty: branch not found on remote
            return orig(args, **kwargs)

        monkeypatch.setattr(_mod, 'run_git', fake_run_git)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), base='main')

        result = cmd_switch_and_pull(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'branch_not_found'
        assert 'origin/main' in result['message']

    def test_ls_remote_failure_returns_branch_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When ls-remote exits non-zero, error_type is branch_not_found."""
        _init_repo(tmp_path)
        orig = _mod.run_git

        def fake_run_git(args, **kwargs):
            if 'ls-remote' in args:
                return (1, '', 'connection refused')
            return orig(args, **kwargs)

        monkeypatch.setattr(_mod, 'run_git', fake_run_git)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), base='main')

        result = cmd_switch_and_pull(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'branch_not_found'

    @pytest.mark.parametrize(
        'keyword,expected_type',
        [
            ('conflict', 'merge_conflict'),
            ('overwrite', 'merge_conflict'),
            ('uncommitted', 'merge_conflict'),
            ('unrelated error here', 'pull_failed'),
        ],
    )
    def test_checkout_failure_keyword_classification(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, keyword: str, expected_type: str
    ) -> None:
        """Checkout-failure keywords map to the right error_type.

        Patches run_git to intercept ALL git calls after git-repo verification so
        the checkout-error classification is tested without the real checkout step.
        """
        _init_repo(tmp_path)
        orig = _mod.run_git

        def fake_run_git(git_args, **kwargs):
            a = list(git_args)
            if 'rev-parse' in a and '--show-toplevel' in a:
                # _verify_git_repo — must succeed for real.
                return orig(git_args, **kwargs)
            if 'ls-remote' in a:
                return (0, 'abc123\trefs/heads/main\n', '')
            if 'rev-parse' in a:
                # pre_sha capture.
                return (0, 'deadbeef', '')
            if 'checkout' in a:
                return (1, '', f'error: {keyword}')
            return (0, '', '')

        monkeypatch.setattr(_mod, 'run_git', fake_run_git)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), base='main')

        result = cmd_switch_and_pull(args)

        assert result['status'] == 'error'
        assert result['error_type'] == expected_type

    def test_pull_failure_returns_pull_failed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """git pull non-zero exit → pull_failed."""
        _init_repo(tmp_path)
        orig = _mod.run_git

        def fake_run_git(args, **kwargs):
            if 'ls-remote' in args:
                return (0, 'abc123\trefs/heads/main\n', '')
            if 'rev-parse' in args and 'HEAD' in args:
                return (0, 'abc123', '')
            if 'checkout' in args:
                return (0, '', '')
            if 'pull' in args:
                return (1, '', 'error: network unreachable')
            return orig(args, **kwargs)

        monkeypatch.setattr(_mod, 'run_git', fake_run_git)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), base='main')

        result = cmd_switch_and_pull(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'pull_failed'
        assert 'pre_sha' in result

    def test_success_path_returns_required_fields(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Successful switch-and-pull returns status, pre_sha, post_sha, commits_pulled."""
        _init_repo(tmp_path)
        orig = _mod.run_git
        pre_sha = 'aaa111'
        post_sha = 'bbb222'

        def fake_run_git(args, **kwargs):
            if 'ls-remote' in args:
                return (0, f'{post_sha}\trefs/heads/main\n', '')
            if 'rev-parse' in args and 'HEAD' in args:
                return (0, pre_sha, '')
            if 'checkout' in args:
                return (0, '', '')
            if 'pull' in args:
                return (0, '', '')
            if 'rev-list' in args and '--count' in args:
                return (0, '2', '')
            if 'rev-parse' in args:
                return (0, post_sha, '')
            return orig(args, **kwargs)

        monkeypatch.setattr(_mod, 'run_git', fake_run_git)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), base='main')

        result = cmd_switch_and_pull(args)

        assert result['status'] == 'success'
        assert result['operation'] == 'switch-and-pull'
        assert result['base_branch'] == 'main'
        assert 'pre_sha' in result
        assert 'post_sha' in result
        assert result['commits_pulled'] == 2

    def test_success_zero_commits_pulled(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Already-up-to-date pull returns commits_pulled = 0."""
        _init_repo(tmp_path)
        orig = _mod.run_git
        sha = 'aaa111'

        def fake_run_git(args, **kwargs):
            if 'ls-remote' in args:
                return (0, f'{sha}\trefs/heads/main\n', '')
            if 'rev-parse' in args and 'HEAD' in args:
                return (0, sha, '')
            if 'checkout' in args:
                return (0, '', '')
            if 'pull' in args:
                return (0, 'Already up to date.', '')
            if 'rev-list' in args and '--count' in args:
                return (0, '0', '')
            if 'rev-parse' in args:
                return (0, sha, '')
            return orig(args, **kwargs)

        monkeypatch.setattr(_mod, 'run_git', fake_run_git)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), base='main')

        result = cmd_switch_and_pull(args)

        assert result['status'] == 'success'
        assert result['commits_pulled'] == 0

    def test_envelope_echoes_base_branch(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Response envelope always includes operation and base_branch."""
        _init_repo(tmp_path)
        orig = _mod.run_git

        def fake_run_git(args, **kwargs):
            if 'ls-remote' in args:
                return (0, '', '')  # trigger branch_not_found early
            return orig(args, **kwargs)

        monkeypatch.setattr(_mod, 'run_git', fake_run_git)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), base='develop')

        result = cmd_switch_and_pull(args)

        assert result['operation'] == 'switch-and-pull'
        assert result['base_branch'] == 'develop'
