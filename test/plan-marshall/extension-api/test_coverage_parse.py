#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _coverage_parse.py shared coverage report parsing module."""

from pathlib import Path

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from _coverage_parse import find_report, parse_coverage_report

FIXTURES_DIR = Path(__file__).parent / 'fixtures' / 'coverage'


# =============================================================================
# Threshold verdict across every XML/JSON format
# =============================================================================


class TestThresholdVerdictAcrossFormats:
    """One threshold, every format: the high fixture passes and the low one fails.

    The three format-specific classes below own what each parser reads OUT of its
    own report shape. This one owns the verdict every format shares, so the
    high/low fixture pair stays a matched positive/negative control at each
    format — visible as two separately named cases rather than one merged case.
    """

    @pytest.mark.parametrize(
        ('fixture_name', 'fmt', 'expected_passed', 'expected_message_fragment'),
        [
            ('jacoco-high.xml', 'jacoco', True, 'meets threshold'),
            ('jacoco-low.xml', 'jacoco', False, 'below threshold'),
            ('cobertura-high.xml', 'cobertura', True, 'meets threshold'),
            ('cobertura-low.xml', 'cobertura', False, 'below threshold'),
            ('jest-high.json', 'jest_json', True, 'meets threshold'),
            ('jest-low.json', 'jest_json', False, 'below threshold'),
        ],
        ids=[
            'jacoco-high-passes',
            'jacoco-low-fails',
            'cobertura-high-passes',
            'cobertura-low-fails',
            'jest-high-passes',
            'jest-low-fails',
        ],
    )
    def test_threshold_verdict(self, fixture_name, fmt, expected_passed, expected_message_fragment):
        """A report parses cleanly and its verdict matches its coverage level."""
        result = parse_coverage_report(FIXTURES_DIR / fixture_name, fmt, threshold=80)
        assert result['status'] == 'success'
        assert result['passed'] is expected_passed
        assert result['threshold'] == 80
        assert expected_message_fragment in result['message']


# =============================================================================
# JaCoCo XML Format Tests
# =============================================================================


class TestJacocoFormat:
    """Tests for JaCoCo XML format parsing."""

    def test_high_coverage_overall_metrics(self):
        """JaCoCo report returns correct overall metrics."""
        result = parse_coverage_report(FIXTURES_DIR / 'jacoco-high.xml', 'jacoco')
        overall = result['overall']
        assert overall['line'] == 100.0  # 0 missed, 5 covered
        assert overall['branch'] == 100.0  # 0 missed, 2 covered
        assert overall['instruction'] > 0
        assert overall['method'] > 0

    def test_low_coverage_detects_classes(self):
        """JaCoCo low-coverage report identifies classes below threshold."""
        result = parse_coverage_report(FIXTURES_DIR / 'jacoco-low.xml', 'jacoco', threshold=80)
        assert len(result['low_coverage']) > 0
        class_names = [entry['class'] for entry in result['low_coverage']]
        assert any('LegacyService' in c for c in class_names)

    def test_low_coverage_has_missed_methods(self):
        """JaCoCo low-coverage entries include missed method detail."""
        result = parse_coverage_report(FIXTURES_DIR / 'jacoco-low.xml', 'jacoco', threshold=80)
        for entry in result['low_coverage']:
            assert 'missed_methods' in entry
            # LegacyService has 'cleanup' uncovered
            if 'LegacyService' in entry['class']:
                assert 'cleanup' in entry['missed_methods']

    def test_custom_threshold_passes(self):
        """Low-coverage report passes with a low threshold."""
        result = parse_coverage_report(FIXTURES_DIR / 'jacoco-low.xml', 'jacoco', threshold=10)
        assert result['passed'] is True


# =============================================================================
# Cobertura XML Format Tests
# =============================================================================


class TestCoberturaFormat:
    """Tests for Cobertura XML format parsing."""

    def test_high_coverage_overall_metrics(self):
        """Cobertura report returns correct overall metrics."""
        result = parse_coverage_report(FIXTURES_DIR / 'cobertura-high.xml', 'cobertura')
        overall = result['overall']
        assert overall['line'] == 90.0  # line-rate="0.90"
        assert overall['branch'] == 87.5  # branch-rate="0.875"

    def test_low_coverage_detects_classes(self):
        """Cobertura low-coverage report identifies classes below threshold."""
        result = parse_coverage_report(FIXTURES_DIR / 'cobertura-low.xml', 'cobertura', threshold=80)
        assert len(result['low_coverage']) > 0
        class_names = [entry['class'] for entry in result['low_coverage']]
        assert any('legacy' in c for c in class_names)

    def test_low_coverage_has_missed_methods(self):
        """Cobertura low-coverage entries include missed method detail."""
        result = parse_coverage_report(FIXTURES_DIR / 'cobertura-low.xml', 'cobertura', threshold=80)
        for entry in result['low_coverage']:
            if 'legacy' in entry['class']:
                assert 'old_process' in entry['missed_methods']

    def test_cobertura_has_file_field(self):
        """Cobertura low-coverage entries include file path."""
        result = parse_coverage_report(FIXTURES_DIR / 'cobertura-low.xml', 'cobertura', threshold=80)
        for entry in result['low_coverage']:
            assert 'file' in entry


# =============================================================================
# Jest/Istanbul JSON Format Tests
# =============================================================================


class TestJestJsonFormat:
    """Tests for Jest/Istanbul JSON format parsing."""

    def test_high_coverage_overall_metrics(self):
        """Jest JSON report returns correct overall metrics."""
        result = parse_coverage_report(FIXTURES_DIR / 'jest-high.json', 'jest_json')
        overall = result['overall']
        assert overall['line'] == 90
        assert overall['branch'] == 84
        assert overall['function'] == 90
        assert overall['statement'] == 90

    def test_low_coverage_detects_files(self):
        """Jest JSON low-coverage report identifies files below threshold."""
        result = parse_coverage_report(FIXTURES_DIR / 'jest-low.json', 'jest_json', threshold=80)
        assert len(result['low_coverage']) > 0
        files = [entry['file'] for entry in result['low_coverage']]
        assert any('Widget' in f for f in files)
        assert any('api' in f for f in files)

    def test_low_coverage_has_branch_pct(self):
        """Jest JSON low-coverage entries include branch percentage."""
        result = parse_coverage_report(FIXTURES_DIR / 'jest-low.json', 'jest_json', threshold=80)
        for entry in result['low_coverage']:
            assert 'branch_pct' in entry


# =============================================================================
# LCOV Format Tests
# =============================================================================


class TestLcovFormat:
    """Tests for LCOV format parsing."""

    def test_lcov_parses_overall_metrics(self):
        """LCOV report returns correct overall metrics."""
        result = parse_coverage_report(FIXTURES_DIR / 'sample.lcov', 'lcov')
        assert result['status'] == 'success'
        overall = result['overall']
        # Total: LH=20, LF=30 => 66.67%
        assert overall['line'] == 66.67
        assert 'branch' in overall
        assert 'function' in overall
        assert 'statement' in overall

    def test_lcov_high_threshold_fails(self):
        """LCOV report fails with high threshold."""
        result = parse_coverage_report(FIXTURES_DIR / 'sample.lcov', 'lcov', threshold=80)
        assert result['passed'] is False

    def test_lcov_low_threshold_passes(self):
        """LCOV report passes with low threshold."""
        result = parse_coverage_report(FIXTURES_DIR / 'sample.lcov', 'lcov', threshold=50)
        assert result['passed'] is True

    def test_lcov_detects_low_coverage_files(self):
        """LCOV report identifies files below threshold."""
        result = parse_coverage_report(FIXTURES_DIR / 'sample.lcov', 'lcov', threshold=80)
        assert len(result['low_coverage']) > 0
        files = [entry['file'] for entry in result['low_coverage']]
        # Button.js has 3/10 = 30% coverage
        assert any('Button' in f for f in files)

    def test_lcov_low_coverage_has_branch_pct(self):
        """LCOV low-coverage entries include branch percentage."""
        result = parse_coverage_report(FIXTURES_DIR / 'sample.lcov', 'lcov', threshold=80)
        for entry in result['low_coverage']:
            assert 'branch_pct' in entry


# =============================================================================
# find_report() Tests
# =============================================================================


class TestFindReport:
    """Tests for find_report() path resolution."""

    @pytest.mark.parametrize(
        ('report_name', 'expected_fmt'),
        [
            ('jacoco-high.xml', 'jacoco'),
            ('cobertura-high.xml', 'cobertura'),
            ('jest-high.json', 'jest_json'),
        ],
        ids=['jacoco-xml', 'cobertura-xml', 'jest-json'],
    )
    def test_explicit_path_resolves_and_auto_detects_its_format(self, report_name, expected_fmt):
        """An existing explicit path is returned with its format auto-detected.

        The three cases enumerate every format ``find_report`` detects from a
        path — two of them sharing the ``.xml`` extension, so detection cannot be
        passing on the extension alone. ``test_explicit_path_not_found`` below is
        the matched negative control for the resolution half.
        """
        path, fmt = find_report([], explicit_path=str(FIXTURES_DIR / report_name))
        assert path is not None
        assert path.name == report_name
        assert fmt == expected_fmt

    def test_explicit_path_not_found(self):
        """find_report returns None for missing explicit path."""
        path, fmt = find_report([], explicit_path='/nonexistent/report.xml')
        assert path is None
        assert fmt == 'unknown'

    def test_search_paths_first_match(self):
        """find_report returns first matching candidate from search paths."""
        search = [
            ('nonexistent.xml', 'jacoco'),
            ('jacoco-high.xml', 'jacoco'),
            ('cobertura-high.xml', 'cobertura'),
        ]
        path, fmt = find_report(search, base_path=str(FIXTURES_DIR))
        assert path is not None
        assert path.name == 'jacoco-high.xml'
        assert fmt == 'jacoco'

    def test_search_paths_no_match(self):
        """find_report returns None when no candidate matches."""
        search = [
            ('nonexistent1.xml', 'jacoco'),
            ('nonexistent2.xml', 'cobertura'),
        ]
        path, fmt = find_report(search, base_path=str(FIXTURES_DIR))
        assert path is None
        assert fmt == 'unknown'

    def test_search_paths_default_base(self):
        """find_report uses current directory as default base."""
        # Should not crash with default base_path
        path, fmt = find_report([('nonexistent.xml', 'jacoco')])
        assert path is None


# =============================================================================
# Threshold Checking Tests
# =============================================================================


class TestThresholdChecking:
    """Tests for threshold pass/fail logic."""

    @pytest.mark.parametrize(
        ('fixture_name', 'fmt', 'threshold', 'expected_passed'),
        [
            ('jacoco-high.xml', 'jacoco', 100, True),
            ('jest-high.json', 'jest_json', 91, False),
            ('jacoco-low.xml', 'jacoco', 0, True),
        ],
        ids=[
            'coverage-exactly-at-threshold-passes',
            'coverage-one-point-below-threshold-fails',
            'zero-threshold-passes-any-coverage',
        ],
    )
    def test_threshold_comparison_at_the_boundary(self, fixture_name, fmt, threshold, expected_passed):
        """The comparison is ``>=``, pinned from both sides of the boundary.

        ``jacoco-high.xml`` is 100% line coverage against a threshold of 100, so
        equality must pass; ``jest-high.json`` is 90% against 91, the smallest
        integer step below, so it must fail. A threshold of 0 passes the lowest
        fixture in the set.
        """
        result = parse_coverage_report(FIXTURES_DIR / fixture_name, fmt, threshold=threshold)
        assert result['passed'] is expected_passed

    def test_default_threshold_is_80(self):
        """Default threshold is 80%."""
        result = parse_coverage_report(FIXTURES_DIR / 'jacoco-high.xml', 'jacoco')
        assert result['threshold'] == 80


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error conditions."""

    def test_missing_report_file(self):
        """Missing report file returns error status."""
        result = parse_coverage_report('/nonexistent/report.xml', 'jacoco')
        assert result['status'] == 'error'
        assert result['error'] == 'report_not_found'
        assert 'not found' in result['message']

    def test_unsupported_format(self):
        """Unsupported format returns error status."""
        result = parse_coverage_report(FIXTURES_DIR / 'jacoco-high.xml', 'unknown_format')
        assert result['status'] == 'error'
        assert result['error'] == 'unsupported_format'
        assert 'Unsupported format' in result['message']

    def test_unsupported_format_lists_supported(self):
        """Unsupported format error lists supported formats."""
        result = parse_coverage_report(FIXTURES_DIR / 'jacoco-high.xml', 'invalid')
        assert 'jacoco' in result['message']
        assert 'cobertura' in result['message']
        assert 'lcov' in result['message']
        assert 'jest_json' in result['message']


# =============================================================================
# Low Coverage Detection Tests
# =============================================================================


class TestLowCoverageDetection:
    """Tests for low coverage detection across formats."""

    def test_no_low_coverage_when_all_above_threshold(self):
        """No low-coverage entries when all items pass threshold."""
        result = parse_coverage_report(FIXTURES_DIR / 'jacoco-high.xml', 'jacoco', threshold=50)
        assert result['low_coverage'] == []

    def test_low_coverage_count_jacoco(self):
        """JaCoCo low-coverage returns correct count of flagged classes."""
        result = parse_coverage_report(FIXTURES_DIR / 'jacoco-low.xml', 'jacoco', threshold=80)
        # Only LegacyService class, which is below 80%
        assert len(result['low_coverage']) == 1

    def test_low_coverage_count_jest(self):
        """Jest low-coverage returns correct count of flagged files."""
        result = parse_coverage_report(FIXTURES_DIR / 'jest-low.json', 'jest_json', threshold=80)
        # Widget.js (40%) and api.js (60%) both below 80%
        assert len(result['low_coverage']) == 2

    def test_low_coverage_line_pct_present(self):
        """All low-coverage entries have line_pct field."""
        result = parse_coverage_report(FIXTURES_DIR / 'jest-low.json', 'jest_json', threshold=80)
        for entry in result['low_coverage']:
            assert 'line_pct' in entry
            assert isinstance(entry['line_pct'], (int, float))
