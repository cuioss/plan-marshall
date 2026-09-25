# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    _write_full_marshal,
    cmd_compose,
    read_manifest,
)


def test_marshal_json_preferred_over_csv_preserves_project_prefixes(plan_context):
    """When marshal.json declares project: steps, the manifest preserves them even if CSV strips them.

    An agent-built CSV with prefixes stripped would produce a manifest of bare
    names the dispatcher mis-routes as built-in default: steps. The composer
    treats marshal.json as the source of truth — agent CSV is fallback only.
    """
    full_phase_6 = [
        'default:push',
        'project:finalize-step-deploy-target',
        'project:finalize-step-sync-plugin-cache',
        'default:create-pr',
        'plan-marshall:automatic-review',
        'default:lessons-capture',
        'project:finalize-step-plugin-doctor',
        'default:branch-cleanup',
        'default:record-metrics',
        'plan-marshall:plan-retrospective',
        'default:archive-plan',
    ]
    # The CSV the agent built (prefixes stripped). marshal.json should win.
    bad_csv = ','.join(
        [
            'push',
            'deploy-target',
            'sync-plugin-cache',
            'create-pr',
            'automatic-review',
            'lessons-capture',
            'plugin-doctor',
            'branch-cleanup',
            'record-metrics',
            'plan-retrospective',
            'archive-plan',
        ]
    )
    _write_full_marshal(plan_context.fixture_dir, phase_6_steps=full_phase_6)
    result = cmd_compose(
        _compose_ns(
            plan_id='marshal-source-of-truth',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=11,
            phase_6_steps=bad_csv,  # noise — should be ignored
        )
    )
    assert result is not None and result['status'] == 'success'
    manifest = read_manifest('marshal-source-of-truth')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    # Prefixes from marshal.json are preserved (except `default:` which
    # is stripped at the boundary normalization step).
    assert 'project:finalize-step-deploy-target' in steps
    assert 'project:finalize-step-sync-plugin-cache' in steps
    assert 'project:finalize-step-plugin-doctor' in steps
    assert 'plan-marshall:plan-retrospective' in steps
    # Bare names from the CSV must not appear in the manifest output.
    assert 'deploy-target' not in steps
    assert 'sync-plugin-cache' not in steps
    assert 'plugin-doctor' not in steps
    assert 'plan-retrospective' not in steps
    # `default:` prefixes ARE stripped by boundary normalization.
    assert 'push' in steps
    assert 'default:push' not in steps



def test_marshal_json_phase_5_steps_also_preferred(plan_context):
    """The marshal.json source-of-truth path applies to phase-5 steps as well as phase-6."""
    custom_phase_5 = ['quality-gate', 'module-tests']
    full_phase_6 = ['default:push', 'default:create-pr', 'plan-marshall:automatic-review', 'default:archive-plan']
    _write_full_marshal(
        plan_context.fixture_dir,
        phase_5_steps=custom_phase_5,
        phase_6_steps=full_phase_6,
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='marshal-phase-5',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=3,
            phase_5_steps='WRONG,STUFF',  # noise — marshal.json should win
        )
    )
    assert result is not None and result['status'] == 'success'
    manifest = read_manifest('marshal-phase-5')
    assert manifest is not None
    assert set(manifest['phase_5']['verification_steps']) == set(custom_phase_5)
