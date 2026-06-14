"""Tests for _cmd_prune_ref.py — prune-local-and-remote-ref verb.

Tier 2 (direct import) tests covering:
* _resolve_project_dir_and_head — --project-dir escape-hatch path, missing args
* _verify_git_repo              — non-git path detection
* cmd_prune_ref                 — currently-checked-out-branch guard,
                                  local branch delete failure,
                                  local_only mode (skip remote-tracking ref),
                                  show-ref absent (graceful partial no-op),
                                  update-ref failure after show-ref confirms ref,
                                  success path (local + remote ref deleted)
* _find_executor                — helper-based executor path resolution

Tier 3 (subprocess CLI plumbing) tests:
* --project-dir requires --head
* --project-dir + --head + non-git path returns structured error
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

_PRUNE_REF_PATH = get_script_path(
    'plan-marshall', 'workflow-integration-git', '_cmd_prune_ref.py'
)
_SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

_spec = importlib.util.spec_from_file_location('_cmd_prune_ref', _PRUNE_REF_PATH)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_prune_ref = _mod.cmd_prune_ref
_resolve_project_dir_and_head = _mod._resolve_project_dir_and_head
_verify_git_repo = _mod._verify_git_repo
_find_executor = _mod._find_executor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_repo(path: Path, branch: str = 'main') -> None:
    """Initialise a minimal git repo with a single commit on ``branch``."""
    subprocess.run(['git', 'init', '-q', '-b', branch, str(path)], check=True)
    subprocess.run(['git', '-C', str(path), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(path), 'config', 'user.name', 'Test'], check=True)
    (path / 'README.md').write_text('x\n')
    subprocess.run(['git', '-C', str(path), 'add', 'README.md'], check=True)
    subprocess.run(['git', '-C', str(path), 'commit', '-m', 'init'], check=True)


def _create_branch(path: Path, branch: str) -> None:
    """Create a branch without checking it out."""
    subprocess.run(['git', '-C', str(path), 'branch', branch], check=True)


# ---------------------------------------------------------------------------
# Tier 2: _verify_git_repo
# ---------------------------------------------------------------------------


class TestVerifyGitRepo:
    def test_valid_repo_returns_none(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)

        assert _verify_git_repo(tmp_path) is None

    def test_non_git_path_returns_error_string(self, tmp_path: Path) -> None:
        result = _verify_git_repo(tmp_path)

        assert result is not None
        assert 'working tree' in result


# ---------------------------------------------------------------------------
# Tier 2: _resolve_project_dir_and_head — escape-hatch path
# ---------------------------------------------------------------------------


class TestResolveProjectDirAndHead:
    def test_project_dir_and_head_resolves(self) -> None:
        args = Namespace(plan_id=None, project_dir='/some/path', head='feature/x')

        path, head, error = _resolve_project_dir_and_head(args)

        assert error is None
        assert path == Path('/some/path')
        assert head == 'feature/x'

    def test_project_dir_without_head_returns_error(self) -> None:
        args = Namespace(plan_id=None, project_dir='/some/path', head=None)

        path, head, error = _resolve_project_dir_and_head(args)

        assert path is None
        assert head is None
        assert error is not None
        assert error['error_type'] == 'missing_required_arg'

    def test_neither_plan_id_nor_project_dir_returns_error(self) -> None:
        args = Namespace(plan_id=None, project_dir=None, head=None)

        path, head, error = _resolve_project_dir_and_head(args)

        assert path is None
        assert head is None
        assert error is not None
        assert error['error_type'] == 'missing_required_arg'


# ---------------------------------------------------------------------------
# Tier 2: cmd_prune_ref — project-dir escape-hatch path
# ---------------------------------------------------------------------------


def _patch_run_git(monkeypatch: pytest.MonkeyPatch, fake_run_git) -> None:
    """Replace _mod.run_git with ``fake_run_git`` for the duration of a test.

    The fake receives ``(args, **kwargs)`` and may call ``orig`` (captured via a
    default arg) to fall through to the real git binary for un-intercepted calls.
    """
    monkeypatch.setattr(_mod, 'run_git', fake_run_git)


class TestCmdPruneRefEscapeHatch:
    def test_non_git_project_dir_returns_error(self, tmp_path: Path) -> None:
        """--project-dir not a git repo → project_dir_not_a_git_repo."""
        args = Namespace(plan_id=None, project_dir=str(tmp_path), head='feature/x', mode='local_and_remote')

        result = cmd_prune_ref(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'project_dir_not_a_git_repo'
        assert result['operation'] == 'prune-local-and-remote-ref'

    def test_currently_checked_out_branch_guard(self, tmp_path: Path) -> None:
        """Attempting to delete the currently checked-out branch → branch_delete_failed."""
        _init_repo(tmp_path, branch='main')
        # HEAD is 'main', so head='main' should be rejected.
        args = Namespace(plan_id=None, project_dir=str(tmp_path), head='main', mode='local_and_remote')

        result = cmd_prune_ref(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'branch_delete_failed'
        assert result['local_deleted'] is False
        assert 'currently checked-out' in result['message']

    def test_branch_delete_failure_returns_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """git branch -D failure → branch_delete_failed with local_deleted=False."""
        _init_repo(tmp_path, branch='main')
        orig = _mod.run_git

        def fake_run_git(args, **kwargs):
            if '--abbrev-ref' in args:
                return (0, 'main', '')
            if '-D' in args:
                return (1, '', 'error: branch not found')
            return orig(args, **kwargs)

        _patch_run_git(monkeypatch, fake_run_git)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), head='feature/x', mode='local_and_remote')

        result = cmd_prune_ref(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'branch_delete_failed'
        assert result['local_deleted'] is False

    def test_local_only_mode_skips_remote_ref(self, tmp_path: Path) -> None:
        """local_only mode deletes branch and returns remote_ref_deleted=False."""
        _init_repo(tmp_path, branch='main')
        _create_branch(tmp_path, 'feature/x')
        args = Namespace(plan_id=None, project_dir=str(tmp_path), head='feature/x', mode='local_only')

        result = cmd_prune_ref(args)

        assert result['status'] == 'success'
        assert result['local_deleted'] is True
        assert result['remote_ref_deleted'] is False
        assert result['mode'] == 'local_only'

    def test_show_ref_absent_returns_partial(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Remote-tracking ref already absent → partial + remote_ref_deleted=False."""
        _init_repo(tmp_path, branch='main')
        orig = _mod.run_git

        def fake_run_git(args, **kwargs):
            if '--abbrev-ref' in args:
                return (0, 'main', '')
            if '-D' in args:
                return (0, '', '')
            if 'show-ref' in args:
                return (1, '', '')  # ref absent
            return orig(args, **kwargs)

        _patch_run_git(monkeypatch, fake_run_git)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), head='feature/x', mode='local_and_remote')

        result = cmd_prune_ref(args)

        assert result['status'] == 'partial'
        assert result['local_deleted'] is True
        assert result['remote_ref_deleted'] is False
        assert 'already absent' in result['remote_ref_warning']

    def test_update_ref_failure_after_show_ref_returns_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """update-ref -d failure after show-ref confirms ref exists → unexpected_ref_error."""
        _init_repo(tmp_path, branch='main')
        orig = _mod.run_git

        def fake_run_git(args, **kwargs):
            if '--abbrev-ref' in args:
                return (0, 'main', '')
            if '-D' in args:
                return (0, '', '')
            if 'show-ref' in args:
                return (0, '', '')  # ref present
            if 'update-ref' in args:
                return (1, '', 'error: could not delete ref')
            return orig(args, **kwargs)

        _patch_run_git(monkeypatch, fake_run_git)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), head='feature/x', mode='local_and_remote')

        result = cmd_prune_ref(args)

        assert result['status'] == 'error'
        assert result['error_type'] == 'unexpected_ref_error'
        assert result['local_deleted'] is True
        assert result['remote_ref_deleted'] is False

    def test_full_success_local_and_remote(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Both local branch and remote-tracking ref deleted → status=success."""
        _init_repo(tmp_path, branch='main')
        orig = _mod.run_git

        def fake_run_git(args, **kwargs):
            if '--abbrev-ref' in args:
                return (0, 'main', '')
            if '-D' in args:
                return (0, '', '')
            if 'show-ref' in args:
                return (0, '', '')  # ref present
            if 'update-ref' in args:
                return (0, '', '')
            return orig(args, **kwargs)

        _patch_run_git(monkeypatch, fake_run_git)
        args = Namespace(plan_id=None, project_dir=str(tmp_path), head='feature/x', mode='local_and_remote')

        result = cmd_prune_ref(args)

        assert result['status'] == 'success'
        assert result['local_deleted'] is True
        assert result['remote_ref_deleted'] is True
        assert result['head_branch'] == 'feature/x'
        assert result['mode'] == 'local_and_remote'

    def test_envelope_includes_project_dir(self, tmp_path: Path) -> None:
        """Response envelope echoes project_dir when --project-dir is used."""
        args = Namespace(plan_id=None, project_dir=str(tmp_path), head='feature/x', mode='local_and_remote')

        result = cmd_prune_ref(args)

        assert 'project_dir' in result
        assert result['project_dir'] == str(tmp_path)

    def test_envelope_excludes_plan_id_when_project_dir_path(self, tmp_path: Path) -> None:
        """When --project-dir path is used, plan_id must not appear in response."""
        args = Namespace(plan_id=None, project_dir=str(tmp_path), head='feature/x', mode='local_and_remote')

        result = cmd_prune_ref(args)

        assert 'plan_id' not in result


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


class TestCmdPruneRefCli:
    """Subprocess tests for prune-local-and-remote-ref CLI plumbing."""

    def test_project_dir_without_head_returns_error(self, tmp_path: Path) -> None:
        """--project-dir without --head → missing_required_arg TOON error."""
        result = run_script(
            _SCRIPT_PATH, 'prune-local-and-remote-ref',
            '--project-dir', str(tmp_path),
        )

        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'error'
        assert parsed['error_type'] == 'missing_required_arg'

    def test_non_git_project_dir_returns_toon_error(self, tmp_path: Path) -> None:
        """Non-git --project-dir + --head → project_dir_not_a_git_repo."""
        result = run_script(
            _SCRIPT_PATH, 'prune-local-and-remote-ref',
            '--project-dir', str(tmp_path),
            '--head', 'feature/x',
        )

        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'error'
        assert parsed['error_type'] == 'project_dir_not_a_git_repo'

    def test_local_only_mode_accepted(self, tmp_path: Path) -> None:
        """--mode local_only is accepted by argparse (no exit code 2)."""
        result = run_script(
            _SCRIPT_PATH, 'prune-local-and-remote-ref',
            '--project-dir', str(tmp_path),
            '--head', 'feature/x',
            '--mode', 'local_only',
        )

        # Non-git dir → structured error, not argparse exit 2.
        assert result.returncode == 0
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'error'

    def test_help_shows_prune_subcommand(self) -> None:
        """--help lists prune-local-and-remote-ref."""
        result = run_script(_SCRIPT_PATH, '--help')

        assert result.returncode == 0
        assert 'prune-local-and-remote-ref' in result.stdout
