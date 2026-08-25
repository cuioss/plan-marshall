#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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

from toon_parser import serialize_toon

# =============================================================================
# Constants
# =============================================================================

# Core fields in output order
CORE_FIELDS = ['status', 'exit_code', 'duration_seconds', 'log_file', 'command']
"""Core fields that appear in every result, in display order."""

# Additional fields that may appear after core fields
EXTRA_FIELDS = [
    'error',
    'message',
    'timeout_used_seconds',
    'tool_duration_seconds',
    'wrapper',
    'command_type',
    'truncated',
    'tests_run',
    'tests_population',
    'analyses_examined',
]
"""Additional scalar fields that appear after core fields.

**This list is a whitelist, and omission is silent.** A field absent from it is
dropped from TOON output with no warning while the JSON path still carries it,
so the two formats disagree and a TOON consumer is denied a value the producer
computed. Every scalar a consumer must act on therefore has to be listed here.

``message`` carries the operator-facing detail of a result whose ``status`` alone
does not say what to do — above all a ``killed`` build's "externally killed — not
flaky, do not blind-retry". Dropping it would leave the emitted TOON saying a
build was killed while withholding the one instruction that changes the reader's
next action.

``truncated`` is the count reconciling the capped/deduped ``errors`` array against
the true total (see ``_build_shared._cap_errors_with_truncation``); it must be in
this whitelist or ``format_toon`` silently drops it and ``errors`` count-vs-shown
can disagree in TOON output (the JSON path already passes it through).

``tool_duration_seconds`` is the test tool's own reported run duration, surfaced
next to ``duration_seconds`` (wall clock) so a run killed before it finished shows
how long the suite actually took before the kill. Like ``truncated`` it must be
listed here or ``format_toon`` drops it silently.

``tests_run`` is the MEASURED executed-test count a green run reports on its
success result (see ``_build_shared.cmd_run_common``). It is part of the
population the green-build finding reconciliation was decided on — a
``test-failure`` finding is cleared only when a measured ``tests_run > 0`` — so it
must be published, never left implicit; listing it here keeps the TOON and JSON
success outputs in agreement. It is emitted ONLY when the count was measured: an
unmeasured run omits the key rather than publishing a zero that a consumer would
read as "tested nothing".

``tests_population`` is that omission's discriminator (``measured`` /
``unmeasured``). It is always present on a success result, so an absent
``tests_run`` is legible as "not measured" rather than merely missing — the
absence says something, and this field is what says it.

``analyses_examined`` names the analysis kinds the run actually performed
(``compile``, ``lint``, ``test``), or the literal ``unknown`` when the invocation
is not one the canonical vocabulary describes. It is the OTHER half of the
reconciliation population: a finding type is cleared only when the run performed
an analysis that can reach it, and this field publishes which those were."""

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
        # The optional `detail` projection surfaces the representative failure
        # block (deliverable 9) on default TOON output. Issue.to_dict() already
        # exposes `detail` to JSON, but the tabular error rows dropped it, so the
        # default TOON path silently lost the failure detail. The column is added
        # only when at least one row carries a detail (the historical 4-field
        # shape is preserved otherwise, keeping existing consumers stable).
        include_detail = any(err.get('detail') for err in errors)
        rows: list[OrderedDict[str, Any]] = []
        for err in errors:
            row: OrderedDict[str, Any] = OrderedDict(
                [
                    ('file', err.get('file', '-') or '-'),
                    ('line', err.get('line') if err.get('line') is not None else '-'),
                    ('message', err.get('message', '')),
                    ('category', err.get('category', '')),
                ]
            )
            if include_detail:
                row['detail'] = _collapse_detail(err.get('detail'))
            rows.append(row)
        ordered['errors'] = rows

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

    # Tests section — normalize UnitTestSummary to dict.
    # `duration_seconds` is projected only when the tool reported one, so the
    # historical three-field block stays bit-for-bit identical for tools whose
    # parsers do not populate it (Maven/Gradle/npm). `total` stays unprojected.
    if 'tests' in result and result['tests']:
        tests = _normalize_dict(result['tests'])
        tests_section: OrderedDict[str, Any] = OrderedDict(
            [
                ('passed', tests.get('passed', 0)),
                ('failed', tests.get('failed', 0)),
                ('skipped', tests.get('skipped', 0)),
            ]
        )
        if tests.get('duration_seconds') is not None:
            tests_section['duration_seconds'] = tests['duration_seconds']
        ordered['tests'] = tests_section

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


def _collapse_detail(detail: Any) -> str:
    """Collapse a possibly multi-line failure detail block to a single line.

    The TOON error table is line-oriented (one physical line per row), so a raw
    multi-line traceback block would break the row-per-line round-trip — the
    serializer quotes newline-bearing values but the embedded newline still
    splits the row across physical lines. Collapsing the block's non-empty lines
    to a ` | `-joined single line keeps it on one physical row while remaining
    readable. Empty / None details render as '-'.
    """
    if not detail:
        return '-'
    parts = [segment.strip() for segment in str(detail).splitlines() if segment.strip()]
    return ' | '.join(parts) if parts else '-'


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
