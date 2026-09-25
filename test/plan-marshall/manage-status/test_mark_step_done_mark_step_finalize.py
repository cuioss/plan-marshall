# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_mark_step_done_fixtures import (
    _args,
    _make_plan,
    cmd_mark_step_done,
    pytest,
    read_status,
)


@pytest.mark.parametrize('detail', [None, '', '   '], ids=['omitted', 'empty', 'whitespace'])
def test_mark_step_finalize_rejects_blank_display_detail(plan_context, detail):
    """A 6-finalize yield with no progress narrative is refused before persistence."""
    plan_id = 'mark-step-detail-required'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '6-finalize', 'push', 'done', display_detail=detail))

    assert result['status'] == 'error'
    assert result['error'] == 'display_detail_required'

    persisted = read_status(plan_id)
    assert 'phase_steps' not in persisted.get('metadata', {})
