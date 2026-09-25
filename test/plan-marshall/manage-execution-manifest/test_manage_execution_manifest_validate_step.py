# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_validate_fixtures import (
    VALID_STEP_OWNERS,
    Namespace,
    _compose_ns,
    _seed_keyed_map_marshal,
    cmd_compose,
    cmd_step_params_get,
)


def test_step_params_get_resolves_dict_snapshot_from_keyed_map_marshal(plan_context):
    """step-params get resolves against the DICT manifest snapshot sourced from keyed-map marshal.

    The snapshot is the id-keyed DICT the composer wrote from the keyed-map
    marshal.json; `step-params get` returns the full param object for a step in a
    single call, resolving the bare-keyed DICT entry.
    """
    _seed_keyed_map_marshal(plan_context.fixture_dir)
    cmd_compose(_compose_ns(plan_id='val-keyed-sp-get'))

    result = cmd_step_params_get(Namespace(plan_id='val-keyed-sp-get', phase='6-finalize', step_id='branch-cleanup'))

    assert result is not None and result['status'] == 'success'
    assert result['params'] == {
        'pr_merge_strategy': 'squash',
        'final_merge_without_asking': False,
    }



# =============================================================================
# Per-step owner schema field (orchestrator-owned | leaf-dispatchable)
# =============================================================================


def test_step_owner_schema_vocabulary_is_closed():
    """The owner schema vocabulary is the closed two-value tuple."""
    assert VALID_STEP_OWNERS == ('orchestrator-owned', 'leaf-dispatchable')
