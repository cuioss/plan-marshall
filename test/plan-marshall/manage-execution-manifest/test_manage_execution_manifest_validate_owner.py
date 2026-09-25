# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_validate_fixtures import (
    ORCHESTRATOR_OWNED_STEPS,
    owner_of,
    validate_step_owner,
)


def test_owner_of_yields_a_schema_valid_owner_for_every_step():
    """owner_of always returns a value that passes the schema validator.

    Schema-integrity invariant: the classifier never emits an owner outside the
    declared vocabulary, for both registry and non-registry steps.
    """
    for step in (
        *ORCHESTRATOR_OWNED_STEPS,
        'push',
        'create-pr',
        'ci-verify',
        'verify:quality-gate',
        'project:finalize-step-plugin-doctor',
        'default:finalize-step-simplify',
    ):
        assert validate_step_owner(owner_of(step)) is True
