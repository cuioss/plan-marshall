#!/usr/bin/env python3
"""Tests for npm coverage-report subcommand."""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from conftest import get_script_path, run_script
from toon_parser import parse_toon  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'build-npm', 'npm.py')
FIXTURES_DIR = Path(__file__).parent / 'coverage'


def test_coverage_report_json_format():
    """Test coverage-report with JSON coverage-summary."""
    result = run_script(
        SCRIPT_PATH, 'coverage-report',
        '--report-path', str(FIXTURES_DIR / 'coverage-summary.json'),
        '--threshold', '80',
    )
    # 70% line coverage < 80% threshold → exit code 1
    assert not result.success

    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['passed'] is False
    assert 'below threshold' in data['message']


def test_coverage_report_high_coverage():
    """Test coverage-report with high coverage JSON."""
    result = run_script(
        SCRIPT_PATH, 'coverage-report',
        '--report-path', str(FIXTURES_DIR / 'high-coverage.json'),
        '--threshold', '80',
    )
    assert result.success, f'Script failed: {result.stderr}'

    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['passed'] is True


def test_coverage_report_low_coverage_files():
    """Test that low-coverage files are identified."""
    result = run_script(
        SCRIPT_PATH, 'coverage-report',
        '--report-path', str(FIXTURES_DIR / 'coverage-summary.json'),
        '--threshold', '80',
    )
    data = parse_toon(result.stdout)
    assert 'low_coverage' in data
    assert len(data['low_coverage']) > 0

    # Button.js has 50% coverage — should be flagged
    files = [entry['file'] for entry in data['low_coverage']]
    assert any('Button' in f for f in files)


def test_coverage_report_lcov_format():
    """Test coverage-report with LCOV format."""
    result = run_script(
        SCRIPT_PATH, 'coverage-report',
        '--report-path', str(FIXTURES_DIR / 'lcov.info'),
        '--threshold', '50',
    )
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert 'overall' in data


def test_coverage_report_missing_file():
    """Test coverage-report with non-existent report."""
    result = run_script(
        SCRIPT_PATH, 'coverage-report',
        '--report-path', '/nonexistent/coverage.json',
    )
    assert not result.success

    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert data['error'] == 'report_not_found'
