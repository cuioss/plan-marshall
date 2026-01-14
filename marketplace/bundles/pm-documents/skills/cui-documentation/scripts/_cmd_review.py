#!/usr/bin/env python3
"""Review subcommand for analyzing content quality issues."""

import json
import re
import sys
from pathlib import Path
from typing import Any

from plan_logging import log_entry  # type: ignore[import-not-found]

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 2

# Marketing language patterns
MARKETING_PATTERNS = [
    (r'\b(amazing|incredible|revolutionary|magical|awesome)\b', 'promotional_adjective'),
    (r'\b(powerful|robust|enterprise-grade|world-class|best-in-class)\b', 'qualification_buzzword'),
    (r'\b(blazing[-\s]?fast|lightning[-\s]?fast|ultra[-\s]?fast)\b', 'performance_buzzword'),
]

# Completeness patterns
COMPLETENESS_PATTERNS = [
    (r'^\s*(\*\s*)?TODO:?\s', 'todo_marker'),
    (r'^\s*(\*\s*)?FIXME:?\s', 'fixme_marker'),
    (r'\bwork\s+in\s+progress\b', 'wip_text'),
    (r'\bcoming\s+soon\b', 'placeholder_text'),
]


def analyze_content_line(line: str, line_number: int, file_path: str) -> list[dict[str, Any]]:
    """Analyze a single line for content issues."""
    issues = []

    for pattern, issue_type in MARKETING_PATTERNS:
        for match in re.finditer(pattern, line, re.IGNORECASE):
            issues.append({'file': file_path, 'line': line_number, 'type': 'tone', 'subtype': issue_type, 'severity': 'high', 'text': match.group(), 'message': f"Marketing language: '{match.group()}'"})

    for pattern, issue_type in COMPLETENESS_PATTERNS:
        for match in re.finditer(pattern, line, re.IGNORECASE):
            issues.append({'file': file_path, 'line': line_number, 'type': 'completeness', 'subtype': issue_type, 'severity': 'high', 'text': match.group(), 'message': f"Completeness issue: {issue_type}"})

    return issues


def cmd_review(args):
    """Handle review subcommand."""
    if not args.file and not args.directory:
        print("Error: --file or --directory required", file=sys.stderr)
        return EXIT_ERROR

    results = []
    paths = [Path(args.file)] if args.file else list(Path(args.directory).glob('**/*.adoc' if args.recursive else '*.adoc'))

    for file_path in paths:
        if 'target' in file_path.parts or not file_path.exists():
            continue

        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        all_issues = []
        in_code_block = False

        for line_num, line in enumerate(lines, 1):
            if line.strip().startswith('----'):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            all_issues.extend(analyze_content_line(line, line_num, str(file_path)))

        results.append({'file': str(file_path), 'issues': all_issues, 'issue_count': len(all_issues)})

    all_issues = [i for r in results for i in r['issues']]
    tone_count = len([i for i in all_issues if i['type'] == 'tone'])
    completeness_count = len([i for i in all_issues if i['type'] == 'completeness'])

    if all_issues:
        log_entry('script', 'global', 'INFO', f'[DOCS-REVIEW] Found {len(all_issues)} issues ({tone_count} tone, {completeness_count} completeness)')

    output = {
        'status': 'success',
        'data': {'files_analyzed': len(results), 'total_issues': len(all_issues), 'issues': all_issues},
        'metrics': {'tone_issues': tone_count, 'completeness_issues': completeness_count}
    }

    output_json = json.dumps(output, indent=2)
    if args.output:
        Path(args.output).write_text(output_json)
    else:
        print(output_json)

    return EXIT_SUCCESS
