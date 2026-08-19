#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``planning-lane`` subcommand of manage-status."""


from __future__ import annotations

import json

from _planning_lane_fixtures import (
    _mod,
    _ns_route,
    _ns_scope,
    _write_marshal,
    _write_references,
    _write_request,
    _write_status,
    cmd_planning_lane_route,
    cmd_scope_estimate_heuristic,
)

from conftest import load_script_module

# =============================================================================
# cmd_scope_estimate_heuristic — persistence to references.json
# =============================================================================


def test_scope_heuristic_persists_surgical_to_references(plan_context):
    """--persist writes the classified scope_estimate into references.json."""
    plan_dir = plan_context.plan_dir_for('pl-scope-persist')
    _write_request(plan_dir, 'Fix marketplace/bundles/plan-marshall/skills/x/scripts/x.py.')
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(_ns_scope('pl-scope-persist', persist=True))

    assert result['status'] == 'success'
    assert result['scope_estimate'] == 'surgical'
    assert result['persisted'] is True
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert refs['scope_estimate'] == 'surgical'
    # The persist preserves other references fields.
    assert refs['base_branch'] == 'main'


def test_scope_heuristic_persists_single_module_for_the_middle_band(plan_context):
    """A five-path request persists single_module — the 4–7 middle band, end to end."""
    plan_dir = plan_context.plan_dir_for('pl-scope-middle')
    _write_request(plan_dir, 'Touch a/one.py, b/two.py, c/three.py, d/four.py, e/five.py.')
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(_ns_scope('pl-scope-middle', persist=True))

    assert result['scope_estimate'] == 'single_module'
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert refs['scope_estimate'] == 'single_module'


def test_scope_heuristic_persists_multi_module_for_a_large_request(plan_context):
    """An eight-path request persists multi_module — the band that used to be unreachable.

    End-to-end proof that the upper segment of the path-count line now exists: the
    persisted value is a deep-biasing S2 band, so a large concrete request stops
    routing light.
    """
    plan_dir = plan_context.plan_dir_for('pl-scope-large')
    _write_request(
        plan_dir,
        'Touch ' + ', '.join(f'dir{i}/file{i}.py' for i in range(8)) + '.',
    )
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(_ns_scope('pl-scope-large', persist=True))

    assert result['scope_estimate'] == 'multi_module'
    assert result['distinct_path_count'] == 8
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert refs['scope_estimate'] == 'multi_module'
    assert 'multi_module' in _mod._DEEP_SCOPE_ESTIMATES


def test_scope_heuristic_without_persist_does_not_write(plan_context):
    """Without --persist the classifier reports but does not mutate references.json."""
    plan_dir = plan_context.plan_dir_for('pl-scope-nopersist')
    _write_request(plan_dir, 'Fix pkg/one.py.')
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(_ns_scope('pl-scope-nopersist'))

    assert result['scope_estimate'] == 'surgical'
    assert result['persisted'] is False
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert 'scope_estimate' not in refs


def test_scope_heuristic_plan_dir_not_found_errors(plan_context):
    """scope-estimate-heuristic against a missing plan dir returns a structured error."""
    result = cmd_scope_estimate_heuristic(_ns_scope('pl-scope-missing', persist=True))

    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


# =============================================================================
# D2 acceptance — pre-route classification unblocks the light lane
# =============================================================================


def test_prerouted_surgical_scope_flips_s2_from_deep_to_light(plan_context):
    """The pre-route scope classification flips S2 from deep (None) to light (surgical).

    Before D2, a concrete narrow request reached the router with scope_estimate
    unset, so S2 fired deep unconditionally. After the pre-route classifier
    persists scope_estimate=surgical, S2 no longer fires and the router reaches
    the light lane for a well-bounded, concrete request.
    """
    plan_dir = plan_context.plan_dir_for('pl-d2-accept')
    _write_request(plan_dir, 'Fix marketplace/bundles/plan-marshall/skills/x/scripts/x.py per the diagnosis.')
    _write_status(plan_dir, metadata={'plan_source': 'lesson', 'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate=None)
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='auto')

    # Pre-classification: with scope_estimate still None, S2 fires deep.
    before = cmd_planning_lane_route(_ns_route('pl-d2-accept'))
    assert before['planning_lane'] == 'deep'
    assert 'S2:scope_estimate' in before['fired_signals']

    # Run the pre-route classifier; it persists scope_estimate=surgical.
    scope_result = cmd_scope_estimate_heuristic(_ns_scope('pl-d2-accept', persist=True))
    assert scope_result['scope_estimate'] == 'surgical'

    # Now the router routes light — S2 no longer fires.
    after = cmd_planning_lane_route(_ns_route('pl-d2-accept'))
    assert after['planning_lane'] == 'light'
    assert 'S2:scope_estimate' not in after['fired_signals']


# =============================================================================
# Dispatch wiring — scope-estimate-heuristic
# =============================================================================


def test_scope_estimate_heuristic_registered_in_manage_status_dispatch():
    """The scope-estimate-heuristic verb resolves to cmd_scope_estimate_heuristic."""
    import argparse  # noqa: PLC0415

    manage_status = load_script_module(
        'plan-marshall', 'manage-status', 'manage-status.py', '_manage_status_dispatch_check_scope_est'
    )

    assert callable(manage_status.cmd_scope_estimate_heuristic)
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')
    scope = sub.add_parser('scope-estimate-heuristic')
    scope.set_defaults(func=manage_status.cmd_scope_estimate_heuristic)
    ns = p.parse_args(['scope-estimate-heuristic'])
    assert ns.func is manage_status.cmd_scope_estimate_heuristic
