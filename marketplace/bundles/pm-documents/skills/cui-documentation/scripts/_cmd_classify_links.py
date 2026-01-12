#!/usr/bin/env python3
"""Classify-links subcommand for categorizing broken links."""

import json
import sys
from pathlib import Path
from typing import Any, Dict

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 2


def categorize_broken_link(issue: Dict[str, Any]) -> str:
    """Categorize a broken link issue."""
    link = issue.get('link', '')
    if link.startswith('<<') or '#' in link:
        return 'likely-false-positive'
    if any(p in link.lower() for p in ['localhost', '127.0.0.1', '0.0.0.0']):
        return 'likely-false-positive'
    if link.startswith('file://'):
        return 'likely-false-positive'
    if any(g in link for g in ['target/', 'build/', 'dist/']):
        return 'likely-false-positive'
    if link.startswith('http://') or link.startswith('https://'):
        return 'must-verify-manual'
    return 'must-verify-manual'


def cmd_classify_links(args):
    """Handle classify-links subcommand."""
    try:
        if args.input:
            with open(args.input, 'r') as f:
                input_data = json.load(f)
        else:
            input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return EXIT_ERROR

    issues = input_data.get('issues', input_data.get('data', {}).get('issues', []))
    categorized = {'likely-false-positive': [], 'must-verify-manual': [], 'definitely-broken': []}

    for issue in issues:
        category = categorize_broken_link(issue)
        issue['category'] = category
        categorized[category].append(issue)

    result = {
        'summary': {'total_issues': len(issues), 'likely_false_positive_count': len(categorized['likely-false-positive']), 'must_verify_manual_count': len(categorized['must-verify-manual']), 'definitely_broken_count': len(categorized['definitely-broken'])},
        'categorized_issues': categorized
    }

    output_json = json.dumps(result, indent=2 if args.pretty else None)
    if args.output:
        Path(args.output).write_text(output_json)
    else:
        print(output_json)

    return EXIT_SUCCESS
