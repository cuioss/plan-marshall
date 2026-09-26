# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_step_params_fixtures import _mem, get_manifest_path, read_manifest, write_manifest


def test_write_manifest_serializes_no_empty_dict_for_ownerless_steps(plan_context):
    """write_manifest never serializes an empty {} block for an ownerless step.

    Reading the raw on-disk TOON proves the ownerless step round-trips through
    the write boundary as null (TOON renders it as the empty string), not a {}
    block, satisfying the no-empty-{} contract end to end.
    """
    manifest = {
        'phase_5': {'step_params': {'quality-gate': {}, 'module-tests': {}}},
        'phase_6': {'step_params': {'push': {}, 'branch-cleanup': {'pr_merge_strategy': 'squash'}}},
    }

    write_manifest('sp-write-no-empty', manifest)

    # the raw serialized manifest carries no empty {} block for ownerless steps
    raw = get_manifest_path('sp-write-no-empty').read_text(encoding='utf-8')
    parsed = _mem.parse_toon(raw)
    # ownerless steps serialized as null (None), not as a {} block
    assert parsed['phase_5']['step_params'].get('quality-gate') is None
    assert parsed['phase_6']['step_params'].get('push') is None
    # param-owning step survived
    assert parsed['phase_6']['step_params']['branch-cleanup'] == {'pr_merge_strategy': 'squash'}


def test_write_then_read_manifest_round_trips_ownerless_step_to_empty_dict(plan_context):
    """An ownerless step written via write_manifest reads back as {} via read_manifest.

    End-to-end suppression+coercion: the write boundary collapses {} to null, and
    the read boundary coerces it back to {}, so the ownerless step is {} on read
    while no empty {} block was ever serialized.
    """
    manifest = {
        'phase_5': {'step_params': {'quality-gate': {}, 'module-tests': {}}},
        'phase_6': {'step_params': {'push': {}, 'branch-cleanup': {'pr_merge_strategy': 'squash'}}},
    }

    write_manifest('sp-round-trip', manifest)
    read_back = read_manifest('sp-round-trip')

    assert read_back is not None
    # ownerless steps read back as the empty dict
    assert read_back['phase_5']['step_params']['quality-gate'] == {}
    assert read_back['phase_5']['step_params']['module-tests'] == {}
    assert read_back['phase_6']['step_params']['push'] == {}
    # param-owning step round-trips unchanged
    assert read_back['phase_6']['step_params']['branch-cleanup'] == {'pr_merge_strategy': 'squash'}
