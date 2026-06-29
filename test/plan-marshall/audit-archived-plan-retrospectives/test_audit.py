#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Regression tests for the global-log-analysis benign-probe allowlist.

Pin the ``resolve`` subcommand's membership in ``_LOG_BENIGN_PROBE_SUBCOMMANDS``:
a marker-free ``resolve`` call line stamped at an elevated level is a benign
non-zero-exit probe (e.g. ``manage-personas resolve`` answering a
resolution-miss) and MUST be excluded from ``error_lines``, while the SAME line
carrying a failure marker MUST still be flagged. Drives
``cross_global_log_analysis`` directly by inserting the project-local audit
skill's ``scripts/`` dir on sys.path (the script is not a marketplace-bundle
script, so ``conftest.get_script_path`` does not resolve it).
"""

from __future__ import annotations

import sys
from pathlib import Path

from conftest import PROJECT_ROOT  # type: ignore[import-not-found]

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
