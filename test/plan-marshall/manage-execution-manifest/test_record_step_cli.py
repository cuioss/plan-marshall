# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_record_step_fixtures import SCRIPT_PATH, run_script

# =============================================================================
# CLI plumbing (subprocess) tests
# =============================================================================


def test_cli_record_step_roundtrip(plan_context):
    """record-step over the CLI appends a row and echoes the success TOON."""
    # compose a manifest via the CLI so the subprocess sees it.
    compose = run_script(
        SCRIPT_PATH,
        'compose',
        '--plan-id',
        'cli-rec',
        '--plan-change-type',
        'feature',
        '--track',
        'complex',
        '--scope-estimate',
        'multi_module',
        '--affected-files-count',
        '5',
    )
    assert compose.returncode == 0

    result = run_script(
        SCRIPT_PATH,
        'record-step',
        '--plan-id',
        'cli-rec',
        '--step-id',
        'verify:quality-gate',
        '--phase',
        '5-execute',
        '--outcome',
        'executed',
        '--total-tokens',
        '1500',
        '--tool-uses',
        '4',
        '--duration-ms',
        '2200',
    )

    assert result.returncode == 0
    data = result.toon()
    assert data['status'] == 'success'
    assert data['recorded'] is True
    assert data['step_id'] == 'verify:quality-gate'
    assert data['outcome'] == 'executed'
    assert data['total_tokens'] == 1500
    assert data['tool_uses'] == 4
    assert data['duration_ms'] == 2200
    assert data['execution_log_count'] == 1



def test_cli_record_step_missing_manifest_emits_toon_error(plan_context):
    """record-step over the CLI without a manifest emits file_not_found via TOON."""
    result = run_script(
        SCRIPT_PATH,
        'record-step',
        '--plan-id',
        'cli-rec-missing',
        '--step-id',
        'verify:quality-gate',
        '--phase',
        '5-execute',
        '--outcome',
        'executed',
    )

    # TOON contract: script exits 0 on missing-file errors.
    assert result.returncode == 0
    data = result.toon()
    assert data['status'] == 'error'
    assert data['error'] == 'file_not_found'
