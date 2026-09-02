#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""An explicit ``--timeout`` binds on the DAEMON-ROUTED leg, not just in-process.

``_build_cli.add_run_subparser`` documents ``--timeout`` as an override of the
learned value. That claim held only on the in-process leg: the routed leg dropped
the value at the wire boundary — ``_route_to_daemon`` never forwarded it,
``JobSpec`` had no field to carry it, and the daemon therefore bounded EVERY
routed build by its own default. A caller asking for 3000s got 1800s back with a
``timeout`` status and nothing saying its bound had been discarded.

The property was untestable from where it was tested: ``test/conftest.py``'s
autouse ``_neutralize_daemon_routing`` fixture patches ``_route_to_daemon`` out
for every test outside this directory, and the truthfulness suite pins
``execution_mode='in_process'``. This module lives under
``test/plan-marshall/build-server/``, which that fixture carves out BY LOCATION,
so the real routing seam runs here.

Three layers, ending in one chain:

1. ``cmd_run`` forwards the bound into ``_route_to_daemon`` and on into the
   client's ``submit`` call — with the matched negative that an unsupplied flag
   stays unsupplied.
2. The client puts a supplied bound on the wire and OMITS the key when there is
   none, so a spec stating no bound keeps the wire shape it always had.
3. ``Daemon._execute`` raises its supervisory bound to the job's, falls back to
   its own default when the job states none, and treats that default as a FLOOR
   a smaller request cannot undercut.

``JobSpec``'s own codec contract for the field lives with the rest of the codec,
in ``test_build_server_protocol.py``.

The closing chain test drives 1 → 3 with only the socket and the build subprocess
faked, so the value ``run_job`` is bounded by is the one ``cmd_run`` was handed.
Against the pre-fix code it fails at the first link.
"""

from __future__ import annotations

import asyncio
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest
from _build_extension_fixtures import build_scripts_dir, execute_config
from conftest import get_script_path

_SHARED_SCRIPTS = build_scripts_dir().parent
_CLIENT_SCRIPTS = get_script_path('plan-marshall', 'build-server-client', 'build_server.py').parent
_DAEMON_SCRIPTS = get_script_path('plan-marshall', 'manage-build-server', 'marshalld.py').parent
_LOGGING_SCRIPTS = get_script_path('plan-marshall', 'manage-logging', 'plan_logging.py').parent

for _dep in (_SHARED_SCRIPTS, _CLIENT_SCRIPTS, _DAEMON_SCRIPTS, _LOGGING_SCRIPTS):
    if str(_dep) not in sys.path:
        sys.path.insert(0, str(_dep))

import _build_execute_factory as factory  # noqa: E402
import build_server as bsclient  # noqa: E402
import marshalld  # noqa: E402
from _build_execute import CaptureStrategy  # noqa: E402
from _build_server_protocol import MARSHALLD_JOB_ENV, JobSpec, make_job_spec  # noqa: E402
from _marshalld_journal import Journal  # noqa: E402
from _marshalld_scheduler import Scheduler  # noqa: E402

#: The bound every layer below carries. Deliberately ABOVE the daemon default, so
#: a dropped forward is unmistakable: with the value discarded the supervisor
#: resolves 1800 — exactly what the field report showed.
REQUESTED_TIMEOUT = 3000

#: A request BELOW the daemon default, for the floor assertion.
BELOW_DEFAULT_TIMEOUT = 120


# =============================================================================
# Fixtures / helpers
# =============================================================================


@pytest.fixture(autouse=True)
def _clear_reentrancy(monkeypatch):
    """The re-entrancy marker must be absent or nothing routes at all."""
    monkeypatch.delenv(MARSHALLD_JOB_ENV, raising=False)


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """Point the machine-global home root at an isolated tmp dir."""
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return Path(tmp_path)


class _RecordingClient:
    """A build_server stand-in recording the ``submit`` Namespace it was handed."""

    def __init__(self) -> None:
        self.submit_calls: list[Namespace] = []

    def run_preflight(self, _args) -> dict:
        return {'status': 'success', 'preflight': 'ready'}

    def run_submit(self, args) -> dict:
        self.submit_calls.append(args)
        return {'status': 'success', 'job_id': 'JOB-T'}

    def run_wait(self, _args) -> dict:
        return {
            'status': 'success',
            'job_status': 'success',
            'duration_seconds': 1,
            'log_file': 'job.log',
        }


class _RealSubmitClient(_RecordingClient):
    """Records the submit AND delegates it to the REAL client verb.

    The chain test needs the genuine ``run_submit`` — the layer that builds the
    job spec — rather than a canned response, so the wire frame it asserts on is
    the one production would have sent.
    """

    def run_submit(self, args) -> dict:
        self.submit_calls.append(args)
        return bsclient.run_submit(args)


@pytest.fixture
def wire_frames(monkeypatch) -> list[dict]:
    """Stub the client's socket + ledger seams; collect the request frames sent."""
    frames: list[dict] = []

    def _call(request, timeout):
        # ``timeout`` is the SOCKET read budget, not the job bound; unused here.
        frames.append(request)
        return {'status': 'queued', 'job_id': 'JOB-T', 'attached': False}

    monkeypatch.setattr(bsclient, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(bsclient, '_call_daemon', _call)
    monkeypatch.setattr(bsclient, '_record_job', lambda *_a, **_k: None)
    return frames


def _run_args(**overrides) -> Namespace:
    base = {
        'command_args': 'verify',
        'project_dir': '/tree',
        'plan_id': 'plan-x',
        'format': 'toon',
        'mode': 'actionable',
        'timeout': None,
        'execution_mode': 'auto',
    }
    base.update(overrides)
    return Namespace(**base)


def _routing_cmd_run(monkeypatch, client):
    """Return a ``cmd_run`` whose routed leg reaches ``client``, rendering stubbed."""
    monkeypatch.setattr(sys, 'argv', ['pyproject_build.py', 'run', '--command-args', 'verify'])
    monkeypatch.setattr(factory, '_load_build_server', lambda: client)
    monkeypatch.setattr(factory, 'cmd_run_common', lambda **_kw: 0)
    config = execute_config(factory, CaptureStrategy.STDOUT_REDIRECT, tool_name='python')
    _, cmd_run = factory.create_execute_handlers(config, parse_log_fn=lambda *_a: None)
    return cmd_run


def _submit_args(project_path: str, **overrides) -> Namespace:
    """The client ``submit`` Namespace, shaped as ``_route_to_daemon`` builds it."""
    base = {
        'command': json.dumps(
            ['python3', f'{project_path}/.plan/execute-script.py', 'a:b:c', 'run']
        ),
        'exec_path': project_path,
        'project_path': project_path,
        'plan_id': 'p1',
        'timeout': None,
    }
    base.update(overrides)
    return Namespace(**base)


def _spec(project_root: Path, timeout: int | None) -> JobSpec:
    return make_job_spec(
        command=['python3', str(project_root / '.plan' / 'execute-script.py'), 'a:b:c', 'run'],
        exec_path=str(project_root),
        project_path=str(project_root),
        plan_id='p1',
        timeout=timeout,
    )


def _bound_run_job_received(tmp_path, spec: JobSpec, monkeypatch) -> int:
    """Drive the REAL ``_execute`` seam and return the bound ``run_job`` was given.

    The job is submitted and admitted first, exactly as ``_admit_ready`` does in
    production — ``_execute``'s scheduler tail is a no-op on a job that was never
    admitted, leaving the job's own queue entry behind for the tail to re-admit.
    """
    daemon = marshalld.Daemon(
        scheduler=Scheduler(max_slots=1),
        journal=Journal(),
        log_dir=tmp_path / 'job-logs',
    )
    seen: dict[str, int] = {}

    async def _fake_run_job(*_args, **kwargs):
        seen['timeout'] = kwargs['timeout']
        return {'status': 'success', 'duration_seconds': 1, 'log_file': 'x'}

    monkeypatch.setattr(marshalld, 'run_job', _fake_run_job)

    result = daemon._scheduler.submit(spec, 'root')
    daemon._journal.record_spec(result.job_id, spec.to_dict())
    admitted = daemon._scheduler.admit_next()
    assert admitted is not None and admitted.job_id == result.job_id
    daemon._journal.record_status(result.job_id, 'running')
    asyncio.run(daemon._execute(result.job_id, spec.to_dict()))

    assert 'timeout' in seen, 'run_job was never reached'
    return seen['timeout']


# =============================================================================
# 1. cmd_run -> _route_to_daemon -> the client submit call
# =============================================================================


def test_cmd_run_forwards_the_explicit_timeout_to_the_submit(monkeypatch):
    """The routed leg carries ``--timeout`` into the submit it sends.

    This is the layer the defect lived at: ``cmd_run`` read ``explicit_timeout``
    correctly and then called ``_route_to_daemon`` without it, so the value
    reached the in-process leg and nowhere else.
    """
    client = _RecordingClient()
    cmd_run = _routing_cmd_run(monkeypatch, client)

    assert cmd_run(_run_args(timeout=REQUESTED_TIMEOUT)) == 0

    assert len(client.submit_calls) == 1
    assert client.submit_calls[0].timeout == REQUESTED_TIMEOUT


def test_cmd_run_without_the_flag_submits_no_bound(monkeypatch):
    """The matched negative: an unsupplied flag stays unsupplied on the wire.

    Without it, a forward hard-coding any value would satisfy the test above
    while destroying the "no bound stated, use the daemon default" case.
    """
    client = _RecordingClient()
    cmd_run = _routing_cmd_run(monkeypatch, client)

    assert cmd_run(_run_args(timeout=None)) == 0

    assert client.submit_calls[0].timeout is None


# =============================================================================
# 2. The client puts the bound on the wire
# =============================================================================


def test_submit_puts_the_explicit_bound_on_the_wire(home, wire_frames):
    result = bsclient.run_submit(_submit_args(str(home / 'proj'), timeout=REQUESTED_TIMEOUT))

    assert result['status'] == 'success'
    assert wire_frames[0]['job']['timeout'] == REQUESTED_TIMEOUT


def test_submit_without_a_bound_omits_the_key(home, wire_frames):
    """An absent bound is absent from the frame, not a null the daemon must read."""
    bsclient.run_submit(_submit_args(str(home / 'proj')))

    assert 'timeout' not in wire_frames[0]['job']


# =============================================================================
# 3. The daemon applies the job's bound
# =============================================================================


def test_daemon_raises_its_bound_to_the_requested_one(home, tmp_path, monkeypatch):
    """The supervisor runs the child under the REQUESTED bound, not the default.

    Asserted as ``> _DEFAULT_JOB_TIMEOUT`` alongside the exact value, so a
    regression back to the default is named for what it is.
    """
    received = _bound_run_job_received(tmp_path, _spec(home, REQUESTED_TIMEOUT), monkeypatch)

    assert received > marshalld._DEFAULT_JOB_TIMEOUT
    assert received == REQUESTED_TIMEOUT + marshalld._JOB_TIMEOUT_MARGIN_SECONDS


def test_daemon_falls_back_to_its_default_when_no_bound_is_stated(home, tmp_path, monkeypatch):
    received = _bound_run_job_received(tmp_path, _spec(home, None), monkeypatch)

    assert received == marshalld._DEFAULT_JOB_TIMEOUT


def test_a_request_below_the_default_does_not_lower_the_outer_bound(home, tmp_path, monkeypatch):
    """The daemon default is a FLOOR: a smaller request cannot undercut the child.

    The child enforces the smaller bound itself (it re-runs the same argv), so an
    outer bound beneath it would kill the run before the child's own timeout
    could report which step hung — the inner/outer inversion the margin exists to
    prevent, arriving from the other direction.
    """
    received = _bound_run_job_received(tmp_path, _spec(home, BELOW_DEFAULT_TIMEOUT), monkeypatch)

    assert received == marshalld._DEFAULT_JOB_TIMEOUT


# =============================================================================
# The chain — cmd_run's --timeout is the bound the supervisor measures against
# =============================================================================


def test_the_requested_bound_survives_from_cmd_run_to_the_supervisor(
    home, tmp_path, monkeypatch, wire_frames
):
    """END TO END: the value ``cmd_run`` was handed is the one that bounds the child.

    Every test above is one link; this asserts the chain. Only the socket and the
    build subprocess are faked — the real ``_route_to_daemon``, the real client
    ``run_submit``, the real ``JobSpec`` codec, and the real ``Daemon._execute``
    all run. Against the pre-fix code it fails at the first link, with the
    supervisor bounded by the daemon default instead of the caller's request.
    """
    project = home / 'proj'
    project.mkdir()
    cmd_run = _routing_cmd_run(monkeypatch, _RealSubmitClient())

    assert cmd_run(_run_args(project_dir=str(project), timeout=REQUESTED_TIMEOUT)) == 0

    # The frame the daemon would have received, handed to the real daemon.
    received = _bound_run_job_received(
        tmp_path, JobSpec.from_dict(wire_frames[0]['job']), monkeypatch
    )

    assert received == REQUESTED_TIMEOUT + marshalld._JOB_TIMEOUT_MARGIN_SECONDS, (
        f'the caller asked for {REQUESTED_TIMEOUT}s and the supervisor was bounded by '
        f'{received}s; a bound equal to the daemon default means the explicit '
        '--timeout was dropped somewhere on the routed leg'
    )
