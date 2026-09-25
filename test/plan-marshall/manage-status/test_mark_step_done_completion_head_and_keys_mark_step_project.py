# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_mark_step_done_completion_head_and_keys_fixtures import (
    _args,
    _make_plan,
    _real_head,
    cmd_mark_step_done,
    read_status,
)


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
    sha = _real_head()
    result = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'project:finalize-step-plugin-doctor',
            'done',
            display_detail='test detail',
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
            'display_detail': 'test detail',
            'head_at_completion': sha,
        }
    }
