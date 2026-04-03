#!/usr/bin/env python3
"""Tests for Gradle coverage-report subcommand.

Uses shared build_test_helpers for common coverage test patterns.
Uses the same JaCoCo XML format as Maven - the coverage parser is shared.
"""

from pathlib import Path

from build_test_helpers import (
    assert_coverage_custom_threshold,
    assert_coverage_has_low_items,
    assert_coverage_high,
    assert_coverage_low,
    assert_coverage_missing_file,
)
from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'build-gradle', 'gradle.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures' / 'coverage'


def test_coverage_report_high_coverage():
    """Test coverage-report with report above threshold."""
    assert_coverage_high(SCRIPT_PATH, FIXTURES_DIR / 'high-coverage.xml')


def test_coverage_report_low_coverage():
    """Test coverage-report with report below threshold."""
    assert_coverage_low(SCRIPT_PATH, FIXTURES_DIR / 'low-coverage.xml')


def test_coverage_report_low_coverage_classes():
    """Test that low-coverage classes are identified."""
    data = assert_coverage_has_low_items(SCRIPT_PATH, FIXTURES_DIR / 'low-coverage.xml')
    assert len(data['low_coverage']) > 0


def test_coverage_report_missing_file():
    """Test coverage-report with non-existent report."""
    assert_coverage_missing_file(SCRIPT_PATH)


def test_coverage_report_custom_threshold():
    """Test coverage-report with low threshold that passes on high-coverage report."""
    assert_coverage_custom_threshold(SCRIPT_PATH, FIXTURES_DIR / 'high-coverage.xml', threshold=60)
