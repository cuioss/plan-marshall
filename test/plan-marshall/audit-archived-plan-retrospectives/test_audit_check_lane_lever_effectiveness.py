#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``lane-lever-effectiveness`` — a surgical scope over its target is a genuine
signal, an engaged lever within target records the spend avoided, rows sort
by plan id, and a plan with no metrics or an unclassed scope is handled.
"""

import json
from pathlib import Path

from _audit_fixtures import audit


def _plan_lane(
    repo_root: Path,
    name: str,
    scope: str,
    *,
    total_tokens: int | None = None,
    planning_lane: str = "deep",
    execution_profile: str | None = None,
    plan_source: str | None = None,
    change_type: str = "feature",
) -> audit.PlanInputs:
    """Materialise a plan carrying the lane-lever-effectiveness inputs.

    ``cross_lane_lever_effectiveness`` reads ``scope_estimate`` (references.json),
    the summed ``total_tokens`` (work/metrics.toon), and the ``planning_lane`` /
    ``execution_profile`` / ``plan_source`` metadata (status.json).
    """
    pd = repo_root / ".plan" / "local" / "archived-plans" / name
    (pd / "work").mkdir(parents=True, exist_ok=True)
    (pd / "references.json").write_text(
        json.dumps({"scope_estimate": scope}), encoding="utf-8"
    )
    md: dict = {"change_type": change_type, "planning_lane": planning_lane}
    if execution_profile is not None:
        md["execution_profile"] = execution_profile
    if plan_source is not None:
        md["plan_source"] = plan_source
    (pd / "status.json").write_text(json.dumps({"metadata": md}), encoding="utf-8")
    if total_tokens is not None:
        (pd / "work" / "metrics.toon").write_text(
            f"[5-execute]\ntotal_tokens: {total_tokens}\n", encoding="utf-8"
        )
    return audit.collect_inputs(pd)


def test_lane_lever_surgical_over_target_is_genuine(tmp_path):
    # A surgical plan spending 1.5M > the 1.2M armed target is `over` — the
    # genuine overspend signal — and, being surgical without a minimal posture,
    # also records posture_not_taken.
    i = _plan_lane(tmp_path, "surg-over", "surgical", total_tokens=1_500_000)
    result = audit.cross_lane_lever_effectiveness([i])
    row = result["rows"][0]
    assert row["checkpoint_class"] == "surgical"
    assert row["target"] == 1_200_000
    assert row["verdict"] == "over"
    assert row["flags"] == "checkpoint_over"
    assert row["posture_not_taken"] == "true"
    assert audit._lane_lever_genuine(row) is True
    assert result["corpus"]["checkpoint_over_count"] == 1
    assert result["corpus"]["by_class"]["surgical"]["over"] == 1


def test_lane_lever_within_target_with_lever_records_avoided(tmp_path):
    # A single_module plan under its 1.5M target with the minimal posture engaged
    # is `within`, informational, and credits the headroom as avoided_tokens.
    i = _plan_lane(
        tmp_path, "sm-within", "single_module",
        total_tokens=1_000_000, execution_profile="minimal",
    )
    result = audit.cross_lane_lever_effectiveness([i])
    row = result["rows"][0]
    assert row["verdict"] == "within"
    assert row["lever_engaged"] == "true"
    assert row["avoided_tokens"] == 500_000
    assert row["flags"] == ""
    assert audit._lane_lever_genuine(row) is False
    assert result["corpus"]["estimated_avoided_tokens"] == 500_000
    assert result["corpus"]["minimal_posture_chosen"] == 1


def test_lane_lever_recipe_and_light_lever_counts(tmp_path):
    # recipe auto-route (plan_source) and light-lane fire (planning_lane) are the
    # engagement levers surfaced in the corpus counts.
    i = _plan_lane(
        tmp_path, "recipe", "multi_module",
        total_tokens=2_000_000, planning_lane="light",
        plan_source="2026-07-09-04-001",
    )
    result = audit.cross_lane_lever_effectiveness([i])
    row = result["rows"][0]
    assert row["recipe_routed"] == "true"
    assert row["lane"] == "light"
    assert row["lever_engaged"] == "true"
    assert result["corpus"]["recipe_routed_count"] == 1
    assert result["corpus"]["light_lane_fires"] == 1


def test_lane_lever_no_metrics_and_unclassed_scope(tmp_path):
    # A plan with no recorded tokens is `no_metrics`; a scope outside the armed
    # set is `unclassed` — neither is a genuine overspend.
    i1 = _plan_lane(tmp_path, "nom", "surgical", total_tokens=None)
    i2 = _plan_lane(tmp_path, "broad", "broad", total_tokens=900_000)
    result = audit.cross_lane_lever_effectiveness([i1, i2])
    by = {r["plan_id"]: r for r in result["rows"]}
    assert by["nom"]["verdict"] == "no_metrics"
    assert by["broad"]["verdict"] == "unclassed"
    assert by["broad"]["checkpoint_class"] == "unclassed"
    assert result["corpus"]["plans_measured"] == 1


def test_lane_lever_rows_sorted_by_plan_id(tmp_path):
    # Deterministic row ordering (sorted by plan_id) so the persisted report diff
    # is stable run-to-run.
    _plan_lane(tmp_path, "zeta", "single_module", total_tokens=100)
    _plan_lane(tmp_path, "alpha", "single_module", total_tokens=100)
    inputs = [
        audit.collect_inputs(tmp_path / ".plan" / "local" / "archived-plans" / n)
        for n in ("zeta", "alpha")
    ]
    result = audit.cross_lane_lever_effectiveness(inputs)
    assert [r["plan_id"] for r in result["rows"]] == ["alpha", "zeta"]


def test_emit_lane_lever_block_renders_header_and_severity(tmp_path):
    # The emitted block carries the corpus header scalars, the per-class over
    # tallies, the genuine_signal_count, and the rows[] column set ending in severity.
    i = _plan_lane(tmp_path, "surg-over", "surgical", total_tokens=1_500_000)
    result = audit.cross_lane_lever_effectiveness([i])

    block = audit.emit_lane_lever_effectiveness_block(result)

    assert "check: lane-lever-effectiveness" in block
    assert "status: success" in block
    assert "checkpoint_over: 1" in block
    assert "surgical_over: 1/1 (target 1200000)" in block
    assert "genuine_signal_count: 1" in block
    assert (
        "rows[1]{plan_id,scope,checkpoint_class,target,total_tokens,verdict,"
        "recipe_routed,lane,posture,posture_not_taken,lever_engaged,"
        "avoided_tokens,flags,severity}:" in block
    )
    genuine_row = next(
        ln.strip() for ln in block.splitlines() if ln.strip().startswith("surg-over,")
    )
    assert genuine_row.endswith(",genuine")
