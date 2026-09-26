# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    cmd_compose,
    read_manifest,
)


def test_compose_is_idempotent_and_deterministic(plan_context):
    """Re-composing with identical inputs overwrites and yields identical manifest."""
    first = cmd_compose(_compose_ns(plan_id='matrix-idempotent'))
    manifest_first = read_manifest('matrix-idempotent')
    second = cmd_compose(_compose_ns(plan_id='matrix-idempotent'))
    manifest_second = read_manifest('matrix-idempotent')
    assert first is not None and second is not None
    assert first['rule_fired'] == second['rule_fired']
    assert manifest_first == manifest_second
