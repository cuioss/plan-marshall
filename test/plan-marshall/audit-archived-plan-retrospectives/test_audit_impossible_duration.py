#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The call-class-aware impossible-duration ceiling — a deterministic call over
the flat ceiling is flagged, while a ci-wait call is measured against its own
ratcheted ceiling and degrades to the flat one when no config supplies it.
"""

from _audit_fixtures import PROBE_LOG_NAME, _write_log, audit


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
        PROBE_LOG_NAME,
        [_log_line("plan-marshall:manage-tasks:manage-tasks read --task-number 3", 700.0)],
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
        PROBE_LOG_NAME,
        [_log_line("plan-marshall:build-pyproject:pyproject_build run --command-args verify", 700.0)],
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
        PROBE_LOG_NAME,
        [_log_line("plan-marshall:build-pyproject:pyproject_build run --command-args verify", 1300.0)],
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
