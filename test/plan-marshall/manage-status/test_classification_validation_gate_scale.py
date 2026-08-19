#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the deterministic classification-validation gate."""


from __future__ import annotations

import builtins

import pytest
from _classification_validation_gate_fixtures import (
    _FEATURE_BODY,
    _MULTI_MODULE_MIN_PATHS,
    _SCALE_BAND_ROW_BODIES,
    _body_with_fan_out_marker,
    _body_with_paths,
    _body_with_unscannable_line,
    _ns_route,
    _write_marshal,
    _write_references,
    _write_request,
    _write_status,
    classify_scope_pure,
    cmd_planning_lane_route,
    read_request_body,
    run_classification_validation,
)


def test_scale_mismatch_boundary_is_driven_by_the_sensor_threshold(plan_context):
    """The 7/8 boundary comes from the SENSOR's constant, not from a copy in the gate.

    Asserted from both sides of the floor, and the floor itself is read from
    ``_cmd_planning_lane``. If the sensor's threshold moved and the gate had its own
    copy, these two cases would disagree — which is the drift the import exists to
    prevent.
    """
    below = _MULTI_MODULE_MIN_PATHS - 1
    below_dir = plan_context.plan_dir_for('cv-scale-below')
    _write_request(below_dir, _body_with_paths(below))
    _write_status(below_dir, metadata={'change_type': 'tech_debt'})
    _write_references(below_dir, scope_estimate='surgical')

    at_floor_dir = plan_context.plan_dir_for('cv-scale-at-floor')
    _write_request(at_floor_dir, _body_with_paths(_MULTI_MODULE_MIN_PATHS))
    _write_status(at_floor_dir, metadata={'change_type': 'tech_debt'})
    _write_references(at_floor_dir, scope_estimate='surgical')

    below_result = run_classification_validation('cv-scale-below')
    at_floor_result = run_classification_validation('cv-scale-at-floor')

    assert below_result['mismatch_count'] == 0, f'{below} paths must not fire'
    assert at_floor_result['mismatch_count'] == 1, (
        f'{_MULTI_MODULE_MIN_PATHS} paths must fire'
    )


# -----------------------------------------------------------------------------
# Class 3 — scan_incomplete propagation (the detector's own scale-blind spot)
# -----------------------------------------------------------------------------


def test_scale_mismatch_fires_when_the_scan_is_incomplete_below_the_floor(plan_context):
    """An incomplete scan is NOT evidence of narrowness — the class must still fire.

    The regression this test pins: the detector used to call ``_distinct_paths``,
    which DISCARDS ``scan_incomplete`` and returns only the paths the bounded scan
    reached. On a body too large / adversarially-repetitive to scan in full, that
    total is an UNDERCOUNT, so comparing it against the floor let the detector
    return ``None`` on exactly the body the sensor bands ``multi_module`` — the
    scale-blind false negative this whole gate exists to catch, reproduced inside
    the safety net itself.

    The fixture is deliberately below the floor on the scannable text alone, so a
    count-only reading sees "2 paths, narrow, nothing to flag" and passes silently.
    """
    plan_dir = plan_context.plan_dir_for('cv-scale-scan-incomplete')
    _write_request(plan_dir, _body_with_unscannable_line(2))
    _write_status(plan_dir, metadata={'change_type': 'tech_debt'})
    _write_references(plan_dir, scope_estimate='surgical')

    result = run_classification_validation('cv-scale-scan-incomplete')

    classes = {m['mismatch'] for m in result['mismatches']}
    assert classes == {'scale_mismatch_light_routing'}, (
        'an incomplete scan under the floor must fall through to the mismatch, '
        'not short-circuit past it'
    )
    assert result['findings_emitted'] == 1
    # Flag-not-block is unchanged by the widened predicate.
    assert result['status'] == 'success'
    assert result['blocked'] is False


def test_scale_mismatch_agrees_with_the_sensor_band_on_an_incomplete_scan(plan_context):
    """The gate's verdict and the sensor's band are asserted on the SAME body.

    This is the anti-drift assertion, not a restatement of the test above: it reads
    the sensor's own verdict for the fixture (``multi_module`` via the
    ``scan_incomplete`` band rule, which wins BEFORE the path-count rows) and
    requires the gate to disagree with the persisted ``surgical`` for that body. If
    a future change made either side read a truncated scan as a low count, exactly
    one of these two assertions would break.
    """
    body = _body_with_unscannable_line(2)
    band, provenance = classify_scope_pure(body)
    assert band == 'multi_module'
    assert provenance['band_rule'] == 'scan_incomplete'
    assert provenance['distinct_path_count'] < _MULTI_MODULE_MIN_PATHS, (
        'the fixture must undercount, otherwise it would fire via the path-count row '
        'and would not exercise scan_incomplete at all'
    )

    plan_dir = plan_context.plan_dir_for('cv-scale-scan-agree')
    _write_request(plan_dir, body)
    _write_status(plan_dir, metadata={'change_type': 'tech_debt'})
    _write_references(plan_dir, scope_estimate='surgical')

    result = run_classification_validation('cv-scale-scan-agree')

    assert 'scale_mismatch_light_routing' in {m['mismatch'] for m in result['mismatches']}


def test_scale_mismatch_silent_on_an_incomplete_scan_with_a_non_narrow_band(plan_context):
    """``scan_incomplete`` widens the reading; it does not bypass the narrow-claim test.

    Class 3 flags a contradicted NARROW CLAIM. With ``multi_module`` persisted there
    is no narrow claim to contradict, so the incomplete scan must stay silent —
    otherwise the widened predicate would have turned into an unconditional flag.
    """
    plan_dir = plan_context.plan_dir_for('cv-scale-scan-broad-band')
    _write_request(plan_dir, _body_with_unscannable_line(2))
    _write_status(plan_dir, metadata={'change_type': 'tech_debt'})
    _write_references(plan_dir, scope_estimate='multi_module')

    result = run_classification_validation('cv-scale-scan-broad-band')

    assert 'scale_mismatch_light_routing' not in {m['mismatch'] for m in result['mismatches']}


# -----------------------------------------------------------------------------
# Class 3 — fan_out_marker propagation (the sibling of the scan_incomplete row)
# -----------------------------------------------------------------------------


def test_scale_mismatch_fires_on_a_fan_out_marker_below_the_floor(plan_context):
    """A glob is a declared unbounded file set — the class must fire on it too.

    The regression this test pins: after the ``scan_incomplete`` row was folded in,
    the detector still re-derived only TWO of the sensor's three multi_module rows
    and never consulted ``fan_out_marker``, which ``classify_scope_pure`` evaluates
    BEFORE the path count. A body whose only wide signal is a glob therefore read
    ``multi_module`` to the sensor and narrow to the gate — the same sensor/gate
    disagreement the ``scan_incomplete`` fix closed, left open on the sibling row.
    The fixture names only 2 literal paths so the path-count row cannot carry it.
    """
    plan_dir = plan_context.plan_dir_for('cv-scale-fan-out')
    _write_request(plan_dir, _body_with_fan_out_marker(2))
    _write_status(plan_dir, metadata={'change_type': 'tech_debt'})
    _write_references(plan_dir, scope_estimate='surgical')

    result = run_classification_validation('cv-scale-fan-out')

    classes = {m['mismatch'] for m in result['mismatches']}
    assert classes == {'scale_mismatch_light_routing'}, (
        'a fan-out marker under the path-count floor must fall through to the '
        'mismatch, not short-circuit past it'
    )
    assert result['findings_emitted'] == 1
    assert result['status'] == 'success'
    assert result['blocked'] is False


@pytest.mark.parametrize(
    ('plan_id', 'body'),
    _SCALE_BAND_ROW_BODIES,
    # The plan id doubles as the case id: without it pytest would fold each body —
    # including the 2000-character unscannable fixture — into the test name.
    ids=[case_plan_id for case_plan_id, _ in _SCALE_BAND_ROW_BODIES],
)
def test_scale_mismatch_verdict_equals_the_sensor_band(plan_context, plan_id, body):
    """The gate fires IFF the sensor bands the same body ``multi_module``.

    The anti-re-derivation assertion, and the reason the production detector calls
    ``classify_scope_pure`` instead of copying rows out of it. Three separate
    loop-backs on this plan each added one missing row to a hand-copied predicate,
    and each copy drifted again on the next row. This test removes the possibility
    by construction: it never states which bodies *should* fire — it reads the
    sensor's verdict for the very text the gate reads (``_read_request_body``, so the
    two inputs are byte-identical) and requires the gate to agree. A future band row
    the gate stopped honouring breaks exactly this one test, whichever row it is.

    ``scope_estimate`` is pinned to ``surgical`` for every case so the narrow-claim
    precondition is satisfied throughout and the band is the only free variable.
    """
    plan_dir = plan_context.plan_dir_for(plan_id)
    _write_request(plan_dir, body)
    _write_status(plan_dir, metadata={'change_type': 'tech_debt'})
    _write_references(plan_dir, scope_estimate='surgical')

    sensor_band, provenance = classify_scope_pure(read_request_body(plan_id))
    result = run_classification_validation(plan_id)

    fired = 'scale_mismatch_light_routing' in {m['mismatch'] for m in result['mismatches']}
    assert fired == (sensor_band == 'multi_module'), (
        f'gate fired={fired} but the sensor banded {sensor_band!r} '
        f'(band_rule={provenance["band_rule"]!r}) for the same body — the gate must '
        f'consume the sensor band, never re-derive a subset of its rows'
    )


def test_scale_band_row_fixtures_cover_every_multi_module_row():
    """The equivalence fixtures exercise ALL of the sensor's widening rows.

    Without this, the equivalence test could pass vacuously on a fixture set that
    happened to miss the very row a future change breaks. Deriving the covered set
    from the fixtures' own ``band_rule`` provenance keeps the coverage claim
    population-derived rather than asserted from a stale list.
    """
    covered = {classify_scope_pure(body)[1]['band_rule'] for _, body in _SCALE_BAND_ROW_BODIES}

    widening = {
        'scan_incomplete',
        'fan_out_marker',
        'path_count_at_or_above_multi_module_floor',
    }
    assert widening <= covered
    # And at least one non-widening row, so the IFF has a false side to prove.
    assert covered - widening


def test_scale_mismatch_degrades_when_the_deferred_import_fails(plan_context, monkeypatch):
    """An ImportError on the deferred sensor import degrades this one check, not the gate.

    ``run_classification_validation`` is documented flag-not-block and is called with
    no surrounding try/except from ``cmd_planning_lane_route``, so an unguarded
    deferred import would let an import failure crash ``planning-lane route``
    outright. The guard must swallow it and return no finding for class 3 only —
    the other classes still report normally.
    """
    plan_dir = plan_context.plan_dir_for('cv-scale-import-fail')
    # A body that WOULD fire class 3, so a silent pass cannot be mistaken for
    # "there was nothing to find".
    _write_request(plan_dir, _body_with_paths(_MULTI_MODULE_MIN_PATHS, lead=f'{_FEATURE_BODY} '))
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='surgical')

    real_import = builtins.__import__

    def _failing_import(name, *args, **kwargs):
        if name == '_cmd_planning_lane':
            raise ImportError('simulated import cycle failure')
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', _failing_import)

    result = run_classification_validation('cv-scale-import-fail')

    assert result['status'] == 'success'
    assert result['blocked'] is False
    classes = {m['mismatch'] for m in result['mismatches']}
    assert 'scale_mismatch_light_routing' not in classes
    # The unaffected class still reports — the degradation is scoped to class 3.
    assert 'feature_as_bug_fix' in classes


def test_class_two_and_class_three_are_mutually_exclusive(plan_context):
    """Classes 2 and 3 can never co-fire, so all three classes cannot fire at once.

    Class 2 requires ``scope_estimate`` to be null / empty / ``none``; class 3
    requires it to be exactly ``surgical``. The two predicates are disjoint on the
    same field by construction. Recording this keeps ``mismatch_count`` honest — the
    gate has three classes but its ceiling is two, and a future reader must not
    infer a maximum of three from the class count.
    """
    plan_dir = plan_context.plan_dir_for('cv-mutual-exclusion')
    _write_request(plan_dir, _body_with_paths(_MULTI_MODULE_MIN_PATHS))
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    # A null scope satisfies class 2 and, by the same value, disqualifies class 3.
    _write_references(plan_dir, scope_estimate=None, affected_files=['a/b.py'])

    result = run_classification_validation('cv-mutual-exclusion')

    classes = {m['mismatch'] for m in result['mismatches']}
    assert 'non_empty_affected_files_with_null_scope' in classes
    assert 'scale_mismatch_light_routing' not in classes


def test_class_one_and_class_three_co_fire_two_findings(plan_context):
    """The reachable two-class maximum: a feature-shaped bug_fix stamp over a large body."""
    plan_dir = plan_context.plan_dir_for('cv-one-and-three')
    _write_request(
        plan_dir, _body_with_paths(_MULTI_MODULE_MIN_PATHS, lead=f'{_FEATURE_BODY} ')
    )
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='surgical')

    result = run_classification_validation('cv-one-and-three')

    classes = {m['mismatch'] for m in result['mismatches']}
    assert classes == {'feature_as_bug_fix', 'scale_mismatch_light_routing'}
    assert result['mismatch_count'] == 2
    assert result['findings_emitted'] == 2
    assert result['blocked'] is False


def test_route_is_not_blocked_by_a_scale_mismatch(plan_context):
    """A fired class-3 finding rides along on the route return without gating the lane."""
    plan_dir = plan_context.plan_dir_for('cv-scale-route')
    _write_request(plan_dir, _body_with_paths(_MULTI_MODULE_MIN_PATHS))
    _write_status(plan_dir, metadata={'change_type': 'tech_debt', 'plan_source': 'lesson'})
    _write_references(plan_dir, scope_estimate='surgical')
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_ns_route('cv-scale-route'))

    assert result['status'] == 'success'
    assert result['planning_lane'] in ('light', 'deep')
    cv = result['classification_validation']
    assert 'scale_mismatch_light_routing' in {m['mismatch'] for m in cv['mismatches']}


# =============================================================================
# Both mismatches together
# =============================================================================


def test_both_mismatches_fire_two_findings(plan_context):
    """A plan tripping both classes records two distinct findings without blocking."""
    # bug_fix over a feature narrative AND affected_files without scope.
    plan_dir = plan_context.plan_dir_for('cv-both')
    _write_request(plan_dir, _FEATURE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate=None, affected_files=['a/b.py'])

    result = run_classification_validation('cv-both')

    classes = {m['mismatch'] for m in result['mismatches']}
    assert classes == {'feature_as_bug_fix', 'non_empty_affected_files_with_null_scope'}
    assert result['mismatch_count'] == 2
    assert result['findings_emitted'] == 2
    assert result['blocked'] is False
