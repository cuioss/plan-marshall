#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``track-selection-accuracy`` light-lane carve-out — the carve-out suffix is
era-relative, a plain over-track verdict carries no suffix, and a plan with
no routing record carries an empty era.
"""

import json
from pathlib import Path

from _audit_fixtures import audit

from conftest import PROJECT_ROOT


def _routing_or_skip():
    routing = audit._load_routing_logic(PROJECT_ROOT)
    assert routing is not None, 'planning-lane router unavailable'
    return routing


def _track_inputs(repo_root: Path, scope: str, change_type: str, lane: str) -> audit.PlanInputs:
    plan_dir = repo_root / ".plan" / "local" / "archived-plans" / "track-plan"
    plan_dir.mkdir(parents=True, exist_ok=True)

    (plan_dir / "references.json").write_text(
        json.dumps({"scope_estimate": scope, "track": _lane_track(lane)}), encoding="utf-8"
    )
    (plan_dir / "status.json").write_text(
        json.dumps({"metadata": {"change_type": change_type, "planning_lane": lane}}),
        encoding="utf-8",
    )
    # A concrete request (carries a file-path anchor → request_concrete=True).
    (plan_dir / "request.md").write_text(
        "Fix the bug in marketplace/bundles/foo/bar.py so the flag resets.", encoding="utf-8"
    )
    return audit.collect_inputs(plan_dir)


def _lane_track(lane: str) -> str:
    return "complex" if lane == "deep" else "simple"


def test_track_selection_carveout_over_track_is_era_relative(tmp_path):
    # Arrange: a narrow + concrete + generative (feature) plan that ran DEEP. Under
    # the post-#854 carve-out the counterfactual is LIGHT, so it is OVER-TRACKED —
    # but the over-tracking is attributable to the carve-out (era-relative).
    routing = _routing_or_skip()
    inputs = _track_inputs(tmp_path, "surgical", "feature", "deep")

    # Act: compatibility="breaking" would also force deep pre-carve-out.
    row = audit.check_track_selection_accuracy(inputs, routing, "breaking")

    # Assert: OVER-TRACKED, and the era carries the :carve_out attribution.
    assert row["verdict"] == "OVER-TRACKED", row
    assert row["era"] == f"{audit.CHECK_ERA['track-selection-accuracy']}:carve_out", row


def test_track_selection_plain_over_track_no_carveout_suffix(tmp_path):
    # Arrange: a narrow + concrete but NON-generative (bug_fix) plan that ran DEEP.
    # The counterfactual is light (no deep signal fires), so it is OVER-TRACKED,
    # but NOT attributable to the carve-out (bug_fix would not have forced deep).
    routing = _routing_or_skip()
    inputs = _track_inputs(tmp_path, "surgical", "bug_fix", "deep")

    # Act
    row = audit.check_track_selection_accuracy(inputs, routing, "deprecation")

    # Assert: plain era stamp, no :carve_out suffix.
    assert row["verdict"] == "OVER-TRACKED", row
    assert row["era"] == audit.CHECK_ERA["track-selection-accuracy"], row


def test_track_selection_no_routing_carries_empty_era(tmp_path):
    # A degrade path (routing=None) carries an empty era, not a missing key — the
    # `era` column must be present on every row so the emit_table_block never
    # KeyErrors.
    inputs = _track_inputs(tmp_path, "surgical", "feature", "deep")
    row = audit.check_track_selection_accuracy(inputs, None, None)
    assert row["verdict"] == "no_routing_logic"
    assert row["era"] == ""
