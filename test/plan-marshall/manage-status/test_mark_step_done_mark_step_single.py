# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done, read_status


def test_mark_step_single_firing_writes_the_historical_record_shape(plan_context):
    """One firing produces a byte-identical historical entry — no new keys.

    The matched negative control for the test above: without it, an
    unconditional history stamp would satisfy the positive assertions while
    changing every record in the corpus.
    """
    plan_id = 'mark-step-firings-one'
    _make_plan(plan_id)

    cmd_mark_step_done(_args(plan_id, '6-finalize', 'push', 'done', display_detail='pushed'))

    entry = read_status(plan_id)['metadata']['phase_steps']['6-finalize']['push']
    assert entry == {'outcome': 'done', 'display_detail': 'pushed'}
    assert 'firing_count' not in entry
    assert 'prior_firings' not in entry
