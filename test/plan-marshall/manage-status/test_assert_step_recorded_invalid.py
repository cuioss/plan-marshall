# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_assert_step_recorded_fixtures import _assert_args, cmd_assert_step_recorded, pytest


def test_invalid_plan_id_raises_system_exit(plan_context):
    """Invalid plan_id format triggers require_valid_plan_id exit."""
    with pytest.raises(SystemExit):
        cmd_assert_step_recorded(_assert_args('Invalid_Plan', '1-init', 'step-a'))
