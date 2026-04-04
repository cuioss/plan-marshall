#!/usr/bin/env python3
"""Build result output formatting utilities.

Shared formatting for build command results across build systems.
Provides TOON and JSON output formats per build-execution.md specification.

Uses serialize_toon from toon_parser (ref-toon-format) as the canonical
TOON serializer. This module normalizes build-specific data structures
(Issue objects, UnitTestSummary) before delegating to serialize_toon.

Convention: None values in issue fields are rendered as '-' (dash) in
formatted output for readability (e.g., missing file or line number).

Usage:
    from build_format import format_toon, format_json

    # Format result as TOON
    result = {"status": "success", "exit_code": 0, ...}
    toon_output = format_toon(result)

    # Format result as JSON
    json_output = format_json(result)
"""

import json
from collections import OrderedDict
from typing import Any

from toon_parser import serialize_toon  # type: ignore[import-not-found]

# =============================================================================
# Constants
# =============================================================================

# Core fields in output order
CORE_FIELDS = ['status', 'exit_code', 'duration_seconds', 'log_file', 'command']
"""Core fields that appear in every result, in display order."""

# Additional fields that may appear after core fields
EXTRA_FIELDS = ['error', 'timeout_used_seconds', 'wrapper', 'command_type']
"""Additional scalar fields that appear after core fields."""

# Structured fields handled specially
STRUCTURED_FIELDS = {'errors', 'warnings', 'tests'}
"""Fields containing structured data (lists/dicts) formatted specially in TOON."""


# =============================================================================
# TOON Formatting
# =============================================================================


def format_toon(result: dict) -> str:
    """Format result dict as TOON output using canonical serialize_toon.

    Normalizes Issue/UnitTestSummary objects to plain dicts, orders fields
    per the build-execution.md specification, then delegates to serialize_toon
    from toon_parser (ref-toon-format skill).

    Args:
        result: Result dict from build_result.*_result() functions.
            May contain Issue objects (with to_dict()) or plain dicts.

    Returns:
        TOON-formatted string.
    """
    # Build ordered dict to control field output order
    ordered: OrderedDict[str, Any] = OrderedDict()

    # Core fields first (in order)
    for field in CORE_FIELDS:
        if field in result:
            ordered[field] = result[field]

    # Extra scalar fields
    for field in EXTRA_FIELDS:
        if field in result:
            ordered[field] = result[field]

    # Errors section — normalize Issue objects to dicts with consistent fields
    if 'errors' in result and result['errors']:
        errors = _normalize_issues(result['errors'])
        # Ensure consistent field set for uniform array serialization
        ordered['errors'] = [
            OrderedDict(
                [
                    ('file', err.get('file', '-') or '-'),
                    ('line', err.get('line') if err.get('line') is not None else '-'),
                    ('message', err.get('message', '')),
                    ('category', err.get('category', '')),
                ]
            )
            for err in errors
        ]

    # Warnings section — normalize with optional accepted field
    if 'warnings' in result and result['warnings']:
        warnings = _normalize_issues(result['warnings'])
        has_accepted = any(w.get('accepted') is not None for w in warnings)
        if has_accepted:
            ordered['warnings'] = [
                OrderedDict(
                    [
                        ('file', w.get('file', '-') or '-'),
                        ('line', w.get('line') if w.get('line') is not None else '-'),
                        ('message', w.get('message', '')),
                        ('accepted', '[accepted]' if w.get('accepted') else ''),
                    ]
                )
                for w in warnings
            ]
        else:
            ordered['warnings'] = [
                OrderedDict(
                    [
                        ('file', w.get('file', '-') or '-'),
                        ('line', w.get('line') if w.get('line') is not None else '-'),
                        ('message', w.get('message', '')),
                    ]
                )
                for w in warnings
            ]

    # Tests section — normalize UnitTestSummary to dict
    if 'tests' in result and result['tests']:
        tests = _normalize_dict(result['tests'])
        ordered['tests'] = OrderedDict(
            [
                ('passed', tests.get('passed', 0)),
                ('failed', tests.get('failed', 0)),
                ('skipped', tests.get('skipped', 0)),
            ]
        )

    return serialize_toon(dict(ordered))


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
    normalized: dict[str, Any] = {}
    for key, value in result.items():
        if key == 'errors' or key == 'warnings':
            normalized[key] = _normalize_issues(value)
        elif key == 'tests':
            normalized[key] = _normalize_dict(value)
        else:
            normalized[key] = value
    return normalized


def _normalize_issues(issues: list) -> list[dict[Any, Any]]:
    """Convert list of Issues or dicts to list of dicts.

    Args:
        issues: List that may contain Issue objects or plain dicts.

    Returns:
        List of plain dicts.
    """
    result: list[dict[Any, Any]] = []
    for issue in issues:
        if hasattr(issue, 'to_dict'):
            issue_dict: dict[Any, Any] = issue.to_dict()
            result.append(issue_dict)
        elif isinstance(issue, dict):
            result.append(issue)
        else:
            # Unexpected type, skip
            continue
    return result


def _normalize_dict(obj: Any) -> dict[Any, Any]:
    """Convert object with to_dict() or dict to plain dict.

    Args:
        obj: Object that may have to_dict() method or be a dict.

    Returns:
        Plain dict.
    """
    if hasattr(obj, 'to_dict'):
        normalized: dict[Any, Any] = obj.to_dict()
        return normalized
    if isinstance(obj, dict):
        return obj
    return {}
