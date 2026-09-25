# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_step_params_fixtures import (
    _compose_ns,
    _mem,
    _seed_marshal_with_branch_cleanup_params,
    cmd_compose,
    get_manifest_path,
    read_manifest,
)


def test_compose_then_read_manifest_ownerless_steps_read_as_empty_dict(plan_context):
    """A composed manifest's ownerless steps read back as {} (no empty {} on disk).

    Exercises the real compose → write → read path: cmd_compose snapshots
    ownerless verify/finalize steps as null, write_manifest serializes no empty
    {}, and read_manifest coerces them back to {}.
    """
    _seed_marshal_with_branch_cleanup_params(plan_context.fixture_dir)
    cmd_compose(_compose_ns('sp-compose-ownerless'))

    # the raw on-disk manifest carries no empty {} block for ownerless steps
    raw = get_manifest_path('sp-compose-ownerless').read_text(encoding='utf-8')
    parsed_raw = _mem.parse_toon(raw)
    phase_6_raw = parsed_raw['phase_6']['step_params']
    # push is ownerless — its on-disk value is null (None), not a {} block
    assert phase_6_raw.get('push') is None

    # the read boundary coerces it back to {}
    read_back = read_manifest('sp-compose-ownerless')
    assert read_back is not None
    assert read_back['phase_6']['step_params']['push'] == {}
    # the param-owning step survives the round-trip
    assert read_back['phase_6']['step_params']['branch-cleanup'] == {
        'pr_merge_strategy': 'squash',
        'final_merge_without_asking': False,
        'auto_rebase_threshold': 'no_overlap_only',
    }
