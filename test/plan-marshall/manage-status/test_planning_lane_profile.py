#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``planning-lane`` subcommand of manage-status."""


from __future__ import annotations

from argparse import Namespace

import pytest
from _planning_lane_fixtures import (
    _BOILERPLATE_CITATION,
    _mod,
    _ns_route,
    _ns_scope,
    _pure,
    _write_ingested_request,
    _write_marshal,
    _write_references,
    _write_request,
    _write_status,
    classify_scope_pure,
    cmd_planning_lane_route,
    cmd_scope_estimate_heuristic,
    project_profile_pure,
    scope_estimate_from_request_pure,
)


def test_concreteness_and_scope_consume_the_identical_body(plan_context, monkeypatch):
    """S5 concreteness and the scope band read the SAME text — asserted, not claimed.

    The two signals are corroborating readings of one request. If one consumer
    were ever narrowed (say, to a declared-surface region) while the other kept
    the whole body, they would silently describe different documents and their
    agreement would stop meaning anything. This records the shared-population
    invariant behaviourally by capturing what each consumer actually receives.
    """
    plan_dir = plan_context.plan_dir_for('pl-shared-population')
    _write_ingested_request(plan_dir)
    _write_status(plan_dir)
    _write_references(plan_dir, scope_estimate=None)

    seen: list[str] = []
    real_read = _mod._read_request_body

    def _recording_read(plan_id: str) -> str:
        # _mod is loaded dynamically, so real_read is untyped (Any) to mypy.
        body: str = real_read(plan_id)
        seen.append(body)
        return body

    monkeypatch.setattr(_mod, '_read_request_body', _recording_read)

    _mod._evaluate_signals('pl-shared-population', {})
    cmd_scope_estimate_heuristic(Namespace(plan_id='pl-shared-population', persist=False))

    assert len(seen) == 2, 'both consumers must go through _read_request_body'
    assert seen[0] == seen[1] != ''


# =============================================================================
# project_profile_pure — execution-profile posture projection
# =============================================================================
#
# The posture projection recommends minimal / standard / full over the SAME signals
# the lane verdict scores. It is a pure derivation (no I/O, no cognition) and is
# independent of the deep_lane ceremony gate (deep_lane governs planning depth,
# not the profile — §4.2 of the lane-selection outline).


@pytest.mark.parametrize('change_type', ['feature', 'feature_breaking'])
@pytest.mark.parametrize('scope_estimate', ['multi_module', 'broad'])
def test_profile_generative_broad_change_projects_full(change_type, scope_estimate):
    """A generative change over a broad scope projects the full posture."""
    posture = project_profile_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility='deprecation',
        request_concrete=True,
    )

    assert posture == 'full'


def test_profile_narrow_concrete_breaking_change_projects_minimal():
    """A surgical, concretely-specified breaking generative change projects minimal.

    The narrow-and-concrete predicate dominates: a bounded surgical fix stays
    ``minimal`` even when its change_type reads generative and its compatibility
    reads breaking. (A BROAD generative breaking change still projects full — see
    ``test_profile_generative_broad_change_projects_full``.)
    """
    posture = project_profile_pure(
        scope_estimate='surgical',
        change_type='feature',
        compatibility='breaking',
        request_concrete=True,
    )

    assert posture == 'minimal'


def test_profile_narrow_concrete_nongenerative_change_projects_minimal():
    """A non-generative, SURGICAL, concretely-specified change projects minimal.

    ``surgical`` is the sole member of ``_NARROW_SCOPE_ESTIMATES``, so this case is
    no longer parametrized over ``single_module``: the middle band does not earn
    the carve-out. See
    ``test_profile_non_narrow_concrete_change_does_not_project_minimal`` for the
    mirrored negative.
    """
    posture = project_profile_pure(
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
    )

    assert posture == 'minimal'


def test_profile_narrow_nongenerative_but_vague_request_projects_standard():
    """A narrow non-generative change with a vague request falls back to standard."""
    posture = project_profile_pure(
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=False,
    )

    assert posture == 'standard'


def test_profile_generative_narrow_concrete_change_projects_minimal():
    """A generative but SURGICAL, concretely-specified change projects minimal.

    Under the narrow-and-concrete carve-out the bounded, well-anchored generative
    change is recommended ``minimal`` — the narrow, concrete bound dominates the
    generative signal. Narrowness is now literal: only ``surgical`` qualifies.
    """
    posture = project_profile_pure(
        scope_estimate='surgical',
        change_type='feature',
        compatibility='deprecation',
        request_concrete=True,
    )

    assert posture == 'minimal'


@pytest.mark.parametrize('scope_estimate', ['single_module', 'multi_module'])
@pytest.mark.parametrize('change_type', ['bug_fix', 'feature'])
def test_profile_non_narrow_concrete_change_does_not_project_minimal(scope_estimate, change_type):
    """The mirrored negative: a concrete but NON-narrow change never projects minimal.

    This is the security-gate half of the defect. ``_NARROW_SCOPE_ESTIMATES`` is
    shared verbatim with ``evaluate_signals_pure``, so before the narrowing a
    ``single_module`` band collapsed the posture to ``minimal`` — which drops the
    security audit, the sonar round-trip and the self-review — purely on the
    strength of a catch-all band. Asserting the lane alone would have left this
    path live, so the posture is pinned independently here.
    """
    posture = project_profile_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility='breaking',
        request_concrete=True,
    )

    assert posture != 'minimal'


def test_profile_projection_is_deterministic_over_the_signal_set():
    """The projection is a pure function — identical inputs yield identical output."""
    kwargs = {
        'scope_estimate': 'multi_module',
        'change_type': 'feature',
        'compatibility': 'breaking',
        'request_concrete': False,
    }

    first = project_profile_pure(**kwargs)
    second = project_profile_pure(**kwargs)

    assert first == second == 'full'


def test_evaluate_signals_pure_emits_profile_projection():
    """evaluate_signals_pure carries the profile projection alongside the lane verdict."""
    result = _pure(scope_estimate='multi_module', change_type='feature')

    assert result['profile']['recommended_posture'] == 'full'
    assert result['profile']['candidate_postures'] == ['minimal', 'standard', 'full']


# --- scope_provenance — why the band came out as it did -----------------------
#
# The operator-facing half of the fix (arm 1 of the surfacing question): the route
# return and the decision-log line explain the band rather than only asserting it.
# No new prompt and no new override seam — --lane-override / S6 already exists.


# =============================================================================
# classify_scope_pure — pre-route coarse scope classifier (D2)
# =============================================================================

@pytest.mark.parametrize(
    ('body', 'expected_rule', 'expected_count', 'expected_fan_out'),
    [
        ('', 'unscoreable_body', 0, False),
        (
            'Sweep test/plan-marshall/x/test_x.py and every marketplace/bundles/*/plugin.json.',
            'fan_out_marker',
            1,
            True,
        ),
        (
            'Touch ' + ', '.join(f'dir{i}/file{i}.py' for i in range(8)) + '.',
            'path_count_at_or_above_multi_module_floor',
            8,
            False,
        ),
        ('Touch a/one.py, b/two.py, c/three.py, d/four.py.', 'path_count_middle_band', 4, False),
        ('Fix a/one.py.', 'path_count_at_or_below_surgical_max', 1, False),
        ('Make the thing better, somehow.', 'pathless_non_empty_body', 0, False),
    ],
)
def test_classify_scope_pure_reports_the_band_rule_that_fired(
    body, expected_rule, expected_count, expected_fan_out
):
    """Every row of the band table reports its own ``band_rule`` plus both measurements.

    One case per table row, so a future row that stops being reachable — a
    vacuous band — shows up as a failing case rather than as silently dead code.
    """
    _band, provenance = classify_scope_pure(body)

    assert provenance == {
        'distinct_path_count': expected_count,
        'fan_out_marker': expected_fan_out,
        'band_rule': expected_rule,
    }


def test_classify_scope_pure_band_and_provenance_cannot_disagree():
    """``scope_estimate_from_request_pure`` is a projection of ``classify_scope_pure``.

    The band and its explanation come from ONE decision, so the thin wrapper can
    never drift from the provenance-bearing classifier.
    """
    body = 'Rewrite all **/*.py under the module.'

    assert scope_estimate_from_request_pure(body) == classify_scope_pure(body)[0]


# --- Settled path-counter semantics ------------------------------------------
#
# Both properties below are DECISIONS recorded in _distinct_paths' docstring, not
# accidents of the regex. They are asserted so a future edit has to change the
# test deliberately rather than drift.


@pytest.mark.parametrize(
    'bare_name',
    ['_cmd_planning_lane.py', 'agents.md', 'retro_sections.py'],
)
def test_distinct_paths_excludes_bare_filenames_intentionally(bare_name):
    """A bare filename is deliberately NOT counted — a directory separator is required.

    ``_PATH_RE`` matches only ``dir/name.ext``. This exclusion is intentional: a
    bare filename cannot be resolved to a repo location without the directory
    discovery this module is defined to exclude, and matching bare ``word.word``
    tokens would sweep in ordinary prose (``e.g.``, version numbers,
    sentence-final abbreviations). The consequence is an UNDER-count, which
    biases toward the wider band — the same conservative direction as citation
    inflation.
    """
    body = f'Rewrite {bare_name} so the handler is reachable.'

    assert _mod._distinct_paths(body) == set()
    # Under-counting to zero paths lands in single_module (wider), never surgical.
    assert scope_estimate_from_request_pure(body) == 'single_module'


def test_distinct_paths_counts_a_citation_it_cannot_distinguish_from_a_target():
    """The counter counts path STRINGS; it cannot tell a citation from a target.

    A body whose only path is a citation of a governing document still counts
    one path and bands ``surgical``. The sensor declares its inapplicability for
    this discrimination rather than faking it — but the residual must stay
    visible, so it is asserted rather than left implicit. The error is
    one-directional: citations INFLATE the count, and inflation moves the band
    from ``surgical`` toward ``single_module`` (wider), never the reverse.
    """
    citation_only = (
        'Tidy the hand-off prose. See '
        f'`{_BOILERPLATE_CITATION}` for the tier contract.'
    )

    assert _mod._distinct_paths(citation_only) == {_BOILERPLATE_CITATION}
    assert scope_estimate_from_request_pure(citation_only) == 'surgical'

    # Adding real targets alongside the citation moves the band wider, never narrower.
    with_targets = (
        f'{citation_only} Change a/one.py, b/two.py, c/three.py and d/four.py.'
    )
    assert scope_estimate_from_request_pure(with_targets) == 'single_module'


# =============================================================================
# D2 acceptance — pre-route classification unblocks the light lane
# =============================================================================


def test_prerouted_surgical_scope_flips_s2_from_deep_to_light(plan_context):
    """The pre-route scope classification flips S2 from deep (None) to light (surgical).

    Before D2, a concrete narrow request reached the router with scope_estimate
    unset, so S2 fired deep unconditionally. After the pre-route classifier
    persists scope_estimate=surgical, S2 no longer fires and the router reaches
    the light lane for a well-bounded, concrete request.
    """
    plan_dir = plan_context.plan_dir_for('pl-d2-accept')
    _write_request(plan_dir, 'Fix marketplace/bundles/plan-marshall/skills/x/scripts/x.py per the diagnosis.')
    _write_status(plan_dir, metadata={'plan_source': 'lesson', 'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate=None)
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='auto')

    # Pre-classification: with scope_estimate still None, S2 fires deep.
    before = cmd_planning_lane_route(_ns_route('pl-d2-accept'))
    assert before['planning_lane'] == 'deep'
    assert 'S2:scope_estimate' in before['fired_signals']

    # Run the pre-route classifier; it persists scope_estimate=surgical.
    scope_result = cmd_scope_estimate_heuristic(_ns_scope('pl-d2-accept', persist=True))
    assert scope_result['scope_estimate'] == 'surgical'

    # Now the router routes light — S2 no longer fires.
    after = cmd_planning_lane_route(_ns_route('pl-d2-accept'))
    assert after['planning_lane'] == 'light'
    assert 'S2:scope_estimate' not in after['fired_signals']
