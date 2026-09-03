#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D0/D1/D2 — prose-only corroboration, signal-resolution confidence, and the
orchestrator-spec ``plan_source`` bridge for the planning-lane router.

Context (plan 240, ``truthful-signals``): the router bought ``planning_lane=deep``
on a single fired signal — ``S7:risk_prose`` — against a resolved ``single_module``
scope, over a signal vector in which three metadata inputs and the override were
null. Three defects, three deliverables exercised here:

- **D2** — a prose-only warning must not carry the lane ALONE when a MEASUREMENT
  contradicts it. The corroboration is scoped to the non-committal middle band
  (``single_module``) reached by the ``path_count_middle_band`` rule, so it fixes the
  recorded over-route WITHOUT reopening the prior false-negative fix, which lets S7
  outrank a POSITIVELY-earned narrow band (``surgical``). A ``single_module`` band
  that counted nothing (``pathless_non_empty_body``), an unrecognised band, and a
  caller that supplies no band rule at all are all "no measurement" — S7 keeps the
  lane. ``test_prior_fix_surgical_plus_s7_alone_still_deep`` is the don't-fight
  regression; ``test_planning_lane_risk_prose.py`` keeps the original surgical
  assertions unchanged.
- **D1** — the route reports the resolved-vs-null split of the six READ signals
  (``planning_lane_override`` is excluded — its absence is the normal state), and
  flags ``low_confidence`` when two or more of the four discriminating reads are
  null, so a decision resting on two unresolved inputs cannot read as a confident one.
- **D0/S1** — ``plan_source`` is null for EVERY orchestrator-launched plan because
  phase-1-init records the spec pointer as ``request.md`` ``source_id`` but never
  seeds ``status.metadata.plan_source`` on the file-pointer branch. The router
  bridges the two at read time.

D3 coverage (each of a–d from the plan's deliverable 4):

- ``test_d3a_recorded_vector_does_not_route_deep`` — (a) replay the exact recorded
  vector against a MEASURED middle band (``path_count_middle_band``); it must NOT
  route deep.
- ``test_d3b_orchestrator_spec_resolves_plan_source_nonnull`` — (b) an
  orchestrator-spec-sourced request resolves ``plan_source`` non-null.
- ``test_d3c_several_nulls_reported_low_confidence`` — (c) a several-nulls vector is
  reported low-confidence.
- ``test_d3d_control_deep_warranting_vector_still_routes_deep`` — (d) the CONTROL: a
  genuinely deep-warranting vector still routes deep (a router hardwired to
  ``light`` would pass every OTHER test here).

The measured-evidence bound adds four more:

- ``test_recorded_case_end_to_end_routes_light`` — a body whose 4 distinct paths
  MEASURE the middle band still routes light, end to end.
- ``test_pathless_single_module_band_does_not_suppress_s7`` — a ``single_module``
  band that counted no path suppresses nothing; the warning routes deep.
- ``test_unrecognised_noncommittal_band_does_not_suppress_s7`` — an unrecognised,
  empty or whitespace-padded band is not in the allowlist and suppresses nothing.
- ``test_post_bridge_motivating_vector_is_low_confidence`` — the motivating vector
  is still low-confidence once the bridge resolves ``plan_source``.
"""


from __future__ import annotations

import pytest
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

# The ONE ``band_rule`` that counts as a measurement of the non-committal middle
# band: 4-7 distinct paths counted, landing between the surgical maximum and the
# multi-module floor. Every other band rule leaves S7 uncontradicted.
_MEASURED_MIDDLE_BAND = 'path_count_middle_band'

# =============================================================================
# D3(a) — replay the recorded vector: NOT deep
# =============================================================================


def test_d3a_recorded_vector_does_not_route_deep():
    """(a) The exact recorded signal vector must NOT route deep.

    S7 was the SOLE fired signal against a ``single_module`` scope — the
    non-committal middle band — and the band was MEASURED
    (``path_count_middle_band``), so a real count contradicts the prose warning.
    The warning is uncorroborated and does not carry the lane: the verdict is
    ``light``, and S7 is reported under ``suppressed_signals`` rather than silently
    dropped.
    """
    result = evaluate_signals_pure(
        **_RECORDED_VECTOR, scope_band_rule=_MEASURED_MIDDLE_BAND
    )

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

    result = evaluate_signals_pure(**vector, scope_band_rule=_MEASURED_MIDDLE_BAND)

    assert result['lane'] == 'light'
    assert result['fired_signals'] == []
    assert result['suppressed_signals'] == []


def test_recorded_vector_without_a_measured_band_keeps_the_lane():
    """No band rule supplied means nothing was measured — S7 keeps the lane.

    The same recorded vector, called the way a consumer that cannot supply a band
    rule calls it. Nothing contradicts the author, so the warning carries ``deep``
    and the suppressed set stays empty. This is the negative control for the
    measured-evidence bound: it differs from ``test_d3a_...`` in the band rule alone.
    """
    result = evaluate_signals_pure(**_RECORDED_VECTOR)

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S7:risk_prose']
    assert result['suppressed_signals'] == []


# =============================================================================
# D0/D3(b) — the orchestrator-spec plan_source bridge (end-to-end via the router)
# =============================================================================

def test_recorded_case_end_to_end_routes_light(plan_context):
    """End-to-end wiring of D3(a): a MEASURED middle band that fires ONLY S7 routes
    light through the real command entry point.

    The body names four distinct paths and no fan-out marker, so the band table
    counts them into the middle band (``path_count_middle_band``) — a real
    measurement, not a default. The count also keeps S5 / S1 quiet, while one
    risk-prose phrase (``foundation``) fires S7 alone. The corroboration then denies
    it the lane: ``light``, with S7 suppressed — the recorded over-route, corrected,
    proven through the reader rather than only the pure scorer.
    """
    plan_dir = plan_context.plan_dir_for('pl-recorded-e2e')
    _write_orchestrator_request(
        plan_dir,
        '.plan/local/orchestrator/y/plans/PLAN-03-y.md',
        'Update pkg/one.py, pkg/two.py, pkg/three.py and pkg/four.py. '
        'This is foundation work the rest builds on.',
    )
    _write_status(plan_dir, metadata={})
    _write_references(plan_dir, scope_estimate='single_module')
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_ns_route('pl-recorded-e2e'))

    assert result['scope_provenance']['band_rule'] == _MEASURED_MIDDLE_BAND
    assert result['signals']['risk_prose'] is True
    assert result['planning_lane'] == 'light'
    assert result['fired_signals'] == []
    assert result['suppressed_signals'] == ['S7:risk_prose']


def test_pathless_single_module_band_does_not_suppress_s7(plan_context):
    """A ``single_module`` band that counted NO path cannot contradict the author.

    The body carries a ``manage-*`` notation (so S5 reads it as concrete and S7 stays
    the sole fired signal) but no ``dir/name.ext`` path at all, so the band table
    falls through to ``pathless_non_empty_body`` — ``single_module`` by default,
    measured from nothing. The plain-text request shape is what makes that reachable:
    the orchestrator-spec header carries a path-shaped ``source_id`` the whole-body
    read would count. The warning therefore keeps the lane: ``deep``, with an EMPTY
    suppressed set.
    """
    plan_dir = plan_context.plan_dir_for('pl-pathless')
    _write_plaintext_request(
        plan_dir,
        'Rework the manage-status router. This is foundation work the rest builds on.',
    )
    _write_status(plan_dir, metadata={})
    _write_references(plan_dir, scope_estimate='single_module')
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_ns_route('pl-pathless'))

    assert result['scope_provenance']['band_rule'] == 'pathless_non_empty_body'
    assert result['signals']['risk_prose'] is True
    assert result['planning_lane'] == 'deep'
    assert result['fired_signals'] == ['S7:risk_prose']
    assert result['suppressed_signals'] == []


@pytest.mark.parametrize(
    'scope_estimate',
    ['module_pair', '', ' single_module'],
    ids=['unrecognised_band', 'empty_band', 'whitespace_padded_band'],
)
def test_unrecognised_noncommittal_band_does_not_suppress_s7(scope_estimate):
    """Only the explicit allowlist denies S7 the lane — nothing else does.

    Each band here is neither deep-biasing nor narrow, so the retired
    complement-of-two-sets test admitted all three and suppressed the warning. The
    allowlist admits ``single_module`` alone, so an unrecognised band, an empty one
    and a whitespace-padded one all fall through to "no corroboration" — even with
    the measured middle-band rule supplied, which isolates the allowlist as the
    single discriminator.
    """
    result = evaluate_signals_pure(
        plan_source='lesson',
        scope_estimate=scope_estimate,
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
        risk_prose=True,
        override=None,
        scope_band_rule=_MEASURED_MIDDLE_BAND,
    )

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S7:risk_prose']
    assert result['suppressed_signals'] == []


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

    The recorded vector resolved only 3 of the 6 READ signals — ``plan_source``,
    ``change_type`` and ``compatibility`` were null. Three of the four discriminating
    reads are unresolved, so the block flags it low-confidence and a 3-of-6 decision
    cannot masquerade as a confident one. ``planning_lane_override`` is absent from
    the split entirely: it was never read, only unset.
    """
    result = evaluate_signals_pure(**_RECORDED_VECTOR)
    confidence = result['confidence']

    assert confidence['signals_total'] == 6
    assert confidence['signals_resolved'] == 3
    assert confidence['signals_null'] == 3
    assert confidence['null_signals'] == ['change_type', 'compatibility', 'plan_source']
    assert confidence['low_confidence'] is True


def test_post_bridge_motivating_vector_is_low_confidence():
    """The motivating vector stays low-confidence once the bridge resolves plan_source.

    Two of the four discriminating reads (``change_type``, ``compatibility``) are
    null against four resolved signals — a bare majority rule called that confident,
    because the two body-derived booleans can never be null and always pad the
    resolved side. Keying on the discriminators alone is what makes the flag fire.
    """
    result = evaluate_signals_pure(
        plan_source='.plan/local/orchestrator/x/plans/PLAN-01-x.md',
        scope_estimate='single_module',
        change_type=None,
        compatibility=None,
        request_concrete=True,
        risk_prose=True,
        override=None,
    )
    confidence = result['confidence']

    assert confidence['signals_resolved'] == 4
    assert confidence['null_signals'] == ['change_type', 'compatibility']
    assert confidence['low_confidence'] is True


def test_confidence_high_when_most_signals_resolve():
    """The mirror: a fully-resolved vector is NOT flagged low-confidence.

    Pairs with the low-confidence cases so the flag is shown to discriminate, not to
    fire unconditionally. Every read resolved, so the null set is empty — the unset
    override is no longer counted as an unresolved read.
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
    assert confidence['signals_null'] == 0
    assert confidence['null_signals'] == []
    assert confidence['low_confidence'] is False


def test_one_null_discriminator_is_not_low_confidence():
    """A single unresolved discriminating read is not enough to flag the verdict.

    The boundary companion of the two-null case: the predicate fires at two, so one
    null must not. Without this the ``>= 2`` threshold would be indistinguishable
    from ``>= 1``.
    """
    result = evaluate_signals_pure(
        plan_source=None,
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
        risk_prose=False,
        override=None,
    )
    confidence = result['confidence']

    assert confidence['null_signals'] == ['plan_source']
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
