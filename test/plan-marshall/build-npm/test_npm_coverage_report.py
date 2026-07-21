#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for npm coverage-report subcommand.

npm is the odd backend out: its fixtures live in ``coverage/`` (not
``fixtures/coverage/``) and its reports are Istanbul JSON and LCOV rather than
XML. Only the two format-agnostic cases (``missing_file``, ``high``) route
through ``build_test_helpers.run_coverage_report_case``; the JSON-summary,
LCOV, and low-coverage-file assertions are npm-specific and stay here.
"""

from pathlib import Path

import pytest
from build_test_helpers import assert_coverage_has_low_items, run_coverage_report_case
from toon_parser import parse_toon

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'build-npm', 'npm.py')
FIXTURES_DIR = Path(__file__).parent / 'coverage'

#: The subset of the shared contract npm's report formats support. The `low`
#: and `custom_threshold` cases are excluded: npm has no below-threshold XML
#: twin, and its below-threshold case is the JSON-summary test below.
NPM_COVERAGE_REPORT_CASES = ('missing_file', 'high')


@pytest.mark.parametrize('case', NPM_COVERAGE_REPORT_CASES)
def test_coverage_report_contract(case):
    """npm satisfies the format-agnostic coverage-report cases."""
    run_coverage_report_case(case, SCRIPT_PATH, FIXTURES_DIR, high_report='high-coverage.json')


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
