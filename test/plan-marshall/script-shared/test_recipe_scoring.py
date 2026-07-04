#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Unit tests for ``recipe_scoring`` — the single shared recipe-match scorer.

The module under test is imported directly (PYTHONPATH-resolved by the root
conftest, not an executor entry point) and exercised as pure functions. It is
the ONE implementation of the keyword/intent-overlap scoring used by both the
lesson-auto-suggest path (``manage-lessons``'s ``_cmd_auto_suggest``) and the
generalized recipe-match verb (``manage-config``'s ``_cmd_recipe_match``), so
this is the canonical coverage of the scoring core.

Coverage:

* ``tokenize`` — lower-casing, stop-word filtering, short-token dropping,
  empty/``None`` input, hyphen/underscore handling, idempotence;
* ``score_recipe`` keyword arm — overlap drives confidence, no overlap floors
  it, the matched-keyword breakdown is reported, an empty recipe description
  yields a zero keyword score;
* ``score_recipe`` domain arm — exact (case-insensitive) domain match boosts
  confidence, a mismatch / unset domain does not;
* ``score_recipe`` scope arm — surgical↔module and broad↔codebase_wide
  alignments boost confidence, a misaligned scope does not;
* ``score_recipe`` invariants — confidence stays within ``[0.0, 1.0]``, the
  blend weights are honoured, the breakdown structure is complete;
* ``load_registry`` — returns ``[]`` when the discovery helper is absent and
  tolerates discovery exceptions / non-list returns without raising.
"""

from __future__ import annotations

import builtins

import pytest

from recipe_scoring import (
    MIN_CONFIDENCE,
    load_registry,
    score_recipe,
    tokenize,
)

_DOC_RECIPE = {
    'key': 'doc-verify',
    'name': 'Verify Documentation',
    'description': 'Recipe for verifying documentation quality across project',
    'domain': 'documentation',
    'scope': 'codebase_wide',
}


# =============================================================================
# tokenize
# =============================================================================


def test_tokenize_lowercases_and_filters_stopwords():
    """Tokens are lower-cased and common stop-words are dropped."""
    tokens = tokenize('Verify the Documentation and the Links')
    assert 'verify' in tokens
    assert 'documentation' in tokens
    assert 'links' in tokens
    # 'the' / 'and' are stop-words; the casing is normalized to lower.
    assert 'the' not in tokens
    assert 'and' not in tokens
    assert 'Verify' not in tokens


def test_tokenize_drops_short_tokens():
    """Tokens shorter than three characters are dropped as noise."""
    tokens = tokenize('go to ab abc abcd')
    # 'go'/'to'/'ab' are <= 2 chars (or stop-words) and dropped; 'abc' is 3 chars and kept.
    assert 'go' not in tokens
    assert 'ab' not in tokens
    assert 'abc' in tokens
    assert 'abcd' in tokens


def test_tokenize_drops_plan_marshall_vocabulary_stopwords():
    """plan-marshall vocabulary noise (plan/recipe/workflow/standards) is filtered."""
    tokens = tokenize('plan recipe workflow standards refactor')
    assert 'plan' not in tokens
    assert 'recipe' not in tokens
    assert 'workflow' not in tokens
    assert 'standards' not in tokens
    assert 'refactor' in tokens


def test_tokenize_empty_and_none_yield_empty_set():
    """Empty and ``None`` input return an empty set, never raise."""
    assert tokenize('') == set()
    assert tokenize(None) == set()


def test_tokenize_handles_hyphen_and_underscore_tokens():
    """Hyphenated/underscored identifiers survive as single tokens."""
    tokens = tokenize('refactor-to-profile snake_case_name')
    assert 'refactor-to-profile' in tokens
    assert 'snake_case_name' in tokens


def test_tokenize_is_idempotent():
    """Tokenizing twice yields the same set (pure function)."""
    text = 'Verify documentation links across the project.'
    assert tokenize(text) == tokenize(text)


# =============================================================================
# score_recipe — keyword arm
# =============================================================================


def test_score_keyword_overlap_drives_match():
    """Keyword overlap dominates when domain/scope are unset."""
    narrative = tokenize('Verify documentation quality across the entire project.')
    confidence, breakdown = score_recipe(_DOC_RECIPE, narrative, plan_domain=None, plan_scope=None)
    assert confidence > 0.0
    matched = breakdown['matched_keywords']
    assert 'documentation' in matched
    assert 'verifying' in matched or 'quality' in matched or 'project' in matched


def test_score_no_keyword_overlap_floors_keyword_score():
    """A narrative with zero overlap yields a zero keyword score."""
    narrative = tokenize('Completely unrelated subject matter about cooking pasta.')
    confidence, breakdown = score_recipe(_DOC_RECIPE, narrative, plan_domain=None, plan_scope=None)
    assert breakdown['keyword_score'] == 0.0
    assert breakdown['matched_keywords'] == []
    assert confidence == 0.0


def test_score_empty_recipe_description_yields_zero_keyword_score():
    """An empty recipe description/name produces a zero keyword score (no div-by-zero)."""
    recipe = {'key': 'empty', 'name': '', 'description': '', 'domain': '', 'scope': ''}
    narrative = tokenize('Verify documentation links.')
    confidence, breakdown = score_recipe(recipe, narrative, plan_domain=None, plan_scope=None)
    assert breakdown['keyword_score'] == 0.0
    assert confidence == 0.0


def test_score_breakdown_reports_sorted_matched_keywords():
    """The matched-keyword breakdown is sorted for deterministic surfacing."""
    narrative = tokenize('verifying quality documentation project')
    _, breakdown = score_recipe(_DOC_RECIPE, narrative, plan_domain=None, plan_scope=None)
    matched = breakdown['matched_keywords']
    assert matched == sorted(matched)


# =============================================================================
# score_recipe — domain arm
# =============================================================================


def test_score_domain_alignment_boosts_confidence():
    """When plan.domain matches recipe.domain, confidence rises."""
    narrative = tokenize('Verify documentation links.')
    no_domain, _ = score_recipe(_DOC_RECIPE, narrative, plan_domain=None, plan_scope=None)
    with_domain, breakdown = score_recipe(_DOC_RECIPE, narrative, plan_domain='documentation', plan_scope=None)
    assert with_domain > no_domain
    assert breakdown['domain_score'] == 1.0


def test_score_domain_match_is_case_insensitive():
    """Domain matching ignores case and surrounding whitespace."""
    narrative = tokenize('Verify documentation links.')
    _, breakdown = score_recipe(_DOC_RECIPE, narrative, plan_domain='  Documentation  ', plan_scope=None)
    assert breakdown['domain_score'] == 1.0


def test_score_domain_mismatch_does_not_boost():
    """A non-matching plan domain leaves the domain score at zero."""
    narrative = tokenize('Verify documentation links.')
    _, breakdown = score_recipe(_DOC_RECIPE, narrative, plan_domain='java', plan_scope=None)
    assert breakdown['domain_score'] == 0.0


# =============================================================================
# score_recipe — scope arm
# =============================================================================


def test_score_broad_plan_aligns_with_codebase_wide_recipe():
    """A 'broad'-scoped plan aligns with a codebase_wide recipe."""
    narrative = tokenize('Verify documentation links.')
    no_scope, _ = score_recipe(_DOC_RECIPE, narrative, plan_domain=None, plan_scope=None)
    with_scope, breakdown = score_recipe(_DOC_RECIPE, narrative, plan_domain=None, plan_scope='broad')
    assert with_scope > no_scope
    assert breakdown['scope_score'] == 1.0


def test_score_surgical_plan_aligns_with_module_recipe():
    """A 'surgical'-scoped plan aligns with a module-scoped recipe."""
    recipe = {
        'key': 'mod-recipe',
        'name': 'Module Recipe',
        'description': 'A narrowly scoped module-level recipe',
        'domain': 'plan-marshall-plugin-dev',
        'scope': 'module',
    }
    narrative = tokenize('module-level scoped change')
    _, breakdown = score_recipe(recipe, narrative, plan_domain=None, plan_scope='surgical')
    assert breakdown['scope_score'] == 1.0


def test_score_misaligned_scope_does_not_boost():
    """A surgical plan does NOT align with a codebase_wide recipe."""
    narrative = tokenize('Verify documentation links.')
    _, breakdown = score_recipe(_DOC_RECIPE, narrative, plan_domain=None, plan_scope='surgical')
    assert breakdown['scope_score'] == 0.0


# =============================================================================
# score_recipe — invariants
# =============================================================================


def test_score_confidence_stays_within_unit_interval():
    """Even a fully-aligned match keeps confidence within [0.0, 1.0]."""
    narrative = tokenize('verify documentation quality across project')
    confidence, _ = score_recipe(
        _DOC_RECIPE, narrative, plan_domain='documentation', plan_scope='broad'
    )
    assert 0.0 <= confidence <= 1.0


def test_score_blend_weights_are_honoured():
    """Domain (0.25) + scope (0.15) contribute exactly 0.4 with a zero keyword arm."""
    # A narrative with no keyword overlap isolates the domain+scope contribution.
    narrative = tokenize('cooking pasta recipes unrelated')
    confidence, breakdown = score_recipe(
        _DOC_RECIPE, narrative, plan_domain='documentation', plan_scope='broad'
    )
    assert breakdown['keyword_score'] == 0.0
    # 0.6*0 + 0.25*1 + 0.15*1 == 0.4
    assert confidence == pytest.approx(0.4)


def test_score_breakdown_structure_is_complete():
    """The breakdown dict carries every documented key."""
    narrative = tokenize('verify documentation')
    _, breakdown = score_recipe(_DOC_RECIPE, narrative, plan_domain=None, plan_scope=None)
    assert set(breakdown) == {'keyword_score', 'domain_score', 'scope_score', 'matched_keywords'}


def test_min_confidence_floor_is_a_float_in_unit_interval():
    """The exported confidence floor is a sensible probability."""
    assert isinstance(MIN_CONFIDENCE, float)
    assert 0.0 < MIN_CONFIDENCE < 1.0


# =============================================================================
# load_registry
# =============================================================================


def test_load_registry_returns_empty_when_helper_missing(monkeypatch):
    """When the discovery helper cannot be imported, ``[]`` is returned."""
    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == '_cmd_skill_resolution':
            raise ImportError('simulated absence of _cmd_skill_resolution')
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', _fake_import)
    assert load_registry() == []


def test_load_registry_tolerates_discovery_exception(monkeypatch):
    """A discovery-helper exception is swallowed into an empty registry."""
    real_import = builtins.__import__

    def _raising_discover():
        raise OSError('simulated registry read failure')

    import types

    fake_mod = types.ModuleType('_cmd_skill_resolution')
    fake_mod._discover_all_recipes = _raising_discover  # type: ignore[attr-defined]

    def _fake_import(name, *args, **kwargs):
        if name == '_cmd_skill_resolution':
            return fake_mod
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', _fake_import)
    assert load_registry() == []


def test_load_registry_coerces_non_list_to_empty(monkeypatch):
    """A non-list discovery return is normalized to an empty list."""
    import types

    fake_mod = types.ModuleType('_cmd_skill_resolution')
    fake_mod._discover_all_recipes = lambda: {'not': 'a list'}  # type: ignore[attr-defined]

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == '_cmd_skill_resolution':
            return fake_mod
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', _fake_import)
    assert load_registry() == []


def test_load_registry_returns_discovered_list(monkeypatch):
    """A well-formed discovery return is passed through verbatim."""
    import types

    recipes = [{'key': 'doc-verify', 'name': 'Verify Documentation'}]
    fake_mod = types.ModuleType('_cmd_skill_resolution')
    fake_mod._discover_all_recipes = lambda: recipes  # type: ignore[attr-defined]

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == '_cmd_skill_resolution':
            return fake_mod
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', _fake_import)
    assert load_registry() == recipes
