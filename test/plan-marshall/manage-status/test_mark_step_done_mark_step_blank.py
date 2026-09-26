# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done, pytest


@pytest.mark.parametrize('phase', ['1-init', '5-execute'], ids=['init', 'execute'])
def test_mark_step_blank_display_detail_allowed_outside_finalize(plan_context, phase):
    """The narrative requirement is scoped to 6-finalize; other phases keep optional details."""
    plan_id = f'mark-step-detail-optional-{phase}'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, phase, 'step-a', 'done'))

    assert result['status'] == 'success'
