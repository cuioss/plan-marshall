# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    cmd_compose,
    json,
    read_manifest,
)


def test_compose_snapshots_resolved_step_params_from_keyed_map(plan_context):
    """compose snapshots each selected step's resolved params from the marshal keyed map.

    Seeds a marshal.json whose phase-6-finalize steps map carries nested params
    on default:branch-cleanup and default:sonar-roundtrip. The composer must
    snapshot those resolved params into body.phase_6.step_params, keyed by the
    bare in-manifest step id (the default: prefix is stripped at the boundary),
    for every selected step. Steps with no marshal-side params snapshot as {}.
    """
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    phase_6_map = {
        'default:push': {},
        'default:create-pr': {},
        'plan-marshall:automatic-review': {'review_bot_buffer_seconds': 240},
        'default:sonar-roundtrip': {
            'touched_file_cleanup': 'touched_files_zero',
            'do_transition': True,
            'ce_wait_timeout_seconds': 720,
        },
        'default:lessons-capture': {},
        'default:branch-cleanup': {
            'pr_merge_strategy': 'rebase',
            'final_merge_without_asking': True,
            'auto_rebase_threshold': 'no_overlap_only',
        },
        'default:record-metrics': {},
        'default:archive-plan': {},
    }
    data = {'plan': {'phase-6-finalize': {'steps': phase_6_map}}}
    marshal_path.write_text(json.dumps(data), encoding='utf-8')

    result = cmd_compose(
        _compose_ns(
            plan_id='snapshot-params',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=11,
        )
    )
    assert result is not None and result['status'] == 'success'

    manifest = read_manifest('snapshot-params')
    assert manifest is not None
    step_params = manifest['phase_6']['step_params']
    # the snapshot is keyed by the bare in-manifest step id (default: stripped)
    # and carries the resolved nested params for selected steps
    assert step_params['branch-cleanup'] == {
        'pr_merge_strategy': 'rebase',
        'final_merge_without_asking': True,
        'auto_rebase_threshold': 'no_overlap_only',
    }
    assert step_params['sonar-roundtrip'] == {
        'touched_file_cleanup': 'touched_files_zero',
        'do_transition': True,
        'ce_wait_timeout_seconds': 720,
    }
    assert step_params['automatic-review'] == {'review_bot_buffer_seconds': 240}
    # an ownerless selected step snapshots as the empty param object
    assert step_params['push'] == {}
    # every in-manifest step has a snapshot entry
    assert set(step_params.keys()) == set(manifest['phase_6']['steps'])


def test_compose_snapshots_step_params_from_keyed_map(plan_context):
    """compose snapshots resolved params from a keyed-map marshal.json.

    Seeds a marshal.json whose phase-6-finalize steps are the keyed-map form with
    param-bearing values on branch-cleanup and sonar-roundtrip. The composer
    snapshots the resolved params into body.phase_6.step_params (keyed by the
    bare in-manifest step id). Config-less steps snapshot as {}.
    """
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    phase_6_map = {
        'default:push': {},
        'default:create-pr': {},
        'plan-marshall:automatic-review': {'review_bot_buffer_seconds': 240},
        'default:sonar-roundtrip': {
            'touched_file_cleanup': 'touched_files_zero',
            'do_transition': True,
            'ce_wait_timeout_seconds': 720,
        },
        'default:lessons-capture': {},
        'default:branch-cleanup': {
            'pr_merge_strategy': 'rebase',
            'final_merge_without_asking': True,
            'auto_rebase_threshold': 'no_overlap_only',
        },
        'default:record-metrics': {},
        'default:archive-plan': {},
    }
    data = {'plan': {'phase-6-finalize': {'steps': phase_6_map}}}
    marshal_path.write_text(json.dumps(data), encoding='utf-8')

    result = cmd_compose(
        _compose_ns(
            plan_id='snapshot-params-keyed',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=11,
        )
    )
    assert result is not None and result['status'] == 'success'

    manifest = read_manifest('snapshot-params-keyed')
    assert manifest is not None
    step_params = manifest['phase_6']['step_params']
    # the snapshot is keyed by the bare in-manifest step id (default: stripped)
    assert step_params['branch-cleanup'] == {
        'pr_merge_strategy': 'rebase',
        'final_merge_without_asking': True,
        'auto_rebase_threshold': 'no_overlap_only',
    }
    assert step_params['sonar-roundtrip'] == {
        'touched_file_cleanup': 'touched_files_zero',
        'do_transition': True,
        'ce_wait_timeout_seconds': 720,
    }
    assert step_params['automatic-review'] == {'review_bot_buffer_seconds': 240}
    # a config-less selected step snapshots as the empty param object
    assert step_params['push'] == {}
    # every in-manifest step has a snapshot entry
    assert set(step_params.keys()) == set(manifest['phase_6']['steps'])
