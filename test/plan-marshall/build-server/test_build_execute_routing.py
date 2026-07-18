#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the D5 build-execute routing seam and the shared machine-global slot.

Two production surfaces are exercised:

* ``_build_execute_factory`` — the routing decision (``_route_to_daemon``), the
  notation resolution, the daemon-result mapping, and the ``cmd_run`` integration
  that either routes to marshalld (no fallback slot) or builds in-process under a
  single machine-global build-queue slot.
* ``_build_queue_slot`` / ``build_queue`` — the shared reader/writer of the ONE
  machine-global ``build-queue.json``: a routed build takes no slot (the
  no-stacking ``routed`` guard), an unregistered build acquires exactly one slot
  against that same file, and a plan-less build is an unchanged no-op passthrough.

The build-server CLIENT is stubbed (``_load_build_server`` returns a fake), so no
socket, daemon, or change-ledger is touched by the routing tests. The slot tests
drive the REAL ``build_queue`` against a ``PLAN_MARSHALL_HOME``-isolated file so
the single-shared-file and contention behaviour is asserted on real state.
"""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from conftest import get_script_path

# --- sys.path: the script-shared build library + its sibling deps ------------
_SHARED_SCRIPTS = get_script_path('plan-marshall', 'script-shared', 'marketplace_paths.py').parent
_BUILD_DIR = _SHARED_SCRIPTS / 'build'
_WORKFLOW_DIR = _SHARED_SCRIPTS / 'workflow'
_LOCKS_SCRIPTS = get_script_path('plan-marshall', 'manage-locks', 'build_queue.py').parent
_FILE_OPS_SCRIPTS = get_script_path('plan-marshall', 'tools-file-ops', 'file_ops.py').parent

for _dep in (_BUILD_DIR, _SHARED_SCRIPTS, _WORKFLOW_DIR, _LOCKS_SCRIPTS, _FILE_OPS_SCRIPTS):
    if str(_dep) not in sys.path:
        sys.path.insert(0, str(_dep))

import _build_execute_factory as factory  # noqa: E402
import _build_queue_slot as slot_mod  # noqa: E402
import build_queue as bq  # noqa: E402
from _build_execute import CaptureStrategy  # noqa: E402
from _build_server_protocol import MARSHALLD_JOB_ENV  # noqa: E402


# =============================================================================
# Fakes / fixtures
# =============================================================================


class _FakeClient:
    """A stand-in for the build_server client with scripted verb responses."""

    def __init__(self, preflight=None, submit=None, waits=None):
        self._preflight = preflight or {'status': 'success', 'preflight': 'disabled'}
        self._submit = submit or {'status': 'success', 'job_id': 'JOB-1'}
        self._waits = list(waits or [{'status': 'success', 'job_status': 'success'}])
        self.preflight_calls: list = []
        self.submit_calls: list = []
        self.wait_calls: list = []

    def run_preflight(self, args):
        self.preflight_calls.append(args)
        return self._preflight

    def run_submit(self, args):
        self.submit_calls.append(args)
        return self._submit

    def run_wait(self, args):
        self.wait_calls.append(args)
        # Pop scripted responses; repeat the last once exhausted.
        return self._waits.pop(0) if len(self._waits) > 1 else self._waits[0]


@pytest.fixture
def use_fake_client(monkeypatch):
    """Install a fake build_server client and return a factory for it."""

    def _install(**kwargs) -> _FakeClient:
        client = _FakeClient(**kwargs)
        monkeypatch.setattr(factory, '_load_build_server', lambda: client)
        return client

    return _install


@pytest.fixture(autouse=True)
def _clear_reentrancy(monkeypatch):
    """Ensure the re-entrancy marker is absent unless a test sets it."""
    monkeypatch.delenv(MARSHALLD_JOB_ENV, raising=False)


@pytest.fixture
def isolated_queue(tmp_path, monkeypatch) -> dict:
    """Isolate the machine-global build-queue file and its main-anchored side effects.

    The queue file resolves under an isolated ``PLAN_MARSHALL_HOME``; the
    ``project_root`` stamp, the [LOCK] event log, and the adaptive-limit run-config
    writes are pinned/stubbed so a real acquire touches ONLY the isolated queue
    file (never the developer's real ``~/.plan-marshall`` or main-anchored state).
    """
    home = tmp_path / 'home'
    home.mkdir()
    main_repo = tmp_path / 'main'
    (main_repo / '.plan' / 'local' / 'plans').mkdir(parents=True)
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(home))
    monkeypatch.setattr(bq, 'main_checkout_root', lambda: main_repo)
    monkeypatch.setattr(bq, 'log_lock_event', lambda *a, **k: None)
    monkeypatch.setattr(bq, '_read_build_queue_upper_limit', lambda: 600)
    monkeypatch.setattr(bq, '_write_build_queue_upper_limit', lambda *a, **k: None)
    return {'home': home, 'main_repo': main_repo, 'queue_path': home / 'build-queue.json'}


def _make_live_plan(main_repo: Path, plan_id: str) -> None:
    """Create a holder plan dir so its liveness check does not prune it."""
    (main_repo / '.plan' / 'local' / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)


def _config(**overrides: Any) -> factory.ExecuteConfig:
    """A minimal ExecuteConfig for driving cmd_run in tests."""
    base: dict[str, Any] = dict(
        tool_name='maven',
        unix_wrapper='mvnw',
        windows_wrapper='mvnw.cmd',
        system_fallback='mvn',
        capture_strategy=CaptureStrategy.TOOL_LOG_FLAG,
        build_command_fn=factory.default_build_command_fn,
        scope_fn=lambda a: 'default',
        command_key_fn=factory.default_command_key_fn,
    )
    base.update(overrides)
    return factory.ExecuteConfig(**base)


# =============================================================================
# Notation resolution
# =============================================================================


def test_resolve_notation_by_tool_name():
    assert factory._resolve_notation(_config(tool_name='maven')) == 'plan-marshall:build-maven:maven'
    assert factory._resolve_notation(_config(tool_name='gradle')) == 'plan-marshall:build-gradle:gradle'
    assert factory._resolve_notation(_config(tool_name='npm')) == 'plan-marshall:build-npm:npm'
    assert (
        factory._resolve_notation(_config(tool_name='python'))
        == 'plan-marshall:build-pyproject:pyproject_build'
    )


def test_resolve_notation_explicit_override_wins():
    cfg = _config(tool_name='maven', notation='my-bundle:my-skill:my_build')
    assert factory._resolve_notation(cfg) == 'my-bundle:my-skill:my_build'


def test_resolve_notation_unknown_tool_is_empty():
    assert factory._resolve_notation(_config(tool_name='rust')) == ''


# =============================================================================
# _route_to_daemon — the routing decision
# =============================================================================


def test_route_reentrancy_guard_skips_routing(monkeypatch):
    # A build already running inside a marshalld job never routes back.
    monkeypatch.setenv(MARSHALLD_JOB_ENV, '1')

    def _must_not_load():
        raise AssertionError('re-entrant build must not touch the client')

    monkeypatch.setattr(factory, '_load_build_server', _must_not_load)

    result, reason = factory._route_to_daemon(_config(), '/tree', 'plan-x')

    assert result is None
    assert reason == 'in_daemon_job'


def test_route_unroutable_tool_skips_without_client(monkeypatch):
    def _must_not_load():
        raise AssertionError('an unroutable tool must not touch the client')

    monkeypatch.setattr(factory, '_load_build_server', _must_not_load)

    result, reason = factory._route_to_daemon(_config(tool_name='rust'), '/tree', 'plan-x')

    assert result is None
    assert reason == 'no_notation'


def test_route_disabled_falls_back_without_submit(use_fake_client):
    client = use_fake_client(preflight={'status': 'success', 'preflight': 'disabled'})

    result, reason = factory._route_to_daemon(_config(), '/tree', 'plan-x')

    assert result is None
    assert reason == 'disabled'
    assert client.submit_calls == []  # unregistered → no submit


def test_route_down_falls_back_with_named_reason(use_fake_client):
    client = use_fake_client(
        preflight={'status': 'success', 'preflight': 'down', 'reason': 'socket_absent'}
    )

    result, reason = factory._route_to_daemon(_config(), '/tree', 'plan-x')

    assert result is None
    assert reason == 'socket_absent'
    assert client.submit_calls == []


def test_route_ready_submits_reconstructed_command(use_fake_client, monkeypatch, tmp_path):
    # Pin argv so the reconstructed executor-form command is deterministic.
    monkeypatch.setattr(sys, 'argv', ['maven.py', 'run', '--command-args', 'verify core'])
    client = use_fake_client(
        preflight={'status': 'success', 'preflight': 'ready'},
        submit={'status': 'success', 'job_id': 'JOB-9'},
        waits=[{'status': 'success', 'job_status': 'success', 'duration_seconds': 4, 'log_file': 'x.log'}],
    )
    tree = str(tmp_path)

    result, reason = factory._route_to_daemon(_config(tool_name='maven'), tree, 'plan-x')

    assert reason == ''
    assert result is not None
    assert result['status'] == 'success'
    # The submit carried the positional executor-form command the daemon verifies.
    submitted = json.loads(client.submit_calls[0].command)
    assert submitted[0] == 'python3'
    assert submitted[1] == str(Path(tree).resolve() / '.plan' / 'execute-script.py')
    assert submitted[2] == 'plan-marshall:build-maven:maven'
    assert submitted[3:] == ['run', '--command-args', 'verify core']
    # exec_path / project_path are the resolved tree; plan_id is forwarded.
    assert client.submit_calls[0].exec_path == str(Path(tree).resolve())
    assert client.submit_calls[0].plan_id == 'plan-x'


def test_route_wait_reissues_on_running(use_fake_client):
    client = use_fake_client(
        preflight={'status': 'success', 'preflight': 'ready'},
        submit={'status': 'success', 'job_id': 'JOB-2'},
        waits=[
            {'status': 'success', 'job_status': 'running'},
            {'status': 'success', 'job_status': 'success', 'duration_seconds': 1, 'log_file': 'l'},
        ],
    )

    result, reason = factory._route_to_daemon(_config(), '/tree', 'plan-x')

    assert reason == ''
    assert result is not None
    assert len(client.wait_calls) == 2  # re-issued once on the running return


def test_route_refused_falls_back(use_fake_client):
    client = use_fake_client(
        preflight={'status': 'success', 'preflight': 'ready'},
        submit={'status': 'refused', 'reason': 'not_registered'},
    )

    result, reason = factory._route_to_daemon(_config(), '/tree', 'plan-x')

    assert result is None
    assert reason == 'not_registered'
    assert client.wait_calls == []  # never waited on a refused submit


def test_route_wait_degraded_falls_back(use_fake_client):
    client = use_fake_client(
        preflight={'status': 'success', 'preflight': 'ready'},
        submit={'status': 'success', 'job_id': 'JOB-3'},
        waits=[{'status': 'degraded', 'reason': 'unreachable'}],
    )

    result, reason = factory._route_to_daemon(_config(), '/tree', 'plan-x')

    assert result is None
    assert reason == 'unreachable'


# =============================================================================
# _daemon_result_to_direct — status mapping
# =============================================================================


def test_daemon_result_success_maps_to_success():
    result = factory._daemon_result_to_direct(
        {'job_status': 'success', 'duration_seconds': 7, 'log_file': 'a.log'}, 'cmd'
    )
    assert result['status'] == 'success'
    assert result['exit_code'] == 0
    assert result['log_file'] == 'a.log'
    assert result['command'] == 'cmd'


def test_daemon_result_failure_maps_to_error():
    result = factory._daemon_result_to_direct(
        {'job_status': 'failure', 'exit_code': 2, 'duration_seconds': 3, 'log_file': 'b.log'}, 'cmd'
    )
    assert result['status'] == 'error'
    assert result['exit_code'] == 2


def test_daemon_result_timeout_maps_to_timeout():
    result = factory._daemon_result_to_direct(
        {'job_status': 'timeout', 'duration_seconds': 9, 'log_file': 'c.log'}, 'cmd'
    )
    assert result['status'] == 'timeout'


def test_daemon_result_killed_carries_no_blind_retry_message():
    result = factory._daemon_result_to_direct(
        {'job_status': 'killed', 'exit_code': -9, 'duration_seconds': 1, 'log_file': 'd.log'}, 'cmd'
    )
    assert result['status'] == 'error'
    assert result['error'] == 'killed'
    assert 'do not blind-retry' in result['message']


# =============================================================================
# build_queue_slot — the no-stacking / passthrough guards
# =============================================================================


def test_slot_routed_is_noop_passthrough(monkeypatch):
    # A routed build must NOT acquire a fallback slot (no stacking).
    def _must_not_load():
        raise AssertionError('a routed build must not touch the queue')

    monkeypatch.setattr(slot_mod, '_load_build_queue', _must_not_load)

    with slot_mod.build_queue_slot('plan-x', routed=True):
        pass  # no exception ⇒ no queue interaction


def test_slot_planless_is_noop_passthrough(monkeypatch):
    def _must_not_load():
        raise AssertionError('a plan-less build must not touch the queue')

    monkeypatch.setattr(slot_mod, '_load_build_queue', _must_not_load)

    with slot_mod.build_queue_slot(None):
        pass


# =============================================================================
# Shared machine-global file — one slot, one file, contention
# =============================================================================


def test_fallback_acquires_exactly_one_slot_on_shared_file(isolated_queue, monkeypatch):
    # The in-process fallback (build_queue_slot) resolves the ONE machine-global
    # file and a single build holds exactly one active slot while running. Route
    # the slot wrapper's build_queue at the isolated instance.
    monkeypatch.setattr(slot_mod, '_load_build_queue', lambda: bq)
    queue_path = bq._resolve_queue_path()
    assert queue_path == isolated_queue['queue_path']

    with slot_mod.build_queue_slot('plan-a'):
        state = json.loads(queue_path.read_text())
        assert len(state['active']) == 1
        assert state['active'][0]['plan_id'] == 'plan-a'

    # Released in the finally: no active slot remains.
    state = json.loads(queue_path.read_text())
    assert state['active'] == []


def test_registered_and_unregistered_contend_on_one_file(isolated_queue, monkeypatch):
    # Both the daemon-served (registered) path and the in-process fallback acquire
    # against the SAME machine-global file via the rmw_json serialization, sharing
    # ONE slot budget: with a 1-slot budget the second acquire blocks.
    monkeypatch.setattr(bq, '_resolve_max_slots', lambda: 1)
    _make_live_plan(isolated_queue['main_repo'], 'registered-build')
    _make_live_plan(isolated_queue['main_repo'], 'unregistered-build')

    first = bq.run_acquire(Namespace(plan_id='registered-build'))
    second = bq.run_acquire(Namespace(plan_id='unregistered-build'))

    assert first['admission'] == 'admitted'
    assert second['admission'] == 'blocked'  # one budget, shared across both paths
    assert first['queue_path'] == second['queue_path'] == str(isolated_queue['queue_path'])


# =============================================================================
# cmd_run integration — route vs fallback wiring
# =============================================================================


def _run_args(**overrides) -> Namespace:
    base = dict(command_args='verify core', project_dir='/tree', plan_id='plan-x',
                format='toon', mode='actionable', timeout=None)
    base.update(overrides)
    return Namespace(**base)


def test_cmd_run_routes_and_takes_no_fallback_slot(monkeypatch):
    canned = {'status': 'success', 'exit_code': 0, 'duration_seconds': 1, 'log_file': 'l', 'command': 'c'}
    monkeypatch.setattr(factory, '_route_to_daemon', lambda *a, **k: (canned, ''))

    entered = {'slot': False}

    @contextmanager
    def _recording_slot(plan_id, *, routed=False):
        entered['slot'] = True
        yield

    monkeypatch.setattr(factory, 'build_queue_slot', _recording_slot)

    seen = {}
    monkeypatch.setattr(factory, 'cmd_run_common', lambda **kw: (seen.update(kw), 0)[1])

    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)
    rc = cmd_run(_run_args())

    assert rc == 0
    assert entered['slot'] is False  # routed ⇒ no fallback slot acquired
    assert seen['result'] is canned  # the daemon result flows through rendering


def test_cmd_run_falls_back_under_a_slot_when_not_routed(monkeypatch):
    monkeypatch.setattr(factory, '_route_to_daemon', lambda *a, **k: (None, 'disabled'))
    monkeypatch.setattr(
        factory, 'execute_direct_base',
        lambda **kw: {'status': 'success', 'exit_code': 0, 'duration_seconds': 1,
                      'log_file': 'l', 'command': 'c'},
    )

    entered = {'slot': False, 'plan_id': None}

    @contextmanager
    def _recording_slot(plan_id, *, routed=False):
        entered['slot'] = True
        entered['plan_id'] = plan_id
        yield

    monkeypatch.setattr(factory, 'build_queue_slot', _recording_slot)
    monkeypatch.setattr(factory, 'cmd_run_common', lambda **kw: 0)

    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)
    rc = cmd_run(_run_args())

    assert rc == 0
    assert entered['slot'] is True  # not routed ⇒ in-process under a fallback slot
    assert entered['plan_id'] == 'plan-x'
