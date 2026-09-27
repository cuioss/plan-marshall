# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_security_class_gate_regression_fixtures import (
    _LARGE_FOOTPRINT,
    _SECURITY_STEP,
    _capture_decision_log,
    _compose,
    _composed_steps,
    _restore_patched_seams,
    _stub_footprint,
)


def test_no_omission_report_when_the_step_is_kept(plan_context):
    """The report is drop-only — a kept step produces no record and no [STATUS] line.

    Without this, ``security_class_omitted`` could be populated unconditionally and
    the drop-naming assertion above would still pass, making the loudness signal
    meaningless.

    Pre-fix failure (observed against pre-fix HEAD):
    ``KeyError: 'security_class_omitted'``.
    """
    plan_id = 'secclass-kept-no-report'
    _stub_footprint(_LARGE_FOOTPRINT)
    captured = _capture_decision_log()

    result = _compose(plan_id, change_type='feature', affected_files_count=12)

    assert result['security_class_omitted'] == []
    assert _SECURITY_STEP in _composed_steps(plan_id)
    assert [msg for pid, msg in captured if 'security_class_inactive' in msg] == []
