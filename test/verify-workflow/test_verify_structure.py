#!/usr/bin/env python3
"""
Tests for verify-structure.py script.

Tests the structural verification functionality that checks workflow outputs
via manage-* tool interfaces.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

# Import the loaded module from conftest (PYTHONPATH is already set up)
from conftest import verify_structure

# Import what we need from the loaded module
StructuralChecker = verify_structure.StructuralChecker

# Import shared parsing function (now from _plan_parsing)
from _plan_parsing import parse_toon_simple  # type: ignore[import-not-found]  # noqa: E402

# Import serialize_toon from toon_parser (same as the script does)
from toon_parser import serialize_toon  # type: ignore[import-not-found]  # noqa: E402


def make_base_path_mock(tmp_path: Path):
    """Create a mock base_path function that returns paths in tmp_path."""

    def mock_base_path(*args) -> Path:
        return tmp_path.joinpath(*args)

    return mock_base_path


class TestSerializeToon:
    """Tests for TOON serialization."""

    def test_simple_key_value(self):
        """Test simple key-value serialization."""
        data = {'status': 'success', 'plan_id': 'test-plan'}
        result = serialize_toon(data)
        assert 'status: success' in result
        assert 'plan_id: test-plan' in result

    def test_boolean_values(self):
        """Test boolean serialization to lowercase."""
        data = {'exists': True, 'valid': False}
        result = serialize_toon(data)
        assert 'exists: true' in result
        assert 'valid: false' in result

    def test_nested_dict(self):
        """Test nested dictionary serialization."""
        data = {'outer': {'inner': 'value'}}
        result = serialize_toon(data)
        assert 'outer:' in result
        assert 'inner: value' in result

    def test_simple_list(self):
        """Test simple list serialization."""
        data = {'items': ['one', 'two', 'three']}
        result = serialize_toon(data)
        assert 'items[3]:' in result
        assert 'one' in result
        assert 'two' in result

    def test_uniform_array(self):
        """Test uniform array (list of dicts) serialization."""
        data = {
            'checks': [
                {'name': 'check1', 'status': 'pass'},
                {'name': 'check2', 'status': 'fail'},
            ]
        }
        result = serialize_toon(data)
        assert 'checks[2]{name,status}:' in result
        assert 'check1,pass' in result
        assert 'check2,fail' in result

    def test_empty_list(self):
        """Test empty list serialization."""
        data = {'items': []}
        result = serialize_toon(data)
        assert 'items[0]:' in result


class TestParseToonSimple:
    """Tests for simple TOON parsing."""

    def test_key_value_pairs(self):
        """Test parsing key-value pairs."""
        content = 'status: success\nplan_id: test-plan'
        result = parse_toon_simple(content)
        assert result['status'] == 'success'
        assert result['plan_id'] == 'test-plan'

    def test_list_parsing(self):
        """Test parsing lists."""
        content = 'items[3]:\n  one\n  two\n  three'
        result = parse_toon_simple(content)
        assert 'items' in result
        assert len(result['items']) == 3

    def test_comment_skipping(self):
        """Test that comments are skipped."""
        content = '# Comment\nstatus: success'
        result = parse_toon_simple(content)
        assert result['status'] == 'success'
        assert '#' not in str(result)


class TestStructuralChecker:
    """Tests for StructuralChecker class."""

    @pytest.fixture
    def temp_test_case(self, tmp_path):
        """Create a temporary test case directory."""
        test_case_dir = tmp_path / 'test-case'
        test_case_dir.mkdir()

        # Create expected-artifacts.toon
        expected = test_case_dir / 'expected-artifacts.toon'
        expected.write_text('deliverable_count: 3\naffected_files[2]:\n  file1.md\n  file2.md')

        return test_case_dir

    def test_add_check(self, temp_test_case):
        """Test adding a check result."""
        checker = StructuralChecker('test-plan', temp_test_case)
        checker.add_check('test_check', 'pass', 'Test passed')

        assert len(checker.checks) == 1
        assert checker.checks[0]['name'] == 'test_check'
        assert checker.checks[0]['status'] == 'pass'

    def test_add_finding(self, temp_test_case):
        """Test adding a finding."""
        checker = StructuralChecker('test-plan', temp_test_case)
        checker.add_finding('error', 'Something failed')

        assert len(checker.findings) == 1
        assert checker.findings[0]['severity'] == 'error'
        assert checker.findings[0]['message'] == 'Something failed'

    def test_load_expected_artifacts(self, temp_test_case):
        """Test loading expected artifacts from test case."""
        checker = StructuralChecker('test-plan', temp_test_case)
        expected = checker.load_expected_artifacts()

        assert 'deliverable_count' in expected
        assert expected['deliverable_count'] == '3'

    def test_check_solution_outline_exists_success(self, temp_test_case, tmp_path):
        """Test solution outline existence check - success case."""
        # Create mock plan directory structure
        plan_dir = tmp_path / 'plans' / 'test-plan'
        plan_dir.mkdir(parents=True)
        solution_path = plan_dir / 'solution_outline.md'
        solution_path.write_text('# Solution\n\nContent here')

        with patch('verify_structure.base_path', make_base_path_mock(tmp_path)):
            checker = StructuralChecker('test-plan', temp_test_case)
            result = checker.check_solution_outline_exists()

        assert result is True
        assert len(checker.checks) == 1
        assert checker.checks[0]['status'] == 'pass'

    def test_check_solution_outline_exists_failure(self, temp_test_case, tmp_path):
        """Test solution outline existence check - failure case."""
        # Create plan dir but no solution file
        plan_dir = tmp_path / 'plans' / 'test-plan'
        plan_dir.mkdir(parents=True)

        with patch('verify_structure.base_path', make_base_path_mock(tmp_path)):
            checker = StructuralChecker('test-plan', temp_test_case)
            result = checker.check_solution_outline_exists()

        assert result is False
        assert len(checker.checks) == 1
        assert checker.checks[0]['status'] == 'fail'
        assert len(checker.findings) == 1
        assert checker.findings[0]['severity'] == 'error'

    def test_check_solution_outline_valid_success(self, temp_test_case, tmp_path):
        """Test validation check success."""
        plan_dir = tmp_path / 'plans' / 'test-plan'
        plan_dir.mkdir(parents=True)
        solution_path = plan_dir / 'solution_outline.md'
        solution_path.write_text(
            '# Solution\n\n## Summary\n\nSummary text.\n\n## Overview\n\nOverview text.\n\n## Deliverables\n\n### 1. Test\n\nContent.'
        )

        with patch('verify_structure.base_path', make_base_path_mock(tmp_path)):
            checker = StructuralChecker('test-plan', temp_test_case)
            result = checker.check_solution_outline_valid()

        assert result is True
        assert checker.checks[0]['status'] == 'pass'

    def test_check_solution_outline_valid_with_warnings(self, temp_test_case, tmp_path):
        """Test validation with missing section produces errors (not just warnings)."""
        plan_dir = tmp_path / 'plans' / 'test-plan'
        plan_dir.mkdir(parents=True)
        # Missing required sections
        solution_path = plan_dir / 'solution_outline.md'
        solution_path.write_text('# Solution\n\nContent only, no sections')

        with patch('verify_structure.base_path', make_base_path_mock(tmp_path)):
            checker = StructuralChecker('test-plan', temp_test_case)
            result = checker.check_solution_outline_valid()

        # Should fail due to missing required sections
        assert result is False
        assert checker.checks[0]['status'] == 'fail'
        assert len(checker.findings) >= 1

    def test_run_all_checks_calculates_status(self, temp_test_case, tmp_path):
        """Test that run_all_checks calculates overall status."""
        # Create mock plan directory with all required files
        plan_dir = tmp_path / 'plans' / 'test-plan'
        plan_dir.mkdir(parents=True)

        solution_content = """# Solution

## Summary

This is the summary section.

## Overview

This is the overview section.

## Deliverables

### 1. First Deliverable

Content for first deliverable.

### 2. Second Deliverable

Content for second deliverable.

### 3. Third Deliverable

Content for third deliverable.
"""
        (plan_dir / 'solution_outline.md').write_text(solution_content)
        (plan_dir / 'status.toon').write_text('current_phase: execute')
        (plan_dir / 'references.json').write_text(
            '{"branch": "main", "domains": ["java"], "affected_files": ["file1.md", "file2.md"]}'
        )

        with patch('verify_structure.base_path', make_base_path_mock(tmp_path)):
            checker = StructuralChecker('test-plan', temp_test_case)
            results = checker.run_all_checks()

        assert results['status'] == 'pass'
        assert results['plan_id'] == 'test-plan'
        assert 'passed' in results
        assert 'failed' in results
        assert 'checks' in results


class TestIntegration:
    """Integration tests (require actual filesystem)."""

    def test_checker_with_missing_test_case(self, tmp_path):
        """Test checker handles missing expected-artifacts.toon."""
        checker = StructuralChecker('test-plan', tmp_path / 'nonexistent')
        expected = checker.load_expected_artifacts()
        assert expected == {}
