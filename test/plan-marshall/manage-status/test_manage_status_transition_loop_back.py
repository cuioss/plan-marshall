#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for manage-status.py transition: the loop-back target contract,
the inline strict-verify guard, and the persisted-title-state drive seam."""


import json
from argparse import Namespace

import _handshake_commands as _cmds
import _invariants as _inv
import pytest
from _manage_status_transition_fixtures import (
    SCRIPT_PATH,
    _core,
    _lifecycle,
    _mark_step_args,
    _seed_execute_phase_plan,
    _seed_plan_with_5_execute_capture,
    _setup_plan,
    _stub_metadata,
    cmd_mark_step_done,
    cmd_transition,
)

from conftest import run_script

# =============================================================================
# Regression Tests: cmd_transition inline strict-verify guard for guarded
# boundaries (folded from the standalone phase_handshake verify --strict step
# that orchestrator workflow docs used to issue separately at 5-execute -> 6-finalize).
# =============================================================================

@pytest.fixture
def _stubbed_invariants(monkeypatch):
    """Deterministic invariant registry shared across cmd_capture / cmd_verify."""
    state = {
        'main_sha': 'abc123',
        'main_dirty': 0,
        'main_dirty_files': [],
        'worktree_sha': None,
        'worktree_dirty': None,
        'worktree_orphan': None,
        'task_state_hash': 'hash-tasks',
        'qgate_open_count': 0,
        'config_hash': 'hash-cfg',
        'unfinished_tasks_count': 2,
        'phase_steps_complete': None,
        'pending_findings_by_type': '',
        'pending_findings_blocking_count': 0,
    }

    def always(_pid, _md):
        return True

    def make_capture(name):
        def _cap(_pid, _md, _phase):
            return state[name]

        return _cap

    stubbed = [
        ('main_sha', always, make_capture('main_sha')),
        ('main_dirty', always, make_capture('main_dirty')),
        ('main_dirty_files', always, make_capture('main_dirty_files')),
        ('task_state_hash', always, make_capture('task_state_hash')),
        ('qgate_open_count', always, make_capture('qgate_open_count')),
        ('config_hash', always, make_capture('config_hash')),
        ('unfinished_tasks_count', always, make_capture('unfinished_tasks_count')),
        ('pending_findings_by_type', always, make_capture('pending_findings_by_type')),
        ('pending_findings_blocking_count', always, make_capture('pending_findings_blocking_count')),
    ]
    monkeypatch.setattr(_inv, 'INVARIANTS', stubbed)
    monkeypatch.setattr(_cmds, 'INVARIANTS', stubbed)
    return state


# =============================================================================
# Test: Hybrid loopback contract — `--loop-back-target` granularity flag
# =============================================================================

class TestLoopBackTargetValidation:
    """The `--loop-back-target` flag is REQUIRED on every loop_back outcome
    and FORBIDDEN on every other outcome.
    """

    def test_loop_back_without_target_returns_missing_error(self, plan_context) -> None:
        """Case 1: omitting `--loop-back-target` on a loop_back outcome
        returns `error: missing_loop_back_target`."""
        plan_id = 'lbt-missing-target'
        _setup_plan(plan_id)
        result = cmd_mark_step_done(
            _mark_step_args(
                plan_id,
                '6-finalize',
                'automatic-review',
                'loop_back',
                display_detail='loop-back without target',
                loop_back_target=None,
            )
        )
        assert result['status'] == 'error'
        assert result['error'] == 'missing_loop_back_target'
        assert 'required' in result['message'].lower()

    def test_loop_back_with_target_5_execute_persists_field(self, plan_context) -> None:
        """Case 2: `--loop-back-target 5-execute` succeeds and persists."""
        plan_id = 'lbt-target-5-execute'
        _setup_plan(plan_id)
        result = cmd_mark_step_done(
            _mark_step_args(
                plan_id,
                '6-finalize',
                'sonar-roundtrip',
                'loop_back',
                display_detail='loop-back iter 1 (target=5-execute)',
                loop_back_target='5-execute',
            )
        )
        assert result['status'] == 'success'
        assert result['outcome'] == 'loop_back'
        assert result['loop_back_target'] == '5-execute'

        status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
        entry = status['metadata']['phase_steps']['6-finalize']['sonar-roundtrip']
        assert entry['outcome'] == 'loop_back'
        assert entry['loop_back_target'] == '5-execute', (
            'Persisted phase_steps record must carry loop_back_target=5-execute'
        )

    def test_loop_back_with_target_6_finalize_persists_field(self, plan_context) -> None:
        """Case 3: `--loop-back-target 6-finalize` succeeds and persists."""
        plan_id = 'lbt-target-6-finalize'
        _setup_plan(plan_id)
        result = cmd_mark_step_done(
            _mark_step_args(
                plan_id,
                '6-finalize',
                'automatic-review',
                'loop_back',
                display_detail='loop-back iter 1 (target=6-finalize)',
                loop_back_target='6-finalize',
            )
        )
        assert result['status'] == 'success'
        assert result['outcome'] == 'loop_back'
        assert result['loop_back_target'] == '6-finalize'

        status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
        entry = status['metadata']['phase_steps']['6-finalize']['automatic-review']
        assert entry['outcome'] == 'loop_back'
        assert entry['loop_back_target'] == '6-finalize', (
            'Persisted phase_steps record must carry loop_back_target=6-finalize'
        )

    def test_loop_back_with_invalid_target_rejected_by_argparse(self, plan_context) -> None:
        """Case 4: argparse `choices` enforcement rejects invalid value."""
        plan_id = 'lbt-invalid-target'
        _setup_plan(plan_id)
        result = run_script(
            SCRIPT_PATH,
            'mark-step-done',
            '--plan-id',
            plan_id,
            '--phase',
            '6-finalize',
            '--step',
            'automatic-review',
            '--outcome',
            'loop_back',
            '--loop-back-target',
            'invalid-phase',
            '--display-detail',
            'loop-back invalid target',
        )
        assert result.returncode == 2, (
            f'argparse must reject invalid --loop-back-target value '
            f'with exit code 2; got {result.returncode}'
        )
        assert 'invalid choice' in result.stderr.lower() or 'invalid-phase' in result.stderr.lower()

    def test_loop_back_target_forbidden_on_non_loop_back_outcome(self, plan_context) -> None:
        """Guard: supplying `--loop-back-target` alongside a non-loop_back outcome errors."""
        plan_id = 'lbt-forbidden-on-done'
        _setup_plan(plan_id)
        result = cmd_mark_step_done(
            _mark_step_args(
                plan_id,
                '6-finalize',
                'push',
                'done',
                display_detail='step complete',
                loop_back_target='5-execute',
            )
        )
        assert result['status'] == 'error'
        assert result['error'] == 'unexpected_loop_back_target'

    def test_loop_back_target_invalid_at_api_layer(self, plan_context) -> None:
        """API-layer guard: bypassing argparse with invalid loop_back_target value."""
        plan_id = 'lbt-api-invalid-target'
        _setup_plan(plan_id)
        result = cmd_mark_step_done(
            _mark_step_args(
                plan_id,
                '6-finalize',
                'automatic-review',
                'loop_back',
                display_detail='loop-back invalid api target',
                loop_back_target='not-a-real-phase',
            )
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_loop_back_target'


# =============================================================================
# Regression Tests: persisted-title-state-write drive seam (Defects 1 & 2)
# =============================================================================

def test_cmd_transition_fires_drive_seam_after_write(plan_context, monkeypatch):
    """cmd_transition fires _surface_drive exactly once (with the plan_id) on advance."""
    plan_id = 'drive-seam-transition'
    _seed_execute_phase_plan(plan_context.plan_dir_for(plan_id), plan_id)

    calls = []
    monkeypatch.setattr(_lifecycle, '_surface_drive', lambda pid: calls.append(pid))

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result['status'] == 'success'
    assert calls == [plan_id], (
        f'cmd_transition must fire the drive seam exactly once with the plan_id '
        f'after write_status, got {calls!r}.'
    )


def test_cmd_transition_drift_refusal_does_not_fire_drive_seam(
    plan_context, _stubbed_invariants, _stub_metadata, monkeypatch
):
    """A guarded-boundary drift refusal returns BEFORE write_status — the drive
    seam must NOT fire (no phase advanced, nothing to repaint)."""
    plan_id = 'drive-seam-no-fire-on-drift'
    _seed_plan_with_5_execute_capture(plan_id)
    _stubbed_invariants['main_sha'] = 'drifted-no-fire'

    calls = []
    monkeypatch.setattr(_lifecycle, '_surface_drive', lambda pid: calls.append(pid))

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result['status'] == 'drift'
    assert calls == [], (
        f'The drive seam must not fire when the transition is refused before '
        f'write_status, got {calls!r}.'
    )


def test_surface_drive_fires_bind_then_repaint(monkeypatch):
    """_surface_drive fires exactly one bind then one repaint, both with the plan_id."""
    events = []
    monkeypatch.setattr(_core, '_drive_bind', lambda pid: events.append(('bind', pid)))
    monkeypatch.setattr(_core, '_drive_repaint', lambda pid: events.append(('repaint', pid)))

    _core._surface_drive('seam-plan')

    assert events == [('bind', 'seam-plan'), ('repaint', 'seam-plan')], (
        f'_surface_drive must fire one bind then one repaint, got {events!r}.'
    )


def test_surface_drive_swallows_delegation_failure(monkeypatch):
    """A raising primitive is fully swallowed — _surface_drive never propagates."""
    def _boom(_pid):
        raise RuntimeError('delegation blew up')

    monkeypatch.setattr(_core, '_drive_bind', _boom)

    # Must NOT raise — the seam is best-effort and self-guarding.
    _core._surface_drive('seam-plan')


def test_drive_bind_and_repaint_target_correct_verbs(monkeypatch):
    """_drive_bind -> session bind; _drive_repaint -> session push-title-token (NO --icon)."""
    calls = []
    monkeypatch.setattr(_core, '_run_executor', lambda notation, *args: calls.append((notation, args)))

    _core._drive_bind('bind-plan')
    _core._drive_repaint('paint-plan')

    assert calls[0] == (
        'plan-marshall:platform-runtime:platform_runtime',
        ('session', 'bind', '--plan-id', 'bind-plan'),
    )
    assert calls[1] == (
        'plan-marshall:platform-runtime:platform_runtime',
        ('session', 'push-title-token', '--plan-id', 'paint-plan'),
    ), 'repaint must push with NO --icon (plain repaint, default active icon)'
    assert '--icon' not in calls[1][1], 'the repaint seam must never pass --icon (Defect 1 plain repaint)'
