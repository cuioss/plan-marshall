#!/usr/bin/env python3
"""Tests for Maven coverage-report subcommand."""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

from conftest import get_script_path, run_script  # noqa: E402

SCRIPT_PATH = get_script_path('plan-marshall', 'build-maven', 'maven.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures' / 'coverage'


def test_coverage_report_high_coverage():
    """Test coverage-report with report above threshold."""
    result = run_script(
        SCRIPT_PATH, 'coverage-report',
        '--report-path', str(FIXTURES_DIR / 'high-coverage.xml'),
        '--threshold', '80',
    )
    assert result.success, f'Script failed: {result.stderr}'

    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['passed'] is True
    assert float(data['overall']['line']) > 80


def test_coverage_report_low_coverage():
    """Test coverage-report with report below threshold."""
    result = run_script(
        SCRIPT_PATH, 'coverage-report',
        '--report-path', str(FIXTURES_DIR / 'low-coverage.xml'),
        '--threshold', '80',
    )
    # Exit code 1 for failed threshold
    assert not result.success

    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['passed'] is False
    assert 'below threshold' in data['message']


def test_coverage_report_low_coverage_classes():
    """Test that low-coverage classes are identified."""
    result = run_script(
        SCRIPT_PATH, 'coverage-report',
        '--report-path', str(FIXTURES_DIR / 'low-coverage.xml'),
        '--threshold', '80',
    )
    data = parse_toon(result.stdout)
    assert 'low_coverage' in data
    assert len(data['low_coverage']) > 0

    # The low-coverage fixture has LegacyService with ~18.75% line coverage
    class_names = [entry['class'] for entry in data['low_coverage']]
    assert any('LegacyService' in c for c in class_names)


def test_coverage_report_missing_file():
    """Test coverage-report with non-existent report."""
    result = run_script(
        SCRIPT_PATH, 'coverage-report',
        '--report-path', '/nonexistent/jacoco.xml',
    )
    assert not result.success

    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert data['error'] == 'report_not_found'


def test_coverage_report_custom_threshold():
    """Test coverage-report with custom threshold that passes."""
    result = run_script(
        SCRIPT_PATH, 'coverage-report',
        '--report-path', str(FIXTURES_DIR / 'low-coverage.xml'),
        '--threshold', '10',
    )
    assert result.success, f'Script failed: {result.stderr}'

    data = parse_toon(result.stdout)
    assert data['passed'] is True
    assert str(data['threshold']) == '10'
