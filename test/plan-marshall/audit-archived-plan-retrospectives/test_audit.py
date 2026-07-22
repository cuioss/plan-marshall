#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Regression tests for the audit skill's global-log allowlist and era model.

Two concern clusters:

* the ``global-log-analysis`` benign-probe allowlist — a marker-free ``resolve``
  call stamped at an elevated level is a benign non-zero-exit probe and MUST be
  excluded from ``error_lines``, while the SAME line carrying a failure marker
  MUST still be flagged; and
* the check era model (deliverable 1) — every emitted check block carries its
  ``fixed_since`` stamp sourced from the single ``CHECK_ERA`` table, and the
  retire-on-quiet mechanism proposes (never removes) a check quiet for at least
  ``THRESHOLDS["retire_on_quiet_runs"]`` consecutive recorded runs.

Drives ``audit`` directly by inserting the project-local audit skill's
``scripts/`` dir on sys.path (the script is not a marketplace-bundle script, so
``conftest.get_script_path`` does not resolve it).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from conftest import PROJECT_ROOT

_AUDIT_SCRIPTS_DIR = (
    PROJECT_ROOT / ".claude" / "skills" / "audit-archived-plan-retrospectives" / "scripts"
)
if str(_AUDIT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AUDIT_SCRIPTS_DIR))

import audit  # type: ignore[import-untyped]  # noqa: E402

# A completed read-only ``resolve`` probe stamped at ERROR with a trailing
# duration and NO failure marker — the benign non-zero-exit "not found" answer.
_BENIGN_RESOLVE_LINE = (
    "[2026-06-29T09:00:01Z] [ERROR] [3befe7] "
    "plan-marshall:manage-personas:manage-personas resolve --persona reviewer (0.15s)"
)
# The same call line carrying a ``status: error`` failure marker — a genuine
# failure that must be flagged regardless of the benign-probe allowlist.
_RESOLVE_LINE_WITH_MARKER = (
    "[2026-06-29T09:00:01Z] [ERROR] [3befe7] "
    "plan-marshall:manage-personas:manage-personas resolve --persona reviewer "
    "status: error (0.15s)"
)


def _write_log(repo_root: Path, line: str) -> None:
    """Stage a single-line ``script-execution`` log under repo_root's global logs."""
    logs_dir = repo_root / ".plan" / "local" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "script-execution-2026-06-29.log").write_text(line + "\n", encoding="utf-8")


def test_resolve_probe_excluded_from_error_lines(tmp_path):
    # Arrange: a marker-free `resolve` call stamped at ERROR.
    _write_log(tmp_path, _BENIGN_RESOLVE_LINE)

    # Act
    result = audit.cross_global_log_analysis(tmp_path)

    # Assert: the benign `resolve` probe is NOT counted as an error line.
    details = [entry["detail"] for entry in result["error_lines"]]
    assert result["error_lines"] == [], (
        f"benign resolve probe should be excluded from error_lines, got {details}"
    )


def test_resolve_with_failure_marker_included_in_error_lines(tmp_path):
    # Arrange: the same `resolve` call carrying a `status: error` failure marker.
    _write_log(tmp_path, _RESOLVE_LINE_WITH_MARKER)

    # Act
    result = audit.cross_global_log_analysis(tmp_path)

    # Assert: a failure-marker line is flagged even though `resolve` is allowlisted.
    assert len(result["error_lines"]) == 1, (
        f"resolve line with failure marker must be flagged, got {result['error_lines']}"
    )
    assert "resolve" in result["error_lines"][0]["detail"]


# ---------------------------------------------------------------------------
# Era model: CHECK_ERA / fixed_since stamping
# ---------------------------------------------------------------------------


def _minimal_corpus(repo_root: Path) -> list:
    """Build a one-plan archived corpus and return its collected inputs."""
    plan_dir = repo_root / ".plan" / "local" / "archived-plans" / "sample-plan"
    plan_dir.mkdir(parents=True)
    (plan_dir / "references.json").write_text('{"scope_estimate": "surgical"}', encoding="utf-8")
    (plan_dir / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    return [audit.collect_inputs(plan_dir)]


def test_check_era_covers_exactly_all_checks():
    # The single CHECK_ERA table must stamp every registered check — no more, no
    # less — so no check inline-duplicates or misses a boundary stamp.
    assert set(audit.CHECK_ERA) == set(audit.CHECK_NAMES)


def test_reworked_checks_carry_this_plan_boundary():
    # Plan-13 reworks two checks' mechanics — the classify-before-route lane
    # signals and the Tier-1 recipe floor that re-arms the checkpoint measurement
    # — so their era boundary is plan-13's PR (#875), kept in lock-step with the
    # audit.py mirror. The `metrics` check has since moved OFF #875 to this plan's
    # own PR-PENDING boundary (see test_metrics_check_carries_this_plan_pr_boundary).
    for check in ("track-selection-accuracy", "lane-lever-effectiveness"):
        assert audit.CHECK_ERA[check] == "#875", check


def test_metrics_check_carries_this_plan_pr_boundary():
    # This plan makes per-step token attribution sound — D1 dispatch-boundary
    # reconciliation, D2 inline 6-finalize main-context attribution, and D3 the
    # loop-back boundary-monotonicity idle guard — exactly the per-phase
    # token/duration recording mechanics the `metrics` check verifies. So its era
    # boundary is this plan's own PR, carried as the PR-PENDING placeholder
    # (bumped from #875) until project:finalize-step-era-stamp-fill resolves it to
    # the real PR at finalize. This is the co-changing mirror of the audit.py
    # CHECK_ERA constant — the pair changes together and is the designated
    # acceptance for era-fill firing from a composed manifest.
    assert audit.CHECK_ERA["metrics"] == "#922"


def test_merge_window_accounting_carries_this_plan_pr_boundary():
    # Plan-14 reworked the merge-window-accounting mechanics — D1 strips
    # --delete-branch/--strategy from the pr merge-queue enqueue path and D3 fixes the
    # merge-lock stale-holder liveness — both surfaces this check accounts for, so its
    # era boundary is plan-14's PR (#877, bumped from #863).
    assert audit.CHECK_ERA["merge-window-accounting"] == "#877"


def test_finalize_flow_conformance_carries_this_plan_pr_boundary():
    # Plan-17 reworked the finalize-flow-conformance mechanics — D1's pre-merge
    # comment barrier and D2's completion-aware polling rework the finalize
    # merge-completeness surface this check accounts for, so its era boundary is
    # plan-17's PR (#884, bumped from #849).
    assert audit.CHECK_ERA["finalize-flow-conformance"] == "#884"


def test_sequence_build_minimality_carries_plan7_boundary():
    # sequence-and-build-minimality's era boundary is plan-7's PR (#887): plan-7's
    # D1 which-module containment fix and the per-task-vs-per-deliverable build-cost
    # model change are the mechanics this check's rows are read against. plan-8 does
    # NOT rework it, so its stamp stays resolved at #887.
    assert audit.CHECK_ERA["sequence-and-build-minimality"] == "#887"


def test_plan8_reworked_checks_carry_pr_pending_boundary():
    # Plan-8 reworks two checks' mechanics, so their era boundary is plan-8's own PR,
    # carried as the PR-PENDING placeholder until project:finalize-step-era-stamp-fill
    # resolves it to the real PR at finalize (in lock-step with the audit.py mirror —
    # the pair changes together and is the designated acceptance for era-fill firing
    # from a composed manifest):
    #   * token-economics — plan-8's finalize-wait consolidation changes the
    #     finalize_heavy token-economics accounting this check flags (bumped from #887).
    #   * token-efficiency-trend — plan-8's per-dispatch context trim lowers the
    #     tokens-per-phase floor this cross-plan trend check reads (bumped from plan-10).
    for check in ("token-economics", "token-efficiency-trend"):
        assert audit.CHECK_ERA[check] == "#899", check


def test_dispatch_topology_carries_this_plan_pr_boundary():
    # This plan reworks the dispatch-topology check's boundary: D6's compose-time
    # execution_tier structural guard changes how the leaf/dispatch-topology
    # invariant (a leaf cannot reap a backgrounded build) is ENFORCED — from a
    # prose-only rule into a manifest fact — so its era boundary is this plan's own
    # PR, carried as the PR-PENDING placeholder (bumped from plan-10) until
    # project:finalize-step-era-stamp-fill resolves it to the real PR at finalize.
    # This is the co-changing mirror of the audit.py CHECK_ERA constant — the pair
    # changes together and is the designated acceptance for era-fill firing from a
    # composed manifest.
    assert audit.CHECK_ERA["dispatch-topology"] == "#893"


def test_stamp_era_inserts_fixed_since_after_status():
    # Arrange: a synthetic check block for a known check.
    block = "check: metrics\nstatus: success\ngenuine_signal_count: 0\nrows[0]{a}:\n"

    # Act
    stamped = audit._stamp_era(block)

    # Assert: fixed_since rides immediately after the status line, sourced from CHECK_ERA.
    lines = stamped.split("\n")
    assert lines[0] == "check: metrics"
    assert lines[1] == "status: success"
    assert lines[2] == f"fixed_since: {audit.CHECK_ERA['metrics']}"


def test_stamp_era_leaves_meta_blocks_untouched():
    # Meta blocks (report-diff / retire-on-quiet) carry no CHECK_ERA entry and
    # must pass through unchanged.
    meta = "check: report-diff\nstatus: success\nrows[0]{a}:\n"
    assert audit._stamp_era(meta) == meta


def test_execution_context_manifest_era_stamped_to_promotion_boundary():
    # The self-review promotion (default:pre-submission-self-review) bumped the
    # finalize-step-id surface this check re-derives, so its era stamp moves to #872.
    assert audit.CHECK_ERA["execution-context-manifest"] == "#872"
    block = "check: execution-context-manifest\nstatus: success\nrows[0]{a}:\n"
    stamped = audit._stamp_era(block)
    lines = stamped.split("\n")
    assert lines[0] == "check: execution-context-manifest"
    assert lines[1] == "status: success"
    assert lines[2] == "fixed_since: #872"


def test_full_run_stamps_every_check_block(tmp_path):
    # Arrange
    inputs = _minimal_corpus(tmp_path)

    # Act
    output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

    # Assert: every check block carries its fixed_since stamp right after status.
    for check in audit.CHECK_NAMES:
        expected = f"check: {check}\nstatus: success\nfixed_since: {audit.CHECK_ERA[check]}"
        assert expected in output, f"{check} missing its fixed_since stamp"


# ---------------------------------------------------------------------------
# Era model: retire-on-quiet proposals
# ---------------------------------------------------------------------------


def _stage_prior_report(repo_root: Path, stem: str, genuine: dict[str, int]) -> None:
    """Write a prior persisted report carrying `genuine__{check}` summary keys."""
    reports_dir = repo_root / audit.AUDIT_REPORTS_REL
    reports_dir.mkdir(parents=True, exist_ok=True)
    lines = ["report: audit", "summary_metrics:"]
    for check, count in genuine.items():
        lines.append(f"  genuine__{check}: {count}")
    (reports_dir / f"{stem}.toon").write_text("\n".join(lines) + "\n\n", encoding="utf-8")


def test_retire_on_quiet_fires_at_threshold(tmp_path):
    # Arrange: two prior runs where `metrics` was quiet; current run also quiet.
    _stage_prior_report(tmp_path, "20260101T000000Z", {"metrics": 0, "quality-chain": 2})
    _stage_prior_report(tmp_path, "20260102T000000Z", {"metrics": 0, "quality-chain": 0})

    # Act: current run has metrics quiet (streak = current + 2 priors = 3).
    proposals, runs_recorded = audit._retire_on_quiet_proposals(
        tmp_path, {"metrics": 0, "quality-chain": 1}
    )

    # Assert: metrics proposed at the 3-quiet-run threshold; quality-chain broken
    # by its non-zero prior; the run count reflects current + 2 priors.
    proposed = {p["check"]: p for p in proposals}
    assert "metrics" in proposed
    assert proposed["metrics"]["quiet_run_count"] == 3
    assert "quality-chain" not in proposed
    assert runs_recorded == 3


def test_retire_on_quiet_below_threshold_no_proposal(tmp_path):
    # Arrange: only one prior quiet run — current + 1 prior = streak 2 < 3.
    _stage_prior_report(tmp_path, "20260101T000000Z", {"metrics": 0})

    # Act
    proposals, runs_recorded = audit._retire_on_quiet_proposals(tmp_path, {"metrics": 0})

    # Assert: no proposal below the threshold.
    assert proposals == []
    assert runs_recorded == 2


def test_retire_on_quiet_missing_prior_breaks_streak(tmp_path):
    # Arrange: a prior report predating the era model (no genuine__ keys) must
    # break the streak rather than silently extend it.
    _stage_prior_report(tmp_path, "20260101T000000Z", {"metrics": 0})
    _stage_prior_report(tmp_path, "20260102T000000Z", {})  # legacy report, unknown

    # Act
    proposals, _ = audit._retire_on_quiet_proposals(tmp_path, {"metrics": 0})

    # Assert: the unknown legacy run breaks the streak (no false proposal).
    assert proposals == []


def test_retire_on_quiet_proposes_never_removes(tmp_path):
    # Arrange: a firing proposal.
    _stage_prior_report(tmp_path, "20260101T000000Z", {"metrics": 0})
    _stage_prior_report(tmp_path, "20260102T000000Z", {"metrics": 0})
    proposals, runs_recorded = audit._retire_on_quiet_proposals(tmp_path, {"metrics": 0})
    before = list(audit.CHECK_NAMES)

    # Act
    block = audit.emit_retire_on_quiet_block(proposals, runs_recorded)

    # Assert: the block is a proposal only — the check is never removed.
    assert "check: retire-on-quiet" in block
    assert "proposal_count: 1" in block
    assert "proposal only, no removal" in block
    assert list(audit.CHECK_NAMES) == before


def test_full_run_emits_retire_on_quiet_block_with_no_history(tmp_path):
    # Arrange: a fresh corpus with no prior reports.
    inputs = _minimal_corpus(tmp_path)

    # Act
    output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

    # Assert: the mechanism runs (block emitted) but proposes nothing on run 1.
    assert "check: retire-on-quiet" in output
    assert "runs_recorded: 1" in output
    assert "proposal_count: 0" in output


# ---------------------------------------------------------------------------
# Deliverable 2 (a): call-class-aware impossible-duration ceiling (#849)
# ---------------------------------------------------------------------------


def _log_line(notation_sub: str, seconds: float, level: str = "INFO") -> str:
    """Build one script-execution log line with a trailing (Ns) duration."""
    return (
        f"[2026-06-29T09:00:01Z] [{level}] [3befe7] {notation_sub} (%.1fs)" % seconds
    )


def test_impossible_duration_flags_deterministic_call_over_600(tmp_path):
    # Arrange: a deterministic per-plan-op call recorded well over the flat 600s
    # ceiling (no build / ci-wait class match) and NO run-configuration.
    _write_log(
        tmp_path,
        _log_line("plan-marshall:manage-tasks:manage-tasks read --task-number 3", 700.0),
    )

    # Act
    result = audit.cross_global_log_analysis(tmp_path)

    # Assert: the deterministic call keeps the flat 600s ceiling and is flagged.
    keys = [r["key"] for r in result["impossible_calls"]]
    assert result["impossible_count"] == 1, result["impossible_calls"]
    assert keys == ["plan-marshall:manage-tasks:manage-tasks read"]


def test_impossible_duration_spares_ratcheted_ci_wait_call(tmp_path):
    # Arrange: a build/ci-wait class call at 700s AND a run-configuration whose
    # ratcheted build-queue ceiling (1200s) covers it — #849's adaptive ratchet.
    _write_log(
        tmp_path,
        _log_line("plan-marshall:build-pyproject:pyproject_build run --command-args verify", 700.0),
    )
    config_dir = tmp_path / ".plan"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "run-configuration.json").write_text(
        '{"build": {"queue": {"upper_limit_seconds": 1200}}}', encoding="utf-8"
    )

    # Act
    result = audit.cross_global_log_analysis(tmp_path)

    # Assert: the ratcheted ci-wait call is NOT flagged impossible; it lands in the
    # slow band instead (700 >= slow ceiling but < ratcheted 1200).
    assert result["impossible_count"] == 0, result["impossible_calls"]
    slow_keys = [r["key"] for r in result["slow_calls"]]
    assert "plan-marshall:build-pyproject:pyproject_build run" in slow_keys


def test_impossible_duration_flags_ci_wait_over_ratcheted_ceiling(tmp_path):
    # Arrange: a build/ci-wait class call that EXCEEDS even the ratcheted ceiling
    # (1300 > 1200) — a real hang past the adaptive budget, still flagged.
    _write_log(
        tmp_path,
        _log_line("plan-marshall:build-pyproject:pyproject_build run --command-args verify", 1300.0),
    )
    config_dir = tmp_path / ".plan"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "run-configuration.json").write_text(
        '{"build": {"queue": {"upper_limit_seconds": 1200}}}', encoding="utf-8"
    )

    # Act
    result = audit.cross_global_log_analysis(tmp_path)

    # Assert: over the ratcheted ceiling → flagged impossible.
    assert result["impossible_count"] == 1, result["impossible_calls"]


def test_ratcheted_ci_wait_ceiling_degrades_to_flat_without_config(tmp_path):
    # Arrange: no run-configuration.json at all.
    # Act
    ceiling = audit._ratcheted_ci_wait_ceiling(tmp_path)
    # Assert: degrades to the flat deterministic ceiling (never below the floor).
    assert ceiling == audit._IMPOSSIBLE_DURATION_SECONDS


def test_is_build_or_ci_wait_call_classifier():
    assert audit._is_build_or_ci_wait_call("plan-marshall:build-pyproject:pyproject_build run")
    assert audit._is_build_or_ci_wait_call("plan-marshall:tools-integration-ci:ci checks")
    assert not audit._is_build_or_ci_wait_call("plan-marshall:manage-tasks:manage-tasks read")


# ---------------------------------------------------------------------------
# Deliverable 2 (b): #812 recorded-partiality markers (metrics + input-integrity)
# ---------------------------------------------------------------------------


def _plan_with_metrics(repo_root: Path, body: str) -> audit.PlanInputs:
    """Stage a one-plan corpus whose metrics.toon carries `body`; return inputs."""
    plan_dir = repo_root / ".plan" / "local" / "archived-plans" / "sample-plan"
    (plan_dir / "work").mkdir(parents=True, exist_ok=True)
    (plan_dir / "references.json").write_text('{"scope_estimate": "surgical"}', encoding="utf-8")
    (plan_dir / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    (plan_dir / "work" / "metrics.toon").write_text(body, encoding="utf-8")
    return audit.collect_inputs(plan_dir)


# A zero-token 5-execute with NO partiality marker → genuinely unexplained.
_METRICS_UNEXPLAINED = "[4-plan]\n  total_tokens: 100\n[5-execute]\n  total_tokens: 0\n"
# The SAME zero-token 5-execute, but the #812 markers explain it → recorded-partial.
_METRICS_MARKED = (
    "partial: true\n"
    "unrecorded_phases: 5-execute\n"
    "[4-plan]\n  total_tokens: 100\n[5-execute]\n  total_tokens: 0\n"
)


def test_metrics_unexplained_zero_token_is_incomplete(tmp_path):
    inputs = _plan_with_metrics(tmp_path, _METRICS_UNEXPLAINED)
    result = audit.check_metrics(inputs)
    assert "5-execute" in result["incomplete_recording"]


def test_metrics_marker_explained_zero_token_not_incomplete(tmp_path):
    inputs = _plan_with_metrics(tmp_path, _METRICS_MARKED)
    result = audit.check_metrics(inputs)
    # The marker-explained phase is excluded from incomplete_recording and surfaced
    # as an informational recorded-partial anomaly instead.
    assert "5-execute" not in result["incomplete_recording"]
    assert any("recorded-partial" in a for a in result["anomalies"]), result["anomalies"]


def test_parse_metrics_partiality_reads_markers(tmp_path):
    path = tmp_path / "metrics.toon"
    path.write_text(_METRICS_MARKED, encoding="utf-8")
    partial, unrecorded = audit.parse_metrics_partiality(path)
    assert partial is True
    assert unrecorded == {"5-execute"}


def test_parse_metrics_partiality_absent_markers_degrade(tmp_path):
    path = tmp_path / "metrics.toon"
    path.write_text(_METRICS_UNEXPLAINED, encoding="utf-8")
    partial, unrecorded = audit.parse_metrics_partiality(path)
    assert partial is False
    assert unrecorded == set()


def test_input_integrity_unexplained_execute_is_blind(tmp_path):
    inputs = _plan_with_metrics(tmp_path, _METRICS_UNEXPLAINED)
    result = audit.check_input_integrity(inputs)
    assert result["data_confidence"] == "blind"
    assert "5-execute" in result["metrics_blind"]


def test_input_integrity_marker_explained_execute_is_partial_not_blind(tmp_path):
    inputs = _plan_with_metrics(tmp_path, _METRICS_MARKED)
    result = audit.check_input_integrity(inputs)
    # A #812-marker-explained zero-token execute is recorded-partial, never blind.
    assert result["data_confidence"] == "partial"
    assert "5-execute" not in result["metrics_blind"]


# ---------------------------------------------------------------------------
# Deliverable 2 (c): execution-context-manifest owner-drift (#852 D6)
# ---------------------------------------------------------------------------


def _resolve_owner(step: str):
    return audit._resolve_step_owner(step)


def test_resolve_step_owner_classes():
    assert _resolve_owner("default:push") == "orchestrator"
    assert _resolve_owner("push") == "orchestrator"
    assert _resolve_owner("plan-marshall:automatic-review") == "leaf"
    assert _resolve_owner("default:architecture-refresh") == "hybrid"
    assert _resolve_owner("project:finalize-step-plugin-doctor") == "leaf"
    # Unknown BUILT-IN → None (roster drift); unknown EXTERNAL → None (not drift).
    assert _resolve_owner("default:bogus-finalize-step") is None
    assert _resolve_owner("project:some-unknown-step") is None


def _plan_with_phase6(repo_root: Path, steps: list[str]) -> audit.PlanInputs:
    plan_dir = repo_root / ".plan" / "local" / "archived-plans" / "sample-plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / "references.json").write_text('{"scope_estimate": "surgical"}', encoding="utf-8")
    (plan_dir / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    step_lines = "\n".join(f'    - "{s}"' for s in steps)
    manifest = (
        "phase_5:\n  early_terminate: false\n"
        "phase_6:\n"
        f"  steps[{len(steps)}]:\n{step_lines}\n"
    )
    (plan_dir / "execution.toon").write_text(manifest, encoding="utf-8")
    return audit.collect_inputs(plan_dir)


def test_owner_drift_flags_unknown_builtin_phase6_step(tmp_path):
    inputs = _plan_with_phase6(tmp_path, ["default:push", "default:bogus-finalize-step"])
    drift = audit.detect_owner_drift(inputs)
    assert drift is not None
    assert "bogus-finalize-step" in drift


def test_owner_drift_clean_on_canonical_roster(tmp_path):
    inputs = _plan_with_phase6(
        tmp_path, ["default:push", "default:create-pr", "default:archive-plan"]
    )
    assert audit.detect_owner_drift(inputs) is None


def test_owner_drift_ignores_unknown_external_step(tmp_path):
    # An unknown project/skill step is project-defined, never a canonical-roster fault.
    inputs = _plan_with_phase6(tmp_path, ["default:push", "project:some-unknown-step"])
    assert audit.detect_owner_drift(inputs) is None


def test_manifest_check_surfaces_owner_drift_column(tmp_path):
    inputs = _plan_with_phase6(tmp_path, ["default:bogus-finalize-step"])
    row = audit.check_execution_manifest(inputs, tmp_path, {})
    assert row["owner_drift"]
    assert audit._manifest_genuine(row) is True


# ---------------------------------------------------------------------------
# Deliverable 2 (d): track-selection-accuracy #854 light-lane carve-out era
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Deliverable 2 (e): sequence ci_rerun / phase_reentry (post-#849/#850) pins
# ---------------------------------------------------------------------------


def test_sequence_ci_rerun_fires_on_multiple_ci_run_dirs(tmp_path):
    # Pin: the ci_rerun signal still counts CI run directories (logic unchanged by
    # the post-#849/#850 re-doc; only the interpretation guidance changed).
    plan_dir = tmp_path / ".plan" / "local" / "archived-plans" / "seq-plan"
    (plan_dir / "artifacts" / "ci-runs" / "run-1").mkdir(parents=True)
    (plan_dir / "artifacts" / "ci-runs" / "run-2").mkdir(parents=True)
    (plan_dir / "references.json").write_text('{"scope_estimate": "surgical"}', encoding="utf-8")
    (plan_dir / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    inputs = audit.collect_inputs(plan_dir)

    result = audit.cross_sequence_build_minimality([inputs])
    row = next(r for r in result["rows"] if r["plan_id"] == "seq-plan")
    assert row["ci_runs"] == 2
    assert any(f.startswith("ci_rerun") for f in row["flags"]), row["flags"]


# ---------------------------------------------------------------------------
# Deliverable 3: dispatch-topology check
# ---------------------------------------------------------------------------


def _plan_with_worklog(repo_root: Path, name: str, lines: str) -> audit.PlanInputs:
    pd = repo_root / ".plan" / "local" / "archived-plans" / name
    (pd / "logs").mkdir(parents=True, exist_ok=True)
    (pd / "references.json").write_text('{"scope_estimate": "surgical"}', encoding="utf-8")
    (pd / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    (pd / "logs" / "work.log").write_text(lines, encoding="utf-8")
    return audit.collect_inputs(pd)


def test_dispatch_topology_flags_leaf_dispatch(tmp_path):
    # A dispatch whose caller is a LEAF skill (execute-task) is a topology
    # violation; the orchestrator dispatch and the bare role marker are clean.
    log = (
        "[2026-06-29T09:00:01Z] [INFO] [a] [DISPATCH] (plan-marshall:plan-marshall) target=execution-context-level-3 role=phase-5-execute\n"
        "[2026-06-29T09:00:02Z] [INFO] [b] [DISPATCH] (plan-marshall:execute-task) target=execution-context-level-2 role=phase-5-execute\n"
        "[2026-06-29T09:00:03Z] [INFO] [c] [DISPATCH] (plan-marshall:plan-marshall) role=phase-6-finalize\n"
    )
    row = audit.check_dispatch_topology(_plan_with_worklog(tmp_path, "p1", log))
    assert row["dispatch_count"] == 2  # bare role marker (no target=) excluded
    assert row["leaf_dispatch"] == 1
    assert "plan-marshall:execute-task" in row["violators"]
    assert audit._dispatch_topology_genuine(row) is True


def test_dispatch_topology_clean_on_orchestrator_and_phase_callers(tmp_path):
    # The orchestrator and phase-context callers are the allowed dispatchers.
    log = (
        "[2026-06-29T09:00:01Z] [INFO] [a] [DISPATCH] (plan-marshall:plan-marshall) target=execution-context-level-3 role=phase-5-execute\n"
        "[2026-06-29T09:00:02Z] [INFO] [b] [DISPATCH] (plan-marshall:phase-5-execute) target=execution-context-level-4 role=verification-feedback\n"
    )
    row = audit.check_dispatch_topology(_plan_with_worklog(tmp_path, "clean", log))
    assert row["leaf_dispatch"] == 0
    assert row["violators"] == ""
    assert audit._dispatch_topology_genuine(row) is False


def test_dispatch_topology_no_worklog_is_zero(tmp_path):
    pd = tmp_path / ".plan" / "local" / "archived-plans" / "nolog"
    pd.mkdir(parents=True)
    (pd / "references.json").write_text('{"scope_estimate": "surgical"}', encoding="utf-8")
    (pd / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    row = audit.check_dispatch_topology(audit.collect_inputs(pd))
    assert row["dispatch_count"] == 0
    assert row["leaf_dispatch"] == 0


# ---------------------------------------------------------------------------
# Deliverable 4: finalize-flow-conformance check
# ---------------------------------------------------------------------------


def _plan_finalize(
    repo_root: Path, name: str, phase6: list[str], ci_runs: dict[str, tuple[str, str]]
) -> audit.PlanInputs:
    pd = repo_root / ".plan" / "local" / "archived-plans" / name
    pd.mkdir(parents=True, exist_ok=True)
    (pd / "references.json").write_text('{"scope_estimate": "surgical"}', encoding="utf-8")
    (pd / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    step_lines = "\n".join(f'    - "{s}"' for s in phase6)
    (pd / "execution.toon").write_text(
        f"phase_5:\n  early_terminate: false\nphase_6:\n  steps[{len(phase6)}]:\n{step_lines}\n",
        encoding="utf-8",
    )
    for run_id, (wo, fs) in ci_runs.items():
        rd = pd / "artifacts" / "ci-runs" / run_id
        rd.mkdir(parents=True)
        (rd / "manifest.toon").write_text(
            f"run_id: {run_id}\nwait_outcome: {wo}\nfinal_status: {fs}\n", encoding="utf-8"
        )
    return audit.collect_inputs(pd)


def test_finalize_flow_missing_ci_verify(tmp_path):
    inputs = _plan_finalize(tmp_path, "pr_no_civ", ["default:create-pr", "default:push"], {})
    row = audit.check_finalize_flow_conformance(inputs)
    assert "missing_ci_verify" in row["flags"]
    assert audit._finalize_flow_genuine(row) is True


def test_finalize_flow_ci_wait_timeout_and_unresolved(tmp_path):
    inputs = _plan_finalize(
        tmp_path,
        "timeout",
        ["default:create-pr", "default:ci-verify", "default:push"],
        {"111": ("deadline_exceeded", "timeout")},
    )
    row = audit.check_finalize_flow_conformance(inputs)
    assert "ci_wait_timeout" in row["flags"]
    assert "ci_unresolved" in row["flags"]


def test_finalize_flow_conformant_is_clean(tmp_path):
    inputs = _plan_finalize(
        tmp_path,
        "clean",
        ["default:create-pr", "default:ci-verify", "default:push"],
        {"111": ("completed", "success")},
    )
    row = audit.check_finalize_flow_conformance(inputs)
    assert row["flags"] == ""
    assert row["has_ci_verify_step"] == "true"
    assert audit._finalize_flow_genuine(row) is False


# ---------------------------------------------------------------------------
# Deliverables 3-5: registration + full-sweep coupling wiring
# ---------------------------------------------------------------------------


def test_new_checks_registered_and_era_stamped():
    for c in ("dispatch-topology", "finalize-flow-conformance", "merge-window-accounting"):
        assert c in audit.CHECK_NAMES
        assert c in audit.CHECK_ERA
    assert "merge-window-accounting" in audit.CROSS_PLAN_CHECKS
    assert "dispatch-topology" not in audit.CROSS_PLAN_CHECKS
    assert audit.CHECK_NAMES[-1] == "cross-check-synthesis"


def test_full_sweep_emits_new_blocks_and_couplings(tmp_path):
    inputs = _minimal_corpus(tmp_path)
    output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)
    for c in (
        "dispatch-topology",
        "finalize-flow-conformance",
        "merge-window-accounting",
        "lane-lever-effectiveness",
    ):
        assert f"check: {c}\nstatus: success\nfixed_since: {audit.CHECK_ERA[c]}" in output
    for coupling in (
        "dispatch_topology_reentry",
        "finalize_gate_gap_ci_rerun",
        "merge_window_ci_rerun",
        "surgical_overpay",
    ):
        assert coupling in output
    # cross-check-synthesis remains the last check block, ahead of the meta blocks.
    assert output.index("check: lane-lever-effectiveness") < output.index(
        "check: cross-check-synthesis"
    )


# ---------------------------------------------------------------------------
# Deliverable 6: lane-lever-effectiveness check (cross-plan)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Deliverable 6: surgical_overpay cross-check-synthesis coupling (j)
# ---------------------------------------------------------------------------


def test_lane_lever_registered_and_era_stamped():
    assert "lane-lever-effectiveness" in audit.CHECK_NAMES
    assert "lane-lever-effectiveness" in audit.CROSS_PLAN_CHECKS
    # Era bumped to this plan's own PR boundary (#875).
    assert audit.CHECK_ERA["lane-lever-effectiveness"] == "#875"
    # cross-check-synthesis stays last after the new registration.
    assert audit.CHECK_NAMES[-1] == "cross-check-synthesis"


def test_surgical_overpay_coupling_fires_on_miss_and_big_spend():
    # coupling (j): a lane-lever miss (checkpoint_over) AND token-economics
    # big_spend_tiny_footprint over the same plan.
    all_results = {
        "lane-lever-effectiveness": {
            "rows": [{"plan_id": "p-over", "flags": "checkpoint_over"}]
        },
        "token-economics": {
            "rows": [{"plan_id": "p-over", "flags": ["big_spend_tiny_footprint(2Mtok)"]}]
        },
    }
    result = audit.cross_check_synthesis(all_results)
    by = {r["coupling"]: r for r in result["rows"]}
    assert by["surgical_overpay"]["fired"] is True
    assert "p-over" in by["surgical_overpay"]["detail"]
    assert result["couplings_evaluated"] == 10


def test_surgical_overpay_coupling_unfired_when_facets_disjoint():
    # The lane-lever miss and the big-spend footprint on DIFFERENT plans do not
    # couple — the coupling requires the SAME plan on both facets.
    all_results = {
        "lane-lever-effectiveness": {
            "rows": [{"plan_id": "p-over", "flags": "checkpoint_over"}]
        },
        "token-economics": {
            "rows": [{"plan_id": "other", "flags": ["big_spend_tiny_footprint(2Mtok)"]}]
        },
    }
    result = audit.cross_check_synthesis(all_results)
    by = {r["coupling"]: r for r in result["rows"]}
    assert by["surgical_overpay"]["fired"] is False


def test_synthesis_evaluates_ten_couplings_on_empty_results():
    # Best-effort degradation: every coupling (now ten) still evaluated, none fired.
    result = audit.cross_check_synthesis({})
    assert result["couplings_evaluated"] == 10
    assert result["couplings_fired"] == 0
    by = {r["coupling"]: r for r in result["rows"]}
    assert "surgical_overpay" in by


# ---------------------------------------------------------------------------
# Deliverable 5: merge-window-accounting check (cross-plan)
# ---------------------------------------------------------------------------


def _write_merge_log(repo_root: Path, name: str, lines: str) -> None:
    """Stage a global log carrying `[LOCK] (merge:*)` lifecycle lines."""
    logs_dir = repo_root / ".plan" / "local" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / name).write_text(lines, encoding="utf-8")


def _lock_inputs(repo_root: Path, *plan_ids: str) -> list:
    """Build a corpus of PlanInputs for the named plan ids (no disk artifacts).

    ``cross_merge_window_accounting`` reads only the corpus plan-id set (for the
    ``in_corpus`` attribution column) plus the global logs under ``repo_root``, so
    the inputs are constructed directly rather than materialised on disk.
    """
    return [
        audit.PlanInputs(
            plan_id=pid,
            plan_dir=repo_root / ".plan" / "local" / "archived-plans" / pid,
        )
        for pid in plan_ids
    ]


def test_merge_window_blocked_plan_flags_contention(tmp_path):
    # A plan that was `blocked` (waited behind the FIFO front) records
    # merge_contention and is a genuine signal; its max_waiting rides on the
    # immediately-following indented waiting_count line.
    log = (
        "[2026-07-01T10:00:00Z] [INFO] [a] [LOCK] (merge:blocked) planA\n"
        "    waiting_count: 2\n"
        "[2026-07-01T10:05:00Z] [INFO] [b] [LOCK] (merge:acquired) planA\n"
        "    waiting_count: 0\n"
        "[2026-07-01T10:10:00Z] [INFO] [c] [LOCK] (merge:released) planA\n"
    )
    _write_merge_log(tmp_path, "work-2026-07-01.log", log)
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planA"), tmp_path)

    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["plan_id"] == "planA"
    assert row["in_corpus"] == "true"
    assert row["blocked"] == 1
    assert row["acquired"] == 1
    assert row["released"] == 1
    assert row["max_waiting"] == 2
    assert row["flags"] == "merge_contention"
    assert audit._merge_window_genuine(row) is True
    assert result["corpus"]["contended_plans"] == 1
    assert result["corpus"]["total_blocked"] == 1
    assert result["corpus"]["max_waiting_observed"] == 2


def test_merge_window_uncontended_plan_is_clean(tmp_path):
    # A plain acquire/release with no block and a queue depth of 1 (only this
    # plan) is uncontended: no flag, informational.
    log = (
        "[2026-07-01T11:00:00Z] [INFO] [a] [LOCK] (merge:acquired) planB\n"
        "    waiting_count: 1\n"
        "[2026-07-01T11:05:00Z] [INFO] [b] [LOCK] (merge:released) planB\n"
    )
    _write_merge_log(tmp_path, "work-2026-07-01.log", log)
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planB"), tmp_path)

    row = result["rows"][0]
    assert row["blocked"] == 0
    assert row["max_waiting"] == 1
    assert row["flags"] == ""
    assert audit._merge_window_genuine(row) is False
    assert result["corpus"]["contended_plans"] == 0


def test_merge_window_high_waiting_count_flags_contention(tmp_path):
    # Even without a `blocked` event, a max_waiting > 1 (other plans queued
    # behind this one) is contention — the plan held the mutex while others waited.
    log = (
        "[2026-07-01T12:00:00Z] [INFO] [a] [LOCK] (merge:acquired) planC\n"
        "    waiting_count: 3\n"
    )
    _write_merge_log(tmp_path, "work-2026-07-01.log", log)
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planC"), tmp_path)

    row = result["rows"][0]
    assert row["blocked"] == 0
    assert row["max_waiting"] == 3
    assert row["flags"] == "merge_contention"


def test_merge_window_attributes_out_of_corpus_lock(tmp_path):
    # A lock_id whose plan is NOT in the scanned corpus still emits a row (carried
    # for corpus totals) but is marked in_corpus=false.
    log = (
        "[2026-07-01T13:00:00Z] [INFO] [a] [LOCK] (merge:acquired) foreign-plan\n"
        "    waiting_count: 0\n"
    )
    _write_merge_log(tmp_path, "work-2026-07-01.log", log)
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planA"), tmp_path)

    assert len(result["rows"]) == 1
    assert result["rows"][0]["plan_id"] == "foreign-plan"
    assert result["rows"][0]["in_corpus"] == "false"


def test_merge_window_no_logs_yields_no_rows(tmp_path):
    # Best-effort: an absent logs dir yields no rows and zeroed corpus totals.
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planA"), tmp_path)
    assert result["rows"] == []
    assert result["corpus"]["plans_with_merge_events"] == 0
    assert result["corpus"]["max_waiting_observed"] == 0


def test_merge_window_reclaimed_event_counted(tmp_path):
    # The `reclaimed` event (a stale lock reclaimed) is bucketed and counted
    # per-plan without itself being contention.
    log = (
        "[2026-07-01T14:00:00Z] [INFO] [a] [LOCK] (merge:reclaimed) planD\n"
        "    waiting_count: 0\n"
    )
    _write_merge_log(tmp_path, "work-2026-07-01.log", log)
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planD"), tmp_path)

    row = result["rows"][0]
    assert row["reclaimed"] == 1
    assert row["flags"] == ""


def test_emit_merge_window_block_renders_header_and_severity(tmp_path):
    # The emitted block carries the corpus header scalars, the genuine_signal_count
    # summary, and the rows[] column set ending in severity.
    log = (
        "[2026-07-01T15:00:00Z] [INFO] [a] [LOCK] (merge:blocked) planE\n"
        "    waiting_count: 2\n"
        "[2026-07-01T15:05:00Z] [INFO] [b] [LOCK] (merge:acquired) planE\n"
    )
    _write_merge_log(tmp_path, "work-2026-07-01.log", log)
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planE"), tmp_path)

    block = audit.emit_merge_window_accounting_block(result)

    assert "check: merge-window-accounting" in block
    assert "status: success" in block
    assert "contended_plans: 1" in block
    assert "genuine_signal_count: 1" in block
    assert (
        "rows[1]{plan_id,in_corpus,acquired,released,blocked,reclaimed,"
        "max_waiting,flags,severity}:" in block
    )
    genuine_row = next(
        ln.strip() for ln in block.splitlines() if ln.strip().startswith("planE,")
    )
    assert genuine_row.endswith(",genuine")
