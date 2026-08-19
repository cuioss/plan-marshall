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
   while the request body reads as ``multi_module`` to the scope sensor. The gate
   CALLS ``classify_scope_pure`` and consumes its band rather than re-deriving any
   of its rows, so every widening row (``scan_incomplete``, ``fan_out_marker``, the
   ``_MULTI_MODULE_MIN_PATHS`` path-count floor) is honoured by construction. The
   safety net for the residual the pre-route sensor cannot close alone: the sensor
   is not the only writer of ``scope_estimate``, so a narrow band can outlive a body
   that is plainly not narrow.

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
- Class 3's ``fan_out_marker`` propagation: a body whose only wide signal is a glob
  fires the class even with few explicit paths.
- Class 3 gate-vs-sensor EQUIVALENCE over one body per band row: the gate fires iff
  the sensor bands the same body ``multi_module``. This is the anti-re-derivation
  assertion — any future band row the gate stopped honouring breaks exactly this
  one test, whichever row it is.
- Class 3's deferred ``_cmd_planning_lane`` import degrades to "no finding" on
  ``ImportError`` rather than propagating out of a flag-not-block gate.
- The gate never blocks (``blocked`` is always ``False``; ``status`` success).
- Re-running the gate dedups (no duplicate findings).
- The gate is folded into ``planning-lane route`` as a pre-route pass and never
  changes the resolved lane.
"""


from __future__ import annotations

from _classification_validation_gate_fixtures import (
    _BUGFIX_BODY,
    _FEATURE_BODY,
    _MULTI_MODULE_MIN_PATHS,
    _body_with_paths,
    _write_references,
    _write_request,
    _write_status,
    run_classification_validation,
)

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
