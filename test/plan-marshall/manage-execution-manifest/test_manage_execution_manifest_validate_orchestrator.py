# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_validate_fixtures import ORCHESTRATOR_OWNED_STEPS, owner_of


def test_orchestrator_owned_registry_steps_all_resolve_orchestrator_owned():
    """Every registry member classifies as orchestrator-owned (schema field consistency)."""
    for step in ORCHESTRATOR_OWNED_STEPS:
        assert owner_of(step) == 'orchestrator-owned', step
