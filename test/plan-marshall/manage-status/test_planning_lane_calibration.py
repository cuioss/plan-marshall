#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Calibration matrix for the narrow-and-concrete carve-out of the planning-lane router.

The carve-out relaxes the S3 (generative ``change_type``) and S4 (breaking
``compatibility``) deep-bias signals for a positively-bounded request — one that
is BOTH narrowly scoped (``scope_estimate ∈ _NARROW_SCOPE_ESTIMATES``, whose sole
member is ``surgical``) AND concretely specified (``request_concrete=True``). For
such a request S3/S4 must not force ``deep`` *alone*, and ``project_profile_pure``
recommends the ``minimal`` posture over the same predicate. The conservative
unknown-to-deep default is preserved: S1 (free-form source AND non-concrete), S2
(broad/unknown scope), and S5 (no anchors) continue to bias ``deep`` unchanged.

**Narrowness is literal.** ``single_module`` is the catch-all middle band and
``multi_module`` is the large band; neither is narrow, so neither earns the
carve-out. That matters twice over, because ``_NARROW_SCOPE_ESTIMATES`` is shared
verbatim by ``evaluate_signals_pure`` (the lane verdict) and
``project_profile_pure`` (the posture projection): one wrong narrow verdict
corrupts BOTH the lane and the execution posture, and a ``minimal`` posture drops
the security audit. Every band case in this module therefore asserts the lane AND
the posture — a lane-only assertion would leave the security-gate suppression path
live.

This module tests ``evaluate_signals_pure`` and ``project_profile_pure`` directly
over the calibration corners:

- (i)   surgical + concrete + breaking          → light  / minimal
- (ii)  surgical + concrete + feature           → light  / minimal
- (ii') non-narrow + concrete + breaking/feature → deep   / not minimal (mirrored)
- (iii) unknown scope (conservative default)    → deep   (unchanged)
- (iv)  broad + feature + breaking              → deep   / full (unchanged)
"""

from __future__ import annotations

import pytest

from conftest import load_script_module

_mod = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_planning_lane.py', '_cmd_planning_lane_calibration_under_test'
)
evaluate_signals_pure = _mod.evaluate_signals_pure
project_profile_pure = _mod.project_profile_pure


# =============================================================================
# (i) + (ii) — narrow + concrete relaxes S3/S4 (the carve-out)
# =============================================================================


def test_narrow_concrete_breaking_scores_light():
    """(i) A SURGICAL, concretely-specified BREAKING change does not fire S4 → light.

    No longer parametrized over ``single_module``: that band is not narrow, so it
    does not receive the carve-out. See
    ``test_non_narrow_concrete_breaking_still_fires_s4`` for the mirrored case.
    """
    result = evaluate_signals_pure(
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='breaking',
        plan_source='lesson',
        request_concrete=True,
    )

    assert result['lane'] == 'light'
    assert 'S4:compatibility' not in result['fired_signals']
    assert result['fired_signals'] == []
    # The mirror guard: genuinely-surgical work also keeps its minimal posture.
    assert result['profile']['recommended_posture'] == 'minimal'


@pytest.mark.parametrize('change_type', ['feature', 'feature_breaking'])
def test_narrow_concrete_feature_scores_light(change_type):
    """(ii) A SURGICAL, concretely-specified generative change does not fire S3 → light."""
    result = evaluate_signals_pure(
        scope_estimate='surgical',
        change_type=change_type,
        compatibility='deprecation',
        plan_source='lesson',
        request_concrete=True,
    )

    assert result['lane'] == 'light'
    assert 'S3:change_type' not in result['fired_signals']
    assert result['fired_signals'] == []
    assert result['profile']['recommended_posture'] == 'minimal'


# =============================================================================
# (ii') Mirrored — a NON-narrow concrete request keeps its S3/S4 escalation
# =============================================================================
#
# The core defect: the catch-all `single_module` band used to satisfy
# `narrow_and_concrete`, which suppressed S3/S4 (→ light) and returned MINIMAL
# from project_profile_pure (→ security audit dropped). One wrong narrow verdict,
# two corrupted decisions — so both are asserted for both non-narrow bands.


@pytest.mark.parametrize('scope_estimate', ['single_module', 'multi_module'])
def test_non_narrow_concrete_breaking_still_fires_s4(scope_estimate):
    """(ii') A concrete BREAKING change over a non-narrow band fires S4 → deep, not minimal."""
    result = evaluate_signals_pure(
        scope_estimate=scope_estimate,
        change_type='bug_fix',
        compatibility='breaking',
        plan_source='lesson',
        request_concrete=True,
    )

    assert result['lane'] == 'deep'
    assert 'S4:compatibility' in result['fired_signals']
    assert result['profile']['recommended_posture'] != 'minimal'


@pytest.mark.parametrize('scope_estimate', ['single_module', 'multi_module'])
@pytest.mark.parametrize('change_type', ['feature', 'feature_breaking'])
def test_non_narrow_concrete_feature_still_fires_s3(scope_estimate, change_type):
    """(ii') A concrete generative change over a non-narrow band fires S3 → deep, not minimal."""
    result = evaluate_signals_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility='deprecation',
        plan_source='lesson',
        request_concrete=True,
    )

    assert result['lane'] == 'deep'
    assert 'S3:change_type' in result['fired_signals']
    assert result['profile']['recommended_posture'] != 'minimal'


@pytest.mark.parametrize('scope_estimate', ['single_module', 'multi_module'])
def test_non_narrow_bands_are_outside_the_narrow_frozenset(scope_estimate):
    """The membership behind both corrections, pinned directly.

    ``_NARROW_SCOPE_ESTIMATES`` is the single shared frozenset. Widening it back to
    include ``single_module`` would silently re-suppress S3/S4 *and* re-collapse the
    posture to ``minimal``, so the membership itself is asserted alongside the two
    behavioural consequences above.
    """
    assert scope_estimate not in _mod._NARROW_SCOPE_ESTIMATES
    assert _mod._NARROW_SCOPE_ESTIMATES == frozenset({'surgical'})


def test_narrow_concrete_feature_and_breaking_together_score_light():
    """The carve-out suppresses S3 AND S4 co-firing for the positively-bounded case."""
    result = evaluate_signals_pure(
        scope_estimate='surgical',
        change_type='feature_breaking',
        compatibility='breaking',
        plan_source='lesson',
        request_concrete=True,
    )

    assert result['lane'] == 'light'
    assert 'S3:change_type' not in result['fired_signals']
    assert 'S4:compatibility' not in result['fired_signals']


def test_narrow_concrete_breaking_projects_minimal():
    """(i) The surgical+concrete predicate projects the minimal posture even when breaking.

    The mirror guard for the posture axis: ``_SURGICAL_MAX_PATHS`` is untouched by
    the band change, so genuinely-surgical work is not over-escalated.
    """
    posture = project_profile_pure(
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='breaking',
        request_concrete=True,
    )

    assert posture == 'minimal'


@pytest.mark.parametrize('change_type', ['feature', 'feature_breaking'])
def test_narrow_concrete_feature_projects_minimal(change_type):
    """(ii) The surgical+concrete predicate projects minimal even for a generative change."""
    posture = project_profile_pure(
        scope_estimate='surgical',
        change_type=change_type,
        compatibility='deprecation',
        request_concrete=True,
    )

    assert posture == 'minimal'


@pytest.mark.parametrize('scope_estimate', ['single_module', 'multi_module'])
@pytest.mark.parametrize('change_type', ['bug_fix', 'feature', 'feature_breaking'])
def test_non_narrow_concrete_change_never_projects_minimal(scope_estimate, change_type):
    """(ii') The posture axis of the mirrored case, across every change_type.

    ``minimal`` is the posture that drops the security audit, the sonar round-trip
    and the pre-submission self-review. It must be reachable only for genuinely
    bounded work, whatever the change_type reads.
    """
    posture = project_profile_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility='breaking',
        request_concrete=True,
    )

    assert posture != 'minimal'


# =============================================================================
# The carve-out is gated on BOTH narrow AND concrete — neither alone relaxes S3/S4
# =============================================================================


def test_narrow_but_not_concrete_does_not_relax_s4():
    """A narrow but non-concrete breaking change is NOT carved out — S4 (and S5) still fire deep."""
    result = evaluate_signals_pure(
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='breaking',
        plan_source='lesson',
        request_concrete=False,
    )

    assert result['lane'] == 'deep'
    assert 'S4:compatibility' in result['fired_signals']
    assert 'S5:concreteness' in result['fired_signals']


def test_concrete_but_broad_scope_does_not_relax_s3():
    """A concrete but broad-scope feature is NOT carved out — S2 and S3 still fire deep."""
    result = evaluate_signals_pure(
        scope_estimate='multi_module',
        change_type='feature',
        compatibility='deprecation',
        plan_source='lesson',
        request_concrete=True,
    )

    assert result['lane'] == 'deep'
    assert 'S2:scope_estimate' in result['fired_signals']
    assert 'S3:change_type' in result['fired_signals']


# =============================================================================
# (iii) — the conservative unknown-to-deep default is preserved
# =============================================================================


def test_unknown_scope_still_scores_deep():
    """(iii) An unknown (None) scope keeps biasing deep via S2 — the carve-out never applies."""
    result = evaluate_signals_pure(
        scope_estimate=None,
        change_type='bug_fix',
        compatibility='deprecation',
        plan_source='lesson',
        request_concrete=True,
    )

    assert result['lane'] == 'deep'
    assert 'S2:scope_estimate' in result['fired_signals']


def test_unknown_scope_projects_standard():
    """(iii) An unknown scope is neither narrow-and-concrete nor generative-broad → standard."""
    posture = project_profile_pure(
        scope_estimate=None,
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
    )

    assert posture == 'standard'


def test_narrow_non_concrete_free_form_still_scores_deep():
    """The unknown case (non-concrete free-form) still fires S1/S5 deep even when scope is narrow."""
    result = evaluate_signals_pure(
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='deprecation',
        plan_source=None,
        request_concrete=False,
    )

    assert result['lane'] == 'deep'
    assert 'S1:plan_source' in result['fired_signals']
    assert 'S5:concreteness' in result['fired_signals']


# =============================================================================
# (iv) — the correctly-deep broad generative case is unchanged
# =============================================================================


@pytest.mark.parametrize('scope_estimate', ['multi_module', 'broad'])
@pytest.mark.parametrize('change_type', ['feature', 'feature_breaking'])
def test_broad_feature_breaking_scores_deep(scope_estimate, change_type):
    """(iv) A broad generative breaking change still scores deep (S2/S3/S4 all fire)."""
    result = evaluate_signals_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility='breaking',
        plan_source='lesson',
        request_concrete=True,
    )

    assert result['lane'] == 'deep'
    assert 'S2:scope_estimate' in result['fired_signals']
    assert 'S3:change_type' in result['fired_signals']
    assert 'S4:compatibility' in result['fired_signals']


@pytest.mark.parametrize('scope_estimate', ['multi_module', 'broad'])
@pytest.mark.parametrize('change_type', ['feature', 'feature_breaking'])
def test_broad_feature_breaking_projects_full(scope_estimate, change_type):
    """(iv) A broad generative change projects the full posture (unchanged)."""
    posture = project_profile_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility='breaking',
        request_concrete=True,
    )

    assert posture == 'full'


# =============================================================================
# S6 override is NOT relaxed by the carve-out
# =============================================================================


def test_narrow_concrete_with_explicit_deep_override_still_deep():
    """S6 (explicit deep override) is one-way and untouched by the narrow-and-concrete carve-out."""
    result = evaluate_signals_pure(
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='breaking',
        plan_source='lesson',
        request_concrete=True,
        override='deep',
    )

    assert result['lane'] == 'deep'
    assert 'S6:override' in result['fired_signals']
