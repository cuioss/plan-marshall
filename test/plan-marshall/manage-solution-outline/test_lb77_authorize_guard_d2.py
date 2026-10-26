#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The re-freeze authorization reads, checks and commits under one snapshot guard.

``authorize_change`` used to read the snapshot and check it for tampering before
taking the plan-scoped snapshot guard, then commit from that stale copy — so a
re-freeze landing in the window was reverted. It also wrote its decision-log line
before the commit, so a ``snapshot_busy`` refusal left a log line for an
authorization that never happened. These tests drive the real code path over a
sandboxed plan directory.

``authorize_refreeze`` carried only half of that treatment: no snapshot guard, so
a ``write_snapshot`` could consume an authorization whose decision line was never
written, and a withdrawal that could not tell its own authorization from a newer
one. Both halves are exercised here, together with the double-fault direction:
an authorization whose line and whose digest re-record both fail is undone rather
than left standing, and the snapshot is left reading ``tampered`` so it is refused
until repaired.

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

from conftest import get_skill_dir

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


def test_a_refreeze_landing_before_the_guard_is_refused(plan_context, monkeypatch) -> None:
    """A re-freeze started inside another writer's guarded window cannot land.

    Both writers take the same plan-scoped guard, so the nested re-freeze is
    refused ``snapshot_busy`` rather than committing into a window it would then
    have to be reverted out of. The snapshot is left exactly as it was.
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
            refreeze.update(_snap.authorize_refreeze(plan_id, 'operator: approve the refined criteria'))
        return snapshot

    monkeypatch.setattr(_snap, 'read_snapshot', _read_then_refreeze)

    result = _snap.authorize_change(PLAN_ID, 1, 'the old criterion', 'operator: approve the wording')

    assert result['status'] == 'success', result
    assert refreeze.get('error') == 'snapshot_busy', refreeze
    stored = json.loads(_snapshot_file(plan_dir).read_text(encoding='utf-8'))
    assert stored['deliverables'][0]['criteria'] == ['the old criterion'], stored['deliverables'][0]
    assert _snap.snapshot_state(PLAN_ID) == 'frozen'


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


def test_a_write_snapshot_started_inside_the_log_window_consumes_nothing(plan_context, monkeypatch) -> None:
    """A re-freeze that starts in the record-then-log window cannot consume it.

    Both writers take the same plan-scoped snapshot guard, so a ``write_snapshot``
    begun from inside the decision-log window — the widest point of the window —
    is refused ``snapshot_busy`` instead of consuming an authorization whose
    decision line then never lands.
    """
    plan_dir = _plan(plan_context)
    before = _snapshot_file(plan_dir).read_bytes()
    monkeypatch.setattr(_locks_core, '_GUARD_TIMEOUT_SECONDS', 0.2)
    observed: dict[str, Any] = {}

    def _refreeze_then_fail(*args: Any, **kwargs: Any) -> dict[str, Any]:
        observed.update(_snap.write_snapshot(PLAN_ID))
        return {'status': 'error', 'error': 'injected'}

    monkeypatch.setattr(plan_logging, 'log_decision', _refreeze_then_fail)

    result = _snap.authorize_refreeze(PLAN_ID, 'operator: approve the refined criteria')

    assert result['status'] == 'error', result
    assert result['error'] == 'decision_log_unavailable'
    assert observed.get('error') == 'snapshot_busy', observed
    assert _snapshot_file(plan_dir).read_bytes() == before
    assert 'refreeze_authorized' not in _snap.integrity_record(PLAN_ID)


def test_a_newer_authorization_survives_an_older_failed_log(plan_context, monkeypatch) -> None:
    """A withdrawal removes only the authorization its own call set.

    The newer authorization is installed from inside the log call, which is the
    one point where a second writer can be observed between this call's record and
    its withdrawal. Under the identity token the older call leaves it standing and
    says so; without one it would delete the newer authorization along with its
    decision line.
    """

    def _newer_authorization_then_fail(*args: Any, **kwargs: Any) -> dict[str, Any]:
        def _set_newer(block: dict[str, Any]) -> None:
            block['refreeze_authorized'] = True
            block[_snap.REFREEZE_TOKEN_KEY] = 'newer-token'

        assert _snap._merge_integrity(PLAN_ID, _set_newer)
        return {'status': 'error', 'error': 'injected'}

    _plan(plan_context)
    monkeypatch.setattr(plan_logging, 'log_decision', _newer_authorization_then_fail)

    result = _snap.authorize_refreeze(PLAN_ID, 'operator: approve the refined criteria')

    assert result['status'] == 'error', result
    assert 'a newer authorization replaced it' in result['message']
    record = _snap.integrity_record(PLAN_ID)
    assert record['refreeze_authorized'] is True
    assert record[_snap.REFREEZE_TOKEN_KEY] == 'newer-token'


def test_a_failed_log_restores_a_prior_authorization(plan_context, monkeypatch) -> None:
    """A call that found an authorization already recorded puts it back on failure.

    ``restored`` is the state the operator needs: the withdrawal landed, but a
    re-freeze is still authorized, because one was authorized before this call.
    """

    def _prior(block: dict[str, Any]) -> None:
        block['refreeze_authorized'] = True

    _plan(plan_context)
    assert _snap._merge_integrity(PLAN_ID, _prior)
    monkeypatch.setattr(plan_logging, 'log_decision', lambda *args, **kwargs: {'status': 'error', 'error': 'injected'})

    result = _snap.authorize_refreeze(PLAN_ID, 'operator: approve the refined criteria')

    assert result['status'] == 'error', result
    assert 'prior authorization' in result['message']
    assert _snap.integrity_record(PLAN_ID)['refreeze_authorized'] is True


def test_a_withdrawal_that_cannot_be_written_is_reported_as_not_withdrawn(plan_context, monkeypatch) -> None:
    """A failed withdrawal is never reported as one that landed."""
    _plan(plan_context)
    real_merge = _snap._merge_integrity
    calls = {'count': 0}

    def _fail_the_withdrawal(plan_id: str, merge: Any) -> bool:
        calls['count'] += 1
        return real_merge(plan_id, merge) if calls['count'] == 1 else False

    monkeypatch.setattr(_snap, '_merge_integrity', _fail_the_withdrawal)
    monkeypatch.setattr(plan_logging, 'log_decision', lambda *args, **kwargs: {'status': 'error', 'error': 'injected'})

    result = _snap.authorize_refreeze(PLAN_ID, 'operator: approve the refined criteria')

    assert result['status'] == 'error', result
    assert 'NOT withdrawn' in result['message']
    assert _snap.integrity_record(PLAN_ID)['refreeze_authorized'] is True


def test_a_consumed_authorization_reports_already_consumed(plan_context, monkeypatch) -> None:
    """A re-freeze that consumed this call's authorization wins over the failed log.

    The consumption happens inside the log call, where a stale-guard window could
    still let a re-freeze commit; the withdrawal must then report
    ``already_consumed`` instead of restoring a decision the re-freeze already
    spent, and must leave no identity token naming an authorization that no longer
    exists.
    """
    _plan(plan_context)

    def _consume_then_fail(*args: Any, **kwargs: Any) -> dict[str, Any]:
        assert _snap.record_snapshot_digest(PLAN_ID, consume_refreeze=True)
        return {'status': 'error', 'error': 'injected'}

    monkeypatch.setattr(plan_logging, 'log_decision', _consume_then_fail)

    result = _snap.authorize_refreeze(PLAN_ID, 'operator: approve the refined criteria')

    assert result['status'] == 'error', result
    assert 'already consumed' in result['message']
    record = _snap.integrity_record(PLAN_ID)
    assert record['refreeze_authorized'] is False
    assert _snap.REFREEZE_TOKEN_KEY not in record


def test_a_raising_decision_log_rolls_the_change_authorization_back(plan_context, monkeypatch) -> None:
    """The change path treats a raising log like a refused one and rolls back."""
    plan_dir = _plan(plan_context)
    before = _snapshot_file(plan_dir).read_bytes()

    def _raise(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError('injected log failure')

    monkeypatch.setattr(plan_logging, 'log_decision', _raise)

    result = _snap.authorize_change(PLAN_ID, 1, FROZEN[0], 'operator: approve the wording')

    assert result['status'] == 'error', result
    assert result['error'] == 'decision_log_unavailable'
    assert 'injected log failure' in result['message']
    assert 'rolled back' in result['message']
    assert _snapshot_file(plan_dir).read_bytes() == before
    assert _snap.snapshot_state(PLAN_ID) == 'frozen'


def test_a_rollback_does_not_erase_a_newer_commit(plan_context, monkeypatch) -> None:
    """A writer that committed behind the failed one survives the rollback."""
    plan_dir = _plan(plan_context)
    snapshot_file = _snapshot_file(plan_dir)

    def _commit_newer_then_fail(*args: Any, **kwargs: Any) -> dict[str, Any]:
        current = json.loads(snapshot_file.read_text(encoding='utf-8'))
        current['authorized_changes'] = [{'deliverable': 1, 'criterion': 'a newer authorization'}]
        snapshot_file.write_text(json.dumps(current, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        assert _snap.record_snapshot_digest(PLAN_ID)
        return {'status': 'error', 'error': 'injected'}

    monkeypatch.setattr(plan_logging, 'log_decision', _commit_newer_then_fail)

    result = _snap.authorize_change(PLAN_ID, 1, FROZEN[0], 'operator: approve the wording')

    assert result['status'] == 'error', result
    assert 'NOT fully rolled back' in result['message']
    stored = json.loads(snapshot_file.read_text(encoding='utf-8'))
    assert stored['authorized_changes'] == [{'deliverable': 1, 'criterion': 'a newer authorization'}]
    assert _snap.snapshot_state(PLAN_ID) == 'frozen'


def test_a_failed_digest_withdrawal_fails_closed_as_tampered(plan_context, monkeypatch) -> None:
    """The double fault leaves NO standing authorization, at the cost of a tamper flag.

    The edit is undone, so no authorization stands without a decision line. The
    status record still binds the committed bytes' digest, which the undo cannot
    withdraw, so the snapshot reads ``tampered`` and every consumer refuses it
    until the record is repaired. That is the fail-closed direction: the retired
    behaviour re-committed the edit so the record matched its bytes, leaving an
    unlogged authorization usable.
    """
    plan_dir = _plan(plan_context)
    snapshot_file = _snapshot_file(plan_dir)
    before = snapshot_file.read_bytes()
    real_record = _snap.record_snapshot_digest
    calls = {'count': 0}

    def _only_the_first(*args: Any, **kwargs: Any) -> bool:
        calls['count'] += 1
        return real_record(*args, **kwargs) if calls['count'] == 1 else False

    monkeypatch.setattr(_snap, 'record_snapshot_digest', _only_the_first)
    monkeypatch.setattr(plan_logging, 'log_decision', lambda *args, **kwargs: {'status': 'error', 'error': 'injected'})

    result = _snap.authorize_change(PLAN_ID, 1, FROZEN[0], 'operator: approve the wording')

    assert result['status'] == 'error', result
    assert 'tamper' in result['message']
    assert snapshot_file.read_bytes() == before
    stored = json.loads(snapshot_file.read_text(encoding='utf-8'))
    assert stored['authorized_changes'] == []
    assert _snap.snapshot_state(PLAN_ID) == 'tampered'


# =============================================================================
# The outcome vocabulary the code reports is the one its documents state
# =============================================================================


def _frozen_record_bullet() -> str:
    """The rubric bullet that governs the frozen record, verbatim from the skill."""
    rubric: str = (get_skill_dir('plan-marshall', 'phase-6-finalize') / 'standards' / 'review-rubric.md').read_text(
        encoding='utf-8'
    )
    for line in rubric.splitlines():
        if line.startswith('- A criterion the **frozen record**'):
            return line
    raise AssertionError('the frozen-record bullet is missing from review-rubric.md')


def test_the_authorization_outcome_vocabulary_matches_its_documents() -> None:
    """Every term the vocabulary declares appears in both documents that describe it.

    Both assertions are ``AUTHORIZATION_OUTCOMES ⊆ document``: a term the code
    reports that the writers' docstrings omit leaves the author without the state
    it must act on, and the same term missing from the rubric bullet leaves the
    reviewer without it. The reverse direction — a term a document describes that
    the vocabulary never reports — is NOT checked here, because the vocabulary is
    the declaration the check reads; each outcome is instead pinned by a test that
    drives it, and a term listed with no such test is the drift to watch for.
    """
    docstrings = f'{_snap.authorize_change.__doc__}\n{_snap.authorize_refreeze.__doc__}'
    rubric_bullet = _frozen_record_bullet()

    undocumented = [term for term in _snap.AUTHORIZATION_OUTCOMES if term not in docstrings]
    unrubricked = [term for term in _snap.AUTHORIZATION_OUTCOMES if term not in rubric_bullet]

    assert not undocumented, f'outcomes the docstrings do not name: {undocumented}'
    assert not unrubricked, f'outcomes the frozen-record rubric bullet does not name: {unrubricked}'
    assert len(set(_snap.AUTHORIZATION_OUTCOMES)) == len(_snap.AUTHORIZATION_OUTCOMES), (
        'the outcome vocabulary lists a term twice'
    )
