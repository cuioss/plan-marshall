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


def test_unresolvable_footprint_keeps_the_step(plan_context):
    """An UNRESOLVABLE live footprint is no evidence, so the step is KEPT.

    The gate's drop requires BOTH signals to be genuinely empty. A footprint that
    could not be resolved at all (the normal state at phase-4-plan compose, before
    the worktree is materialised) is not "nothing to audit" — it is "we could not
    look" — so it fails toward inclusion, the same discipline the absent
    change-type leg follows.

    This is the one falsy footprint state that does NOT drop, which is exactly why
    it needs its own case: the sibling above pins ``[]`` dropping the step, and
    both states are falsy. A predicate written as ``not live_footprint`` would
    satisfy that sibling and silently drop a security audit on every plan whose
    worktree was not yet inspectable.
    """
    plan_id = 'secclass-unresolvable'
    _stub_footprint(None)
    captured = _capture_decision_log()

    result = _compose(plan_id, change_type='feature', affected_files_count=0)

    assert result['security_class_omitted'] == []
    assert _SECURITY_STEP in _composed_steps(plan_id)
    assert [msg for pid, msg in captured if 'security_class_inactive' in msg] == []



def test_unresolvable_and_resolvable_empty_footprints_diverge(plan_context):
    """The paired opposite: identical inputs but for the footprint STATE.

    Comparing the two outcomes against each other is what fails if a future change
    re-collapses ``None`` into ``[]`` at this seam — each case asserted alone would
    still pass against a gate that had lost the distinction in one direction.
    """
    _stub_footprint(None)
    _capture_decision_log()
    unresolvable = _compose('secclass-div-unresolvable', change_type='feature', affected_files_count=0)

    _stub_footprint([])
    _capture_decision_log()
    resolvable_empty = _compose('secclass-div-empty', change_type='feature', affected_files_count=0)

    assert unresolvable['security_class_omitted'] == []
    assert [r['step'] for r in resolvable_empty['security_class_omitted']] == [_SECURITY_STEP]
    assert _SECURITY_STEP in _composed_steps('secclass-div-unresolvable')
    assert _SECURITY_STEP not in _composed_steps('secclass-div-empty')
