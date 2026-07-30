#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the deterministic classification-validation gate.

The gate cross-checks a plan's ``change_type`` and ``scope_estimate`` against
cheap request signals and emits a phase-1-init Q-Gate finding (recorded against
``2-refine``) on a mismatch. It is **flag-not-block** — it never gates routing.

Three mismatch classes, each chosen to raise zero false positives:

1. ``feature_as_bug_fix`` — ``change_type == bug_fix`` while the deterministic
   change-type heuristic resolves a non-ambiguous ``feature`` winner.
2. ``non_empty_affected_files_with_null_scope`` — ``affected_files`` non-empty
   while ``scope_estimate`` is null / empty / ``none``.
3. ``scale_mismatch_light_routing`` — ``scope_estimate`` persisted as ``surgical``
   while the request body reads as ``multi_module`` to the scope sensor: either it
   names at least ``_MULTI_MODULE_MIN_PATHS`` distinct paths, or the ReDoS-bounded
   path scan could not cover the whole body (``scan_incomplete``). The safety net
   for the residual the pre-route sensor cannot close alone: the sensor is not the
   only writer of ``scope_estimate``, so a narrow band can outlive a body that is
   plainly not narrow.

Coverage:
- No-signal / valid input yields no finding (no false positives).
- Each mismatch class fires its finding in isolation.
- Two co-firing mismatches produce two findings.
- Classes 2 and 3 are mutually exclusive by construction (null scope vs
  ``surgical`` scope), so the three classes cannot all fire at once — asserted
  rather than left as an unexamined assumption about ``mismatch_count``.
- Class 3's threshold is IMPORTED from the sensor, not restated: the 7/8 boundary
  is driven off ``_cmd_planning_lane._MULTI_MODULE_MIN_PATHS`` itself.
- Class 3's ``scan_incomplete`` propagation: a body the bounded scan cannot cover
  in full fires the class even when the (undercounted) path total is BELOW the
  floor, and the gate's verdict is asserted against the sensor's own band for the
  same body so the two cannot drift apart.
- Class 3's deferred ``_cmd_planning_lane`` import degrades to "no finding" on
  ``ImportError`` rather than propagating out of a flag-not-block gate.
- The gate never blocks (``blocked`` is always ``False``; ``status`` success).
- Re-running the gate dedups (no duplicate findings).
- The gate is folded into ``planning-lane route`` as a pre-route pass and never
  changes the resolved lane.
"""

from __future__ import annotations

import builtins
import json
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

_gate = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_classification_validate.py', '_cmd_classification_validate_under_test'
)
run_classification_validation = _gate.run_classification_validation
cmd_classification_validate = _gate.cmd_classification_validate

_lane = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_planning_lane.py', '_cmd_planning_lane_for_classification_test'
)
cmd_planning_lane_route = _lane.cmd_planning_lane_route
classify_scope_pure = _lane.classify_scope_pure


# =============================================================================
# Fixture authoring helpers
# =============================================================================

# A request body that clearly reads as a feature ("add / create / implement a
# new X"), so the change-type heuristic resolves a non-ambiguous feature winner.
_FEATURE_BODY = 'Add a new export command that creates and implements a fresh report generator.'

# A request body that clearly reads as a bug fix, so the heuristic does NOT
# resolve feature (no feature-as-bug_fix false positive).
_BUGFIX_BODY = 'The parser crashes on empty input — this is a regression; fix the broken exception path.'


def _write_request(plan_dir: Path, body: str) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    content = (
        '# Request\n\n'
        '## Original Input\n\n'
        '(unused)\n\n'
        '## Clarified Request\n\n'
        f'{body}\n'
    )
    (plan_dir / 'request.md').write_text(content, encoding='utf-8')


def _write_status(plan_dir: Path, metadata: dict | None = None) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_dir.name, 'phases': [], 'metadata': metadata or {}}),
        encoding='utf-8',
    )


def _write_references(
    plan_dir: Path,
    *,
    scope_estimate: str | None,
    affected_files: list[str] | None = None,
) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    refs: dict = {'base_branch': 'main'}
    if scope_estimate is not None:
        refs['scope_estimate'] = scope_estimate
    if affected_files is not None:
        refs['affected_files'] = affected_files
    (plan_dir / 'references.json').write_text(json.dumps(refs), encoding='utf-8')


def _write_marshal(fixture_dir: Path) -> None:
    config = {
        'plan': {
            'phase-1-init': {'deep_lane': 'auto'},
            'phase-2-refine': {'compatibility': 'deprecation'},
        },
    }
    (fixture_dir / 'marshal.json').write_text(json.dumps(config, indent=2), encoding='utf-8')


# The multi_module floor, read from the SENSOR rather than restated here. The
# production detector imports the same constant, so these boundary cases move with
# it automatically — a threshold hard-coded in the test would let the gate and the
# sensor drift apart while every test still passed.
_MULTI_MODULE_MIN_PATHS = _lane._MULTI_MODULE_MIN_PATHS

# The ReDoS-defense per-line cap, likewise read from the SENSOR. A line longer
# than this is SKIPPED by ``_safe_path_scan`` and sets ``scan_incomplete`` — the
# cheapest way to construct a body whose path total is a lower bound rather than
# a count, without needing a 50KB fixture to exhaust the budget instead.
_MAX_SCAN_LINE_CHARS = _lane._MAX_SCAN_LINE_CHARS


def _body_with_paths(count: int, *, lead: str = '') -> str:
    """Return a request body naming exactly ``count`` distinct repo-relative paths."""
    paths = ', '.join(f'pkg/mod{i}/file{i}.py' for i in range(count))
    return f'{lead}Touch {paths}.'


def _body_with_unscannable_line(path_count: int) -> str:
    """Return a body the bounded scan cannot cover in full, naming few paths.

    One over-long, path-free line forces ``_safe_path_scan`` to skip it and report
    ``scan_incomplete=True``, while the remaining scannable text names only
    ``path_count`` paths — deliberately BELOW ``_MULTI_MODULE_MIN_PATHS``. That is
    exactly the shape a count-only detector reads as "narrow, nothing to flag".
    """
    unscannable = 'x' * (_MAX_SCAN_LINE_CHARS + 1)
    return f'{_body_with_paths(path_count)}\n\n{unscannable}\n'


def _ns(plan_id: str) -> Namespace:
    return Namespace(plan_id=plan_id)


def _ns_route(plan_id: str):
    return Namespace(plan_id=plan_id, lane_override=None, persist=False)


# =============================================================================
# No false positives — valid input
# =============================================================================


def test_no_mismatch_on_valid_bug_fix(plan_context):
    """A bug_fix stamp over a bug-shaped request with a scope estimate yields no finding."""
    # bug_fix, bug-shaped narrative, scope set, no affected_files gap.
    plan_dir = plan_context.plan_dir_for('cv-valid-bugfix')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='surgical')

    result = run_classification_validation('cv-valid-bugfix')

    assert result['status'] == 'success'
    assert result['mismatch_count'] == 0
    assert result['findings_emitted'] == 0
    assert result['blocked'] is False


def test_no_mismatch_when_scope_set_with_affected_files(plan_context):
    """A non-empty affected_files WITH a scope estimate does not trip mismatch class 2."""
    plan_dir = plan_context.plan_dir_for('cv-valid-scope')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='single_module', affected_files=['a/b.py'])

    result = run_classification_validation('cv-valid-scope')

    assert result['mismatch_count'] == 0
    assert result['findings_emitted'] == 0


def test_no_mismatch_when_no_metadata(plan_context):
    """A plan with no change_type and no affected_files produces no finding."""
    # Minimal plan, nothing to cross-check.
    plan_dir = plan_context.plan_dir_for('cv-empty')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={})
    _write_references(plan_dir, scope_estimate=None)

    result = run_classification_validation('cv-empty')

    assert result['mismatch_count'] == 0
    assert result['blocked'] is False


# =============================================================================
# Mismatch class 1 — feature-as-bug_fix
# =============================================================================


def test_feature_as_bug_fix_fires(plan_context):
    """change_type=bug_fix over a feature-shaped narrative flags one finding."""
    plan_dir = plan_context.plan_dir_for('cv-feat-bug')
    _write_request(plan_dir, _FEATURE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='surgical')

    result = run_classification_validation('cv-feat-bug')

    assert result['mismatch_count'] == 1
    assert result['mismatches'][0]['mismatch'] == 'feature_as_bug_fix'
    assert result['findings_emitted'] == 1
    assert result['blocked'] is False


def test_feature_as_bug_fix_does_not_fire_for_feature_change_type(plan_context):
    """A feature-shaped narrative correctly stamped change_type=feature is not flagged."""
    plan_dir = plan_context.plan_dir_for('cv-feat-ok')
    _write_request(plan_dir, _FEATURE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'feature'})
    _write_references(plan_dir, scope_estimate='multi_module')

    result = run_classification_validation('cv-feat-ok')

    # No feature-as-bug_fix flag (change_type already matches).
    classes = {m['mismatch'] for m in result['mismatches']}
    assert 'feature_as_bug_fix' not in classes


# =============================================================================
# Mismatch class 2 — affected_files without scope_estimate
# =============================================================================


def test_affected_files_without_scope_fires(plan_context):
    """Non-empty affected_files with a null scope_estimate flags one finding."""
    # affected_files set, scope_estimate absent.
    plan_dir = plan_context.plan_dir_for('cv-files-noscope')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate=None, affected_files=['x/y.py', 'x/z.py'])

    result = run_classification_validation('cv-files-noscope')

    classes = {m['mismatch'] for m in result['mismatches']}
    assert classes == {'non_empty_affected_files_with_null_scope'}
    assert result['findings_emitted'] == 1
    assert result['blocked'] is False


def test_affected_files_with_none_scope_string_fires(plan_context):
    """The literal scope_estimate 'none' counts as null for mismatch class 2."""
    plan_dir = plan_context.plan_dir_for('cv-files-nonescope')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='none', affected_files=['x/y.py'])

    result = run_classification_validation('cv-files-nonescope')

    classes = {m['mismatch'] for m in result['mismatches']}
    assert 'non_empty_affected_files_with_null_scope' in classes


# =============================================================================
# Mismatch class 3 — a narrow persisted band over a multi-module-sized body
# =============================================================================


def test_scale_mismatch_light_routing_fires(plan_context):
    """A persisted surgical band over a body naming >= 8 distinct paths flags one finding.

    The residual the sensor cannot close on its own: the pre-route classifier would
    band this body ``multi_module``, so a persisted ``surgical`` can only have come
    from a different writer (refine's module-mapping derivation or outline's
    refinement) or from a body that grew after init. ``change_type`` is deliberately
    NOT ``bug_fix`` so mismatch class 1 cannot fire and the assertion isolates
    class 3.
    """
    plan_dir = plan_context.plan_dir_for('cv-scale-mismatch')
    _write_request(plan_dir, _body_with_paths(_MULTI_MODULE_MIN_PATHS))
    _write_status(plan_dir, metadata={'change_type': 'tech_debt'})
    _write_references(plan_dir, scope_estimate='surgical')

    result = run_classification_validation('cv-scale-mismatch')

    classes = {m['mismatch'] for m in result['mismatches']}
    assert classes == {'scale_mismatch_light_routing'}
    assert result['mismatch_count'] == 1
    assert result['findings_emitted'] == 1
    # Flag-not-block holds for the new class exactly as for the other two.
    assert result['status'] == 'success'
    assert result['blocked'] is False


def test_scale_mismatch_silent_when_band_and_count_agree(plan_context):
    """A surgical band over a genuinely small body is agreement, not a mismatch."""
    plan_dir = plan_context.plan_dir_for('cv-scale-agree')
    _write_request(plan_dir, _body_with_paths(2))
    _write_status(plan_dir, metadata={'change_type': 'tech_debt'})
    _write_references(plan_dir, scope_estimate='surgical')

    result = run_classification_validation('cv-scale-agree')

    assert result['mismatch_count'] == 0
    assert result['blocked'] is False


def test_scale_mismatch_silent_for_a_non_narrow_persisted_band(plan_context):
    """A large body with a large persisted band is agreement too — nothing to flag.

    The check is about a NARROW CLAIM being contradicted, not about size. Only
    ``surgical`` is a narrow claim; ``single_module`` is the catch-all middle band,
    so pairing it with a high count is not a contradiction.
    """
    plan_dir = plan_context.plan_dir_for('cv-scale-broad-band')
    _write_request(plan_dir, _body_with_paths(_MULTI_MODULE_MIN_PATHS + 4))
    _write_status(plan_dir, metadata={'change_type': 'tech_debt'})
    _write_references(plan_dir, scope_estimate='multi_module')

    result = run_classification_validation('cv-scale-broad-band')

    classes = {m['mismatch'] for m in result['mismatches']}
    assert 'scale_mismatch_light_routing' not in classes


def test_scale_mismatch_silent_for_an_unscoreable_body(plan_context):
    """An unscoreable body contradicts nothing, so class 3 stays silent.

    The gate must not manufacture a disagreement out of zero bytes — the same
    declared-unknown discipline the sensor itself follows.
    """
    plan_dir = plan_context.plan_dir_for('cv-scale-no-body')
    plan_dir.mkdir(parents=True, exist_ok=True)
    _write_status(plan_dir, metadata={'change_type': 'tech_debt'})
    _write_references(plan_dir, scope_estimate='surgical')
    # No request.md is written at all.

    result = run_classification_validation('cv-scale-no-body')

    assert result['mismatch_count'] == 0


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


# =============================================================================
# Dedup on re-run
# =============================================================================


def test_rerun_dedups_findings(plan_context):
    """Re-running the gate does not record duplicate findings (title dedup)."""
    plan_dir = plan_context.plan_dir_for('cv-dedup')
    _write_request(plan_dir, _FEATURE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='surgical')

    # Run twice.
    first = run_classification_validation('cv-dedup')
    second = run_classification_validation('cv-dedup')

    # First records the finding; the second dedups (0 new emitted).
    assert first['findings_emitted'] == 1
    assert second['mismatch_count'] == 1
    assert second['findings_emitted'] == 0
    assert second['mismatches'][0]['finding_status'] == 'deduplicated'


# =============================================================================
# Subcommand wrapper + missing-plan handling
# =============================================================================


def test_cmd_returns_error_for_missing_plan(plan_context):
    """The subcommand returns a structured error when the plan dir is absent."""
    # No plan dir created.
    result = cmd_classification_validate(_ns('cv-nonexistent'))

    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


# =============================================================================
# Folded into planning-lane route — pre-route pass, never blocks the lane
# =============================================================================


def test_route_surfaces_classification_without_blocking(plan_context):
    """planning-lane route runs the gate as a pre-route pass and still resolves a lane."""
    # A plan that trips a mismatch (affected_files without scope).
    plan_dir = plan_context.plan_dir_for('cv-route')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate=None, affected_files=['a/b.py'])
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_ns_route('cv-route'))

    # Routing succeeded and resolved a lane; the gate result rides along.
    assert result['status'] == 'success'
    assert result['planning_lane'] in ('light', 'deep')
    cv = result['classification_validation']
    assert cv['mismatch_count'] >= 1
    assert 'non_empty_affected_files_with_null_scope' in {m['mismatch'] for m in cv['mismatches']}
