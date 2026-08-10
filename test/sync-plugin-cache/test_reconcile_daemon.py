#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the project-local marshalld reconcile (D1/D2/D3, D6 cases).

The reconcile heals version drift from the meta-project's own sync surface. The
DECISION (``decide``) is pure and pins the D1 idle-conditional contract; the
ORCHESTRATION (``reconcile``) is driven with injected fakes so the safety
properties are asserted without a real daemon:

* idle-and-stale → upgrade (reconciled);
* BUSY-and-stale → NOT drained (no reconcile verb runs at all), deferral marker
  written, the in-flight job left untouched — the deliverable that matters most;
* down-but-enrolled (socket_absent) → plain start, no drain;
* running the fresh pin → no-op;
* not enrolled / status unavailable → silent no-op;
* running provenance unknown → defer, fail-closed (never drain on a guess).

The script is project-local (``.claude/skills/sync-plugin-cache/scripts``), not a
marketplace bundle — sync-plugin-cache is meta-project-only tooling.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT

_SCRIPTS = PROJECT_ROOT / '.claude' / 'skills' / 'sync-plugin-cache' / 'scripts'
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import reconcile_daemon as rd  # noqa: E402

_RESOLVED = '/cache/plan-marshall/0.1.1231/skills/manage-build-server/scripts/marshalld.py'
_RUNNING_STALE = '/cache/plan-marshall/0.1.1212/skills/manage-build-server/scripts/marshalld.py'


def _status(**overrides) -> dict:
    """A ready manage-build-server status dict, overridable per test."""
    base = {
        'status': 'success',
        'action': 'status',
        'running': True,
        'registered': True,
        'running_binary_path': _RESOLVED,
        'resolved_binary_path': _RESOLVED,
        'binary_diverges': False,
        'in_flight': 0,
        'queued': 0,
    }
    base.update(overrides)
    return base


# =============================================================================
# decide() — the pure D1 contract
# =============================================================================


def test_idle_and_stale_decides_upgrade():
    status = _status(running_binary_path=_RUNNING_STALE, binary_diverges=True, in_flight=0, queued=0)
    assert rd.decide(status) == rd.ReconcileDecision(rd.ACTION_UPGRADE, 'idle_and_stale')


def test_busy_and_stale_decides_defer_not_upgrade():
    # The BUSY case: something is in flight, so the reconcile must DEFER, never
    # drain. This is the safety property the whole gate exists to protect.
    status = _status(running_binary_path=_RUNNING_STALE, binary_diverges=True, in_flight=1, queued=0)
    decision = rd.decide(status)
    assert decision.action == rd.ACTION_DEFER
    assert decision.action != rd.ACTION_UPGRADE
    assert decision.reason == 'busy'


def test_queued_work_also_counts_as_busy():
    # A queued-but-not-running job would be silently lost on a drain, so a nonzero
    # queue is busy too.
    status = _status(running_binary_path=_RUNNING_STALE, binary_diverges=True, in_flight=0, queued=2)
    assert rd.decide(status).action == rd.ACTION_DEFER


def test_socket_absent_but_enrolled_decides_plain_start():
    status = _status(running=False, reason='socket_absent', running_binary_path=None)
    decision = rd.decide(status)
    assert decision.action == rd.ACTION_START
    assert decision.reason == 'socket_absent'


def test_unreachable_but_enrolled_decides_start():
    status = _status(running=False, reason='unreachable')
    assert rd.decide(status).action == rd.ACTION_START


def test_running_the_fresh_pin_is_noop():
    # running == resolved → not stale → nothing to do.
    assert rd.decide(_status(binary_diverges=False)).action == rd.ACTION_NOOP


def test_not_enrolled_is_silent_noop():
    assert rd.decide(_status(registered=False)).action == rd.ACTION_NOOP


def test_status_unavailable_is_noop():
    assert rd.decide({'status': 'error'}).action == rd.ACTION_NOOP
    assert rd.decide({}).action == rd.ACTION_NOOP


def test_unknown_provenance_defers_never_drains():
    # Fail-closed: an undeterminable running binary must NEVER be reconciled by a
    # drain — the reconcile defers instead of guessing idleness.
    status = _status(running_binary_path='unknown', binary_diverges=False, in_flight=0, queued=0)
    decision = rd.decide(status)
    assert decision.action == rd.ACTION_DEFER
    assert decision.action not in (rd.ACTION_UPGRADE, rd.ACTION_START)
    assert decision.reason == 'provenance_unknown'


# =============================================================================
# reconcile() — orchestration with injected fakes
# =============================================================================


@pytest.fixture
def marker(tmp_path) -> Path:
    return tmp_path / 'reconcile-owed.json'


class _Runner:
    """Records every reconcile verb the orchestration runs."""

    def __init__(self, result: dict | None = None):
        self.calls: list[str] = []
        self._result = result or {'status': 'success'}

    def __call__(self, action: str) -> dict:
        self.calls.append(action)
        return self._result


def test_idle_and_stale_runs_upgrade_and_clears_marker(marker):
    marker.write_text(json.dumps({'owed': True, 'defer_count': 2}), encoding='utf-8')
    runner = _Runner()
    status = _status(running_binary_path=_RUNNING_STALE, binary_diverges=True)

    summary = rd.reconcile(
        status_reader=lambda: status, action_runner=runner, marker=marker, now='T0',
    )

    assert summary['action'] == rd.ACTION_UPGRADE
    assert runner.calls == ['upgrade']
    # A prior owed marker is discharged by the reconcile.
    assert not marker.exists()
    assert summary['owed_cleared'] is True


def test_busy_defer_never_runs_a_reconcile_verb_and_writes_marker(marker):
    # THE critical test: a busy-and-stale daemon is left entirely untouched — no
    # upgrade, no start, no drain — so the in-flight job cannot be drained. Only a
    # readable deferral marker is written.
    runner = _Runner()
    status = _status(running_binary_path=_RUNNING_STALE, binary_diverges=True, in_flight=1)

    summary = rd.reconcile(
        status_reader=lambda: status, action_runner=runner, marker=marker, now='T1',
    )

    assert summary['action'] == rd.ACTION_DEFER
    # No mutating control verb was issued — the daemon (and its in-flight job) is
    # untouched. A deferral log with a killed job would be a failed deliverable.
    assert runner.calls == []
    # The deferral is observable after the fact without a raw log scan.
    assert marker.exists()
    recorded = json.loads(marker.read_text(encoding='utf-8'))
    assert recorded['owed'] is True
    assert recorded['reason'] == 'busy'
    assert recorded['defer_count'] == 1
    assert recorded['in_flight'] == 1


def test_defer_count_increments_across_busy_syncs(marker):
    runner = _Runner()
    status = _status(running_binary_path=_RUNNING_STALE, binary_diverges=True, in_flight=1)

    first = rd.reconcile(status_reader=lambda: status, action_runner=runner, marker=marker, now='T1')
    second = rd.reconcile(status_reader=lambda: status, action_runner=runner, marker=marker, now='T2')
    third = rd.reconcile(status_reader=lambda: status, action_runner=runner, marker=marker, now='T3')

    assert (first['defer_count'], second['defer_count'], third['defer_count']) == (1, 2, 3)
    recorded = json.loads(marker.read_text(encoding='utf-8'))
    # `since` is preserved from the first deferral; `last_deferred` advances — a
    # daemon stale across several busy syncs is visibly, cumulatively owed.
    assert recorded['since'] == 'T1'
    assert recorded['last_deferred'] == 'T3'
    assert recorded['defer_count'] == 3
    # Still no reconcile verb ever ran across the three busy syncs.
    assert runner.calls == []


def test_socket_absent_runs_start(marker):
    runner = _Runner()
    status = _status(running=False, reason='socket_absent', running_binary_path=None)

    summary = rd.reconcile(status_reader=lambda: status, action_runner=runner, marker=marker, now='T0')

    assert summary['action'] == rd.ACTION_START
    assert runner.calls == ['start']


def test_current_daemon_clears_a_stale_owed_marker(marker):
    marker.write_text(json.dumps({'owed': True, 'defer_count': 5}), encoding='utf-8')
    runner = _Runner()

    summary = rd.reconcile(
        status_reader=lambda: _status(binary_diverges=False), action_runner=runner, marker=marker, now='T0',
    )

    assert summary['action'] == rd.ACTION_NOOP
    assert runner.calls == []
    # The daemon is current now — an earlier owed reconcile is moot, so cleared.
    assert not marker.exists()
    assert summary['owed_cleared'] is True


def test_status_unavailable_preserves_an_owed_marker(marker):
    # An indeterminate status read must NOT discard a genuine owed marker.
    marker.write_text(json.dumps({'owed': True, 'defer_count': 3}), encoding='utf-8')
    runner = _Runner()

    summary = rd.reconcile(status_reader=lambda: {}, action_runner=runner, marker=marker, now='T0')

    assert summary['action'] == rd.ACTION_NOOP
    assert summary['reason'] == 'status_unavailable'
    assert marker.exists()  # preserved
    assert runner.calls == []


def test_not_enrolled_is_silent_noop_with_no_verb(marker):
    runner = _Runner()
    summary = rd.reconcile(
        status_reader=lambda: _status(registered=False), action_runner=runner, marker=marker, now='T0',
    )
    assert summary['action'] == rd.ACTION_NOOP
    assert runner.calls == []


# =============================================================================
# marker + adapter fail-open
# =============================================================================


def test_marker_read_of_absent_file_is_none(tmp_path):
    assert rd.read_marker(tmp_path / 'nope.json') is None


def test_invoke_executor_absent_executor_fails_open(tmp_path):
    # No .plan/execute-script.py under the repo root → silent {} (no reconcile),
    # so a repository not using marshalld is unaffected.
    assert rd._invoke_executor('status', tmp_path) == {}


def test_emit_toon_renders_booleans_lowercase():
    out = rd._emit_toon({'status': 'success', 'action': 'noop', 'owed': False})
    assert 'action: noop' in out
    assert 'owed: false' in out
