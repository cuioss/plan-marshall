#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D1: the daemon's ping handshake carries the scheduler's in-flight / queued counts.

The reconcile reads daemon idleness from the daemon's OWN scheduler count rather
than inferring it — so the ping response must expose ``in_flight`` (running jobs)
and ``queued`` (admitted-but-not-yet-running jobs). Adding these to ping stays
backward-compatible: the client handshake reads only ``status`` and ``version``.
"""

from __future__ import annotations

import asyncio

# PLAIN import, deliberately: the build-server suites annotate against
# ``marshalld.Daemon``, and only a plain import gives mypy the real module — the
# shared loader returns ``Any``, which turns every such annotation into an
# undefined name. The name is bound the same way in every suite, so no loaded copy
# is ever published beside the plainly-imported one.
import marshalld
import pytest
from _build_server_protocol import JobSpec
from _marshalld_journal import Journal
from _marshalld_scheduler import Scheduler


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return tmp_path


def _spec(fingerprint: str) -> JobSpec:
    return JobSpec(
        command=['python3', 'x'], exec_path='/t', project_path='/t',
        plan_id='p', fingerprint=fingerprint,
    )


def test_ping_reports_zero_counts_on_an_idle_daemon(home, tmp_path):
    daemon = marshalld.Daemon(
        scheduler=Scheduler(max_slots=2), journal=Journal(), log_dir=tmp_path / 'job-logs',
    )

    response = asyncio.run(daemon.handle_request({'op': 'ping'}))

    assert response['status'] == 'ok'
    assert response['version'] == marshalld.VERSION
    assert response['in_flight'] == 0
    assert response['queued'] == 0


def test_ping_reflects_running_and_queued_jobs(home, tmp_path):
    # max_slots=1: admit one job (running=1), leave two queued.
    scheduler = Scheduler(max_slots=1)
    scheduler.submit(_spec('FP-A'), 'root')
    scheduler.submit(_spec('FP-B'), 'root')
    scheduler.submit(_spec('FP-C'), 'root')
    admitted = scheduler.admit_next()
    assert admitted is not None  # one slot filled → running_count == 1
    daemon = marshalld.Daemon(scheduler=scheduler, journal=Journal(), log_dir=tmp_path / 'job-logs')

    response = asyncio.run(daemon.handle_request({'op': 'ping'}))

    assert response['in_flight'] == 1
    assert response['queued'] == 2
