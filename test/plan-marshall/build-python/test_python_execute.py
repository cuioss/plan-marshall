#!/usr/bin/env python3
"""Tests for _python_execute.py.

Tests the Python execution config and factory-generated functions.
"""

# Mock runtime-only modules before importing
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.modules.setdefault('plan_logging', MagicMock(log_entry=MagicMock()))
sys.modules.setdefault('run_config', MagicMock(timeout_get=MagicMock(return_value=300), timeout_set=MagicMock()))

# Tier 2 direct imports via importlib for uniform import style
import importlib.util  # noqa: E402

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'build-python'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_python_execute_mod = _load_module('_python_execute', '_python_execute.py')

_CONFIG = _python_execute_mod._CONFIG
execute_direct = _python_execute_mod.execute_direct

# =============================================================================
# Config Tests
# =============================================================================


def test_config_tool_name():
    """Config has correct tool name."""
    assert _CONFIG.tool_name == 'python'


def test_config_wrapper_names():
    """Config has correct wrapper names for pyprojectx."""
    assert _CONFIG.unix_wrapper == 'pw'
    assert _CONFIG.windows_wrapper == 'pw.bat'
    assert _CONFIG.system_fallback == 'pwx'


def test_config_default_timeout():
    """Config has 300s default timeout."""
    assert _CONFIG.default_timeout == 300


def test_config_capture_strategy():
    """Config uses stdout redirect (not log flag)."""
    from _build_execute import CaptureStrategy

    assert _CONFIG.capture_strategy == CaptureStrategy.STDOUT_REDIRECT


# =============================================================================
# Command Key Function
# =============================================================================


def test_command_key_fn_verify():
    """Extracts 'verify' from args."""
    assert _CONFIG.command_key_fn('verify') == 'verify'


def test_command_key_fn_module_tests():
    """Scope-aware: module suffix included so full-scope and module-scoped
    invocations learn distinct adaptive timeouts."""
    assert _CONFIG.command_key_fn('module-tests core') == 'module_tests_core'


def test_command_key_fn_empty():
    """Returns 'default' for empty args."""
    assert _CONFIG.command_key_fn('') == 'default'


# =============================================================================
# Scope Function
# =============================================================================


def test_scope_fn_default_for_single_arg():
    """Python scope is 'default' for single-arg commands."""
    assert _CONFIG.scope_fn('verify') == 'default'


def test_scope_fn_extracts_module():
    """Python scope extracts module name from second arg."""
    assert _CONFIG.scope_fn('module-tests core') == 'core'
    assert _CONFIG.scope_fn('verify plan-marshall') == 'plan-marshall'


# =============================================================================
# Build Command Function
# =============================================================================


def test_build_command_fn():
    """Builds command parts from wrapper and args."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('./pw', 'verify', '/tmp/log.log')
    assert cmd_parts == ['./pw', 'verify']
    assert cmd_str == './pw verify'


def test_build_command_fn_with_module():
    """Includes module argument in command."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('./pw', 'module-tests core', '/tmp/log.log')
    assert cmd_parts == ['./pw', 'module-tests', 'core']


# =============================================================================
# Wrapper Resolution
# =============================================================================


def test_wrapper_resolve_raises_when_missing(tmp_path):
    """Raises FileNotFoundError when no wrapper found."""
    with patch('_build_execute.shutil.which', return_value=None):
        with pytest.raises(FileNotFoundError, match='No pyprojectx wrapper found'):
            _CONFIG.wrapper_resolve_fn(str(tmp_path))


def test_execute_direct_error_on_missing_wrapper(tmp_path):
    """execute_direct returns error result when wrapper not found."""
    with patch('_build_execute.shutil.which', return_value=None):
        result = execute_direct(
            args='verify',
            command_key='python:verify',
            project_dir=str(tmp_path),
        )
        assert result['status'] == 'error'
        assert result['exit_code'] == -1


# =============================================================================
# Self-Heal Retry
# =============================================================================


def _make_log(tmp_path: Path, text: str) -> str:
    log_path = tmp_path / 'build.log'
    log_path.write_text(text)
    return str(log_path)


def _patched_execute_direct(call_results):
    """Patch the inner execute_direct to return a sequence of results."""
    iterator = iter(call_results)
    calls = []

    def fake(**kwargs):
        calls.append(kwargs)
        return next(iterator)

    return fake, calls


def test_self_heal_retries_on_uv_missing(tmp_path):
    """Self-heal renames .pyprojectx and retries when 'uv: command not found' is observed."""
    cache_dir = tmp_path / '.pyprojectx'
    cache_dir.mkdir()
    log_file = _make_log(tmp_path, '/bin/sh: uv: command not found\nexit 127')
    failure = {'status': 'error', 'exit_code': 127, 'log_file': log_file, 'command': './pw verify', 'error': ''}
    success = {'status': 'success', 'exit_code': 0, 'log_file': log_file, 'command': './pw verify'}
    fake, calls = _patched_execute_direct([failure, success])
    with patch.object(_python_execute_mod, '_inner_execute_direct', side_effect=fake):
        result = execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))
    assert result['status'] == 'success'
    assert len(calls) == 2
    assert (tmp_path / '.pyprojectx.broken').is_dir()
    assert not cache_dir.exists()


def test_self_heal_retries_on_directory_not_empty(tmp_path):
    """Self-heal retries on 'Failed to create virtual environment ... Directory not empty'."""
    (tmp_path / '.pyprojectx').mkdir()
    log_text = (
        'error: Failed to create virtual environment\n'
        'Caused by: failed to remove directory bin: Directory not empty (os error 66)\n'
    )
    log_file = _make_log(tmp_path, log_text)
    failure = {'status': 'error', 'exit_code': 1, 'log_file': log_file, 'command': './pw verify', 'error': ''}
    success = {'status': 'success', 'exit_code': 0, 'log_file': log_file, 'command': './pw verify'}
    fake, calls = _patched_execute_direct([failure, success])
    with patch.object(_python_execute_mod, '_inner_execute_direct', side_effect=fake):
        result = execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))
    assert result['status'] == 'success'
    assert len(calls) == 2
    assert (tmp_path / '.pyprojectx.broken').is_dir()


def test_self_heal_skipped_for_unrelated_failure(tmp_path):
    """Unrelated errors (e.g. test failure) do not trigger self-heal."""
    (tmp_path / '.pyprojectx').mkdir()
    log_file = _make_log(tmp_path, 'FAILED tests/test_foo.py::test_bar - AssertionError')
    failure = {'status': 'error', 'exit_code': 1, 'log_file': log_file, 'command': './pw verify', 'error': ''}
    fake, calls = _patched_execute_direct([failure])
    with patch.object(_python_execute_mod, '_inner_execute_direct', side_effect=fake):
        result = execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))
    assert result is failure
    assert len(calls) == 1
    assert not (tmp_path / '.pyprojectx.broken').exists()
    assert (tmp_path / '.pyprojectx').is_dir()


def test_self_heal_skipped_when_broken_dir_already_exists(tmp_path):
    """Self-heal short-circuits when .pyprojectx.broken already exists."""
    (tmp_path / '.pyprojectx').mkdir()
    (tmp_path / '.pyprojectx.broken').mkdir()
    log_file = _make_log(tmp_path, '/bin/sh: uv: command not found')
    failure = {'status': 'error', 'exit_code': 127, 'log_file': log_file, 'command': './pw verify', 'error': ''}
    fake, calls = _patched_execute_direct([failure])
    with patch.object(_python_execute_mod, '_inner_execute_direct', side_effect=fake):
        result = execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))
    assert result is failure
    assert len(calls) == 1
    assert (tmp_path / '.pyprojectx').is_dir()


def test_self_heal_passthrough_on_success(tmp_path):
    """Successful first run is unaffected by the self-heal layer."""
    (tmp_path / '.pyprojectx').mkdir()
    success = {'status': 'success', 'exit_code': 0, 'log_file': '', 'command': './pw verify'}
    fake, calls = _patched_execute_direct([success])
    with patch.object(_python_execute_mod, '_inner_execute_direct', side_effect=fake):
        result = execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))
    assert result is success
    assert len(calls) == 1
    assert not (tmp_path / '.pyprojectx.broken').exists()
