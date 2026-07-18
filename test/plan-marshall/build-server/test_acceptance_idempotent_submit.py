#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Acceptance: identical concurrent submits attach to one job.

The scheduler keys on the idempotent-submit fingerprint (plan_id + command +
tree): a second identical submit ATTACHES to the in-flight job and returns its
id instead of double-running the build. Verified at the scheduler level and
end-to-end through the daemon's submit dispatch over a verified registration.
"""

from __future__ import annotations

import asyncio
import sys

import pytest
from conftest import get_script_path

_DAEMON_DIR = get_script_path('plan-marshall', 'manage-build-server', 'marshalld.py').parent
if str(_DAEMON_DIR) not in sys.path:
    sys.path.insert(0, str(_DAEMON_DIR))

import marshalld  # noqa: E402
from _build_server_protocol import STATUS_QUEUED, JobSpec, make_job_spec  # noqa: E402
from _build_server_registry import canonicalize_root, register_project  # noqa: E402
from _marshalld_journal import Journal  # noqa: E402
from _marshalld_scheduler import Scheduler  # noqa: E402

_NOTATION = 'plan-marshall:build-pyproject:pyproject_build'


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return tmp_path


def test_scheduler_attaches_an_identical_submit():
    scheduler = Scheduler(max_slots=2)
    spec = JobSpec(command=['python3', 'x'], exec_path='/t', project_path='/t', plan_id='p', fingerprint='FP')

    first = scheduler.submit(spec, 'root')
    second = scheduler.submit(spec, 'root')

    assert first.attached is False
    assert second.attached is True
    assert second.job_id == first.job_id  # attached to the same in-flight job
    assert scheduler.queued_count == 1  # only ONE job enqueued


def test_daemon_submit_attaches_identical_concurrent_submits(home, tmp_path):
    root = tmp_path / 'proj'
    (root / '.plan').mkdir(parents=True)
    (root / '.plan' / 'execute-script.py').write_text('print("ok")')
    canonical = canonicalize_root(root)
    register_project(canonical, notation_allowlist=[_NOTATION])

    spec = make_job_spec(
        command=[sys.executable, str(root / '.plan' / 'execute-script.py'), _NOTATION, 'run'],
        exec_path=canonical, project_path=canonical, plan_id='p',
    )

    async def _drive():
        daemon = marshalld.Daemon(
            scheduler=Scheduler(max_slots=2), journal=Journal(), log_dir=tmp_path / 'job-logs',
        )
        first = await daemon.handle_request({'op': 'submit', 'job': spec.to_dict()})
        second = await daemon.handle_request({'op': 'submit', 'job': spec.to_dict()})
        await asyncio.gather(*list(daemon._tasks.values()), return_exceptions=True)
        return first, second

    first, second = asyncio.run(_drive())

    assert first['status'] == STATUS_QUEUED
    assert second['status'] == STATUS_QUEUED
    assert second['attached'] is True
    assert second['job_id'] == first['job_id']
