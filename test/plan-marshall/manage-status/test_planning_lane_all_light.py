#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``planning-lane`` subcommand of manage-status."""


from __future__ import annotations

from _planning_lane_fixtures import (
    _CONCRETE_BODY,
    _VAGUE_BODY,
    _light_setup,
    _mod,
    _ns_route,
    _write_marshal,
    _write_references,
    _write_request,
    _write_status,
    cmd_planning_lane_route,
)

# =============================================================================
# All-light default
# =============================================================================


def test_all_light_signals_resolve_light(plan_context):
    """When no deep-precondition fires, the router resolves the light default."""
    _light_setup(plan_context, 'pl-light')

    result = cmd_planning_lane_route(_ns_route('pl-light'))

    assert result['status'] == 'success'
    assert result['planning_lane'] == 'light'
    assert result['fired_signals'] == []
    assert result['decision_predicate'] == 'signal_set'


# =============================================================================
# Each signal firing deep in isolation
# =============================================================================


def test_s2_scope_estimate_multi_module_forces_deep(plan_context):
    """S2 — a broad scope_estimate forces deep while all other signals stay light."""
    # Flip only scope_estimate to multi_module.
    plan_dir = _light_setup(plan_context, 'pl-s2')
    _write_references(plan_dir, scope_estimate='multi_module')

    result = cmd_planning_lane_route(_ns_route('pl-s2'))

    assert result['planning_lane'] == 'deep'
    assert 'S2:scope_estimate' in result['fired_signals']


def test_s2_scope_estimate_absent_forces_deep(plan_context):
    """S2 — an absent scope_estimate (unknown band) biases deep."""
    # References with no scope_estimate at all.
    plan_dir = _light_setup(plan_context, 'pl-s2-absent')
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_planning_lane_route(_ns_route('pl-s2-absent'))

    assert result['planning_lane'] == 'deep'
    assert 'S2:scope_estimate' in result['fired_signals']


def test_s3_change_type_feature_suppressed_when_narrow_and_concrete(plan_context):
    """S3 — a generative change_type is SUPPRESSED under the narrow-and-concrete carve-out.

    The ``_light_setup`` baseline is surgical scope + a concrete request, so a
    ``feature`` change_type no longer forces deep on its own — the positively
    bounded case stays light. (S3 firing deep for a broad/unknown scope is
    covered by ``test_planning_lane_calibration.py``.)
    """
    # Flip only change_type to feature; the narrow+concrete baseline carves it out.
    plan_dir = _light_setup(plan_context, 'pl-s3')
    _write_status(plan_dir, metadata={'plan_source': 'lesson', 'change_type': 'feature'})

    result = cmd_planning_lane_route(_ns_route('pl-s3'))

    assert result['planning_lane'] == 'light'
    assert 'S3:change_type' not in result['fired_signals']


def test_s4_compatibility_breaking_suppressed_when_narrow_and_concrete(plan_context):
    """S4 — breaking compatibility is SUPPRESSED under the narrow-and-concrete carve-out.

    The ``_light_setup`` baseline is surgical scope + a concrete request, so a
    ``breaking`` compatibility no longer forces deep on its own. (S4 firing deep
    for a broad/unknown scope is covered by ``test_planning_lane_calibration.py``.)
    """
    # Flip only compatibility to breaking; the narrow+concrete baseline carves it out.
    _light_setup(plan_context, 'pl-s4')
    _write_marshal(plan_context.fixture_dir, compatibility='breaking', deep_lane='auto')

    result = cmd_planning_lane_route(_ns_route('pl-s4'))

    assert result['planning_lane'] == 'light'
    assert 'S4:compatibility' not in result['fired_signals']


def test_s5_vague_request_forces_deep(plan_context):
    """S5 — a vague request (no path, no fix signal) forces deep."""
    # Replace the concrete body with a vague one.
    plan_dir = _light_setup(plan_context, 'pl-s5')
    _write_request(plan_dir, _VAGUE_BODY)

    result = cmd_planning_lane_route(_ns_route('pl-s5'))

    assert result['planning_lane'] == 'deep'
    assert 'S5:concreteness' in result['fired_signals']
    assert result['signals']['request_concrete'] is False


def test_s5_concrete_request_with_cli_signal_stays_light(plan_context):
    """S5 — a request body carrying a CLI invocation counts as concrete (light)."""
    # Body with a python3 .plan/execute-script.py invocation, no path.
    plan_dir = _light_setup(plan_context, 'pl-s5-cli')
    _write_request(
        plan_dir,
        'Run python3 .plan/execute-script.py plan-marshall:foo:foo bar and verify.',
    )

    result = cmd_planning_lane_route(_ns_route('pl-s5-cli'))

    # Concreteness passes, so S5 does not fire; lane stays light.
    assert result['signals']['request_concrete'] is True
    assert 'S5:concreteness' not in result['fired_signals']
    assert result['planning_lane'] == 'light'


# =============================================================================
# S5 regex constants + _request_is_concrete importability (downstream consumers)
# =============================================================================
#
# The audit retrospective check (deliverable 2) re-derives request_concrete from
# each archived request.md by importing these symbols. These tests lock that they
# remain module-level and importable, and that _request_is_concrete matches the
# documented S5 anchors.


def test_s5_regex_constants_are_module_level_importable():
    """The four S5 regexes are importable module-level compiled patterns."""
    import re  # noqa: PLC0415

    for name in ('_PATH_RE', '_FENCE_RE', '_CLI_RE', '_NOTATION_RE'):
        pattern = getattr(_mod, name)
        assert isinstance(pattern, re.Pattern), f'{name} must be a compiled regex'


# =============================================================================
# Each signal firing deep in isolation
# =============================================================================

def test_s1_free_form_source_with_vague_request_forces_deep(plan_context):
    """S1 — free-form source AND failed S5 concreteness conjunction forces deep."""
    # Free-form source (plan_source unset) + vague body.
    plan_dir = plan_context.plan_dir_for('pl-s1')
    _write_request(plan_dir, _VAGUE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})  # no plan_source
    _write_references(plan_dir, scope_estimate='surgical')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='auto')

    result = cmd_planning_lane_route(_ns_route('pl-s1'))

    # Both S1 and S5 fire (the conjunction is what S1 keys off).
    assert result['planning_lane'] == 'deep'
    assert 'S1:plan_source' in result['fired_signals']


def test_s1_free_form_source_with_concrete_request_stays_light(plan_context):
    """S1 calibration — free-form source ALONE does not force deep when S5 passes."""
    # Free-form source but a concrete request body.
    plan_dir = plan_context.plan_dir_for('pl-s1-concrete')
    _write_request(plan_dir, _CONCRETE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})  # no plan_source
    _write_references(plan_dir, scope_estimate='surgical')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='auto')

    result = cmd_planning_lane_route(_ns_route('pl-s1-concrete'))

    # Concrete anchor keeps the free-form request light.
    assert result['planning_lane'] == 'light'
    assert 'S1:plan_source' not in result['fired_signals']


def test_s6_lane_override_deep_forces_deep(plan_context):
    """S6 — an explicit --lane-override deep forces deep regardless of signals."""
    # All-light baseline, then override to deep.
    _light_setup(plan_context, 'pl-s6')

    result = cmd_planning_lane_route(_ns_route('pl-s6', lane_override='deep'))

    assert result['planning_lane'] == 'deep'
    assert 'S6:override' in result['fired_signals']


# =============================================================================
# plan.phase-1-init.deep_lane short-circuit
# =============================================================================


def test_deep_lane_always_forces_deep_overriding_light_signals(plan_context):
    """deep_lane=always forces deep even when every signal is light."""
    # All-light baseline, then deep_lane always.
    _light_setup(plan_context, 'pl-deep-lane-always')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='always')

    result = cmd_planning_lane_route(_ns_route('pl-deep-lane-always'))

    assert result['planning_lane'] == 'deep'
    assert result['decision_predicate'] == 'plan.phase-1-init.deep_lane=always'
    assert result['ceremony_deep_lane'] == 'always'


def test_deep_lane_never_forces_light_overriding_deep_signals(plan_context):
    """deep_lane=never forces light even when deep signals fire."""
    # Multiple deep signals present, then deep_lane never short-circuits.
    plan_dir = _light_setup(plan_context, 'pl-deep-lane-never')
    _write_references(plan_dir, scope_estimate='multi_module')  # S2 deep
    _write_status(plan_dir, metadata={'plan_source': 'lesson', 'change_type': 'feature'})  # S3 deep
    _write_marshal(plan_context.fixture_dir, compatibility='breaking', deep_lane='never')  # S4 deep

    result = cmd_planning_lane_route(_ns_route('pl-deep-lane-never'))

    # The never short-circuit wins over all the deep signals.
    assert result['planning_lane'] == 'light'
    assert result['decision_predicate'] == 'plan.phase-1-init.deep_lane=never'


def test_deep_lane_auto_defers_to_signal_set(plan_context):
    """deep_lane=auto (default) lets the signal set decide."""
    # One deep signal under auto.
    plan_dir = _light_setup(plan_context, 'pl-deep-lane-auto')
    _write_references(plan_dir, scope_estimate='broad')  # S2 deep

    result = cmd_planning_lane_route(_ns_route('pl-deep-lane-auto'))

    assert result['decision_predicate'] == 'signal_set'
    assert result['planning_lane'] == 'deep'


# =============================================================================
# project_profile_pure — execution-profile posture projection
# =============================================================================

def test_deep_lane_always_does_not_coerce_profile_to_full(plan_context):
    """deep_lane=always forces planning_lane=deep but leaves the profile projection alone.

    Planning depth and the execution profile are independent axes (§4.2): the
    ceremony gate that ratchets the lane to deep must NOT coerce the posture to
    full. An all-light narrow concrete change keeps its minimal projection even
    under deep_lane=always.
    """
    _light_setup(plan_context, 'pl-profile-indep')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='always')

    result = cmd_planning_lane_route(_ns_route('pl-profile-indep'))

    # The deep-lane gate wins the planning-depth verdict ...
    assert result['planning_lane'] == 'deep'
    assert result['decision_predicate'] == 'plan.phase-1-init.deep_lane=always'
    # ... but the execution-profile projection is unaffected by it.
    assert result['execution_profile'] == 'minimal'
