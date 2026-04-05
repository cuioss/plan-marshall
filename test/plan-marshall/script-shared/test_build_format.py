#!/usr/bin/env python3
"""Tests for build_format.py module."""

# Tier 2 direct imports via importlib for uniform import style
import importlib.util  # noqa: E402
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'script-shared' / 'scripts' / 'build'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_build_format_mod = _load_module('_build_format', '_build_format.py')
_build_parse_mod = _load_module('_build_parse', '_build_parse.py')

CORE_FIELDS = _build_format_mod.CORE_FIELDS
EXTRA_FIELDS = _build_format_mod.EXTRA_FIELDS
STRUCTURED_FIELDS = _build_format_mod.STRUCTURED_FIELDS
format_json = _build_format_mod.format_json
format_toon = _build_format_mod.format_toon

SEVERITY_ERROR = _build_parse_mod.SEVERITY_ERROR
SEVERITY_WARNING = _build_parse_mod.SEVERITY_WARNING
Issue = _build_parse_mod.Issue
UnitTestSummary = _build_parse_mod.UnitTestSummary

# =============================================================================
# Constants Tests
# =============================================================================


def test_core_fields_order():
    """CORE_FIELDS has expected fields in order."""
    expected = ['status', 'exit_code', 'duration_seconds', 'log_file', 'command']
    assert CORE_FIELDS == expected


def test_extra_fields():
    """EXTRA_FIELDS contains expected fields."""
    assert 'error' in EXTRA_FIELDS
    assert 'timeout_used_seconds' in EXTRA_FIELDS


def test_structured_fields():
    """STRUCTURED_FIELDS contains expected fields."""
    assert 'errors' in STRUCTURED_FIELDS
    assert 'warnings' in STRUCTURED_FIELDS
    assert 'tests' in STRUCTURED_FIELDS


# =============================================================================
# format_toon Tests - Success Cases
# =============================================================================


def test_format_toon_success_basic():
    """Formats success result with colon-space separators."""
    result = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 45,
        'log_file': '.plan/temp/build-output/default/maven.log',
        'command': './mvnw clean verify',
    }
    output = format_toon(result)

    assert 'status: success' in output
    assert 'exit_code: 0' in output
    assert 'duration_seconds: 45' in output
    assert 'log_file: .plan/temp/build-output/default/maven.log' in output
    assert 'command: ./mvnw clean verify' in output


def test_format_toon_success_field_order():
    """Fields appear in correct order."""
    result = {
        'command': './mvnw clean verify',
        'status': 'success',
        'log_file': '.plan/temp/build-output/default/maven.log',
        'exit_code': 0,
        'duration_seconds': 45,
    }
    output = format_toon(result)
    lines = output.split('\n')

    assert lines[0].startswith('status: ')
    assert lines[1].startswith('exit_code: ')
    assert lines[2].startswith('duration_seconds: ')
    assert lines[3].startswith('log_file: ')
    assert lines[4].startswith('command: ')


def test_format_toon_with_extra_fields():
    """Extra fields appear after core fields."""
    result = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 45,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'wrapper': './mvnw',
    }
    output = format_toon(result)

    assert 'wrapper: ./mvnw' in output


# =============================================================================
# format_toon Tests - Error Cases
# =============================================================================


def test_format_toon_error_with_error_field():
    """Error field appears for error results."""
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 23,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'error': 'build_failed',
    }
    output = format_toon(result)

    assert 'status: error' in output
    assert 'error: build_failed' in output


def test_format_toon_error_with_errors_list():
    """Formats errors list section."""
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 23,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'error': 'build_failed',
        'errors': [
            {'file': 'src/Main.java', 'line': 15, 'message': 'cannot find symbol', 'category': 'compilation'},
            {'file': 'src/Test.java', 'line': 42, 'message': 'test failed', 'category': 'test_failure'},
        ],
    }
    output = format_toon(result)

    assert 'errors[2]{file,line,message,category}:' in output
    assert '  src/Main.java,15,cannot find symbol,compilation' in output
    assert '  src/Test.java,42,test failed,test_failure' in output


def test_format_toon_errors_with_issue_objects():
    """Handles Issue objects in errors list."""
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 23,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'errors': [
            Issue(
                file='src/Main.java',
                line=15,
                message='cannot find symbol',
                severity=SEVERITY_ERROR,
                category='compilation',
            ),
        ],
    }
    output = format_toon(result)

    assert 'errors[1]{file,line,message,category}:' in output
    assert '  src/Main.java,15,cannot find symbol,compilation' in output


def test_format_toon_errors_null_line():
    """Handles null line number as dash."""
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 23,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'errors': [
            {'file': 'pom.xml', 'line': None, 'message': 'dependency error', 'category': 'dependency'},
        ],
    }
    output = format_toon(result)

    assert '  pom.xml,-,dependency error,dependency' in output


# =============================================================================
# format_toon Tests - Warnings
# =============================================================================


def test_format_toon_warnings_actionable_mode():
    """Formats warnings without accepted field (actionable mode)."""
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 23,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'warnings': [
            {'file': 'pom.xml', 'line': None, 'message': 'deprecated version'},
        ],
    }
    output = format_toon(result)

    assert 'warnings[1]{file,line,message}:' in output
    assert '  pom.xml,-,deprecated version' in output


def test_format_toon_warnings_structured_mode():
    """Formats warnings with accepted field (structured mode)."""
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 23,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'warnings': [
            {'file': 'pom.xml', 'line': None, 'message': 'deprecated version', 'accepted': False},
            {'file': 'src/Util.java', 'line': 10, 'message': 'unchecked cast', 'accepted': True},
        ],
    }
    output = format_toon(result)

    assert 'warnings[2]{file,line,message,accepted}:' in output
    assert '  pom.xml,-,deprecated version,' in output
    assert '  src/Util.java,10,unchecked cast,[accepted]' in output


def test_format_toon_warnings_with_issue_objects():
    """Handles Issue objects in warnings list."""
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 23,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'warnings': [
            Issue(file='pom.xml', line=None, message='deprecated version', severity=SEVERITY_WARNING, accepted=True),
        ],
    }
    output = format_toon(result)

    assert 'warnings[1]{file,line,message,accepted}:' in output
    assert '[accepted]' in output


# =============================================================================
# format_toon Tests - Tests Section
# =============================================================================


def test_format_toon_tests_section():
    """Formats tests summary section."""
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 23,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'tests': {'passed': 10, 'failed': 2, 'skipped': 1},
    }
    output = format_toon(result)

    assert 'tests:' in output
    assert '  passed: 10' in output
    assert '  failed: 2' in output
    assert '  skipped: 1' in output


def test_format_toon_tests_with_testsummary_object():
    """Handles UnitTestSummary object."""
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 23,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'tests': UnitTestSummary(passed=10, failed=2, skipped=1, total=13),
    }
    output = format_toon(result)

    assert 'tests:' in output
    assert '  passed: 10' in output
    assert '  failed: 2' in output
    assert '  skipped: 1' in output


# =============================================================================
# format_toon Tests - Empty/Missing Sections
# =============================================================================


def test_format_toon_empty_errors():
    """Empty errors list is not included."""
    result = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 45,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'errors': [],
    }
    output = format_toon(result)

    assert 'errors' not in output


def test_format_toon_empty_warnings():
    """Empty warnings list is not included."""
    result = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 45,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'warnings': [],
    }
    output = format_toon(result)

    assert 'warnings' not in output


def test_format_toon_empty_tests():
    """Empty tests dict is not included."""
    result = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 45,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'tests': {},
    }
    output = format_toon(result)

    assert 'tests:' not in output


# =============================================================================
# format_toon Tests - Timeout
# =============================================================================


def test_format_toon_timeout():
    """Formats timeout result."""
    result = {
        'status': 'timeout',
        'exit_code': -1,
        'duration_seconds': 300,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'error': 'timeout',
        'timeout_used_seconds': 300,
    }
    output = format_toon(result)

    assert 'status: timeout' in output
    assert 'error: timeout' in output
    assert 'timeout_used_seconds: 300' in output


# =============================================================================
# format_json Tests
# =============================================================================


def test_format_json_success_basic():
    """Formats success result as JSON."""
    result = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 45,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
    }
    output = format_json(result)
    parsed = json.loads(output)

    assert parsed['status'] == 'success'
    assert parsed['exit_code'] == 0
    assert parsed['duration_seconds'] == 45


def test_format_json_with_errors():
    """Formats error result with errors list."""
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 23,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'errors': [
            {'file': 'src/Main.java', 'line': 15, 'message': 'cannot find symbol'},
        ],
    }
    output = format_json(result)
    parsed = json.loads(output)

    assert len(parsed['errors']) == 1
    assert parsed['errors'][0]['file'] == 'src/Main.java'


def test_format_json_with_issue_objects():
    """Converts Issue objects to dicts."""
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 23,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'errors': [
            Issue(
                file='src/Main.java',
                line=15,
                message='cannot find symbol',
                severity=SEVERITY_ERROR,
                category='compilation',
            ),
        ],
    }
    output = format_json(result)
    parsed = json.loads(output)

    assert parsed['errors'][0]['file'] == 'src/Main.java'
    assert parsed['errors'][0]['severity'] == 'error'
    assert parsed['errors'][0]['category'] == 'compilation'


def test_format_json_with_testsummary_object():
    """Converts UnitTestSummary object to dict."""
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 23,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'tests': UnitTestSummary(passed=10, failed=2, skipped=1, total=13),
    }
    output = format_json(result)
    parsed = json.loads(output)

    assert parsed['tests']['passed'] == 10
    assert parsed['tests']['failed'] == 2
    assert parsed['tests']['skipped'] == 1
    assert parsed['tests']['total'] == 13


def test_format_json_indentation():
    """Produces indented JSON."""
    result = {'status': 'success', 'exit_code': 0}
    output = format_json(result, indent=2)

    assert '\n' in output
    assert '  ' in output


def test_format_json_valid():
    """Output is valid JSON."""
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 23,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'error': 'build_failed',
        'errors': [
            Issue(
                file='src/Main.java',
                line=15,
                message='cannot find symbol',
                severity=SEVERITY_ERROR,
                category='compilation',
            ),
        ],
        'warnings': [
            Issue(file='pom.xml', line=None, message='deprecated', severity=SEVERITY_WARNING, accepted=True),
        ],
        'tests': UnitTestSummary(passed=10, failed=2, skipped=1, total=13),
    }
    output = format_json(result)

    # Should not raise
    parsed = json.loads(output)
    assert isinstance(parsed, dict)


if __name__ == '__main__':
    import traceback

    tests = [
        test_core_fields_order,
        test_extra_fields,
        test_structured_fields,
        test_format_toon_success_basic,
        test_format_toon_success_field_order,
        test_format_toon_with_extra_fields,
        test_format_toon_error_with_error_field,
        test_format_toon_error_with_errors_list,
        test_format_toon_errors_with_issue_objects,
        test_format_toon_errors_null_line,
        test_format_toon_warnings_actionable_mode,
        test_format_toon_warnings_structured_mode,
        test_format_toon_warnings_with_issue_objects,
        test_format_toon_tests_section,
        test_format_toon_tests_with_testsummary_object,
        test_format_toon_empty_errors,
        test_format_toon_empty_warnings,
        test_format_toon_empty_tests,
        test_format_toon_timeout,
        test_format_json_success_basic,
        test_format_json_with_errors,
        test_format_json_with_issue_objects,
        test_format_json_with_testsummary_object,
        test_format_json_indentation,
        test_format_json_valid,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception:
            failed += 1
            print(f'FAILED: {test.__name__}')
            traceback.print_exc()
            print()

    print(f'\nResults: {passed} passed, {failed} failed')
    sys.exit(0 if failed == 0 else 1)
