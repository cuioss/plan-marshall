#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``global-log-analysis`` benign-probe allowlist — a marker-free ``resolve``
call stamped at an elevated level is a benign non-zero-exit probe and is
excluded from ``error_lines``, while the SAME line carrying a failure marker
is still flagged.
"""


from _audit_fixtures import PROBE_LOG_NAME, _write_log, audit

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


def test_resolve_probe_excluded_from_error_lines(tmp_path):
    # Arrange: a marker-free `resolve` call stamped at ERROR.
    _write_log(tmp_path, PROBE_LOG_NAME, [_BENIGN_RESOLVE_LINE])

    # Act
    result = audit.cross_global_log_analysis(tmp_path)

    # Assert: the benign `resolve` probe is NOT counted as an error line.
    details = [entry["detail"] for entry in result["error_lines"]]
    assert result["error_lines"] == [], (
        f"benign resolve probe should be excluded from error_lines, got {details}"
    )


def test_resolve_with_failure_marker_included_in_error_lines(tmp_path):
    # Arrange: the same `resolve` call carrying a `status: error` failure marker.
    _write_log(tmp_path, PROBE_LOG_NAME, [_RESOLVE_LINE_WITH_MARKER])

    # Act
    result = audit.cross_global_log_analysis(tmp_path)

    # Assert: a failure-marker line is flagged even though `resolve` is allowlisted.
    assert len(result["error_lines"]) == 1, (
        f"resolve line with failure marker must be flagged, got {result['error_lines']}"
    )
    assert "resolve" in result["error_lines"][0]["detail"]
