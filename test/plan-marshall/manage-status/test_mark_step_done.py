#!/usr/bin/env python3
"""Tests for the mark-step-done subcommand of manage-status."""

import importlib.util
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import PlanContext

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-status'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_lifecycle = _load_module('_mark_step_lifecycle', '_cmd_lifecycle.py')
_mark_step = _load_module('_mark_step_cmd', '_cmd_mark_step.py')
_status_core = _load_module('_mark_step_core', '_status_core.py')

cmd_create = _lifecycle.cmd_create
cmd_mark_step_done = _mark_step.cmd_mark_step_done
read_status = _status_core.read_status
write_status = _status_core.write_status


def _make_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Mark Step Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def _args(
    plan_id: str,
    phase: str,
    step: str,
    outcome: str,
    force: bool = False,
    display_detail: str | None = None,
    head_at_completion: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        step=step,
        outcome=outcome,
        force=force,
        display_detail=display_detail,
        head_at_completion=head_at_completion,
    )


# =============================================================================
# Happy path
# =============================================================================


def test_mark_step_done_happy_path():
    """Mark a new step done; persists dict-shaped entry under metadata.phase_steps."""
    plan_id = 'mark-step-happy'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        result = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done'))

        assert result['status'] == 'success'
        assert result['changed'] is True
        assert result['previous_outcome'] is None
        assert result['previous_display_detail'] is None
        assert result['phase'] == '1-init'
        assert result['step'] == 'step-a'
        assert result['outcome'] == 'done'
        assert result['display_detail'] is None

        persisted = read_status(plan_id)
        assert persisted['metadata']['phase_steps']['1-init']['step-a'] == {
            'outcome': 'done',
            'display_detail': None,
        }


def test_mark_step_skipped_happy_path():
    """Outcome 'skipped' persists as dict with null display_detail."""
    plan_id = 'mark-step-skipped'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        result = cmd_mark_step_done(_args(plan_id, '2-refine', 'clarify', 'skipped'))

        assert result['status'] == 'success'
        assert result['changed'] is True
        assert result['outcome'] == 'skipped'
        assert result['display_detail'] is None

        persisted = read_status(plan_id)
        assert persisted['metadata']['phase_steps']['2-refine']['clarify'] == {
            'outcome': 'skipped',
            'display_detail': None,
        }


def test_mark_step_persists_display_detail():
    """--display-detail value is stored alongside the outcome."""
    plan_id = 'mark-step-detail'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        result = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done', display_detail='my detail'))

        assert result['status'] == 'success'
        assert result['changed'] is True
        assert result['display_detail'] == 'my detail'

        persisted = read_status(plan_id)
        assert persisted['metadata']['phase_steps']['1-init']['step-a'] == {
            'outcome': 'done',
            'display_detail': 'my detail',
        }


def test_mark_step_absent_flag_persists_null_detail():
    """Omitting --display-detail persists display_detail=None."""
    plan_id = 'mark-step-no-detail'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        result = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done'))

        assert result['display_detail'] is None
        persisted = read_status(plan_id)
        assert persisted['metadata']['phase_steps']['1-init']['step-a']['display_detail'] is None


# =============================================================================
# Idempotency
# =============================================================================


def test_mark_step_done_idempotent_on_identical_outcome_and_detail():
    """Marking same step with same outcome AND same detail is a no-op."""
    plan_id = 'mark-step-idempotent'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done', display_detail='detail-a'))

        persisted_before = read_status(plan_id)
        updated_before = persisted_before['updated']

        second = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done', display_detail='detail-a'))

        assert second['status'] == 'success'
        assert second['changed'] is False
        assert 'previous_outcome' not in second

        persisted_after = read_status(plan_id)
        # No file rewrite: updated timestamp unchanged.
        assert persisted_after['updated'] == updated_before
        assert persisted_after['metadata']['phase_steps']['1-init']['step-a'] == {
            'outcome': 'done',
            'display_detail': 'detail-a',
        }


def test_mark_step_detail_only_update_rewrites_entry():
    """Same outcome + different detail overwrites the detail and reports changed=True."""
    plan_id = 'mark-step-detail-update'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done', display_detail='a'))

        second = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done', display_detail='b'))

        assert second['status'] == 'success'
        assert second['changed'] is True
        assert second['outcome'] == 'done'
        assert second['display_detail'] == 'b'
        assert second['previous_outcome'] == 'done'
        assert second['previous_display_detail'] == 'a'

        persisted = read_status(plan_id)
        assert persisted['metadata']['phase_steps']['1-init']['step-a'] == {
            'outcome': 'done',
            'display_detail': 'b',
        }


# =============================================================================
# Conflict handling
# =============================================================================


def test_mark_step_conflict_without_force():
    """Different outcome on existing step without --force returns conflict error."""
    plan_id = 'mark-step-conflict'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done', display_detail='keep'))

        result = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'skipped'))

        assert result['status'] == 'error'
        assert result['error'] == 'conflict'
        assert result['existing_outcome'] == 'done'
        assert result['requested_outcome'] == 'skipped'
        assert result['phase'] == '1-init'
        assert result['step'] == 'step-a'

        # Persistence unchanged — existing detail still in place.
        persisted = read_status(plan_id)
        assert persisted['metadata']['phase_steps']['1-init']['step-a'] == {
            'outcome': 'done',
            'display_detail': 'keep',
        }


def test_mark_step_force_overwrites():
    """With --force, a differing outcome overwrites and reports previous_outcome."""
    plan_id = 'mark-step-force'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done', display_detail='old'))

        result = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'skipped', force=True, display_detail='new'))

        assert result['status'] == 'success'
        assert result['changed'] is True
        assert result['previous_outcome'] == 'done'
        assert result['previous_display_detail'] == 'old'
        assert result['outcome'] == 'skipped'
        assert result['display_detail'] == 'new'

        persisted = read_status(plan_id)
        assert persisted['metadata']['phase_steps']['1-init']['step-a'] == {
            'outcome': 'skipped',
            'display_detail': 'new',
        }


# =============================================================================
# Legacy bare-string rejection
# =============================================================================


def test_mark_step_rejects_legacy_bare_string_entry():
    """A seeded bare-string entry must be rejected with legacy_string_entry error."""
    plan_id = 'mark-step-legacy'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        status = read_status(plan_id)
        status.setdefault('metadata', {})['phase_steps'] = {'1-init': {'step-a': 'done'}}
        write_status(plan_id, status)

        result = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done', display_detail='ignored'))

        assert result['status'] == 'error'
        assert result['error'] == 'legacy_string_entry'
        assert result['existing_outcome'] == 'done'
        assert result['requested_outcome'] == 'done'
        assert result['phase'] == '1-init'
        assert result['step'] == 'step-a'

        persisted = read_status(plan_id)
        assert persisted['metadata']['phase_steps']['1-init']['step-a'] == 'done'


# =============================================================================
# Multi-phase / multi-step coexistence
# =============================================================================


def test_mark_step_multi_phase_and_multi_step():
    """Independent phases and steps should coexist in phase_steps."""
    plan_id = 'mark-step-multi'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)

        cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done'))
        cmd_mark_step_done(_args(plan_id, '1-init', 'step-b', 'skipped'))
        cmd_mark_step_done(_args(plan_id, '2-refine', 'clarify', 'done', display_detail='clarified'))
        cmd_mark_step_done(_args(plan_id, '3-outline', 'draft', 'done'))

        persisted = read_status(plan_id)
        phase_steps = persisted['metadata']['phase_steps']

        assert phase_steps['1-init'] == {
            'step-a': {'outcome': 'done', 'display_detail': None},
            'step-b': {'outcome': 'skipped', 'display_detail': None},
        }
        assert phase_steps['2-refine'] == {
            'clarify': {'outcome': 'done', 'display_detail': 'clarified'},
        }
        assert phase_steps['3-outline'] == {
            'draft': {'outcome': 'done', 'display_detail': None},
        }


# =============================================================================
# Error paths
# =============================================================================


def test_mark_step_missing_plan():
    """Missing plan: require_status emits TOON and returns None."""
    with PlanContext():
        result = cmd_mark_step_done(_args('nonexistent-plan', '1-init', 'step-a', 'done'))
        assert result is None


def test_mark_step_invalid_outcome():
    """Invalid outcome value returns invalid_outcome error without writing."""
    plan_id = 'mark-step-bad-outcome'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        result = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'bogus'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_outcome'

        persisted = read_status(plan_id)
        assert 'phase_steps' not in persisted.get('metadata', {})


def test_mark_step_empty_phase():
    """Empty phase is rejected with invalid_argument."""
    plan_id = 'mark-step-empty-phase'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        result = cmd_mark_step_done(_args(plan_id, '', 'step-a', 'done'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_argument'


def test_mark_step_empty_step():
    """Empty step is rejected with invalid_argument."""
    plan_id = 'mark-step-empty-step'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        result = cmd_mark_step_done(_args(plan_id, '1-init', '', 'done'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_argument'


def test_mark_step_invalid_plan_id():
    """Invalid plan_id format triggers require_valid_plan_id exit."""
    with PlanContext():
        with pytest.raises(SystemExit):
            cmd_mark_step_done(_args('Invalid_Plan', '1-init', 'step-a', 'done'))


# =============================================================================
# head_at_completion field
# =============================================================================


def test_mark_step_persists_head_at_completion_on_first_call():
    """--head-at-completion is persisted as a third key alongside outcome+display_detail."""
    plan_id = 'mark-step-head-first'
    sha = 'abc1234567890abcdef1234567890abcdef1234'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        result = cmd_mark_step_done(
            _args(
                plan_id,
                '6-finalize',
                'pre-push-quality-gate',
                'done',
                head_at_completion=sha,
            )
        )

        assert result['status'] == 'success'
        assert result['changed'] is True
        assert result['head_at_completion'] == sha
        assert result['outcome'] == 'done'
        assert result['display_detail'] is None

        persisted = read_status(plan_id)
        assert persisted['metadata']['phase_steps']['6-finalize']['pre-push-quality-gate'] == {
            'outcome': 'done',
            'display_detail': None,
            'head_at_completion': sha,
        }


def test_mark_step_idempotent_when_head_at_completion_matches():
    """Re-call with same outcome+display_detail+head_at_completion is a no-op."""
    plan_id = 'mark-step-head-idempotent'
    sha = 'deadbeefcafebabe0123456789abcdef01234567'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        cmd_mark_step_done(
            _args(
                plan_id,
                '6-finalize',
                'pre-push-quality-gate',
                'done',
                display_detail='gate green',
                head_at_completion=sha,
            )
        )

        persisted_before = read_status(plan_id)
        updated_before = persisted_before['updated']

        second = cmd_mark_step_done(
            _args(
                plan_id,
                '6-finalize',
                'pre-push-quality-gate',
                'done',
                display_detail='gate green',
                head_at_completion=sha,
            )
        )

        assert second['status'] == 'success'
        assert second['changed'] is False
        assert second['head_at_completion'] == sha
        assert 'previous_outcome' not in second

        persisted_after = read_status(plan_id)
        # No file rewrite: updated timestamp unchanged.
        assert persisted_after['updated'] == updated_before
        assert persisted_after['metadata']['phase_steps']['6-finalize']['pre-push-quality-gate'] == {
            'outcome': 'done',
            'display_detail': 'gate green',
            'head_at_completion': sha,
        }


def test_mark_step_head_at_completion_change_overwrites_without_force():
    """Re-call with same outcome+display_detail but different SHA is a 'changed' overwrite, no --force."""
    plan_id = 'mark-step-head-overwrite'
    sha_old = '1111111111111111111111111111111111111111'
    sha_new = '2222222222222222222222222222222222222222'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        cmd_mark_step_done(
            _args(
                plan_id,
                '6-finalize',
                'pre-push-quality-gate',
                'done',
                display_detail='gate green',
                head_at_completion=sha_old,
            )
        )

        # Same outcome and display_detail, different SHA, no --force.
        second = cmd_mark_step_done(
            _args(
                plan_id,
                '6-finalize',
                'pre-push-quality-gate',
                'done',
                display_detail='gate green',
                head_at_completion=sha_new,
            )
        )

        assert second['status'] == 'success'
        assert second['changed'] is True
        assert second['outcome'] == 'done'
        assert second['display_detail'] == 'gate green'
        assert second['head_at_completion'] == sha_new
        assert second['previous_outcome'] == 'done'
        assert second['previous_display_detail'] == 'gate green'
        assert second['previous_head_at_completion'] == sha_old

        persisted = read_status(plan_id)
        assert persisted['metadata']['phase_steps']['6-finalize']['pre-push-quality-gate'] == {
            'outcome': 'done',
            'display_detail': 'gate green',
            'head_at_completion': sha_new,
        }


def test_mark_step_omits_head_at_completion_key_when_flag_absent():
    """Caller omitting --head-at-completion produces the legacy two-key dict shape."""
    plan_id = 'mark-step-head-omitted'
    with PlanContext(plan_id=plan_id):
        _make_plan(plan_id)
        result = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done', display_detail='legacy'))

        assert result['status'] == 'success'
        assert result['changed'] is True
        # Result echoes the field as None, but persistence omits the key entirely.
        assert result['head_at_completion'] is None

        persisted = read_status(plan_id)
        entry = persisted['metadata']['phase_steps']['1-init']['step-a']
        assert entry == {'outcome': 'done', 'display_detail': 'legacy'}
        assert 'head_at_completion' not in entry
