# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_security_class_gate_regression.py: large."""

from _manage_execution_manifest_security_class_gate_regression_fixtures import (
    _LARGE_FOOTPRINT,
    _SECURITY_STEP,
    _capture_decision_log,
    _compose,
    _composed_steps,
    _mem,
    _restore_patched_seams,
    _stub_footprint,
    pytest,
)

# =============================================================================
# (a) A large multi-file change with an excluded change_type keeps the sweep
# =============================================================================


assert len(_mem.VALID_CHANGE_TYPES) > 0, 'VALID_CHANGE_TYPES must not be empty, or this sweep covers nothing'


@pytest.mark.parametrize('change_type', sorted(_mem.VALID_CHANGE_TYPES))
def test_large_change_keeps_security_audit_for_every_change_type(plan_context, change_type):
    """The incident, reproduced: a 12-file change keeps the sweep whatever its change_type.

    The parametrization sweeps the WHOLE ``VALID_CHANGE_TYPES`` vocabulary rather
    than sampling ``analysis`` / ``verification`` — the two values the incident
    happened to involve. ``cmd_compose`` rejects anything outside that enum before
    the pre-filter runs, so the enum IS the reachable population, and a change type
    added later is covered the moment it joins it.

    Pre-fix failure (observed against pre-fix HEAD, all six parameters):
    ``KeyError: 'security_class_omitted'`` — the pre-fix compose result carried a
    bare ``security_audit_omitted`` boolean instead. That assertion is reached
    first, so it masks the second defect, which is present for ``analysis`` and
    ``verification``: those two are outside ``_SIMPLIFY_CHANGE_TYPES``, so
    ``_apply_security_audit_inactive`` dropped the step and the membership
    assertion would have failed too.
    """
    plan_id = f'secclass-large-{change_type}'.replace('_', '-')
    _stub_footprint(_LARGE_FOOTPRINT)
    _capture_decision_log()

    result = _compose(plan_id, change_type=change_type, affected_files_count=12)

    assert result['security_class_omitted'] == []
    assert _SECURITY_STEP in _composed_steps(plan_id)
