# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_record_step_fixtures import is_leaf_dispatchable


def test_is_leaf_dispatchable_rejects_orchestrator_owned_step():
    """A dispatched leaf must never be handed an orchestrator-owned step."""
    assert is_leaf_dispatchable('project:finalize-step-plugin-doctor') is False
    assert is_leaf_dispatchable('automatic-review') is False
    # A leaf-dispatchable step is accepted.
    assert is_leaf_dispatchable('push') is True
    assert is_leaf_dispatchable('verify:quality-gate') is True
