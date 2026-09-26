# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_validate_fixtures import (
    _compose_ns,
    _seed_keyed_map_marshal,
    cmd_compose,
    read_manifest,
)


def test_compose_from_keyed_map_marshal_snapshots_dict_step_params(plan_context):
    """A keyed-map marshal.json composes to a DICT (id-keyed) manifest step_params snapshot.

    The composer reads the keyed-map steps and writes the per-step params into the
    manifest as an id-keyed DICT. This locks the "manifest snapshot stays a DICT"
    contract.
    """
    _seed_keyed_map_marshal(plan_context.fixture_dir)
    cmd_compose(_compose_ns(plan_id='val-keyed-snapshot'))

    manifest = read_manifest('val-keyed-snapshot')
    assert manifest is not None
    snapshot = manifest['phase_6']['step_params']
    # The manifest snapshot is an id-keyed DICT.
    assert isinstance(snapshot, dict)
    # The param-bearing step's params survive (snapshot is keyed by the bare step
    # id — the default: prefix is stripped).
    assert snapshot['branch-cleanup'] == {
        'pr_merge_strategy': 'squash',
        'final_merge_without_asking': False,
    }
    # A config-less step reads back as the empty dict (no params).
    assert snapshot['push'] == {}
