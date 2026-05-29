"""Tests for _build_shared utilities and resolve_project_dir executor resolution."""

import importlib
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

    _executor_path() delegates to file_ops.get_executor_path() (worktree-safe
    resolution via git-common-dir) and re-wraps a RuntimeError (no git repo)
    into WorktreeResolutionError so callers can surface the message verbatim.
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
