#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Acceptance: a second / rebuilt session re-attaches via the ledger job_id.

submit persists the daemon-assigned job_id to the change-ledger (kind=job); a
later wait with NO --job-id recovers it from the ledger, so a session that lost
its in-memory job_id (a rebuilt context, a reaped wait) re-attaches to the same
running build from plan state alone.
"""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest
from conftest import get_script_path

_CLIENT_DIR = get_script_path('plan-marshall', 'build-server-client', 'build_server.py').parent
if str(_CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(_CLIENT_DIR))

import _ledger_core as ledger_core  # noqa: E402
import build_server as client  # noqa: E402
from _build_server_protocol import STATUS_QUEUED  # noqa: E402


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    ledger_path = Path(tmp_path) / 'change-ledger.jsonl'
    monkeypatch.setattr(ledger_core, 'resolve_ledger_path', lambda: ledger_path)
    monkeypatch.setattr(client, 'compute_worktree_sha', lambda _p: 'test-sha')
    return tmp_path


def test_wait_reattaches_via_the_ledger_job_id(isolated, monkeypatch):
    # First "session": submit records the daemon job_id to the ledger.
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client, '_call_daemon',
        lambda _req, timeout: {'status': STATUS_QUEUED, 'job_id': 'JOB-77', 'attached': False},
    )
    submit = client.run_submit(
        Namespace(
            command=json.dumps(['python3', '/tree/.plan/execute-script.py', 'nt:sk:s', 'run']),
            exec_path='/tree', project_path='/tree', plan_id='plan-x',
        )
    )
    assert submit['status'] == 'success'
    assert submit['job_id'] == 'JOB-77'

    # Second / rebuilt "session": wait with NO --job-id re-attaches via the ledger.
    seen = {}

    def _capture(req, timeout):
        seen['job_id'] = req.get('job_id')
        return {'status': 'success', 'job_status': 'success', 'duration_seconds': 1, 'log_file': 'l'}

    monkeypatch.setattr(client, '_call_daemon', _capture)
    waited = client.run_wait(Namespace(job_id=None, plan_id='plan-x', bound=1))

    assert seen['job_id'] == 'JOB-77'  # recovered from the ledger, not passed in
    assert waited['job_status'] == 'success'
