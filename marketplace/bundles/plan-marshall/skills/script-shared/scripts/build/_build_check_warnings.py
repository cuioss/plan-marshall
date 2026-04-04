#!/usr/bin/env python3
"""Shared check-warnings subcommand logic for all build skills.

Extracts the common input parsing and classification flow that was duplicated
across build-maven and build-gradle. Each skill provides its matcher type,
severity filter, and pattern handling; the input/output logic is identical.
"""

from __future__ import annotations

import json

from _build_shared import create_subcommand_handler  # noqa: F401 -- re-export for backward compat
from _warnings_classify import categorize_warnings  # type: ignore[import-not-found]
from toon_parser import serialize_toon  # type: ignore[import-not-found]


def create_check_warnings_handler(
    matcher: str = 'substring',
    filter_severity: str | None = None,
):
    """Factory: create a tool-specific check-warnings subcommand handler.

    Thin wrapper around create_subcommand_handler for backward compatibility.
    New code should use create_subcommand_handler(cmd_check_warnings_base, ...)
    directly.
    """
    return create_subcommand_handler(
        cmd_check_warnings_base,
        matcher=matcher,
        filter_severity=filter_severity,
    )


def cmd_check_warnings_base(
    args,
    matcher: str = 'substring',
    filter_severity: str | None = None,
) -> int:
    """Handle check-warnings subcommand with tool-specific classification options.

    Args:
        args: Parsed argparse namespace. Expects attributes:
            warnings (JSON string), acceptable_warnings (JSON string).
        matcher: Pattern matcher type ('substring', 'wildcard', 'regex').
        filter_severity: If set, only warnings with this severity are processed.

    Returns:
        Exit code: 0 if no fixable/unknown warnings, 1 otherwise.
    """
    warnings = None
    patterns: dict = {}

    if not args.warnings:
        print(serialize_toon({'status': 'error', 'error': 'No input provided. Use --warnings.'}))
        return 1

    try:
        warnings = json.loads(args.warnings)
    except json.JSONDecodeError as e:
        print(serialize_toon({'status': 'error', 'error': f'Invalid JSON in --warnings: {e}'}))
        return 1

    if getattr(args, 'acceptable_warnings', None):
        try:
            patterns = json.loads(args.acceptable_warnings)
        except json.JSONDecodeError as e:
            print(serialize_toon({'status': 'error', 'error': f'Invalid JSON in --acceptable-warnings: {e}'}))
            return 1

    if warnings is None or not isinstance(warnings, list):
        print(serialize_toon({'status': 'error', 'error': 'warnings must be an array'}))
        return 1

    classify_kwargs: dict = {'matcher': matcher}
    if filter_severity:
        classify_kwargs['filter_severity'] = filter_severity

    categorized = categorize_warnings(warnings, patterns, **classify_kwargs)
    fixable_count = len(categorized['fixable'])
    unknown_count = len(categorized['unknown'])
    result = {
        'status': 'success',
        'total': len(warnings),
        'acceptable': len(categorized['acceptable']),
        'fixable': fixable_count,
        'unknown': unknown_count,
        'categorized': categorized,
    }
    print(serialize_toon(result))
    return 1 if fixable_count > 0 or unknown_count > 0 else 0
