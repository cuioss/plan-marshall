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

import sys
from pathlib import Path

from conftest import PROJECT_ROOT

_AUDIT_SCRIPTS_DIR = (
    PROJECT_ROOT / ".claude" / "skills" / "audit-archived-plan-retrospectives" / "scripts"
)
if str(_AUDIT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AUDIT_SCRIPTS_DIR))

import audit  # noqa: E402

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


def _plan_with_metrics(repo_root: Path, body: str) -> "audit.PlanInputs":
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
    assert _resolve_owner("default:automated-review") == "leaf"
    assert _resolve_owner("default:architecture-refresh") == "hybrid"
    assert _resolve_owner("project:finalize-step-plugin-doctor") == "leaf"
    # Unknown BUILT-IN → None (roster drift); unknown EXTERNAL → None (not drift).
    assert _resolve_owner("default:bogus-finalize-step") is None
    assert _resolve_owner("project:some-unknown-step") is None


def _plan_with_phase6(repo_root: Path, steps: list[str]) -> "audit.PlanInputs":
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
    if routing is None:  # pragma: no cover - router import guard
        import pytest

        pytest.skip("planning-lane router unavailable")
    return routing


def _track_inputs(repo_root: Path, scope: str, change_type: str, lane: str) -> "audit.PlanInputs":
    plan_dir = repo_root / ".plan" / "local" / "archived-plans" / "track-plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    import json

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


def _plan_with_worklog(repo_root: Path, name: str, lines: str) -> "audit.PlanInputs":
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
) -> "audit.PlanInputs":
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
    for c in ("dispatch-topology", "finalize-flow-conformance", "merge-window-accounting"):
        assert f"check: {c}\nstatus: success\nfixed_since: {audit.CHECK_ERA[c]}" in output
    for coupling in (
        "dispatch_topology_reentry",
        "finalize_gate_gap_ci_rerun",
        "merge_window_ci_rerun",
    ):
        assert coupling in output
