#!/usr/bin/env python3
"""Tests for npm coverage-report subcommand.

Uses shared build_test_helpers for common patterns.
npm-specific: tests JSON and LCOV format support.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from build_test_helpers import (  # noqa: E402
    assert_coverage_has_low_items,
    assert_coverage_high,
    assert_coverage_missing_file,
)
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

from conftest import get_script_path, run_script  # noqa: E402

SCRIPT_PATH = get_script_path('plan-marshall', 'build-npm', 'npm.py')
FIXTURES_DIR = Path(__file__).parent / 'coverage'


def test_coverage_report_json_format():
    """Test coverage-report with JSON coverage-summary (npm-specific format)."""
    result = run_script(
        SCRIPT_PATH,
        'coverage-report',
        '--report-path',
        str(FIXTURES_DIR / 'coverage-summary.json'),
        '--threshold',
        '80',
    )
    assert not result.success

    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['passed'] is False
    assert 'below threshold' in data['message']


def test_coverage_report_high_coverage():
    """Test coverage-report with high coverage JSON."""
    assert_coverage_high(SCRIPT_PATH, FIXTURES_DIR / 'high-coverage.json')


def test_coverage_report_low_coverage_files():
    """Test that low-coverage files are identified."""
    data = assert_coverage_has_low_items(SCRIPT_PATH, FIXTURES_DIR / 'coverage-summary.json')
    files = [entry['file'] for entry in data['low_coverage']]
    assert any('Button' in f for f in files)


def test_coverage_report_lcov_format():
    """Test coverage-report with LCOV format (npm-specific)."""
    result = run_script(
        SCRIPT_PATH,
        'coverage-report',
        '--report-path',
        str(FIXTURES_DIR / 'lcov.info'),
        '--threshold',
        '50',
    )
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert 'overall' in data


def test_coverage_report_missing_file():
    """Test coverage-report with non-existent report."""
    assert_coverage_missing_file(SCRIPT_PATH)
