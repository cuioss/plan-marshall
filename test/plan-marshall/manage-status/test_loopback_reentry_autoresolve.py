#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: E402
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
(d) a forward ``set-phase`` writes no marker.

The companion implementation lives in ``_status_query.py``
(``cmd_set_phase`` marker persistence) and ``_cmd_lifecycle.py``
(``_loop_back_auto_override``, consumed by ``cmd_transition``'s
blocking-boundary guard).
"""

import json
import sys as _sys
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module

_lifecycle = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_cmd_lifecycle_loopback'
)
_query = load_script_module(
    'plan-marshall', 'manage-status', '_status_query.py', '_status_query_loopback'
)

cmd_create = _lifecycle.cmd_create
cmd_transition = _lifecycle.cmd_transition
cmd_set_phase = _query.cmd_set_phase

# Standard imports for the handshake modules so the invariant stubs hit the
# same module instance ``_cmd_lifecycle.cmd_verify`` / ``cmd_capture`` read at
# runtime (mirrors test_transition_boundary_guards.py).
_PLAN_HANDSHAKE_SCRIPTS_DIR = str(
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'plan-marshall'
    / 'scripts'
)
if _PLAN_HANDSHAKE_SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _PLAN_HANDSHAKE_SCRIPTS_DIR)

import _handshake_commands as _cmds
import _handshake_store as _store
import _invariants as _inv

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

    _cmds.cmd_capture(
        Namespace(plan_id=plan_id, phase='5-execute', override=False, reason=None, strict=False)
    )
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


def test_backward_set_phase_persists_loop_back_marker(
    plan_context, _stubbed_invariants, _stub_metadata
):
    """5-execute → 2-refine (backward) writes metadata.loop_back_reentry."""
    plan_id = 'loopback-marker-persisted'
    status_path = _seed_plan(plan_context, plan_id, {'use_worktree': False})

    result = cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))

    assert result['status'] == 'success'
    marker = _read_status(status_path).get('metadata', {}).get('loop_back_reentry')
    assert marker is not None, (
        'Backward set-phase must persist metadata.loop_back_reentry so the '
        'guarded-boundary drift can be auto-resolved.'
    )
    assert marker['from_phase'] == '5-execute'
    assert marker['to_phase'] == '2-refine'
    assert marker['at'], 'Marker must carry a timestamp.'


# =============================================================================
# (b) Drift + marker → auto-recapture, marker cleared, phase advances
# =============================================================================


def test_drift_with_marker_auto_recaptures_and_advances(
    plan_context, _stubbed_invariants, _stub_metadata
):
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
    assert result['status'] == 'success', (
        f'Scheduled loop-back drift must be auto-resolved, got {result!r}.'
    )
    assert result['next_phase'] == '6-finalize'

    after = _read_status(status_path)
    assert after['current_phase'] == '6-finalize'
    assert 'loop_back_reentry' not in after.get('metadata', {}), (
        'The marker must be cleared so the override fires exactly once.'
    )

    row = _store.get_row(plan_id, '5-execute')
    assert row is not None
    assert _is_true(row.get('override')), (
        f'Auto-recapture must mark the replaced row override=true, got {row!r}.'
    )
    assert 'loop-back re-entry auto-override (scheduled by 5-execute loop_back)' in str(
        row.get('override_reason')
    ), f'Recorded reason must name the scheduling loop-back, got {row!r}.'
    assert row.get('task_state_hash') == 'hash-tasks-after-loopback', (
        'The replaced row must capture the post-loop-back state.'
    )


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
    assert result['status'] == 'drift', (
        f'Drift without the marker must block the transition, got {result!r}.'
    )
    assert result['drift_count'] >= 1
    after = _read_status(status_path)
    assert after['current_phase'] == '5-execute', (
        'cmd_transition advanced despite unscheduled drift — the auto-override '
        'must be gated on the loop_back_reentry marker.'
    )


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
