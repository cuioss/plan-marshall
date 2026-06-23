#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _pyproject_execute.py.

Tests the Python execution config and factory-generated functions.

Also covers the D6 build-queue integration at the pyproject ``cmd_run`` wrap
site: ``cmd_run`` runs ``execute_direct`` (the self-heal wrapper) inside
``build_queue_slot(plan_id)`` and turns a ``BuildQueueTimeout`` into the
structured ``queue_saturated`` error via ``_emit_queue_timeout``. The
integration tests drive ``cmd_run`` end-to-end through the REAL
``build_queue_slot`` context manager (queue ``_acquire`` / ``_release`` and the
title-token seams mocked on the ``_build_queue_slot`` module) and assert the
four admission paths: admitted-once, blocked-then-admitted, max-retries-exhausted
(structured ``queue_saturated`` error, build NOT run), and plan_id-absent
(pure passthrough, zero queue/token interaction).
"""

# Mock runtime-only modules before importing
import argparse
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import _build_queue_slot as bqs
import pytest

from conftest import load_script_module

sys.modules.setdefault('plan_logging', MagicMock(log_entry=MagicMock()))
sys.modules.setdefault('run_config', MagicMock(timeout_get=MagicMock(return_value=300), timeout_set=MagicMock()))


_pyproject_execute_mod = load_script_module('plan-marshall', 'build-pyproject', '_pyproject_execute.py', '_pyproject_execute')

_CONFIG = _pyproject_execute_mod._CONFIG
execute_direct = _pyproject_execute_mod.execute_direct
cmd_run = _pyproject_execute_mod.cmd_run


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


def test_scope_fn_default_for_single_arg():
    """Python scope is 'default' for single-arg commands."""
    assert _CONFIG.scope_fn('verify') == 'default'


def test_scope_fn_extracts_module():
    """Python scope extracts module name from second arg."""
    assert _CONFIG.scope_fn('module-tests core') == 'core'
    assert _CONFIG.scope_fn('verify plan-marshall') == 'plan-marshall'


def test_build_command_fn():
    """Builds command parts from wrapper and args."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('./pw', 'verify', '/tmp/log.log')
    assert cmd_parts == ['./pw', 'verify']
    assert cmd_str == './pw verify'


def test_build_command_fn_with_module():
    """Includes module argument in command."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('./pw', 'module-tests core', '/tmp/log.log')
    assert cmd_parts == ['./pw', 'module-tests', 'core']


def test_config_require_wrapper_default_on():
    """pyproject migrated to the factory gate: require_wrapper=True and the old
    per-resolver wrapper_resolve_fn is removed."""
    assert _CONFIG.require_wrapper is True
    assert _CONFIG.wrapper_resolve_fn is None


def test_execute_direct_error_on_missing_wrapper(tmp_path):
    """execute_direct returns error result when wrapper not found, anchored on
    the canonical factory-gate message."""
    with patch('_build_execute.shutil.which', return_value=None):
        result = execute_direct(
            args='verify',
            command_key='python:verify',
            project_dir=str(tmp_path),
        )
        assert result['status'] == 'error'
        assert result['exit_code'] == -1
        assert 'No python wrapper found' in result['error']


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
    with patch.object(_pyproject_execute_mod, '_inner_execute_direct', side_effect=fake):
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
    with patch.object(_pyproject_execute_mod, '_inner_execute_direct', side_effect=fake):
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
    with patch.object(_pyproject_execute_mod, '_inner_execute_direct', side_effect=fake):
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
    with patch.object(_pyproject_execute_mod, '_inner_execute_direct', side_effect=fake):
        result = execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))
    assert result is failure
    assert len(calls) == 1
    assert (tmp_path / '.pyprojectx').is_dir()


def test_self_heal_passthrough_on_success(tmp_path):
    """Successful first run is unaffected by the self-heal layer."""
    (tmp_path / '.pyprojectx').mkdir()
    success = {'status': 'success', 'exit_code': 0, 'log_file': '', 'command': './pw verify'}
    fake, calls = _patched_execute_direct([success])
    with patch.object(_pyproject_execute_mod, '_inner_execute_direct', side_effect=fake):
        result = execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))
    assert result is success
    assert len(calls) == 1
    assert not (tmp_path / '.pyprojectx.broken').exists()


# D6: Build-queue integration at the pyproject cmd_run wrap site.
#
# These tests drive the pyproject ``cmd_run`` end-to-end through the REAL
# ``build_queue_slot`` context manager. The queue acquire/release seam
# (``_acquire`` / ``_release_raw``) is mocked on the ``_build_queue_slot``
# module, so the slot's admit / wait / release behaviour is exercised exactly as
# in production while the build itself (the module-level ``execute_direct``
# self-heal wrapper) is replaced by a recorder and ``cmd_run_common`` (downstream
# of the slot) is stubbed to a no-op. ``time.sleep`` is patched to a no-op so the
# 60s blocked-poll wait is never actually slept.


class _QueueDouble:
    """Scriptable acquire/release double installed over ``_build_queue_slot``'s
    ``_acquire`` / ``_release_raw`` seams. Acquire responses are popped
    left-to-right (the last repeats); every release is recorded."""

    def __init__(self, acquire_responses: list[dict]):
        self._acquire_responses = list(acquire_responses)
        self.acquire_calls: list[str] = []
        self.release_calls: list[tuple[str, str]] = []

    def acquire(self, plan_id: str) -> dict:
        self.acquire_calls.append(plan_id)
        if not self._acquire_responses:
            return {'status': 'error', 'error': 'no scripted acquire response'}
        return self._acquire_responses.pop(0) if len(self._acquire_responses) > 1 else self._acquire_responses[0]

    def release(self, plan_id: str, admission_id: str) -> dict:
        self.release_calls.append((plan_id, admission_id))
        return {'status': 'success', 'action': 'released'}

    @property
    def released_ids(self) -> list[str]:
        return [aid for _plan, aid in self.release_calls]


class _ExecRecorder:
    """Records whether (and with what args) the pyproject build body ran.

    ``cmd_run`` calls the module-level ``execute_direct`` (the self-heal
    wrapper). Patching ``_pyproject_execute_mod.execute_direct`` with this
    recorder lets the integration tests assert the build ran exactly once
    (admitted paths) or never (saturation path) without spawning a real
    subprocess."""

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return {
            'status': 'success',
            'exit_code': 0,
            'duration_seconds': 0,
            'log_file': '',
            'command': 'pw verify',
        }

    @property
    def ran(self) -> bool:
        return len(self.calls) > 0


@pytest.fixture(autouse=True)
def _no_sleep_queue(monkeypatch: pytest.MonkeyPatch):
    """Never actually sleep 60s in a unit test — patch the slot's time.sleep."""
    monkeypatch.setattr(bqs.time, 'sleep', lambda _s: None)


def _install_queue(monkeypatch: pytest.MonkeyPatch, double: _QueueDouble):
    """Install the queue double + exec recorder, and stub ``cmd_run_common`` to a
    no-op. Returns the exec_recorder."""
    monkeypatch.setattr(bqs, '_acquire', double.acquire)
    monkeypatch.setattr(bqs, '_release_raw', double.release)

    exec_recorder = _ExecRecorder()
    monkeypatch.setattr(_pyproject_execute_mod, 'execute_direct', exec_recorder)
    monkeypatch.setattr(_pyproject_execute_mod, 'cmd_run_common', lambda **_kwargs: 0)
    return exec_recorder


class TestPyprojectCmdRunQueueAdmitted:
    """Admitted-immediately: the build runs once inside the slot and the slot is
    released."""

    def test_admitted_runs_build_once_inside_slot(self, monkeypatch):
        double = _QueueDouble([{'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-1'}])
        exec_recorder = _install_queue(monkeypatch, double)

        rc = cmd_run(argparse.Namespace(command_args='verify', plan_id='P', format='toon'))

        assert rc == 0
        assert exec_recorder.ran is True
        assert len(exec_recorder.calls) == 1
        assert 'P:uuid-1' in double.released_ids


class TestPyprojectCmdRunQueueBlockedThenAdmitted:
    """Blocked-then-admitted: the first poll is blocked (sleep mocked), a later
    poll admits, and only then does the build run."""

    def test_blocked_then_admitted_waits_then_runs(self, monkeypatch):
        double = _QueueDouble(
            [
                {'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-A'},
                {'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-B'},
            ]
        )
        exec_recorder = _install_queue(monkeypatch, double)

        rc = cmd_run(argparse.Namespace(command_args='verify', plan_id='P', format='toon'))

        assert rc == 0
        assert len(exec_recorder.calls) == 1
        # The blocked id is NOT released before re-polling — re-poll is idempotent
        # so the plan keeps its FIFO position. Only the final admitted id is
        # released in the finally.
        assert 'P:uuid-A' not in double.released_ids
        assert double.released_ids == ['P:uuid-B']

    def test_blocked_then_admitted_sleeps_once_per_retry(self, monkeypatch):
        sleeps: list[int] = []
        monkeypatch.setattr(bqs.time, 'sleep', lambda s: sleeps.append(s))
        double = _QueueDouble(
            [
                {'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-A'},
                {'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-B'},
                {'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-C'},
            ]
        )
        exec_recorder = _install_queue(monkeypatch, double)

        cmd_run(argparse.Namespace(command_args='verify', plan_id='P', format='toon'))

        assert sleeps == [bqs._WAIT_SECONDS, bqs._WAIT_SECONDS]
        assert len(exec_recorder.calls) == 1


class TestPyprojectCmdRunQueueSaturated:
    """Max-retries-exhausted: the queue stays blocked past max_retries, so
    cmd_run returns the structured ``queue_saturated`` error, releases the
    queued id, and NEVER runs the build."""

    def test_saturation_returns_structured_error_without_running_build(self, monkeypatch, capsys):
        monkeypatch.setattr(bqs, '_resolve_max_retries', lambda: 2)
        double = _QueueDouble([{'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-X'}])
        exec_recorder = _install_queue(monkeypatch, double)

        rc = cmd_run(argparse.Namespace(command_args='verify', plan_id='P', format='toon'))

        assert rc == 1
        assert exec_recorder.ran is False
        out = capsys.readouterr().out
        # cmd_run renders the saturation via the shared _emit_queue_timeout.
        assert 'queue_saturated' in out
        assert 'try again later' in out
        assert 'P' in out
        assert 'P:uuid-X' in double.released_ids


class TestPyprojectCmdRunPlanIdAbsentPassthrough:
    """plan_id-absent: pure passthrough — the build runs with ZERO queue
    interaction (the backward-compatibility guarantee for plan-less builds)."""

    @pytest.mark.parametrize('plan_id', [None, ''])
    def test_no_plan_id_runs_build_with_no_queue_interaction(self, monkeypatch, plan_id):
        double = _QueueDouble([])
        exec_recorder = _install_queue(monkeypatch, double)

        rc = cmd_run(argparse.Namespace(command_args='verify', plan_id=plan_id, format='toon'))

        assert rc == 0
        assert len(exec_recorder.calls) == 1
        assert double.acquire_calls == []
        assert double.release_calls == []

    def test_missing_plan_id_attr_is_passthrough(self, monkeypatch):
        """A Namespace with no plan_id attribute at all (getattr default None)
        is also a pure passthrough."""
        double = _QueueDouble([])
        exec_recorder = _install_queue(monkeypatch, double)

        rc = cmd_run(argparse.Namespace(command_args='verify', format='toon'))

        assert rc == 0
        assert len(exec_recorder.calls) == 1
        assert double.acquire_calls == []
