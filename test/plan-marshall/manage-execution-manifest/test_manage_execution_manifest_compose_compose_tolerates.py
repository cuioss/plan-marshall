# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _compose_ns, cmd_compose


def test_compose_tolerates_malformed_status_json(plan_context):
    """compose still succeeds (Row 7) when status.json cannot be parsed."""
    plan_id = 'compose-malformed-status'
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text('not json at all', encoding='utf-8')
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            recipe_key=None,
            affected_files_count=4,
        )
    )
    assert result is not None and result['rule_fired'] == 'default'
