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
    'plan-marshall', 'build-server-client', 'build_server.py',
    register=False,
)

#: The one ``wait`` command line this module drives, parsed by ``build_server.py``'s
#: OWN parser. Every value is fixed, so no per-test derivation is needed. Hoisted
#: because ``parse_ns`` re-executes the script module on every call, and
#: ``register=False`` for the same reason the loader above passes it.
_WAIT_ARGS = parse_ns(
    'plan-marshall', 'build-server-client', 'build_server.py',
    'wait', '--job-id', 'J', '--plan-id', '', '--bound', '1',
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
            exec_path=str(tmp_path), project_path=str(tmp_path),
            plan_id='p', fingerprint='fp',
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
        client, '_call_daemon',
        lambda _req, timeout: {'status': STATUS_KILLED, 'job_id': 'J', 'exit_code': -9},
    )

    result = client.run_wait(_WAIT_ARGS)

    assert result['job_status'] == STATUS_KILLED
    assert 'do not blind-retry' in result['message']
