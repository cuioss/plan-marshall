#!/usr/bin/env python3
"""Check-warnings subcommand for Maven — thin wrapper over shared classifier."""

import json
import sys

from _warnings_classify import categorize_warnings, flatten_patterns


def cmd_check_warnings(args):
    """Handle check-warnings subcommand."""
    warnings, patterns = None, []

    if args.warnings:
        try:
            warnings = json.loads(args.warnings)
        except json.JSONDecodeError as e:
            print(json.dumps({'success': False, 'error': f'Invalid JSON in --warnings: {e}'}, indent=2))
            return 1
        if args.patterns:
            try:
                patterns = json.loads(args.patterns)
            except json.JSONDecodeError as e:
                print(json.dumps({'success': False, 'error': f'Invalid JSON in --patterns: {e}'}, indent=2))
                return 1
        elif args.acceptable_warnings:
            try:
                patterns = flatten_patterns(json.loads(args.acceptable_warnings))
            except json.JSONDecodeError as e:
                print(json.dumps({'success': False, 'error': f'Invalid JSON in --acceptable-warnings: {e}'}, indent=2))
                return 1
    else:
        if sys.stdin.isatty():
            print(json.dumps({'success': False, 'error': 'No input provided. Use --warnings/--patterns or pipe JSON to stdin.'}, indent=2))
            return 1
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(json.dumps({'success': False, 'error': f'Invalid JSON from stdin: {e}'}, indent=2))
            return 1
        warnings = input_data.get('warnings', [])
        patterns = input_data.get('patterns', []) or flatten_patterns(input_data.get('acceptable_warnings', {}))

    if warnings is None or not isinstance(warnings, list):
        print(json.dumps({'success': False, 'error': 'warnings must be an array'}, indent=2))
        return 1

    categorized = categorize_warnings(warnings, patterns, matcher='substring', filter_severity='WARNING')
    result = {
        'success': True,
        'total': sum(len(v) for v in categorized.values()),
        'acceptable': len(categorized['acceptable']),
        'fixable': len(categorized['fixable']),
        'unknown': len(categorized['unknown']),
        'categorized': categorized,
    }
    print(json.dumps(result, indent=2))
    return 1 if result['fixable'] > 0 or result['unknown'] > 0 else 0
