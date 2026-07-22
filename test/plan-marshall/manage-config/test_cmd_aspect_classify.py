#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the aspect-classify command in manage-config.

The aspect-classify verb is a deterministic request-aspect classifier. It
tokenizes free-form ``--request-text`` via the shared ``recipe_scoring.tokenize``
and scores the overlap of the request tokens against three fixed keyword tables
(analysis / planning / implementation). The higher of analysis/planning is the
candidate aspect; it is accepted only when its confidence clears the
``>= --threshold`` bar (default ``0.7``) AND beats the implementation overlap.
Below the threshold the verb returns ``aspect: implementation`` — the
conservative default.

Scope: the verb classifies request INTENT and nothing else. It has NO say in
whether a change needs a build — that is the exclusive province of the
``build-decision`` verdict over the ``build.map`` globs and the live footprint
(ADR-004 § "Amendment: ``build-decision`` is the sole build/no-build
authority"). The classifier reads only the request narrative, which is
structurally blind to the footprint, so it can neither decide nor influence
build necessity. The regression section below pins that the retired
build-facing output (``drops_build_steps``, ``negative_constraint_matched``, and
the raw-text negation-phrase override that produced them) is gone and stays
gone.

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
"""

from argparse import Namespace

import pytest
from test_helpers import SCRIPT_PATH

from conftest import load_script_module, run_script

_cmd_aspect_classify_mod = load_script_module('plan-marshall', 'manage-config', '_cmd_aspect_classify.py')
cmd_aspect_classify = _cmd_aspect_classify_mod.cmd_aspect_classify


def _ns(request_text: str, threshold: float = 0.7) -> Namespace:
    return Namespace(request_text=request_text, threshold=threshold)


# The complete set of keys the verb's result may carry. Pinned as a set so a
# future re-introduction of a build-facing field fails here rather than quietly
# handing the classifier a second say in build necessity.
_RESULT_KEYS = {
    'status',
    'request_tokens',
    'threshold',
    'aspect',
    'confidence',
    'scores',
    'breakdown',
}


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


def test_pure_implementation_request_classifies_implementation():
    """A request made entirely of implementation keywords classifies as implementation."""
    result = cmd_aspect_classify(_ns('implement build create refactor'))

    assert result['status'] == 'success'
    assert result['aspect'] == 'implementation'
    assert result['confidence'] == 1.0


def test_planning_outranks_analysis_when_both_present():
    """The higher of analysis/planning wins the candidate slot.

    Three planning tokens vs one analysis token → planning_score (0.75) >
    analysis_score (0.25), so planning is the candidate, clears 0.7, and beats
    the zero implementation overlap.
    """
    result = cmd_aspect_classify(_ns('design roadmap architecture analyze'))

    assert result['aspect'] == 'planning'
    assert result['scores']['planning'] > result['scores']['analysis']


# =============================================================================
# Below-threshold implementation fallback — Tier 2
# =============================================================================


def test_below_threshold_request_falls_back_to_implementation():
    """A request whose analysis overlap is below 0.7 falls back to implementation.

    Two analysis tokens out of five total → analysis overlap 0.4 < 0.7, so the
    conservative implementation fallback applies even though no implementation
    keyword is present.
    """
    # 2 analysis keywords (analyze, audit) + 3 non-keyword distinct tokens.
    result = cmd_aspect_classify(_ns('analyze audit xylophone marmalade obsidian'))

    assert result['aspect'] == 'implementation'
    assert result['scores']['analysis'] < 0.7


def test_no_keyword_request_falls_back_to_implementation():
    """A request matching no keyword table classifies as implementation (confidence 0)."""
    result = cmd_aspect_classify(_ns('xylophone marmalade obsidian'))

    assert result['aspect'] == 'implementation'
    assert result['confidence'] == 0.0


def test_empty_request_falls_back_to_implementation():
    """An empty request classifies as implementation — the conservative default."""
    result = cmd_aspect_classify(_ns(''))

    assert result['aspect'] == 'implementation'
    assert result['confidence'] == 0.0


def test_candidate_must_beat_implementation_overlap():
    """An analysis candidate at threshold still loses when implementation overlaps more.

    Two analysis tokens + three implementation tokens out of five → analysis 0.4,
    implementation 0.6; analysis is below 0.7 anyway, so the implementation
    fallback applies.
    """
    result = cmd_aspect_classify(_ns('analyze audit implement build create'))

    assert result['aspect'] == 'implementation'
    assert result['scores']['implementation'] > result['scores']['analysis']


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


def test_just_below_threshold_falls_back():
    """An analysis overlap just below 0.7 falls back to implementation.

    Six analysis tokens out of ten distinct total → analysis overlap 0.6 < 0.7.
    """
    request = 'analyze audit investigate evaluate assess inspect xylophone marmalade obsidian quokka'
    result = cmd_aspect_classify(_ns(request))

    assert result['scores']['analysis'] == 0.6
    assert result['aspect'] == 'implementation'


def test_custom_threshold_below_score_accepts_aspect():
    """A low custom --threshold lets a modest analysis overlap earn the analysis aspect.

    Two analysis tokens out of four total → analysis 0.5; a 0.5 threshold meets
    via ``>=`` and beats the zero implementation overlap.
    """
    result = cmd_aspect_classify(_ns('analyze audit xylophone marmalade', threshold=0.5))

    assert result['threshold'] == 0.5
    assert result['scores']['analysis'] == 0.5
    assert result['aspect'] == 'analysis'


def test_custom_threshold_above_score_falls_back():
    """A high custom --threshold pushes an otherwise-winning aspect to the fallback."""
    result = cmd_aspect_classify(_ns('analyze audit investigate evaluate', threshold=1.5))

    assert result['threshold'] == 1.5
    assert result['scores']['analysis'] == 1.0
    assert result['aspect'] == 'implementation'


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


def test_result_carries_no_build_facing_field():
    """The result surface is exactly the intent fields — nothing build-facing.

    ``drops_build_steps`` and ``negative_constraint_matched`` were this verb's
    build-facing output: a downstream composer read them and dropped build steps
    on the strength of a NARRATIVE read, which is a second build/no-build oracle
    running beside the footprint authority. Pinning the key set as a whole (not
    just the two retired names) means any newly-invented build-facing field also
    fails here.
    """
    result = cmd_aspect_classify(_ns('analyze audit investigate evaluate'))

    assert set(result) == _RESULT_KEYS


# =============================================================================
# Regression — the narrative negation override is retired
#
# The verb used to scan the RAW request text for a fixed negation-phrase table
# ('no build', 'docs only', …) and, on a match, flip the aspect away from
# implementation and emit ``drops_build_steps: true``. That override let a
# sentence in a request veto the build — a build/no-build claim derived from
# prose rather than from the footprint. It is deleted; these cases pin that a
# request SAYING it needs no build changes nothing about the classification.
# =============================================================================


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
def test_negation_phrase_does_not_override_the_classification(phrase):
    """No negation phrase promotes a sub-threshold request off the fallback.

    The request embeds the phrase in otherwise non-keyword text, so every aspect
    score stays far below the threshold. Under the retired override this returned
    a non-implementation aspect; it must now take the ordinary fallback.
    """
    result = cmd_aspect_classify(_ns(f'xylophone marmalade {phrase} obsidian'))

    assert result['aspect'] == 'implementation'
    assert 'negative_constraint_matched' not in result
    assert 'drops_build_steps' not in result


def test_negation_phrase_does_not_change_a_docs_review_request():
    """The TokenSheriff #576 shape: sub-threshold docs review WITH 'no build'.

    This request is what the override existed to catch. Its build implications
    are now settled by the footprint at run time, not by the sentence, so the
    classifier reports the same conservative fallback it reports for any other
    sub-threshold request.
    """
    request = 'Review the getting-started docs wording for accuracy, no build needed'
    result = cmd_aspect_classify(_ns(request))

    assert result['scores']['analysis'] < 0.7
    assert result['aspect'] == 'implementation'
    assert set(result) == _RESULT_KEYS


def test_negation_phrase_does_not_survive_tokenization_hostile_text():
    """Raw-text phrase matching is gone — only the token set drives the verdict.

    ``recipe_scoring.tokenize`` drops 'no' (length filter) and keeps 'build' (an
    implementation keyword). The retired override read the raw text and so could
    see a negation the tokens cannot express; the verb now sees only the tokens,
    which here are implementation-shaped.
    """
    result = cmd_aspect_classify(_ns('You need no build because the docs already explain it'))

    assert result['aspect'] == 'implementation'
    assert set(result) == _RESULT_KEYS


def test_request_text_mentioning_a_build_is_scored_by_tokens_alone():
    """Whether a request says 'build' or 'no build', only token overlap counts.

    The two texts differ solely by the negation word that the retired override
    keyed on, and ``tokenize`` drops it — so the classifier must return identical
    results. A divergence would mean raw-text phrase inspection had returned.
    """
    affirmative = cmd_aspect_classify(_ns('You need a build for the docs'))
    negated = cmd_aspect_classify(_ns('You need no build for the docs'))

    assert affirmative == negated


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
    assert 'drops_build_steps' not in data


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


# =============================================================================
# Purity regression — NO plan-scoped read surface
#
# aspect-classify is a narrative-only signal and deliberately performs no
# plan-scoped footprint read. Two independent reasons now: the compose-time
# footprint is always empty (a read here would resolve [] and mislead), and
# build necessity is not this verb's question at all. These tests guard against
# a future re-introduction of a plan-scoped read: the CLI argument surface must
# expose no --plan-id / footprint parameter, and classification is a pure
# function of --request-text alone.
# =============================================================================


def test_cli_aspect_classify_rejects_plan_id_flag(plan_context, tmp_path):
    """Constructed-argv: --plan-id is NOT an accepted flag — the argparse surface is footprint-free.

    A future re-introduction of a plan-scoped read would add a --plan-id (or
    footprint) flag to the verb. This test pins the purity contract at the CLI
    boundary: passing --plan-id is an argparse rejection (exit 2), proving no
    such surface exists.
    """
    result = run_script(
        SCRIPT_PATH,
        'aspect-classify',
        '--request-text',
        'analyze audit investigate evaluate',
        '--plan-id',
        'some-plan',
        cwd=tmp_path,
    )

    # argparse rejects the unknown --plan-id flag with exit code 2.
    assert result.returncode == 2


def test_cli_aspect_classify_rejects_affected_files_flag(plan_context, tmp_path):
    """Constructed-argv: no --affected-files footprint surface exists either."""
    result = run_script(
        SCRIPT_PATH,
        'aspect-classify',
        '--request-text',
        'analyze audit investigate evaluate',
        '--affected-files',
        'scripts/foo.py',
        cwd=tmp_path,
    )

    assert result.returncode == 2


def test_classification_is_pure_function_of_request_text():
    """Representative analysis / planning / implementation requests classify from text alone.

    No plan context, no footprint, no environment is consulted — the same
    request text always yields the same narrative-only verdict. This is the
    behavioural half of the purity contract (the CLI-surface half is asserted
    above).
    """
    analysis = cmd_aspect_classify(_ns('analyze audit investigate evaluate'))
    planning = cmd_aspect_classify(_ns('design roadmap architecture blueprint'))
    implementation = cmd_aspect_classify(_ns('implement build create refactor'))

    assert analysis['aspect'] == 'analysis'
    assert planning['aspect'] == 'planning'
    assert implementation['aspect'] == 'implementation'

    # Determinism: a second identical call yields byte-identical output — there is
    # no plan-scoped / footprint state that could shift the result between calls.
    assert cmd_aspect_classify(_ns('analyze audit investigate evaluate')) == analysis
