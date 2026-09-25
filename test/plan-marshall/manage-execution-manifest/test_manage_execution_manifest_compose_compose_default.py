# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    DEFAULT_PHASE_5_STEPS,
    DEFAULT_PHASE_6_STEPS,
    Namespace,
    cmd_compose,
    read_manifest,
)


def test_compose_default_phase_6_steps_when_csv_omitted(plan_context):
    """When --phase-6-steps is None, DEFAULT_PHASE_6_STEPS is used."""
    cmd_compose(
        Namespace(
            plan_id='matrix-default-csv',
            change_type='feature',
            track='complex',
            scope_estimate='multi_module',
            recipe_key=None,
            affected_files_count=12,
            phase_5_steps=None,  # Falls back to DEFAULT_PHASE_5_STEPS.
            phase_6_steps=None,  # Falls back to DEFAULT_PHASE_6_STEPS.
            commit_and_push=None,
        )
    )
    manifest = read_manifest('matrix-default-csv')
    assert manifest is not None
    assert manifest['phase_5']['verification_steps'] == list(DEFAULT_PHASE_5_STEPS)
    assert manifest['phase_6']['steps'] == list(DEFAULT_PHASE_6_STEPS)
