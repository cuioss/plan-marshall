# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_security_class_gate_regression_fixtures import (
    _PEER_STEP,
    _SECURITY_STEP,
    _capture_decision_log,
    _compose,
    _restore_patched_seams,
    _stub_footprint,
)


def test_personaless_peer_is_not_in_the_security_class(plan_context):
    """``finalize-step-simplify`` is never reported by the security gate.

    The out-of-scope sibling keeps its own ``simplify_inactive`` gate and its own
    boolean result field. If the population ever widened to catch it, this fails.

    Pre-fix failure (observed against pre-fix HEAD):
    ``KeyError: 'security_class_omitted'``.
    """
    plan_id = 'secclass-peer-excluded'
    _stub_footprint([])
    _capture_decision_log()

    result = _compose(plan_id, change_type='feature', affected_files_count=0)

    reported = {record['step'] for record in result['security_class_omitted']}
    assert reported == {_SECURITY_STEP}
    assert _PEER_STEP not in reported
    # The peer's own gate still owns it, and still reports through its own field.
    assert result['simplify_omitted'] is True
