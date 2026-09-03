#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Acceptance: a second / rebuilt session re-attaches via the ledger job_id.

submit persists the daemon-assigned job_id to the change-ledger (kind=job); a
later wait with NO --job-id recovers it from the ledger, so a session that lost
its in-memory job_id (a rebuilt context, a reaped wait) re-attaches to the same
running build from plan state alone.
"""

from __future__ import annotations

import json
from pathlib import Path

import _ledger_core as ledger_core
import pytest
from _build_server_protocol import STATUS_QUEUED

from conftest import load_script_module, parse_ns

_BUNDLE = 'plan-marshall'
_SKILL = 'build-server-client'
_SCRIPT = 'build_server.py'

client = load_script_module(_BUNDLE, _SKILL, _SCRIPT)

#: The two command lines this acceptance drives, parsed by ``build_server.py``'s
#: OWN parser and hoisted to module scope because ``parse_ns`` re-executes the
#: script module on every call. Both carry only fixed values, so no per-test
#: derivation is needed: the submit half names the tree it targets, and the wait
#: half deliberately omits ``--job-id`` — the parser's ``None`` for it is the very
#: input that forces the ledger re-attach this test is about. ``register=False``
#: so neither publishes a second ``build_server`` in ``sys.modules``.
_SUBMIT_ARGS = parse_ns(
    _BUNDLE, _SKILL, _SCRIPT, 'submit',
    '--command', json.dumps(['python3', '/tree/.plan/execute-script.py', 'nt:sk:s', 'run']),
    '--exec-path', '/tree',
    '--project-path', '/tree',
    '--plan-id', 'plan-x',
    register=False,
)
_WAIT_ARGS = parse_ns(
    _BUNDLE, _SKILL, _SCRIPT, 'wait',
    '--plan-id', 'plan-x',
    '--bound', '1',
    register=False,
)


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
    submit = client.run_submit(_SUBMIT_ARGS)
    assert submit['status'] == 'success'
    assert submit['job_id'] == 'JOB-77'

    # Second / rebuilt "session": wait with NO --job-id re-attaches via the ledger.
    seen = {}

    def _capture(req, timeout):
        seen['job_id'] = req.get('job_id')
        return {'status': 'success', 'job_status': 'success', 'duration_seconds': 1, 'log_file': 'l'}

    monkeypatch.setattr(client, '_call_daemon', _capture)
    waited = client.run_wait(_WAIT_ARGS)

    assert seen['job_id'] == 'JOB-77'  # recovered from the ledger, not passed in
    assert waited['job_status'] == 'success'
