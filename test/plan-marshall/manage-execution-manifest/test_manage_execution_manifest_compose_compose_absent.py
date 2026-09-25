# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _compose_ns, cmd_compose

# --- compose integration -----------------------------------------------------


def test_compose_absent_profile_defaults_to_full_no_pruning(plan_context):
    """A plan with no execution_profile composes as full — the back-compat no-prune path."""
    result = cmd_compose(_compose_ns(plan_id='lane-absent-profile'))

    assert result is not None
    assert result['execution_profile'] == 'full'
    assert result['lane_dropped'] == []
    assert result['lane_warnings'] == []
