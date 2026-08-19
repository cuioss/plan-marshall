#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``planning-lane`` subcommand of manage-status."""


from __future__ import annotations

import json
from argparse import Namespace

import pytest
from _planning_lane_fixtures import (
    _light_setup,
    _mod,
    _ns_route,
    _pure,
    _write_ingested_request,
    _write_marshal,
    _write_references,
    _write_status,
    cmd_planning_lane_route,
    cmd_scope_estimate_heuristic,
    project_profile_pure,
)


def test_concreteness_and_scope_consume_the_identical_body(plan_context, monkeypatch):
    """S5 concreteness and the scope band read the SAME text — asserted, not claimed.

    The two signals are corroborating readings of one request. If one consumer
    were ever narrowed (say, to a declared-surface region) while the other kept
    the whole body, they would silently describe different documents and their
    agreement would stop meaning anything. This records the shared-population
    invariant behaviourally by capturing what each consumer actually receives.
    """
    plan_dir = plan_context.plan_dir_for('pl-shared-population')
    _write_ingested_request(plan_dir)
    _write_status(plan_dir)
    _write_references(plan_dir, scope_estimate=None)

    seen: list[str] = []
    real_read = _mod._read_request_body

    def _recording_read(plan_id: str) -> str:
        # _mod is loaded dynamically, so real_read is untyped (Any) to mypy.
        body: str = real_read(plan_id)
        seen.append(body)
        return body

    monkeypatch.setattr(_mod, '_read_request_body', _recording_read)

    _mod._evaluate_signals('pl-shared-population', {})
    cmd_scope_estimate_heuristic(Namespace(plan_id='pl-shared-population', persist=False))

    assert len(seen) == 2, 'both consumers must go through _read_request_body'
    assert seen[0] == seen[1] != ''


# =============================================================================
# project_profile_pure — execution-profile posture projection
# =============================================================================
#
# The posture projection recommends minimal / standard / full over the SAME signals
# the lane verdict scores. It is a pure derivation (no I/O, no cognition) and is
# independent of the deep_lane ceremony gate (deep_lane governs planning depth,
# not the profile — §4.2 of the lane-selection outline).


@pytest.mark.parametrize('change_type', ['feature', 'feature_breaking'])
@pytest.mark.parametrize('scope_estimate', ['multi_module', 'broad'])
def test_profile_generative_broad_change_projects_full(change_type, scope_estimate):
    """A generative change over a broad scope projects the full posture."""
    posture = project_profile_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility='deprecation',
        request_concrete=True,
    )

    assert posture == 'full'


def test_profile_narrow_concrete_breaking_change_projects_minimal():
    """A surgical, concretely-specified breaking generative change projects minimal.

    The narrow-and-concrete predicate dominates: a bounded surgical fix stays
    ``minimal`` even when its change_type reads generative and its compatibility
    reads breaking. (A BROAD generative breaking change still projects full — see
    ``test_profile_generative_broad_change_projects_full``.)
    """
    posture = project_profile_pure(
        scope_estimate='surgical',
        change_type='feature',
        compatibility='breaking',
        request_concrete=True,
    )

    assert posture == 'minimal'


def test_profile_narrow_concrete_nongenerative_change_projects_minimal():
    """A non-generative, SURGICAL, concretely-specified change projects minimal.

    ``surgical`` is the sole member of ``_NARROW_SCOPE_ESTIMATES``, so this case is
    no longer parametrized over ``single_module``: the middle band does not earn
    the carve-out. See
    ``test_profile_non_narrow_concrete_change_does_not_project_minimal`` for the
    mirrored negative.
    """
    posture = project_profile_pure(
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
    )

    assert posture == 'minimal'


def test_profile_narrow_nongenerative_but_vague_request_projects_standard():
    """A narrow non-generative change with a vague request falls back to standard."""
    posture = project_profile_pure(
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=False,
    )

    assert posture == 'standard'


def test_profile_generative_narrow_concrete_change_projects_minimal():
    """A generative but SURGICAL, concretely-specified change projects minimal.

    Under the narrow-and-concrete carve-out the bounded, well-anchored generative
    change is recommended ``minimal`` — the narrow, concrete bound dominates the
    generative signal. Narrowness is now literal: only ``surgical`` qualifies.
    """
    posture = project_profile_pure(
        scope_estimate='surgical',
        change_type='feature',
        compatibility='deprecation',
        request_concrete=True,
    )

    assert posture == 'minimal'


@pytest.mark.parametrize('scope_estimate', ['single_module', 'multi_module'])
@pytest.mark.parametrize('change_type', ['bug_fix', 'feature'])
def test_profile_non_narrow_concrete_change_does_not_project_minimal(scope_estimate, change_type):
    """The mirrored negative: a concrete but NON-narrow change never projects minimal.

    This is the security-gate half of the defect. ``_NARROW_SCOPE_ESTIMATES`` is
    shared verbatim with ``evaluate_signals_pure``, so before the narrowing a
    ``single_module`` band collapsed the posture to ``minimal`` — which drops the
    security audit, the sonar round-trip and the self-review — purely on the
    strength of a catch-all band. Asserting the lane alone would have left this
    path live, so the posture is pinned independently here.
    """
    posture = project_profile_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility='breaking',
        request_concrete=True,
    )

    assert posture != 'minimal'


def test_profile_projection_is_deterministic_over_the_signal_set():
    """The projection is a pure function — identical inputs yield identical output."""
    kwargs = {
        'scope_estimate': 'multi_module',
        'change_type': 'feature',
        'compatibility': 'breaking',
        'request_concrete': False,
    }

    first = project_profile_pure(**kwargs)
    second = project_profile_pure(**kwargs)

    assert first == second == 'full'


def test_evaluate_signals_pure_emits_profile_projection():
    """evaluate_signals_pure carries the profile projection alongside the lane verdict."""
    result = _pure(scope_estimate='multi_module', change_type='feature')

    assert result['profile']['recommended_posture'] == 'full'
    assert result['profile']['candidate_postures'] == ['minimal', 'standard', 'full']


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


def test_persist_writes_execution_profile_metadata(plan_context):
    """--persist writes the projected posture into status.metadata.execution_profile."""
    plan_dir = _light_setup(plan_context, 'pl-profile-persist')

    result = cmd_planning_lane_route(_ns_route('pl-profile-persist', persist=True))

    assert result['persisted'] is True
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['execution_profile'] == 'minimal'


def test_route_without_persist_does_not_write_execution_profile(plan_context):
    """Without --persist the projected posture is not written to status.json."""
    plan_dir = _light_setup(plan_context, 'pl-profile-nopersist')

    cmd_planning_lane_route(_ns_route('pl-profile-nopersist'))

    status = json.loads((plan_dir / 'status.json').read_text())
    assert 'execution_profile' not in status.get('metadata', {})
