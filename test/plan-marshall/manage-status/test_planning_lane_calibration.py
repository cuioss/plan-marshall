#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Calibration matrix for the narrow-and-concrete carve-out of the planning-lane router.

The carve-out relaxes the S3 (generative ``change_type``) and S4 (breaking
``compatibility``) deep-bias signals for a positively-bounded request — one that
is BOTH narrowly scoped (``scope_estimate ∈ {surgical, single_module}``) AND
concretely specified (``request_concrete=True``). For such a request S3/S4 must
not force ``deep`` *alone*, and ``project_profile_pure`` recommends the
``minimal`` posture over the same predicate. The conservative unknown-to-deep
default is preserved: S1 (free-form source AND non-concrete), S2 (broad/unknown
scope), and S5 (no anchors) continue to bias ``deep`` unchanged.

This module tests ``evaluate_signals_pure`` and ``project_profile_pure`` directly
over the four calibration corners:

- (i)   narrow + concrete + breaking            → light  / minimal
- (ii)  narrow + concrete + feature             → light  / minimal
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


@pytest.mark.parametrize('scope_estimate', ['surgical', 'single_module'])
def test_narrow_concrete_breaking_scores_light(scope_estimate):
    """(i) A narrow, concretely-specified BREAKING change no longer fires S4 → light."""
    result = evaluate_signals_pure(
        scope_estimate=scope_estimate,
        change_type='bug_fix',
        compatibility='breaking',
        plan_source='lesson',
        request_concrete=True,
    )

    assert result['lane'] == 'light'
    assert 'S4:compatibility' not in result['fired_signals']
    assert result['fired_signals'] == []


@pytest.mark.parametrize('scope_estimate', ['surgical', 'single_module'])
@pytest.mark.parametrize('change_type', ['feature', 'feature_breaking'])
def test_narrow_concrete_feature_scores_light(scope_estimate, change_type):
    """(ii) A narrow, concretely-specified generative change no longer fires S3 → light."""
    result = evaluate_signals_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility='deprecation',
        plan_source='lesson',
        request_concrete=True,
    )

    assert result['lane'] == 'light'
    assert 'S3:change_type' not in result['fired_signals']
    assert result['fired_signals'] == []


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


@pytest.mark.parametrize('scope_estimate', ['surgical', 'single_module'])
def test_narrow_concrete_breaking_projects_minimal(scope_estimate):
    """(i) The narrow+concrete predicate projects the minimal posture even when breaking."""
    posture = project_profile_pure(
        scope_estimate=scope_estimate,
        change_type='bug_fix',
        compatibility='breaking',
        request_concrete=True,
    )

    assert posture == 'minimal'


@pytest.mark.parametrize('scope_estimate', ['surgical', 'single_module'])
@pytest.mark.parametrize('change_type', ['feature', 'feature_breaking'])
def test_narrow_concrete_feature_projects_minimal(scope_estimate, change_type):
    """(ii) The narrow+concrete predicate projects minimal even for a generative change."""
    posture = project_profile_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility='deprecation',
        request_concrete=True,
    )

    assert posture == 'minimal'


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


def test_unknown_scope_projects_auto():
    """(iii) An unknown scope is neither narrow-and-concrete nor generative-broad → auto."""
    posture = project_profile_pure(
        scope_estimate=None,
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
    )

    assert posture == 'auto'


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
