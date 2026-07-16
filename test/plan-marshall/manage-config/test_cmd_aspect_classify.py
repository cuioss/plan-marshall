#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the aspect-classify command in manage-config.

The aspect-classify verb is a deterministic request-aspect classifier. It
tokenizes free-form ``--request-text`` via the shared ``recipe_scoring.tokenize``
and scores the overlap of the request tokens against three fixed keyword tables
(analysis / planning / implementation). The higher of analysis/planning is the
candidate aspect; it is accepted only when its confidence clears the
``>= --threshold`` bar (default ``0.7``) AND beats the implementation overlap.
Below the threshold the verb returns ``aspect: implementation`` — the safe
fallback that keeps the build / quality-gate / test gates in the composed
manifest.

Scoring note (load-bearing for the assertions below): unlike ``recipe-match``'s
``0.6 * keyword + 0.25 * domain + 0.15 * scope`` blend (capped at 0.6 from
request text alone), the aspect classifier uses a pure ``_overlap_score`` — the
fraction of request tokens that appear in a keyword table, range ``0.0`` to
``1.0`` with NO ``0.6`` ceiling. A request whose tokens are entirely analysis
keywords therefore scores ``1.0`` for analysis, so the default ``0.7`` threshold
is reachable and intentional. The tests exercise the threshold boundary against
that full ``[0, 1.0]`` band.

The verb performs NO LLM call and NO plan-scoped read — only the free-form
request text drives scoring. Tier 2 (direct import) tests with a Tier 3
subprocess test for CLI plumbing / the constructed-argv assertion at the
argparse boundary.

Negation override (exception to the sub-threshold fallback): an explicit
negative build constraint in the RAW request text — a fixed phrase table
(``no build``, ``docs only``, …) matched case-insensitively BEFORE
tokenization — overrides the implementation fallback. ``recipe_scoring.tokenize``
drops ``no`` (length filter) and ``build`` is itself an implementation keyword,
so the override must key on the phrase, not the tokens. On a match the verb
returns the higher-scored non-implementation candidate with
``drops_build_steps: true`` and reports the phrase via
``negative_constraint_matched``; without a match, behavior is byte-identical
to the threshold contract above (the field is absent).
"""

from argparse import Namespace

import pytest

from test_helpers import SCRIPT_PATH

from conftest import load_script_module, run_script

_cmd_aspect_classify_mod = load_script_module('plan-marshall', 'manage-config', '_cmd_aspect_classify.py')
cmd_aspect_classify = _cmd_aspect_classify_mod.cmd_aspect_classify


def _ns(request_text: str, threshold: float = 0.7) -> Namespace:
    return Namespace(request_text=request_text, threshold=threshold)


# =============================================================================
# Aspect classification — Tier 2
# =============================================================================


def test_pure_analysis_request_classifies_analysis():
    """A request made entirely of analysis keywords classifies as analysis.

    Four distinct analysis-table tokens, zero non-keyword tokens → analysis
    overlap is 1.0, which clears the default 0.7 threshold and beats the zero
    implementation overlap.
    """
    result = cmd_aspect_classify(_ns('analyze audit investigate evaluate'))

    assert result['status'] == 'success'
    assert result['aspect'] == 'analysis'
    assert result['confidence'] == 1.0
    assert result['drops_build_steps'] is True


def test_pure_planning_request_classifies_planning():
    """A request made entirely of planning keywords classifies as planning.

    ``plan`` itself is a stop-word in ``recipe_scoring.tokenize``, so the request
    uses distinct surviving planning tokens (design / roadmap / architecture /
    blueprint).
    """
    result = cmd_aspect_classify(_ns('design roadmap architecture blueprint'))

    assert result['status'] == 'success'
    assert result['aspect'] == 'planning'
    assert result['confidence'] == 1.0
    assert result['drops_build_steps'] is True


def test_pure_implementation_request_classifies_implementation():
    """A request made entirely of implementation keywords classifies as implementation."""
    result = cmd_aspect_classify(_ns('implement build create refactor'))

    assert result['status'] == 'success'
    assert result['aspect'] == 'implementation'
    assert result['confidence'] == 1.0
    assert result['drops_build_steps'] is False


def test_planning_outranks_analysis_when_both_present():
    """The higher of analysis/planning wins the candidate slot.

    Three planning tokens vs one analysis token → planning_score (0.75) >
    analysis_score (0.25), so planning is the candidate, clears 0.7, and beats
    the zero implementation overlap.
    """
    result = cmd_aspect_classify(_ns('design roadmap architecture analyze'))

    assert result['aspect'] == 'planning'
    assert result['drops_build_steps'] is True
    assert result['scores']['planning'] > result['scores']['analysis']


# =============================================================================
# Below-threshold implementation fallback — Tier 2
# =============================================================================


def test_below_threshold_request_falls_back_to_implementation():
    """A request whose analysis overlap is below 0.7 falls back to implementation.

    Two analysis tokens out of five total → analysis overlap 0.4 < 0.7, so the
    safe implementation fallback applies even though no implementation keyword is
    present.
    """
    # 2 analysis keywords (analyze, audit) + 3 non-keyword distinct tokens.
    result = cmd_aspect_classify(_ns('analyze audit xylophone marmalade obsidian'))

    assert result['aspect'] == 'implementation'
    assert result['drops_build_steps'] is False
    assert result['scores']['analysis'] < 0.7


def test_no_keyword_request_falls_back_to_implementation():
    """A request matching no keyword table classifies as implementation (confidence 0)."""
    result = cmd_aspect_classify(_ns('xylophone marmalade obsidian'))

    assert result['aspect'] == 'implementation'
    assert result['confidence'] == 0.0
    assert result['drops_build_steps'] is False


def test_empty_request_falls_back_to_implementation():
    """An empty request classifies as implementation — the safe gate-keeping default."""
    result = cmd_aspect_classify(_ns(''))

    assert result['aspect'] == 'implementation'
    assert result['confidence'] == 0.0
    assert result['drops_build_steps'] is False


def test_candidate_must_beat_implementation_overlap():
    """An analysis candidate at threshold still loses when implementation overlaps more.

    Two analysis tokens + three implementation tokens out of five → analysis 0.4,
    implementation 0.6; analysis is below 0.7 anyway, so the implementation
    fallback applies.
    """
    result = cmd_aspect_classify(_ns('analyze audit implement build create'))

    assert result['aspect'] == 'implementation'
    assert result['scores']['implementation'] > result['scores']['analysis']
    assert result['drops_build_steps'] is False


# =============================================================================
# Threshold boundary (exactly 0.7) — Tier 2
# =============================================================================


def test_threshold_boundary_exactly_at_default_accepts():
    """An analysis overlap of exactly 0.7 clears the default threshold (>=).

    Seven analysis tokens + three non-keyword tokens (ten distinct total) →
    analysis overlap exactly 0.7, which meets the default 0.7 via ``>=``. The
    three non-keyword tokens carry no implementation overlap, so analysis wins.
    """
    request = 'analyze audit investigate evaluate assess inspect survey xylophone marmalade obsidian'
    result = cmd_aspect_classify(_ns(request))

    assert result['scores']['analysis'] == 0.7
    assert result['aspect'] == 'analysis'
    assert result['drops_build_steps'] is True


def test_just_below_threshold_falls_back():
    """An analysis overlap just below 0.7 falls back to implementation.

    Six analysis tokens out of ten distinct total → analysis overlap 0.6 < 0.7.
    """
    request = 'analyze audit investigate evaluate assess inspect xylophone marmalade obsidian quokka'
    result = cmd_aspect_classify(_ns(request))

    assert result['scores']['analysis'] == 0.6
    assert result['aspect'] == 'implementation'
    assert result['drops_build_steps'] is False


def test_custom_threshold_below_score_accepts_aspect():
    """A low custom --threshold lets a modest analysis overlap earn the analysis aspect.

    Two analysis tokens out of four total → analysis 0.5; a 0.5 threshold meets
    via ``>=`` and beats the zero implementation overlap.
    """
    result = cmd_aspect_classify(_ns('analyze audit xylophone marmalade', threshold=0.5))

    assert result['threshold'] == 0.5
    assert result['scores']['analysis'] == 0.5
    assert result['aspect'] == 'analysis'
    assert result['drops_build_steps'] is True


def test_custom_threshold_above_score_falls_back():
    """A high custom --threshold pushes an otherwise-winning aspect to the fallback."""
    result = cmd_aspect_classify(_ns('analyze audit investigate evaluate', threshold=1.5))

    assert result['threshold'] == 1.5
    assert result['scores']['analysis'] == 1.0
    assert result['aspect'] == 'implementation'
    assert result['drops_build_steps'] is False


# =============================================================================
# TOON output shape — Tier 2
# =============================================================================


def test_result_carries_full_breakdown_and_scores():
    """The result surfaces request_tokens, per-aspect scores, and matched-keyword breakdown."""
    result = cmd_aspect_classify(_ns('analyze audit investigate evaluate'))

    assert sorted(result['request_tokens']) == ['analyze', 'audit', 'evaluate', 'investigate']
    assert set(result['scores']) == {'analysis', 'planning', 'implementation'}
    breakdown = result['breakdown']
    assert set(breakdown) == {'analysis', 'planning', 'implementation'}
    assert breakdown['analysis']['matched_keywords'] == ['analyze', 'audit', 'evaluate', 'investigate']
    assert breakdown['analysis']['score'] == 1.0
    assert breakdown['implementation']['matched_keywords'] == []


# =============================================================================
# Negation override — explicit negative build constraint (Tier 2)
# =============================================================================


def test_negation_override_576_shape_docs_review_with_no_build():
    """The TokenSheriff #576 shape: sub-threshold docs review WITH 'no build'.

    A docs-review request whose analysis overlap is far below 0.7 would fall
    back to ``implementation`` — but the explicit 'no build' constraint
    overrides the fallback: non-implementation aspect, ``drops_build_steps:
    true``, and the matched phrase surfaced for observability.
    """
    request = 'Review the getting-started docs wording for accuracy, no build needed'
    result = cmd_aspect_classify(_ns(request))

    assert result['scores']['analysis'] < 0.7
    assert result['aspect'] in ('analysis', 'planning')
    assert result['drops_build_steps'] is True
    assert result['negative_constraint_matched'] == 'no build'


@pytest.mark.parametrize(
    'phrase',
    [
        'no build',
        'no builds',
        'without build',
        'do not build',
        'no verify',
        'docs only',
        'docs-only',
        'documentation only',
        'documentation-only',
    ],
)
def test_each_representative_negation_phrase_triggers_override(phrase):
    """Every representative negation phrase fires the override and is reported.

    The request embeds the phrase in otherwise non-keyword text, so all aspect
    scores stay far below the threshold — only the negation override can flip
    ``drops_build_steps`` to true.
    """
    result = cmd_aspect_classify(_ns(f'xylophone marmalade {phrase} obsidian'))

    assert result['aspect'] in ('analysis', 'planning')
    assert result['drops_build_steps'] is True
    assert result['negative_constraint_matched'] == phrase


def test_negation_phrase_matches_case_insensitively():
    """The phrase table matches against the lower-cased raw request text."""
    result = cmd_aspect_classify(_ns('Docs ONLY change to the README'))

    assert result['drops_build_steps'] is True
    assert result['negative_constraint_matched'] == 'docs only'


def test_negation_free_sub_threshold_request_unchanged():
    """A negation-free sub-threshold request still falls back to implementation.

    Byte-identical to the pre-override contract: implementation fallback,
    ``drops_build_steps: false``, and NO ``negative_constraint_matched`` field
    in the result.
    """
    result = cmd_aspect_classify(_ns('analyze audit xylophone marmalade obsidian'))

    assert result['aspect'] == 'implementation'
    assert result['drops_build_steps'] is False
    assert 'negative_constraint_matched' not in result


def test_negation_override_survives_tokenization_hostile_text():
    """The phrase match keys on the raw text, not the token set.

    ``recipe_scoring.tokenize`` drops 'no' (length filter) and keeps 'build'
    (an implementation keyword), so the token set of this request looks
    implementation-shaped — yet the raw-text phrase match still sees the
    negation.
    """
    result = cmd_aspect_classify(_ns('You need no build because the docs already explain it'))

    assert result['aspect'] in ('analysis', 'planning')
    assert result['drops_build_steps'] is True
    assert result['negative_constraint_matched'] == 'no build'


# =============================================================================
# CLI plumbing — constructed-argv assertion at the argparse boundary (Tier 3)
# =============================================================================


def test_cli_aspect_classify_argv_boundary(plan_context, tmp_path):
    """Constructed-argv: aspect-classify runs end-to-end through argparse and emits TOON."""
    result = run_script(
        SCRIPT_PATH,
        'aspect-classify',
        '--request-text',
        'analyze audit investigate evaluate',
        cwd=tmp_path,
    )

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    assert data['status'] == 'success'
    assert data['aspect'] == 'analysis'
    assert data['drops_build_steps'] is True


def test_cli_aspect_classify_custom_threshold_argv(plan_context, tmp_path):
    """Constructed-argv: --threshold parses as a float and flows into the result."""
    result = run_script(
        SCRIPT_PATH,
        'aspect-classify',
        '--request-text',
        'analyze audit investigate evaluate',
        '--threshold',
        '1.5',
        cwd=tmp_path,
    )

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    assert data['threshold'] == 1.5
    # Above the perfect 1.0 analysis overlap → implementation fallback.
    assert data['aspect'] == 'implementation'


def test_cli_aspect_classify_missing_request_text_rejected(plan_context, tmp_path):
    """Constructed-argv: omitting the required --request-text is an argparse rejection."""
    result = run_script(SCRIPT_PATH, 'aspect-classify', cwd=tmp_path)

    # argparse rejects the missing required flag with exit code 2.
    assert result.returncode == 2
