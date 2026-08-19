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
    _ns,
    _ns_route,
    _write_marshal,
    _write_references,
    _write_request,
    _write_status,
    cmd_classification_validate,
    cmd_planning_lane_route,
    run_classification_validation,
)

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
