#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the mark-step-done subcommand of manage-status."""


from _mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done, read_status, write_status

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

    The phase-6-finalize dispatcher's graceful timeout degradation
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
    # A detail-only refresh IS a re-fire, so the entry carries the firing trail
    # alongside the refreshed fields. `outcome` still means the LATEST firing.
    assert persisted['metadata']['phase_steps']['1-init']['step-a'] == {
        'outcome': 'done',
        'display_detail': 'b',
        'firing_count': 2,
        'prior_firings': [{'outcome': 'done'}],
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
    # The forced overwrite is a re-fire too — the superseded `done` is retained
    # rather than discarded, which is the whole point of the trail.
    assert persisted['metadata']['phase_steps']['1-init']['step-a'] == {
        'outcome': 'skipped',
        'display_detail': 'new',
        'firing_count': 2,
        'prior_firings': [{'outcome': 'done'}],
    }


# =============================================================================
# Legacy bare-string rejection (unforced) and migration (forced)
# =============================================================================


def test_mark_step_force_migrates_legacy_bare_string_preserving_prior_outcome(plan_context):
    """A forced migration retains the bare string as the FIRST prior firing.

    The bare string IS a readable firing — the unforced rejection below reports
    that very value back as ``existing_outcome`` — so dropping it on the forced
    path makes the migrated record indistinguishable from a genuine first
    firing, destroying the one fact the firing trail exists to preserve.

    ``test_mark_step_rejects_legacy_bare_string_entry`` is the matching negative
    control: the SAME seeded entry without ``--force`` still errors and writes
    nothing, so this test cannot pass by the migration branch firing everywhere.
    """
    # Arrange: seed the legacy bare-string shape.
    plan_id = 'mark-step-legacy-force-bare-string'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {'1-init': {'step-a': 'done'}}
    write_status(plan_id, status)

    # Act: force the migration to the dict shape.
    result = cmd_mark_step_done(
        _args(plan_id, '1-init', 'step-a', 'skipped', force=True, display_detail='migrated')
    )

    # Assert: the migration succeeds and the superseded bare string is retained.
    assert result['status'] == 'success'
    assert result['changed'] is True

    persisted = read_status(plan_id)
    assert persisted['metadata']['phase_steps']['1-init']['step-a'] == {
        'outcome': 'skipped',
        'display_detail': 'migrated',
        'firing_count': 2,
        'prior_firings': [{'outcome': 'done'}],
    }
