#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Acceptance: the status-TOON's two hard guarantees.

A bound-expiry wait returns a LIVE running status carrying elapsed / eta /
last_progress — never a timeout-shaped empty body. And a killed job is rendered
by the client with the no-blind-retry message, never folded into failure.
"""

from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace

# PLAIN import, deliberately: the build-server suites annotate against
# ``marshalld.Daemon``, which only a plain import gives mypy. The name is bound the
# same way in every suite, so no loaded copy is published beside it.
import marshalld
import pytest
from _build_server_protocol import STATUS_KILLED, STATUS_RUNNING, JobSpec
from _marshalld_journal import Journal
from _marshalld_scheduler import Scheduler

from conftest import load_script_module, parse_ns

#: ``register=False`` because only the returned module is used here. Publishing
#: ``build_server`` into ``sys.modules`` would collide with the sibling modules
#: that import it plainly, and a plain importer then reaches whichever copy was
#: registered last rather than the one this module loaded.
client = load_script_module(
    'plan-marshall',
    'build-server-client',
    'build_server.py',
    register=False,
)

#: The one ``wait`` command line this module drives, parsed by ``build_server.py``'s
#: OWN parser. Every value is fixed, so no per-test derivation is needed. Hoisted
#: because ``parse_ns`` re-executes the script module on every call, and
#: ``register=False`` for the same reason the loader above passes it.
_WAIT_ARGS = parse_ns(
    'plan-marshall',
    'build-server-client',
    'build_server.py',
    'wait',
    '--job-id',
    'J',
    '--plan-id',
    '',
    '--bound',
    '1',
    register=False,
)


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return tmp_path


def test_bound_expiry_wait_is_a_live_running_status(home, tmp_path):
    async def _drive():
        daemon = marshalld.Daemon(
            scheduler=Scheduler(max_slots=1),
            journal=Journal(),
            log_dir=tmp_path / 'job-logs',
        )
        spec = JobSpec(
            command=[sys.executable, '-c', 'import time; time.sleep(0.5)'],
            exec_path=str(tmp_path),
            project_path=str(tmp_path),
            plan_id='p',
            fingerprint='fp',
        )
        result = daemon._scheduler.submit(spec, 'root')
        daemon._journal.record_spec(result.job_id, spec.to_dict())
        daemon._admit_ready()
        waited = await daemon._wait({'job_id': result.job_id, 'bound': 0})
        await asyncio.gather(*list(daemon._tasks.values()), return_exceptions=True)
        return waited

    waited = asyncio.run(_drive())

    # A live running status — never a timeout-shaped / empty body.
    assert waited['status'] == STATUS_RUNNING
    assert 'elapsed' in waited
    assert 'last_progress' in waited
    assert 'eta' in waited
    assert waited.get('status') != 'timeout'


def test_client_renders_killed_with_no_blind_retry_message(home, monkeypatch):
    # A daemon 'killed' status crosses the client and is rendered verbatim with
    # the do-not-blind-retry message — never folded into failure.
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {'status': STATUS_KILLED, 'job_id': 'J', 'exit_code': -9},
    )

    result = client.run_wait(_WAIT_ARGS)

    assert result['job_status'] == STATUS_KILLED
    assert 'do not blind-retry' in result['message']


# =============================================================================
# D2: the wait is visible — queued status, waiting_on, queued_seconds
# =============================================================================
# A job that has not been admitted yet used to be reported as ``running`` with
# ``elapsed`` 0, indistinguishable from a job that had just started. These tests
# pin the queued shape, the submit's ``queued_behind``, and that a terminal
# result carries the wait it paid.


def _spec_for(directory, notation: str) -> JobSpec:
    executor = f'{directory}/.plan/execute-script.py'
    return JobSpec(
        command=[sys.executable, executor, notation],
        exec_path=str(directory),
        project_path=str(directory),
        plan_id='p',
        fingerprint=f'fp-{notation}',
    )


def _accept_every_submit(monkeypatch) -> None:
    outcome = SimpleNamespace(accepted=True, record={'canonical_root': '/proj'})
    monkeypatch.setattr(marshalld, 'read_registry', lambda: {})
    monkeypatch.setattr(marshalld, 'verify_submit', lambda *_a, **_k: outcome)


def _gated_run_job(monkeypatch, gate):
    async def fake_run_job(command, project_path, **_kwargs):
        await gate.wait()
        return {'status': 'success', 'exit_code': 0, 'duration_seconds': 1, 'log_file': ''}

    monkeypatch.setattr(marshalld, 'run_job', fake_run_job)


def test_submit_carries_queued_behind_for_a_busy_directory(home, tmp_path, monkeypatch):
    """``queued_behind`` names the job running in the same directory, and is
    empty when nothing is."""
    _accept_every_submit(monkeypatch)

    async def _drive():
        gate = asyncio.Event()
        _gated_run_job(monkeypatch, gate)
        daemon = marshalld.Daemon(
            scheduler=Scheduler(max_slots=2), journal=Journal(), log_dir=tmp_path / 'job-logs'
        )
        w1 = tmp_path / 'W1'
        w2 = tmp_path / 'W2'
        a = await daemon.handle_request({'op': 'submit', 'job': _spec_for(w1, 'a:1:x').to_dict()})
        b = await daemon.handle_request({'op': 'submit', 'job': _spec_for(w1, 'b:1:x').to_dict()})
        c = await daemon.handle_request({'op': 'submit', 'job': _spec_for(w2, 'c:1:x').to_dict()})
        await asyncio.sleep(0)
        gate.set()
        await asyncio.gather(*list(daemon._tasks.values()), return_exceptions=True)
        return a, b, c

    a, b, c = asyncio.run(_drive())

    assert a['queued_behind'] == '', 'nothing was running when A was submitted'
    assert b['queued_behind'] == a['job_id'], 'B waits on A, of its own directory'
    assert c['queued_behind'] == '', 'W2 belongs to another directory'


def test_submit_reports_an_empty_queued_behind_when_no_job_runs(home, tmp_path, monkeypatch):
    """The no-other-job edge: nothing to wait on, so the field is empty."""
    _accept_every_submit(monkeypatch)

    async def _drive():
        gate = asyncio.Event()
        _gated_run_job(monkeypatch, gate)
        daemon = marshalld.Daemon(
            scheduler=Scheduler(max_slots=1), journal=Journal(), log_dir=tmp_path / 'job-logs'
        )
        response = await daemon.handle_request({'op': 'submit', 'job': _spec_for(tmp_path / 'W1', 'a:1:x').to_dict()})
        gate.set()
        await asyncio.gather(*list(daemon._tasks.values()), return_exceptions=True)
        return response

    response = asyncio.run(_drive())

    assert response['queued_behind'] == ''


def test_wait_for_a_queued_job_reports_queued_waiting_on_and_queued_seconds(home, tmp_path, monkeypatch):
    """A job not yet admitted is ``queued``, names what it waits on, and says
    how long it has waited — never ``running`` with ``elapsed`` 0."""
    _accept_every_submit(monkeypatch)

    async def _drive():
        gate = asyncio.Event()
        _gated_run_job(monkeypatch, gate)
        daemon = marshalld.Daemon(
            scheduler=Scheduler(max_slots=2), journal=Journal(), log_dir=tmp_path / 'job-logs'
        )
        w1 = tmp_path / 'W1'
        a = await daemon.handle_request({'op': 'submit', 'job': _spec_for(w1, 'a:1:x').to_dict()})
        b = await daemon.handle_request({'op': 'submit', 'job': _spec_for(w1, 'b:1:x').to_dict()})
        await asyncio.sleep(0)
        waited = await daemon.handle_request({'op': 'wait', 'job_id': b['job_id'], 'bound': 0})
        gate.set()
        await asyncio.gather(*list(daemon._tasks.values()), return_exceptions=True)
        return a, waited

    a, waited = asyncio.run(_drive())

    assert waited['status'] == 'queued'
    assert waited['job_id']
    assert waited['waiting_on'] == a['job_id'], 'one job ahead, named by its id'
    assert isinstance(waited['queued_seconds'], int) and waited['queued_seconds'] >= 0


def test_terminal_result_carries_the_queued_seconds_it_waited(home, tmp_path, monkeypatch):
    """The wait a build paid survives onto its terminal result."""
    _accept_every_submit(monkeypatch)

    async def _drive():
        gate = asyncio.Event()
        _gated_run_job(monkeypatch, gate)
        daemon = marshalld.Daemon(
            scheduler=Scheduler(max_slots=2), journal=Journal(), log_dir=tmp_path / 'job-logs'
        )
        w1 = tmp_path / 'W1'
        await daemon.handle_request({'op': 'submit', 'job': _spec_for(w1, 'a:1:x').to_dict()})
        b = await daemon.handle_request({'op': 'submit', 'job': _spec_for(w1, 'b:1:x').to_dict()})
        await asyncio.sleep(0)
        gate.set()
        for _ in range(100):
            await asyncio.sleep(0)
            entry = daemon._journal.get(b['job_id'])
            if entry is not None and entry.get('result'):
                return entry['result']
        raise AssertionError('B never reached a terminal result')  # pragma: no cover

    result = asyncio.run(_drive())

    assert result['status'] == 'success'
    assert 'queued_seconds' in result
    assert int(result['queued_seconds']) >= 0


def test_client_passes_the_queue_fields_through(home, monkeypatch):
    """The client-facing TOON carries ``queued`` / ``waiting_on`` / ``queued_seconds``.

    The passthrough is a WHITELIST (``_PASSTHROUGH_STATUS_FIELDS``), so a new
    daemon field that is not listed is silently dropped on the way to the caller.
    """
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {'status': 'queued', 'job_id': 'J', 'waiting_on': 'JOB-A', 'queued_seconds': 4},
    )

    result = client.run_wait(_WAIT_ARGS)

    assert result['job_status'] == 'queued'
    assert result['waiting_on'] == 'JOB-A'
    assert result['queued_seconds'] == 4
