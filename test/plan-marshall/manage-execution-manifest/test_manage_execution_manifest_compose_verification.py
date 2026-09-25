# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    cmd_compose,
    read_manifest,
)

# =============================================================================
# Bundle-self-modification tests removed
#
# The ``bundle_self_modification`` stacked rule is retired — the project-local
# ``project:finalize-step-sync-plugin-cache`` step (order 85) runs after
# ``project:finalize-step-deploy-target`` (order 81) in the post-merge band of
# the canonical Phase 6 ordering, which subsumes the rule's job. Tests pinning
# the removed rule are deleted with the rule itself.
# =============================================================================


def test_verification_no_files_keeps_full_phase_5_trims_phase_6(plan_context):
    """Row 6 — verification w/o files: full Phase 5, Phase 6 trimmed to records+archive."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-vnofiles',
            change_type='verification',
            scope_estimate='none',
            affected_files_count=0,
            phase_5_steps='quality-gate,module-tests,coverage',
        )
    )
    assert result is not None and result['rule_fired'] == 'verification_no_files'
    manifest = read_manifest('matrix-vnofiles')
    assert manifest is not None
    assert manifest['phase_5']['verification_steps'] == ['quality-gate', 'module-tests', 'coverage']
    assert set(manifest['phase_6']['steps']) == {'lessons-capture', 'adr-propose', 'archive-plan'}
