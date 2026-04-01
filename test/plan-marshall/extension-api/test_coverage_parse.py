#!/usr/bin/env python3
"""Tests for _coverage_parse.py shared coverage report parsing module."""

from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from _coverage_parse import find_report, parse_coverage_report

FIXTURES_DIR = Path(__file__).parent / 'fixtures' / 'coverage'


# =============================================================================
# JaCoCo XML Format Tests
# =============================================================================


class TestJacocoFormat:
    """Tests for JaCoCo XML format parsing."""

    def test_high_coverage_passes_threshold(self):
        """JaCoCo report with high coverage passes threshold check."""
        result = parse_coverage_report(FIXTURES_DIR / 'jacoco-high.xml', 'jacoco', threshold=80)
        assert result['status'] == 'success'
        assert result['passed'] is True
        assert result['threshold'] == 80
        assert 'meets threshold' in result['message']

    def test_high_coverage_overall_metrics(self):
        """JaCoCo report returns correct overall metrics."""
        result = parse_coverage_report(FIXTURES_DIR / 'jacoco-high.xml', 'jacoco')
        overall = result['overall']
        assert overall['line'] == 100.0  # 0 missed, 5 covered
        assert overall['branch'] == 100.0  # 0 missed, 2 covered
        assert overall['instruction'] > 0
        assert overall['method'] > 0

    def test_low_coverage_fails_threshold(self):
        """JaCoCo report with low coverage fails threshold check."""
        result = parse_coverage_report(FIXTURES_DIR / 'jacoco-low.xml', 'jacoco', threshold=80)
        assert result['status'] == 'success'
        assert result['passed'] is False
        assert 'below threshold' in result['message']

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

    def test_high_coverage_passes_threshold(self):
        """Cobertura report with high coverage passes threshold check."""
        result = parse_coverage_report(FIXTURES_DIR / 'cobertura-high.xml', 'cobertura', threshold=80)
        assert result['status'] == 'success'
        assert result['passed'] is True
        assert 'meets threshold' in result['message']

    def test_high_coverage_overall_metrics(self):
        """Cobertura report returns correct overall metrics."""
        result = parse_coverage_report(FIXTURES_DIR / 'cobertura-high.xml', 'cobertura')
        overall = result['overall']
        assert overall['line'] == 90.0  # line-rate="0.90"
        assert overall['branch'] == 87.5  # branch-rate="0.875"

    def test_low_coverage_fails_threshold(self):
        """Cobertura report with low coverage fails threshold check."""
        result = parse_coverage_report(FIXTURES_DIR / 'cobertura-low.xml', 'cobertura', threshold=80)
        assert result['status'] == 'success'
        assert result['passed'] is False
        assert 'below threshold' in result['message']

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

    def test_high_coverage_passes_threshold(self):
        """Jest JSON report with high coverage passes threshold check."""
        result = parse_coverage_report(FIXTURES_DIR / 'jest-high.json', 'jest_json', threshold=80)
        assert result['status'] == 'success'
        assert result['passed'] is True
        assert 'meets threshold' in result['message']

    def test_high_coverage_overall_metrics(self):
        """Jest JSON report returns correct overall metrics."""
        result = parse_coverage_report(FIXTURES_DIR / 'jest-high.json', 'jest_json')
        overall = result['overall']
        assert overall['line'] == 90
        assert overall['branch'] == 84
        assert overall['function'] == 90
        assert overall['statement'] == 90

    def test_low_coverage_fails_threshold(self):
        """Jest JSON report with low coverage fails threshold check."""
        result = parse_coverage_report(FIXTURES_DIR / 'jest-low.json', 'jest_json', threshold=80)
        assert result['status'] == 'success'
        assert result['passed'] is False
        assert 'below threshold' in result['message']

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

    def test_explicit_path_found(self):
        """find_report returns explicit path when file exists."""
        path, fmt = find_report([], explicit_path=str(FIXTURES_DIR / 'jacoco-high.xml'))
        assert path is not None
        assert path.name == 'jacoco-high.xml'
        assert fmt == 'jacoco'

    def test_explicit_path_json_format(self):
        """find_report auto-detects JSON format from explicit path."""
        path, fmt = find_report([], explicit_path=str(FIXTURES_DIR / 'jest-high.json'))
        assert path is not None
        assert fmt == 'jest_json'

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

    def test_explicit_cobertura_xml_detection(self):
        """find_report auto-detects Cobertura XML format."""
        path, fmt = find_report([], explicit_path=str(FIXTURES_DIR / 'cobertura-high.xml'))
        assert path is not None
        assert fmt == 'cobertura'


# =============================================================================
# Threshold Checking Tests
# =============================================================================


class TestThresholdChecking:
    """Tests for threshold pass/fail logic."""

    def test_exact_threshold_passes(self):
        """Coverage exactly at threshold passes."""
        # jacoco-high.xml has 100% line coverage
        result = parse_coverage_report(FIXTURES_DIR / 'jacoco-high.xml', 'jacoco', threshold=100)
        assert result['passed'] is True

    def test_one_below_threshold_fails(self):
        """Coverage one below threshold fails."""
        # jest-high.json has 90% line coverage, threshold 91 should fail
        result = parse_coverage_report(FIXTURES_DIR / 'jest-high.json', 'jest_json', threshold=91)
        assert result['passed'] is False

    def test_zero_threshold_always_passes(self):
        """Zero threshold always passes."""
        result = parse_coverage_report(FIXTURES_DIR / 'jacoco-low.xml', 'jacoco', threshold=0)
        assert result['passed'] is True

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
