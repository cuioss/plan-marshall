"""Tests for _cmd_force_push.py — force-push-with-lease verb.

Tier 2 (direct import) tests covering:
* _resolve_branch_and_path  — --plan-id missing executor, missing branch, base branch guard
* _verify_git_repo          — non-git path
* cmd_force_push            — success path, branch_not_found, push_rejected, push_failed,
                              lease_check_failed, base-branch rejection
* _find_executor            — helper-based executor path resolution

Tier 3 (subprocess CLI plumbing) tests covering:
* Missing required args (argparse rejects)
* force-push-with-lease --project-dir path with --branch (escape-hatch)
"""

from __future__ import annotations

import importlib.util
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest
from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import get_script_path, run_script

# ---------------------------------------------------------------------------
# Load module under test
# ---------------------------------------------------------------------------

_FORCE_PUSH_PATH = get_script_path('plan-marshall', 'workflow-integration-git', '_cmd_force_push.py')
_SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

_spec = importlib.util.spec_from_file_location('_cmd_force_push', _FORCE_PUSH_PATH)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_force_push = _mod.cmd_force_push
_verify_git_repo = _mod._verify_git_repo
_resolve_branch_and_path = _mod._resolve_branch_and_path
_find_executor = _mod._find_executor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_repo(path: Path) -> None:
    """Initialise a minimal git repo with a single commit."""
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(path)], check=True)
    subprocess.run(['git', '-C', str(path), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(path), 'config', 'user.name', 'Test'], check=True)
    (path / 'README.md').write_text('x\n')
    subprocess.run(['git', '-C', str(path), 'add', 'README.md'], check=True)
    subprocess.run(['git', '-C', str(path), 'commit', '-m', 'init'], check=True)


def _create_feature_branch(path: Path, branch: str) -> None:
    """Create a feature branch in the repo."""
    subprocess.run(['git', '-C', str(path), 'checkout', '-b', branch], check=True)


# ---------------------------------------------------------------------------
# Tier 2: _verify_git_repo
# ---------------------------------------------------------------------------


class TestVerifyGitRepo:
    """Direct-import tests for the git-repo verification helper."""

    def test_returns_none_for_valid_git_repo(self, tmp_path: Path) -> None:
        """Returns None when path is a valid git working tree."""
        _init_repo(tmp_path)

        result = _verify_git_repo(tmp_path)

        assert result is None

    def test_returns_error_for_non_git_path(self, tmp_path: Path) -> None:
        """Returns an error string when path is not a git repo."""
        result = _verify_git_repo(tmp_path)

        assert result is not None
        assert 'working tree' in result


# ---------------------------------------------------------------------------
# Tier 2: _resolve_branch_and_path
# ---------------------------------------------------------------------------


class TestResolveBranchAndPath:
    """Direct-import tests for argument resolution."""

    def test_project_dir_path_missing_branch_returns_error(self) -> None:
        """--project-dir without --branch produces missing_required_arg error."""
        args = Namespace(plan_id=None, project_dir='/some/path', branch=None)

        branch, path, error = _resolve_branch_and_path(args)

        assert branch is None
        assert path is None
        assert error is not None
        assert error['error_type'] == 'missing_required_arg'

    def test_project_dir_with_branch_returns_path(self) -> None:
        """--project-dir + --branch escape-hatch resolves successfully."""
        args = Namespace(plan_id=None, project_dir='/some/path', branch='feature/x')

        branch, path, error = _resolve_branch_and_path(args)

        assert error is None
        assert branch == 'feature/x'
        assert path == Path('/some/path')

    def test_no_args_returns_error(self) -> None:
        """Neither --plan-id nor --project-dir → missing_required_arg error."""
        args = Namespace(plan_id=None, project_dir=None, branch=None)

        branch, path, error = _resolve_branch_and_path(args)

        assert branch is None
        assert path is None
        assert error is not None


# ---------------------------------------------------------------------------
# Tier 2: cmd_force_push — project-dir escape-hatch path
# ---------------------------------------------------------------------------


class TestCmdForcePushEscapeHatch:
    """Direct-import tests for cmd_force_push via --project-dir."""

    def test_project_dir_not_a_git_repo_returns_error(self, tmp_path: Path) -> None:
        """--project-dir pointing at a non-git directory → project_dir_not_a_git_repo."""
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'project_dir_not_a_git_repo'
        assert result['operation'] == 'force-push-with-lease'

    def test_branch_not_found_locally_returns_error(self, tmp_path: Path) -> None:
        """Branch that does not exist locally → branch_not_found."""
        _init_repo(tmp_path)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/nonexistent')

        result = cmd_force_push(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'branch_not_found'
        assert 'feature/nonexistent' in result['message']

    def test_main_branch_rejection(self, tmp_path: Path) -> None:
        """Attempting to push 'main' → branch_not_found (base branch guard)."""
        _init_repo(tmp_path)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='main')

        result = cmd_force_push(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'branch_not_found'
        assert 'base branch' in result['message']

    def test_master_branch_rejection(self, tmp_path: Path) -> None:
        """Attempting to push 'master' → branch_not_found (base branch guard)."""
        _init_repo(tmp_path)
        subprocess.run(['git', '-C', str(tmp_path), 'checkout', '-b', 'master'], check=True)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='master')

        result = cmd_force_push(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'branch_not_found'
        assert 'base branch' in result['message']

    def test_envelope_includes_project_dir_when_supplied(self, tmp_path: Path) -> None:
        """Response envelope echoes project_dir when --project-dir is used."""
        _init_repo(tmp_path)
        # Use a nonexistent branch to get an early error (avoids needing a remote).
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert 'project_dir' in result
        assert result['project_dir'] == str(tmp_path)

    def test_envelope_excludes_plan_id_when_project_dir_path(self, tmp_path: Path) -> None:
        """When --project-dir path is used, plan_id must not appear in response."""
        _init_repo(tmp_path)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert 'plan_id' not in result


# ---------------------------------------------------------------------------
# Tier 2: cmd_force_push — push failure error mapping
# ---------------------------------------------------------------------------


def _patch_run_git(monkeypatch: pytest.MonkeyPatch, responses: dict) -> None:
    """Patch _mod.run_git to return canned responses keyed by an args tuple.

    Any git call whose argv contains all elements of a ``responses`` key returns
    the mapped triple; everything else falls through to the real ``run_git`` (so
    e.g. ``rev-parse --verify`` branch-existence checks run for real).
    """
    orig_run_git = _mod.run_git

    def fake_run_git(args, **kwargs):
        key = tuple(args)
        for pattern, response in responses.items():
            if all(p in key for p in pattern):
                return response
        return orig_run_git(args, **kwargs)

    monkeypatch.setattr(_mod, 'run_git', fake_run_git)


class TestCmdForcePushPushFailures:
    """Test push error categorization by monkeypatching run_git."""

    def test_non_fast_forward_rejection_mapped_to_push_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Lease violation with 'rejected' + 'non-fast-forward' → push_rejected_non_fast_forward."""
        _init_repo(tmp_path)
        _create_feature_branch(tmp_path, 'feature/x')
        _patch_run_git(monkeypatch, {
            ('push', 'origin'): (1, '', 'error: failed to push some refs\n! [rejected] feature/x -> feature/x (non-fast-forward)'),
        })
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert result['status'] == 'rejected'
        assert result['error_type'] == 'push_rejected_non_fast_forward'

    def test_generic_push_failure_mapped_to_push_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-rejection push failure → push_failed."""
        _init_repo(tmp_path)
        _create_feature_branch(tmp_path, 'feature/x')
        _patch_run_git(monkeypatch, {
            ('push', 'origin'): (1, '', 'error: could not connect to remote'),
        })
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'push_failed'

    def test_success_path_returns_success_status(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Successful push returns status=success and branch/remote fields."""
        _init_repo(tmp_path)
        _create_feature_branch(tmp_path, 'feature/x')
        _patch_run_git(monkeypatch, {
            ('push', 'origin'): (0, '', ''),
            ('ls-remote', 'origin'): (0, 'abc123\trefs/heads/feature/x\n', ''),
        })
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert result['status'] == 'success'
        assert result['branch'] == 'feature/x'
        assert result['remote'] == 'origin'
        assert 'remote_sha' in result
        assert result['remote_sha'] == 'abc123'

    def test_success_without_ls_remote_omits_remote_sha(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When ls-remote fails, remote_sha is absent (not None or empty)."""
        _init_repo(tmp_path)
        _create_feature_branch(tmp_path, 'feature/x')
        _patch_run_git(monkeypatch, {
            ('push', 'origin'): (0, '', ''),
            ('ls-remote', 'origin'): (1, '', 'connection failed'),
        })
        args = Namespace(plan_id=None, project_dir=str(tmp_path), branch='feature/x')

        result = cmd_force_push(args)

        assert result['status'] == 'success'
        assert 'remote_sha' not in result


# ---------------------------------------------------------------------------
# Tier 2: _find_executor — helper-based executor path resolution
# ---------------------------------------------------------------------------


class TestFindExecutor:
    """Direct-import tests for _find_executor's helper-based resolution.

    _find_executor delegates to ``file_ops.get_executor_path()`` (worktree-safe
    resolution via git-common-dir) and returns the resolved path only when it
    exists on disk, falling back to None on RuntimeError (no git repo) or a
    missing executor file.
    """

    def test_returns_resolved_path_when_executor_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When get_executor_path resolves an existing file, return it."""
        import file_ops  # type: ignore[import-not-found]  # noqa: PLC0415

        executor = tmp_path / 'execute-script.py'
        executor.write_text('# executor\n')
        monkeypatch.setattr(file_ops, 'get_executor_path', lambda: executor)

        result = _find_executor()

        assert result == executor

    def test_returns_none_when_executor_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the resolved path does not exist on disk, return None."""
        import file_ops  # type: ignore[import-not-found]  # noqa: PLC0415

        missing = tmp_path / 'execute-script.py'  # never created
        monkeypatch.setattr(file_ops, 'get_executor_path', lambda: missing)

        result = _find_executor()

        assert result is None

    def test_returns_none_when_helper_raises_runtime_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When get_executor_path raises RuntimeError (no git repo), return None."""
        import file_ops  # type: ignore[import-not-found]  # noqa: PLC0415

        def _raise() -> Path:
            raise RuntimeError('no git repository')

        monkeypatch.setattr(file_ops, 'get_executor_path', _raise)

        result = _find_executor()

        assert result is None


# ---------------------------------------------------------------------------
# Tier 3: CLI plumbing
# ---------------------------------------------------------------------------


class TestCmdForcePushCli:
    """Subprocess tests for CLI plumbing of force-push-with-lease."""

    def test_missing_plan_id_and_project_dir_exits_with_error(self) -> None:
        """Neither --plan-id nor --project-dir produces a structured error."""
        result = run_script(_SCRIPT_PATH, 'force-push-with-lease')

        # Expected: exit 0 with TOON error (argparse supplies both as optional).
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'error'

    def test_project_dir_requires_branch(self, tmp_path: Path) -> None:
        """--project-dir without --branch returns missing_required_arg error."""
        result = run_script(
            _SCRIPT_PATH, 'force-push-with-lease',
            '--project-dir', str(tmp_path),
        )

        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'error'
        assert parsed['error_type'] == 'missing_required_arg'

    def test_help_flag_shows_force_push_subcommand(self) -> None:
        """--help lists force-push-with-lease in output."""
        result = run_script(_SCRIPT_PATH, '--help')

        assert result.returncode == 0
        assert 'force-push-with-lease' in result.stdout
