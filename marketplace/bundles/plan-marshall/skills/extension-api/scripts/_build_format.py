#!/usr/bin/env python3
"""Build result output formatting utilities.

Shared formatting for build command results across build systems.
Provides TOON and JSON output formats per build-return.md specification.

Usage:
    from build_format import format_toon, format_json

    # Format result as TOON
    result = {"status": "success", "exit_code": 0, ...}
    toon_output = format_toon(result)

    # Format result as JSON
    json_output = format_json(result)
"""

import json
from typing import Any


# =============================================================================
# Constants
# =============================================================================

# Core fields in output order
CORE_FIELDS = ["status", "exit_code", "duration_seconds", "log_file", "command"]
"""Core fields that appear in every result, in display order."""

# Additional fields that may appear after core fields
EXTRA_FIELDS = ["error", "timeout_used_seconds", "wrapper", "command_type"]
"""Additional scalar fields that appear after core fields."""

# Structured fields handled specially
STRUCTURED_FIELDS = {"errors", "warnings", "tests"}
"""Fields containing structured data (lists/dicts) formatted specially in TOON."""


# =============================================================================
# TOON Formatting
# =============================================================================

def format_toon(result: dict) -> str:
    """Format result dict as TOON output.

    Produces tab-separated key-value pairs for scalar fields,
    followed by structured sections for errors, warnings, and tests.

    Args:
        result: Result dict from build_result.*_result() functions.
            May contain Issue objects (with to_dict()) or plain dicts.

    Returns:
        TOON-formatted string with tab separators.

    Example output (success):
        status\tsuccess
        exit_code\t0
        duration_seconds\t45
        log_file\t.plan/temp/build-output/default/maven-2026-01-06-143000.log
        command\t./mvnw clean verify

    Example output (error with issues):
        status\terror
        exit_code\t1
        ...
        error\tbuild_failed

        errors[2]{file,line,message,category}:
        src/Main.java\t15\tcannot find symbol\tcompilation
        src/Test.java\t42\ttest failed\ttest_failure

        warnings[1]{file,line,message}:
        pom.xml\t-\tdeprecated version\tdeprecation

        tests:
          passed: 10
          failed: 2
          skipped: 1
    """
    lines = []

    # Core fields first (in order)
    for field in CORE_FIELDS:
        if field in result:
            lines.append(f"{field}\t{result[field]}")

    # Extra scalar fields
    for field in EXTRA_FIELDS:
        if field in result:
            lines.append(f"{field}\t{result[field]}")

    # Errors section
    if "errors" in result and result["errors"]:
        lines.append("")  # Blank line before section
        errors = _normalize_issues(result["errors"])
        lines.append(f"errors[{len(errors)}]{{file,line,message,category}}:")
        for err in errors:
            line_num = err.get("line") if err.get("line") is not None else "-"
            category = err.get("category", "")
            lines.append(f"{err.get('file', '-')}\t{line_num}\t{err.get('message', '')}\t{category}")

    # Warnings section
    if "warnings" in result and result["warnings"]:
        lines.append("")  # Blank line before section
        warnings = _normalize_issues(result["warnings"])
        # Check if any warning has 'accepted' field (structured mode)
        has_accepted = any(w.get("accepted") is not None for w in warnings)
        if has_accepted:
            lines.append(f"warnings[{len(warnings)}]{{file,line,message,accepted}}:")
            for warn in warnings:
                line_num = warn.get("line") if warn.get("line") is not None else "-"
                accepted = "[accepted]" if warn.get("accepted") else ""
                lines.append(f"{warn.get('file', '-')}\t{line_num}\t{warn.get('message', '')}\t{accepted}")
        else:
            lines.append(f"warnings[{len(warnings)}]{{file,line,message}}:")
            for warn in warnings:
                line_num = warn.get("line") if warn.get("line") is not None else "-"
                lines.append(f"{warn.get('file', '-')}\t{line_num}\t{warn.get('message', '')}")

    # Tests section
    if "tests" in result and result["tests"]:
        lines.append("")  # Blank line before section
        tests = _normalize_dict(result["tests"])
        lines.append("tests:")
        lines.append(f"  passed: {tests.get('passed', 0)}")
        lines.append(f"  failed: {tests.get('failed', 0)}")
        lines.append(f"  skipped: {tests.get('skipped', 0)}")

    return "\n".join(lines)


# =============================================================================
# JSON Formatting
# =============================================================================

def format_json(result: dict, indent: int = 2) -> str:
    """Format result dict as JSON output.

    Converts any Issue or UnitTestSummary objects to dicts before serialization.

    Args:
        result: Result dict from build_result.*_result() functions.
            May contain Issue objects (with to_dict()) or plain dicts.
        indent: JSON indentation level (default 2).

    Returns:
        JSON-formatted string.

    Example:
        >>> result = {"status": "success", "exit_code": 0}
        >>> print(format_json(result))
        {
          "status": "success",
          "exit_code": 0
        }
    """
    normalized = _normalize_result(result)
    return json.dumps(normalized, indent=indent)


# =============================================================================
# Helper Functions
# =============================================================================

def _normalize_result(result: dict) -> dict:
    """Normalize result dict for JSON serialization.

    Converts Issue and UnitTestSummary objects to dicts.

    Args:
        result: Result dict that may contain objects with to_dict().

    Returns:
        Dict with all nested objects converted to plain dicts.
    """
    normalized = {}
    for key, value in result.items():
        if key == "errors" or key == "warnings":
            normalized[key] = _normalize_issues(value)
        elif key == "tests":
            normalized[key] = _normalize_dict(value)
        else:
            normalized[key] = value
    return normalized


def _normalize_issues(issues: list) -> list[dict]:
    """Convert list of Issues or dicts to list of dicts.

    Args:
        issues: List that may contain Issue objects or plain dicts.

    Returns:
        List of plain dicts.
    """
    result = []
    for issue in issues:
        if hasattr(issue, "to_dict"):
            result.append(issue.to_dict())
        elif isinstance(issue, dict):
            result.append(issue)
        else:
            # Unexpected type, skip
            continue
    return result


def _normalize_dict(obj: Any) -> dict:
    """Convert object with to_dict() or dict to plain dict.

    Args:
        obj: Object that may have to_dict() method or be a dict.

    Returns:
        Plain dict.
    """
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return obj
    return {}
