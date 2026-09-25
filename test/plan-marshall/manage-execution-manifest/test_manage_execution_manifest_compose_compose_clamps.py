# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _compose_ns, cmd_compose


def test_compose_clamps_negative_affected_files_count(plan_context):
    """Negative affected_files_count should be clamped to 0 (no crash)."""
    result = cmd_compose(
        _compose_ns(
            plan_id='val-negfiles',
            change_type='analysis',
            scope_estimate='none',
            affected_files_count=-5,
        )
    )
    # With clamp to 0, analysis+0 → early_terminate.
    assert result is not None and result['status'] == 'success'
    assert result['rule_fired'] == 'early_terminate_analysis'
