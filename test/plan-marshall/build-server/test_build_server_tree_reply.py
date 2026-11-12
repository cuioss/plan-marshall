#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A build-server submit and its wait name the tree they built.

A green result says nothing about WHICH tree it is green for unless the reply
names it, and the daemon's status payload carries only the job's outcome. So both
replies carry the three fields a caller compares with the tree it meant —
``exec_path``, ``project_path`` and ``plan_id`` (the ``NO_PLAN`` sentinel STATED,
never blank) — and a plan-less submission, which has no plan-scoped work log,
writes its queued line to the GLOBAL work log with the plan-less identity in the
message.

The daemon-facing seams (``_handshake`` / ``_call_daemon``) are monkeypatched so
no socket is opened, and the change-ledger is isolated at a per-test path.
"""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import Any

import _ledger_core as ledger_core
import pytest
from _resolve_project_dir_fixtures import NO_PLAN_SENTINEL

from conftest import load_script_module, parse_ns

_BUNDLE = 'plan-marshall'
_SKILL = 'build-server-client'
_SCRIPT = 'build_server.py'

#: ``register=False`` because only the returned module is used here — the
#: ``captured_logs`` fixture patches through this object, never through a dotted
#: string.
client = load_script_module(_BUNDLE, _SKILL, _SCRIPT, register=False)


def _verb_args(*argv: str) -> argparse.Namespace:
    """The namespace ``build_server.py``'s OWN parser yields for ``argv``."""
    args: argparse.Namespace = parse_ns(_BUNDLE, _SKILL, _SCRIPT, *argv, register=False)
    return args


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from a parser-derived base, overriding named fields."""
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


_SUBMIT_ARGS = _verb_args('submit', '--command', '[]')
_WAIT_ARGS = _verb_args('wait')


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """Point the machine-global home root at an isolated tmp dir."""
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return Path(tmp_path)


@pytest.fixture
def ledger(tmp_path, monkeypatch) -> Path:
    """Isolate the change-ledger at a per-test path (never the real ledger)."""
    ledger_path = Path(tmp_path) / 'change-ledger.jsonl'
    monkeypatch.setattr(ledger_core, 'resolve_ledger_path', lambda: ledger_path)
    monkeypatch.setattr(client, 'compute_worktree_sha', lambda _path: 'test-sha')
    return ledger_path


@pytest.fixture
def captured_logs(monkeypatch) -> list[tuple[str, str | None, str, str]]:
    """Capture every ``plan_logging.log_entry`` call the client makes."""
    calls: list[tuple[str, str | None, str, str]] = []
    monkeypatch.setattr(
        client,
        'log_entry',
        lambda log_type, plan_id, level, message: calls.append((log_type, plan_id, level, message)),
    )
    return calls


def _submit_args(project_path: str, plan_id: str | None = 'p1') -> argparse.Namespace:
    command = f'["python3", "{project_path}/.plan/execute-script.py", "a:b:c", "run"]'
    return _variant(
        _SUBMIT_ARGS,
        command=command,
        exec_path=project_path,
        project_path=project_path,
        plan_id=plan_id,
    )


def _queue(monkeypatch, *, job_id: str = 'JOB-1') -> None:
    """Pin a successful submit round-trip for ``job_id``."""
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {'status': 'queued', 'job_id': job_id, 'attached': False},
    )


def _finish(monkeypatch, *, job_id: str = 'JOB-1') -> None:
    """Pin a terminal daemon result for ``job_id``."""
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {'status': 'success', 'job_id': job_id, 'exit_code': 0},
    )


def _job_rows() -> list[dict]:
    return [entry for entry in ledger_core.read_entries() if entry.get('kind') == ledger_core.KIND_JOB]


# =============================================================================
# The reply fields
# =============================================================================


def test_the_submit_reply_names_the_tree_it_builds(home, ledger, monkeypatch) -> None:
    """A green result is a fact about THIS tree, so the reply states which."""
    root = str(home / 'proj')
    _queue(monkeypatch)

    result = client.run_submit(_submit_args(root))

    assert result['exec_path'] == root
    assert result['project_path'] == root
    assert result['plan_id'] == 'p1'


def test_a_plan_less_submit_reply_states_the_sentinel(home, ledger, monkeypatch) -> None:
    """``NO_PLAN`` is STATED, never blank — the sentinel is the answer, not an absence."""
    root = str(home / 'proj')
    _queue(monkeypatch, job_id='JOB-NP')

    result = client.run_submit(_submit_args(root, plan_id=None))

    assert result['plan_id'] == NO_PLAN_SENTINEL
    assert result['project_path'] == root


def test_the_job_row_records_the_tree_the_job_builds(home, ledger, monkeypatch) -> None:
    """The wait reply has no argv of its own, so the row is where the tree lives."""
    root = str(home / 'proj')
    _queue(monkeypatch)

    client.run_submit(_submit_args(root))

    row = _job_rows()[0]
    assert row['exec_path'] == root
    assert row['project_path'] == root


def test_the_wait_reply_carries_the_tree_the_submit_named(home, ledger, monkeypatch) -> None:
    """The wait names the same tree as the submit, from the job record it reads."""
    root = str(home / 'proj')
    _queue(monkeypatch)
    submitted = client.run_submit(_submit_args(root))

    _finish(monkeypatch)
    result = client.run_wait(_variant(_WAIT_ARGS, job_id=None, plan_id='p1', bound=1))

    assert result['exec_path'] == submitted['exec_path']
    assert result['project_path'] == submitted['project_path']
    assert result['plan_id'] == submitted['plan_id']


def test_a_plan_less_wait_reply_states_the_sentinel(home, ledger, monkeypatch) -> None:
    """The plan-less round trip states ``NO_PLAN`` on both replies."""
    root = str(home / 'proj')
    _queue(monkeypatch, job_id='JOB-NP')
    client.run_submit(_submit_args(root, plan_id=None))

    _finish(monkeypatch, job_id='JOB-NP')
    result = client.run_wait(_variant(_WAIT_ARGS, job_id=None, plan_id=None, bound=1))

    assert result['plan_id'] == NO_PLAN_SENTINEL
    assert result['project_path'] == root


def test_a_wait_for_a_row_that_names_no_tree_reports_no_tree(home, ledger, monkeypatch) -> None:
    """CONTROL: a row written before the fields existed yields absence, not a guess."""
    ledger_core.append_entry(
        ledger_core.job_record(
            job_id='JOB-OLD',
            plan_id='p1',
            fingerprint='fp',
            notation='a:b:c',
            worktree_sha='test-sha',
        )
    )
    _finish(monkeypatch, job_id='JOB-OLD')

    result = client.run_wait(_variant(_WAIT_ARGS, job_id=None, plan_id='p1', bound=1))

    assert 'exec_path' not in result
    assert 'project_path' not in result
    assert result['plan_id'] == 'p1', 'the plan id the ROW states is still reported'


# =============================================================================
# The plan-less work log
# =============================================================================


def test_plan_less_submit_writes_the_global_work_log_as_plan_less(home, ledger, captured_logs, monkeypatch) -> None:
    """A plan-less submission is NOT silent: it lands in the GLOBAL work log.

    ``_audit_log`` still no-ops for the sentinel — there is no plan-scoped work
    log to write to — so the plan-less identity travels in the MESSAGE (a log
    path cannot carry it) and the target is the global fallback. Without this a
    green result for the main checkout left no trace at all beside the plans' own
    builds in the same journal.
    """
    root = str(home / 'proj')
    _queue(monkeypatch, job_id='JOB-NP')

    client.run_submit(_submit_args(root, plan_id=None))

    assert captured_logs, 'a plan-less submit must leave a trace'
    assert all(plan_id is None for _t, plan_id, _l, _m in captured_logs), (
        f'a plan-less submit wrote to a plan-scoped log: {captured_logs!r}'
    )
    log_type, _p, level, message = captured_logs[-1]
    assert log_type == 'work', 'the plan-less trace belongs to the work log, not the script or decision log'
    assert level == 'INFO'
    assert 'JOB-NP' in message
    assert f'plan={NO_PLAN_SENTINEL}' in message, 'the global log line must state the plan-less identity'
    assert root not in message, 'the global work log must not carry the project path'


def test_an_empty_plan_id_traces_the_same_way(home, ledger, captured_logs, monkeypatch) -> None:
    """The empty-string plan id resolves to the same plan-less trace."""
    _queue(monkeypatch)

    client.run_submit(_submit_args(str(home / 'proj'), plan_id=''))

    assert captured_logs, 'a plan-less submit must leave a trace'
    assert f'plan={NO_PLAN_SENTINEL}' in captured_logs[-1][3]


def test_a_plan_less_degraded_submit_is_traced_too(home, ledger, captured_logs, monkeypatch) -> None:
    """Every plan-less outcome is traced, not only the queued acceptance.

    The routing sits in `_audit_log`, so a fallback or a refusal cannot slip past
    it — which is what "plan-less builds are traced, not silent" claims.
    """
    monkeypatch.setattr(client, '_handshake', lambda _p: (None, client.REASON_IMPOSTOR_SOCKET))

    client.run_submit(_submit_args(str(home / 'proj'), plan_id=None))

    assert captured_logs, 'a plan-less degraded submit must leave a trace'
    assert all(plan_id is None for _t, plan_id, _l, _m in captured_logs), captured_logs
    warnings = [entry for entry in captured_logs if entry[2] == 'WARNING']
    assert warnings, 'the degraded fallback must be recorded at WARNING'
    assert f'plan={NO_PLAN_SENTINEL}' in warnings[-1][3]
    assert client.REASON_IMPOSTOR_SOCKET in warnings[-1][3]


def test_a_plan_scoped_submit_writes_no_global_line(home, ledger, captured_logs, monkeypatch) -> None:
    """CONTROL: the global line is the plan-less route only."""
    _queue(monkeypatch)

    client.run_submit(_submit_args(str(home / 'proj')))

    assert captured_logs, 'a plan-scoped submit still logs'
    assert all(plan_id == 'p1' for _t, plan_id, _l, _m in captured_logs), captured_logs
