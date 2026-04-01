#!/usr/bin/env python3
"""Check-warnings subcommand for Gradle — thin wrapper over shared classifier."""

import json
import sys

from _warnings_classify import categorize_warnings


def cmd_check_warnings(args):
    """Handle check-warnings subcommand."""
    warnings, acceptable_patterns = None, {}

    if args.warnings:
        try:
            warnings = json.loads(args.warnings)
        except json.JSONDecodeError as e:
            print(json.dumps({'success': False, 'error': f'Invalid warnings JSON: {e}'}, indent=2))
            return 1
        if args.acceptable_warnings:
            try:
                acceptable_patterns = json.loads(args.acceptable_warnings)
            except json.JSONDecodeError:
                pass
    else:
        if sys.stdin.isatty():
            print(json.dumps({'success': False, 'error': 'No input provided. Use --warnings or pipe JSON to stdin.'}, indent=2))
            return 1
        try:
            data = json.load(sys.stdin)
            warnings = data.get('warnings', [])
            acceptable_patterns = data.get('acceptable_warnings', {})
        except json.JSONDecodeError as e:
            print(json.dumps({'success': False, 'error': f'Invalid stdin JSON: {e}'}, indent=2))
            return 1

    if warnings is None or not isinstance(warnings, list):
        print(json.dumps({'success': False, 'error': 'warnings must be an array'}, indent=2))
        return 1

    categorized = categorize_warnings(warnings, acceptable_patterns, matcher='wildcard')
    result = {
        'success': True,
        'total': len(warnings),
        'acceptable': len(categorized['acceptable']),
        'fixable': len(categorized['fixable']),
        'unknown': len(categorized['unknown']),
        'categorized': categorized,
    }
    print(json.dumps(result, indent=2))
    return 1 if result['fixable'] > 0 or result['unknown'] > 0 else 0
