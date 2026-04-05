"""Tests for pr_doctor.py - PR Doctor handoff parsing and validation.

Tier 2 (direct import) tests with 3 subprocess tests for CLI plumbing.
"""

import json
import sys
import unittest
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_script_path, run_script  # noqa: E402

# Import toon_parser - conftest sets up PYTHONPATH

# Script under test (for subprocess CLI plumbing tests)
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-pr-doctor', 'pr_doctor.py')

# Tier 2 direct imports — conftest sets up PYTHONPATH for cross-skill imports
from pr_doctor import (  # type: ignore[import-not-found]  # noqa: E402
    check_attempt,
    diagnose_pr,
    merge_handoff_with_params,
    validate_handoff,
)
from triage_helpers import make_error, parse_json_arg  # type: ignore[import-not-found]  # noqa: E402


def _parse_and_merge(handoff_json, pr=None, checks=None, auto_fix=None, max_fix_attempts=None, wait=None):
    """Helper to parse JSON handoff and merge with params, returning result dict."""
    handoff, rc = parse_json_arg(handoff_json, '--handoff')
    if rc:
        return rc
    if not isinstance(handoff, dict):
        return make_error('Handoff must be a JSON object')
    warnings = validate_handoff(handoff)

    merged = merge_handoff_with_params(
        handoff,
        pr=pr,
        checks=checks,
        auto_fix=auto_fix,
        max_fix_attempts=max_fix_attempts,
        wait=wait,
    )

    return {
        'merged': merged,
        'validation': {
            'valid': len(warnings) == 0,
            'warnings': warnings,
        },
        'status': 'success',
    }


class TestParseHandoff(unittest.TestCase):
    """Test pr_doctor.py parse-handoff via direct import."""

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
        result = _parse_and_merge(json.dumps(handoff))
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
        result = _parse_and_merge(json.dumps(handoff))
        merged = result['merged']
        self.assertEqual(merged['pr_number'], 42)
        self.assertEqual(merged['checks'], 'all')  # default
        self.assertFalse(merged['auto_fix'])  # default
        self.assertEqual(merged['max_fix_attempts'], 3)  # default

    def test_explicit_params_override_handoff(self):
        """Test that explicit params override handoff values."""
        handoff = {
            'artifacts': {'pr_number': 100},
            'decisions': {'checks': 'all', 'auto_fix': False},
        }
        result = _parse_and_merge(json.dumps(handoff), pr=456, checks='build', auto_fix=True)
        merged = result['merged']
        self.assertEqual(merged['pr_number'], 456)  # overridden
        self.assertEqual(merged['checks'], 'build')  # overridden
        self.assertTrue(merged['auto_fix'])  # overridden

    def test_empty_handoff(self):
        """Test parsing empty handoff uses defaults."""
        result = _parse_and_merge('{}')
        merged = result['merged']
        self.assertIsNone(merged['pr_number'])
        self.assertEqual(merged['checks'], 'all')
        self.assertFalse(merged['auto_fix'])

    def test_invalid_json(self):
        """Test error on invalid JSON."""
        result = _parse_and_merge('not-json')
        self.assertEqual(result['status'], 'error')
        self.assertIn('Invalid', result['error'])
        self.assertIn('JSON', result['error'])

    def test_handoff_not_dict(self):
        """Test error when handoff is not a dict."""
        result = _parse_and_merge('[1,2,3]')
        self.assertEqual(result['status'], 'error')
        self.assertIn('object', result['error'])

    def test_validation_warns_on_bad_pr_number(self):
        """Test validation warns on invalid PR number."""
        handoff = {'artifacts': {'pr_number': -1}}
        result = _parse_and_merge(json.dumps(handoff))
        self.assertFalse(result['validation']['valid'])
        self.assertTrue(any('pr_number' in w for w in result['validation']['warnings']))

    def test_validation_warns_on_bad_checks(self):
        """Test validation warns on invalid checks value."""
        handoff = {'decisions': {'checks': 'invalid'}}
        result = _parse_and_merge(json.dumps(handoff))
        self.assertFalse(result['validation']['valid'])
        self.assertTrue(any('checks' in w for w in result['validation']['warnings']))

    def test_validation_warns_on_unknown_keys(self):
        """Test validation warns on unknown top-level keys."""
        handoff = {'artifacts': {}, 'extra_key': 'value'}
        result = _parse_and_merge(json.dumps(handoff))
        self.assertTrue(any('Unknown' in w for w in result['validation']['warnings']))

    def test_validation_warns_on_bad_auto_fix_type(self):
        """Test validation warns when auto_fix is not a bool."""
        handoff = {'decisions': {'auto_fix': 'yes'}}
        result = _parse_and_merge(json.dumps(handoff))
        self.assertTrue(any('auto_fix' in w for w in result['validation']['warnings']))

    def test_validation_warns_on_bad_max_fix_attempts(self):
        """Test validation warns when max_fix_attempts is not a positive int."""
        handoff = {'constraints': {'max_fix_attempts': 0}}
        result = _parse_and_merge(json.dumps(handoff))
        self.assertTrue(any('max_fix_attempts' in w for w in result['validation']['warnings']))

    def test_validation_warns_on_bad_protected_files(self):
        """Test validation warns when protected_files contains non-strings."""
        handoff = {'constraints': {'protected_files': [1, 2]}}
        result = _parse_and_merge(json.dumps(handoff))
        self.assertTrue(any('protected_files' in w for w in result['validation']['warnings']))

    def test_max_fix_attempts_override(self):
        """Test that max_fix_attempts param overrides handoff."""
        handoff = {'constraints': {'max_fix_attempts': 5}}
        result = _parse_and_merge(json.dumps(handoff), max_fix_attempts=10)
        self.assertEqual(result['merged']['max_fix_attempts'], 10)

    def test_auto_fix_not_provided_uses_handoff(self):
        """Test that omitting auto_fix defers to handoff value."""
        handoff = {'decisions': {'auto_fix': False}}
        result = _parse_and_merge(json.dumps(handoff))
        self.assertFalse(result['merged']['auto_fix'])

    def test_auto_fix_not_provided_defaults_false(self):
        """Test that omitting auto_fix without handoff defaults to False."""
        handoff = {'artifacts': {'pr_number': 1}}
        result = _parse_and_merge(json.dumps(handoff))
        self.assertFalse(result['merged']['auto_fix'])

    def test_no_wait_overrides_handoff(self):
        """Test that wait=False overrides handoff wait=true."""
        handoff = {'decisions': {'wait': True}}
        result = _parse_and_merge(json.dumps(handoff), wait=False)
        self.assertFalse(result['merged']['wait'])

    def test_wait_defaults_true(self):
        """Test that wait defaults to True without flags."""
        handoff = {'artifacts': {'pr_number': 1}}
        result = _parse_and_merge(json.dumps(handoff))
        self.assertTrue(result['merged']['wait'])

    def test_wait_override_true(self):
        """Test that wait=True overrides handoff wait=false."""
        handoff = {'decisions': {'wait': False}}
        result = _parse_and_merge(json.dumps(handoff), wait=True)
        self.assertTrue(result['merged']['wait'])


class TestTrackAttempt(unittest.TestCase):
    """Test pr_doctor.py track-attempt via direct import."""

    def test_first_attempt_proceeds(self):
        """Test that the first attempt (current=0) should proceed."""
        result = check_attempt('build', 0, 3)
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['proceed'])
        self.assertEqual(result['attempt'], 1)
        self.assertEqual(result['remaining'], 2)
        self.assertEqual(result['category'], 'build')

    def test_last_attempt_proceeds(self):
        """Test that the last attempt (current=2 with max=3) proceeds."""
        result = check_attempt('sonar', 2, 3)
        self.assertTrue(result['proceed'])
        self.assertEqual(result['attempt'], 3)
        self.assertEqual(result['remaining'], 0)

    def test_exceeds_max_stops(self):
        """Test that exceeding max attempts stops."""
        result = check_attempt('reviews', 3, 3)
        self.assertFalse(result['proceed'])
        self.assertEqual(result['attempt'], 4)
        self.assertEqual(result['remaining'], 0)
        self.assertIn('reached max', result['reason'])

    def test_custom_max_attempts(self):
        """Test with custom max-attempts value."""
        result = check_attempt('build', 4, 5)
        self.assertTrue(result['proceed'])
        self.assertEqual(result['attempt'], 5)
        self.assertEqual(result['remaining'], 0)

    def test_default_max_attempts(self):
        """Test that default max-attempts is 3."""
        result = check_attempt('build', 0, 3)
        self.assertEqual(result['max_attempts'], 3)


class TestDiagnose(unittest.TestCase):
    """Test pr_doctor.py diagnose via direct import."""

    def test_all_pass(self):
        """Test diagnosis with no issues."""
        result = diagnose_pr(build_status='success')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['overall'], 'pass')
        self.assertEqual(result['build_status'], 'PASS')
        self.assertEqual(result['review_comments'], 0)
        self.assertEqual(result['sonar_issues'], 0)
        self.assertEqual(len(result['issues']), 0)

    def test_build_failure(self):
        """Test diagnosis with build failure."""
        result = diagnose_pr(
            build_status='failure',
            build_failures=[{'step': 'test', 'message': '3 tests failed'}],
        )
        self.assertEqual(result['overall'], 'fail')
        self.assertEqual(result['build_status'], 'FAIL')
        self.assertTrue(any(i['category'] == 'build' for i in result['issues']))
        self.assertTrue(any('build' in a.lower() for a in result['recommended_actions']))

    def test_review_comments(self):
        """Test diagnosis with unresolved review comments."""
        result = diagnose_pr(
            review_comments=[
                {'priority': 'high', 'body': 'Fix this'},
                {'priority': 'low', 'body': 'Nit'},
            ]
        )
        self.assertEqual(result['overall'], 'fail')
        self.assertEqual(result['review_comments'], 2)
        review_issue = next(i for i in result['issues'] if i['category'] == 'reviews')
        self.assertEqual(review_issue['severity'], 'high')

    def test_sonar_issues(self):
        """Test diagnosis with Sonar issues."""
        result = diagnose_pr(
            sonar_issues=[
                {'severity': 'BLOCKER', 'rule': 'java:S1234'},
                {'severity': 'MAJOR', 'rule': 'java:S5678'},
                {'severity': 'MINOR', 'rule': 'java:S9012'},
            ]
        )
        self.assertEqual(result['sonar_issues'], 3)
        sonar_issue = next(i for i in result['issues'] if i['category'] == 'sonar')
        self.assertEqual(sonar_issue['severity'], 'high')  # Has blocker

    def test_combined_diagnosis(self):
        """Test diagnosis with all three categories."""
        result = diagnose_pr(
            build_status='failure',
            build_failures=[{'step': 'compile', 'message': 'error'}],
            review_comments=[{'priority': 'medium'}],
            sonar_issues=[{'severity': 'MAJOR'}],
        )
        self.assertEqual(result['overall'], 'fail')
        categories = {i['category'] for i in result['issues']}
        self.assertEqual(categories, {'build', 'reviews', 'sonar'})
        self.assertEqual(len(result['recommended_actions']), 3)

    def test_build_pass_with_review_issues(self):
        """Test diagnosis with passing build but unresolved review comments (#52)."""
        result = diagnose_pr(
            build_status='success',
            review_comments=[{'priority': 'high', 'body': 'Fix this'}],
        )
        self.assertEqual(result['overall'], 'fail')  # Still fail due to reviews
        self.assertEqual(result['build_status'], 'PASS')
        self.assertEqual(result['review_comments'], 1)
        categories = {i['category'] for i in result['issues']}
        self.assertIn('reviews', categories)
        self.assertNotIn('build', categories)

    def test_no_inputs_is_pass(self):
        """Test that diagnose with no inputs reports pass."""
        result = diagnose_pr()
        self.assertEqual(result['overall'], 'pass')
        self.assertEqual(result['build_status'], 'UNKNOWN')

    def test_sonar_severity_breakdown(self):
        """Test that Sonar diagnosis includes severity breakdown."""
        result = diagnose_pr(
            sonar_issues=[
                {'severity': 'CRITICAL'},
                {'severity': 'CRITICAL'},
                {'severity': 'MAJOR'},
            ]
        )
        sonar_issue = next(i for i in result['issues'] if i['category'] == 'sonar')
        self.assertEqual(sonar_issue['breakdown']['CRITICAL'], 2)
        self.assertEqual(sonar_issue['breakdown']['MAJOR'], 1)


class TestDiagnoseBuildSeverity(unittest.TestCase):
    """Test that build failure severity varies by step type (#46)."""

    def test_lint_failure_is_medium(self):
        """Lint failure should be medium severity, not high."""
        result = diagnose_pr(
            build_status='failure',
            build_failures=[{'step': 'lint', 'message': 'ESLint errors'}],
        )
        build_issue = next(i for i in result['issues'] if i['category'] == 'build')
        self.assertEqual(build_issue['severity'], 'medium')

    def test_compile_failure_is_high(self):
        """Compile failure should be high severity."""
        result = diagnose_pr(
            build_status='failure',
            build_failures=[{'step': 'compile', 'message': 'Compilation error'}],
        )
        build_issue = next(i for i in result['issues'] if i['category'] == 'build')
        self.assertEqual(build_issue['severity'], 'high')

    def test_unknown_step_defaults_to_high(self):
        """Unknown step type should default to high severity."""
        result = diagnose_pr(
            build_status='failure',
            build_failures=[{'step': 'unknown', 'message': 'Something failed'}],
        )
        build_issue = next(i for i in result['issues'] if i['category'] == 'build')
        self.assertEqual(build_issue['severity'], 'high')


class TestDiagnoseEdgeCases(unittest.TestCase):
    """Test pr_doctor.py diagnose edge cases."""

    def test_build_status_none_with_failures_skips_build(self):
        """When build_status is None, build failures are ignored."""
        result = diagnose_pr(
            build_failures=[{'step': 'test', 'message': 'fails'}],
        )
        self.assertEqual(result['build_status'], 'UNKNOWN')
        build_issues = [i for i in result['issues'] if i['category'] == 'build']
        self.assertEqual(len(build_issues), 0)


class TestDiagnoseInputValidation(unittest.TestCase):
    """Test pr_doctor.py diagnose input validation for malformed data."""

    def test_diagnose_build_failures_missing_keys(self):
        """Test diagnose handles build failures without expected keys."""
        result = diagnose_pr(
            build_status='failure',
            build_failures=[{'unexpected_key': 'value'}],
        )
        self.assertEqual(result['status'], 'success')
        build_issue = next(i for i in result['issues'] if i['category'] == 'build')
        self.assertEqual(build_issue['step'], 'unknown')
        self.assertEqual(build_issue['detail'], 'Build failure')

    def test_diagnose_review_comments_non_dict_entries(self):
        """Test diagnose handles non-dict entries in review comments array."""
        result = diagnose_pr(
            review_comments=[
                {'priority': 'high'},
                'not-a-dict',
                42,
            ]
        )
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['review_comments'], 3)

    def test_diagnose_sonar_issues_non_dict_entries(self):
        """Test diagnose handles non-dict entries in sonar issues array."""
        result = diagnose_pr(
            sonar_issues=[
                {'severity': 'MAJOR'},
                'invalid-entry',
            ]
        )
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['sonar_issues'], 2)

    def test_diagnose_build_failures_non_dict_entries(self):
        """Test diagnose handles non-dict entries in build failures array."""
        result = diagnose_pr(
            build_status='failure',
            build_failures=['not-a-dict', 42],
        )
        self.assertEqual(result['status'], 'success')
        for issue in result['issues']:
            if issue['category'] == 'build':
                self.assertEqual(issue['step'], 'unknown')


class TestHandoffSkipSonar(unittest.TestCase):
    """Test parse-handoff with skip_sonar field (#31)."""

    def test_skip_sonar_true(self):
        """Test that skip_sonar is extracted from handoff decisions."""
        handoff = {'decisions': {'skip_sonar': True}}
        result = _parse_and_merge(json.dumps(handoff))
        self.assertTrue(result['merged']['skip_sonar'])

    def test_skip_sonar_defaults_false(self):
        """Test that skip_sonar defaults to False when not in handoff."""
        handoff = {'artifacts': {'pr_number': 1}}
        result = _parse_and_merge(json.dumps(handoff))
        self.assertFalse(result['merged']['skip_sonar'])


class TestHandoffAutomatedReview(unittest.TestCase):
    """Test parse-handoff with automated_review field (#32)."""

    def test_automated_review_true(self):
        """Test that automated_review is extracted from handoff decisions."""
        handoff = {'decisions': {'automated_review': True}}
        result = _parse_and_merge(json.dumps(handoff))
        self.assertTrue(result['merged']['automated_review'])

    def test_automated_review_defaults_false(self):
        """Test that automated_review defaults to False when not in handoff."""
        handoff = {'artifacts': {'pr_number': 1}}
        result = _parse_and_merge(json.dumps(handoff))
        self.assertFalse(result['merged']['automated_review'])


class TestHandoffSemanticValidation(unittest.TestCase):
    """Test that contradictory handoff values generate warnings (#41)."""

    def test_checks_sonar_with_skip_sonar_warns(self):
        """checks=sonar + skip_sonar=true is contradictory — should warn."""
        handoff = {'decisions': {'checks': 'sonar', 'skip_sonar': True}}
        result = _parse_and_merge(json.dumps(handoff))
        warnings = result['validation']['warnings']
        self.assertTrue(
            any('sonar' in w.lower() and ('skip' in w.lower() or 'contradict' in w.lower()) for w in warnings),
            f'Expected contradiction warning about sonar, got: {warnings}',
        )


# =============================================================================
# Subprocess (Tier 3) tests — CLI plumbing only
# =============================================================================


def run_doctor_script(args: list) -> tuple:
    """Run pr_doctor.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


class TestMain(unittest.TestCase):
    """Test pr_doctor.py main entry point (CLI plumbing)."""

    def test_no_subcommand(self):
        """Test error when no subcommand provided."""
        _, stderr, code = run_doctor_script([])
        self.assertNotEqual(code, 0)

    def test_help(self):
        """Test help output."""
        stdout, _, code = run_doctor_script(['--help'])
        self.assertEqual(code, 0)
        self.assertIn('parse-handoff', stdout)
        self.assertIn('track-attempt', stdout)
        self.assertIn('diagnose', stdout)

    def test_invalid_category(self):
        """Test that invalid category is rejected by argparse."""
        _, stderr, code = run_doctor_script(
            [
                'track-attempt',
                '--category',
                'invalid',
                '--current',
                '0',
            ]
        )
        self.assertNotEqual(code, 0)
        self.assertIn('invalid', stderr)


if __name__ == '__main__':
    unittest.main()
