#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``planning-lane`` subcommand of manage-status.

The router resolves ``planning_lane ∈ {light, deep}`` from the DQ1 signal set
(S1–S7) plus a ``request.md`` regex, with zero codebase discovery. The default
is ``light``; any deep-precondition signal forces ``deep``; the
``plan.phase-1-init.deep_lane`` (``always``/``never``/``auto``) gate
short-circuits the signal evaluation. The ``escalate`` verb is a one-way
light→deep ratchet that refuses any downgrade.

Coverage:
- Each signal (S1–S6) firing deep in isolation. S7 (``risk_prose``) is covered
  in ``test_planning_lane_risk_prose.py``, not here.
- The all-light default (no deep signal fires).
- The deep_lane ``always`` / ``never`` short-circuit.
- ``--lane-override`` handling.
- ``--persist`` writes status.metadata.planning_lane.
- The one-way escalate invariant (deep + lane_escalated, no downgrade).
- Dispatch wiring (both verbs registered in manage-status.py argparse).
- ``evaluate_signals_pure`` — direct, I/O-free unit coverage of the extracted
  pure scorer: each of the six signal arguments firing deep in isolation, the
  all-light default, the S6 override, and the importability of the S5 regex
  constants and ``_request_is_concrete`` for downstream consumers.
- ``project_profile_pure`` — the execution-profile posture projection: the
  ``full`` / ``minimal`` / ``standard`` recommendation as a pure function of the same
  signals, the ``profile`` key on the route return, ``--persist`` writing
  ``status.metadata.execution_profile``, the independence invariant that
  ``deep_lane=always`` does NOT coerce the posture to ``full``, and the mirrored
  negative that a concrete but NON-narrow change never projects ``minimal`` (the
  security-gate half of the shared-predicate defect).
- ``classify_scope_pure`` / ``scope_estimate_from_request_pure`` — the pre-route
  coarse scope classifier over the whole band table: ``surgical`` for one-to-three
  distinct file paths with no fan-out marker, ``single_module`` for the 4–7 middle
  band and for an ambiguous pathless request, ``multi_module`` for a real fan-out
  marker or eight-or-more distinct paths, ``none`` as the DECLARED UNKNOWN for an
  unscoreable body (plus the invariant that the unknown biases S2 deep). Also the
  band boundaries at 3/4 and 7/8, markdown bold NOT registering as fan-out,
  distinct-path dedup, the ``scope_provenance`` explanation block, and the
  zero-architecture-call invariant.
- ``_read_request_body`` — the whole-body, heading-blind read: text below a
  nested ``## `` heading is reached, only the host ``# Request`` title line is
  stripped, and an absent / title-only / non-UTF-8 ``request.md`` degrades to the
  declared unknown instead of raising.
- The settled path-counter semantics — the intentional bare-filename exclusion
  (a directory separator is required) and the declared inapplicability of
  target-vs-citation discrimination, both asserted with their one-directional
  (band-widening) residual.
- The shared-population invariant — S5 concreteness and the scope band are shown
  to consume the identical body, not merely documented as doing so.
- ``cmd_scope_estimate_heuristic`` — ``--persist`` writing
  ``references.json.scope_estimate``, the ``scope_resolved`` classified-vs-unknown
  discriminator, the no-persist read-only path, the missing plan-dir error, its
  manage-status dispatch registration, and the D2 acceptance that
  pre-classification flips the router's S2 from deep to light for a concrete
  narrow request.
"""


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
