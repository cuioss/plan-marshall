#!/usr/bin/env python3
"""Coverage-report subcommand — parse JaCoCo XML reports into structured TOON output.

Reuses the Maven JaCoCo parser (same XML format) but with Gradle-specific report locations.
"""

from pathlib import Path

from _maven_cmd_coverage_report import JACOCO_REPORT_PATHS as _MAVEN_PATHS  # type: ignore[import-not-found]
from _maven_cmd_coverage_report import parse_jacoco_xml  # type: ignore[import-not-found]
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# Gradle JaCoCo report locations (tried in order, then fall back to Maven locations)
GRADLE_REPORT_PATHS = [
    'build/reports/jacoco/test/jacocoTestReport.xml',
    'build/reports/jacoco/jacocoTestReport.xml',
]


def _find_report(module_path: str | None, report_path: str | None) -> Path | None:
    """Find JaCoCo XML report file (Gradle locations first, then Maven fallback)."""
    if report_path:
        p = Path(report_path)
        return p if p.is_file() else None

    base = Path(module_path) if module_path else Path('.')
    for candidate in GRADLE_REPORT_PATHS + _MAVEN_PATHS:
        p = base / candidate
        if p.is_file():
            return p
    return None


def cmd_coverage_report(args) -> int:
    """Handle coverage-report subcommand."""
    report_file = _find_report(
        getattr(args, 'module_path', None),
        getattr(args, 'report_path', None),
    )

    if not report_file:
        result = {
            'status': 'error',
            'error': 'report_not_found',
            'message': 'No JaCoCo XML report found. Run coverage build first.',
            'searched': GRADLE_REPORT_PATHS + _MAVEN_PATHS,
        }
        print(serialize_toon(result))
        return 1

    threshold = getattr(args, 'threshold', 80) or 80
    result = parse_jacoco_xml(report_file, threshold)
    print(serialize_toon(result))
    return 0 if result.get('passed', False) else 1
