#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for build_format.py module."""

import json

import _build_format as _build_format_mod
import _build_parse as _build_parse_mod
import pytest

CORE_FIELDS = _build_format_mod.CORE_FIELDS
EXTRA_FIELDS = _build_format_mod.EXTRA_FIELDS
STRUCTURED_FIELDS = _build_format_mod.STRUCTURED_FIELDS
format_json = _build_format_mod.format_json
format_toon = _build_format_mod.format_toon

SEVERITY_ERROR = _build_parse_mod.SEVERITY_ERROR
SEVERITY_WARNING = _build_parse_mod.SEVERITY_WARNING
Issue = _build_parse_mod.Issue
UnitTestSummary = _build_parse_mod.UnitTestSummary

#: The log path the success rendering asserts verbatim, so the table and the
#: expected fragment cannot drift apart.
SUCCESS_LOG_FILE = '.plan/local/plans/my-plan/build-results/default/maven.log'


def _result(**overrides) -> dict:
    """A failed-build result carrying the five core fields, plus any overrides.

    Every rendering case starts from the same core envelope and states only what
    it varies, so a row reads as the difference it is about rather than as a
    twentieth copy of the same five keys.
    """
    return {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 23,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        **overrides,
    }


def _success_result(**overrides) -> dict:
    """A green-build result: the same envelope with a zero exit and a longer run."""
    return _result(status='success', exit_code=0, duration_seconds=45, **overrides)


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


#: ``(result, the fragments the rendering must contain)``. The Issue / summary
#: rows sit beside their plain-dict twins on purpose: the formatter accepts both
#: shapes, and a row for only one of them would leave the object path uncovered.
_TOON_RENDERING_CASES = [
    (
        _success_result(log_file=SUCCESS_LOG_FILE),
        [
            'status: success',
            'exit_code: 0',
            'duration_seconds: 45',
            f'log_file: {SUCCESS_LOG_FILE}',
            'command: ./mvnw clean verify',
        ],
    ),
    (_success_result(wrapper='./mvnw'), ['wrapper: ./mvnw']),
    (_result(error='build_failed'), ['status: error', 'error: build_failed']),
    (
        _result(
            error='build_failed',
            errors=[
                {
                    'file': 'src/Main.java',
                    'line': 15,
                    'message': 'cannot find symbol',
                    'category': 'compilation',
                },
                {
                    'file': 'src/Test.java',
                    'line': 42,
                    'message': 'test failed',
                    'category': 'test_failure',
                },
            ],
        ),
        [
            'errors[2]{file,line,message,category}:',
            '  src/Main.java,15,cannot find symbol,compilation',
            '  src/Test.java,42,test failed,test_failure',
        ],
    ),
    (
        _result(
            errors=[
                Issue(
                    file='src/Main.java',
                    line=15,
                    message='cannot find symbol',
                    severity=SEVERITY_ERROR,
                    category='compilation',
                ),
            ]
        ),
        [
            'errors[1]{file,line,message,category}:',
            '  src/Main.java,15,cannot find symbol,compilation',
        ],
    ),
    (
        _result(
            errors=[
                {
                    'file': 'pom.xml',
                    'line': None,
                    'message': 'dependency error',
                    'category': 'dependency',
                },
            ]
        ),
        ['  pom.xml,-,dependency error,dependency'],
    ),
    (
        _result(warnings=[{'file': 'pom.xml', 'line': None, 'message': 'deprecated version'}]),
        ['warnings[1]{file,line,message}:', '  pom.xml,-,deprecated version'],
    ),
    (
        _result(
            warnings=[
                {
                    'file': 'pom.xml',
                    'line': None,
                    'message': 'deprecated version',
                    'accepted': False,
                },
                {
                    'file': 'src/Util.java',
                    'line': 10,
                    'message': 'unchecked cast',
                    'accepted': True,
                },
            ]
        ),
        [
            'warnings[2]{file,line,message,accepted}:',
            '  pom.xml,-,deprecated version,',
            '  src/Util.java,10,unchecked cast,[accepted]',
        ],
    ),
    (
        _result(
            warnings=[
                Issue(
                    file='pom.xml',
                    line=None,
                    message='deprecated version',
                    severity=SEVERITY_WARNING,
                    accepted=True,
                ),
            ]
        ),
        ['warnings[1]{file,line,message,accepted}:', '[accepted]'],
    ),
    (
        _result(tests={'passed': 10, 'failed': 2, 'skipped': 1}),
        ['tests:', '  passed: 10', '  failed: 2', '  skipped: 1'],
    ),
    (
        _result(tests=UnitTestSummary(passed=10, failed=2, skipped=1, total=13)),
        ['tests:', '  passed: 10', '  failed: 2', '  skipped: 1'],
    ),
    (
        _result(
            status='timeout',
            exit_code=-1,
            duration_seconds=300,
            error='timeout',
            timeout_used_seconds=300,
        ),
        ['status: timeout', 'error: timeout', 'timeout_used_seconds: 300'],
    ),
]

_TOON_RENDERING_IDS = [
    'success-core-fields',
    'extra-field-after-the-core-fields',
    'error-field-on-an-error-result',
    'errors-list-of-dicts',
    'errors-list-of-issue-objects',
    'error-row-with-a-null-line-renders-a-dash',
    'warnings-actionable-mode-has-no-accepted-column',
    'warnings-structured-mode-carries-the-accepted-column',
    'warnings-list-of-issue-objects',
    'tests-summary-as-a-dict',
    'tests-summary-as-a-unit-test-summary-object',
    'timeout-result',
]


@pytest.mark.parametrize('result,fragments', _TOON_RENDERING_CASES, ids=_TOON_RENDERING_IDS)
def test_format_toon_renders(result: dict, fragments: list[str]):
    output = format_toon(result)

    for fragment in fragments:
        assert fragment in output, output


def test_format_toon_success_field_order():
    """Fields appear in correct order."""
    result = {
        'command': './mvnw clean verify',
        'status': 'success',
        'log_file': SUCCESS_LOG_FILE,
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


#: ``(empty section payload, the token that must NOT appear)``. An empty section
#: is omitted rather than rendered as a zero-length block, so the assertion is an
#: absence in each row.
_EMPTY_SECTION_CASES = [
    ({'errors': []}, 'errors'),
    ({'warnings': []}, 'warnings'),
    ({'tests': {}}, 'tests:'),
]

_EMPTY_SECTION_IDS = ['empty-errors-list', 'empty-warnings-list', 'empty-tests-dict']


@pytest.mark.parametrize('section,absent', _EMPTY_SECTION_CASES, ids=_EMPTY_SECTION_IDS)
def test_format_toon_omits_an_empty_section(section: dict, absent: str):
    output = format_toon(_success_result(**section))

    assert absent not in output, output


def test_format_json_success_basic():
    """Formats success result as JSON."""
    parsed = json.loads(format_json(_success_result()))

    assert parsed['status'] == 'success'
    assert parsed['exit_code'] == 0
    assert parsed['duration_seconds'] == 45


def test_format_json_with_errors():
    """Formats error result with errors list."""
    result = _result(errors=[{'file': 'src/Main.java', 'line': 15, 'message': 'cannot find symbol'}])

    parsed = json.loads(format_json(result))

    assert len(parsed['errors']) == 1
    assert parsed['errors'][0]['file'] == 'src/Main.java'


def test_format_json_with_issue_objects():
    """Converts Issue objects to dicts."""
    result = _result(
        errors=[
            Issue(
                file='src/Main.java',
                line=15,
                message='cannot find symbol',
                severity=SEVERITY_ERROR,
                category='compilation',
            ),
        ]
    )

    parsed = json.loads(format_json(result))

    assert parsed['errors'][0]['file'] == 'src/Main.java'
    assert parsed['errors'][0]['severity'] == 'error'
    assert parsed['errors'][0]['category'] == 'compilation'


def test_format_json_with_testsummary_object():
    """Converts UnitTestSummary object to dict."""
    result = _result(tests=UnitTestSummary(passed=10, failed=2, skipped=1, total=13))

    parsed = json.loads(format_json(result))

    assert parsed['tests']['passed'] == 10
    assert parsed['tests']['failed'] == 2
    assert parsed['tests']['skipped'] == 1
    assert parsed['tests']['total'] == 13


def test_format_json_indentation():
    """Produces indented JSON."""
    output = format_json({'status': 'success', 'exit_code': 0}, indent=2)

    assert '\n' in output
    assert '  ' in output


def test_format_json_valid():
    """Output is valid JSON."""
    result = _result(
        error='build_failed',
        errors=[
            Issue(
                file='src/Main.java',
                line=15,
                message='cannot find symbol',
                severity=SEVERITY_ERROR,
                category='compilation',
            ),
        ],
        warnings=[
            Issue(
                file='pom.xml',
                line=None,
                message='deprecated',
                severity=SEVERITY_WARNING,
                accepted=True,
            ),
        ],
        tests=UnitTestSummary(passed=10, failed=2, skipped=1, total=13),
    )

    parsed = json.loads(format_json(result))

    assert isinstance(parsed, dict)
