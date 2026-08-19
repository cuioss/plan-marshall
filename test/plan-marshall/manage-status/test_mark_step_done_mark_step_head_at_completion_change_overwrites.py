#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the mark-step-done subcommand of manage-status."""


from _mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done, read_status, write_status


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
    # A HEAD-only refresh is a re-fire of the same outcome, so the trail records
    # the superseded `done` — the outcome repeats, the firing does not.
    assert persisted['metadata']['phase_steps']['6-finalize']['pre-push-quality-gate'] == {
        'outcome': 'done',
        'display_detail': 'gate green',
        'head_at_completion': sha_new,
        'firing_count': 2,
        'prior_firings': [{'outcome': 'done'}],
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
# Step-key canonicalization
#
# The canonicalizer's own unit coverage (default strip, project/bundle preserve,
# idempotence) lives in test_step_key_canonical.py — the shared resolver's home.
# These cases assert the mark-step-done BOUNDARY behaviour: a prefixed --step is
# recorded under the canonical key computed by the shared resolver.
# =============================================================================


def test_mark_step_default_prefixed_records_under_bare_key(plan_context):
    """A ``default:``-prefixed --step is recorded under the bare manifest key.

    Recording under the caller's ``default:``-prefixed spelling must not orphan
    the record from the bare-keyed dispatcher reader, which would leave the step
    done on disk and invisible to the reader that checks whether it is done. The
    canonicalized key MUST be the bare name.
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
    # ``project:finalize-step-plugin-doctor`` declares ``head_dependent: true``,
    # so a ``done`` record must carry the anchor. What this test pins is the KEY
    # the record lands under, not the anchor — supplying it is what lets the call
    # reach the write at all.
    sha = 'c' * 40
    result = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'project:finalize-step-plugin-doctor',
            'done',
            head_at_completion=sha,
        )
    )

    assert result['status'] == 'success'
    assert result['step'] == 'project:finalize-step-plugin-doctor'

    persisted = read_status(plan_id)
    phase_steps = persisted['metadata']['phase_steps']['6-finalize']
    assert phase_steps == {
        'project:finalize-step-plugin-doctor': {
            'outcome': 'done',
            'display_detail': None,
            'head_at_completion': sha,
        }
    }


# =============================================================================
# Stale legacy-key duplicate migration
#
# A pre-migration run may have persisted a ``default:``-prefixed key directly.
# A later canonical write must locate that stale key via the canonicalized
# fallback scan (so the conflict check fires against the true existing outcome)
# AND pop it on write, so a legacy-vs-canonical duplicate never survives.
# =============================================================================


def test_mark_step_migrates_stale_legacy_key_on_detail_refresh(plan_context):
    """A detail-refresh write over a stale ``default:push`` key pops the legacy key.

    ``get('push')`` must not miss the pre-migration ``default:push`` key; if it
    does, the write adds a NEW ``push`` key alongside the OLD ``default:push``.
    The duplicate is what breaks: the dispatcher reads the bare key and sees a
    fresh first firing, while the conflict check reads the stale one, so the two
    disagree about whether the step ever ran. The canonicalized fallback scan
    finds the stale key and the write pops it — exactly one canonical entry
    survives.
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
    # Exactly one entry under the bare key — the stale legacy key was popped —
    # and the migrated entry retains the firing it superseded.
    assert phase_steps == {
        'push': {
            'outcome': 'done',
            'display_detail': 'new',
            'firing_count': 2,
            'prior_firings': [{'outcome': 'done'}],
        }
    }
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
