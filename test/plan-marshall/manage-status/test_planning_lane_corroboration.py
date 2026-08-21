#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D0/D1/D2 — prose-only corroboration, signal-resolution confidence, and the
orchestrator-spec ``plan_source`` bridge for the planning-lane router.

Context (plan 240, ``truthful-signals``): the router bought ``planning_lane=deep``
on a single fired signal — ``S7:risk_prose`` — against a resolved ``single_module``
scope, over a signal vector in which three metadata inputs and the override were
null. Three defects, three deliverables exercised here:

- **D2** — a prose-only warning must not carry the lane ALONE when it contradicts a
  resolved scope estimate. The corroboration is scoped to the non-committal middle
  band (``single_module``) so it fixes the recorded over-route WITHOUT reopening the
  prior false-negative fix, which lets S7 outrank a POSITIVELY-earned narrow band
  (``surgical``). ``test_prior_fix_surgical_plus_s7_alone_still_deep`` is the
  don't-fight regression; ``test_planning_lane_risk_prose.py`` keeps the original
  surgical assertions unchanged.
- **D1** — the route reports the resolved-vs-null split of the signal vector, so a
  1-of-4 decision cannot read like a 1-of-7 one.
- **D0/S1** — ``plan_source`` is null for EVERY orchestrator-launched plan because
  phase-1-init records the spec pointer as ``request.md`` ``source_id`` but never
  seeds ``status.metadata.plan_source`` on the file-pointer branch. The router
  bridges the two at read time.

D3 coverage (each of a–d from the plan's deliverable 4):

- ``test_d3a_recorded_vector_does_not_route_deep`` — (a) replay the exact recorded
  vector; it must NOT route deep.
- ``test_d3b_orchestrator_spec_resolves_plan_source_nonnull`` — (b) an
  orchestrator-spec-sourced request resolves ``plan_source`` non-null.
- ``test_d3c_several_nulls_reported_low_confidence`` — (c) a several-nulls vector is
  reported low-confidence.
- ``test_d3d_control_deep_warranting_vector_still_routes_deep`` — (d) the CONTROL: a
  genuinely deep-warranting vector still routes deep (a router hardwired to
  ``light`` would pass every OTHER test here).
"""


from __future__ import annotations

from _planning_lane_corroboration_fixtures import (
    _RECORDED_VECTOR,
    _ns_route,
    _write_marshal,
    _write_orchestrator_request,
    _write_plaintext_request,
    _write_references,
    _write_status,
    cmd_planning_lane_route,
    evaluate_signals_pure,
)

# =============================================================================
# D3(a) — replay the recorded vector: NOT deep
# =============================================================================


def test_d3a_recorded_vector_does_not_route_deep():
    """(a) The exact recorded signal vector must NOT route deep.

    S7 was the SOLE fired signal against a resolved ``single_module`` scope — the
    non-committal middle band. Post-fix the prose warning is uncorroborated and
    does not carry the lane: the verdict is ``light``, and S7 is reported under
    ``suppressed_signals`` rather than silently dropped.
    """
    result = evaluate_signals_pure(**_RECORDED_VECTOR)

    assert result['lane'] == 'light'
    assert result['fired_signals'] == []
    assert result['suppressed_signals'] == ['S7:risk_prose']
    # The signal FIRED — it is suppressed, not erased. The record must still say so.
    assert result['signals']['risk_prose'] is True


def test_recorded_vector_routes_deep_without_the_corroboration_fix():
    """Sanity anchor for D3(a): the vector's deep verdict was S7-carried.

    Flipping ``risk_prose`` off (the ONLY fired signal) yields ``light`` with an
    EMPTY suppressed set — proving the deep verdict in the test above came from S7
    and that suppression, not some other signal, is what changed.
    """
    vector = {**_RECORDED_VECTOR, 'risk_prose': False}

    result = evaluate_signals_pure(**vector)

    assert result['lane'] == 'light'
    assert result['fired_signals'] == []
    assert result['suppressed_signals'] == []


# =============================================================================
# D0/D3(b) — the orchestrator-spec plan_source bridge (end-to-end via the router)
# =============================================================================

def test_recorded_case_end_to_end_routes_light(plan_context):
    """End-to-end wiring of D3(a): a single_module request whose body fires ONLY S7
    routes light through the real command entry point.

    The scope is persisted ``single_module`` and the body names a concrete path (so
    S5 / S1 stay quiet) while carrying one risk-prose phrase (``foundation``), so S7
    is the sole fired signal. The corroboration then denies it the lane: ``light``,
    with S7 suppressed — the recorded over-route, corrected, proven through the
    reader rather than only the pure scorer.
    """
    plan_dir = plan_context.plan_dir_for('pl-recorded-e2e')
    _write_orchestrator_request(
        plan_dir,
        '.plan/local/orchestrator/y/plans/PLAN-03-y.md',
        'Update pkg/one.py. This is foundation work the rest builds on.',
    )
    _write_status(plan_dir, metadata={})
    _write_references(plan_dir, scope_estimate='single_module')
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_ns_route('pl-recorded-e2e'))

    assert result['signals']['risk_prose'] is True
    assert result['planning_lane'] == 'light'
    assert result['fired_signals'] == []
    assert result['suppressed_signals'] == ['S7:risk_prose']


# =============================================================================
# D3(d) — CONTROL: a genuinely deep-warranting vector still routes deep
# =============================================================================


def test_d3d_control_deep_warranting_vector_still_routes_deep():
    """(d) CONTROL — a genuinely deep-warranting vector still routes deep.

    The most important test in the plan: everything else confirms the router stops
    over-escalating; ONLY this confirms it can still escalate. A router hardwired to
    ``light`` would pass every other case here and fail this one. The vector fires
    several independent deep signals (broad scope → S2, generative change → S3,
    breaking compat → S4, vague request → S5, free-form source → S1), so the
    prose-only corroboration never applies and the lane is a confident deep.
    """
    result = evaluate_signals_pure(
        plan_source=None,
        scope_estimate='multi_module',
        change_type='feature',
        compatibility='breaking',
        request_concrete=False,
        risk_prose=True,
        override=None,
    )

    assert result['lane'] == 'deep'
    assert 'S2:scope_estimate' in result['fired_signals']
    # Not a lone-prose verdict — corroboration cannot fire, nothing is suppressed.
    assert result['suppressed_signals'] == []
    assert result['confidence']['low_confidence'] is False


# =============================================================================
# D2 — the corroboration boundary (don't-fight regression + corroborated deep)
# =============================================================================


def test_prior_fix_surgical_plus_s7_alone_still_deep():
    """The prior false-negative fix is preserved: S7 alone STILL carries a surgical band.

    ``surgical`` is a POSITIVELY-earned narrow verdict; an author's explicit prose
    warning overriding it is a high-information act, and the prior fix (see
    ``test_planning_lane_risk_prose.py``) deliberately lets it win. The
    corroboration is scoped to the non-committal middle band only, so this case is
    untouched — the two fixes do not fight.
    """
    result = evaluate_signals_pure(
        plan_source='lesson',
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
        risk_prose=True,
        override=None,
    )

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S7:risk_prose']
    assert result['suppressed_signals'] == []


def test_s7_with_a_corroborator_routes_deep_not_suppressed():
    """S7 is suppressed only when ALONE — a corroborated prose warning still routes deep.

    Here a ``multi_module`` scope fires S2 alongside S7, so ``fired`` is not the
    prose-only singleton and nothing is suppressed. A genuinely large change that
    also carries an author warning is never de-escalated.
    """
    result = evaluate_signals_pure(
        plan_source='lesson',
        scope_estimate='multi_module',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
        risk_prose=True,
        override=None,
    )

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S2:scope_estimate', 'S7:risk_prose']
    assert result['suppressed_signals'] == []


def test_single_module_without_s7_is_unaffected():
    """The corroboration touches ONLY the prose-only singleton.

    A ``single_module`` scope with no risk prose and no other deep signal was light
    before and stays light — the rule removes nothing that was not S7-alone.
    """
    result = evaluate_signals_pure(
        plan_source='lesson',
        scope_estimate='single_module',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
        risk_prose=False,
        override=None,
    )

    assert result['lane'] == 'light'
    assert result['fired_signals'] == []
    assert result['suppressed_signals'] == []


# =============================================================================
# D1 — signal-resolution confidence
# =============================================================================


def test_d3c_several_nulls_reported_low_confidence():
    """(c) A signal vector with several nulls is reported low-confidence.

    The recorded vector resolved only 3 of 7 signals — ``plan_source``,
    ``change_type``, ``compatibility`` and ``planning_lane_override`` were null. The
    confidence block reports that split and flags it low-confidence, so a 1-of-4
    decision cannot masquerade as a 1-of-7 one.
    """
    result = evaluate_signals_pure(**_RECORDED_VECTOR)
    confidence = result['confidence']

    assert confidence['signals_total'] == 7
    assert confidence['signals_resolved'] == 3
    assert confidence['signals_null'] == 4
    assert confidence['null_signals'] == [
        'change_type',
        'compatibility',
        'plan_source',
        'planning_lane_override',
    ]
    assert confidence['low_confidence'] is True


def test_confidence_high_when_most_signals_resolve():
    """The mirror: a mostly-resolved vector is NOT flagged low-confidence.

    Pairs with the low-confidence case so the flag is shown to discriminate, not to
    fire unconditionally. Only the (unset) override is null here.
    """
    result = evaluate_signals_pure(
        plan_source='lesson',
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
        risk_prose=False,
        override=None,
    )
    confidence = result['confidence']

    assert confidence['signals_resolved'] == 6
    assert confidence['signals_null'] == 1
    assert confidence['null_signals'] == ['planning_lane_override']
    assert confidence['low_confidence'] is False


# =============================================================================
# D0/D3(b) — the orchestrator-spec plan_source bridge (end-to-end via the router)
# =============================================================================

def test_d3b_orchestrator_spec_resolves_plan_source_nonnull(plan_context):
    """(b) An orchestrator-spec-sourced request resolves ``plan_source`` non-null.

    ``status.metadata`` carries NO ``plan_source`` (the file-pointer branch never
    seeds it). The router bridges the retained ``request.md`` ``source_id`` pointer,
    so ``plan_source`` resolves to that pointer instead of null — and therefore
    counts as resolved in the confidence split.
    """
    plan_dir = plan_context.plan_dir_for('pl-d3b')
    spec_id = '.plan/local/orchestrator/some-slug/plans/PLAN-07-do-a-thing.md'
    _write_orchestrator_request(plan_dir, spec_id, 'Implement the four targets in pkg/a.py.')
    _write_status(plan_dir, metadata={})
    _write_references(plan_dir, scope_estimate='single_module')
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_ns_route('pl-d3b'))

    assert result['signals']['plan_source'] == spec_id
    assert 'plan_source' not in result['confidence']['null_signals']


def test_metadata_plan_source_wins_over_the_bridge(plan_context):
    """A lesson/recipe-seeded ``plan_source`` is never overwritten by the bridge.

    The bridge fills a null only. When ``status.metadata.plan_source`` is present it
    wins, even if ``request.md`` also carries a ``source_id``.
    """
    plan_dir = plan_context.plan_dir_for('pl-d3b-meta')
    _write_orchestrator_request(
        plan_dir, '.plan/local/orchestrator/x/plans/PLAN-01-x.md', 'Implement pkg/a.py.'
    )
    _write_status(plan_dir, metadata={'plan_source': '2026-05-11-08-004'})
    _write_references(plan_dir, scope_estimate='single_module')
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_ns_route('pl-d3b-meta'))

    assert result['signals']['plan_source'] == '2026-05-11-08-004'


def test_plaintext_description_does_not_resolve_orchestrator_provenance(plan_context):
    """A plain-text ``description`` (no ``source_id``) stays free-form — plan_source null.

    The bridge is scoped to the file-pointer shape; a plain-text description is
    genuinely free-form and must keep a null ``plan_source`` so S1 continues to
    treat it as such.
    """
    plan_dir = plan_context.plan_dir_for('pl-d3b-plain')
    _write_plaintext_request(plan_dir, 'Make the thing better somehow.')
    _write_status(plan_dir, metadata={})
    _write_references(plan_dir, scope_estimate='single_module')
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_ns_route('pl-d3b-plain'))

    assert result['signals']['plan_source'] is None
    assert 'plan_source' in result['confidence']['null_signals']
