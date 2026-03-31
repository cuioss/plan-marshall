#!/usr/bin/env python3
"""Coverage-report subcommand — parse coverage.py XML reports (Cobertura format) into TOON output."""

import xml.etree.ElementTree as ET
from pathlib import Path

from toon_parser import serialize_toon  # type: ignore[import-not-found]

# Standard coverage report locations (tried in order)
COVERAGE_REPORT_PATHS = [
    'coverage.xml',
    'htmlcov/coverage.xml',
]


def _find_report(project_path: str | None, report_path: str | None) -> Path | None:
    """Find coverage.py XML report file."""
    if report_path:
        p = Path(report_path)
        return p if p.is_file() else None

    base = Path(project_path) if project_path else Path('.')
    for candidate in COVERAGE_REPORT_PATHS:
        p = base / candidate
        if p.is_file():
            return p
    return None


def parse_cobertura_xml(report_file: Path, threshold: int = 80) -> dict:
    """Parse Cobertura XML report (coverage.py output) and return structured data."""
    tree = ET.parse(report_file)  # noqa: S314
    root = tree.getroot()

    # Overall coverage from root attributes
    line_rate = float(root.get('line-rate', '0'))
    branch_rate = float(root.get('branch-rate', '0'))

    overall = {
        'line': round(line_rate * 100, 2),
        'branch': round(branch_rate * 100, 2),
    }

    # Per-class analysis for low coverage detection
    low_coverage = []
    for package in root.findall('.//package'):
        for cls in package.findall('.//class'):
            cls_name = cls.get('name', '')
            cls_filename = cls.get('filename', '')
            cls_line_rate = float(cls.get('line-rate', '0'))
            cls_pct = round(cls_line_rate * 100, 2)

            if cls_pct < threshold:
                # Find uncovered methods
                uncovered_methods = []
                for method in cls.findall('methods/method'):
                    m_line_rate = float(method.get('line-rate', '0'))
                    if m_line_rate == 0:
                        uncovered_methods.append(method.get('name', ''))

                low_coverage.append({
                    'class': cls_name,
                    'file': cls_filename,
                    'line_pct': cls_pct,
                    'missed_methods': ','.join(uncovered_methods) if uncovered_methods else '-',
                })

    passed = overall['line'] >= threshold
    if passed:
        message = f"Coverage meets threshold: {overall['line']}% line, {overall['branch']}% branch"
    else:
        message = f"Coverage below threshold: {overall['line']}% line (threshold: {threshold}%)"

    return {
        'status': 'success',
        'passed': passed,
        'threshold': threshold,
        'message': message,
        'overall': overall,
        'low_coverage': low_coverage,
    }


def cmd_coverage_report(args) -> int:
    """Handle coverage-report subcommand."""
    report_file = _find_report(
        getattr(args, 'project_path', None),
        getattr(args, 'report_path', None),
    )

    if not report_file:
        result = {
            'status': 'error',
            'error': 'report_not_found',
            'message': 'No coverage.py XML report found. Run pytest with --cov --cov-report=xml first.',
            'searched': COVERAGE_REPORT_PATHS,
        }
        print(serialize_toon(result))
        return 1

    threshold = getattr(args, 'threshold', 80) or 80
    result = parse_cobertura_xml(report_file, threshold)
    print(serialize_toon(result))
    return 0 if result.get('passed', False) else 1
