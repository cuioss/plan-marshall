"""Tests for pr_doctor.py - PR Doctor handoff parsing and validation."""

import json
import sys
import unittest
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

from conftest import get_script_path, run_script  # noqa: E402

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-pr-doctor', 'pr_doctor.py')


def run_doctor_script(args: list) -> tuple:
    """Run pr_doctor.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


class TestParseHandoff(unittest.TestCase):
    """Test pr_doctor.py parse-handoff subcommand."""

    def test_full_handoff(self):
        """Test parsing a complete handoff structure."""
        handoff = {
            'artifacts': {
                'pr_number': 123,
                'branch': 'feature/my-feature',
                'commit_hash': 'abc123',
                'plan_id': 'my-plan',
            },
            'decisions': {
                'auto_fix': True,
                'checks': 'all',
                'skip_sonar': False,
            },
            'constraints': {
                'max_fix_attempts': 3,
                'protected_files': ['README.md'],
            },
        }
        stdout, _, code = run_doctor_script(['parse-handoff', '--handoff', json.dumps(handoff)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'success')
        merged = result['merged']
        self.assertEqual(merged['pr_number'], 123)
        self.assertEqual(merged['branch'], 'feature/my-feature')
        self.assertEqual(merged['checks'], 'all')
        self.assertTrue(merged['auto_fix'])
        self.assertEqual(merged['max_fix_attempts'], 3)
        self.assertTrue(result['validation']['valid'])
        self.assertEqual(len(result['validation']['warnings']), 0)

    def test_minimal_handoff(self):
        """Test parsing a minimal handoff with defaults."""
        handoff = {'artifacts': {'pr_number': 42}}
        stdout, _, code = run_doctor_script(['parse-handoff', '--handoff', json.dumps(handoff)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        merged = result['merged']
        self.assertEqual(merged['pr_number'], 42)
        self.assertEqual(merged['checks'], 'all')  # default
        self.assertFalse(merged['auto_fix'])  # default
        self.assertEqual(merged['max_fix_attempts'], 3)  # default

    def test_explicit_params_override_handoff(self):
        """Test that explicit CLI params override handoff values."""
        handoff = {
            'artifacts': {'pr_number': 100},
            'decisions': {'checks': 'all', 'auto_fix': False},
        }
        stdout, _, code = run_doctor_script([
            'parse-handoff', '--handoff', json.dumps(handoff),
            '--pr', '456', '--checks', 'build', '--auto-fix',
        ])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        merged = result['merged']
        self.assertEqual(merged['pr_number'], 456)  # overridden
        self.assertEqual(merged['checks'], 'build')  # overridden
        self.assertTrue(merged['auto_fix'])  # overridden

    def test_empty_handoff(self):
        """Test parsing empty handoff uses defaults."""
        stdout, _, code = run_doctor_script(['parse-handoff', '--handoff', '{}'])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        merged = result['merged']
        self.assertIsNone(merged['pr_number'])
        self.assertEqual(merged['checks'], 'all')
        self.assertFalse(merged['auto_fix'])

    def test_invalid_json(self):
        """Test error on invalid JSON."""
        stdout, _, code = run_doctor_script(['parse-handoff', '--handoff', 'not-json'])
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'failure')
        self.assertIn('Invalid JSON', result['error'])

    def test_handoff_not_dict(self):
        """Test error when handoff is not a dict."""
        stdout, _, code = run_doctor_script(['parse-handoff', '--handoff', '[1,2,3]'])
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'failure')
        self.assertIn('object', result['error'])

    def test_validation_warns_on_bad_pr_number(self):
        """Test validation warns on invalid PR number."""
        handoff = {'artifacts': {'pr_number': -1}}
        stdout, _, code = run_doctor_script(['parse-handoff', '--handoff', json.dumps(handoff)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertFalse(result['validation']['valid'])
        self.assertTrue(any('pr_number' in w for w in result['validation']['warnings']))

    def test_validation_warns_on_bad_checks(self):
        """Test validation warns on invalid checks value."""
        handoff = {'decisions': {'checks': 'invalid'}}
        stdout, _, code = run_doctor_script(['parse-handoff', '--handoff', json.dumps(handoff)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertFalse(result['validation']['valid'])
        self.assertTrue(any('checks' in w for w in result['validation']['warnings']))

    def test_validation_warns_on_unknown_keys(self):
        """Test validation warns on unknown top-level keys."""
        handoff = {'artifacts': {}, 'extra_key': 'value'}
        stdout, _, code = run_doctor_script(['parse-handoff', '--handoff', json.dumps(handoff)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertTrue(any('Unknown' in w for w in result['validation']['warnings']))

    def test_validation_warns_on_bad_auto_fix_type(self):
        """Test validation warns when auto_fix is not a bool."""
        handoff = {'decisions': {'auto_fix': 'yes'}}
        stdout, _, code = run_doctor_script(['parse-handoff', '--handoff', json.dumps(handoff)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertTrue(any('auto_fix' in w for w in result['validation']['warnings']))

    def test_validation_warns_on_bad_max_fix_attempts(self):
        """Test validation warns when max_fix_attempts is not a positive int."""
        handoff = {'constraints': {'max_fix_attempts': 0}}
        stdout, _, code = run_doctor_script(['parse-handoff', '--handoff', json.dumps(handoff)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertTrue(any('max_fix_attempts' in w for w in result['validation']['warnings']))

    def test_validation_warns_on_bad_protected_files(self):
        """Test validation warns when protected_files contains non-strings."""
        handoff = {'constraints': {'protected_files': [1, 2]}}
        stdout, _, code = run_doctor_script(['parse-handoff', '--handoff', json.dumps(handoff)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertTrue(any('protected_files' in w for w in result['validation']['warnings']))

    def test_max_fix_attempts_override(self):
        """Test that --max-fix-attempts overrides handoff."""
        handoff = {'constraints': {'max_fix_attempts': 5}}
        stdout, _, code = run_doctor_script([
            'parse-handoff', '--handoff', json.dumps(handoff),
            '--max-fix-attempts', '10',
        ])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['merged']['max_fix_attempts'], 10)

    def test_auto_fix_flag_without_value(self):
        """Test --auto-fix as bare flag sets True."""
        handoff = {'artifacts': {'pr_number': 1}}
        stdout, _, code = run_doctor_script([
            'parse-handoff', '--handoff', json.dumps(handoff), '--auto-fix',
        ])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertTrue(result['merged']['auto_fix'])

    def test_auto_fix_not_provided_uses_handoff(self):
        """Test that omitting --auto-fix defers to handoff value."""
        handoff = {'decisions': {'auto_fix': False}}
        stdout, _, code = run_doctor_script([
            'parse-handoff', '--handoff', json.dumps(handoff),
        ])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertFalse(result['merged']['auto_fix'])

    def test_auto_fix_not_provided_defaults_false(self):
        """Test that omitting --auto-fix without handoff defaults to False."""
        handoff = {'artifacts': {'pr_number': 1}}
        stdout, _, code = run_doctor_script([
            'parse-handoff', '--handoff', json.dumps(handoff),
        ])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertFalse(result['merged']['auto_fix'])


class TestMain(unittest.TestCase):
    """Test pr_doctor.py main entry point."""

    def test_no_subcommand(self):
        """Test error when no subcommand provided."""
        _, stderr, code = run_doctor_script([])
        self.assertNotEqual(code, 0)

    def test_help(self):
        """Test help output."""
        stdout, _, code = run_doctor_script(['--help'])
        self.assertEqual(code, 0)
        self.assertIn('parse-handoff', stdout)

    def test_unknown_subcommand(self):
        """Test error when unknown subcommand provided."""
        _, stderr, code = run_doctor_script(['unknown-command'])
        self.assertNotEqual(code, 0)


if __name__ == '__main__':
    unittest.main()
