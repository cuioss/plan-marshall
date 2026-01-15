#!/usr/bin/env python3
"""Analyze-tone subcommand for detecting promotional language."""

import json
import re
import sys
from pathlib import Path

from plan_logging import log_entry  # type: ignore[import-not-found]

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 2

# Promotional language patterns
PROMOTIONAL_PATTERNS = [
    (r'\b(best|greatest|ultimate|perfect|ideal)\b', 'superlative'),
    (r'\b(leading|top|premier|superior)\b', 'comparative_superlative'),
    (r'\b(enterprise-grade|production-ready|industry-leading|world-class)\b', 'buzzword'),
    (r'\b(powerful|robust|elegant|beautiful|amazing|awesome)\b', 'subjective'),
]

# Performance claim patterns
PERFORMANCE_PATTERNS = [
    r'\b(faster|slower|quicker)\s+than\b',
    r'\b\d+x\s+(faster|slower|more|less)\b',
    r'\b(sub-millisecond|millisecond|nanosecond)\b',
]


def cmd_analyze_tone(args):
    """Handle analyze-tone subcommand."""
    if not args.file and not args.directory:
        print('Error: --file or --directory required', file=sys.stderr)
        return EXIT_ERROR

    all_issues = []

    def analyze_file(file_path: str):
        with open(file_path, encoding='utf-8') as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            if line.strip().startswith(('----', '....', '//', ':', '=')):
                continue

            for pattern, category in PROMOTIONAL_PATTERNS:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    all_issues.append(
                        {
                            'file': file_path,
                            'line': line_num,
                            'text': match.group(0),
                            'category': 'promotional',
                            'subcategory': category,
                        }
                    )

            for pattern in PERFORMANCE_PATTERNS:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    all_issues.append(
                        {'file': file_path, 'line': line_num, 'text': match.group(0), 'category': 'performance_claim'}
                    )

    if args.file:
        analyze_file(args.file)
    else:
        for f in Path(args.directory).glob('*.adoc'):
            if 'target' not in f.parts:
                analyze_file(str(f))

    promotional_count = len([i for i in all_issues if i['category'] == 'promotional'])
    perf_count = len([i for i in all_issues if i['category'] == 'performance_claim'])

    if all_issues:
        log_entry(
            'script',
            'global',
            'INFO',
            f'[DOCS-TONE] Found {len(all_issues)} issues ({promotional_count} promotional, {perf_count} performance claims)',
        )

    result = {
        'summary': {
            'total_issues': len(all_issues),
            'promotional_count': promotional_count,
            'performance_claim_count': perf_count,
        },
        'all_issues': all_issues,
    }

    output_json = json.dumps(result, indent=2 if args.pretty else None)
    if args.output:
        Path(args.output).write_text(output_json)
    else:
        print(output_json)

    return EXIT_SUCCESS
