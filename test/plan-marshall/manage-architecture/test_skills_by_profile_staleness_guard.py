#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the skills_by_profile staleness guard in ``_cmd_client_query.py``.

The guard is a non-blocking, read-path WARNING surface: it flags a module whose
``skills_by_profile`` references skill notations absent from the live registry
(retired / renamed IDs) or is missing entirely. It never raises. The pure
``detect_stale_skills_by_profile`` core takes an injected ``is_live`` predicate
so staleness detection is deterministic without a real bundle tree.
"""

from conftest import load_script_module

_cmd_client_query = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client_query.py', '_cmd_client_query'
)

detect_stale_skills_by_profile = _cmd_client_query.detect_stale_skills_by_profile
_iter_skill_notations = _cmd_client_query._iter_skill_notations


# A retired ID that no longer resolves in the registry.
_STALE_NOTATION = 'plan-marshall:dev-agent-behavior-rules'
_LIVE_NOTATION = 'plan-marshall:persona-plan-marshall-agent'


def _profile_map(*skills: str) -> dict:
    """Build a skills_by_profile map with the given notations under one profile."""
    return {'implementation': {'defaults': [{'skill': s, 'description': f'desc for {s}'} for s in skills]}}


def _all_live(_notation: str) -> bool:
    return True


def _none_live(_notation: str) -> bool:
    return False


def test_warns_on_retired_notation():
    """A retired skill notation absent from the live registry surfaces one WARNING."""
    sbp = _profile_map(_LIVE_NOTATION, _STALE_NOTATION)
    warnings = detect_stale_skills_by_profile('default', sbp, lambda n: n != _STALE_NOTATION)
    assert len(warnings) == 1
    assert _STALE_NOTATION in warnings[0]
    assert 'absent from the live registry' in warnings[0]


def test_warns_on_missing_map():
    """A missing/empty skills_by_profile surfaces one WARNING without a registry lookup."""
    warnings = detect_stale_skills_by_profile('documentation', {}, _none_live)
    assert len(warnings) == 1
    assert 'missing or empty' in warnings[0]


def test_no_warning_when_all_notations_live():
    """A fully-resolvable skills_by_profile produces no WARNING."""
    sbp = _profile_map(_LIVE_NOTATION)
    assert detect_stale_skills_by_profile('default', sbp, _all_live) == []


def test_guard_is_non_blocking():
    """The guard returns a list and never raises, even for an all-stale map."""
    sbp = _profile_map(_STALE_NOTATION)
    warnings = detect_stale_skills_by_profile('default', sbp, _none_live)
    assert isinstance(warnings, list)
    assert len(warnings) == 1


def test_iter_collects_defaults_and_optionals():
    """``_iter_skill_notations`` walks both defaults and optionals, and string entries."""
    sbp = {
        'implementation': {
            'defaults': [{'skill': 'a:one'}, 'b:two'],
            'optionals': [{'skill': 'c:three'}],
        }
    }
    assert _iter_skill_notations(sbp) == ['a:one', 'b:two', 'c:three']


def test_multiple_stale_notations_are_sorted_and_deduped():
    """Several stale notations across profiles are reported once each, sorted."""
    sbp = {
        'implementation': {'defaults': [{'skill': 'z:retired'}, {'skill': 'a:retired'}]},
        'quality': {'defaults': [{'skill': 'a:retired'}]},
    }
    warnings = detect_stale_skills_by_profile('default', sbp, _none_live)
    assert len(warnings) == 1
    assert 'a:retired, z:retired' in warnings[0]


# =============================================================================
# Per-profile unresolved-vs-declared-minimal distinction
# =============================================================================
#
# A per-profile empty resolution (a profile block present in the map but with
# no defaults and no optionals) must be distinguishable from a deliberately
# MINIMAL profile that declares itself with ``"minimal": true``. Before the
# guard learned the distinction, a non-empty map whose one profile block was
# empty produced NO signal at all — the whole-map "missing or empty" branch did
# not fire, and an empty block contributes no notations to the stale check — so
# an unresolved profile and a deliberately-minimal one were byte-identical here.


def _map_with_empty_profile(*, declared_minimal: bool) -> dict:
    """Build a map with a populated ``implementation`` and an empty ``module_testing``.

    ``declared_minimal`` toggles the ``"minimal": true`` declaration on the
    empty ``module_testing`` block — the single bit that must separate a
    deliberately-minimal profile from an unmarked-empty one.
    """
    module_testing: dict = {'defaults': [], 'optionals': []}
    if declared_minimal:
        module_testing['minimal'] = True
    return {
        'implementation': {'defaults': [{'skill': _LIVE_NOTATION, 'description': 'core'}]},
        'module_testing': module_testing,
    }


def test_warns_on_unresolved_undeclared_empty_profile():
    """A present-but-empty profile with no minimal declaration surfaces the named condition.

    This is the empty-case assertion. It FAILS before the guard fix: the pre-fix
    function returns ``[]`` for a non-empty map whose ``module_testing`` block is
    empty, so the unresolved profile is invisible.
    """
    sbp = _map_with_empty_profile(declared_minimal=False)
    warnings = detect_stale_skills_by_profile('default', sbp, _all_live)
    assert any('module_testing' in w and 'not declared minimal' in w for w in warnings), warnings


def test_no_warning_on_declared_minimal_profile():
    """A present-but-empty profile that DECLARES minimality surfaces no condition — the escape hatch."""
    sbp = _map_with_empty_profile(declared_minimal=True)
    warnings = detect_stale_skills_by_profile('default', sbp, _all_live)
    assert not any('module_testing' in w for w in warnings), warnings


def test_declared_minimal_and_unmarked_empty_are_distinguishable():
    """The two states differ by exactly the declaration: one warns, the other does not.

    Both directions asserted together — the vacuous-guard trap this deliverable
    exists to close. An empty-only assertion cannot detect that the
    declared-minimal escape hatch silently swallowed the signal.
    """
    unmarked = detect_stale_skills_by_profile('default', _map_with_empty_profile(declared_minimal=False), _all_live)
    declared = detect_stale_skills_by_profile('default', _map_with_empty_profile(declared_minimal=True), _all_live)
    unmarked_condition = any('module_testing' in w and 'not declared minimal' in w for w in unmarked)
    declared_condition = any('module_testing' in w for w in declared)
    assert unmarked_condition and not declared_condition
