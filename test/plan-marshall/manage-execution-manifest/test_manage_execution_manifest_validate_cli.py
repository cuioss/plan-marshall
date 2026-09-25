# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_validate_fixtures import (
    DEFAULT_PHASE_5_STEPS,
    DEFAULT_PHASE_6_STEPS,
    SCRIPT_PATH,
    run_script,
)

# =============================================================================
# CLI plumbing (subprocess) tests for validate
# =============================================================================


def test_cli_validate_happy_path(plan_context):
    """validate via CLI returns status=success TOON."""
    compose = run_script(
        SCRIPT_PATH,
        'compose',
        '--plan-id',
        'cli-val-ok',
        '--plan-change-type',
        'feature',
        '--track',
        'complex',
        '--scope-estimate',
        'multi_module',
    )
    assert compose.success

    result = run_script(
        SCRIPT_PATH,
        'validate',
        '--plan-id',
        'cli-val-ok',
        '--phase-5-steps',
        ','.join(DEFAULT_PHASE_5_STEPS),
        '--phase-6-steps',
        ','.join(DEFAULT_PHASE_6_STEPS),
    )
    assert result.success
    data = result.toon()
    assert data['status'] == 'success'
    # TOON parser may coerce booleans — accept both shapes defensively.
    assert data['valid'] in (True, 'true', 1)
