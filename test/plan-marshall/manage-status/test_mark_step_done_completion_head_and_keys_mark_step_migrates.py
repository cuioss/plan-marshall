# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_mark_step_done_completion_head_and_keys_fixtures import (
    _args,
    _make_plan,
    cmd_mark_step_done,
    read_status,
    write_status,
)

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
