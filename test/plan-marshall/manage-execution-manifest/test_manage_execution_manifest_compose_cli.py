# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import SCRIPT_PATH, run_script

# =============================================================================
# CLI plumbing (subprocess) tests — keep small, just confirm wiring
# =============================================================================


def test_cli_compose_then_read_roundtrip(plan_context):
    result = run_script(
        SCRIPT_PATH,
        'compose',
        '--plan-id',
        'cli-rt',
        '--plan-change-type',
        'feature',
        '--track',
        'complex',
        '--scope-estimate',
        'multi_module',
        '--affected-files-count',
        '10',
    )
    assert result.success, f'compose failed: stderr={result.stderr!r}'
    compose_data = result.toon()
    assert compose_data['status'] == 'success'

    read_result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'cli-rt')
    assert read_result.success
    read_data = read_result.toon()
    assert read_data['plan_id'] == 'cli-rt'
    assert read_data['manifest_version'] == 1



def test_cli_compose_invalid_change_type_emits_toon_error(plan_context):
    result = run_script(
        SCRIPT_PATH,
        'compose',
        '--plan-id',
        'cli-bad',
        '--plan-change-type',
        'nonsense',
        '--track',
        'simple',
        '--scope-estimate',
        'surgical',
    )
    # Script exits 0 on validation errors (TOON contract); error in stdout.
    assert result.returncode == 0
    data = result.toon()
    assert data['status'] == 'error'
    assert data['error'] == 'invalid_change_type'



def test_cli_compose_with_all_optional_flags_roundtrips(plan_context):
    """CLI accepts --recipe-key, --affected-files-count, and both step CSVs."""
    result = run_script(
        SCRIPT_PATH,
        'compose',
        '--plan-id',
        'cli-allflags',
        '--plan-change-type',
        'tech_debt',
        '--track',
        'simple',
        '--scope-estimate',
        'surgical',
        '--recipe-key',
        'lesson_cleanup',
        '--affected-files-count',
        '2',
        '--phase-5-steps',
        'quality-gate,module-tests',
        '--phase-6-steps',
        'push,create-pr,branch-cleanup',
    )
    assert result.success, f'compose failed: stderr={result.stderr!r}'
    data = result.toon()
    assert data['status'] == 'success'
    assert data['rule_fired'] == 'recipe'



def test_cli_compose_commit_and_push_false_omits_commit_push(plan_context):
    """CLI accepts --commit-and-push false and emits a manifest without push."""
    result = run_script(
        SCRIPT_PATH,
        'compose',
        '--plan-id',
        'cli-cap-false',
        '--plan-change-type',
        'feature',
        '--track',
        'complex',
        '--scope-estimate',
        'multi_module',
        '--commit-and-push',
        'false',
    )
    assert result.success, f'compose failed: stderr={result.stderr!r}'
    compose_data = result.toon()
    assert compose_data['status'] == 'success'
    # The scalar ``commit_push_omitted`` flag is replaced by the per-step record
    # list, so the CLI surface is asserted on the manifest effect below plus the
    # absence of the retired key rather than on a coerced boolean.
    assert 'commit_push_omitted' not in compose_data

    read_result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'cli-cap-false')
    assert read_result.success
    manifest = read_result.toon()
    assert 'push' not in manifest['phase_6']['steps']
