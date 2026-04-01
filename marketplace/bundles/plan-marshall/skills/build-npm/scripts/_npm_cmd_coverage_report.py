#!/usr/bin/env python3
"""Coverage-report subcommand -- thin wrapper delegating to shared _coverage_parse."""

from _coverage_parse import find_report, parse_coverage_report  # type: ignore[import-not-found]
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# Standard JS coverage report locations with format hints (tried in order)
NPM_SEARCH_PATHS = [
    ('coverage/coverage-summary.json', 'jest_json'),
    ('coverage/lcov.info', 'lcov'),
    ('dist/coverage/coverage-summary.json', 'jest_json'),
]


def cmd_coverage_report(args) -> int:
    """Handle coverage-report subcommand."""
    report_file, fmt = find_report(
        NPM_SEARCH_PATHS,
        base_path=getattr(args, 'project_path', None),
        explicit_path=getattr(args, 'report_path', None),
    )

    if not report_file:
        result = {
            'status': 'error',
            'error': 'report_not_found',
            'message': 'No coverage report found. Run tests with coverage first.',
            'searched': [p for p, _ in NPM_SEARCH_PATHS],
        }
        print(serialize_toon(result))
        return 1

    threshold = getattr(args, 'threshold', 80) or 80
    result = parse_coverage_report(report_file, fmt, threshold)
    print(serialize_toon(result))
    return 0 if result.get('passed', False) else 1
