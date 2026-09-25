# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _compose_ns, cmd_compose


def test_single_module_tech_debt_with_docs_candidates_falls_to_default(plan_context):
    """The retired row also covered ``single_module`` scope; that path is gone too.

    ``single_module`` + ``tech_debt`` misses the scope row (which requires
    ``surgical``), so with no docs_only row to catch it the default row fires.
    """
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-single-mod-docs',
            change_type='tech_debt',
            scope_estimate='single_module',
            affected_files_count=4,
            phase_5_steps='verify:quality-gate',
        )
    )
    assert result is not None and result['rule_fired'] == 'default'
    assert result['phase_5']['verification_steps_count'] == 1
