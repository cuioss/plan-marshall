# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _LANE_STEPS,
    _apply_lane_resolution,
    _dropped_steps,
    _mem,
    _patch_element_lane,
)


def test_apply_lane_resolution_full_is_noop(monkeypatch):
    """The full posture keeps every element (no pruning)."""
    _patch_element_lane(monkeypatch)
    kept, dropped, warnings = _apply_lane_resolution(_LANE_STEPS, 'full', None)

    assert kept == _LANE_STEPS
    assert dropped == []
    assert warnings == []


def test_apply_lane_resolution_minimal_keeps_only_floor(monkeypatch):
    """Minimal keeps only the tier-minimal floor; standard/full-tier elements drop."""
    _patch_element_lane(monkeypatch)
    kept, dropped, _warnings = _apply_lane_resolution(_LANE_STEPS, 'minimal', None)

    assert kept == ['push', 'archive-plan', 'project:finalize-step-deploy-target']
    assert _dropped_steps(dropped) == {
        'sonar-roundtrip',
        'finalize-step-security-audit',
        'plan-marshall:plan-retrospective',
    }


def test_apply_lane_resolution_standard_drops_only_full_tier(monkeypatch):
    """Standard keeps minimal + standard tiers and drops the two full-tier elements."""
    _patch_element_lane(monkeypatch)
    kept, dropped, _warnings = _apply_lane_resolution(_LANE_STEPS, 'standard', None)

    assert _dropped_steps(dropped) == {
        'finalize-step-security-audit',
        'plan-marshall:plan-retrospective',
    }
    assert 'sonar-roundtrip' in kept
    assert 'project:finalize-step-deploy-target' in kept


def test_apply_lane_resolution_every_drop_carries_a_reason(monkeypatch):
    """Each dropped element names WHY it was removed, per step.

    The former bare-id list meant a single aggregate log line named the whole
    dropped set at once, so no individual drop carried its own reason. The two
    reason shapes are distinguishable: an explicit ``off`` opt-out versus an
    effective tier above the posture cutoff.
    """
    _patch_element_lane(monkeypatch)
    _kept, dropped, _warnings = _apply_lane_resolution(_LANE_STEPS, 'minimal', None)

    assert dropped, 'the minimal posture must drop something for this case to mean anything'
    for record in dropped:
        assert set(record) == {'step', 'reason'}
        assert record['reason']
        # Posture-cutoff drops name the cutoff, not an opt-out.
        assert 'posture cutoff' in record['reason']


def test_apply_lane_resolution_off_override_reason_names_the_opt_out(monkeypatch):
    """An explicit ``off`` override is reported as an opt-out, not a tier cutoff.

    The two reasons must stay distinguishable: "the operator turned this off" and
    "this tier exceeds the posture" are different facts about the same drop, and
    an operator reading the log needs to tell them apart.
    """
    _patch_element_lane(monkeypatch)
    overrides = {'sonar-roundtrip': {'lane': 'off'}}
    _kept, dropped, _warnings = _apply_lane_resolution(_LANE_STEPS, 'auto', overrides)

    reason = next(r['reason'] for r in dropped if r['step'] == 'sonar-roundtrip')
    assert "'off'" in reason
    assert 'posture cutoff' not in reason


def test_apply_lane_resolution_keeps_unblocked_elements(monkeypatch):
    """An element with no lane: block is not lane-participating and is always kept."""
    monkeypatch.setattr(_mem, '_resolve_element_lane', lambda step: None)
    kept, dropped, _warnings = _apply_lane_resolution(['no-block-step'], 'minimal', None)

    assert kept == ['no-block-step']
    assert dropped == []


def test_apply_lane_resolution_derived_state_off_override_is_immune(monkeypatch):
    """An ``off`` marshal override of a derived-state floor element is IMMUNE — the
    element is KEPT with an informational warning (the mandatory floor cannot be weakened)."""
    _patch_element_lane(monkeypatch)
    overrides = {'project:finalize-step-deploy-target': {'lane': 'off'}}
    kept, dropped, warnings = _apply_lane_resolution(_LANE_STEPS, 'minimal', overrides)

    assert 'project:finalize-step-deploy-target' in kept
    assert kept == ['push', 'archive-plan', 'project:finalize-step-deploy-target']
    assert 'project:finalize-step-deploy-target' not in _dropped_steps(dropped)
    assert any(step == 'project:finalize-step-deploy-target' and 'immune' in warning for step, warning in warnings)


def test_apply_lane_resolution_adversarial_off_override_drops_cleanly(monkeypatch):
    """An ``off`` marshal override of a non-floor adversarial element drops it with NO
    warning — the opt-out is a real drop (standard posture would otherwise keep it)."""
    _patch_element_lane(monkeypatch)
    overrides = {'sonar-roundtrip': {'lane': 'off'}}
    kept, dropped, warnings = _apply_lane_resolution(_LANE_STEPS, 'standard', overrides)

    assert 'sonar-roundtrip' in _dropped_steps(dropped)
    assert 'sonar-roundtrip' not in kept
    assert all(step != 'sonar-roundtrip' for step, _ in warnings)
