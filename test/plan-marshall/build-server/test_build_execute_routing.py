#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the build-execute routing seam and the shared machine-global slot.

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

This module is one arm of a matched mirror pair with
``test_acceptance_resolution_log.py``: this arm pins the routing decision and
its wiring with the build-server client stubbed, never live, while the mirror
pins the resolution record reaching a durable sink. The two are a matched pair
and deleting or weakening either one voids the other's evidentiary value.
"""

from __future__ import annotations

import argparse
import copy
import importlib
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import _build_execute_factory as factory
import _build_queue_slot as slot_mod
import pytest
from _build_execute import CaptureStrategy
from _build_extension_fixtures import execute_config
from _build_server_protocol import MARSHALLD_JOB_ENV

from conftest import load_script_module, parse_ns

bq = load_script_module('plan-marshall', 'manage-locks', 'build_queue.py')


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from a hoisted parser-derived base.

    The base supplies every parser default; ``overrides`` names only the fields
    this call differs in. A shallow copy is enough because the values are the
    parser's own scalars, and the base must stay unmutated for the other callers
    sharing it.
    """
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


#: The ``run`` namespace ``pyproject_build.py``'s OWN parser yields — the shared
#: build CLI whose ``cmd_run`` the routing tests below drive. Parser-derived, so it
#: carries ``--env`` and ``--working-dir`` alongside the flags this module names;
#: the hand-built namespace it replaces had neither, which is exactly the gap that
#: lets a newly-added build flag break production while the tests stay green.
#: Hoisted because ``parse_ns`` re-executes the script module on every call.
_RUN_ARGS = parse_ns(
    'plan-marshall',
    'build-pyproject',
    'pyproject_build.py',
    'run',
    '--command-args',
    'verify core',
    '--plan-id',
    'plan-x',
    register=False,
)
#: ``--plan-id`` and ``--project-dir`` are mutually exclusive on the shared build
#: CLI, so no argv carrying both ever reaches ``cmd_run``: ``build_main`` refuses
#: the pair outright and otherwise DERIVES ``project_dir`` from the plan before
#: dispatching. The assignment below models that derivation, so the base stays a
#: namespace production can actually deliver — which is what makes the
#: production-fidelity claim above true rather than merely asserted.
_RUN_ARGS.project_dir = '/tree'

#: The ``acquire`` namespace ``build_queue.py``'s OWN parser yields.
#: ``register=False`` so it never displaces the ``build_queue`` imported above.
_ACQUIRE_ARGS = parse_ns(
    'plan-marshall',
    'manage-locks',
    'build_queue.py',
    'acquire',
    '--plan-id',
    'plan-x',
    register=False,
)


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

    The queue file resolves under an isolated ``PLAN_MARSHALL_HOME``, and only two
    things are still pinned or stubbed: the ``project_root`` stamp (so holder
    liveness resolves under the fixture's own checkout) and the [LOCK] event log
    (so no emission reaches the developer's main-anchored log). A real acquire
    therefore touches ONLY the isolated queue file.

    The adaptive reap threshold needs no stub at all any more: it is a top-level
    ``upper_limit_seconds`` field of the isolated queue file itself, so seeding it
    at the floor below pins the reaper's threshold in the shape ``build_queue``
    actually reads. The two run-config helpers this fixture used to monkeypatch
    onto ``bq`` no longer exist on the module, and ``monkeypatch.setattr``
    defaults to ``raising=True`` — so leaving them would have errored every slot
    test using this fixture rather than merely over-stubbing.
    """
    home = tmp_path / 'home'
    home.mkdir()
    main_repo = tmp_path / 'main'
    (main_repo / '.plan' / 'local' / 'plans').mkdir(parents=True)
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(home))
    monkeypatch.setattr(bq, 'main_checkout_root', lambda: main_repo)
    monkeypatch.setattr(bq, 'log_lock_event', lambda *a, **k: None)
    queue_path = home / 'build-queue.json'
    # Seed the threshold in the queue's OWN state, at the floor, so the reaper's
    # threshold is pinned without stubbing anything on the module under test.
    queue_path.write_text(
        json.dumps(
            {
                'active': [],
                'waiting': [],
                'run_log': [],
                bq.UPPER_LIMIT_FIELD: bq.UPPER_LIMIT_FLOOR_SECONDS,
            }
        ),
        encoding='utf-8',
    )
    return {'home': home, 'main_repo': main_repo, 'queue_path': queue_path}


def _make_live_plan(main_repo: Path, plan_id: str) -> None:
    """Create a holder plan dir so its liveness check does not prune it."""
    (main_repo / '.plan' / 'local' / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)


def _config(**overrides: Any):
    """A minimal ExecuteConfig for driving cmd_run in tests.

    Unannotated return: ``factory`` is loaded at runtime, so
    ``factory.ExecuteConfig`` is a value rather than a statically known type and
    an annotation naming it checks nothing.
    """
    return execute_config(factory, CaptureStrategy.TOOL_LOG_FLAG, **overrides)


# =============================================================================
# Notation resolution
# =============================================================================


def test_resolve_notation_by_tool_name():
    assert factory._resolve_notation(_config(tool_name='maven')) == 'plan-marshall:build-maven:maven'
    assert factory._resolve_notation(_config(tool_name='gradle')) == 'plan-marshall:build-gradle:gradle'
    assert factory._resolve_notation(_config(tool_name='npm')) == 'plan-marshall:build-npm:npm'
    assert factory._resolve_notation(_config(tool_name='python')) == 'plan-marshall:build-pyproject:pyproject_build'


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
    client = use_fake_client(preflight={'status': 'success', 'preflight': 'down', 'reason': 'socket_absent'})

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


def test_route_submits_the_absolute_project_dir_for_the_separated_form(use_fake_client, monkeypatch, tmp_path):
    """The daemon re-runs the argv in the worktree, so the relative value must not survive.

    The lane hands every build ``--project-dir .plan/local/worktrees/{plan_id}``.
    Submitted verbatim, the child re-resolves it against the worktree the daemon
    made its working directory, names a directory that does not exist, and the
    wrapper lookup falls through to a bare system command that is not installed.
    Only the VALUE may change: every other token is what the caller wrote.
    """
    worktree = tmp_path / '.plan' / 'local' / 'worktrees' / 'plan-x'
    worktree.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'pyproject_build.py',
            'run',
            '--command-args',
            'verify core',
            '--project-dir',
            '.plan/local/worktrees/plan-x',
        ],
    )
    client = use_fake_client(
        preflight={'status': 'success', 'preflight': 'ready'},
        submit={'status': 'success', 'job_id': 'JOB-1'},
        waits=[{'status': 'success', 'job_status': 'success', 'duration_seconds': 1, 'log_file': 'x.log'}],
    )

    result, reason = factory._route_to_daemon(_config(tool_name='python'), '.plan/local/worktrees/plan-x', None)

    assert reason == ''
    assert result is not None
    submitted = json.loads(client.submit_calls[0].command)
    assert submitted[3:] == [
        'run',
        '--command-args',
        'verify core',
        '--project-dir',
        str(worktree.resolve()),
    ], 'the submitted argv must carry the absolute tree and leave every other token alone'


def test_route_submits_the_absolute_project_dir_for_the_equals_form(use_fake_client, monkeypatch, tmp_path):
    """``--project-dir=X`` is the same flag: its value is rewritten, the token kept."""
    worktree = tmp_path / '.plan' / 'local' / 'worktrees' / 'plan-x'
    worktree.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'pyproject_build.py',
            'run',
            '--command-args',
            'verify core',
            '--project-dir=.plan/local/worktrees/plan-x',
        ],
    )
    client = use_fake_client(
        preflight={'status': 'success', 'preflight': 'ready'},
        submit={'status': 'success', 'job_id': 'JOB-1'},
        waits=[{'status': 'success', 'job_status': 'success', 'duration_seconds': 1, 'log_file': 'x.log'}],
    )

    factory._route_to_daemon(_config(tool_name='python'), '.plan/local/worktrees/plan-x', None)

    submitted = json.loads(client.submit_calls[0].command)
    assert submitted[3:] == [
        'run',
        '--command-args',
        'verify core',
        f'--project-dir={worktree.resolve()}',
    ]


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


def test_route_wait_treats_queued_as_non_terminal(use_fake_client):
    """A ``queued`` wait payload keeps the loop waiting — it is not a verdict.

    At HEAD the routed client recognised only ``running`` as non-terminal, so a
    ``queued`` job_status fell through to ``_daemon_result_to_direct`` and landed
    on its "terminal job_status this client does not recognise" leg: an
    ``indeterminate`` result for a build that had not even started. The two
    scripted waits are the whole claim: the first is ``queued`` (must NOT stop
    the loop) and the second is terminal (must be the result).
    """
    client = use_fake_client(
        preflight={'status': 'success', 'preflight': 'ready'},
        submit={'status': 'success', 'job_id': 'JOB-Q'},
        waits=[
            {'status': 'success', 'job_status': 'queued', 'waiting_on': 'JOB-A', 'queued_seconds': 3},
            {'status': 'success', 'job_status': 'success', 'duration_seconds': 1, 'log_file': 'l', 'queued_seconds': 9},
        ],
    )

    result, reason = factory._route_to_daemon(_config(), '/tree', 'plan-x')

    assert reason == ''
    assert result is not None
    assert len(client.wait_calls) == 2, 'a queued return must be followed by another wait'
    assert result['status'] == 'success'
    assert result.get('error') != 'indeterminate'
    # The wait the build paid travels on the terminal result.
    assert result['queued_seconds'] == 9


def test_route_hand_back_carries_queued_seconds_when_the_bound_expires(use_fake_client, monkeypatch):
    """A job still ``queued`` at the bound returns a hand-back, never
    ``indeterminate`` — and the hand-back says how long it has waited.

    The bound is shortened so the test exercises the real expiry path (one wait,
    then the hand-back) instead of sleeping the production 300 s.
    """
    monkeypatch.setattr(factory, '_DAEMON_WAIT_BOUND_SECONDS', 0.05)
    client = use_fake_client(
        preflight={'status': 'success', 'preflight': 'ready'},
        submit={'status': 'success', 'job_id': 'JOB-S'},
        waits=[{'status': 'success', 'job_status': 'queued', 'waiting_on': 'JOB-B', 'queued_seconds': 12}],
    )

    result, reason = factory._route_to_daemon(_config(), '/tree', 'plan-x')

    assert reason == ''
    assert result is not None
    assert client.wait_calls, 'the loop really waited before the bound expired'
    assert result['status'] == 'running', 'a still-queued job is a live hand-back, not a verdict'
    assert result['job_id'] == 'JOB-S'
    assert result['job_status'] == 'queued', 'the hand-back reports what the daemon last said, not "running"'
    assert result['queued_seconds'] == 12


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
    use_fake_client(
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


def test_daemon_result_killed_maps_to_killed_not_error():
    """A daemon-classified kill keeps its OWN status through the client mapping.

    Mapping it to ``error`` — as this leg historically did, marking the kill
    only in a secondary ``error`` field — lost the distinction at the renderer:
    ``cmd_run_common`` rebuilds its payload from ``status`` alone, so the
    daemon's correctly-classified kill reached every consuming gate as a build
    failure, complete with a synthesised ``errors[]`` row.
    """
    result = factory._daemon_result_to_direct(
        {'job_status': 'killed', 'exit_code': -9, 'duration_seconds': 1, 'log_file': 'd.log'}, 'cmd'
    )
    assert result['status'] == 'killed'
    assert result['status'] != 'error'
    assert result['error'] == 'killed'
    assert result['exit_code'] == -9
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


def test_registered_and_unregistered_contend_on_one_file(isolated_queue):
    # Both the daemon-served (registered) path and the in-process fallback acquire
    # against the SAME machine-global file via the rmw_json serialization, sharing
    # ONE slot budget: with a 1-slot budget the second acquire blocks.
    #
    # The cap is machine-global, so it is STAGED as the real
    # machine-config.json under the isolated PLAN_MARSHALL_HOME rather than
    # stubbed at the resolution seam. That keeps the shared-budget claim resting
    # on the same resolver production uses — a stub would assert the budget is
    # shared while bypassing the code that makes it shared.
    config_dir = isolated_queue['home'] / 'marshalld'
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / 'machine-config.json').write_text(
        json.dumps({'version': 1, 'build': {'queue': {'max_slots': 1}}}), encoding='utf-8'
    )
    _make_live_plan(isolated_queue['main_repo'], 'registered-build')
    _make_live_plan(isolated_queue['main_repo'], 'unregistered-build')

    first = bq.run_acquire(_variant(_ACQUIRE_ARGS, plan_id='registered-build'))
    second = bq.run_acquire(_variant(_ACQUIRE_ARGS, plan_id='unregistered-build'))

    assert first['admission'] == 'admitted'
    assert second['admission'] == 'blocked'  # one budget, shared across both paths
    assert first['queue_path'] == second['queue_path'] == str(isolated_queue['queue_path'])
    # Both paths resolved the cap from the machine-global file, not per-caller.
    assert first['max_slots'] == second['max_slots'] == 1
    assert first['max_slots_source'] == second['max_slots_source'] == 'machine_config'


# =============================================================================
# cmd_run integration — route vs fallback wiring
# =============================================================================


def _run_args(**overrides) -> argparse.Namespace:
    """The hoisted ``run`` namespace, with per-test overrides.

    The base is parser-derived and then carries the ``project_dir`` that
    ``build_main`` resolves from ``--plan-id``, so it models an argv the CLI
    can actually deliver to ``cmd_run``.
    """
    return _variant(_RUN_ARGS, **overrides)


def _recording_slot_stub(entered: dict):
    """A ``build_queue_slot`` stub that only records whether it was entered.

    Shared by the "routed, no fallback slot" assertions below — those tests
    care solely about whether the slot context manager was entered, not the
    ``plan_id`` it was called with (contrast ``_install_in_process_stubs``,
    whose in-process variant also records ``plan_id``).
    """

    @contextmanager
    def _recording_slot(plan_id, *, routed=False):
        entered['slot'] = True
        yield

    return _recording_slot


def test_cmd_run_routes_and_takes_no_fallback_slot(monkeypatch):
    canned = {'status': 'success', 'exit_code': 0, 'duration_seconds': 1, 'log_file': 'l', 'command': 'c'}
    monkeypatch.setattr(factory, '_route_to_daemon', lambda *a, **k: (canned, ''))

    entered = {'slot': False}
    monkeypatch.setattr(factory, 'build_queue_slot', _recording_slot_stub(entered))

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
        factory,
        'execute_direct_base',
        lambda **kw: {'status': 'success', 'exit_code': 0, 'duration_seconds': 1, 'log_file': 'l', 'command': 'c'},
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


def test_cmd_run_takes_the_directory_lock_before_the_slot(monkeypatch):
    """The lock order is directory first, then slot — one order, everywhere.

    Within a build process that order is what keeps the two limiters from
    interleaving: a build holding a slot never waits on a directory, because it had
    to take the directory first. (The daemon/child pair leaves one bounded window —
    the daemon spends a slot at admission and the child takes the directory a moment
    later — which is bounded by whichever budget expires first, not removed by this
    order.)
    """
    order: list[str] = []
    monkeypatch.setattr(factory, '_route_to_daemon', lambda *a, **k: (None, 'disabled'))
    monkeypatch.setattr(
        factory,
        'execute_direct_base',
        lambda **kw: {'status': 'success', 'exit_code': 0, 'duration_seconds': 1, 'log_file': 'l', 'command': 'c'},
    )

    @contextmanager
    def _directory_lock(directory, **_kwargs):
        order.append('directory')
        yield SimpleNamespace(waited_seconds=0.0)

    @contextmanager
    def _slot(plan_id, *, routed=False):
        order.append('slot')
        yield

    monkeypatch.setattr(factory, 'directory_lock', _directory_lock)
    monkeypatch.setattr(factory, 'build_queue_slot', _slot)
    monkeypatch.setattr(factory, 'cmd_run_common', lambda **kw: 0)

    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)
    rc = cmd_run(_run_args())

    assert rc == 0
    assert order == ['directory', 'slot']


def test_cmd_run_reports_directory_busy_and_never_spawns_the_build(monkeypatch, capsys):
    """A directory that stays busy yields the named ``directory_busy`` error.

    The build never runs: the refusal happens before ``execute_direct`` is
    reached, which is the difference between waiting/refusing and running
    concurrently.
    """
    spawned: list[bool] = []
    monkeypatch.setattr(factory, '_route_to_daemon', lambda *a, **k: (None, 'disabled'))

    @contextmanager
    def _busy(directory, **_kwargs):
        raise factory.DirectoryBusy(
            directory=directory,
            holder={'plan_id': 'other-plan', 'command': 'module-tests', 'pid': 4242, 'acquired_at': 0.0},
            waited_seconds=600.0,
        )
        yield  # pragma: no cover

    monkeypatch.setattr(factory, 'directory_lock', _busy)
    monkeypatch.setattr(factory, 'execute_direct_base', lambda **kw: spawned.append(True))

    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)
    rc = cmd_run(_run_args())

    assert rc == 1
    assert spawned == [], 'the build must not run while its directory is held'
    out = capsys.readouterr().out
    assert factory.ERROR_DIRECTORY_BUSY in out
    assert 'other-plan' in out
    assert '4242' in out


def test_cmd_run_emits_queued_seconds_on_the_rendered_result(monkeypatch, capsys):
    """The wait must survive the EMIT boundary, not only the intermediate result.

    ``cmd_run_common`` rebuilds the payload per branch, so a field carried only on
    the routing seam's dict is dropped before the operator ever sees it. This
    asserts the rendered TOON, which is what the agent-facing contract means by
    "the result carries queued_seconds".
    """
    canned = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 1,
        'log_file': 'l',
        'command': 'c',
        'queued_seconds': 7,
    }
    monkeypatch.setattr(factory, '_route_to_daemon', lambda *a, **k: (canned, ''))

    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)
    rc = cmd_run(_run_args())

    assert rc == 0
    assert 'queued_seconds: 7' in capsys.readouterr().out


def test_cmd_run_reports_the_directory_wait_it_paid(monkeypatch, capsys):
    """An in-process build serialised behind another reports its wait.

    The lease is the only place that number exists on this path, so a wrapper that
    discards it would leave the second build looking merely slow.
    """
    monkeypatch.setattr(factory, '_route_to_daemon', lambda *a, **k: (None, 'disabled'))
    monkeypatch.setattr(
        factory,
        'execute_direct_base',
        lambda **kw: {'status': 'success', 'exit_code': 0, 'duration_seconds': 1, 'log_file': 'l', 'command': 'c'},
    )

    @contextmanager
    def _lease(directory, **_kwargs):
        yield SimpleNamespace(waited_seconds=12.4)

    @contextmanager
    def _slot(plan_id, *, routed=False):
        yield

    monkeypatch.setattr(factory, 'directory_lock', _lease)
    monkeypatch.setattr(factory, 'build_queue_slot', _slot)

    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)
    rc = cmd_run(_run_args())

    assert rc == 0
    assert 'queued_seconds: 12' in capsys.readouterr().out


def test_cmd_run_omits_queued_seconds_when_there_was_no_wait(monkeypatch, capsys):
    """A sub-second acquisition is not a wait, and says nothing.

    The lease is a float, so ``> 0`` would be true for the microseconds a free
    directory takes — and ``int()`` would then print ``queued_seconds: 0`` on every
    in-process build, erasing the very distinction the field exists to make.
    """
    monkeypatch.setattr(factory, '_route_to_daemon', lambda *a, **k: (None, 'disabled'))
    monkeypatch.setattr(
        factory,
        'execute_direct_base',
        lambda **kw: {'status': 'success', 'exit_code': 0, 'duration_seconds': 1, 'log_file': 'l', 'command': 'c'},
    )

    @contextmanager
    def _lease(directory, **_kwargs):
        yield SimpleNamespace(waited_seconds=0.4)

    @contextmanager
    def _slot(plan_id, *, routed=False):
        yield

    monkeypatch.setattr(factory, 'directory_lock', _lease)
    monkeypatch.setattr(factory, 'build_queue_slot', _slot)

    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)
    assert cmd_run(_run_args()) == 0

    assert 'queued_seconds' not in capsys.readouterr().out


def test_routed_build_for_a_plan_submits_and_records_that_plan(use_fake_client, monkeypatch, tmp_path):
    """A build routed for a plan names that plan to the daemon and in its ``kind=build`` row.

    The ledger module is taken from ``sys.modules`` at run time because the
    routing seam imports it lazily, by name, at the moment it appends.
    """
    ledger = importlib.import_module('_ledger_core')
    ledger_path = tmp_path / 'change-ledger.jsonl'
    monkeypatch.setattr(ledger, 'resolve_ledger_path', lambda: ledger_path)
    monkeypatch.setattr(
        sys, 'argv', ['pyproject_build.py', 'run', '--plan-id', 'plan-x', '--command-args', 'verify core']
    )
    monkeypatch.setattr(factory, 'cmd_run_common', lambda **kw: 0)
    client = use_fake_client(
        preflight={'status': 'success', 'preflight': 'ready'},
        submit={'status': 'success', 'job_id': 'JOB-5'},
        waits=[{'status': 'success', 'job_status': 'success', 'duration_seconds': 3, 'log_file': 'x.log'}],
    )
    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)

    rc = cmd_run(_run_args(project_dir=str(tmp_path)))

    build_rows = [row for row in ledger.read_entries(ledger_path) if row['kind'] == 'build']
    assert rc == 0
    assert client.submit_calls[0].plan_id == 'plan-x'
    assert [row['plan_id'] for row in build_rows] == ['plan-x']
    assert build_rows[0]['outcome']['route'] == 'routed'


# =============================================================================
# cmd_run integration — explicit execution_mode branches
# =============================================================================


def _install_in_process_stubs(monkeypatch, entered):
    """Stub execute_direct_base + build_queue_slot + cmd_run_common for the in-process path."""
    monkeypatch.setattr(
        factory,
        'execute_direct_base',
        lambda **kw: {'status': 'success', 'exit_code': 0, 'duration_seconds': 1, 'log_file': 'l', 'command': 'c'},
    )

    @contextmanager
    def _recording_slot(plan_id, *, routed=False):
        entered['slot'] = True
        entered['plan_id'] = plan_id
        yield

    monkeypatch.setattr(factory, 'build_queue_slot', _recording_slot)
    monkeypatch.setattr(factory, 'cmd_run_common', lambda **kw: 0)


def test_cmd_run_in_process_never_touches_the_client(monkeypatch):
    # execution_mode=in_process never attempts to route — _route_to_daemon is
    # never called, so the run is deterministic regardless of live daemon state.
    def _must_not_route(*a, **k):
        raise AssertionError('in_process mode must never attempt to route')

    monkeypatch.setattr(factory, '_route_to_daemon', _must_not_route)

    entered: dict = {'slot': False, 'plan_id': None}
    _install_in_process_stubs(monkeypatch, entered)

    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)
    rc = cmd_run(_run_args(execution_mode='in_process'))

    assert rc == 0
    assert entered['slot'] is True  # ran in-process under a fallback slot
    assert entered['plan_id'] == 'plan-x'


def test_cmd_run_daemon_fail_loud_on_unavailable(monkeypatch, capsys):
    # execution_mode=daemon requires the daemon: a genuine unavailability is a
    # hard fail-loud (ERROR_DAEMON_REQUIRED, exit 1), never an in-process fallback.
    monkeypatch.setattr(factory, '_route_to_daemon', lambda *a, **k: (None, 'disabled'))

    def _must_not_slot(*a, **k):
        raise AssertionError('daemon fail-loud must not acquire a fallback slot')

    monkeypatch.setattr(factory, 'build_queue_slot', _must_not_slot)

    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)
    rc = cmd_run(_run_args(execution_mode='daemon'))

    assert rc == 1
    out = capsys.readouterr().out
    assert factory.ERROR_DAEMON_REQUIRED == 'daemon_required'
    assert 'error: daemon_required' in out
    assert 'reason: disabled' in out


def test_cmd_run_daemon_fail_loud_on_env_or_working_dir(monkeypatch, capsys):
    # A build carrying an env override the daemon cannot honour fails loud in
    # daemon mode — WITHOUT ever attempting to route.
    def _must_not_route(*a, **k):
        raise AssertionError('daemon-incompatible build must not attempt to route')

    monkeypatch.setattr(factory, '_route_to_daemon', _must_not_route)

    _, cmd_run = factory.create_execute_handlers(_config(supports_env_vars=True), parse_log_fn=lambda *a: None)
    rc = cmd_run(_run_args(execution_mode='daemon', env='KEY=VALUE'))

    assert rc == 1
    out = capsys.readouterr().out
    assert 'error: daemon_required' in out
    assert 'reason: env_or_working_dir_set' in out


def test_cmd_run_daemon_proceeds_in_process_under_in_daemon_job(monkeypatch):
    # The sole in-process exception in daemon mode: this process IS the daemon
    # child (in_daemon_job) and MUST proceed in-process, not fail loud.
    monkeypatch.setattr(factory, '_route_to_daemon', lambda *a, **k: (None, 'in_daemon_job'))

    entered: dict = {'slot': False, 'plan_id': None}
    _install_in_process_stubs(monkeypatch, entered)

    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)
    rc = cmd_run(_run_args(execution_mode='daemon'))

    assert rc == 0
    assert entered['slot'] is True  # daemon child ran in-process under a slot


def test_cmd_run_daemon_routes_successfully(monkeypatch):
    # execution_mode=daemon routes exactly like auto when the daemon is ready.
    canned = {'status': 'success', 'exit_code': 0, 'duration_seconds': 1, 'log_file': 'l', 'command': 'c'}
    monkeypatch.setattr(factory, '_route_to_daemon', lambda *a, **k: (canned, ''))

    entered = {'slot': False}
    monkeypatch.setattr(factory, 'build_queue_slot', _recording_slot_stub(entered))

    seen: dict = {}
    monkeypatch.setattr(factory, 'cmd_run_common', lambda **kw: (seen.update(kw), 0)[1])

    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)
    rc = cmd_run(_run_args(execution_mode='daemon'))

    assert rc == 0
    assert entered['slot'] is False  # routed ⇒ no fallback slot
    assert seen['result'] is canned


def test_cmd_run_records_requested_and_resolved_mode(monkeypatch, capsys):
    # Every resolved outcome records BOTH the requested and the resolved mode
    # (the F2/F6 requested-vs-resolved audit requirement). The line is asserted
    # on the stderr sink, NOT on a logging handler: this build subprocess wires
    # no handler, so a logger-only emit is discarded by the last-resort WARNING
    # threshold and the audit line is lost.

    # (a) auto + route ⇒ resolved=routed
    canned = {'status': 'success', 'exit_code': 0, 'duration_seconds': 1, 'log_file': 'l', 'command': 'c'}
    monkeypatch.setattr(factory, '_route_to_daemon', lambda *a, **k: (canned, ''))
    monkeypatch.setattr(factory, 'cmd_run_common', lambda **kw: 0)
    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)
    cmd_run(_run_args(execution_mode='auto'))
    assert 'requested=auto, resolved=routed' in capsys.readouterr().err

    # (b) in_process ⇒ resolved=in_process
    def _must_not_route(*a, **k):
        raise AssertionError('in_process must not route')

    monkeypatch.setattr(factory, '_route_to_daemon', _must_not_route)
    entered: dict = {'slot': False, 'plan_id': None}
    _install_in_process_stubs(monkeypatch, entered)
    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)
    cmd_run(_run_args(execution_mode='in_process'))
    assert 'requested=in_process, resolved=in_process' in capsys.readouterr().err

    # (c) daemon + unavailable ⇒ resolved=fail-loud
    monkeypatch.setattr(factory, '_route_to_daemon', lambda *a, **k: (None, 'disabled'))
    monkeypatch.setattr(factory, 'build_queue_slot', lambda *a, **k: None)
    _, cmd_run = factory.create_execute_handlers(_config(), parse_log_fn=lambda *a: None)
    cmd_run(_run_args(execution_mode='daemon'))
    assert 'requested=daemon, resolved=fail-loud' in capsys.readouterr().err


# =============================================================================
# A routed build whose plan record is not in the child's tree
# =============================================================================
#
# The move-back window: ``integrate_into_main`` has moved the plan directory back
# to the main checkout, and the worktree directory still exists. A build routed
# with ``--plan-id`` in that window resolves fine in the ROUTING process (its cwd
# is main, which holds the plan record, and the record names the still-existing
# worktree) — and then the daemon child re-runs the same argv from the worktree,
# where the plan directory is absent. The child refuses with its own
# ``worktree_resolution_failed`` body and exit 2 unless the routing process hands
# it the tree it already resolved.
#
# The fixture below stages exactly that layout. The one thing it models rather
# than executes is the process hop inside ``file_ops._run_get_worktree_path``:
# the real verb shells out to ``manage-status get-worktree-path``, whose STRICT
# gate reads the plan record from the CURRENT checkout only. The model reads the
# same on-disk layout through the same ``derive_worktree_state``, so the hop's
# strictness is what is reproduced, not re-invented.

_MOVED_BACK_PLAN = 'plan-moved-back'

_MOVED_BACK_REASON = 'status.json not found for the moved-back plan'
"""The reason the child states; asserted at the routed layer, not only at the reader."""

#: The routed child's tree carry, spelled here because an executor's recorded
#: surface is what refuses it: the flag name is the whole fixture's premise.
_CARRY_FLAG = '--resolved-project-dir'


def _stage_moved_back_plan(plan_root: Path, worktree: Path) -> Path:
    """Stage the plan record on ``plan_root`` with ``worktree`` persisted in it."""
    plan_dir = plan_root / '.plan' / 'local' / 'plans' / _MOVED_BACK_PLAN
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text(
        json.dumps(
            {
                'plan_id': _MOVED_BACK_PLAN,
                'metadata': {
                    'use_worktree': 'true',
                    'worktree_path': str(worktree),
                    'worktree_branch': f'feature/{_MOVED_BACK_PLAN}',
                },
            }
        ),
        encoding='utf-8',
    )
    return plan_dir


def _strict_gate_reader():
    """``get-worktree-path``'s STRICT gate, read from the CURRENT checkout."""
    import file_ops

    def _strict_gate(plan_id: str):
        record = Path.cwd() / '.plan' / 'local' / 'plans' / plan_id / 'status.json'
        if not record.is_file():
            raise file_ops.WorktreeResolutionError(
                'manage-status get-worktree-path returned non-success: '
                f"error='file_not_found' message='status.json not found for {plan_id!r}'"
            )
        metadata = json.loads(record.read_text(encoding='utf-8')).get('metadata') or {}
        return file_ops.derive_worktree_state(metadata)

    return _strict_gate


def _stale_executor_refusal(argv: list[str]) -> dict | None:
    """The body a surface-predating executor emits for ``argv``, or ``None``.

    The executor validates an invocation against the surface it recorded when it was
    generated, and refuses an undeclared flag before spawning the script with a
    ``status: error`` / ``error: invalid_invocation`` body whose ``reason`` is
    ``unknown_flag``. A surface generated before the carry flag existed therefore
    refuses it — the shape this helper reproduces from the argv the routing seam
    would submit. A build whose argv carries no carry runs.

    Args:
        argv: The routed argv tail the daemon child would be re-run with.

    Returns:
        The refusal body, or ``None`` when the executor would spawn the script.
    """
    if _CARRY_FLAG not in argv:
        return None
    return {
        'status': 'error',
        'error': 'invalid_invocation',
        'notation': 'plan-marshall:build-pyproject:pyproject_build',
        'reason': 'unknown_flag',
        'rejected': _CARRY_FLAG,
        'accepted': '--command-args, --timeout, --mode, --format, --plan-id, --project-dir',
        'message': f'`{_CARRY_FLAG}` is not declared for `pyproject_build run`',
    }


def _job_log(tmp_path: Path, body: dict, name: str = 'job.log') -> str:
    """Write a child body as a job log, with the canonical TOON serializer."""
    from toon_parser import serialize_toon

    log = tmp_path / name
    log.write_text(serialize_toon(body), encoding='utf-8')
    return str(log)


@pytest.fixture
def moved_back_window(monkeypatch, tmp_path) -> dict:
    """The daemon child's view of the window: cwd in the worktree, plan record on main."""
    import file_ops

    main = tmp_path / 'main'
    worktree = tmp_path / 'worktree'
    worktree.mkdir(parents=True)
    _stage_moved_back_plan(main, worktree)
    monkeypatch.chdir(worktree)
    monkeypatch.setattr(file_ops, '_query_worktree_path', _strict_gate_reader())
    return {'main': main, 'worktree': worktree}


@pytest.fixture
def plan_bound_tree(monkeypatch, tmp_path) -> dict:
    """The steady state: one tree holds the plan record and runs every process.

    The routing process and the daemon child share it, so the child re-resolves the
    same record to the same path and needs no tree handed over.
    """
    import file_ops

    tree = tmp_path / 'worktree'
    tree.mkdir(parents=True)
    _stage_moved_back_plan(tree, tree)
    monkeypatch.chdir(tree)
    monkeypatch.setattr(file_ops, '_query_worktree_path', _strict_gate_reader())
    return {'tree': tree}


def _child_fault_job_log(tmp_path, plan_id: str = _MOVED_BACK_PLAN) -> str:
    """Write the job log the child produces, from the child's OWN error emitter."""
    import resolve_project_dir as routing
    from _build_format import format_toon

    exc = routing.WorktreeResolutionError(_MOVED_BACK_REASON)
    body = format_toon(routing.emit_worktree_error(plan_id, exc))
    log = tmp_path / 'moved-back-job.log'
    log.write_text(f'[EXEC] python3 .plan/execute-script.py … run --plan-id {plan_id}\n{body}', encoding='utf-8')
    return str(log)


class TestMovedBackPlanRoutedBuild:
    """A routed build in the move-back window: the child is handed the tree it cannot resolve."""

    def test_the_child_cannot_resolve_the_plan_from_its_own_tree(self, moved_back_window):
        """The child re-resolves ``--plan-id`` from a tree without the plan.

        The strict gate is NOT weakened here — this remains the child's answer. The
        routed re-run is fixed by handing the child the tree, never by relaxing the
        gate.
        """
        import resolve_project_dir as routing

        with pytest.raises(routing.WorktreeResolutionError):
            routing.resolve_project_dir(_MOVED_BACK_PLAN, '.', default='.')

    def test_the_routing_process_resolves_the_still_existing_worktree(self, moved_back_window, monkeypatch):
        """From MAIN the same flag resolves — the asymmetry is what strands the child."""
        monkeypatch.chdir(moved_back_window['main'])
        import resolve_project_dir as routing

        assert routing.resolve_project_dir(_MOVED_BACK_PLAN, '.', default='.') == str(
            moved_back_window['worktree'].resolve()
        )

    def test_the_direct_build_reports_the_same_fault_as_itself(self, moved_back_window, monkeypatch, capsys):
        """The in-process (direct) leg already answers as itself, with exit 2.

        This is the CONTRAST the routed leg has to match, and it is why the defect
        is routing-specific: the same tree, the same flag, the same missing plan
        record — only the non-routed path is honest about it.
        """
        import _build_cli  # the module owning build_main is the subject here
        from _build_cli import add_run_subparser, build_main

        def _register(subparsers):
            parser = add_run_subparser(subparsers, command_args_help='Test')
            parser.set_defaults(func=lambda _args: 0)

        monkeypatch.setattr(
            sys,
            'argv',
            ['pyproject_build.py', 'run', '--command-args', 'verify core', '--plan-id', _MOVED_BACK_PLAN],
        )

        rc = build_main('Python build', [_register])

        emitted = capsys.readouterr().out
        assert rc == 2
        assert 'error: worktree_resolution_failed' in emitted

    def test_the_routed_result_reaches_the_caller_as_the_child_reported_it(self, tmp_path, capsys):
        """The child's routing fault arrives under its own name and code."""
        from _build_shared import cmd_run_common

        log_file = _child_fault_job_log(tmp_path)
        result = factory._daemon_result_to_direct(
            {
                'job_status': 'failure',
                'exit_code': 2,
                'duration_seconds': 1,
                'log_file': log_file,
            },
            f'python3 .plan/execute-script.py … run --plan-id {_MOVED_BACK_PLAN}',
        )

        assert result['error'] == 'worktree_resolution_failed', (
            'the child reported a routing fault before any tool ran; the routed result must carry it as itself'
        )
        assert result['exit_code'] == 2

        cmd_run_common(result, lambda _log: ([], None, 'FAILURE'), 'python')
        emitted = capsys.readouterr().out
        assert 'worktree_resolution_failed' in emitted
        assert _MOVED_BACK_REASON in emitted, "the child's own reason text travels, not just a `reason:` label"
        assert 'exit_code: 2' in emitted, 'the routed path answers the code the direct path answers'
        assert 'no structured errors were parsed' not in emitted, (
            'a routing fault is not a build failure, so no synthetic build_failure row may be published'
        )

    def test_the_routed_child_carries_the_tree_the_routing_process_resolved(
        self, moved_back_window, use_fake_client, monkeypatch
    ):
        """The re-run command carries the resolved tree, and keeps the plan id.

        The plan id has to survive for BOTH attributions the child makes: the
        executor's ``kind=build`` ledger row (which reads ``--plan-id`` off the
        dispatch) and the machine-global build slot the child acquires. That is why
        the tree travels beside it rather than replacing it.
        """
        worktree = str(moved_back_window['worktree'].resolve())
        monkeypatch.chdir(moved_back_window['main'])
        monkeypatch.setattr(
            sys,
            'argv',
            ['pyproject_build.py', 'run', '--command-args', 'verify core', '--plan-id', _MOVED_BACK_PLAN],
        )
        client = use_fake_client(
            preflight={'status': 'success', 'preflight': 'ready'},
            submit={'status': 'success', 'job_id': 'JOB-7'},
            waits=[{'status': 'success', 'job_status': 'success', 'duration_seconds': 1, 'log_file': 'x.log'}],
        )

        result, reason = factory._route_to_daemon(_config(tool_name='python'), worktree, _MOVED_BACK_PLAN)

        assert reason == ''
        assert result is not None and result['status'] == 'success', 'the result is the build own result'
        submitted = json.loads(client.submit_calls[0].command)
        carried = submitted[4:]
        assert carried[:3] == ['--command-args', 'verify core', '--plan-id']
        assert carried[3] == _MOVED_BACK_PLAN
        assert carried[4] == '--resolved-project-dir'
        assert carried[5] == worktree, 'the child is handed the tree the routing process already resolved'
        from plan_logging import extract_plan_id

        assert extract_plan_id(submitted) == _MOVED_BACK_PLAN, 'the child ledger row keeps the plan id'

    def test_the_childs_entry_point_runs_the_build_in_the_carried_tree(self, moved_back_window, monkeypatch):
        """The child's own entry point runs the build there, and its result is the build's.

        The window's failure is the child's re-resolution, so the proof that the
        carry closes it is the child's entry point succeeding: the handler runs
        against the carried tree, and the value the entry point returns is the
        handler's own.
        """
        import _build_cli

        monkeypatch.setenv(MARSHALLD_JOB_ENV, '1')
        worktree = str(moved_back_window['worktree'].resolve())
        seen: list[str] = []

        def capture_run(args):
            seen.append(args.project_dir)
            return 7

        def register(subparsers):
            parser = _build_cli.add_run_subparser(subparsers, command_args_help='Test')
            parser.set_defaults(func=capture_run)

        monkeypatch.setattr(
            sys,
            'argv',
            [
                'pyproject_build.py',
                'run',
                '--command-args',
                'verify core',
                '--plan-id',
                _MOVED_BACK_PLAN,
                _CARRY_FLAG,
                worktree,
            ],
        )

        rc = _build_cli.build_main('Python build', [register])

        assert rc == 7, 'the entry point returns the build own result'
        assert seen == [worktree], 'the build ran against the tree the routing process resolved'


class TestStaleExecutorCarry:
    """A routed plan build is handed the tree only when its child cannot resolve it.

    An executor whose recorded surface predates the carry flag refuses that flag
    outright, and a routed result has no in-process fallback — so appending it where
    the child does not need it turns a healthy routed build into a refusal. The
    child's own tree holding the plan record is what decides.
    """

    def test_outside_the_window_a_stale_executor_runs_the_build(self, plan_bound_tree, use_fake_client, monkeypatch):
        """The tree resolves the plan itself, so no carry is appended and the build runs."""
        tree = str(plan_bound_tree['tree'].resolve())
        monkeypatch.setattr(
            sys,
            'argv',
            ['pyproject_build.py', 'run', '--command-args', 'verify core', '--plan-id', _MOVED_BACK_PLAN],
        )
        client = use_fake_client(
            preflight={'status': 'success', 'preflight': 'ready'},
            submit={'status': 'success', 'job_id': 'JOB-8'},
            waits=[{'status': 'success', 'job_status': 'success', 'duration_seconds': 2, 'log_file': 'x.log'}],
        )

        result, reason = factory._route_to_daemon(_config(tool_name='python'), tree, _MOVED_BACK_PLAN)

        submitted = json.loads(client.submit_calls[0].command)
        assert _stale_executor_refusal(submitted[4:]) is None, (
            'a surface-predating executor refuses the carry, so a tree that resolves the plan itself must not be handed it'
        )
        assert reason == ''
        assert result is not None and result['status'] == 'success', 'the result is the build own result'

    def test_inside_the_window_the_carry_is_still_appended(self, moved_back_window, use_fake_client, monkeypatch):
        """A tree without the record cannot resolve the plan, so the carry travels."""
        worktree = str(moved_back_window['worktree'].resolve())
        monkeypatch.setattr(
            sys,
            'argv',
            ['pyproject_build.py', 'run', '--command-args', 'verify core', '--plan-id', _MOVED_BACK_PLAN],
        )
        client = use_fake_client(
            preflight={'status': 'success', 'preflight': 'ready'},
            submit={'status': 'success', 'job_id': 'JOB-9'},
            waits=[{'status': 'success', 'job_status': 'success', 'duration_seconds': 1, 'log_file': 'x.log'}],
        )

        factory._route_to_daemon(_config(tool_name='python'), worktree, _MOVED_BACK_PLAN)

        submitted = json.loads(client.submit_calls[0].command)
        assert submitted[4 + 4 : 4 + 6] == [_CARRY_FLAG, worktree], (
            'the window child is stranded without the tree the routing process resolved'
        )

    def test_inside_the_window_the_refusal_reaches_the_caller_as_itself(self, tmp_path, capsys):
        """The same stale executor's refusal is reported as itself, not as a red build.

        A routed result has no in-process fallback, so a child that refuses the
        dispatch must reach the caller under the name and code the child used.
        """
        from _build_shared import cmd_run_common

        body = _stale_executor_refusal(
            ['run', '--command-args', 'verify core', '--plan-id', _MOVED_BACK_PLAN, _CARRY_FLAG, '/tree']
        )
        assert body is not None
        log_file = _job_log(tmp_path, body)

        result = factory._daemon_result_to_direct(
            {'job_status': 'failure', 'exit_code': 2, 'duration_seconds': 1, 'log_file': log_file},
            f'python3 .plan/execute-script.py ... run --plan-id {_MOVED_BACK_PLAN}',
        )

        assert result['error'] == 'invalid_invocation'
        assert result['reason'] == 'unknown_flag'
        assert result['exit_code'] == 2

        cmd_run_common(result, lambda _log: ([], None, 'FAILURE'), 'python')
        emitted = capsys.readouterr().out
        assert 'invalid_invocation' in emitted
        assert 'no structured errors were parsed' not in emitted, 'a refusal is not a build failure'


class TestPreToolFaultPassThrough:
    """A pre-tool refusal travels as itself, and a real failure still does not."""

    def test_a_build_that_ran_and_failed_keeps_build_failed_and_its_rows(self, tmp_path, capsys):
        """Matched control: the pass-through must not swallow a genuine failure.

        The discriminator is the child's own error NAME, never its exit code: a build
        that ran and failed reports ``build_failed`` with its parsed rows, and that
        path — including the synthetic row when nothing parsed — is untouched.
        """
        from _build_shared import cmd_run_common

        log = tmp_path / 'ran-and-failed.log'
        log.write_text(
            'status: error\nexit_code: 1\nerror: build_failed\n'
            'errors[1]{file,line,message,category}:\n'
            '  test/a.py,3,"assert 0",test_failure\n',
            encoding='utf-8',
        )
        result = factory._daemon_result_to_direct(
            {'job_status': 'failure', 'exit_code': 1, 'duration_seconds': 2, 'log_file': str(log)},
            'cmd',
        )

        assert result['error'] == 'build_failed'

        cmd_run_common(result, lambda _log: ([], None, 'FAILURE'), 'python')
        emitted = capsys.readouterr().out
        assert 'build_failed' in emitted
        assert 'test/a.py' in emitted, 'the inner wrapper per-test rows still travel'

    def test_the_reader_separates_a_pre_tool_fault_from_a_build_failure(self, tmp_path):
        """The reader's own discriminator: the error name, read off the child's body."""
        import _build_server_protocol as proto

        pre_tool = tmp_path / 'pre.log'
        pre_tool.write_text('status: error\nerror: mutually_exclusive_args\nmessage: pick one\n', encoding='utf-8')
        verdict = proto.read_log_verdict(str(pre_tool))

        assert verdict is not None
        assert verdict.fault is None, 'a routing refusal is not a launch fault'
        assert verdict.child_fault is not None
        assert verdict.child_fault.error == 'mutually_exclusive_args'
        assert verdict.child_fault.message == 'pick one', 'the resolution emitters state their detail in message'
        assert verdict.child_fault.reason is None, 'a body that states no reason keeps none'

        failed = tmp_path / 'failed.log'
        failed.write_text('status: error\nerror: build_failed\n', encoding='utf-8')
        failed_verdict = proto.read_log_verdict(str(failed))

        assert failed_verdict is not None
        assert failed_verdict.child_fault is None, 'a build that ran keeps the build-failure path'

    def test_a_json_formatted_refusal_is_read_as_a_verdict(self, tmp_path):
        """``--format json`` is a caller request, so the reader must understand it.

        A routed child asked for JSON writes its refusal as a JSON object, not as
        column-0 TOON keys. Without the JSON fallback the reader found no verdict and
        the whole job became ``build_failed`` with the synthetic row — the same
        collapse, one output format over. The log also holds progress output before
        the result, so the reader must find the LAST object rather than the first.
        """
        import json

        import _build_server_protocol as proto

        log = tmp_path / 'json-job.log'
        refusal = {
            'status': 'error',
            'error': 'queue_saturated',
            'message': 'no slot was admitted; retry later',
            'max_retries': 3,
            'plan_id': 'p',
        }
        log.write_text(
            '[EXEC] python3 .plan/execute-script.py … run --format json\n' + json.dumps(refusal, indent=2) + '\n',
            encoding='utf-8',
        )

        verdict = proto.read_log_verdict(str(log))

        assert verdict is not None
        assert verdict.status == 'error'
        assert verdict.child_fault is not None
        assert verdict.child_fault.error == 'queue_saturated'
        assert verdict.child_fault.message == 'no slot was admitted; retry later'
        assert verdict.child_fault.reason is None

    def test_a_json_timeout_keeps_its_applied_bound(self, tmp_path):
        """A JSON non-finish must name the bound the inner wrapper applied.

        The bound is what tells a reader whose number fired — a learned bound is
        corrected by one more measured run, an explicit one by raising it. The TOON
        path reads the triple; a JSON-formatted result must not lose it.
        """
        import json

        import _build_server_protocol as proto

        log = tmp_path / 'json-timeout.log'
        log.write_text(
            json.dumps(
                {
                    'status': 'timeout',
                    'error': 'timeout',
                    'exit_code': -1,
                    'timeout_used_seconds': 900,
                    'timeout_source': 'learned',
                    'command_key': 'python:module_tests',
                }
            ),
            encoding='utf-8',
        )

        verdict = proto.read_log_verdict(str(log))

        assert verdict is not None
        assert verdict.status == 'timeout'
        assert verdict.timeout_used_seconds == 900
        assert verdict.timeout_source == 'learned'
        assert verdict.command_key == 'python:module_tests'

    def test_a_trailing_json_object_cannot_discard_the_verdict(self, tmp_path):
        """The result is the last object WITH A STATUS, not the last object.

        A trailing ``{}`` or a footer object after the result would otherwise erase
        the verdict and send the whole job back to ``build_failed`` — the collapse
        this fallback exists to prevent.
        """
        import json

        import _build_server_protocol as proto

        log = tmp_path / 'json-trailing.log'
        log.write_text(
            json.dumps({'status': 'error', 'error': 'queue_saturated', 'message': 'retry later'})
            + '\n'
            + json.dumps({})
            + '\n',
            encoding='utf-8',
        )

        verdict = proto.read_log_verdict(str(log))

        assert verdict is not None
        assert verdict.child_fault is not None
        assert verdict.child_fault.error == 'queue_saturated'

    def test_a_json_failure_keeps_its_rows_and_the_build_failure_path(self, tmp_path):
        """Matched control: JSON parsing must not turn a real failure into a refusal."""
        import json

        import _build_server_protocol as proto

        log = tmp_path / 'json-failure.log'
        log.write_text(
            json.dumps(
                {
                    'status': 'error',
                    'error': 'build_failed',
                    'exit_code': 1,
                    'tests_run': 12,
                    'errors': [{'file': 'test/a.py', 'line': 4, 'message': 'boom', 'category': 'test_failure'}],
                },
                indent=2,
            ),
            encoding='utf-8',
        )

        verdict = proto.read_log_verdict(str(log))

        assert verdict is not None
        assert verdict.status == 'error'
        assert verdict.child_fault is None and verdict.fault is None
        assert verdict.tests_run == 12
        assert [row['file'] for row in verdict.errors] == ['test/a.py']

    def test_a_log_that_states_no_verdict_in_either_format_is_none(self, tmp_path):
        """No TOON status and no JSON object: nothing was established, so nothing is claimed."""
        import _build_server_protocol as proto

        log = tmp_path / 'noise.log'
        log.write_text('usage: unrecognized arguments: --resolved-project-dir\n', encoding='utf-8')

        assert proto.read_log_verdict(str(log)) is None

    def test_a_slot_refusal_is_a_pre_tool_fault_and_keeps_its_message(self, tmp_path, capsys):
        """A child that never got a build slot is a refusal, not a red build.

        The log is the producer's own emitted body, not a hand-written shape, so a
        field the emitter stops writing fails here instead of being papered over by
        the fixture. The producer states ``message`` and no ``reason``, and the
        reader must keep those names rather than substituting one for the other.
        """
        import _build_server_protocol as proto

        exc = slot_mod.BuildQueueTimeout('plan-x', 3)
        assert factory._emit_queue_timeout('python', 'verify core', 'toon', exc) == 1
        log = tmp_path / 'queue.log'
        log.write_text(capsys.readouterr().out, encoding='utf-8')

        verdict = proto.read_log_verdict(str(log))

        assert verdict is not None and verdict.child_fault is not None
        assert verdict.child_fault.error == 'queue_saturated'
        assert verdict.child_fault.message == str(exc)
        assert verdict.child_fault.reason is None, 'the producer states no reason, so none may be invented'

    def test_a_slot_refusal_keeps_the_producers_field_names_across_the_hop(self, tmp_path, capsys):
        """The routed result carries the child's ``message`` as ``message``.

        A body with only a ``message`` that arrives as ``reason`` leaves a consumer
        reading ``message`` empty on the routed route while the direct route fills
        it — the same fault, two shapes.
        """
        exc = slot_mod.BuildQueueTimeout('plan-x', 3)
        assert factory._emit_queue_timeout('python', 'verify core', 'toon', exc) == 1
        log = tmp_path / 'queue.log'
        log.write_text(capsys.readouterr().out, encoding='utf-8')

        result = factory._daemon_result_to_direct(
            {'job_status': 'failure', 'exit_code': 1, 'duration_seconds': 3, 'log_file': str(log)},
            'cmd',
        )

        assert result['error'] == 'queue_saturated'
        assert result['message'] == str(exc)
        assert 'reason' not in result, 'the child stated no reason, so the routed result carries none'

    def test_an_errors_table_from_another_block_is_not_carried(self, tmp_path):
        """A table belongs to the block that carried it, like every other key.

        A verdict block that states no ``errors[]`` table reports no rows, rather
        than inheriting the rows of whatever wrote earlier to the same log.
        """
        import _build_server_protocol as proto

        log = tmp_path / 'two-table-blocks.log'
        log.write_text(
            'status: error\nerror: build_failed\n'
            'errors[1]{file,line,message,category}:\n'
            '  test/earlier.py,1,"earlier failure",test_failure\n'
            'status: error\nerror: worktree_resolution_failed\nmessage: the record left this tree\n',
            encoding='utf-8',
        )

        verdict = proto.read_log_verdict(str(log))

        assert verdict is not None and verdict.child_fault is not None
        assert verdict.errors == (), "the earlier block's rows are not this verdict's rows"

    def test_a_key_from_another_block_cannot_supply_the_verdict(self, tmp_path):
        """Each key is read from the block that holds the verdict.

        A log is a file, so it can hold an earlier body beside the result. Reading
        ``reason`` last-wins across the whole file would attach that writer's reason
        to a refusal whose own block stated only ``message``.
        """
        import _build_server_protocol as proto

        log = tmp_path / 'two-blocks.log'
        log.write_text(
            'status: error\nreason: earlier-writer\n'
            'status: error\nerror: worktree_resolution_failed\nmessage: the record left this tree\n',
            encoding='utf-8',
        )

        verdict = proto.read_log_verdict(str(log))

        assert verdict is not None and verdict.child_fault is not None
        assert verdict.child_fault.message == 'the record left this tree'
        assert verdict.child_fault.reason is None, 'that reason belongs to the earlier block'

    def test_the_emitted_identifiers_are_the_ones_the_lane_classifies(self):
        """Every pre-tool emitter's identifier is a member of the classifier set.

        A fault identifier spelled differently at the producer and in the reader's set
        would silently fall back to ``build_failed`` — the defect this deliverable
        removes — so the agreement is asserted rather than assumed, one producer at a
        time. The executor's refusal literal lives in the generator template, so that
        producer is tied to the set through the template's own text.
        """
        import resolve_project_dir as routing
        from _build_result import (
            ERROR_BUILD_QUEUE_UNAVAILABLE,
            ERROR_DIRECTORY_LOCK_UNAVAILABLE,
            ERROR_INVALID_INVOCATION,
            ERROR_QUEUE_SATURATED,
            PRE_TOOL_FAULT_ERRORS,
        )

        assert routing.emit_worktree_error('p', routing.WorktreeResolutionError('x'))['error'] in (
            PRE_TOOL_FAULT_ERRORS
        )
        assert routing.emit_mutually_exclusive_error('p', 'q')['error'] in PRE_TOOL_FAULT_ERRORS
        assert routing.emit_carried_tree_outside_job_error('/tree', 'p')['error'] in PRE_TOOL_FAULT_ERRORS
        assert ERROR_INVALID_INVOCATION in PRE_TOOL_FAULT_ERRORS
        assert ERROR_QUEUE_SATURATED in PRE_TOOL_FAULT_ERRORS
        # The factory RE-USES those constants rather than spelling the identifiers
        # again, so the limiter faults it emits are classified by construction.
        assert factory.ERROR_QUEUE_SATURATED is ERROR_QUEUE_SATURATED
        assert factory.ERROR_BUILD_QUEUE_UNAVAILABLE is ERROR_BUILD_QUEUE_UNAVAILABLE
        assert factory.ERROR_DIRECTORY_LOCK_UNAVAILABLE is ERROR_DIRECTORY_LOCK_UNAVAILABLE

        template = (
            Path(__file__).parents[3]
            / 'marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template'
        )
        assert template.is_file(), f'the executor template moved; this drift guard must follow it: {template}'
        assert f'error: {ERROR_INVALID_INVOCATION}' in template.read_text(encoding='utf-8')


class TestCarriedTreeRefusalDiagnostics:
    """The carried-tree refusal's own facts reach a TOON consumer.

    The formatter's extra-field list is a WHITELIST and the refusal is printed
    through it, so a field missing from that list is dropped from TOON output while
    the JSON path still carries it. Both fields are the diagnosis: which tree the
    carry pointed at, and which plan it would have been attributed to.
    """

    def test_the_refusal_names_the_tree_and_the_plan_it_would_attribute(self, monkeypatch, capsys):
        import _build_cli

        monkeypatch.delenv(MARSHALLD_JOB_ENV, raising=False)

        def register(subparsers):
            parser = _build_cli.add_run_subparser(subparsers, command_args_help='Test')
            parser.set_defaults(func=lambda _args: 0)

        carried_tree = '/routed/tree/plan-x'
        monkeypatch.setattr(
            sys,
            'argv',
            ['pyproject_build.py', 'run', '--command-args', 'verify', '--plan-id', 'plan-x', _CARRY_FLAG, carried_tree],
        )

        rc = _build_cli.build_main('Python build', [register])

        emitted = capsys.readouterr().out
        assert rc == 2
        assert 'error: carried_tree_outside_daemon_job' in emitted
        assert 'resolved_project_dir' in emitted, 'the refused tree is half the diagnosis'
        assert carried_tree in emitted
        assert 'plan_id' in emitted, 'the plan it would have been attributed to is the other half'
        assert 'plan-x' in emitted


class TestIndeterminateReasonCarry:
    """A child's ``indeterminate`` verdict keeps the REASON it stated.

    The wire maps ``indeterminate`` onto ``failure``, so ``failure`` is the shape a
    routed ``indeterminate`` arrives in. Rebuilding it as a generic ``build_failed``
    would discard the producer's named reason and take the build-failure path —
    fabricating the failure the producer's own status exists to deny.
    """

    def test_an_indeterminate_child_verdict_keeps_its_own_reason(self, tmp_path):
        """The child's ``message:`` line IS the reason the caller must receive."""
        log = tmp_path / 'indeterminate.log'
        reason = "test_selector_matched_nothing: 'Awaits#runs' matched no test, so the run executed nothing"
        log.write_text(f'status: indeterminate\nexit_code: 0\nmessage: "{reason}"\n', encoding='utf-8')

        result = factory._daemon_result_to_direct(
            {'job_status': 'failure', 'exit_code': 0, 'duration_seconds': 4, 'log_file': str(log)},
            'cmd',
        )

        assert result['status'] == 'indeterminate'
        assert result['message'] == reason

    def test_a_verdict_that_states_no_reason_still_gets_the_generic_sentence(self, tmp_path):
        """Matched control: the carry must not invent a reason the log never stated."""
        log = tmp_path / 'no-reason.log'
        log.write_text('status: quiesced\nexit_code: 0\n', encoding='utf-8')

        result = factory._daemon_result_to_direct(
            {'job_status': 'failure', 'exit_code': 0, 'duration_seconds': 4, 'log_file': str(log)},
            'cmd',
        )

        assert result['status'] == 'indeterminate'
        assert 'quiesced' in result['message']
        assert 'outside the build-result vocabulary' in result['message']

    def test_a_real_failure_stays_a_build_failure(self, tmp_path):
        """Matched control: only a non-``error`` verdict is re-rendered as itself."""
        log = tmp_path / 'failed.log'
        log.write_text(
            'status: error\nexit_code: 1\nerror: build_failed\n'
            'errors[1]{file,line,message,category}:\n'
            '  test/a.py,3,"assert 0",test_failure\n',
            encoding='utf-8',
        )

        result = factory._daemon_result_to_direct(
            {'job_status': 'failure', 'exit_code': 1, 'duration_seconds': 4, 'log_file': str(log)},
            'cmd',
        )

        assert result['status'] == 'error'
        assert result['error'] == 'build_failed'

    def test_a_timeout_child_reaches_the_caller_as_a_timeout(self, tmp_path):
        """A routed ``timeout`` keeps its own status and the bound that fired.

        The supervisor translates the wrapper's own ``timeout`` verdict onto the wire
        row of the same name, so the caller sees a non-finish with its applied bound
        rather than a red build.
        """
        log = tmp_path / 'timeout.log'
        log.write_text(
            'status: timeout\nexit_code: -1\ntimeout_used_seconds: 300\ntimeout_source: explicit\n',
            encoding='utf-8',
        )

        result = factory._daemon_result_to_direct(
            {
                'job_status': 'timeout',
                'exit_code': -1,
                'duration_seconds': 300,
                'log_file': str(log),
                'timeout_used_seconds': 300,
                'timeout_source': 'explicit',
            },
            'cmd',
        )

        assert result['status'] == 'timeout'
        assert result['timeout_used_seconds'] == 300

    def test_a_killed_child_reaches_the_caller_as_a_kill(self, tmp_path):
        """A routed ``killed`` keeps its own status, its exit code and its instruction."""
        log = tmp_path / 'killed.log'
        log.write_text('status: killed\nexit_code: -9\n', encoding='utf-8')

        result = factory._daemon_result_to_direct(
            {'job_status': 'killed', 'exit_code': -9, 'duration_seconds': 12, 'log_file': str(log)},
            'cmd',
        )

        assert result['status'] == 'killed'
        assert result['exit_code'] == -9
        assert 'do not blind-retry' in result['message']

    def test_the_selector_reason_survives_both_wire_legs(self, tmp_path):
        """The child's own reason reaches the caller whichever wire row it arrived on.

        The wire flattens an ``indeterminate`` child verdict onto ``failure``, while
        the success cross-check reads the same verdict off a ``success`` row. Both
        legs answer with the producer's own message, so a selector miss is not lost
        to which row the daemon chose.
        """
        reason = "test_selector_matched_nothing: 'Awaits#runs' matched no test, so the run executed nothing"
        log = tmp_path / 'selector.log'
        log.write_text(f'status: indeterminate\nexit_code: 0\nmessage: "{reason}"\n', encoding='utf-8')

        from_failure = factory._daemon_result_to_direct(
            {'job_status': 'failure', 'exit_code': 0, 'duration_seconds': 4, 'log_file': str(log)},
            'cmd',
        )
        from_success = factory._daemon_result_to_direct(
            {'job_status': 'success', 'exit_code': 0, 'duration_seconds': 4, 'log_file': str(log)},
            'cmd',
        )

        assert from_failure['status'] == 'indeterminate'
        assert from_failure['message'] == reason
        assert from_success['status'] == 'indeterminate'
        assert from_success['message'] == reason

    def test_a_multiline_log_message_is_collapsed_before_rendering(self, tmp_path):
        """A log message that carries real newlines must not break the envelope.

        The JSON log path decodes ``\\n`` escapes into real newlines, and the
        result formatter does not re-escape them inside an ordinary string
        value, so the carried message is collapsed to one line.
        """
        import json

        log = tmp_path / 'multiline.log'
        log.write_text(
            json.dumps({'status': 'indeterminate', 'exit_code': 0, 'message': 'first line\nsecond line'}),
            encoding='utf-8',
        )

        result = factory._daemon_result_to_direct(
            {'job_status': 'failure', 'exit_code': 0, 'duration_seconds': 4, 'log_file': str(log)},
            'cmd',
        )

        assert result['status'] == 'indeterminate'
        assert result['message'] == 'first line second line'
