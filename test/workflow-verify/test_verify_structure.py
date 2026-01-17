#!/usr/bin/env python3
"""
Tests for verify-structure.py script.

Tests the structural verification functionality that checks workflow outputs
via manage-* tool interfaces.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Load script module directly from project-level path
PROJECT_ROOT = Path(__file__).parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / '.claude' / 'skills' / 'workflow-verify' / 'scripts' / 'verify-structure.py'

# Load module from file path
spec = importlib.util.spec_from_file_location('verify_structure', SCRIPT_PATH)
assert spec is not None and spec.loader is not None
verify_structure = importlib.util.module_from_spec(spec)
sys.modules['verify_structure'] = verify_structure
spec.loader.exec_module(verify_structure)

# Import what we need
StructuralChecker = verify_structure.StructuralChecker
parse_toon_simple = verify_structure.parse_toon_simple
serialize_toon = verify_structure.serialize_toon


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

    @patch('verify_structure.run_manage_script')
    def test_check_solution_outline_exists_success(self, mock_run, temp_test_case):
        """Test solution outline existence check - success case."""
        mock_run.return_value = (0, 'status: success\nexists: true', '')

        checker = StructuralChecker('test-plan', temp_test_case)
        result = checker.check_solution_outline_exists()

        assert result is True
        assert len(checker.checks) == 1
        assert checker.checks[0]['status'] == 'pass'

    @patch('verify_structure.run_manage_script')
    def test_check_solution_outline_exists_failure(self, mock_run, temp_test_case):
        """Test solution outline existence check - failure case."""
        mock_run.return_value = (1, '', 'Not found')

        checker = StructuralChecker('test-plan', temp_test_case)
        result = checker.check_solution_outline_exists()

        assert result is False
        assert len(checker.checks) == 1
        assert checker.checks[0]['status'] == 'fail'
        assert len(checker.findings) == 1
        assert checker.findings[0]['severity'] == 'error'

    @patch('verify_structure.run_manage_script')
    def test_check_solution_outline_valid_with_warnings(self, mock_run, temp_test_case):
        """Test validation check extracts warnings."""
        mock_run.return_value = (0, 'status: success\nwarnings:\n  - Minor issue', '')

        checker = StructuralChecker('test-plan', temp_test_case)
        result = checker.check_solution_outline_valid()

        assert result is True
        assert checker.checks[0]['status'] == 'pass'

    @patch('verify_structure.run_manage_script')
    def test_run_all_checks_calculates_status(self, mock_run, temp_test_case):
        """Test that run_all_checks calculates overall status."""
        # All checks pass
        mock_run.return_value = (0, 'status: success\nexists: true\ndeliverable_count: 3', '')

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
