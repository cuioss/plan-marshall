#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The re-freeze authorization reads, checks and commits under one snapshot guard.

``authorize_change`` used to read the snapshot and check it for tampering before
taking the plan-scoped snapshot guard, then commit from that stale copy — so a
re-freeze landing in the window was reverted. It also wrote its decision-log line
before the commit, so a ``snapshot_busy`` refusal left a log line for an
authorization that never happened. These tests drive the real code path over a
sandboxed plan directory.

The concurrent tests use a bounded wait so the same test exercises both the
correct interleaving (reads serialized under the guard) and the defective one
(reads before the guard) without depending on wall-clock luck.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import _criteria_snapshot as _snap
import _locks_core
import plan_logging

PLAN_ID = 'lb77-authorize-guard-d2'
FROZEN = ['parser rejects garbage', 'parser accepts input']


def _outline(criteria: list[str]) -> str:
    body = '\n'.join(f'- {text}' for text in criteria)
    return (
        '# Solution: authorize under one guard\n\n## Deliverables\n\n### 1. Authorize it\n\n'
        '**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        f'**Success Criteria:**\n{body}\n'
    )


def _plan(plan_context: Any, criteria: list[str] | None = None) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    status = {'title': 'fixture', 'phases': [], 'current_phase': '3-outline', 'metadata': {'use_worktree': False}}
    (plan_dir / 'status.json').write_text(json.dumps(status), encoding='utf-8')
    (plan_dir / 'solution_outline.md').write_text(_outline(criteria or FROZEN), encoding='utf-8')
    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'
    return plan_dir


def _snapshot_file(plan_dir: Path) -> Path:
    return plan_dir / 'work' / 'criteria-snapshot.json'


def test_a_refreeze_landing_before_the_guard_is_not_reverted(plan_context, monkeypatch) -> None:
    """A re-freeze that commits while the authorization waits is never undone.

    The hook fires in the authorization's own read: with the read under the guard
    the re-freeze is refused (``snapshot_busy``); with the read before the guard
    it commits and the stale copy must not overwrite it.
    """
    plan_dir = _plan(plan_context, ['the old criterion'])
    monkeypatch.setattr(_locks_core, '_GUARD_TIMEOUT_SECONDS', 0.2)
    real_read = _snap.read_snapshot
    fired = threading.Event()
    refreeze: dict[str, Any] = {}

    def _read_then_refreeze(plan_id: str) -> dict[str, Any] | None:
        snapshot = real_read(plan_id)
        if not fired.is_set():
            fired.set()
            assert _snap.authorize_refreeze(plan_id, 'operator: approve the refined criteria')['status'] == 'success'
            (plan_dir / 'solution_outline.md').write_text(_outline(['the new criterion']), encoding='utf-8')
            refreeze.update(_snap.write_snapshot(plan_id))
        return snapshot

    monkeypatch.setattr(_snap, 'read_snapshot', _read_then_refreeze)

    result = _snap.authorize_change(PLAN_ID, 1, 'the old criterion', 'operator: approve the wording')

    assert result['status'] == 'success', result
    if refreeze.get('status') == 'success':
        stored = json.loads(_snapshot_file(plan_dir).read_text(encoding='utf-8'))
        assert stored['deliverables'][0]['criteria'] == ['the new criterion'], stored['deliverables'][0]
        assert _snap.snapshot_state(PLAN_ID) == 'frozen'
    else:
        assert refreeze.get('error') == 'snapshot_busy', refreeze


def test_two_concurrent_authorizations_both_keep_their_entry(plan_context, monkeypatch) -> None:
    """Both calls leave an ``authorized_changes`` entry, not just the later one.

    The barrier sits on the decision log, so both calls reach it before either
    commits when the read is outside the guard — which is the defect. Under the
    guard the second call cannot reach it until the first has committed, and the
    barrier's timeout releases the first.
    """
    plan_dir = _plan(plan_context)
    barrier = threading.Barrier(2, timeout=2.0)
    real_log = plan_logging.log_decision

    def _rendezvous_log(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            barrier.wait()
        except threading.BrokenBarrierError:
            pass
        return real_log(*args, **kwargs)

    monkeypatch.setattr(plan_logging, 'log_decision', _rendezvous_log)
    results: list[dict[str, Any]] = []

    def _authorize(criterion: str) -> None:
        results.append(_snap.authorize_change(PLAN_ID, 1, criterion, 'operator: approve the wording'))

    threads = [threading.Thread(target=_authorize, args=(criterion,)) for criterion in FROZEN]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)

    assert [result['status'] for result in results] == ['success', 'success'], results
    stored = json.loads(_snapshot_file(plan_dir).read_text(encoding='utf-8'))
    assert sorted(entry['criterion'] for entry in stored['authorized_changes']) == sorted(FROZEN)


def test_a_snapshot_busy_refusal_writes_no_decision_log_line(plan_context, monkeypatch) -> None:
    plan_dir = _plan(plan_context)
    monkeypatch.setattr(_locks_core, '_GUARD_TIMEOUT_SECONDS', 0.1)
    logged: list[str] = []

    def _record_log(*args: Any, **kwargs: Any) -> dict[str, Any]:
        logged.append(str(args))
        return {'status': 'success'}

    monkeypatch.setattr(plan_logging, 'log_decision', _record_log)

    with _snap._snapshot_guard(PLAN_ID):
        result = _snap.authorize_change(PLAN_ID, 1, FROZEN[0], 'operator: approve the wording')

    assert result['status'] == 'error', result
    assert result['error'] == 'snapshot_busy'
    assert logged == []
    snapshot = _snap.read_snapshot(PLAN_ID)
    assert snapshot is not None
    assert snapshot['authorized_changes'] == []
    assert _snapshot_file(plan_dir).is_file()


def test_a_failed_decision_log_rolls_the_authorization_back(plan_context, monkeypatch) -> None:
    """A committed authorization is withdrawn when its line cannot be written."""
    plan_dir = _plan(plan_context)
    before = _snapshot_file(plan_dir).read_bytes()
    monkeypatch.setattr(plan_logging, 'log_decision', lambda *args, **kwargs: {'status': 'error', 'error': 'injected'})

    result = _snap.authorize_change(PLAN_ID, 1, FROZEN[0], 'operator: approve the wording')

    assert result['status'] == 'error', result
    assert result['error'] == 'decision_log_unavailable'
    assert 'rolled back' in result['message']
    assert _snapshot_file(plan_dir).read_bytes() == before
    assert _snap.snapshot_state(PLAN_ID) == 'frozen'


def test_a_raising_decision_log_withdraws_the_refreeze_authorization(plan_context, monkeypatch) -> None:
    """A log call that raises is a failed log, and the authorization is withdrawn."""
    _plan(plan_context)

    def _raise(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError('injected log failure')

    monkeypatch.setattr(plan_logging, 'log_decision', _raise)

    result = _snap.authorize_refreeze(PLAN_ID, 'operator: approve the refined criteria')

    assert result['status'] == 'error', result
    assert result['error'] == 'decision_log_unavailable'
    assert 'withdrawn' in result['message']
    assert 'refreeze_authorized' not in _snap.integrity_record(PLAN_ID)
