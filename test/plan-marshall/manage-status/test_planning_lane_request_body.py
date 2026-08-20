#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end regression coverage: an orchestrated plan spec routes on its WHOLE body.

This module is deliberately distinct from ``test_planning_lane.py``. That module
unit-tests the pure helpers (``scope_estimate_from_request_pure``,
``_read_request_body``, ``_distinct_paths``). This one drives the **command entry
points** — ``cmd_scope_estimate_heuristic`` and ``cmd_planning_lane_route`` —
against a ``request.md`` fixture shaped like a real ingested orchestrator plan
spec, so the regression is pinned at the surface phase-1-init actually calls.

The defect being regressed
--------------------------

``request.md`` embeds an ingested orchestrator plan spec verbatim under
``## Original Input``, and that spec legitimately carries its own ``## ``
headings. A section-scoped read terminated the section at the spec's first
nested heading, so the router scored only the preamble — a title, an ``epic:``
line, and the plan-spec template's blockquote citation of a governing document.
The one path token in that preamble is a **citation**, never a target, so a
seven-target plan could score ``surgical`` on the strength of boilerplate.

Every fixture this module uses is built so the truncated reading and the
whole-body reading give **different answers**, which is what makes these
assertions regressions rather than restatements.

The second defect being regressed
---------------------------------

Reaching the whole body was necessary but not sufficient. The band was then
decided by a fan-out short-circuit that fired on **markdown bold** — ``_GLOB_RE``
matched a bare ``**`` — and it returned the *narrow-ish* ``single_module``. Since
orchestrator specs are saturated with ``**bold**``, essentially every orchestrated
plan banded ``single_module`` regardless of how many paths it named, the path-count
thresholds were unreachable, and ``single_module`` then satisfied
``narrow_and_concrete`` — suppressing S3/S4 (→ ``light``) *and* projecting the
``minimal`` posture, which drops the security audit. The fixtures pin all
three halves at the entry point: bold is not fan-out, a real fan-out marker
**widens** to ``multi_module``, and a large concrete spec routes ``deep`` with a
non-``minimal`` posture.

Scenarios
---------

1. ``test_orchestrated_spec_with_many_paths_and_glob_bands_multi_module`` — the
   spec's dropped region names five distinct paths and a real glob.
2. ``test_bolded_spec_with_three_paths_bands_surgical_and_routes_light`` — the
   markdown-bold regression, and simultaneously the mirror false-positive guard:
   genuinely surgical work is NOT over-escalated.
3. ``test_bolded_spec_with_ten_paths_bands_multi_module_and_routes_deep`` — the
   live reproduction, with the persisted posture asserted non-``minimal``.
4. ``test_spec_whose_only_fan_out_signal_is_a_real_glob_routes_deep`` — a single
   counted path plus one genuine ``test/**`` glob still widens to ``deep``.
5. ``test_absent_request_declares_unknown_and_routes_deep`` — an unscoreable
   body yields a declared unknown that fires S2 and resolves ``deep``
   (fail-closed).
6. ``test_empty_request_file_declares_unknown`` — a present-but-empty file
   reaches the same declared unknown as an absent one.
7. ``test_bare_filename_is_excluded_from_the_count_by_the_counter_not_the_reader``
   — the bare-filename exclusion is a counter decision, asserted as intended.

No ``conftest.py`` is introduced. The helpers and region constants this module
drives live beside it in ``_planning_lane_request_body_fixtures.py``, which
serves this module alone — nothing is shared with ``test_planning_lane.py``.
"""


from __future__ import annotations

import json

from _planning_lane_request_body_fixtures import (
    _BARE_FILENAME_REGION,
    _BOLDED_TEN_PATH_REGION,
    _BOLDED_TWO_TARGET_REGION,
    _CITATION,
    _MANY_PATHS_REGION,
    _REAL_GLOB_ONLY_REGION,
    _route_args,
    _scope_args,
    _write_marshal,
    _write_orchestrated_request,
    _write_references,
    _write_status,
    cmd_planning_lane_route,
    cmd_scope_estimate_heuristic,
)


def test_orchestrated_spec_with_many_paths_and_glob_bands_multi_module(plan_context):
    """An orchestrated spec with five paths and a real glob bands multi_module.

    The regression, stated as the two readings of one file:

    - truncated  -> 1 path (the boilerplate citation), no glob -> ``surgical``
    - whole body -> 5 distinct paths and a real fan-out marker -> ``multi_module``

    The band moved from ``single_module`` to ``multi_module`` when the fan-out
    marker stopped narrowing: a pattern is a declared inability to enumerate the
    file set, so it must widen. Both the band and ``distinct_path_count`` are
    asserted. The count is the falsifiable half: a band alone could come out right
    for the wrong reason (the fan-out short-circuit fires before any counting), so
    pinning the count proves the scored text actually reached the surface list
    rather than merely tripping the marker.
    """
    plan_dir = plan_context.plan_dir_for('plrb-many-paths')
    _write_orchestrated_request(plan_dir, _MANY_PATHS_REGION)
    _write_references(plan_dir)

    result = cmd_scope_estimate_heuristic(_scope_args('plrb-many-paths', persist=True))

    assert result['status'] == 'success'
    assert result['scope_estimate'] == 'multi_module'
    assert result['scope_resolved'] is True
    # 4 explicit targets + the boilerplate citation. The glob entry contributes
    # the fan-out marker but no path.
    assert result['distinct_path_count'] == 5, sorted(result['distinct_paths'])
    assert _CITATION in result['distinct_paths']
    assert (
        'marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py'
        in result['distinct_paths']
    )
    # The persisted value is what the router's S2 signal later reads.
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert refs['scope_estimate'] == 'multi_module'


def test_bolded_spec_with_three_paths_bands_surgical_and_routes_light(plan_context):
    """A bold-saturated spec naming three paths bands surgical and routes light.

    Two things at once, both load-bearing:

    - **The markdown-bold regression.** Pre-fix this body tripped ``_GLOB_RE``'s
      bare ``**`` alternative and short-circuited to ``single_module`` without ever
      counting. Asserting ``fan_out_marker is False`` and a count of 3 proves the
      count is now reachable, which is the precondition for the whole band
      extension being anything other than vacuous.
    - **The mirror false-positive guard.** ``_SURGICAL_MAX_PATHS`` is deliberately
      untouched by this plan, so genuinely bounded work must still route ``light``
      with the ``minimal`` posture. A fix that widened the band for large requests
      by over-escalating small ones would trade one wrong verdict for another.
    """
    plan_dir = plan_context.plan_dir_for('plrb-bold-three')
    _write_orchestrated_request(plan_dir, _BOLDED_TWO_TARGET_REGION)
    _write_references(plan_dir)
    _write_status(plan_dir)
    _write_marshal(plan_context.fixture_dir)

    scope_result = cmd_scope_estimate_heuristic(_scope_args('plrb-bold-three', persist=True))

    # The boilerplate citation plus two qualified targets.
    assert scope_result['distinct_path_count'] == 3, sorted(scope_result['distinct_paths'])
    assert scope_result['scope_estimate'] == 'surgical'

    route_result = cmd_planning_lane_route(_route_args('plrb-bold-three', persist=True))

    # Provenance is the direct evidence that bold is not fan-out: had the bare
    # `**` alternative survived, the marker would have short-circuited the band
    # before the count was ever taken.
    assert route_result['scope_provenance']['fan_out_marker'] is False
    assert route_result['scope_provenance']['band_rule'] == (
        'path_count_at_or_below_surgical_max'
    )
    assert route_result['planning_lane'] == 'light'
    assert route_result['fired_signals'] == []
    # The mirror guard on the posture axis: bounded work keeps its cheap posture.
    assert route_result['execution_profile'] == 'minimal'


def test_bolded_spec_with_ten_paths_bands_multi_module_and_routes_deep(plan_context):
    """A bolded ten-path spec bands multi_module, fires S2, routes deep, and is not minimal.

    The live reproduction of the under-routed population. Pre-fix this body banded
    ``single_module`` on the bold short-circuit, S2 stayed quiet, the
    ``narrow_and_concrete`` carve-out suppressed S3/S4, and the posture collapsed
    to ``minimal``. Post-fix the count is reachable and crosses the
    ``multi_module`` floor, so the request is finally described at its real scale.

    The persisted ``execution_profile`` is asserted, not just the projection: the
    security-gate suppression path has to be closed at the surface phase-1-init
    actually writes, not only in the pure function.
    """
    plan_dir = plan_context.plan_dir_for('plrb-bold-ten')
    _write_orchestrated_request(plan_dir, _BOLDED_TEN_PATH_REGION)
    _write_references(plan_dir)
    _write_status(plan_dir)
    _write_marshal(plan_context.fixture_dir)

    scope_result = cmd_scope_estimate_heuristic(_scope_args('plrb-bold-ten', persist=True))

    assert scope_result['scope_estimate'] == 'multi_module'
    # Ten targets + the boilerplate citation.
    assert scope_result['distinct_path_count'] == 11, sorted(scope_result['distinct_paths'])

    route_result = cmd_planning_lane_route(_route_args('plrb-bold-ten', persist=True))

    # The band came from the COUNT, not from bold tripping the marker — which is
    # what makes this the reproduction of the under-routed population rather than
    # an incidental pass.
    assert route_result['scope_provenance']['fan_out_marker'] is False
    assert route_result['scope_provenance']['band_rule'] == (
        'path_count_at_or_above_multi_module_floor'
    )
    assert route_result['planning_lane'] == 'deep'
    assert 'S2:scope_estimate' in route_result['fired_signals']
    assert route_result['execution_profile'] != 'minimal'
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['execution_profile'] != 'minimal'


def test_spec_whose_only_fan_out_signal_is_a_real_glob_routes_deep(plan_context):
    """A real fan-out marker widens to multi_module and routes deep on ONE counted path.

    The truthful-negative case, end to end: "I cannot enumerate the file set" must
    not be reported as a narrow verdict. The path count here is 1 — inside the
    surgical range — so the ``deep`` outcome is attributable to the marker alone,
    which is exactly the inversion this plan removes.
    """
    plan_dir = plan_context.plan_dir_for('plrb-real-glob')
    _write_orchestrated_request(plan_dir, _REAL_GLOB_ONLY_REGION)
    _write_references(plan_dir)
    _write_status(plan_dir)
    _write_marshal(plan_context.fixture_dir)

    scope_result = cmd_scope_estimate_heuristic(_scope_args('plrb-real-glob', persist=True))

    # A single counted path — inside the surgical range — so only the marker can
    # be responsible for the widening.
    assert scope_result['distinct_path_count'] == 1, sorted(scope_result['distinct_paths'])
    assert scope_result['scope_estimate'] == 'multi_module'

    route_result = cmd_planning_lane_route(_route_args('plrb-real-glob', persist=True))

    assert route_result['scope_provenance']['fan_out_marker'] is True
    assert route_result['scope_provenance']['band_rule'] == 'fan_out_marker'
    assert route_result['planning_lane'] == 'deep'
    assert 'S2:scope_estimate' in route_result['fired_signals']
    assert route_result['execution_profile'] != 'minimal'
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['execution_profile'] != 'minimal'


# =============================================================================
# Scenario 2 — an unscoreable body declares unknown and fails closed to deep
# =============================================================================


def test_absent_request_declares_unknown_and_routes_deep(plan_context):
    """An unscoreable body yields a DECLARED UNKNOWN and routes deep, not a band.

    Runs the real phase-1-init order: classify-and-persist, then route. The
    unknown must be distinguishable **on the return payload** — asserting only
    that "some band came back" is exactly the blindness this plan removes, so
    ``scope_resolved`` is asserted alongside the value.

    Fail-closed direction matters as much as the label: ``none`` is a
    deep-biasing S2 value, so a request nobody could score widens the lane
    instead of narrowing it.
    """
    plan_dir = plan_context.plan_dir_for('plrb-absent-request')
    plan_dir.mkdir(parents=True, exist_ok=True)
    _write_references(plan_dir)
    _write_status(plan_dir)
    # No request.md is written at all.

    scope_result = cmd_scope_estimate_heuristic(
        _scope_args('plrb-absent-request', persist=True)
    )

    assert scope_result['scope_estimate'] == 'none'
    assert scope_result['scope_resolved'] is False, (
        'the unknown must be distinguishable on the payload, not inferred from the label'
    )
    assert scope_result['distinct_path_count'] == 0

    route_result = cmd_planning_lane_route(_route_args('plrb-absent-request'))

    assert route_result['status'] == 'success'
    assert route_result['planning_lane'] == 'deep'
    assert 'S2:scope_estimate' in route_result['fired_signals'], (
        'the declared unknown must fire S2 itself, not merely ride S1/S5 to deep'
    )
    assert route_result['signals']['scope_estimate'] == 'none'


def test_empty_request_file_declares_unknown(plan_context):
    """A present-but-empty request.md is unscoreable too, and declares the unknown.

    Distinct from the absent-file case above: the file exists and reads cleanly,
    so the emptiness is a property of the content rather than of the filesystem.
    Both must reach the same declared unknown.
    """
    plan_dir = plan_context.plan_dir_for('plrb-empty-request')
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'request.md').write_text('', encoding='utf-8')
    _write_references(plan_dir)

    result = cmd_scope_estimate_heuristic(_scope_args('plrb-empty-request', persist=True))

    assert result['scope_estimate'] == 'none'
    assert result['scope_resolved'] is False


def test_bare_filename_is_excluded_from_the_count_by_the_counter_not_the_reader(
    plan_context,
):
    """A bare filename contributes zero to the count — the DELIBERATE, settled exclusion.

    This is NOT an accidental pin of a defect. ``_PATH_RE`` requires a directory
    separator by design, settled in this plan's D1/D2 investigation: a bare
    filename cannot be resolved to a repo location without the directory
    discovery this module is defined to exclude, and matching bare ``word.word``
    tokens would sweep in ordinary prose (``e.g.``, version numbers,
    sentence-final abbreviations). The resulting under-count biases toward the
    WIDER band, which is the safe direction.

    What makes this a regression rather than a restatement is *where* the
    exclusion happens. Before the whole-body read, a bare filename below a
    nested heading was uncounted for an entirely different reason — the reader
    never saw it — and the two causes were indistinguishable from the outside.
    The count moving from 1 to 3 proves the reader now reaches the surface list,
    while the bare names staying out of ``distinct_paths`` proves the counter,
    not the reader, is what excludes them.
    """
    plan_dir = plan_context.plan_dir_for('plrb-bare-filename')
    _write_orchestrated_request(plan_dir, _BARE_FILENAME_REGION)
    _write_references(plan_dir)

    result = cmd_scope_estimate_heuristic(_scope_args('plrb-bare-filename', persist=True))

    counted = set(result['distinct_paths'])
    # The reader reached the surface list: both directory-qualified targets are in.
    assert 'pkg/alpha/target_one.py' in counted
    assert 'pkg/beta/target_two.py' in counted
    # The counter excluded both bare names, though the reader delivered them.
    assert 'retro_sections.py' not in counted
    assert 'agents.md' not in counted
    # Citation + two qualified targets. Four names were listed; three are paths.
    assert result['distinct_path_count'] == 3, sorted(counted)
    # Three distinct paths and no glob still reads as surgical.
    assert result['scope_estimate'] == 'surgical'
    assert result['scope_resolved'] is True
