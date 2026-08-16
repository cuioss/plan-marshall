#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Retire-on-quiet — a check quiet for at least ``THRESHOLDS["retire_on_quiet_runs"]``
consecutive recorded runs is PROPOSED for retirement and never removed; a
missing prior report breaks the streak rather than extending it.
"""

from pathlib import Path

from _audit_fixtures import (
    audit,
    minimal_corpus,
)


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
    inputs = minimal_corpus(tmp_path)

    # Act
    output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

    # Assert: the mechanism runs (block emitted) but proposes nothing on run 1.
    assert "check: retire-on-quiet" in output
    assert "runs_recorded: 1" in output
    assert "proposal_count: 0" in output
