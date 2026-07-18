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

# The build-decision handler + its extension_base seam — used by the
# non-contradiction invariant test below. extension_base lives in script-shared
# and is on sys.path (conftest wires every skill scripts dir, including the
# extension/ subdir); the handler resolves should_execute_build from it at call
# time, so monkeypatching helpers on this same module object is what the handler
# actually observes (mirrors test_build_decision.py).
import extension_base  # noqa: E402

_cmd_build_map_mod = load_script_module('plan-marshall', 'manage-config', '_cmd_build_map.py')
cmd_build_decision = _cmd_build_map_mod.cmd_build_decision


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


def test_longest_negation_phrase_wins_when_both_no_build_and_no_builds_present():
    """When the request contains BOTH 'no build' and 'no builds', the longer wins.

    'no builds' is a superstring of 'no build'; the sort-by-length-descending
    precedence must report 'no builds' (the more specific phrase), not its
    'no build' prefix.
    """
    result = cmd_aspect_classify(
        _ns('Refactor the docs; no build now and no builds later either'),
    )

    assert result['drops_build_steps'] is True
    assert result['negative_constraint_matched'] == 'no builds'


def test_no_build_substring_inside_larger_token_does_not_trigger_override():
    """'mono build' must NOT match 'no build' — word boundaries block the substring hit.

    Before the word-boundary fix, 'mono build' contained 'no build' as a
    substring ('mo[no build]') and falsely triggered the negation override.
    The request carries no genuine negation, so it must fall back to the
    implementation gate-keeping default.
    """
    result = cmd_aspect_classify(_ns('Set up a mono build for the workspace'))

    assert result['aspect'] == 'implementation'
    assert result['drops_build_steps'] is False
    assert 'negative_constraint_matched' not in result


def test_no_verify_substring_inside_larger_token_does_not_trigger_override():
    """'chrono verify' must NOT match 'no verify' — word boundaries block the substring hit."""
    result = cmd_aspect_classify(_ns('Add a chrono verify step to the pipeline'))

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


# =============================================================================
# Purity regression — NO plan-scoped read surface (deliverable 2)
#
# aspect-classify is the compose-time narrative-only signal; it deliberately
# performs no plan-scoped footprint read (the compose-time footprint is always
# empty, so a read here would mis-drop). These tests guard against a future
# re-introduction of a plan-scoped read: the CLI argument surface must expose
# no --plan-id / footprint parameter, and classification is a pure function of
# --request-text alone.
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

    assert (analysis['aspect'], analysis['drops_build_steps']) == ('analysis', True)
    assert (planning['aspect'], planning['drops_build_steps']) == ('planning', True)
    assert (implementation['aspect'], implementation['drops_build_steps']) == ('implementation', False)

    # Determinism: a second identical call yields byte-identical output — there is
    # no plan-scoped / footprint state that could shift the result between calls.
    assert cmd_aspect_classify(_ns('analyze audit investigate evaluate')) == analysis


# =============================================================================
# Non-contradiction invariant (seam-level) — aspect-classify narrative vs the
# run-time build-decision footprint gate (deliverable 2)
#
# The two signals are complementary and provably non-contradictory: for a
# pure-doc footprint the RUN-TIME backstop (build-decision --command
# quality-gate) returns not_necessary, while aspect-classify's COMPOSE-TIME
# narrative output is unaffected (it reads no footprint). This test documents
# and pins that division of labour at the seam.
# =============================================================================


def test_pure_doc_footprint_build_decision_not_necessary_while_aspect_unaffected(monkeypatch):
    """Seam invariant: pure-doc footprint -> build-decision not_necessary; aspect narrative unchanged.

    The run-time footprint backstop (D1) is the authority that skips the
    whole-tree build for a docs-only footprint; aspect-classify's narrative
    classification neither reads that footprint nor changes because of it.
    """
    # Arrange — a docs-only live footprint: production build globs registered,
    # but the changed files intersect none of them.
    monkeypatch.setattr(
        extension_base, '_read_build_map_globs', lambda _root=None: ['scripts/*.py']
    )
    monkeypatch.setattr(
        extension_base,
        '_resolve_plan_footprint',
        lambda _plan: ['doc/developer/build.adoc', 'marketplace/bundles/x/skills/y/SKILL.md'],
    )

    # Act — the run-time backstop over the same pure-doc footprint.
    verdict = cmd_build_decision(
        Namespace(command='quality-gate', plan_id='footprint-driven-build-gating', audit_plan_id=None)
    )
    # And the compose-time narrative signal over a representative docs-review request.
    aspect = cmd_aspect_classify(_ns('Review the getting-started docs wording, no build needed'))

    # Assert — the run-time backstop skips; the narrative signal is unaffected by
    # the footprint (it drops on the negation phrase, not on any footprint read).
    assert verdict['status'] == 'success'
    assert verdict['decision'] == 'not_necessary'
    assert verdict['reason']
    assert aspect['drops_build_steps'] is True
    assert aspect['negative_constraint_matched'] == 'no build'
    # The two signals AGREE here (both point away from a build) and never contradict:
    # narrative aspect-drop governs compose-time list membership, build-decision
    # governs the run-time whole-tree build.
