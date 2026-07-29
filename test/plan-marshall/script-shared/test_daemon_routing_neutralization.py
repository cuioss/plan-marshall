#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Proof that the in-process build path is chosen BY THE TEST, not by machine state.

The autouse ``_neutralize_daemon_routing`` fixture in ``test/conftest.py`` holds
the D5 routing seam at its non-routing outcome so no test's behaviour depends on
whether a marshalld daemon happens to be registered and ready on the host. A
fixture like that is easy to believe and hard to check: if it silently stopped
engaging, every test it protects would keep passing on a host with no daemon,
and the regression would surface only as ambient flakiness on a developer
machine where one IS running.

The two tests below are a MATCHED PAIR and are the standing check on that:

* **Positive arm** — the fixture is engaged (its default). The build-server
  client is stubbed so ``run_preflight`` reports ``ready``, i.e. the routable
  condition. The build must STILL run in-process (``execute_direct_base`` ran),
  which is only true if the fixture actually replaced the seam.
* **Negative control** — the identical simulated-ready client, but the test
  carries ``@pytest.mark.allow_daemon_routing`` so the fixture disengages. The
  build must now ROUTE (``execute_direct_base`` did NOT run, and the fake
  client's ``run_submit`` WAS called).

DELETING OR WEAKENING EITHER ARM SILENTLY VOIDS THE OTHER'S EVIDENTIARY VALUE.
The positive arm alone cannot distinguish "the fixture works" from "this host
has no reachable daemon, so nothing would have routed anyway" — the negative
control is what proves the simulated-ready setup is genuinely routable, so the
positive arm's in-process outcome is attributable to the fixture. Conversely the
negative control alone proves only that routing CAN happen, not that it is
suppressed by default. Neither claim survives on its own.

Neither arm depends on the absence of a daemon, and neither may be skipped:

* Routability is SIMULATED at the ``_load_build_server`` seam, so no real daemon
  process and no machine-global registry state is ever consulted.
* ``MARSHALLD_JOB_ENV`` is explicitly cleared in both arms. That guard is not
  incidental bookkeeping — when the suite itself is executed through the
  marshalld daemon, the daemon child sets that variable, ``_route_to_daemon``
  short-circuits to ``in_daemon_job`` for every test in the process, and routing
  is neutralized AMBIENTLY. The negative control would then pass without the
  marker doing anything, and this whole module would false-green. Clearing the
  variable makes both arms independent of how the suite was launched.
"""

from __future__ import annotations

import argparse

import _build_execute_factory as factory
import pytest
from _build_execute import CaptureStrategy


class _FakeReadyClient:
    """A build-server client that reports READY and accepts a routed job.

    Records every call so the negative control can assert that routing genuinely
    reached submit, rather than inferring it from the absence of an in-process
    build.
    """

    def __init__(self) -> None:
        self.preflight_calls = 0
        self.submit_calls = 0
        self.wait_calls = 0

    def run_preflight(self, _ns) -> dict:
        self.preflight_calls += 1
        return {'preflight': 'ready'}

    def run_submit(self, _ns) -> dict:
        self.submit_calls += 1
        return {'status': 'success', 'job_id': 'J-neutralization'}

    def run_wait(self, _ns) -> dict:
        self.wait_calls += 1
        # No log_file, so the client-side verdict cross-check reads None and
        # keeps the success verdict (the documented non-wrapper-command rule).
        return {'job_status': 'success', 'log_file': '', 'duration_seconds': 1}


class _ExecRecorder:
    """Records whether the IN-PROCESS build body ran, returning a success result."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, **kwargs) -> dict:
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
        return bool(self.calls)


def _make_config() -> factory.ExecuteConfig:
    """A minimal routable config — ``tool_name='python'`` resolves to a notation.

    A notation is required: ``_resolve_notation`` returning empty is itself a
    "do not route" path, which would make the negative control pass for the
    wrong reason.
    """
    return factory.ExecuteConfig(
        tool_name='python',
        unix_wrapper='pw',
        windows_wrapper='pw.bat',
        system_fallback='pwx',
        capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
        build_command_fn=factory.default_build_command_fn,
        scope_fn=lambda _a: 'default',
        command_key_fn=factory.default_command_key_fn,
        wrapper_resolve_fn=lambda _project_dir: 'pw',
    )


def _install_simulated_ready_daemon(monkeypatch) -> tuple:
    """Stage the routable condition shared by BOTH arms.

    Returns ``(cmd_run, client, exec_recorder)``. The only difference between the
    two arms is whether the autouse neutralization fixture is engaged — every
    other input here is identical by construction, which is what makes the pair a
    controlled comparison rather than two unrelated tests.
    """
    # The suite may itself be running inside a marshalld job, whose
    # MARSHALLD_JOB_ENV would neutralize routing ambiently and false-green the
    # negative control. Clear it so both arms are independent of the launcher.
    monkeypatch.delenv(factory.MARSHALLD_JOB_ENV, raising=False)

    client = _FakeReadyClient()
    monkeypatch.setattr(factory, '_load_build_server', lambda: client)

    exec_recorder = _ExecRecorder()
    monkeypatch.setattr(factory, 'execute_direct_base', exec_recorder)
    # Downstream of both branches and not under test here.
    monkeypatch.setattr(factory, 'cmd_run_common', lambda **_kwargs: 0)

    _execute_direct, cmd_run = factory.create_execute_handlers(
        _make_config(), lambda *_a, **_k: ([], None, 'SUCCESS')
    )
    return cmd_run, client, exec_recorder


def _auto_mode_args() -> argparse.Namespace:
    """A Namespace that leaves ``execution_mode`` at the ``auto`` default.

    ``auto`` is the whole point: it is the value that consults the routing seam,
    and therefore the only one under which the fixture's presence is observable.
    ``plan_id`` is ``None`` so the build-queue slot is a pure passthrough and the
    resolution audit never writes to a real plan log.
    """
    return argparse.Namespace(command_args='verify', plan_id=None, format='toon')


def test_neutralized_build_runs_in_process_despite_a_ready_daemon(monkeypatch):
    """POSITIVE ARM — the fixture is engaged, so a routable build stays in-process.

    Pairs with ``test_unneutralized_build_routes_to_a_ready_daemon`` below.
    """
    cmd_run, client, exec_recorder = _install_simulated_ready_daemon(monkeypatch)

    rc = cmd_run(_auto_mode_args())

    assert rc == 0
    assert exec_recorder.ran is True, (
        'the autouse _neutralize_daemon_routing fixture did not engage — an '
        'execution_mode=auto build reached a preflight-ready daemon instead of '
        'running in-process, so every test relying on that fixture is silently '
        'host-dependent'
    )
    assert client.submit_calls == 0, 'a neutralized build must never submit a job'


@pytest.mark.allow_daemon_routing
def test_unneutralized_build_routes_to_a_ready_daemon(monkeypatch):
    """NEGATIVE CONTROL — with the fixture disengaged, the same setup DOES route.

    This is what makes the positive arm above meaningful: it proves the simulated
    ready client is genuinely routable, so that arm's in-process outcome is
    attributable to the fixture rather than to an unroutable setup or an absent
    daemon. Pairs with
    ``test_neutralized_build_runs_in_process_despite_a_ready_daemon``.
    """
    cmd_run, client, exec_recorder = _install_simulated_ready_daemon(monkeypatch)

    rc = cmd_run(_auto_mode_args())

    assert rc == 0
    assert client.submit_calls == 1, (
        'the marker did not disengage the neutralization fixture — a routable '
        'execution_mode=auto build never reached submit, so the positive arm '
        'proves nothing'
    )
    assert exec_recorder.ran is False, 'a routed build must not also build in-process'
