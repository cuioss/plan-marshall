#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for Gradle coverage-report subcommand.

The backend-invariant cases run through
``build_test_helpers.run_coverage_report_case``. Gradle uses the same JaCoCo XML
format as Maven — the coverage parser is shared — and its low-coverage variant is
count-only (no class-name check), which the shared ``low_items`` case already
covers, so no Gradle-specific case remains.
"""

from pathlib import Path

import pytest
from build_test_helpers import COVERAGE_REPORT_CASES, run_coverage_report_case

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'build-gradle', 'gradle.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures' / 'coverage'


@pytest.mark.parametrize('case', COVERAGE_REPORT_CASES)
def test_coverage_report_contract(case):
    """Gradle satisfies every backend-invariant coverage-report case."""
    run_coverage_report_case(
        case,
        SCRIPT_PATH,
        FIXTURES_DIR,
        custom_threshold_report='high-coverage.xml',
        custom_threshold=60,
    )
