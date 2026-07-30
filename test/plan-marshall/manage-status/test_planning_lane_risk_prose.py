#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""S7 — the author's own written scale warning as a deep-bias signal.

Every other signal the planning-lane router scores is an *inference*: a path
count, a metadata stamp, a config value. S7 is the one signal that is a
*statement* — the author saying, in prose, that the work is large. That
difference is the whole design, and it is why S7 sits deliberately OUTSIDE the
narrow-and-concrete carve-out: the carve-out exists to stop a cheap band plus a
generative ``change_type`` from forcing ``deep``, but an explicit warning is not a
cheap inference and must outrank the band.

Coverage
--------

1. ``test_each_warning_phrase_fires_s7`` — each of the eight warning phrases is
   detected in isolation, so a phrase silently dropped from ``_RISK_PROSE_RE``
   fails a named case rather than disappearing.
2. ``test_ordinary_prose_does_not_fire_s7`` — the false-positive bar.
3. ``test_word_boundary_anchoring_rejects_substring_matches`` — the anchoring is
   asserted, not assumed: ``epicenter`` / ``foundational`` must not match.
4. ``test_s7_is_not_relaxed_by_the_narrow_and_concrete_carve_out`` — the load-bearing
   case: a surgical AND concrete request carrying an explicit warning still routes
   ``deep``.
5. ``test_s7_appears_in_fired_signals_and_signals`` — S7 is observable on both
   halves of the return, in canonical S1..S7 order.
6. ``test_s7_absent_by_default_cannot_manufacture_deep`` — the default value is the
   NEUTRAL one, so a consumer that omits ``risk_prose`` never gets a deep verdict
   it supplied no evidence for.
7. ``test_route_end_to_end_fires_s7_from_the_request_body`` — the signal is wired
   through the real reader at the command entry point, not only in the pure scorer.
8. ``test_epic_metadata_key_fires_s7_a_documented_conservative_over_fire`` — the
   known over-fire, pinned as a property so it cannot change silently.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module

_mod = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_planning_lane.py', '_cmd_planning_lane_risk_prose'
)
evaluate_signals_pure = _mod.evaluate_signals_pure
cmd_planning_lane_route = _mod.cmd_planning_lane_route

# The all-light baseline: surgical band, non-generative change, non-breaking
# compatibility, pre-specified source, concrete request, no override, NO warning.
# Every signal biases light, so any deep verdict below is attributable to S7 alone.
_LIGHT_KWARGS = {
    'scope_estimate': 'surgical',
    'change_type': 'bug_fix',
    'compatibility': 'deprecation',
    'plan_source': 'lesson',
    'request_concrete': True,
    'risk_prose': False,
    'override': None,
}

# The eight warning phrases `_RISK_PROSE_RE` declares, each embedded in a
# realistic sentence rather than asserted bare, so the word-boundary anchoring is
# exercised on both sides of the phrase.
_WARNING_SENTENCES = [
    'This is a multi-PR block and cannot land in one go.',
    'The change is codebase-wide and touches every bundle.',
    'This is the largest item in the queue.',
    'It is also the riskiest thing we have shipped.',
    'Expect a split into staged plans.',
    'This is foundation work everything else builds on.',
    'Tracked under the truthful-signals epic.',
    'The rename is a campaign, not a single fix.',
]


def _pure(**overrides):
    """Score ``evaluate_signals_pure`` from the all-light baseline."""
    return evaluate_signals_pure(**{**_LIGHT_KWARGS, **overrides})


# =============================================================================
# Detection — each phrase, and the false-positive bar
# =============================================================================


@pytest.mark.parametrize('sentence', _WARNING_SENTENCES)
def test_each_warning_phrase_fires_s7(sentence):
    """Each declared warning phrase is detected in isolation.

    One case per alternative of ``_RISK_PROSE_RE``. A phrase quietly removed from
    the pattern fails its own named case instead of vanishing from coverage.
    """
    assert _mod._request_has_risk_prose(sentence) is True


@pytest.mark.parametrize(
    'body',
    [
        'Fix the parser in pkg/mod.py so the two failing tests pass.',
        'Rename one constant and update its docstring.',
        'The regex is too loose. Tighten it and add a boundary case.',
    ],
)
def test_ordinary_prose_does_not_fire_s7(body):
    """Ordinary request prose carries no warning — the false-positive bar."""
    assert _mod._request_has_risk_prose(body) is False


def test_empty_body_does_not_fire_s7():
    """An unscoreable body has no warning to report.

    The unknown case is already covered twice over by S2 (declared-unknown band)
    and S5 (no anchors), both of which bias deep, so S7 deliberately adds no third
    opinion there rather than inventing evidence from zero bytes.
    """
    assert _mod._request_has_risk_prose('') is False


@pytest.mark.parametrize(
    'body',
    [
        'The epicenter of the failure is the resolver.',
        'This is foundational reading, not a work item.',
        'Recampaigning the metric is out of scope.',
    ],
)
def test_word_boundary_anchoring_rejects_substring_matches(body):
    """The anchoring is asserted rather than assumed.

    ``_RISK_PROSE_RE`` is word-boundary anchored, so ``epicenter``,
    ``foundational`` and ``recampaigning`` must NOT fire. Without this the signal
    would be a substring sweep over ordinary prose, and a signal that fires on
    everything carries no information — the mirror of a guard that never fires.
    """
    assert _mod._request_has_risk_prose(body) is False


# =============================================================================
# S7 outranks the carve-out — the load-bearing behaviour
# =============================================================================


def test_s7_is_not_relaxed_by_the_narrow_and_concrete_carve_out():
    """A surgical AND concrete request carrying an explicit warning still routes deep.

    The whole point of S7. Every other signal in the baseline biases light and the
    request satisfies ``narrow_and_concrete`` exactly, so the carve-out is active —
    yet the author's statement that this is a multi-PR split must still win. If S7
    were folded into the carve-out alongside S3/S4 this case would route ``light``
    and the signal would be unable to do the one job it exists for.
    """
    result = _pure(risk_prose=True)

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S7:risk_prose']


def test_s7_appears_in_fired_signals_and_signals():
    """S7 is observable on both halves of the return, in canonical S1..S7 order."""
    result = _pure(scope_estimate='multi_module', change_type='feature', risk_prose=True)

    assert result['signals']['risk_prose'] is True
    assert result['fired_signals'] == [
        'S2:scope_estimate',
        'S3:change_type',
        'S7:risk_prose',
    ]


def test_s7_absent_by_default_cannot_manufacture_deep():
    """Omitting ``risk_prose`` yields the NEUTRAL value, never a deep verdict.

    ``risk_prose`` defaults to False so a downstream consumer scoring only the
    band-and-metadata signals keeps working. The default direction matters: the
    absence of a warning is not evidence OF a warning, so the default can never
    invent a deep verdict the caller supplied no evidence for.
    """
    kwargs = {k: v for k, v in _LIGHT_KWARGS.items() if k != 'risk_prose'}

    result = evaluate_signals_pure(**kwargs)

    assert result['lane'] == 'light'
    assert result['signals']['risk_prose'] is False
    assert 'S7:risk_prose' not in result['fired_signals']


def test_s7_does_not_change_the_posture_projection():
    """S7 governs planning DEPTH only — it is not an input to the posture projection.

    ``project_profile_pure`` scores the band, the change type, the compatibility
    and concreteness. S7 is deliberately absent from it, so an author warning
    ratchets the lane without silently also ratcheting the finalize ceremony. The
    two axes stay independent, exactly as the deep_lane gate does.
    """
    without_warning = _pure()['profile']['recommended_posture']
    with_warning = _pure(risk_prose=True)['profile']['recommended_posture']

    assert with_warning == without_warning


# =============================================================================
# End-to-end — the signal is wired through the real reader
# =============================================================================


def _write_request(plan_dir: Path, body: str) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'request.md').write_text(
        f'# Request: risk prose\n\nsource: description\n\n{body}\n', encoding='utf-8'
    )


def _write_status(plan_dir: Path) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps(
            {
                'plan_id': plan_dir.name,
                'phases': [],
                'metadata': {'plan_source': 'lesson', 'change_type': 'bug_fix'},
            }
        ),
        encoding='utf-8',
    )


def _write_references(plan_dir: Path) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'references.json').write_text(
        json.dumps({'base_branch': 'main', 'scope_estimate': 'surgical'}), encoding='utf-8'
    )


def _write_marshal(fixture_dir: Path) -> None:
    (fixture_dir / 'marshal.json').write_text(
        json.dumps(
            {
                'plan': {
                    'phase-1-init': {'deep_lane': 'auto'},
                    'phase-2-refine': {'compatibility': 'deprecation'},
                }
            },
            indent=2,
        ),
        encoding='utf-8',
    )


def _route(plan_id: str) -> Namespace:
    return Namespace(plan_id=plan_id, lane_override=None, persist=False)


def test_route_end_to_end_fires_s7_from_the_request_body(plan_context):
    """The reader wires S7 through the command entry point, not only the pure scorer.

    A surgical band is persisted and every other signal biases light, so the
    ``deep`` verdict here is produced by the warning sentence in ``request.md``
    alone — which is the only way to show the body is actually being scanned for
    S7 rather than the flag being threaded but never read.
    """
    plan_dir = plan_context.plan_dir_for('plrp-e2e')
    _write_request(
        plan_dir,
        'Fix pkg/one.py. This is the largest and riskiest block — expect a multi-PR split.',
    )
    _write_status(plan_dir)
    _write_references(plan_dir)
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_route('plrp-e2e'))

    assert result['signals']['scope_estimate'] == 'surgical'
    assert result['signals']['request_concrete'] is True
    assert result['signals']['risk_prose'] is True
    assert result['planning_lane'] == 'deep'
    assert result['fired_signals'] == ['S7:risk_prose']


def test_route_without_warning_prose_stays_light(plan_context):
    """The mirror case: the same baseline without a warning routes light.

    Pairs with the test above so the ``deep`` verdict there is attributable to the
    warning sentence and not to some other property of the fixture.
    """
    plan_dir = plan_context.plan_dir_for('plrp-e2e-quiet')
    _write_request(plan_dir, 'Fix pkg/one.py. The boundary check is off by one.')
    _write_status(plan_dir)
    _write_references(plan_dir)
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_route('plrp-e2e-quiet'))

    assert result['signals']['risk_prose'] is False
    assert result['planning_lane'] == 'light'
    assert result['fired_signals'] == []


def test_epic_metadata_key_does_not_fire_s7():
    """The ``epic:`` METADATA KEY is document chrome, not an author warning.

    Every ingested orchestrator plan spec opens with an ``epic:`` line. A bare
    ``\\bepic\\b`` would therefore fire S7 for the entire orchestrated population,
    which would make the signal mean "is orchestrator-authored" instead of "the
    author warned about scale" — and would make it impossible for ANY orchestrated
    request, however genuinely surgical, to route ``light`` ever again. That is the
    same failure shape as ``_GLOB_RE``'s bare ``**`` matching markdown bold: an
    alternative that matches chrome rather than content fires vacuously. The
    ``(?!\\s*:)`` lookahead is the fix, and this is its regression.
    """
    assert (
        _mod._request_has_risk_prose('epic: truthful-signals\nworkstream: WS-01\n') is False
    )


def test_epic_in_prose_still_fires_s7():
    """The exclusion is scoped to the key form only — prose ``epic`` still counts.

    Pairs with the test above: without this the lookahead could be widened into a
    blanket removal of the ``epic`` alternative and nothing would notice.
    """
    assert _mod._request_has_risk_prose('Tracked under the truthful-signals epic.') is True
    assert _mod._request_has_risk_prose('This is an epic rename across the tree.') is True
