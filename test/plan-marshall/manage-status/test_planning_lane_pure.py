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
    _pure,
    cmd_planning_lane_escalate,
    cmd_planning_lane_route,
)

from conftest import load_script_module


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


# =============================================================================
# Error path
# =============================================================================


def test_route_plan_dir_not_found_errors(plan_context):
    """route against a missing plan dir returns a structured error."""
    result = cmd_planning_lane_route(_ns_route('pl-missing'))

    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


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


def test_pure_all_light_signals_resolve_light():
    """No signal fires → the pure scorer resolves the light default."""
    result = _pure()

    assert result['lane'] == 'light'
    assert result['fired_signals'] == []


@pytest.mark.parametrize('scope_estimate', ['multi_module', 'broad', 'none'])
def test_pure_s2_deep_scope_estimate_fires_deep(scope_estimate):
    """S2 — each deep scope band fires S2 in isolation."""
    result = _pure(scope_estimate=scope_estimate)

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S2:scope_estimate']


def test_pure_s2_absent_scope_estimate_fires_deep():
    """S2 — an absent (None) scope_estimate biases deep."""
    result = _pure(scope_estimate=None)

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S2:scope_estimate']


@pytest.mark.parametrize('change_type', ['feature', 'feature_breaking'])
def test_pure_s3_generative_change_type_suppressed_when_narrow_and_concrete(change_type):
    """S3 — a generative change_type is carved out under the narrow+concrete baseline.

    The all-light baseline is surgical scope + concrete request, so S3 does not
    fire on its own. S3 firing deep alongside a broad/unknown scope is covered by
    ``test_planning_lane_calibration.py`` and ``test_pure_multiple_deep_signals``.
    """
    result = _pure(change_type=change_type)

    assert result['lane'] == 'light'
    assert 'S3:change_type' not in result['fired_signals']


def test_pure_s4_breaking_compatibility_suppressed_when_narrow_and_concrete():
    """S4 — breaking compatibility is carved out under the narrow+concrete baseline.

    S4 firing deep for a broad/unknown scope is covered by
    ``test_planning_lane_calibration.py`` and ``test_pure_multiple_deep_signals``.
    """
    result = _pure(compatibility='breaking')

    assert result['lane'] == 'light'
    assert 'S4:compatibility' not in result['fired_signals']


def test_pure_s5_non_concrete_request_fires_deep():
    """S5 — a non-concrete request fires S5 in isolation."""
    result = _pure(request_concrete=False)

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S5:concreteness']


@pytest.mark.parametrize('plan_source', [None, '', 'free_form', 'cli'])
def test_pure_s1_free_form_source_with_non_concrete_request_fires_deep(plan_source):
    """S1 — free-form source AND failed concreteness conjunction fires S1 (and S5)."""
    result = _pure(plan_source=plan_source, request_concrete=False)

    assert result['lane'] == 'deep'
    # The S1 conjunction keys off the failed S5 concreteness, so both fire.
    assert 'S1:plan_source' in result['fired_signals']
    assert 'S5:concreteness' in result['fired_signals']


@pytest.mark.parametrize('plan_source', [None, '', 'free_form', 'cli'])
def test_pure_s1_free_form_source_with_concrete_request_stays_light(plan_source):
    """S1 — free-form source ALONE does not fire when the request is concrete."""
    result = _pure(plan_source=plan_source, request_concrete=True)

    assert result['lane'] == 'light'
    assert 'S1:plan_source' not in result['fired_signals']


def test_pure_s6_override_deep_fires_deep():
    """S6 — an explicit deep override fires S6 in isolation."""
    result = _pure(override='deep')

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S6:override']


def test_pure_s6_override_light_does_not_force_deep():
    """S6 — a light override does not fire (the override is one-way to deep)."""
    result = _pure(override='light')

    assert result['lane'] == 'light'
    assert 'S6:override' not in result['fired_signals']


def test_pure_signals_echoes_all_realized_values():
    """The returned ``signals`` dict echoes every realized signal value verbatim.

    Compared with ``==`` on purpose: the point is that the echo is COMPLETE, so a
    signal added to the scorer without being echoed fails here. That is why the S7
    ``risk_prose`` key appears below — it is the pin working as designed, not an
    incidental update. (S7's own behaviour is covered by
    ``test_planning_lane_risk_prose.py``.)
    """
    result = _pure(
        scope_estimate='multi_module',
        change_type='feature',
        compatibility='breaking',
        plan_source='lesson',
        request_concrete=False,
        risk_prose=True,
        override='deep',
    )

    assert result['signals'] == {
        'plan_source': 'lesson',
        'scope_estimate': 'multi_module',
        'change_type': 'feature',
        'compatibility': 'breaking',
        'request_concrete': False,
        'risk_prose': True,
        'planning_lane_override': 'deep',
    }


def test_pure_multiple_deep_signals_accumulate_in_fired_order():
    """Multiple deep signals all appear in fired_signals in canonical S1..S7 order."""
    result = _pure(
        scope_estimate='multi_module',  # S2
        change_type='feature',           # S3
        compatibility='breaking',        # S4
    )

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == [
        'S2:scope_estimate',
        'S3:change_type',
        'S4:compatibility',
    ]
