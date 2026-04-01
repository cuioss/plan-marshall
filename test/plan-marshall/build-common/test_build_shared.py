"""Tests for build-common shared utilities."""

import importlib
import sys
from pathlib import Path

# Add script path for imports
_SCRIPT_DIR = Path(__file__).resolve().parents[3] / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'build-common' / 'scripts'
sys.path.insert(0, str(_SCRIPT_DIR))

_build_shared = importlib.import_module('_build_shared')


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


class TestExtractLogScope:
    """Tests for extract_log_scope()."""

    # Maven scope extraction
    def test_maven_pl_argument(self):
        assert _build_shared.extract_log_scope('verify -pl my-module', 'maven') == 'my-module'

    def test_maven_pl_with_profile(self):
        assert _build_shared.extract_log_scope('verify -Ppre-commit -pl core-module', 'maven') == 'core-module'

    def test_maven_no_pl(self):
        assert _build_shared.extract_log_scope('clean verify', 'maven') == 'default'

    # Gradle scope extraction
    def test_gradle_module_task_prefix(self):
        assert _build_shared.extract_log_scope(':core:build', 'gradle') == 'core'

    def test_gradle_nested_module(self):
        assert _build_shared.extract_log_scope(':sub:module:test', 'gradle') == 'sub'

    def test_gradle_no_prefix(self):
        assert _build_shared.extract_log_scope('build', 'gradle') == 'default'

    # npm scope extraction
    def test_npm_workspace_equals(self):
        assert _build_shared.extract_log_scope('run test --workspace=my-pkg', 'npm') == 'my-pkg'

    def test_npm_workspace_space(self):
        assert _build_shared.extract_log_scope('run test --workspace my-pkg', 'npm') == 'my-pkg'

    def test_npm_prefix(self):
        assert _build_shared.extract_log_scope('run test --prefix packages/core', 'npm') == 'packages/core'

    def test_npm_no_workspace(self):
        assert _build_shared.extract_log_scope('run test', 'npm') == 'default'

    # Python scope extraction
    def test_python_returns_default(self):
        assert _build_shared.extract_log_scope('compile plan-marshall', 'python') == 'default'

    # Unknown build tool
    def test_unknown_tool_returns_default(self):
        assert _build_shared.extract_log_scope('some args', 'unknown') == 'default'
