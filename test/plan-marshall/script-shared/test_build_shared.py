"""Tests for _build_shared utilities and resolve_project_dir executor resolution."""

import importlib
import os
import sys
from pathlib import Path

import pytest

# Add script path for imports
_SCRIPT_DIR = (
    Path(__file__).resolve().parents[3]
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'script-shared'
    / 'scripts'
    / 'build'
)
sys.path.insert(0, str(_SCRIPT_DIR))

# resolve_project_dir.py lives in the script-shared scripts/ dir (one level up
# from build/). Add it so `import resolve_project_dir` resolves regardless of
# the conftest PYTHONPATH wiring.
sys.path.insert(0, str(_SCRIPT_DIR.parent))

_build_shared = importlib.import_module('_build_shared')
_resolve_project_dir = importlib.import_module('resolve_project_dir')


class TestGetBashTimeout:
    """Tests for get_bash_timeout()."""

    def test_adds_buffer_to_inner_timeout(self):
        result = _build_shared.get_bash_timeout(300)
        assert result == 330  # 300 + 30 buffer

    def test_small_timeout(self):
        result = _build_shared.get_bash_timeout(10)
        assert result == 40  # 10 + 30 buffer

    def test_zero_timeout(self):
        result = _build_shared.get_bash_timeout(0)
        assert result == 30  # 0 + 30 buffer

    def test_buffer_constant_is_30(self):
        assert _build_shared.OUTER_TIMEOUT_BUFFER == 30


class TestResolveProjectDirExecutorPath:
    """Tests for resolve_project_dir._executor_path().

    _executor_path() delegates to file_ops.get_executor_path() (cwd-relative
    resolution via the uniform cwd rule, ADR-002) and re-wraps a RuntimeError
    (no git repo) into WorktreeResolutionError so callers can surface the
    message verbatim.
    """

    def test_returns_resolved_executor_path(self, tmp_path, monkeypatch):
        """When get_executor_path succeeds, _executor_path returns its result."""
        executor = tmp_path / 'execute-script.py'
        monkeypatch.setattr(_resolve_project_dir, 'get_executor_path', lambda: executor)
        result = _resolve_project_dir._executor_path()
        assert result == executor

    def test_runtime_error_wrapped_in_worktree_resolution_error(self, monkeypatch):
        """A RuntimeError from get_executor_path becomes WorktreeResolutionError."""
        def _raise():
            raise RuntimeError('no git repository')
        monkeypatch.setattr(_resolve_project_dir, 'get_executor_path', _raise)
        with pytest.raises(_resolve_project_dir.WorktreeResolutionError, match='Cannot locate executor'):
            _resolve_project_dir._executor_path()


class TestResolveProjectDirMainCheckoutRoot:
    """Tests for resolve_project_dir._main_checkout_root().

    _main_checkout_root() is the fallback returned when neither --plan-id nor
    --project-dir is supplied, and when --plan-id resolves to use_worktree=false.
    Under the uniform cwd rule (ADR-002) it resolves cwd-relatively via
    marketplace_paths._find_plan_root_from_cwd() — the nearest ancestor of cwd
    containing .plan/local — NOT via git rev-parse --show-toplevel. These tests
    lock in that cwd-relative routing behaviour.
    """

    def test_returns_cwd_relative_plan_root(self, tmp_path, monkeypatch):
        """When _find_plan_root_from_cwd resolves a root, it is returned verbatim."""
        plan_root = tmp_path / 'checkout'
        monkeypatch.setattr(_resolve_project_dir, '_find_plan_root_from_cwd', lambda: plan_root)
        result = _resolve_project_dir._main_checkout_root()
        assert result == str(plan_root)

    def test_falls_back_to_cwd_when_plan_root_unresolvable(self, tmp_path, monkeypatch):
        """When no .plan/local ancestor exists, the absolute cwd is the last-ditch fallback."""
        monkeypatch.setattr(_resolve_project_dir, '_find_plan_root_from_cwd', lambda: None)
        monkeypatch.chdir(tmp_path)
        result = _resolve_project_dir._main_checkout_root()
        # tmp_path may be a symlink target on macOS; compare resolved absolute paths.
        assert result == os.path.abspath(os.getcwd())

    def test_neither_flag_routes_through_main_checkout_root(self, monkeypatch):
        """resolve_project_dir(None, None) delegates to the cwd-relative resolver."""
        monkeypatch.setattr(_resolve_project_dir, '_main_checkout_root', lambda: '/tmp/cwd-relative-root')
        resolved = _resolve_project_dir.resolve_project_dir(None, '.', default='.')
        assert resolved == '/tmp/cwd-relative-root'

    def test_plan_id_use_worktree_false_routes_through_main_checkout_root(self, monkeypatch):
        """--plan-id with use_worktree=false falls back to the cwd-relative resolver."""
        monkeypatch.setattr(_resolve_project_dir, '_query_worktree_path', lambda _pid: (False, ''))
        monkeypatch.setattr(_resolve_project_dir, '_main_checkout_root', lambda: '/tmp/cwd-relative-root')
        resolved = _resolve_project_dir.resolve_project_dir('some-plan', '.', default='.')
        assert resolved == '/tmp/cwd-relative-root'
