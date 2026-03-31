#!/usr/bin/env python3
"""Coverage-report subcommand — parse JaCoCo XML reports into structured TOON output."""

import xml.etree.ElementTree as ET
from pathlib import Path

from toon_parser import serialize_toon  # type: ignore[import-not-found]

# Standard JaCoCo report locations (tried in order)
JACOCO_REPORT_PATHS = [
    'target/site/jacoco/jacoco.xml',
    'target/jacoco/report.xml',
    'target/site/jacoco-aggregate/jacoco.xml',
]


def _calc_pct(missed: int, covered: int) -> float:
    """Calculate coverage percentage from missed/covered counters."""
    total = missed + covered
    return round(covered / total * 100, 2) if total > 0 else 0.0


def _get_counter(element: ET.Element, counter_type: str) -> tuple[int, int]:
    """Extract (missed, covered) for a counter type from an XML element."""
    for counter in element.findall('counter'):
        if counter.get('type') == counter_type:
            return int(counter.get('missed', '0')), int(counter.get('covered', '0'))
    return 0, 0


def _find_report(module_path: str | None, report_path: str | None) -> Path | None:
    """Find JaCoCo XML report file."""
    if report_path:
        p = Path(report_path)
        return p if p.is_file() else None

    base = Path(module_path) if module_path else Path('.')
    for candidate in JACOCO_REPORT_PATHS:
        p = base / candidate
        if p.is_file():
            return p
    return None


def parse_jacoco_xml(report_file: Path, threshold: int = 80) -> dict:
    """Parse JaCoCo XML report and return structured coverage data."""
    tree = ET.parse(report_file)  # noqa: S314
    root = tree.getroot()

    # Overall counters from report root
    line_m, line_c = _get_counter(root, 'LINE')
    branch_m, branch_c = _get_counter(root, 'BRANCH')
    instr_m, instr_c = _get_counter(root, 'INSTRUCTION')
    method_m, method_c = _get_counter(root, 'METHOD')

    overall = {
        'line': _calc_pct(line_m, line_c),
        'branch': _calc_pct(branch_m, branch_c),
        'instruction': _calc_pct(instr_m, instr_c),
        'method': _calc_pct(method_m, method_c),
    }

    # Per-class analysis for low coverage detection
    low_coverage = []
    for package in root.findall('.//package'):
        pkg_name = package.get('name', '').replace('/', '.')
        for cls in package.findall('class'):
            cls_name_raw = cls.get('name', '').replace('/', '.')
            cls_line_m, cls_line_c = _get_counter(cls, 'LINE')
            cls_pct = _calc_pct(cls_line_m, cls_line_c)

            if cls_pct < threshold:
                # Find uncovered methods
                uncovered_methods = []
                for method in cls.findall('method'):
                    m_name = method.get('name', '')
                    if m_name == '<init>' or m_name == '<clinit>':
                        continue
                    m_missed, m_covered = _get_counter(method, 'METHOD')
                    if m_missed > 0:
                        uncovered_methods.append(m_name)

                low_coverage.append({
                    'class': cls_name_raw,
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
        getattr(args, 'module_path', None),
        getattr(args, 'report_path', None),
    )

    if not report_file:
        result = {
            'status': 'error',
            'error': 'report_not_found',
            'message': 'No JaCoCo XML report found. Run coverage build first.',
            'searched': JACOCO_REPORT_PATHS,
        }
        print(serialize_toon(result))
        return 1

    threshold = getattr(args, 'threshold', 80) or 80
    result = parse_jacoco_xml(report_file, threshold)
    print(serialize_toon(result))
    return 0 if result.get('passed', False) else 1
