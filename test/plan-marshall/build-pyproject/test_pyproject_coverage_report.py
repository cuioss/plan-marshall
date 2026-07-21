#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for pyproject coverage-report subcommand.

The backend-invariant cases run through
``build_test_helpers.run_coverage_report_case``; the low-coverage class-name
check is pyproject-specific (it pins the Cobertura fixture's ``legacy`` entry)
and stays here.
"""

from pathlib import Path

import pytest
from build_test_helpers import (
    COVERAGE_REPORT_CASES,
    assert_coverage_has_low_items,
    run_coverage_report_case,
)

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'build-pyproject', 'pyproject_build.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures' / 'coverage'


@pytest.mark.parametrize('case', COVERAGE_REPORT_CASES)
def test_coverage_report_contract(case):
    """build-pyproject satisfies every backend-invariant coverage-report case."""
    run_coverage_report_case(
        case,
        SCRIPT_PATH,
        FIXTURES_DIR,
        custom_threshold_report='low-coverage.xml',
        custom_threshold=40,
    )


def test_coverage_report_low_coverage_classes():
    """The pyproject low-coverage report names the Cobertura fixture's legacy class."""
    data = assert_coverage_has_low_items(SCRIPT_PATH, FIXTURES_DIR / 'low-coverage.xml')
    class_names = [entry['class'] for entry in data['low_coverage']]
    assert any('legacy' in c for c in class_names)
