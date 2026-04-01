#!/usr/bin/env python3
"""Shared check-warnings subcommand logic for all build skills.

Extracts the common input parsing and classification flow that was duplicated
across build-maven and build-gradle. Each skill provides its matcher type,
severity filter, and pattern handling; the input/output logic is identical.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable

from _warnings_classify import categorize_warnings, flatten_patterns  # type: ignore[import-not-found]


def create_check_warnings_handler(
    matcher: str = 'substring',
    filter_severity: str | None = None,
    supports_patterns_arg: bool = False,
) -> Callable:
    """Factory: create a tool-specific check-warnings subcommand handler.

    Args:
        matcher: Pattern matcher type ('substring', 'wildcard', 'regex').
        filter_severity: If set, only warnings with this severity are processed.
        supports_patterns_arg: If True, supports --patterns as flat list input.

    Returns:
        A cmd_check_warnings(args) -> int function ready for argparse set_defaults.
    """
    def cmd_check_warnings(args) -> int:
        return cmd_check_warnings_base(args, matcher=matcher, filter_severity=filter_severity,
                                       supports_patterns_arg=supports_patterns_arg)
    return cmd_check_warnings


def cmd_check_warnings_base(
    args,
    matcher: str = 'substring',
    filter_severity: str | None = None,
    supports_patterns_arg: bool = False,
) -> int:
    """Handle check-warnings subcommand with tool-specific classification options.

    Args:
        args: Parsed argparse namespace. Expects attributes:
            warnings (JSON string), acceptable_warnings (JSON string),
            and optionally patterns (JSON string).
        matcher: Pattern matcher type ('substring', 'wildcard', 'regex').
        filter_severity: If set, only warnings with this severity are processed.
        supports_patterns_arg: If True, supports --patterns as flat list input
            (Maven-style). Otherwise, only --acceptable-warnings dict is supported.

    Returns:
        Exit code: 0 if no fixable/unknown warnings, 1 otherwise.
    """
    warnings = None
    patterns: list | dict = [] if supports_patterns_arg else {}

    if args.warnings:
        try:
            warnings = json.loads(args.warnings)
        except json.JSONDecodeError as e:
            print(json.dumps({'success': False, 'error': f'Invalid JSON in --warnings: {e}'}, indent=2))
            return 1

        if supports_patterns_arg and getattr(args, 'patterns', None):
            try:
                patterns = json.loads(args.patterns)
            except json.JSONDecodeError as e:
                print(json.dumps({'success': False, 'error': f'Invalid JSON in --patterns: {e}'}, indent=2))
                return 1
        elif getattr(args, 'acceptable_warnings', None):
            try:
                aw = json.loads(args.acceptable_warnings)
                patterns = flatten_patterns(aw) if supports_patterns_arg else aw
            except json.JSONDecodeError as e:
                print(json.dumps({'success': False, 'error': f'Invalid JSON in --acceptable-warnings: {e}'}, indent=2))
                return 1
    else:
        if sys.stdin.isatty():
            print(json.dumps({'success': False, 'error': 'No input provided. Use --warnings or pipe JSON to stdin.'}, indent=2))
            return 1
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(json.dumps({'success': False, 'error': f'Invalid JSON from stdin: {e}'}, indent=2))
            return 1
        warnings = input_data.get('warnings', [])
        if supports_patterns_arg:
            patterns = input_data.get('patterns', []) or flatten_patterns(input_data.get('acceptable_warnings', {}))
        else:
            patterns = input_data.get('acceptable_warnings', {})

    if warnings is None or not isinstance(warnings, list):
        print(json.dumps({'success': False, 'error': 'warnings must be an array'}, indent=2))
        return 1

    classify_kwargs: dict = {'matcher': matcher}
    if filter_severity:
        classify_kwargs['filter_severity'] = filter_severity

    categorized = categorize_warnings(warnings, patterns, **classify_kwargs)
    total = sum(len(v) for v in categorized.values()) if supports_patterns_arg else len(warnings)
    fixable_count = len(categorized['fixable'])
    unknown_count = len(categorized['unknown'])
    result = {
        'success': True,
        'total': total,
        'acceptable': len(categorized['acceptable']),
        'fixable': fixable_count,
        'unknown': unknown_count,
        'categorized': categorized,
    }
    print(json.dumps(result, indent=2))
    return 1 if fixable_count > 0 or unknown_count > 0 else 0
