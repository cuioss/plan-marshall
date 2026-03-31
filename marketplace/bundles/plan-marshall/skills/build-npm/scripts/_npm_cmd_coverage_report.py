#!/usr/bin/env python3
"""Coverage-report subcommand — parse JavaScript coverage reports into structured TOON output.

Supports Jest/Istanbul JSON (coverage-summary.json) and LCOV formats.
Outputs TOON with pass/fail threshold evaluation.
"""

from pathlib import Path

from js_coverage import parse_json_coverage, parse_lcov_coverage  # type: ignore[import-not-found]
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# Standard coverage report locations (tried in order)
COVERAGE_REPORT_PATHS = [
    ('coverage/coverage-summary.json', 'json'),
    ('coverage/lcov.info', 'lcov'),
    ('dist/coverage/coverage-summary.json', 'json'),
]


def _find_report(project_path: str | None, report_path: str | None) -> tuple[Path | None, str]:
    """Find coverage report file and detect format."""
    if report_path:
        p = Path(report_path)
        if not p.is_file():
            return None, 'unknown'
        fmt = 'lcov' if p.suffix == '.info' else 'json'
        return p, fmt

    base = Path(project_path) if project_path else Path('.')
    for candidate, fmt in COVERAGE_REPORT_PATHS:
        p = base / candidate
        if p.is_file():
            return p, fmt
    return None, 'unknown'


def parse_coverage_report(report_file: Path, report_format: str, threshold: int = 80) -> dict:
    """Parse JS coverage report and return structured data with pass/fail."""
    if report_format == 'json':
        data = parse_json_coverage(str(report_file))
    elif report_format == 'lcov':
        data = parse_lcov_coverage(str(report_file))
    else:
        return {
            'status': 'error',
            'error': 'unsupported_format',
            'message': f'Unsupported report format: {report_format}',
        }

    overall = data.get('overall', {})
    line_pct = round(overall.get('line_coverage', 0), 2)
    branch_pct = round(overall.get('branch_coverage', 0), 2)
    function_pct = round(overall.get('function_coverage', 0), 2)
    statement_pct = round(overall.get('statement_coverage', 0), 2)

    # Identify low-coverage files
    low_coverage = []
    for file_data in data.get('by_file', []):
        file_line_pct = file_data.get('line_coverage', 0)
        if file_line_pct < threshold:
            low_coverage.append({
                'file': file_data['file'],
                'line_pct': round(file_line_pct, 2),
                'branch_pct': round(file_data.get('branch_coverage', 0), 2),
            })

    passed = line_pct >= threshold
    if passed:
        message = f'Coverage meets threshold: {line_pct}% line, {branch_pct}% branch'
    else:
        message = f'Coverage below threshold: {line_pct}% line (threshold: {threshold}%)'

    return {
        'status': 'success',
        'passed': passed,
        'threshold': threshold,
        'message': message,
        'overall': {
            'line': line_pct,
            'branch': branch_pct,
            'function': function_pct,
            'statement': statement_pct,
        },
        'low_coverage': low_coverage,
    }


def cmd_coverage_report(args) -> int:
    """Handle coverage-report subcommand."""
    report_file, report_format = _find_report(
        getattr(args, 'project_path', None),
        getattr(args, 'report_path', None),
    )

    if not report_file:
        result = {
            'status': 'error',
            'error': 'report_not_found',
            'message': 'No coverage report found. Run tests with coverage first.',
            'searched': [p for p, _ in COVERAGE_REPORT_PATHS],
        }
        print(serialize_toon(result))
        return 1

    threshold = getattr(args, 'threshold', 80) or 80
    result = parse_coverage_report(report_file, report_format, threshold)
    print(serialize_toon(result))
    return 0 if result.get('passed', False) else 1
