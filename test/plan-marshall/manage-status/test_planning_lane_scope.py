#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``planning-lane`` subcommand of manage-status.

The router resolves ``planning_lane ∈ {light, deep}`` from the DQ1 signal set
(S1–S7) plus a ``request.md`` regex, with zero codebase discovery. The default
is ``light``; any deep-precondition signal forces ``deep``; the
``plan.phase-1-init.deep_lane`` (``always``/``never``/``auto``) gate
short-circuits the signal evaluation. The ``escalate`` verb is a one-way
light→deep ratchet that refuses any downgrade.

Coverage:
- Each signal (S1–S6) firing deep in isolation. S7 (``risk_prose``) is covered
  in ``test_planning_lane_risk_prose.py``, not here.
- The all-light default (no deep signal fires).
- The deep_lane ``always`` / ``never`` short-circuit.
- ``--lane-override`` handling.
- ``--persist`` writes status.metadata.planning_lane.
- The one-way escalate invariant (deep + lane_escalated, no downgrade).
- Dispatch wiring (both verbs registered in manage-status.py argparse).
- ``evaluate_signals_pure`` — direct, I/O-free unit coverage of the extracted
  pure scorer: each of the six signal arguments firing deep in isolation, the
  all-light default, the S6 override, and the importability of the S5 regex
  constants and ``_request_is_concrete`` for downstream consumers.
- ``project_profile_pure`` — the execution-profile posture projection: the
  ``full`` / ``minimal`` / ``standard`` recommendation as a pure function of the same
  signals, the ``profile`` key on the route return, ``--persist`` writing
  ``status.metadata.execution_profile``, the independence invariant that
  ``deep_lane=always`` does NOT coerce the posture to ``full``, and the mirrored
  negative that a concrete but NON-narrow change never projects ``minimal`` (the
  security-gate half of the shared-predicate defect).
- ``classify_scope_pure`` / ``scope_estimate_from_request_pure`` — the pre-route
  coarse scope classifier over the whole band table: ``surgical`` for one-to-three
  distinct file paths with no fan-out marker, ``single_module`` for the 4–7 middle
  band and for an ambiguous pathless request, ``multi_module`` for a real fan-out
  marker or eight-or-more distinct paths, ``none`` as the DECLARED UNKNOWN for an
  unscoreable body (plus the invariant that the unknown biases S2 deep). Also the
  band boundaries at 3/4 and 7/8, markdown bold NOT registering as fan-out,
  distinct-path dedup, the ``scope_provenance`` explanation block, and the
  zero-architecture-call invariant.
- ``_read_request_body`` — the whole-body, heading-blind read: text below a
  nested ``## `` heading is reached, only the host ``# Request`` title line is
  stripped, and an absent / title-only / non-UTF-8 ``request.md`` degrades to the
  declared unknown instead of raising.
- The settled path-counter semantics — the intentional bare-filename exclusion
  (a directory separator is required) and the declared inapplicability of
  target-vs-citation discrimination, both asserted with their one-directional
  (band-widening) residual.
- The shared-population invariant — S5 concreteness and the scope band are shown
  to consume the identical body, not merely documented as doing so.
- ``cmd_scope_estimate_heuristic`` — ``--persist`` writing
  ``references.json.scope_estimate``, the ``scope_resolved`` classified-vs-unknown
  discriminator, the no-persist read-only path, the missing plan-dir error, its
  manage-status dispatch registration, and the D2 acceptance that
  pre-classification flips the router's S2 from deep to light for a concrete
  narrow request.
"""


from __future__ import annotations

import pytest
from _planning_lane_fixtures import (
    _BOILERPLATE_CITATION,
    _light_setup,
    _mod,
    _ns_route,
    _write_marshal,
    _write_request,
    classify_scope_pure,
    cmd_planning_lane_route,
    evaluate_signals_pure,
    scope_estimate_from_request_pure,
)


@pytest.mark.parametrize(
    'body',
    [
        'Fix marketplace/bundles/plan-marshall/skills/x/scripts/x.py per the diagnosis.',
        (
            'Update marketplace/bundles/plan-marshall/skills/x/scripts/x.py and '
            'test/plan-marshall/x/test_x.py.'
        ),
        (
            'Touch a/b/one.py, c/d/two.py, and e/f/three.py — three named files, no more.'
        ),
    ],
)
def test_scope_pure_surgical_for_one_to_three_paths(body):
    """One to three distinct file paths with no glob classifies surgical."""
    assert scope_estimate_from_request_pure(body) == 'surgical'


def test_scope_pure_repeated_path_counts_once():
    """The same path mentioned repeatedly counts as one distinct path (still surgical)."""
    body = 'Edit pkg/mod.py, then re-edit pkg/mod.py, and check pkg/mod.py again.'
    assert scope_estimate_from_request_pure(body) == 'surgical'


def test_scope_pure_single_module_for_the_four_to_seven_middle_band():
    """Four-to-seven distinct file paths classifies single_module — the middle band.

    Five paths is neither ``surgical`` (>3) nor ``multi_module`` (<8). The middle
    band is deliberately NOT narrow: it does not earn the S3/S4 carve-out and does
    not project the ``minimal`` posture.
    """
    body = 'Touch a/one.py, b/two.py, c/three.py, d/four.py, and e/five.py.'
    assert scope_estimate_from_request_pure(body) == 'single_module'


@pytest.mark.parametrize(
    'body',
    [
        'Sweep every skills/*/SKILL.md across the bundle.',
        'Rewrite all **/*.py under the module.',
        'Apply the change to marketplace/bundles/*/plugin.json everywhere.',
        'Rewrite the fixtures under test/plan-marshall/manage-status/** wholesale.',
    ],
)
def test_scope_pure_fan_out_marker_bands_multi_module(body):
    """A real fan-out marker bands multi_module — it WIDENS, it does not narrow.

    The inversion this replaces: a genuine glob used to band ``single_module``,
    i.e. a declared inability to enumerate the file set was reported as a narrow
    verdict. An unbounded set cannot be a bounded one, so the marker must widen.
    """
    assert scope_estimate_from_request_pure(body) == 'multi_module'


@pytest.mark.parametrize(
    'body',
    [
        'Fix **the parser** in a/b/one.py so **bold** prose stops confusing it.',
        '**Objective**\n\n**Root cause:** the regex in pkg/mod.py is too loose.',
        '- **`c/d/two.py`** — the target\n- **`e/f/three.py`** — its test\n',
    ],
)
def test_scope_pure_markdown_bold_is_not_a_fan_out_marker(body):
    """Markdown ``**bold**`` does NOT register as fan-out — the load-bearing precision fix.

    ``_GLOB_RE``'s ``**`` alternatives are path-adjacent (``/**`` / ``**/``). Before
    that tightening a bare ``**`` matched markdown bold, and because the marker
    check short-circuits AHEAD of the path count, a bold-saturated orchestrator
    spec banded on its own — making the path-count thresholds unreachable for
    essentially the entire orchestrated-plan population. Any band extension is
    vacuous without this, so the precision is pinned directly.
    """
    band, provenance = classify_scope_pure(body)

    assert provenance['fan_out_marker'] is False
    assert band == 'surgical'


@pytest.mark.parametrize(
    ('path_count', 'expected_band'),
    [(3, 'surgical'), (4, 'single_module'), (7, 'single_module'), (8, 'multi_module')],
)
def test_scope_pure_band_boundaries_at_three_four_and_seven_eight(path_count, expected_band):
    """The two band boundaries are pinned on both sides: 3/4 and 7/8 distinct paths.

    A threshold asserted only from its interior can drift by one without any test
    noticing, so each boundary is asserted from the band below AND the band above.
    """
    body = 'Touch ' + ', '.join(f'dir{i}/file{i}.py' for i in range(path_count)) + '.'

    band, provenance = classify_scope_pure(body)

    assert provenance['distinct_path_count'] == path_count
    assert band == expected_band


@pytest.mark.parametrize('body', ['', None])
def test_scope_pure_declares_unknown_for_unscoreable_body(body):
    """An unscoreable (empty / None) body yields the DECLARED UNKNOWN, not a band.

    This assertion is the inverse of the one it replaces. The prior contract had
    an empty body classify as ``single_module`` — a confident narrow-ish band
    derived from zero bytes, which is precisely the "scorer reads nothing and
    still emits a verdict" failure this change exists to remove. A body that
    cannot be scored must say so.

    ``none`` is deliberately reused rather than a new enum member: it is already
    inside the closed ``none|surgical|single_module|multi_module|broad`` set that
    ``manage-solution-outline validate`` enforces, and it is already a member of
    ``_DEEP_SCOPE_ESTIMATES``, so the unknown biases the lane DEEP (wider) rather
    than narrow. See ``test_scope_unknown_is_a_deep_biasing_s2_value`` for that
    second half — the enum choice is only correct if the routing consequence
    holds, so both are asserted.
    """
    assert scope_estimate_from_request_pure(body) == 'none'


def test_scope_pure_single_module_for_pathless_body():
    """A non-empty but pathless (ambiguous) request still bands as single_module.

    The declared-unknown change narrows to the UNSCOREABLE case only. A body that
    was read successfully and simply names no path is a real, scoreable request
    about which the coarse verdict is "not demonstrably narrow" — it keeps its
    ``single_module`` band and must NOT drift into the unknown.
    """
    assert scope_estimate_from_request_pure('Make the thing better, somehow, everywhere.') == (
        'single_module'
    )


def test_scope_unknown_is_a_deep_biasing_s2_value():
    """The declared unknown routes DEEP — the unknown must widen, never narrow.

    Guards the enum choice in ``scope_estimate_from_request_pure``: reusing
    ``none`` is only safe while ``none`` remains in ``_DEEP_SCOPE_ESTIMATES`` and
    outside ``_NARROW_SCOPE_ESTIMATES``. If a future edit moved it, the unknown
    would silently start biasing light — the exact inversion this plan removes —
    so both memberships and the end-to-end lane verdict are pinned here.
    """
    assert 'none' in _mod._DEEP_SCOPE_ESTIMATES
    assert 'none' not in _mod._NARROW_SCOPE_ESTIMATES

    verdict = evaluate_signals_pure(
        scope_estimate='none',
        change_type='bug_fix',
        compatibility='deprecation',
        plan_source='lesson',
        request_concrete=True,
    )
    assert verdict['lane'] == 'deep'
    assert 'S2:scope_estimate' in verdict['fired_signals']


# --- scope_provenance — why the band came out as it did -----------------------
#
# The operator-facing half of the fix (arm 1 of the surfacing question): the route
# return and the decision-log line explain the band rather than only asserting it.
# No new prompt and no new override seam — --lane-override / S6 already exists.


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


def test_route_surfaces_scope_provenance(plan_context):
    """The route return carries scope_provenance alongside BOTH verdicts.

    The operator reading one surface sees the lane, the posture, and the band rule
    that drove them — the whole point of surfacing provenance rather than adding a
    prompt.
    """
    plan_dir = _light_setup(plan_context, 'pl-provenance')
    _write_request(plan_dir, 'Fix marketplace/bundles/plan-marshall/skills/x/scripts/x.py.')

    result = cmd_planning_lane_route(_ns_route('pl-provenance'))

    assert result['scope_provenance'] == {
        'distinct_path_count': 1,
        'fan_out_marker': False,
        'band_rule': 'path_count_at_or_below_surgical_max',
    }
    # Both verdicts are on the same return, next to the provenance that explains them.
    assert result['planning_lane'] == 'light'
    assert result['execution_profile'] == 'minimal'


def test_route_surfaces_scope_provenance_under_the_deep_lane_short_circuit(plan_context):
    """Provenance is a property of the request body, so the deep_lane gate cannot erase it.

    ``deep_lane=always`` replaces the signal-scored verdict, but the band
    explanation must survive — otherwise the one configuration most likely to hide
    a miscalibrated band is also the one that stops reporting it.
    """
    _light_setup(plan_context, 'pl-provenance-always')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='always')

    result = cmd_planning_lane_route(_ns_route('pl-provenance-always'))

    assert result['decision_predicate'] == 'plan.phase-1-init.deep_lane=always'
    assert result['scope_provenance']['band_rule'] == 'path_count_at_or_below_surgical_max'


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


def test_scope_pure_makes_no_architecture_call(monkeypatch):
    """The classifier performs zero architecture calls (pure, regex-only)."""
    # Any attempt to import or invoke an architecture surface would raise here.
    import builtins  # noqa: PLC0415

    real_import = builtins.__import__

    def _guard_import(name, *args, **kwargs):
        assert 'architecture' not in name, f'scope classifier must not import {name}'
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', _guard_import)
    assert scope_estimate_from_request_pure('Fix pkg/one.py and pkg/two.py.') == 'surgical'
