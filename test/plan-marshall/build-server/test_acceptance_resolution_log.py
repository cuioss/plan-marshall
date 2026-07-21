#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Acceptance: the client's build-routing resolution line reaches a durable sink.

Every ``cmd_run`` resolution — ``routed``, ``in_process`` (with a named fallback
reason), and the ``execution_mode=daemon`` ``fail-loud`` refusal — records ONE
``[BUILD-SERVER] resolved build (...)`` line. The line must reach a sink that
actually survives: this build subprocess configures no logging handler, so a
bare ``logger.info`` emit is discarded by Python's last-resort WARNING threshold
and the diagnostic is lost. Each test therefore asserts BOTH sinks — the
captured ``plan_logging`` work log (via the ``factory.log_entry`` seam) and the
unconditional stderr line — so a regression back to a logger-only emit fails.
"""

from __future__ import annotations

import sys
from argparse import Namespace
from contextlib import contextmanager
from typing import Any

import pytest
from conftest import get_script_path

_SHARED_SCRIPTS = get_script_path('plan-marshall', 'script-shared', 'marketplace_paths.py').parent
_BUILD_DIR = _SHARED_SCRIPTS / 'build'
if str(_BUILD_DIR) not in sys.path:
    sys.path.insert(0, str(_BUILD_DIR))

import _build_execute_factory as factory  # noqa: E402
from _build_execute import CaptureStrategy  # noqa: E402

_MAVEN_NOTATION = 'plan-marshall:build-maven:maven'


def _config(**overrides: Any) -> factory.ExecuteConfig:
    """A minimal ExecuteConfig for driving cmd_run in these tests."""
    base: dict[str, Any] = {
        'tool_name': 'maven',
        'unix_wrapper': 'mvnw',
        'windows_wrapper': 'mvnw.cmd',
        'system_fallback': 'mvn',
        'capture_strategy': CaptureStrategy.TOOL_LOG_FLAG,
        'build_command_fn': factory.default_build_command_fn,
        'scope_fn': lambda a: 'default',
        'command_key_fn': factory.default_command_key_fn,
    }
    base.update(overrides)
    return factory.ExecuteConfig(**base)


def _run_args(**overrides: Any) -> Namespace:
    """The cmd_run argv Namespace, defaulting to a plan-bound auto-mode build."""
    base: dict[str, Any] = {
        'command_args': 'verify core',
        'project_dir': '/tree',
        'plan_id': 'plan-x',
        'format': 'toon',
        'mode': 'actionable',
        'timeout': None,
        'execution_mode': 'auto',
    }
    base.update(overrides)
    return Namespace(**base)


class _FakeClient:
    """A stand-in for the build_server client with scripted verb responses."""

    def __init__(self, preflight: dict, submit: dict | None = None, wait: dict | None = None):
        self._preflight = preflight
        self._submit = submit or {'status': 'success', 'job_id': 'JOB-1'}
        self._wait = wait or {'status': 'success', 'job_status': 'success'}

    def run_preflight(self, _args):
        return self._preflight

    def run_submit(self, _args):
        return self._submit

    def run_wait(self, _args):
        return self._wait


@pytest.fixture(autouse=True)
def _no_reentrancy(monkeypatch):
    """The re-entrancy marker is absent, so routing is attempted normally."""
    monkeypatch.delenv('MARSHALLD_JOB', raising=False)


@pytest.fixture
def captured(monkeypatch) -> list[tuple[str, str | None, str, str]]:
    """Record every ``log_entry`` call the factory makes at the capture seam."""
    calls: list[tuple[str, str | None, str, str]] = []
    monkeypatch.setattr(
        factory, 'log_entry', lambda log_type, plan_id, level, message: calls.append(
            (log_type, plan_id, level, message)
        )
    )
    return calls


def _install_in_process_stubs(monkeypatch) -> None:
    """Stub the in-process build tail so cmd_run reaches its resolution record."""
    monkeypatch.setattr(
        factory, 'execute_direct_base',
        lambda **kw: {'status': 'success', 'exit_code': 0, 'duration_seconds': 1,
                      'log_file': 'l', 'command': 'c'},
    )

    @contextmanager
    def _slot(plan_id, *, routed=False):
        yield

    monkeypatch.setattr(factory, 'build_queue_slot', _slot)
    monkeypatch.setattr(factory, 'cmd_run_common', lambda **kw: 0)


def test_routed_resolution_reaches_the_captured_sink(monkeypatch, capsys, captured):
    # Arrange: a ready daemon that accepts the job and drives it to success.
    monkeypatch.setattr(
        factory, '_load_build_server',
        lambda: _FakeClient(preflight={'status': 'success', 'preflight': 'ready'}),
    )
    monkeypatch.setattr(factory, 'cmd_run_common', lambda **kw: 0)
    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)

    # Act
    rc = cmd_run(_run_args(execution_mode='auto'))

    # Assert: one captured work-log entry at INFO, plus the stderr parity line.
    assert rc == 0
    assert len(captured) == 1
    log_type, plan_id, level, message = captured[0]
    assert (log_type, plan_id, level) == ('work', 'plan-x', 'INFO')
    assert 'requested=auto, resolved=routed' in message
    assert f'notation={_MAVEN_NOTATION}' in message
    assert message in capsys.readouterr().err


def test_in_process_fallback_reason_is_captured_at_warning(monkeypatch, capsys, captured):
    # Arrange: the daemon is down, so auto mode falls back and names the reason.
    monkeypatch.setattr(
        factory, '_load_build_server',
        lambda: _FakeClient(preflight={'status': 'success', 'preflight': 'down', 'reason': 'socket_absent'}),
    )
    _install_in_process_stubs(monkeypatch)
    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)

    # Act
    rc = cmd_run(_run_args(execution_mode='auto'))

    # Assert: a named fallback reason is a degradation ⇒ captured at WARNING.
    assert rc == 0
    assert len(captured) == 1
    log_type, plan_id, level, message = captured[0]
    assert (log_type, plan_id, level) == ('work', 'plan-x', 'WARNING')
    assert 'requested=auto, resolved=in_process' in message
    assert 'reason=socket_absent' in message
    assert message in capsys.readouterr().err


def test_daemon_fail_loud_resolution_is_captured_at_warning(monkeypatch, capsys, captured):
    # Arrange: execution_mode=daemon against a down daemon ⇒ hard refusal.
    monkeypatch.setattr(
        factory, '_load_build_server',
        lambda: _FakeClient(preflight={'status': 'success', 'preflight': 'down', 'reason': 'socket_absent'}),
    )
    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)

    # Act
    rc = cmd_run(_run_args(execution_mode='daemon'))

    # Assert: the refusal is recorded before the error envelope is emitted.
    assert rc == 1
    assert len(captured) == 1
    log_type, plan_id, level, message = captured[0]
    assert (log_type, plan_id, level) == ('work', 'plan-x', 'WARNING')
    assert 'requested=daemon, resolved=fail-loud' in message
    assert 'reason=socket_absent' in message
    assert message in capsys.readouterr().err


def test_plan_less_build_still_writes_stderr_and_captures_nothing(monkeypatch, capsys, captured):
    # Arrange: a plan-less build has no per-plan work log to write to.
    _install_in_process_stubs(monkeypatch)
    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)

    # Act
    rc = cmd_run(_run_args(plan_id=None, execution_mode='in_process'))

    # Assert: stderr still carries the line; the captured sink is untouched.
    assert rc == 0
    assert captured == []
    assert 'requested=in_process, resolved=in_process' in capsys.readouterr().err
