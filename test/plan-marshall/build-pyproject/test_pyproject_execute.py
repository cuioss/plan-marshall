#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _pyproject_execute.py.

Tests the Python execution config and factory-generated functions.

pyproject no longer defines its own ``cmd_run``: it supplies the one-shot
self-heal to ``create_execute_handlers(..., wrap_execute_fn=...)`` and uses the
SHARED factory ``cmd_run`` — the same daemon-routing seam Maven, Gradle, and npm
use. Both the self-heal wrapper and the factory's routing ``cmd_run`` reach the
build through closure variables (``inner_execute`` / ``in_process_execute``),
which are not patchable as module attributes, so every test below patches the
factory-level seams the closures actually call: ``_factory.execute_direct_base``
(the build body) and ``_factory.cmd_run_common`` (the rendering tail).

Also covers the D6 build-queue integration on the in-process leg of that shared
``cmd_run``: it runs the self-heal-wrapped executor inside
``build_queue_slot(plan_id)`` and turns a ``BuildQueueTimeout`` into the
structured ``queue_saturated`` error via ``_emit_queue_timeout``. The
integration tests drive ``cmd_run`` end-to-end through the REAL
``build_queue_slot`` context manager (queue ``_acquire`` / ``_release`` and the
title-token seams mocked on the ``_build_queue_slot`` module) and assert the
four admission paths: admitted-once, blocked-then-admitted, max-retries-exhausted
(structured ``queue_saturated`` error, build NOT run), and plan_id-absent
(pure passthrough, zero queue/token interaction). Each drives the in-process leg
explicitly via ``execution_mode='in_process'`` so no test ever probes a real
daemon; the routing / fallback / daemon-mode fail-loud branches are covered
separately.
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

import _build_execute as build_execute  # noqa: E402
import _build_execute_factory as _factory  # noqa: E402


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


def test_config_has_no_require_wrapper_knob():
    """The require_wrapper gate is removed — ExecuteConfig no longer carries it.
    pyproject keeps no per-resolver wrapper_resolve_fn, so it auto-detects the pw
    wrapper and falls back to the system binary."""
    assert not hasattr(_CONFIG, 'require_wrapper')
    assert _CONFIG.wrapper_resolve_fn is None


def test_execute_direct_absent_wrapper_resolves_system_binary(tmp_path, monkeypatch):
    """With no pw wrapper and pwx absent from PATH, the wrapper auto-resolves to
    the system 'pwx' binary — no wrapper-not-found error and no FileNotFoundError
    during resolution."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setattr(build_execute.shutil, 'which', lambda _cmd: None)

    calls = []

    def _recorder(**kwargs):
        calls.append(kwargs)
        return {'status': 'success', 'exit_code': 0, 'duration_seconds': 0, 'log_file': '', 'command': 'pwx verify'}

    monkeypatch.setattr(_factory, 'execute_direct_base', _recorder)

    result = execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))
    assert result['status'] == 'success'
    assert calls[0]['wrapper'] == 'pwx'


def test_execute_direct_resolves_present_wrapper(tmp_path, monkeypatch):
    """With a present pw, resolution prefers the project wrapper ./pw."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    (tmp_path / 'pw').write_text('#!/bin/sh\n')

    calls = []

    def _recorder(**kwargs):
        calls.append(kwargs)
        return {'status': 'success', 'exit_code': 0, 'duration_seconds': 0, 'log_file': '', 'command': './pw verify'}

    monkeypatch.setattr(_factory, 'execute_direct_base', _recorder)

    result = execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))
    assert result['status'] == 'success'
    assert calls[0]['wrapper'] == './pw'


def _make_log(tmp_path: Path, text: str) -> str:
    log_path = tmp_path / 'build.log'
    log_path.write_text(text)
    return str(log_path)


def _patched_execute_direct(call_results):
    """Build a fake ``execute_direct_base`` returning a sequence of results.

    The self-heal wrapper closes over the factory's inner ``execute_direct``, so
    the patchable seam is the factory-level ``execute_direct_base`` that inner
    callable delegates to. Results are returned verbatim, so identity assertions
    (``result is failure``) still hold through the wrapper.
    """
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
    with patch.object(_factory, 'execute_direct_base', side_effect=fake):
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
    with patch.object(_factory, 'execute_direct_base', side_effect=fake):
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
    with patch.object(_factory, 'execute_direct_base', side_effect=fake):
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
    with patch.object(_factory, 'execute_direct_base', side_effect=fake):
        result = execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))
    assert result is failure
    assert len(calls) == 1
    assert (tmp_path / '.pyprojectx').is_dir()


def test_self_heal_passthrough_on_success(tmp_path):
    """Successful first run is unaffected by the self-heal layer."""
    (tmp_path / '.pyprojectx').mkdir()
    success = {'status': 'success', 'exit_code': 0, 'log_file': '', 'command': './pw verify'}
    fake, calls = _patched_execute_direct([success])
    with patch.object(_factory, 'execute_direct_base', side_effect=fake):
        result = execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))
    assert result is success
    assert len(calls) == 1
    assert not (tmp_path / '.pyprojectx.broken').exists()


# D6: Build-queue integration on the in-process leg of the shared factory
# cmd_run that pyproject now uses.
#
# These tests drive that ``cmd_run`` end-to-end through the REAL
# ``build_queue_slot`` context manager. The queue acquire/release seam
# (``_acquire`` / ``_release_raw``) is mocked on the ``_build_queue_slot``
# module, so the slot's admit / wait / release behaviour is exercised exactly as
# in production while the build itself is replaced by a recorder installed at
# ``_factory.execute_direct_base`` and ``cmd_run_common`` (downstream of the
# slot) is stubbed to a no-op on the factory module. ``time.sleep`` is patched
# to a no-op so the 60s blocked-poll wait is never actually slept. Every
# ``cmd_run`` call passes ``execution_mode='in_process'`` so the routing branch
# is skipped outright and no daemon is ever probed.


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

    ``cmd_run`` invokes the self-heal-wrapped executor through a closure
    variable, so the recorder is installed one level deeper at
    ``_factory.execute_direct_base`` — the seam that closure ultimately calls.
    It returns a success result, so the self-heal never triggers a retry and one
    ``cmd_run`` maps to exactly one recorded call. That lets the integration
    tests assert the build ran exactly once (admitted paths) or never
    (saturation path) without spawning a real subprocess."""

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
    no-op. Returns the exec_recorder.

    The recorder and the ``cmd_run_common`` stub go on ``_factory`` — the shared
    factory module that owns the routing ``cmd_run`` pyproject now uses — not on
    ``_pyproject_execute_mod``, which no longer defines either. The routing
    audit's work-log sink (``log_entry``) is also stubbed so an in-process
    resolution never writes to a real plan log; its stderr half is left intact
    and does not reach the ``capsys`` stdout the saturation test reads.
    """
    monkeypatch.setattr(bqs, '_acquire', double.acquire)
    monkeypatch.setattr(bqs, '_release_raw', double.release)

    exec_recorder = _ExecRecorder()
    monkeypatch.setattr(_factory, 'execute_direct_base', exec_recorder)
    monkeypatch.setattr(_factory, 'cmd_run_common', lambda **_kwargs: 0)
    monkeypatch.setattr(_factory, 'log_entry', lambda *_args, **_kwargs: None)
    return exec_recorder


class TestPyprojectCmdRunQueueAdmitted:
    """Admitted-immediately: the build runs once inside the slot and the slot is
    released."""

    def test_admitted_runs_build_once_inside_slot(self, monkeypatch):
        double = _QueueDouble([{'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-1'}])
        exec_recorder = _install_queue(monkeypatch, double)

        rc = cmd_run(
            argparse.Namespace(
                command_args='verify', plan_id='P', format='toon', execution_mode='in_process'
            )
        )

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

        rc = cmd_run(
            argparse.Namespace(
                command_args='verify', plan_id='P', format='toon', execution_mode='in_process'
            )
        )

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

        cmd_run(
            argparse.Namespace(
                command_args='verify', plan_id='P', format='toon', execution_mode='in_process'
            )
        )

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

        rc = cmd_run(
            argparse.Namespace(
                command_args='verify', plan_id='P', format='toon', execution_mode='in_process'
            )
        )

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

        rc = cmd_run(
            argparse.Namespace(
                command_args='verify', plan_id=plan_id, format='toon', execution_mode='in_process'
            )
        )

        assert rc == 0
        assert len(exec_recorder.calls) == 1
        assert double.acquire_calls == []
        assert double.release_calls == []

    def test_missing_plan_id_attr_is_passthrough(self, monkeypatch):
        """A Namespace with no plan_id attribute at all (getattr default None)
        is also a pure passthrough."""
        double = _QueueDouble([])
        exec_recorder = _install_queue(monkeypatch, double)

        rc = cmd_run(
            argparse.Namespace(command_args='verify', format='toon', execution_mode='in_process')
        )

        assert rc == 0
        assert len(exec_recorder.calls) == 1
        assert double.acquire_calls == []
