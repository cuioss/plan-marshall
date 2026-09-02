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

import argparse
import copy
from contextlib import contextmanager
from typing import Any

import pytest
from _build_extension_fixtures import build_scripts_dir, execute_config
from conftest import parse_ns

build_scripts_dir()

import _build_execute_factory as factory  # noqa: E402
from _build_execute import CaptureStrategy  # noqa: E402

_MAVEN_NOTATION = 'plan-marshall:build-maven:maven'

#: The ``run`` namespace ``pyproject_build.py``'s OWN parser yields for the argv
#: these tests drive — the shared build CLI whose ``cmd_run`` is the subject here.
#: Being parser-derived it also carries ``--env`` and ``--working-dir``, which the
#: hand-built namespace it replaces omitted entirely. Hoisted to module scope
#: because ``parse_ns`` re-executes the script module on every call.
_RUN_ARGS: argparse.Namespace = parse_ns(
    'plan-marshall', 'build-pyproject', 'pyproject_build.py',
    'run', '--command-args', 'verify core', '--project-dir', '/tree', '--plan-id', 'plan-x',
    register=False,
)


def _config(**overrides: Any):
    """A minimal ExecuteConfig for driving cmd_run in these tests.

    Unannotated return: ``factory`` is loaded at runtime, so
    ``factory.ExecuteConfig`` is a value rather than a statically known type and
    an annotation naming it checks nothing.
    """
    return execute_config(factory, CaptureStrategy.TOOL_LOG_FLAG, **overrides)


def _run_args(**overrides: Any) -> argparse.Namespace:
    """The cmd_run argv namespace, defaulting to a plan-bound auto-mode build.

    Derived from the hoisted parser-derived base, which supplies every flag
    default; ``overrides`` names only the fields a given test differs in. The
    shallow copy keeps the shared base unmutated.
    """
    derived = copy.copy(_RUN_ARGS)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


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


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path, monkeypatch):
    """Point the machine-global home at tmp so the D5 fallback-streak state that
    ``_record_resolution`` now writes never touches the real ``~/.plan-marshall``
    tree (and never accumulates a streak across test runs)."""
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))


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
    assert 'mechanism=daemon_longpoll' in message
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
    assert 'mechanism=in_process_fallback' in message
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
    # The fail-loud refusal runs NO build (in-process or otherwise), so the
    # mechanism must name that honestly — never in_process_fallback, which would
    # log an in-process realisation that never happened.
    assert 'mechanism=no_build' in message
    assert 'mechanism=in_process_fallback' not in message
    assert message in capsys.readouterr().err


@pytest.mark.parametrize('child_execution_mode', ['auto', 'daemon'])
def test_daemon_child_reentrancy_records_no_second_resolution(
    monkeypatch, capsys, captured, child_execution_mode
):
    # Arrange: the daemon child re-runs the SAME executor command in-process,
    # with MARSHALLD_JOB set so _route_to_daemon short-circuits to in_daemon_job.
    monkeypatch.setenv('MARSHALLD_JOB', 'JOB-1')
    _install_in_process_stubs(monkeypatch)
    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)

    # Act
    rc = cmd_run(_run_args(execution_mode=child_execution_mode))

    # Assert: the routing parent owns the audit record — the child emits none,
    # to neither the captured work log nor the stderr parity sink.
    assert rc == 0
    assert captured == []
    assert '[BUILD-SERVER] resolved build' not in capsys.readouterr().err


def test_one_routed_request_produces_exactly_one_resolution_record(monkeypatch, capsys, captured):
    # Arrange: the routing parent sees a ready daemon and routes the build.
    monkeypatch.setattr(
        factory, '_load_build_server',
        lambda: _FakeClient(preflight={'status': 'success', 'preflight': 'ready'}),
    )
    monkeypatch.setattr(factory, 'cmd_run_common', lambda **kw: 0)
    _, parent_cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)

    # Act: the parent routes, then the daemon child re-runs the same request
    # in-process against the SAME plan_id.
    parent_rc = parent_cmd_run(_run_args(execution_mode='auto'))
    monkeypatch.setenv('MARSHALLD_JOB', 'JOB-1')
    _install_in_process_stubs(monkeypatch)
    _, child_cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)
    child_rc = child_cmd_run(_run_args(execution_mode='auto'))

    # Assert: ONE logical client request ⇒ exactly ONE resolution record for the
    # plan — the parent's resolved=routed line, with no contradicting
    # resolved=in_process line from the child.
    assert (parent_rc, child_rc) == (0, 0)
    assert len(captured) == 1
    assert 'requested=auto, resolved=routed' in captured[0][3]
    assert 'resolved=in_process' not in capsys.readouterr().err


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
