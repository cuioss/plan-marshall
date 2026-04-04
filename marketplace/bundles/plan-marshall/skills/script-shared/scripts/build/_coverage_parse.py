#!/usr/bin/env python3
"""Format-agnostic coverage report parsing with pluggable format adapters.

Provides a single entry point ``parse_coverage_report`` that delegates to
format-specific adapters (JaCoCo XML, Cobertura XML, LCOV, Jest/Istanbul JSON).
Shared logic for low-coverage detection, threshold checking, and result
formatting lives here so each build skill only needs a thin wrapper.

Supported formats:
    jacoco     - JaCoCo XML (Maven/Gradle)
    cobertura  - Cobertura XML (coverage.py)
    lcov       - LCOV text format
    jest_json  - Jest/Istanbul coverage-summary.json
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# =============================================================================
# Public API
# =============================================================================


def parse_coverage_report(
    report_file: str | Path,
    fmt: str,
    threshold: int = 80,
) -> dict[str, Any]:
    """Parse a coverage report and return structured results.

    Args:
        report_file: Path to the coverage report file.
        fmt: Format identifier - one of 'jacoco', 'cobertura', 'lcov', 'jest_json'.
        threshold: Minimum line coverage percentage to pass (default 80).

    Returns:
        dict with keys: status, passed, threshold, message, overall, low_coverage.
    """
    report_path = Path(report_file)
    if not report_path.is_file():
        return {
            'status': 'error',
            'error': 'report_not_found',
            'message': f'Report file not found: {report_file}',
        }

    adapter = _ADAPTERS.get(fmt)
    if adapter is None:
        return {
            'status': 'error',
            'error': 'unsupported_format',
            'message': f'Unsupported format: {fmt}. Supported: {", ".join(sorted(_ADAPTERS))}',
        }

    overall, items = adapter(report_path)
    low_coverage = _detect_low_coverage(items, threshold)
    passed = overall.get('line', 0) >= threshold

    if passed:
        branch = overall.get('branch', 0)
        message = f'Coverage meets threshold: {overall["line"]}% line, {branch}% branch'
    else:
        message = f'Coverage below threshold: {overall["line"]}% line (threshold: {threshold}%)'

    return {
        'status': 'success',
        'passed': passed,
        'threshold': threshold,
        'message': message,
        'overall': overall,
        'low_coverage': low_coverage,
    }


def find_report(
    search_paths: list[tuple[str, str]],
    base_path: str | None = None,
    explicit_path: str | None = None,
) -> tuple[Path | None, str]:
    """Find a coverage report file from candidate paths.

    Args:
        search_paths: List of (relative_path, format) tuples to try in order.
        base_path: Base directory to resolve relative paths against (default '.').
        explicit_path: If provided, use this path directly (format auto-detected from extension).

    Returns:
        Tuple of (report_path_or_None, format_string).
    """
    if explicit_path:
        p = Path(explicit_path)
        if not p.is_file():
            return None, 'unknown'
        # Auto-detect format from extension
        fmt = _detect_format(p)
        return p, fmt

    base = Path(base_path) if base_path else Path('.')
    for candidate, fmt in search_paths:
        p = base / candidate
        if p.is_file():
            return p, fmt
    return None, 'unknown'


# =============================================================================
# JaCoCo XML Adapter (Maven / Gradle)
# =============================================================================


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


def _parse_jacoco(report_file: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Parse JaCoCo XML report.

    Returns:
        Tuple of (overall_metrics, per_item_list) where per_item_list contains
        dicts with 'name' and 'line_pct' (and optional 'detail').
    """
    tree = ET.parse(report_file)  # noqa: S314
    root = tree.getroot()

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

    items: list[dict[str, Any]] = []
    for package in root.findall('.//package'):
        for cls in package.findall('class'):
            cls_name = cls.get('name', '').replace('/', '.')
            cls_line_m, cls_line_c = _get_counter(cls, 'LINE')
            cls_pct = _calc_pct(cls_line_m, cls_line_c)

            uncovered_methods = []
            for method in cls.findall('method'):
                m_name = method.get('name', '')
                if m_name in ('<init>', '<clinit>'):
                    continue
                m_missed, _ = _get_counter(method, 'METHOD')
                if m_missed > 0:
                    uncovered_methods.append(m_name)

            items.append(
                {
                    'name': cls_name,
                    'line_pct': cls_pct,
                    'detail': ','.join(uncovered_methods) if uncovered_methods else '-',
                    'detail_label': 'missed_methods',
                }
            )

    return overall, items


# =============================================================================
# Cobertura XML Adapter (coverage.py / Python)
# =============================================================================


def _parse_cobertura(report_file: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Parse Cobertura XML report (coverage.py output)."""
    tree = ET.parse(report_file)  # noqa: S314
    root = tree.getroot()

    line_rate = float(root.get('line-rate', '0'))
    branch_rate = float(root.get('branch-rate', '0'))

    overall = {
        'line': round(line_rate * 100, 2),
        'branch': round(branch_rate * 100, 2),
    }

    items: list[dict[str, Any]] = []
    for package in root.findall('.//package'):
        for cls in package.findall('.//class'):
            cls_name = cls.get('name', '')
            cls_filename = cls.get('filename', '')
            cls_line_rate = float(cls.get('line-rate', '0'))
            cls_pct = round(cls_line_rate * 100, 2)

            uncovered_methods = []
            for method in cls.findall('methods/method'):
                m_line_rate = float(method.get('line-rate', '0'))
                if m_line_rate == 0:
                    uncovered_methods.append(method.get('name', ''))

            items.append(
                {
                    'name': cls_name,
                    'file': cls_filename,
                    'line_pct': cls_pct,
                    'detail': ','.join(uncovered_methods) if uncovered_methods else '-',
                    'detail_label': 'missed_methods',
                }
            )

    return overall, items


# =============================================================================
# LCOV Adapter
# =============================================================================


def _parse_lcov(report_file: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Parse LCOV format coverage report."""
    content = report_file.read_text(encoding='utf-8')

    files_data: list[dict[str, Any]] = []
    current_file: str | None = None
    current_data: dict[str, Any] = {}

    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('SF:'):
            current_file = line[3:]
            current_data = {
                'file': current_file,
                'lines_found': 0,
                'lines_hit': 0,
                'functions_found': 0,
                'functions_hit': 0,
                'branches_found': 0,
                'branches_hit': 0,
            }
        elif line.startswith('LF:'):
            current_data['lines_found'] = int(line[3:])
        elif line.startswith('LH:'):
            current_data['lines_hit'] = int(line[3:])
        elif line.startswith('FNF:'):
            current_data['functions_found'] = int(line[4:])
        elif line.startswith('FNH:'):
            current_data['functions_hit'] = int(line[4:])
        elif line.startswith('BRF:'):
            current_data['branches_found'] = int(line[4:])
        elif line.startswith('BRH:'):
            current_data['branches_hit'] = int(line[4:])
        elif line == 'end_of_record' and current_file:
            files_data.append(current_data)
            current_file = None

    total_lf = sum(f['lines_found'] for f in files_data)
    total_lh = sum(f['lines_hit'] for f in files_data)
    total_ff = sum(f['functions_found'] for f in files_data)
    total_fh = sum(f['functions_hit'] for f in files_data)
    total_bf = sum(f['branches_found'] for f in files_data)
    total_bh = sum(f['branches_hit'] for f in files_data)

    overall = {
        'line': round(total_lh / total_lf * 100, 2) if total_lf > 0 else 0.0,
        'branch': round(total_bh / total_bf * 100, 2) if total_bf > 0 else 0.0,
        'function': round(total_fh / total_ff * 100, 2) if total_ff > 0 else 0.0,
        'statement': round(total_lh / total_lf * 100, 2) if total_lf > 0 else 0.0,
    }

    items: list[dict[str, Any]] = []
    for f in files_data:
        lf = f['lines_found']
        lh = f['lines_hit']
        bf = f['branches_found']
        bh = f['branches_hit']
        items.append(
            {
                'name': f['file'],
                'line_pct': round(lh / lf * 100, 2) if lf > 0 else 0.0,
                'branch_pct': round(bh / bf * 100, 2) if bf > 0 else 0.0,
            }
        )

    return overall, items


# =============================================================================
# Jest/Istanbul JSON Adapter
# =============================================================================


def _parse_jest_json(report_file: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Parse Jest/Istanbul coverage-summary.json format."""
    with open(report_file, encoding='utf-8') as f:
        data = json.load(f)

    overall: dict[str, Any] = {}
    if 'total' in data:
        total = data['total']
        overall = {
            'line': round(total.get('lines', {}).get('pct', 0), 2),
            'branch': round(total.get('branches', {}).get('pct', 0), 2),
            'function': round(total.get('functions', {}).get('pct', 0), 2),
            'statement': round(total.get('statements', {}).get('pct', 0), 2),
        }

    items: list[dict[str, Any]] = []
    for file_path, coverage in data.items():
        if file_path == 'total':
            continue
        lines_data = coverage.get('lines', {})
        items.append(
            {
                'name': file_path,
                'line_pct': round(lines_data.get('pct', 0), 2),
                'branch_pct': round(coverage.get('branches', {}).get('pct', 0), 2),
            }
        )

    return overall, items


# =============================================================================
# Shared Low-Coverage Detection
# =============================================================================


def _detect_low_coverage(
    items: list[dict[str, Any]],
    threshold: int,
) -> list[dict[str, Any]]:
    """Filter items below threshold and format for output.

    Each adapter produces items with at least 'name' and 'line_pct'. Additional
    fields vary by format and are passed through to the output.
    """
    low: list[dict[str, Any]] = []
    for item in items:
        if item.get('line_pct', 0) >= threshold:
            continue

        entry: dict[str, Any] = {}
        # Map 'name' to the conventional key for the format
        detail_label = item.get('detail_label')
        if detail_label:
            # JaCoCo / Cobertura style: name=class, detail=missed_methods
            entry['class'] = item['name']
            if 'file' in item:
                entry['file'] = item['file']
            entry['line_pct'] = item['line_pct']
            entry['missed_methods'] = item.get('detail', '-')
        else:
            # LCOV / Jest style: name=file path
            entry['file'] = item['name']
            entry['line_pct'] = item['line_pct']
            if 'branch_pct' in item:
                entry['branch_pct'] = item['branch_pct']

        low.append(entry)

    return low


# =============================================================================
# Format Detection & Adapter Registry
# =============================================================================


def _detect_format(path: Path) -> str:
    """Auto-detect format from file extension."""
    suffix = path.suffix.lower()
    if suffix == '.info':
        return 'lcov'
    if suffix == '.json':
        return 'jest_json'
    if suffix == '.xml':
        # Peek at root element to distinguish JaCoCo vs Cobertura
        try:
            tree = ET.parse(path)  # noqa: S314
            root_tag = tree.getroot().tag
            if root_tag == 'report':
                return 'jacoco'
            if root_tag == 'coverage':
                return 'cobertura'
        except ET.ParseError:
            pass
    return 'unknown'


_ADAPTERS: dict[str, Any] = {
    'jacoco': _parse_jacoco,
    'cobertura': _parse_cobertura,
    'lcov': _parse_lcov,
    'jest_json': _parse_jest_json,
}
