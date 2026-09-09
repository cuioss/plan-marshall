#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
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
* ``score_recipe`` pre-diagnosed-change SHAPE arm (surgical-fix recipe only) —
  a stated root cause co-occurring with an exact-change / file anchor lifts the
  ``recipe-surgical-fix`` recipe above the keyword-only ceiling, a
  discovery-demand narrative is vetoed, and the shape arm never perturbs any
  other recipe. Fixtures are the REAL archived request strings of four
  pre-diagnosed surgical plans and one broad structural-review plan;
* ``load_registry`` — returns ``[]`` when the discovery helper is absent and
  tolerates discovery exceptions / non-list returns without raising.
"""

from __future__ import annotations

import builtins

import pytest

from recipe_scoring import (
    MIN_CONFIDENCE,
    _is_surgical_fix_recipe,
    _score_prediagnosed_shape,
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


#: Sentinel for the row where the discovery helper cannot be imported at all —
#: distinct from a helper that imports and then misbehaves.
_HELPER_MISSING = object()

#: The one well-formed discovery return, so the pass-through row can assert
#: identity rather than a re-stated literal.
_DISCOVERED_RECIPES = [{'key': 'doc-verify', 'name': 'Verify Documentation'}]


def _raising_discover():
    raise OSError('simulated registry read failure')


#: ``(what ``_discover_all_recipes`` does, the registry loaded)``. Every failure
#: shape degrades to the empty list; the last row is the matched control that a
#: well-formed return is passed through rather than swallowed with the rest.
_LOAD_REGISTRY_CASES = [
    (_HELPER_MISSING, []),
    (_raising_discover, []),
    (lambda: {'not': 'a list'}, []),
    (lambda: _DISCOVERED_RECIPES, _DISCOVERED_RECIPES),
]

_LOAD_REGISTRY_IDS = [
    'the-helper-cannot-be-imported',
    'discovery-raises',
    'discovery-returns-a-non-list',
    'discovery-returns-a-well-formed-list',
]


@pytest.mark.parametrize('discover,expected', _LOAD_REGISTRY_CASES, ids=_LOAD_REGISTRY_IDS)
def test_load_registry(monkeypatch, discover, expected):
    import types

    real_import = builtins.__import__
    fake_mod = None
    if discover is not _HELPER_MISSING:
        fake_mod = types.ModuleType('_cmd_skill_resolution')
        fake_mod._discover_all_recipes = discover

    def _fake_import(name, *args, **kwargs):
        if name == '_cmd_skill_resolution':
            if fake_mod is None:
                raise ImportError('simulated absence of _cmd_skill_resolution')
            return fake_mod
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', _fake_import)

    assert load_registry() == expected


# =============================================================================
# Pre-diagnosed-change SHAPE arm (surgical-fix recipe only)
# =============================================================================
#
# The fixtures below are the ACTUAL archived "Original Input" request strings of
# the pre-diagnosed surgical plans (must MATCH) and the broad
# structural-review/consolidation plan (must NOT match). The scorer is only
# trustworthy against the real corpus it will see in production, so these are
# verbatim excerpts of the real requests, NOT synthetic prose.

# Surgical: root cause and exact change known, single file.
_REQ_CHECK_ERA_STAMPS = (
    'Fix the owed CHECK_ERA era stamps in the audit skill (root cause known, '
    'exact change known, single file): in '
    '`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` update '
    "the CHECK_ERA registry — `lane-lever-effectiveness` and "
    "`track-selection-accuracy` from `'#854'` to `'#862'` (plan-5's "
    "routing-order/light-lane fix boundary), `merge-window-accounting` from "
    "`'#849'` to `'#863'` (plan-12's external-merge-traffic boundary) — and "
    'update the adjacent registry comments to match. The '
    '`set(CHECK_ERA) == set(CHECK_NAMES)` invariant test must stay green. '
    'Bounded footprint, no behavior change beyond era attribution.'
)

# Surgical: root cause known, exact change stated.
_REQ_GET_DELIVERABLE = (
    'Fix the missing get-deliverable subcommand in manage-solution-outline '
    '(plan-marshall bundle): root cause known — the argparse choices lack the '
    'verb and four plans independently invented it (lesson 2026-07-06-17-001). '
    'Exact change: add get-deliverable --plan-id --number returning the single '
    'deliverable block, plus a unit test and the SKILL.md verb row. Single '
    'module, bounded footprint.'
)

# Surgical: root cause known, two recurrences cited.
_REQ_MANIFEST_ORDER = (
    'Fix the manifest composer emitting finalize steps after archive-plan in '
    'defiance of their frontmatter order (root cause known, 2 recurrences: #860 '
    'and #866 both composed finalize-step-preference-emitter, frontmatter order: '
    '80, AFTER archive-plan — running it as-listed fails because archive moves '
    'the plan dir; both runs reordered manually and logged a [WARNING]). Fix in '
    'manage-execution-manifest compose: steps must be emitted in frontmatter '
    'order with archive-plan as the terminal barrier. Single module, bounded '
    'footprint.'
)

# Surgical: root cause known, fix has two halves.
_REQ_SAFE_MERGE = (
    'Fix pr safe-merge closing PRs without merging when the platform merge queue '
    'is required but use_merge_queue=false (observed on PR #866: safe-merge '
    'reported success, PR was closed unmerged, ~30-min manual recovery). Root '
    'cause known, two halves: 1. safe-merge does not preflight the branch\'s '
    'queue-required state — it must consult the existing `ci repo merge-queue '
    'probe` verb (shipped #863) before an immediate merge. 2. safe-merge\'s '
    'success detection must treat state=closed-without-merge as FAILURE, never '
    'success. Surface: workflow-integration-github/_github_pr.py safe-merge. '
    'Single bundle, bounded footprint.'
)

# A BROAD consolidation / full-structural-review request. Diagnosis is
# complete AND file paths are
# named, but the request demands a discovery-driven structural review, so it is
# NOT a pre-diagnosed surgical change and MUST be vetoed.
_REQ_TERMINAL_TITLE = (
    'Fix two independent defects in terminal-title handling and '
    'refactor/consolidate the title-handling surface into a coherent structure. '
    'This is a meta-project (plan-marshall bundle) change. Diagnosis is complete '
    'and evidence-backed — this plan implements the fixes plus the '
    'consolidation. The plan MUST include a full structural review of the '
    'current title-handling surface and refactor it toward coherence.'
)

#: The real archived requests, keyed by the id each carries in the test report.
#: Both tables below derive their ids from THIS mapping rather than zipping a
#: parallel list on by position: the requests are multi-paragraph strings pytest
#: cannot name on its own, and an id list drawn from anywhere else would silently
#: relabel every row the moment this order moves.
_SURGICAL_MATCH_REQUESTS_BY_ID = {
    'check-era-stamps': _REQ_CHECK_ERA_STAMPS,
    'get-deliverable': _REQ_GET_DELIVERABLE,
    'manifest-order': _REQ_MANIFEST_ORDER,
    'safe-merge': _REQ_SAFE_MERGE,
}

_SURGICAL_MATCH_REQUESTS = tuple(_SURGICAL_MATCH_REQUESTS_BY_ID.values())

_SURGICAL_RECIPE = {
    'key': 'surgical-fix',
    'name': 'recipe-surgical-fix',
    'skill': 'plan-marshall:recipe-surgical-fix',
    'description': 'Micro-lane recipe for a pre-diagnosed surgical fix bounded to a single module',
    'domain': 'plan-marshall-plugin-dev',
    'scope': 'module',
}


# --- _score_prediagnosed_shape (pure) ----------------------------------------


#: ``(narrative, shape band)`` — every band the shape arm can award. The four
#: strong rows are the REAL archived requests; the veto row is the broad
#: structural-review request; the zero rows are the shapes that must not score
#: at all (no narrative, and a stated root cause carrying no path / notation /
#: CLI / fenced anchor); and the two middle rows separate a generic root cause
#: from an explicit exact-change marker.
_SHAPE_BAND_CASES = [
    *((request, 0.75) for request in _SURGICAL_MATCH_REQUESTS),
    (_REQ_TERMINAL_TITLE, 0.0),
    ('', 0.0),
    (None, 0.0),
    (
        'The root cause is a stale cache; the exact change is known but no anchor is named here.',
        0.0,
    ),
    ('The root cause lives in marketplace/pkg/module.py and needs a small tweak.', 0.45),
    ('Exact change: patch marketplace/pkg/module.py to add the missing guard.', 0.6),
]

_SHAPE_BAND_IDS = [
    *(f'real-request-{key}' for key in _SURGICAL_MATCH_REQUESTS_BY_ID),
    'a-broad-structural-review-request-is-vetoed',
    'an-empty-narrative',
    'no-narrative-at-all',
    'a-root-cause-with-no-concrete-anchor',
    'a-generic-root-cause-plus-an-anchor',
    'an-exact-change-marker-without-the-root-cause-phrase',
]


@pytest.mark.parametrize('narrative,expected', _SHAPE_BAND_CASES, ids=_SHAPE_BAND_IDS)
def test_score_prediagnosed_shape(narrative, expected):
    assert _score_prediagnosed_shape(narrative) == expected


# --- _is_surgical_fix_recipe -------------------------------------------------


#: ``(recipe, is it the surgical-fix recipe?)``. The identity resolves from any
#: of the three spellings a registry entry can carry; the two negatives keep the
#: match from widening to every recipe.
_SURGICAL_IDENTITY_CASES = [
    ({'name': 'recipe-surgical-fix'}, True),
    ({'skill': 'plan-marshall:recipe-surgical-fix'}, True),
    ({'key': 'surgical-fix'}, True),
    (_DOC_RECIPE, False),
    ({'name': 'recipe-simplify-codebase'}, False),
]

_SURGICAL_IDENTITY_IDS = [
    'by-name',
    'by-skill-notation',
    'by-key',
    'a-documentation-recipe',
    'another-recipe-whose-name-starts-with-recipe',
]


@pytest.mark.parametrize(
    'recipe,expected', _SURGICAL_IDENTITY_CASES, ids=_SURGICAL_IDENTITY_IDS
)
def test_is_surgical_fix_recipe(recipe: dict, expected: bool):
    assert bool(_is_surgical_fix_recipe(recipe)) is expected


# --- score_recipe SHAPE blend (surgical-fix only) ----------------------------


@pytest.mark.parametrize(
    'request_text', _SURGICAL_MATCH_REQUESTS, ids=list(_SURGICAL_MATCH_REQUESTS_BY_ID)
)
def test_score_recipe_shape_lifts_surgical_fix_above_auto_route(request_text):
    """The shape arm lifts surgical-fix confidence to the strong band for real requests.

    These requests describe the bug, not the recipe's vocabulary, so their
    keyword overlap alone would floor below MIN_CONFIDENCE; the shape arm is what
    clears both the floor and the 0.6 auto-route threshold.
    """
    confidence, breakdown = score_recipe(
        _SURGICAL_RECIPE, tokenize(request_text), None, None, narrative_text=request_text
    )
    assert breakdown['shape_score'] == 0.75
    assert confidence == 0.75
    assert confidence >= 0.6
    assert confidence >= MIN_CONFIDENCE


def test_score_recipe_shape_does_not_rescue_broad_request():
    """The broad structural-review request stays below the floor for surgical-fix."""
    confidence, breakdown = score_recipe(
        _SURGICAL_RECIPE, tokenize(_REQ_TERMINAL_TITLE), None, None, narrative_text=_REQ_TERMINAL_TITLE
    )
    assert breakdown['shape_score'] == 0.0
    assert confidence < MIN_CONFIDENCE


def test_score_recipe_shape_only_for_surgical_fix_recipe():
    """A non-surgical recipe is unaffected by narrative_text — no shape key, same score."""
    narrative = _REQ_CHECK_ERA_STAMPS
    tokens = tokenize(narrative)
    without_text, breakdown_without = score_recipe(_DOC_RECIPE, tokens, None, None)
    with_text, breakdown_with = score_recipe(_DOC_RECIPE, tokens, None, None, narrative_text=narrative)
    # Byte-identical confidence and no shape_score key for a non-surgical recipe.
    assert with_text == without_text
    assert 'shape_score' not in breakdown_with
    assert set(breakdown_with) == set(breakdown_without) == {
        'keyword_score', 'domain_score', 'scope_score', 'matched_keywords'
    }


def test_score_recipe_omitting_narrative_text_is_backward_compatible():
    """Without narrative_text the surgical-fix recipe scores the pure keyword blend."""
    narrative = _REQ_CHECK_ERA_STAMPS
    tokens = tokenize(narrative)
    confidence, breakdown = score_recipe(_SURGICAL_RECIPE, tokens, None, None)
    # No shape arm engaged: breakdown carries no shape_score, confidence is the
    # keyword-only blend (below the floor for this bug-narrative request).
    assert 'shape_score' not in breakdown
    assert confidence == round(0.6 * breakdown['keyword_score'], 3)


def test_score_recipe_shape_never_lowers_a_strong_keyword_match():
    """When keyword blend already exceeds the shape score, the blend max wins."""
    # A request that echoes the surgical recipe's own description tokens has a
    # high keyword score; a weak/absent shape must not pull the confidence down.
    narrative = 'micro-lane pre-diagnosed surgical fix bounded single module'
    tokens = tokenize(narrative)
    kw_only, _ = score_recipe(_SURGICAL_RECIPE, tokens, None, None)
    blended, breakdown = score_recipe(_SURGICAL_RECIPE, tokens, None, None, narrative_text=narrative)
    assert blended >= kw_only
    assert blended == max(kw_only, breakdown['shape_score'])


# =============================================================================
# _resolve_recipe_skill_md — versioned-cache-layout resolution
# =============================================================================


def test_resolve_recipe_skill_md_finds_bundle_recipe_in_versioned_cache(tmp_path, monkeypatch):
    """A bundle recipe's SKILL.md resolves from the versioned plugin-cache layout
    ({bundle}/{version}/skills/...), not only the flat source layout. The former
    raw ``*/skills/{name}/SKILL.md`` glob matched only the flat layout, so a bundle
    recipe silently lost its lane seed when this ran from the deployed cache.
    """
    import marketplace_bundles

    from recipe_scoring import _resolve_recipe_skill_md

    skill_md = (
        tmp_path / 'plan-marshall' / '0.1-BETA' / 'skills' / 'recipe-zzz-cache-probe' / 'SKILL.md'
    )
    skill_md.parent.mkdir(parents=True)
    skill_md.write_text('---\nname: recipe-zzz-cache-probe\n---\n# body\n', encoding='utf-8')
    # resolve_bundles_root is imported inside _resolve_recipe_skill_md, so patch the
    # source-module attribute the function-local import re-reads.
    monkeypatch.setattr(marketplace_bundles, 'resolve_bundles_root', lambda _f: tmp_path)

    resolved = _resolve_recipe_skill_md({'key': 'zzz-cache-probe'})
    assert resolved == skill_md
