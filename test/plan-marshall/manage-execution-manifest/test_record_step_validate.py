# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_record_step_fixtures import validate_step_owner


def test_validate_step_owner_accepts_declared_and_rejects_unknown():
    """validate_step_owner is a membership predicate over VALID_STEP_OWNERS."""
    assert validate_step_owner('orchestrator-owned') is True
    assert validate_step_owner('leaf-dispatchable') is True
    assert validate_step_owner('main-only') is False
    assert validate_step_owner('') is False
