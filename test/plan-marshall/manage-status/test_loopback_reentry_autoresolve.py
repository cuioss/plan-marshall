#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the loop-back handshake drift auto-resolution.

A loop-back (``cmd_set_phase`` backward move) structurally guarantees
handshake drift at the next guarded boundary: the re-entered phases
legitimately change the invariants the earlier capture recorded. The
auto-resolution contract, proven here:

(a) a backward ``set-phase`` persists ``metadata.loop_back_reentry``
    (``from_phase`` / ``to_phase`` / ``at``) alongside the phase write;
(b) ``cmd_transition`` with invariant drift AND the marker present
    auto-re-captures the handshake (row replaced with ``override=true``
    and the recorded reason), clears the marker, and advances the phase;
(c) drift WITHOUT the marker keeps today's blocking behavior unchanged;
(d) a forward ``set-phase`` writes no marker;
(e) ``cmd_archive`` is the SECOND consumption point for the SAME marker — a plan
    archived while a re-entry is still open never reaches a guarded boundary at
    all, so archive clears the marker and records
    ``metadata.loop_back_reentry_outcome`` stating that the re-entry ended
    without completing, with a matched control proving that outcome record is not
    written unconditionally.

Cases (b) and (c) are the two PRE-EXISTING transition-boundary consumptions, and
they are asserted here unchanged: adding the archive point must leave both of them
behaving exactly as before.

The companion implementation lives in ``_status_query.py``
(``cmd_set_phase`` marker persistence) and ``_cmd_lifecycle.py``
(``_loop_back_auto_override``, consumed by ``cmd_transition``'s
blocking-boundary guard, and the marker consumption folded into
``cmd_archive``'s phase-closing write).
"""

import json
import sys
from argparse import Namespace
from pathlib import Path

# PLAIN imports, deliberately — see the MODULE IDENTITY note below.
import _handshake_commands as _cmds
import _handshake_store as _store
import _invariants as _inv
import pytest

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_cmd_lifecycle_loopback')
_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_status_query_loopback')

cmd_archive = _lifecycle.cmd_archive
cmd_create = _lifecycle.cmd_create
cmd_transition = _lifecycle.cmd_transition
cmd_set_phase = _query.cmd_set_phase


# =============================================================================
# MODULE IDENTITY
# =============================================================================


def test_the_handshake_modules_are_the_instance_the_production_path_resolves():
    """The stubs in this module patch the module objects ``cmd_verify`` reads.

    Plain imports are what make that true, and the property is asserted rather
    than inferred from a green run. ``conftest.load_script_module`` would bind a
    SECOND copy under the same name: the stub would then patch an object the
    production path never consults, and every stubbed test here would pass while
    verifying nothing — a false green no ordinary assertion could distinguish
    from a real one.
    """
    assert sys.modules['_handshake_commands'] is _cmds
    assert sys.modules['_handshake_store'] is _store
    assert sys.modules['_invariants'] is _inv


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def _stubbed_invariants(monkeypatch):
    """Deterministic invariant registry so drift can be induced by mutating a
    single state value between capture and transition."""
    state = {
        'main_sha': 'abc123',
        'main_dirty': 0,
        'main_dirty_files': [],
        'task_state_hash': 'hash-tasks',
        'qgate_open_count': 0,
        'config_hash': 'hash-cfg',
        'unfinished_tasks_count': 0,
        'pending_findings_by_type': '',
        'pending_findings_blocking_count': 0,
    }

    def always(_pid, _md):
        return True

    def make_capture(name):
        def _cap(_pid, _md, _phase):
            return state[name]

        return _cap

    stubbed = [(name, always, make_capture(name)) for name in state]
    monkeypatch.setattr(_inv, 'INVARIANTS', stubbed)
    monkeypatch.setattr(_cmds, 'INVARIANTS', stubbed)
    return state


@pytest.fixture
def _stub_metadata(monkeypatch):
    """Replace ``_load_status_metadata`` so cmd_verify's / cmd_capture's own
    worktree assertion stays out of the way — the marker is read from the
    status dict directly, independent of this stub."""
    md: dict = {}
    monkeypatch.setattr(_cmds, '_load_status_metadata', lambda _pid: md)
    return md


def _seed_plan(plan_context, plan_id: str, metadata: dict | None = None) -> Path:
    """Create a plan at 5-execute with a captured handshake row. Returns the
    plan's status.json path."""
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Loop-Back Auto-Resolve Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    for phase in ('1-init', '2-refine', '3-outline', '4-plan'):
        _query.cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    _query.cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))

    status_path: Path = plan_context.plan_dir_for(plan_id) / 'status.json'
    if metadata is not None:
        status = json.loads(status_path.read_text(encoding='utf-8'))
        status['metadata'] = metadata
        status_path.write_text(json.dumps(status), encoding='utf-8')

    _cmds.cmd_capture(Namespace(plan_id=plan_id, phase='5-execute', override=False, reason=None, strict=False))
    return status_path


def _read_status(status_path: Path) -> dict:
    status: dict = json.loads(status_path.read_text(encoding='utf-8'))
    return status


def _is_true(value) -> bool:
    """Tolerate TOON round-trip bool spellings on stored handshake rows."""
    return value is True or str(value).strip().lower() == 'true'


# =============================================================================
# (a) Backward set-phase persists the marker
# =============================================================================


def test_backward_set_phase_persists_loop_back_marker(plan_context, _stubbed_invariants, _stub_metadata):
    """5-execute → 2-refine (backward) writes metadata.loop_back_reentry."""
    plan_id = 'loopback-marker-persisted'
    status_path = _seed_plan(plan_context, plan_id, {'use_worktree': False})

    result = cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))

    assert result['status'] == 'success'
    marker = _read_status(status_path).get('metadata', {}).get('loop_back_reentry')
    assert marker is not None, (
        'Backward set-phase must persist metadata.loop_back_reentry so the guarded-boundary drift can be auto-resolved.'
    )
    assert marker['from_phase'] == '5-execute'
    assert marker['to_phase'] == '2-refine'
    assert marker['at'], 'Marker must carry a timestamp.'


# =============================================================================
# (b) Drift + marker → auto-recapture, marker cleared, phase advances
# =============================================================================


def test_drift_with_marker_auto_recaptures_and_advances(plan_context, _stubbed_invariants, _stub_metadata):
    """Invariant drift with the marker present is auto-resolved: the handshake
    row is replaced (override=true, reason recorded), the marker is cleared,
    and the transition proceeds to 6-finalize."""
    plan_id = 'loopback-drift-autoresolved'
    status_path = _seed_plan(plan_context, plan_id, {'use_worktree': False})

    # Sanctioned loop-back: backward move writes the marker; the plan then
    # works its way forward again to the guarded boundary.
    cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))
    assert _read_status(status_path)['metadata'].get('loop_back_reentry') is not None

    # The re-run phases legitimately changed an invariant → drift by construction.
    _stubbed_invariants['task_state_hash'] = 'hash-tasks-after-loopback'

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'success', f'Scheduled loop-back drift must be auto-resolved, got {result!r}.'
    assert result['next_phase'] == '6-finalize'

    after = _read_status(status_path)
    assert after['current_phase'] == '6-finalize'
    assert 'loop_back_reentry' not in after.get('metadata', {}), (
        'The marker must be cleared so the override fires exactly once.'
    )

    row = _store.get_row(plan_id, '5-execute')
    assert row is not None
    assert _is_true(row.get('override')), f'Auto-recapture must mark the replaced row override=true, got {row!r}.'
    assert 'loop-back re-entry auto-override (scheduled by 5-execute loop_back)' in str(row.get('override_reason')), (
        f'Recorded reason must name the scheduling loop-back, got {row!r}.'
    )
    assert row.get('task_state_hash') == 'hash-tasks-after-loopback', (
        'The replaced row must capture the post-loop-back state.'
    )


# =============================================================================
# (b2) Clean verify + marker → marker consumed WITHOUT recapture
# =============================================================================


def test_clean_verify_with_marker_consumes_marker_without_recapture(plan_context, _stubbed_invariants, _stub_metadata):
    """Consume-on-next-guarded-verification: a clean (non-blocking) guarded
    verify with the marker present must clear it — without a recapture — so a
    stale marker cannot incorrectly auto-override a later, genuinely
    unscheduled drift."""
    plan_id = 'loopback-clean-verify-consumes-marker'
    status_path = _seed_plan(plan_context, plan_id, {'use_worktree': False})

    # Sanctioned loop-back writes the marker; invariants are NOT mutated, so
    # the guarded verify at the boundary comes back clean.
    cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))
    assert _read_status(status_path)['metadata'].get('loop_back_reentry') is not None

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'success'
    assert result['next_phase'] == '6-finalize'

    after = _read_status(status_path)
    assert 'loop_back_reentry' not in after.get('metadata', {}), (
        'A clean guarded verification must consume the marker — a stale '
        'marker would incorrectly auto-override a later unscheduled drift.'
    )

    row = _store.get_row(plan_id, '5-execute')
    assert row is not None
    assert not _is_true(row.get('override')), (
        f'A clean verify must NOT recapture with override=true — the marker is consumed by a plain clear, got {row!r}.'
    )
    # Unscheduled drift AFTER the marker is consumed still blocks — proven by
    # test_drift_without_marker_still_blocks (case c); the marker-absence
    # assertion above is what guarantees that case now applies.


# =============================================================================
# (c) Drift WITHOUT the marker still blocks
# =============================================================================


def test_drift_without_marker_still_blocks(plan_context, _stubbed_invariants, _stub_metadata):
    """Unscheduled drift keeps today's blocking behavior unchanged."""
    plan_id = 'loopback-unscheduled-drift-blocks'
    status_path = _seed_plan(plan_context, plan_id, {'use_worktree': False})

    _stubbed_invariants['task_state_hash'] = 'hash-tasks-mutated'

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'drift', f'Drift without the marker must block the transition, got {result!r}.'
    assert result['drift_count'] >= 1
    after = _read_status(status_path)
    assert after['current_phase'] == '5-execute', (
        'cmd_transition advanced despite unscheduled drift — the auto-override '
        'must be gated on the loop_back_reentry marker.'
    )


# =============================================================================
# (d-pre) Explicit-None metadata is normalized, never crashed on
# =============================================================================


def test_set_phase_loop_back_with_explicit_none_metadata(plan_context, _stubbed_invariants, _stub_metadata):
    """An explicit JSON null for status['metadata'] must be normalized by the
    backward set-phase (dict.setdefault would return None and the marker
    assignment would raise TypeError)."""
    plan_id = 'loopback-none-metadata-setphase'
    status_path = _seed_plan(plan_context, plan_id)
    status = _read_status(status_path)
    status['metadata'] = None
    status_path.write_text(json.dumps(status), encoding='utf-8')

    result = cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))

    assert result['status'] == 'success'
    marker = _read_status(status_path).get('metadata', {}).get('loop_back_reentry')
    assert marker is not None, (
        'Explicit-None metadata must be normalized to a dict so the backward '
        'set-phase can persist the loop-back marker.'
    )
    assert marker['from_phase'] == '5-execute'


def test_loop_back_auto_override_with_explicit_none_metadata():
    """_loop_back_auto_override must not raise AttributeError when
    status['metadata'] is explicitly None — it returns the verify result
    unchanged (no marker means no auto-override)."""
    verify_result = {'status': 'drift', 'drift_count': 1, 'diffs': []}

    result = _lifecycle._loop_back_auto_override(
        Namespace(plan_id='loopback-none-metadata-override', completed='5-execute'),
        {'metadata': None},
        verify_result,
    )

    assert result is verify_result, (
        'None metadata carries no marker — the blocking verify result must be returned unchanged, not crashed on.'
    )


def test_clean_tree_refusal_with_explicit_none_metadata():
    """_clean_tree_refusal must not raise AttributeError when
    status['metadata'] is explicitly None — no worktree means no refusal."""
    result = _lifecycle._clean_tree_refusal('loopback-none-metadata-cleantree', {'metadata': None})

    assert result is None, 'None metadata implies no use_worktree — the clean-tree gate must pass through, not crash.'


# =============================================================================
# (d) Forward set-phase writes no marker
# =============================================================================


def test_forward_set_phase_writes_no_marker(plan_context, _stubbed_invariants, _stub_metadata):
    """A forward move never schedules an auto-override."""
    plan_id = 'loopback-forward-no-marker'
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Loop-Back Auto-Resolve Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )

    result = cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))

    assert result['status'] == 'success'
    status_path: Path = plan_context.plan_dir_for(plan_id) / 'status.json'
    metadata = _read_status(status_path).get('metadata', {})
    assert 'loop_back_reentry' not in metadata, (
        f'Forward set-phase must not write the loop-back marker, got {metadata!r}.'
    )


# =============================================================================
# (e) Archive is the SECOND consumption point for the SAME marker
#
# The pair below differs along exactly one axis — whether a re-entry is open at
# archive time — so the contrast is attributable to that and nothing else. The
# control is the load-bearing half: without it the first cell is equally consistent
# with archive writing the outcome record unconditionally, which would assert that a
# loop-back ended without completing on a plan that never looped back at all.
# =============================================================================


def test_archive_consumes_an_open_marker_and_records_it_never_completed(
    plan_context, _stubbed_invariants, _stub_metadata
):
    """A plan archived mid-re-entry: the marker is cleared and the outcome recorded.

    Such a plan never reaches the guarded boundary where ``cmd_transition`` would
    consume the marker, so without this second consumption point the marker rides
    into the permanent archived record still asserting that a loop-back is in flight
    for a plan that has finished.

    Clearing alone would not be enough either — the outcome record is what keeps the
    re-entry's end from being silently dropped: it really did end, and it ended
    WITHOUT completing.
    """
    plan_id = 'loopback-archived-mid-reentry'
    status_path = _seed_plan(plan_context, plan_id, {'use_worktree': False})

    cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))
    marker = _read_status(status_path)['metadata'].get('loop_back_reentry')
    assert marker is not None, (
        'Precondition: the re-entry must really be OPEN at archive time, '
        'otherwise every assertion below passes vacuously.'
    )

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))
    assert result['status'] == 'success', f'archive failed: {result}'

    archived_metadata = json.loads((Path(result['archived_to']) / 'status.json').read_text(encoding='utf-8')).get(
        'metadata', {}
    )

    assert 'loop_back_reentry' not in archived_metadata, (
        f'The permanent record must not carry a still-open loop-back marker; got {archived_metadata!r}.'
    )

    outcome = archived_metadata.get('loop_back_reentry_outcome')
    assert outcome is not None, (
        'Consuming the marker is not sufficient — archive must RECORD that the '
        're-entry ended without completing, or the fact is lost with the marker.'
    )
    assert outcome['outcome'] == 'ended_without_completing', outcome
    assert outcome['from_phase'] == marker['from_phase'], (
        f"The outcome must carry the consumed marker's own phases; got {outcome!r} against marker {marker!r}."
    )
    assert outcome['to_phase'] == marker['to_phase'], outcome
    assert outcome['scheduled_at'] == marker['at'], (
        f"scheduled_at must be the marker's own timestamp, not the consumption time; got {outcome!r}."
    )
    assert outcome['consumed_by'] == 'archive', (
        f'The record must name WHICH consumption point fired, since there are two; got {outcome!r}.'
    )
    assert outcome['consumed_at'], 'The outcome must say when the marker was consumed.'


def test_archive_without_an_open_marker_records_no_outcome(plan_context, _stubbed_invariants, _stub_metadata):
    """Matched control: no marker at archive time ⇒ no outcome key at all.

    This is the half that gives the cell above its meaning. A verb that wrote the
    outcome record unconditionally would pass that assertion while claiming a
    loop-back ended without completing on a plan that never had one.
    """
    plan_id = 'loopback-archived-no-marker'
    status_path = _seed_plan(plan_context, plan_id, {'use_worktree': False})
    assert 'loop_back_reentry' not in _read_status(status_path).get('metadata', {}), (
        "Precondition: this plan must carry NO marker, so the absence asserted below is the verb's own answer."
    )

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))
    assert result['status'] == 'success', f'archive failed: {result}'

    archived_metadata = json.loads((Path(result['archived_to']) / 'status.json').read_text(encoding='utf-8')).get(
        'metadata', {}
    )
    assert 'loop_back_reentry_outcome' not in archived_metadata, (
        f'A plan that never looped back must carry no re-entry outcome; got {archived_metadata!r}.'
    )
