#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Acceptance: a submitted job survives a harness reap of the wait.

The wait and the work are separate processes: a bound-expired (reaped) wait
returns a live running snapshot, the build keeps running in the daemon, and
re-issuing wait recovers the FULL terminal result. Drives the real Daemon
in-process over an isolated journal (the verifier is exercised separately in
test_acceptance_security_refusals).
"""

from __future__ import annotations

import asyncio
import sys

# PLAIN import, deliberately: this suite annotates against ``marshalld.Daemon``,
# which only a plain import gives mypy. The name is bound the same way in every
# suite, so no loaded copy is published beside it.
import marshalld
import pytest
from _build_server_protocol import STATUS_RUNNING, JobSpec
from _marshalld_journal import Journal
from _marshalld_scheduler import Scheduler


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return tmp_path


def _submit_direct(daemon: marshalld.Daemon, command: list[str], tree: str) -> str:
    """Enqueue a job directly (bypassing the verifier) and admit it."""
    spec = JobSpec(command=command, exec_path=tree, project_path=tree, plan_id='plan-a', fingerprint='fp-a')
    result = daemon._scheduler.submit(spec, 'root-a')
    daemon._journal.record_spec(result.job_id, spec.to_dict())
    daemon._admit_ready()
    return result.job_id


def test_job_survives_a_reaped_wait(home, tmp_path):
    async def _drive():
        daemon = marshalld.Daemon(
            scheduler=Scheduler(max_slots=2),
            journal=Journal(),
            log_dir=tmp_path / 'job-logs',
        )
        job_id = _submit_direct(
            daemon,
            [sys.executable, '-c', 'import time; time.sleep(0.4); print("built")'],
            str(tmp_path),
        )
        # A reaped / bound-expired wait returns a LIVE running snapshot, not the
        # result — the build is still running in the daemon.
        running = await daemon._wait({'job_id': job_id, 'bound': 0})
        # The job keeps running; let it finish (it did NOT die with the wait).
        await asyncio.gather(*list(daemon._tasks.values()), return_exceptions=True)
        # Re-issuing wait recovers the FULL terminal result — reap survival.
        terminal = await daemon._wait({'job_id': job_id, 'bound': 5})
        return running, terminal

    running, terminal = asyncio.run(_drive())

    assert running['status'] == STATUS_RUNNING
    assert terminal['status'] == 'success'
    assert terminal['exit_code'] == 0
