#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""E2E: one job_id ties the client work log, the server interaction audit, and the ledger.

A submit-then-wait interaction is driven through an env-isolated daemon — the
client's daemon call is monkeypatched to delegate straight into
``Daemon.handle_request``, so the SINGLE daemon-assigned ``job_id`` flows through
all three vantage points naturally. The test then asserts that same ``job_id``
appears in:

* the client's captured work-log entry (the ``plan_logging.log_entry`` seam);
* the server ``interaction-audit.log`` record; and
* the change-ledger ``kind=job`` row.

It also asserts the fallback/refusal path is non-silent (a captured client
WARNING) and that no secret-bearing field (the raw command argv, the interpreter
path) appears in any of the three stores.

The daemon runs with ``max_slots=0`` so the submitted job stays ``queued`` and no
real build subprocess is ever spawned; the verifier seam is stubbed to accept
(real positional verification is covered by the security-refusal acceptance
tests, not this correlation test).
"""

from __future__ import annotations

import asyncio
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest
from conftest import get_script_path

_DAEMON_DIR = get_script_path('plan-marshall', 'manage-build-server', 'marshalld.py').parent
_CLIENT_DIR = get_script_path('plan-marshall', 'build-server-client', 'build_server.py').parent
for _d in (_DAEMON_DIR, _CLIENT_DIR):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

import _ledger_core as ledger_core  # noqa: E402
import _marshalld_audit as audit_mod  # noqa: E402
import build_server as client  # noqa: E402
import marshalld  # noqa: E402
from _marshalld_journal import Journal  # noqa: E402
from _marshalld_scheduler import Scheduler  # noqa: E402


class _Accepted:
    """A verifier outcome stub that accepts every submit.

    Real positional verification (interpreter / exec path / notation allowlist /
    worktree liveness) is exercised by the security-refusal acceptance tests;
    this correlation test only needs a job_id to flow, so it stubs acceptance.
    """

    accepted = True
    reason = ''
    record = {'canonical_root': 'root'}  # noqa: RUF012 — a test stub, not shared state


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """Point the machine-global home root at an isolated tmp dir."""
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return Path(tmp_path)


@pytest.fixture
def ledger(tmp_path, monkeypatch) -> Path:
    """Isolate the change-ledger at a per-test path and stub the worktree-sha shell-out."""
    ledger_path = Path(tmp_path) / 'change-ledger.jsonl'
    monkeypatch.setattr(ledger_core, 'resolve_ledger_path', lambda: ledger_path)
    monkeypatch.setattr(client, 'compute_worktree_sha', lambda _path: 'test-sha')
    return ledger_path


@pytest.fixture
def captured_logs(monkeypatch) -> list[tuple[str, str, str, str]]:
    """Capture every ``plan_logging.log_entry`` call the client makes."""
    calls: list[tuple[str, str, str, str]] = []
    monkeypatch.setattr(
        client,
        'log_entry',
        lambda log_type, plan_id, level, message: calls.append((log_type, plan_id, level, message)),
    )
    return calls


def _job_rows() -> list[dict]:
    return [entry for entry in ledger_core.read_entries() if entry.get('kind') == ledger_core.KIND_JOB]


def _submit_args(tmp_path) -> Namespace:
    command = json.dumps(
        [sys.executable, str(tmp_path / '.plan' / 'execute-script.py'), 'a:b:c', 'run']
    )
    return Namespace(
        command=command,
        exec_path=str(tmp_path),
        project_path=str(tmp_path),
        plan_id='p1',
    )


def _wire_client_to_daemon(daemon, monkeypatch) -> None:
    """Route the client's daemon call straight into the daemon dispatch."""
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda request, timeout: asyncio.run(daemon.handle_request(request)),
    )


def _isolated_daemon(tmp_path, audit) -> marshalld.Daemon:
    return marshalld.Daemon(
        scheduler=Scheduler(max_slots=0),  # keep the job queued — no real subprocess
        journal=Journal(),
        interaction_audit=audit,
        log_dir=tmp_path / 'job-logs',
    )


def test_one_job_id_correlates_all_three_stores(home, ledger, captured_logs, tmp_path, monkeypatch):
    audit = audit_mod.InteractionAudit()
    daemon = _isolated_daemon(tmp_path, audit)
    monkeypatch.setattr(marshalld, 'verify_submit', lambda *a, **k: _Accepted())
    _wire_client_to_daemon(daemon, monkeypatch)

    submit_result = client.run_submit(_submit_args(tmp_path))
    assert submit_result['status'] == 'success'
    job_id = submit_result['job_id']
    assert job_id

    client.run_wait(Namespace(job_id=job_id, plan_id='p1', bound=0))

    # Vantage 1 — the client work log carries the job_id.
    client_messages = [message for _t, _p, _l, message in captured_logs]
    assert any(job_id in message for message in client_messages)

    # Vantage 2 — the server interaction-audit records carry the job_id.
    audit_job_ids = {record['job_id'] for record in audit.read_all()}
    assert job_id in audit_job_ids

    # Vantage 3 — the change-ledger kind=job row carries the SAME job_id.
    rows = _job_rows()
    assert len(rows) == 1
    assert rows[0]['job_id'] == job_id


def test_fallback_path_is_non_silent(home, ledger, captured_logs, tmp_path, monkeypatch):
    # A degraded (fallback) submit must still produce a captured client WARNING —
    # the exact defect class this feature closes.
    monkeypatch.setattr(client, '_handshake', lambda _p: (None, client.REASON_SOCKET_ABSENT))

    result = client.run_submit(_submit_args(tmp_path))

    assert result['status'] == 'degraded'
    assert any(level == 'WARNING' for _t, _p, level, _m in captured_logs)


def test_no_secret_field_in_any_correlated_store(home, ledger, captured_logs, tmp_path, monkeypatch):
    audit = audit_mod.InteractionAudit()
    daemon = _isolated_daemon(tmp_path, audit)
    monkeypatch.setattr(marshalld, 'verify_submit', lambda *a, **k: _Accepted())
    _wire_client_to_daemon(daemon, monkeypatch)

    client.run_submit(_submit_args(tmp_path))

    executor_path = str(tmp_path / '.plan' / 'execute-script.py')

    # Client work log — no raw argv token.
    for _t, _p, _l, message in captured_logs:
        assert executor_path not in message
        assert sys.executable not in message

    # Server interaction audit — fixed schema, no command/env.
    for record in audit.read_all():
        blob = json.dumps(record)
        assert executor_path not in blob
        assert sys.executable not in blob
        assert 'command' not in record

    # Change ledger kind=job row — no raw argv.
    for row in _job_rows():
        blob = json.dumps(row)
        assert executor_path not in blob
        assert sys.executable not in blob
        assert 'command' not in row
