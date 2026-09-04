#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: E402
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
* running provenance unknown → defer, fail-closed (never drain on a guess);
* in-flight / queued counts unreported → defer, the same fail-closed shape: an
  absent count is silence, not idleness;
* a reconcile verb whose own fields say the daemon was never replaced → the owed
  marker is WRITTEN at ``reconcile_failed``, never cleared on the word
  ``success``.

Each fail-closed case carries a matched control — a genuine zero count, and a
verb whose fields do substantiate success — so a guard that fired on everything
would be caught rather than read as green.

The script is project-local (``.claude/skills/sync-plugin-cache/scripts``), not a
marketplace bundle — sync-plugin-cache is meta-project-only tooling.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT

# ``reconcile_daemon`` is a PROJECT-LOCAL skill script under ``.claude/``, not a
# marketplace bundle script, so neither ``load_script_module`` nor
# ``load_skill_module`` can address it and the root conftest's marketplace
# ``sys.path`` setup does not reach it. This bootstrap therefore stays where every
# marketplace one was removed, and it is what the file-level ``I001, E402`` waiver
# above is still paying for.
_SCRIPTS = PROJECT_ROOT / '.claude' / 'skills' / 'sync-plugin-cache' / 'scripts'
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import reconcile_daemon as rd

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


def test_absent_counts_defer_never_drain():
    # A daemon pinned to a copy predating the counts extension answers WITHOUT
    # the count keys. That is not idleness — it is silence — and the two were
    # once the same value here, which is how a live build got drained.
    status = _status(running_binary_path=_RUNNING_STALE, binary_diverges=True)
    del status['in_flight']
    del status['queued']

    decision = rd.decide(status)

    assert decision.action == rd.ACTION_DEFER
    assert decision.action not in (rd.ACTION_UPGRADE, rd.ACTION_START)
    assert decision.reason == 'counts_unknown'


def test_unknown_count_sentinel_defers():
    # The sentinel `status` now emits for an unreported count must reach the same
    # fail-closed branch as an absent key — this is the seam between the status
    # verb's `unknown` and the reconcile's decision.
    status = _status(
        running_binary_path=_RUNNING_STALE,
        binary_diverges=True,
        in_flight='unknown',
        queued='unknown',
    )
    assert rd.decide(status).reason == 'counts_unknown'


def test_one_absent_count_is_enough_to_defer():
    status = _status(running_binary_path=_RUNNING_STALE, binary_diverges=True, queued=0)
    del status['in_flight']
    assert rd.decide(status).reason == 'counts_unknown'


def test_counts_arriving_as_strings_are_still_counts():
    # The matched negative control: status reaches this script as TOON, so a
    # count legitimately arrives as its decimal string. If those read as unknown
    # the guard above would defer EVERY reconcile and the upgrade path would be
    # dead code that still looked green.
    idle = _status(
        running_binary_path=_RUNNING_STALE, binary_diverges=True, in_flight='0', queued='0'
    )
    assert rd.decide(idle) == rd.ReconcileDecision(rd.ACTION_UPGRADE, 'idle_and_stale')

    busy = _status(
        running_binary_path=_RUNNING_STALE, binary_diverges=True, in_flight='1', queued='0'
    )
    assert rd.decide(busy).reason == 'busy'


# =============================================================================
# reconcile() — orchestration with injected fakes
# =============================================================================


@pytest.fixture
def marker(tmp_path) -> Path:
    return tmp_path / 'reconcile-owed.json'


class _Runner:
    """Records every reconcile verb the orchestration runs.

    The default result models what ``upgrade`` / ``start`` ACTUALLY return: a
    status word plus the two fields that can carry a failed reconcile. A bare
    ``{'status': 'success'}`` is deliberately not the default, because the
    orchestration now refuses to treat an unsubstantiated success as one — a
    fake that omits them would be asserting against a verb shape that no longer
    exists.

    The default is selected on ``result is not None``, NOT on truthiness. A
    falsy-triggered ``or`` default silently swapped the SUCCESS default in for
    ``_Runner({})``, which made the fixture structurally incapable of producing
    the one result the production fail-open actually emits: ``_invoke_executor``
    returns ``{}`` whenever the executor is absent, the subprocess errors, the
    return code is non-zero, or the TOON does not parse. The empty dict must
    reach the orchestration verbatim.
    """

    def __init__(self, result: dict | None = None):
        self.calls: list[str] = []
        self._result = (
            result
            if result is not None
            else {
                'status': 'success',
                'drain_exited': True,
                'already_running': False,
            }
        )

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


def test_failed_upgrade_writes_the_owed_marker_and_never_clears_it(marker):
    # The verb says `success` but its own fields say the daemon was never
    # replaced. Gating on the word alone is what cleared a genuine owed marker
    # and recorded a still-stale daemon as reconciled.
    marker.write_text(
        json.dumps({'owed': True, 'since': 'T0', 'defer_count': 1}), encoding='utf-8'
    )
    runner = _Runner({'status': 'success', 'drain_exited': False, 'already_running': True})
    status = _status(running_binary_path=_RUNNING_STALE, binary_diverges=True)

    summary = rd.reconcile(
        status_reader=lambda: status, action_runner=runner, marker=marker, now='T1'
    )

    assert runner.calls == ['upgrade']
    assert summary['reconcile_result'] == 'failed'
    assert summary['owed'] is True
    # WRITTEN, never cleared — the marker is the only durable trace that the
    # daemon is still stale.
    assert marker.exists()
    recorded = json.loads(marker.read_text(encoding='utf-8'))
    assert recorded['reason'] == 'reconcile_failed'
    assert recorded['failed_action'] == rd.ACTION_UPGRADE
    # Carries the same binary-path fields the defer branch records.
    assert recorded['running_binary_path'] == _RUNNING_STALE
    assert recorded['resolved_binary_path'] == _RESOLVED
    # The prior deferral is continued, not restarted.
    assert recorded['since'] == 'T0'
    assert recorded['defer_count'] == 2
    assert 'reconcile FAILED' in summary['display_detail']


def test_failed_start_is_reported_by_already_running(marker):
    # `start` was chosen only because status said the daemon was DOWN. Finding
    # one already up means the world disagrees with that decision, so this is a
    # failed reconcile rather than an idempotent no-op.
    runner = _Runner({'status': 'success', 'already_running': True})
    status = _status(running=False, reason='socket_absent', running_binary_path=None)

    summary = rd.reconcile(
        status_reader=lambda: status, action_runner=runner, marker=marker, now='T1'
    )

    assert runner.calls == ['start']
    assert summary['reconcile_result'] == 'failed'
    assert summary['failure_reason'] == 'daemon_already_running'
    assert json.loads(marker.read_text(encoding='utf-8'))['reason'] == 'reconcile_failed'


def test_verb_that_reports_neither_field_cannot_prove_success(marker):
    # A verb that SAYS success but carries no failure-bearing field cannot
    # substantiate the claim. This is the field-absence arm only — the status word
    # is already 'success', so the gate is reached past the status check. The
    # fail-open {} is a DIFFERENT arm and has its own test below; folding the two
    # together is what left that one uncovered. The owed marker must survive an
    # unverifiable claim rather than be cleared by it.
    marker.write_text(json.dumps({'owed': True, 'defer_count': 4}), encoding='utf-8')
    runner = _Runner({'status': 'success'})
    status = _status(running_binary_path=_RUNNING_STALE, binary_diverges=True)

    summary = rd.reconcile(
        status_reader=lambda: status, action_runner=runner, marker=marker, now='T1'
    )

    assert summary['reconcile_result'] == 'failed'
    assert summary['failure_reason'] == 'already_running_absent'
    assert marker.exists()


def test_empty_verb_result_is_a_failed_reconcile_that_keeps_the_debt(marker):
    # The production fail-open: `_invoke_executor` returns {} when the executor is
    # absent, the subprocess errors, the return code is non-zero, or the TOON does
    # not parse — the single most likely real failure. It carries no status word
    # at all, so it fails at the status gate as `verb_reported_nothing`, EARLIER
    # and under a different reason than the field-absence case above.
    #
    # This case was unreachable until `_Runner` stopped selecting its default on
    # truthiness: `_Runner({})` used to hand back the success default, so the
    # fixture could not express the input two comments claimed was covered.
    marker.write_text(json.dumps({'owed': True, 'defer_count': 4}), encoding='utf-8')
    runner = _Runner({})
    status = _status(running_binary_path=_RUNNING_STALE, binary_diverges=True)

    summary = rd.reconcile(
        status_reader=lambda: status, action_runner=runner, marker=marker, now='T1'
    )

    assert runner.calls == ['upgrade']
    assert summary['reconcile_result'] == 'failed'
    assert summary['failure_reason'] == 'verb_reported_nothing'
    # An unverifiable success must NEVER discharge the debt.
    assert marker.exists()
    assert json.loads(marker.read_text(encoding='utf-8'))['reason'] == 'reconcile_failed'


def test_runner_fixture_returns_an_empty_result_verbatim():
    # Guards the fixture itself, not the orchestration: the case above is only
    # meaningful while `_Runner({})` really hands `{}` back. A truthiness-selected
    # default would substitute the success shape here and quietly turn that test
    # into a duplicate of the confirmed-success path.
    assert _Runner({})('upgrade') == {}
    # Matched negative control: the default is still supplied when nothing is passed.
    assert _Runner()('upgrade')['status'] == 'success'


def test_verb_reporting_error_is_a_failed_reconcile(marker):
    runner = _Runner({'status': 'error', 'reason': 'drain_did_not_exit'})
    status = _status(running_binary_path=_RUNNING_STALE, binary_diverges=True)

    summary = rd.reconcile(
        status_reader=lambda: status, action_runner=runner, marker=marker, now='T1'
    )

    assert summary['reconcile_result'] == 'failed'
    assert summary['failure_reason'] == 'verb_reported_error'
    assert marker.exists()


def test_confirmed_upgrade_still_clears_the_marker(marker):
    # The matched positive control for the four failure cases above: a verb whose
    # fields DO substantiate success still discharges the debt, so the gate is
    # not simply refusing to clear the marker in every case.
    marker.write_text(json.dumps({'owed': True, 'defer_count': 2}), encoding='utf-8')
    runner = _Runner({'status': 'success', 'drain_exited': True, 'already_running': False})
    status = _status(running_binary_path=_RUNNING_STALE, binary_diverges=True)

    summary = rd.reconcile(
        status_reader=lambda: status, action_runner=runner, marker=marker, now='T1'
    )

    assert summary['reconcile_result'] == 'success'
    assert summary['owed_cleared'] is True
    assert not marker.exists()


def test_toon_string_booleans_are_read_as_booleans(marker):
    # The result crosses a TOON boundary in production, so `false` arrives as a
    # string. Reading that as a truthy non-empty string would invert the guard.
    runner = _Runner({'status': 'success', 'drain_exited': 'false', 'already_running': 'true'})
    status = _status(running_binary_path=_RUNNING_STALE, binary_diverges=True)

    summary = rd.reconcile(
        status_reader=lambda: status, action_runner=runner, marker=marker, now='T1'
    )

    assert summary['reconcile_result'] == 'failed'
    assert summary['failure_reason'] == 'daemon_already_running'


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
