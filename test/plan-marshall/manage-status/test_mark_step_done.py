#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the mark-step-done subcommand of manage-status."""

from argparse import Namespace

import pytest

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_mark_step_lifecycle')
_mark_step = load_script_module('plan-marshall', 'manage-status', '_cmd_mark_step.py', '_mark_step_cmd')
_status_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_mark_step_core')

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
    loop_back_target: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        step=step,
        outcome=outcome,
        force=force,
        display_detail=display_detail,
        head_at_completion=head_at_completion,
        loop_back_target=loop_back_target,
    )


# =============================================================================
# Happy path
# =============================================================================


def test_mark_step_done_happy_path(plan_context):
    """Mark a new step done; persists dict-shaped entry under metadata.phase_steps."""
    plan_id = 'mark-step-happy'
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


def test_mark_step_skipped_happy_path(plan_context):
    """Outcome 'skipped' persists as dict with null display_detail."""
    plan_id = 'mark-step-skipped'
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


def test_mark_step_failed_happy_path(plan_context):
    """Outcome 'failed' persists as dict with null display_detail.

    Regression guard for PR #338 review (gemini-code-assist findings 0d1782 and
    f9c054): the phase-6-finalize dispatcher's graceful timeout degradation
    path uses ``--outcome failed`` (see SKILL.md and automatic-review.md
    Timeout Contract), so ``failed`` MUST be a valid persisted outcome.
    """
    plan_id = 'mark-step-failed'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '6-finalize', 'automatic-review', 'failed'))

    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['outcome'] == 'failed'
    assert result['display_detail'] is None

    persisted = read_status(plan_id)
    assert persisted['metadata']['phase_steps']['6-finalize']['automatic-review'] == {
        'outcome': 'failed',
        'display_detail': None,
    }


def test_mark_step_failed_with_display_detail(plan_context):
    """Outcome 'failed' carries a display_detail describing the failure cause."""
    plan_id = 'mark-step-failed-detail'
    _make_plan(plan_id)
    result = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'automatic-review',
            'failed',
            display_detail='timeout after 1800s',
        )
    )

    assert result['status'] == 'success'
    assert result['outcome'] == 'failed'
    assert result['display_detail'] == 'timeout after 1800s'

    persisted = read_status(plan_id)
    assert persisted['metadata']['phase_steps']['6-finalize']['automatic-review'] == {
        'outcome': 'failed',
        'display_detail': 'timeout after 1800s',
    }


def test_mark_step_persists_display_detail(plan_context):
    """--display-detail value is stored alongside the outcome."""
    plan_id = 'mark-step-detail'
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


def test_mark_step_absent_flag_persists_null_detail(plan_context):
    """Omitting --display-detail persists display_detail=None."""
    plan_id = 'mark-step-no-detail'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done'))

    assert result['display_detail'] is None
    persisted = read_status(plan_id)
    assert persisted['metadata']['phase_steps']['1-init']['step-a']['display_detail'] is None


# =============================================================================
# Idempotency
# =============================================================================


def test_mark_step_done_idempotent_on_identical_outcome_and_detail(plan_context):
    """Marking same step with same outcome AND same detail is a no-op."""
    plan_id = 'mark-step-idempotent'
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


def test_mark_step_detail_only_update_rewrites_entry(plan_context):
    """Same outcome + different detail overwrites the detail and reports changed=True."""
    plan_id = 'mark-step-detail-update'
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


def test_mark_step_conflict_without_force(plan_context):
    """Different outcome on existing step without --force returns conflict error."""
    plan_id = 'mark-step-conflict'
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


def test_mark_step_force_overwrites(plan_context):
    """With --force, a differing outcome overwrites and reports previous_outcome."""
    plan_id = 'mark-step-force'
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


def test_mark_step_rejects_legacy_bare_string_entry(plan_context):
    """A seeded bare-string entry must be rejected with legacy_string_entry error."""
    plan_id = 'mark-step-legacy'
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


def test_mark_step_multi_phase_and_multi_step(plan_context):
    """Independent phases and steps should coexist in phase_steps."""
    plan_id = 'mark-step-multi'
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


def test_mark_step_missing_plan(plan_context):
    """Missing plan: require_status emits TOON and returns None."""
    result = cmd_mark_step_done(_args('nonexistent-plan', '1-init', 'step-a', 'done'))
    assert result is None


def test_mark_step_invalid_outcome(plan_context):
    """Invalid outcome value returns invalid_outcome error without writing."""
    plan_id = 'mark-step-bad-outcome'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'bogus'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_outcome'

    persisted = read_status(plan_id)
    assert 'phase_steps' not in persisted.get('metadata', {})


def test_mark_step_failed_idempotent(plan_context):
    """Re-marking a step 'failed' with same detail is a no-op (changed=False)."""
    plan_id = 'mark-step-failed-idempotent'
    _make_plan(plan_id)
    cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'automatic-review', 'failed', display_detail='timeout')
    )

    second = cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'automatic-review', 'failed', display_detail='timeout')
    )

    assert second['status'] == 'success'
    assert second['changed'] is False
    assert second['outcome'] == 'failed'


def test_mark_step_failed_then_done_with_force(plan_context):
    """After a 'failed' marker, dispatcher can re-fire and overwrite with 'done' under --force."""
    plan_id = 'mark-step-failed-then-done'
    _make_plan(plan_id)
    cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'automatic-review', 'failed', display_detail='timeout')
    )

    # Without --force, a different outcome on an existing step is a conflict.
    conflict = cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'automatic-review', 'done', display_detail='retry green')
    )
    assert conflict['status'] == 'error'
    assert conflict['error'] == 'conflict'
    assert conflict['existing_outcome'] == 'failed'
    assert conflict['requested_outcome'] == 'done'

    # With --force, the retry overwrite succeeds.
    retry = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'automatic-review',
            'done',
            force=True,
            display_detail='retry green',
        )
    )
    assert retry['status'] == 'success'
    assert retry['changed'] is True
    assert retry['outcome'] == 'done'
    assert retry['previous_outcome'] == 'failed'

    persisted = read_status(plan_id)
    assert persisted['metadata']['phase_steps']['6-finalize']['automatic-review'] == {
        'outcome': 'done',
        'display_detail': 'retry green',
    }


def test_mark_step_empty_phase(plan_context):
    """Empty phase is rejected with invalid_argument."""
    plan_id = 'mark-step-empty-phase'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '', 'step-a', 'done'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_argument'


def test_mark_step_empty_step(plan_context):
    """Empty step is rejected with invalid_argument."""
    plan_id = 'mark-step-empty-step'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '1-init', '', 'done'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_argument'


def test_mark_step_invalid_plan_id(plan_context):
    """Invalid plan_id format triggers require_valid_plan_id exit."""
    with pytest.raises(SystemExit):
        cmd_mark_step_done(_args('Invalid_Plan', '1-init', 'step-a', 'done'))


# =============================================================================
# head_at_completion field
# =============================================================================


def test_mark_step_persists_head_at_completion_on_first_call(plan_context):
    """--head-at-completion is persisted as a third key alongside outcome+display_detail."""
    plan_id = 'mark-step-head-first'
    sha = 'abc1234567890abcdef1234567890abcdef1234'
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


def test_mark_step_idempotent_when_head_at_completion_matches(plan_context):
    """Re-call with same outcome+display_detail+head_at_completion is a no-op."""
    plan_id = 'mark-step-head-idempotent'
    sha = 'deadbeefcafebabe0123456789abcdef01234567'
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


def test_mark_step_head_at_completion_change_overwrites_without_force(plan_context):
    """Re-call with same outcome+display_detail but different SHA is a 'changed' overwrite, no --force."""
    plan_id = 'mark-step-head-overwrite'
    sha_old = '1111111111111111111111111111111111111111'
    sha_new = '2222222222222222222222222222222222222222'
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


def test_mark_step_omits_head_at_completion_key_when_flag_absent(plan_context):
    """Caller omitting --head-at-completion produces the legacy two-key dict shape."""
    plan_id = 'mark-step-head-omitted'
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


# =============================================================================
# Step-key canonicalization (lesson 2026-06-21-00-002)
#
# The canonicalizer's own unit coverage (default strip, project/bundle preserve,
# idempotence) lives in test_step_key_canonical.py — the shared resolver's home.
# These cases assert the mark-step-done BOUNDARY behaviour: a prefixed --step is
# recorded under the canonical key computed by the shared resolver.
# =============================================================================


def test_mark_step_default_prefixed_records_under_bare_key(plan_context):
    """A ``default:``-prefixed --step is recorded under the bare manifest key.

    Regression guard for lesson 2026-06-21-00-002: recording under the caller's
    ``default:``-prefixed spelling orphaned the record from the bare-keyed
    dispatcher reader. The canonicalized key MUST be the bare name.
    """
    plan_id = 'mark-step-canon-prefixed'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '6-finalize', 'default:push', 'done'))

    assert result['status'] == 'success'
    # The returned step echoes the canonical bare key, not the prefixed input.
    assert result['step'] == 'push'

    persisted = read_status(plan_id)
    phase_steps = persisted['metadata']['phase_steps']['6-finalize']
    assert phase_steps == {'push': {'outcome': 'done', 'display_detail': None}}
    assert 'default:push' not in phase_steps


def test_mark_step_bare_and_default_prefixed_reconcile_to_same_key(plan_context):
    """Recording via ``default:push`` then via ``push`` reconciles to ONE bare entry.

    Both spellings resolve to the same bare manifest key, so the second call is a
    no-op on the same record rather than creating a divergent orphan.
    """
    plan_id = 'mark-step-canon-reconcile'
    _make_plan(plan_id)
    first = cmd_mark_step_done(_args(plan_id, '6-finalize', 'default:push', 'done'))
    assert first['status'] == 'success'
    assert first['changed'] is True

    # Same step, bare spelling, same outcome — idempotent no-op on the SAME entry.
    second = cmd_mark_step_done(_args(plan_id, '6-finalize', 'push', 'done'))
    assert second['status'] == 'success'
    assert second['changed'] is False
    assert second['step'] == 'push'

    persisted = read_status(plan_id)
    phase_steps = persisted['metadata']['phase_steps']['6-finalize']
    # Exactly one entry under the bare key — no divergent default:-prefixed orphan.
    assert list(phase_steps.keys()) == ['push']


def test_mark_step_project_prefixed_records_under_verbatim_key(plan_context):
    """A ``project:``-prefixed --step records under its verbatim key.

    The shared canonicalizer preserves ``project:`` / ``bundle:skill`` ids, so a
    project-local finalize step keeps its prefix (it is NOT stripped to bare).
    """
    plan_id = 'mark-step-canon-project'
    _make_plan(plan_id)
    result = cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'project:finalize-step-plugin-doctor', 'done')
    )

    assert result['status'] == 'success'
    assert result['step'] == 'project:finalize-step-plugin-doctor'

    persisted = read_status(plan_id)
    phase_steps = persisted['metadata']['phase_steps']['6-finalize']
    assert phase_steps == {
        'project:finalize-step-plugin-doctor': {'outcome': 'done', 'display_detail': None}
    }


# =============================================================================
# Stale legacy-key duplicate migration (PR #961 shadowing defect)
#
# A pre-migration run may have persisted a ``default:``-prefixed key directly.
# A later canonical write must locate that stale key via the canonicalized
# fallback scan (so the conflict check fires against the true existing outcome)
# AND pop it on write, so a legacy-vs-canonical duplicate never survives.
# =============================================================================


def test_mark_step_migrates_stale_legacy_key_on_detail_refresh(plan_context):
    """A detail-refresh write over a stale ``default:push`` key pops the legacy key.

    Regression for PR #961: before the fix, ``get('push')`` missed the
    pre-migration ``default:push`` key, so the write added a NEW ``push`` key
    alongside the OLD ``default:push``, leaving a duplicate. The canonicalized
    fallback scan now finds the stale key and the write pops it — exactly one
    canonical entry survives.
    """
    plan_id = 'mark-step-legacy-migrate'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'default:push': {'outcome': 'done', 'display_detail': 'old'}}
    }
    write_status(plan_id, status)

    result = cmd_mark_step_done(_args(plan_id, '6-finalize', 'push', 'done', display_detail='new'))

    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['step'] == 'push'
    assert result['previous_display_detail'] == 'old'

    persisted = read_status(plan_id)
    phase_steps = persisted['metadata']['phase_steps']['6-finalize']
    # Exactly one entry under the bare key — the stale legacy key was popped.
    assert phase_steps == {'push': {'outcome': 'done', 'display_detail': 'new'}}
    assert 'default:push' not in phase_steps


def test_mark_step_conflict_fires_against_stale_legacy_key(plan_context):
    """A differing-outcome write over a stale ``default:push`` key raises conflict.

    Before the fix the stale key was invisible to ``get('push')``, so the conflict
    check was silently bypassed and a divergent duplicate was written. The fallback
    scan now surfaces the true existing outcome so the conflict fires.
    """
    plan_id = 'mark-step-legacy-conflict'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'default:push': {'outcome': 'done', 'display_detail': 'kept'}}
    }
    write_status(plan_id, status)

    result = cmd_mark_step_done(_args(plan_id, '6-finalize', 'push', 'skipped'))

    assert result['status'] == 'error'
    assert result['error'] == 'conflict'
    assert result['existing_outcome'] == 'done'
    assert result['requested_outcome'] == 'skipped'

    # No divergent duplicate written — the stale legacy entry is untouched.
    persisted = read_status(plan_id)
    phase_steps = persisted['metadata']['phase_steps']['6-finalize']
    assert phase_steps == {'default:push': {'outcome': 'done', 'display_detail': 'kept'}}
    assert 'push' not in phase_steps


def test_mark_step_force_overwrites_stale_legacy_key_without_duplicate(plan_context):
    """A ``--force`` differing-outcome write over a stale ``default:push`` key pops it.

    The final-write branch pops the located stale key before storing the new
    canonical entry, so the force overwrite leaves exactly one canonical entry.
    """
    plan_id = 'mark-step-legacy-force'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'default:push': {'outcome': 'done', 'display_detail': 'old'}}
    }
    write_status(plan_id, status)

    result = cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'push', 'skipped', force=True, display_detail='new')
    )

    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['previous_outcome'] == 'done'

    persisted = read_status(plan_id)
    phase_steps = persisted['metadata']['phase_steps']['6-finalize']
    assert phase_steps == {'push': {'outcome': 'skipped', 'display_detail': 'new'}}
    assert 'default:push' not in phase_steps
