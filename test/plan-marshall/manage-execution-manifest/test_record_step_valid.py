# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_record_step_fixtures import (
    DEFAULT_STEP_OWNER,
    VALID_RECORD_OUTCOMES,
    VALID_RECORD_PHASES,
    VALID_STEP_OWNERS,
)


def test_valid_record_enums_are_the_documented_sets(plan_context):
    """Guard the contract constants the record-step subcommand validates against."""
    assert VALID_RECORD_PHASES == ('5-execute', '6-finalize')
    assert VALID_RECORD_OUTCOMES == ('executed', 'skipped', 'loop_back', 'failed', 'error')



# =============================================================================
# Step-ownership routing (orchestrator-owned vs leaf-dispatchable)
# =============================================================================


def test_valid_step_owners_vocabulary():
    """The declared owner vocabulary is the closed two-value set."""
    assert VALID_STEP_OWNERS == ('orchestrator-owned', 'leaf-dispatchable')
    assert DEFAULT_STEP_OWNER == 'leaf-dispatchable'
