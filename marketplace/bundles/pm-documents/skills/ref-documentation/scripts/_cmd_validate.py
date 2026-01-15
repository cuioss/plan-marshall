#!/usr/bin/env python3
"""Validate subcommand for AsciiDoc compliance checking."""

import fnmatch
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from plan_logging import log_entry  # type: ignore[import-not-found]

# Exit codes
EXIT_SUCCESS = 0
EXIT_NON_COMPLIANT = 1
EXIT_ERROR = 2

# Required attributes for AsciiDoc files
REQUIRED_ATTRS = [
    '= ',
    ':toc: left',
    ':toclevels: 3',
    ':toc-title: Table of Contents',
    ':sectnums:',
    ':source-highlighter: highlight.js',
]


def check_list_formatting(content: str) -> list[tuple[int, str, str]]:
    """Check for list formatting issues."""
    lines: list[str] = content.split('\n')
    issues: list[tuple[int, str, str]] = []
    in_code_block = False
    prev_was_blank = True
    in_list = False
    prev_line = ''

    for i, line in enumerate(lines, start=1):
        if line == '----':
            in_code_block = not in_code_block
        current_is_blank = len(line.strip()) == 0

        starts_new_list = False
        list_type = ''
        if not in_code_block:
            if re.match(r'^[\*\-\+] ', line):
                starts_new_list, list_type = True, 'unordered'
            elif re.match(r'^[0-9]+\. ', line):
                starts_new_list, list_type = True, 'ordered'
            elif re.match(r'^[^:]+::', line):
                starts_new_list, list_type = True, 'definition'
            elif re.match(r'^\. ', line) and not in_list:
                starts_new_list, list_type = True, 'numbered'

        continuing_list = False
        if not in_code_block and in_list:
            if (
                re.match(r'^[\*\-\+] ', line)
                or re.match(r'^\*\* ', line)
                or re.match(r'^[0-9]+\. ', line)
                or re.match(r'^\. ', line)
                or current_is_blank
            ):
                continuing_list = True

        if starts_new_list and not prev_was_blank and i > 1 and not in_list:
            issues.append((i, list_type, prev_line[:50]))

        if starts_new_list:
            in_list = True
        elif not continuing_list and not current_is_blank:
            in_list = False

        prev_line = line
        prev_was_blank = current_is_blank

    return issues


def check_file_compliance(file_path: Path) -> dict[str, Any]:
    """Check a single AsciiDoc file for compliance."""
    content = file_path.read_text(encoding='utf-8')
    result: dict[str, Any] = {
        'file': str(file_path),
        'compliant': True,
        'errors': 0,
        'warnings': 0,
        'issues': [],
        'missing_attrs': [],
        'list_issues': [],
        'xref_count': 0,
    }

    for attr in REQUIRED_ATTRS:
        if attr not in content:
            result['missing_attrs'].append(attr)
            result['issues'].append({'type': 'missing_header', 'severity': 'error', 'attribute': attr})
            result['errors'] += 1
            result['compliant'] = False

    list_issues = check_list_formatting(content)
    if list_issues:
        result['list_issues'] = list_issues
        for line_num, list_type, context in list_issues:
            result['issues'].append(
                {
                    'type': 'list_formatting',
                    'severity': 'warning',
                    'line': line_num,
                    'list_type': list_type,
                    'context': context,
                }
            )
        result['warnings'] += len(list_issues)
        result['compliant'] = False

    xref_count = len(re.findall(r'<<.*\.adoc.*>>', content))
    if xref_count > 0:
        result['xref_count'] = xref_count
        result['issues'].append({'type': 'deprecated_xref', 'severity': 'warning', 'count': xref_count})
        result['warnings'] += xref_count
        result['compliant'] = False

    return result


def cmd_validate(args: Any) -> int:
    """Handle validate subcommand."""
    check_path = Path(args.path)

    if not check_path.exists():
        if args.format == 'json':
            print(json.dumps({'error': 'Path not found', 'path': str(check_path)}))
        else:
            print(f"Error: Path '{check_path}' does not exist.")
        return EXIT_ERROR

    results: list[dict[str, Any]] = []
    if check_path.is_file():
        adoc_files = [check_path] if check_path.suffix == '.adoc' else []
    else:
        adoc_files = sorted(check_path.rglob('*.adoc'))

    ignore_patterns: list[str] = args.ignore_patterns or ['asciidoc-standards.adoc']
    for file_path in adoc_files:
        if any(fnmatch.fnmatch(file_path.name, p) for p in ignore_patterns):
            continue
        results.append(check_file_compliance(file_path))

    summary: dict[str, int] = {
        'total_files': len(results),
        'non_compliant_files': sum(1 for r in results if not r['compliant']),
        'compliant_files': sum(1 for r in results if r['compliant']),
        'total_errors': sum(r['errors'] for r in results),
        'total_warnings': sum(r['warnings'] for r in results),
    }

    if summary['non_compliant_files'] > 0:
        log_entry(
            'script',
            'global',
            'INFO',
            f'[DOCS-VALIDATE] Found {summary["non_compliant_files"]} non-compliant files ({summary["total_errors"]} errors, {summary["total_warnings"]} warnings)',
        )

    if args.format == 'json':
        output = {
            'directory': str(check_path),
            'timestamp': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'summary': summary,
            'files': [r for r in results if not r['compliant']],
        }
        print(json.dumps(output, indent=2))
    else:
        print(
            f'Summary: {summary["total_files"]} files, {summary["non_compliant_files"]} non-compliant, {summary["total_errors"]} errors, {summary["total_warnings"]} warnings'
        )

    return EXIT_NON_COMPLIANT if summary['total_errors'] > 0 or summary['total_warnings'] > 0 else EXIT_SUCCESS
