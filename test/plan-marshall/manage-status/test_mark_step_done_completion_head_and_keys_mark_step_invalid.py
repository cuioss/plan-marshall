# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_mark_step_done_completion_head_and_keys_fixtures import _args, cmd_mark_step_done, pytest


def test_mark_step_invalid_plan_id(plan_context):
    """Invalid plan_id format triggers require_valid_plan_id exit."""
    with pytest.raises(SystemExit):
        cmd_mark_step_done(_args('Invalid_Plan', '1-init', 'step-a', 'done'))
