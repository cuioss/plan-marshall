# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_security_class_gate_regression_fixtures import (
    _SECURITY_STEP,
    _capture_decision_log,
    _compose,
    _composed_steps,
    _restore_patched_seams,
    _stub_footprint,
)

# =============================================================================
# (c) A genuine drop names its gating reason, loudly
# =============================================================================


def test_genuine_drop_reports_step_and_reason_in_result_and_decision_log(plan_context):
    """The one real drop case is reported in the compose result AND as a [STATUS] line.

    A plan with no declared affected files and an empty live footprint has nothing
    to audit. That drop is legitimate — but it must be loud: the compose result
    carries a ``{step, reason}`` record (which ``phase-4-plan`` Step 7b surfaces in
    its phase return) and ``decision.log`` carries a ``[STATUS]`` line naming both.

    Pre-fix failure (observed against pre-fix HEAD):
    ``KeyError: 'security_class_omitted'``. The pre-fix result reported a bare
    ``security_audit_omitted: True`` boolean that named neither the step nor the
    reason, and the decision-log line it emitted read
    ``finalize-step-security-audit omitted — change_type=analysis
    affected_files_count=0`` — quoting the inputs rather than the gating reason,
    with no ``[STATUS]`` prefix.
    """
    plan_id = 'secclass-genuine-drop'
    _stub_footprint([])
    captured = _capture_decision_log()

    result = _compose(plan_id, change_type='feature', affected_files_count=0)

    assert result['security_class_omitted'] == [
        {
            'step': _SECURITY_STEP,
            'reason': 'no declared affected files and empty live footprint',
        }
    ]
    assert _SECURITY_STEP not in _composed_steps(plan_id)

    status_lines = [msg for pid, msg in captured if 'security_class_inactive' in msg]
    assert status_lines == [
        '(plan-marshall:manage-execution-manifest:compose) [STATUS] security_class_inactive — '
        f'dropped {_SECURITY_STEP} from phase_6.steps: '
        'no declared affected files and empty live footprint'
    ]
