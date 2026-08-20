#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``planning-lane`` subcommand of manage-status."""


from __future__ import annotations

import json

import pytest
from _planning_lane_fixtures import (
    _light_setup,
    _ns_escalate,
    _ns_route,
    _write_marshal,
    _write_references,
    _write_request,
    _write_status,
    cmd_planning_lane_escalate,
    cmd_planning_lane_route,
)

from conftest import load_script_module

# =============================================================================
# --persist
# =============================================================================


def test_persist_writes_planning_lane_metadata(plan_context):
    """--persist writes the resolved lane into status.metadata.planning_lane."""
    plan_dir = _light_setup(plan_context, 'pl-persist')

    result = cmd_planning_lane_route(_ns_route('pl-persist', persist=True))

    assert result['persisted'] is True
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['planning_lane'] == 'light'


def test_persist_writes_execution_profile_metadata(plan_context):
    """--persist writes the projected posture into status.metadata.execution_profile."""
    plan_dir = _light_setup(plan_context, 'pl-profile-persist')

    result = cmd_planning_lane_route(_ns_route('pl-profile-persist', persist=True))

    assert result['persisted'] is True
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['execution_profile'] == 'minimal'


def test_route_without_persist_does_not_write(plan_context):
    """Without --persist the router does not mutate status.json."""
    plan_dir = _light_setup(plan_context, 'pl-nopersist')

    result = cmd_planning_lane_route(_ns_route('pl-nopersist'))

    assert result['persisted'] is False
    status = json.loads((plan_dir / 'status.json').read_text())
    assert 'planning_lane' not in status.get('metadata', {})


# =============================================================================
# Error path
# =============================================================================


def test_route_plan_dir_not_found_errors(plan_context):
    """route against a missing plan dir returns a structured error."""
    result = cmd_planning_lane_route(_ns_route('pl-missing'))

    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


def test_route_surfaces_execution_profile(plan_context):
    """The route return surfaces execution_profile + the structured profile block."""
    # Generative + broad signals → full posture, deep lane.
    plan_dir = _light_setup(plan_context, 'pl-profile-full')
    _write_references(plan_dir, scope_estimate='multi_module')
    _write_status(plan_dir, metadata={'plan_source': 'lesson', 'change_type': 'feature'})

    result = cmd_planning_lane_route(_ns_route('pl-profile-full'))

    assert result['execution_profile'] == 'full'
    assert result['profile']['recommended_posture'] == 'full'
    assert result['profile']['candidate_postures'] == ['minimal', 'standard', 'full']


def test_route_projects_minimal_for_narrow_concrete_change(plan_context):
    """An all-light, narrow, concrete change projects the minimal posture."""
    _light_setup(plan_context, 'pl-profile-minimal')

    result = cmd_planning_lane_route(_ns_route('pl-profile-minimal'))

    assert result['planning_lane'] == 'light'
    assert result['execution_profile'] == 'minimal'


def test_route_without_persist_does_not_write_execution_profile(plan_context):
    """Without --persist the projected posture is not written to status.json."""
    plan_dir = _light_setup(plan_context, 'pl-profile-nopersist')

    cmd_planning_lane_route(_ns_route('pl-profile-nopersist'))

    status = json.loads((plan_dir / 'status.json').read_text())
    assert 'execution_profile' not in status.get('metadata', {})


def test_route_surfaces_scope_provenance(plan_context):
    """The route return carries scope_provenance alongside BOTH verdicts.

    The operator reading one surface sees the lane, the posture, and the band rule
    that drove them — the whole point of surfacing provenance rather than adding a
    prompt.
    """
    plan_dir = _light_setup(plan_context, 'pl-provenance')
    _write_request(plan_dir, 'Fix marketplace/bundles/plan-marshall/skills/x/scripts/x.py.')

    result = cmd_planning_lane_route(_ns_route('pl-provenance'))

    assert result['scope_provenance'] == {
        'distinct_path_count': 1,
        'fan_out_marker': False,
        'band_rule': 'path_count_at_or_below_surgical_max',
    }
    # Both verdicts are on the same return, next to the provenance that explains them.
    assert result['planning_lane'] == 'light'
    assert result['execution_profile'] == 'minimal'


def test_route_surfaces_scope_provenance_under_the_deep_lane_short_circuit(plan_context):
    """Provenance is a property of the request body, so the deep_lane gate cannot erase it.

    ``deep_lane=always`` replaces the signal-scored verdict, but the band
    explanation must survive — otherwise the one configuration most likely to hide
    a miscalibrated band is also the one that stops reporting it.
    """
    _light_setup(plan_context, 'pl-provenance-always')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='always')

    result = cmd_planning_lane_route(_ns_route('pl-provenance-always'))

    assert result['decision_predicate'] == 'plan.phase-1-init.deep_lane=always'
    assert result['scope_provenance']['band_rule'] == 'path_count_at_or_below_surgical_max'


# =============================================================================
# escalate — one-way ratchet
# =============================================================================


def test_escalate_sets_deep_and_lane_escalated(plan_context):
    """escalate sets planning_lane=deep + lane_escalated=true + escalation_trigger."""
    # A light plan that then escalates.
    plan_dir = _light_setup(plan_context, 'pl-escalate')

    result = cmd_planning_lane_escalate(_ns_escalate('pl-escalate', trigger='explosion', persist=True))

    # Return payload.
    assert result['planning_lane'] == 'deep'
    assert result['lane_escalated'] is True
    assert result['escalation_trigger'] == 'explosion'
    assert result['persisted'] is True
    # Persisted metadata.
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['planning_lane'] == 'deep'
    assert status['metadata']['lane_escalated'] is True
    assert status['metadata']['escalation_trigger'] == 'explosion'


def test_escalate_is_monotonic_route_cannot_downgrade(plan_context):
    """After escalate, a subsequent light-resolving route does NOT clobber deep on disk.

    The one-way invariant: once lane_escalated=true is persisted, a fresh route
    that resolves light must not silently downgrade the escalated lane. The route
    verb persists planning_lane, but the sticky lane_escalated flag remains, so
    the deep escalation evidence is preserved.
    """
    # Escalate first.
    plan_dir = _light_setup(plan_context, 'pl-monotonic')
    cmd_planning_lane_escalate(_ns_escalate('pl-monotonic', trigger='premise', persist=True))

    # A light-resolving route does not clear the sticky escalation flag.
    cmd_planning_lane_route(_ns_route('pl-monotonic', persist=True))

    # lane_escalated remains true (sticky), escalation evidence preserved.
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['lane_escalated'] is True
    assert status['metadata']['escalation_trigger'] == 'premise'


@pytest.mark.parametrize('trigger', ['explosion', 'premise', 'cross_cutting'])
def test_escalate_records_each_trigger(plan_context, trigger):
    """Each escalation trigger value round-trips into escalation_trigger."""
    plan_dir = _light_setup(plan_context, f'pl-trig-{trigger}')

    result = cmd_planning_lane_escalate(_ns_escalate(f'pl-trig-{trigger}', trigger=trigger, persist=True))

    assert result['escalation_trigger'] == trigger
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['escalation_trigger'] == trigger


def test_escalate_plan_dir_not_found_errors(plan_context):
    """escalate against a missing plan dir returns a structured error."""
    result = cmd_planning_lane_escalate(_ns_escalate('pl-missing-esc'))

    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


# =============================================================================
# Dispatch wiring
# =============================================================================


def test_planning_lane_route_registered_in_manage_status_dispatch():
    """The route verb resolves to cmd_planning_lane_route in manage-status.py."""
    import argparse  # noqa: PLC0415

    manage_status = load_script_module(
        'plan-marshall', 'manage-status', 'manage-status.py', '_manage_status_dispatch_check_pl_route'
    )

    assert callable(manage_status.cmd_planning_lane_route)
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')
    lane = sub.add_parser('planning-lane')
    lane_sub = lane.add_subparsers(dest='verb')
    route = lane_sub.add_parser('route')
    route.set_defaults(func=manage_status.cmd_planning_lane_route)
    ns = p.parse_args(['planning-lane', 'route'])
    assert ns.func is manage_status.cmd_planning_lane_route


def test_planning_lane_escalate_registered_in_manage_status_dispatch():
    """The escalate verb resolves to cmd_planning_lane_escalate in manage-status.py."""
    import argparse  # noqa: PLC0415

    manage_status = load_script_module(
        'plan-marshall', 'manage-status', 'manage-status.py', '_manage_status_dispatch_check_pl_esc'
    )

    assert callable(manage_status.cmd_planning_lane_escalate)
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')
    lane = sub.add_parser('planning-lane')
    lane_sub = lane.add_subparsers(dest='verb')
    esc = lane_sub.add_parser('escalate')
    esc.set_defaults(func=manage_status.cmd_planning_lane_escalate)
    ns = p.parse_args(['planning-lane', 'escalate'])
    assert ns.func is manage_status.cmd_planning_lane_escalate
