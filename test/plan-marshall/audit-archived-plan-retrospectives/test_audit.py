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
