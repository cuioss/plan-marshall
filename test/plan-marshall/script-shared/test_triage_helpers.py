#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for triage_helpers.py shared module."""

import json

import pytest
from toon_parser import parse_toon
from triage_helpers import (
    ErrorCode,
    calculate_priority,
    create_workflow_cli,
    is_test_file,
    load_config_file,
    load_skill_config,
    make_error,
    parse_json_arg,
    print_error,
    print_toon,
)


def test_make_error_basic():
    """Test basic error creation."""
    result = make_error('something failed')
    assert result['error'] == 'something failed'
    assert result['status'] == 'error'
    assert 'error_code' not in result


def test_make_error_with_code():
    """Test error creation with error code."""
    result = make_error('not found', code=ErrorCode.NOT_FOUND)
    assert result['error_code'] == 'NOT_FOUND'
    assert result['status'] == 'error'


def test_make_error_with_extra_fields():
    """Test error creation with additional context."""
    result = make_error('parse error', code=ErrorCode.PARSE_ERROR, file='/tmp/x.json')
    assert result['file'] == '/tmp/x.json'
    assert result['error_code'] == 'PARSE_ERROR'


def test_print_toon_success(capsys):
    """Test print_toon returns 0 for success."""
    rc = print_toon({'status': 'success', 'data': 'hello'})
    assert rc == 0
    captured = capsys.readouterr()
    result = parse_toon(captured.out)
    assert result['status'] == 'success'


def test_print_toon_failure(capsys):
    """Test print_toon returns 0 for failure (exit code reserved for uncaught exceptions)."""
    rc = print_toon({'status': 'error', 'error': 'bad'})
    assert rc == 0


def test_print_toon_missing_status(capsys):
    """Test print_toon returns 0 when status is missing."""
    rc = print_toon({'data': 'no status'})
    assert rc == 0


def test_print_error(capsys):
    """Test print_error always returns 0 (exit code reserved for uncaught exceptions)."""
    rc = print_error('oops', code=ErrorCode.INVALID_INPUT)
    assert rc == 0
    captured = capsys.readouterr()
    result = parse_toon(captured.out)
    assert result['error'] == 'oops'
    assert result['error_code'] == 'INVALID_INPUT'


def test_safe_main_is_file_ops_reexport():
    """triage_helpers.safe_main is the canonical file_ops.safe_main.

    The workflow subsystem does not define its own entry-point wrapper — it
    re-exports the single canonical implementation. Its decorator behaviour
    (status:error TOON on stdout, exit 1 on crash) is pinned by
    ``tools-file-ops/test_file_ops.py``.
    """
    import file_ops
    import triage_helpers

    assert triage_helpers.safe_main is file_ops.safe_main


#: ``(raw argument, parsed value — ``None`` when the argument is rejected)``. A
#: rejected argument returns an error envelope AND a ``None`` value; an accepted
#: one returns the value and no envelope.
_PARSE_JSON_ARG_CASES = [
    ('{"key": "val"}', {'key': 'val'}),
    ('[1, 2, 3]', [1, 2, 3]),
    ('not-json', None),
]

_PARSE_JSON_ARG_IDS = ['an-object', 'an-array', 'not-json-at-all']


@pytest.mark.parametrize('raw,expected', _PARSE_JSON_ARG_CASES, ids=_PARSE_JSON_ARG_IDS)
def test_parse_json_arg(raw: str, expected):
    val, err = parse_json_arg(raw, '--data')

    assert val == expected
    if expected is None:
        assert err is not None
        assert err['status'] == 'error'
    else:
        assert err is None


#: The config body used by the accepted row, stated once so the row and its
#: expectation cannot drift apart.
_VALID_CONFIG = {'key': 'value', 'count': 42}

#: ``(file content — ``None`` when the file is never written, the config
#: loaded)``. Both unusable shapes degrade to the empty dict rather than raising,
#: so the caller always receives a mapping.
_LOAD_CONFIG_CASES = [
    (None, {}),
    (json.dumps(_VALID_CONFIG), _VALID_CONFIG),
    ('not json {{{', {}),
]

_LOAD_CONFIG_IDS = ['no-file-at-all', 'a-well-formed-config', 'a-file-that-is-not-json']


@pytest.mark.parametrize('content,expected', _LOAD_CONFIG_CASES, ids=_LOAD_CONFIG_IDS)
def test_load_config_file(tmp_path, content: str | None, expected: dict):
    config_path = tmp_path / 'config.json'
    if content is not None:
        config_path.write_text(content)

    assert load_config_file(config_path, 'test') == expected


def test_load_skill_config_resolves_path(tmp_path):
    """Test load_skill_config computes correct path from script location."""
    # Fixture layout: tmp_path/skill-name/scripts/script.py alongside
    # tmp_path/skill-name/standards/config.json.
    scripts_dir = tmp_path / 'skill-name' / 'scripts'
    scripts_dir.mkdir(parents=True)
    standards_dir = tmp_path / 'skill-name' / 'standards'
    standards_dir.mkdir(parents=True)

    config = {'setting': True}
    (standards_dir / 'my-config.json').write_text(json.dumps(config))

    script_file = str(scripts_dir / 'my_script.py')
    result = load_skill_config(script_file, 'my-config.json')
    assert result == config


#: ``(priority, boost — ``None`` calls WITHOUT the argument so the default is
#: exercised, resulting priority)``. The ±5 rows are the clamps: a boost past
#: either end of the ladder stops at that end rather than running off it.
_PRIORITY_CASES = [
    ('low', None, 'low'),
    ('critical', None, 'critical'),
    ('low', 1, 'medium'),
    ('medium', 1, 'high'),
    ('high', 1, 'critical'),
    ('critical', -1, 'high'),
    ('medium', -1, 'low'),
    ('critical', 5, 'critical'),
    ('low', -5, 'low'),
]

_PRIORITY_IDS = [
    'low-unboosted',
    'critical-unboosted',
    'low-up-one',
    'medium-up-one',
    'high-up-one',
    'critical-down-one',
    'medium-down-one',
    'clamped-at-the-top',
    'clamped-at-the-bottom',
]


@pytest.mark.parametrize('priority,boost,expected', _PRIORITY_CASES, ids=_PRIORITY_IDS)
def test_calculate_priority(priority: str, boost: int | None, expected: str):
    resolved = calculate_priority(priority) if boost is None else calculate_priority(priority, boost)

    assert resolved == expected


#: ``(path, is it a test file?)`` across the four language conventions the
#: detector serves. Each language carries its own negative, so a detector that
#: answered True for everything fails on four rows rather than passing.
_TEST_FILE_CASES = [
    ('src/test/java/com/example/FooTest.java', True),
    ('FooTest.java', True),
    ('FooIT.java', True),
    ('src/main/java/com/example/Foo.java', False),
    ('test_foo.py', True),
    ('tests/test_bar.py', True),
    ('foo.py', False),
    ('Component.test.js', True),
    ('Component.spec.tsx', True),
    ('src/__tests__/Component.js', True),
    ('Component.js', False),
    ('handler_test.go', True),
    ('handler.go', False),
]

_TEST_FILE_IDS = [
    'java-test-under-src-test',
    'java-test-by-suffix',
    'java-integration-test-by-suffix',
    'java-production-source',
    'python-test-at-the-root',
    'python-test-under-tests',
    'python-production-source',
    'javascript-dot-test',
    'typescript-dot-spec',
    'javascript-under-dunder-tests',
    'javascript-production-source',
    'go-underscore-test',
    'go-production-source',
]


@pytest.mark.parametrize('path,expected', _TEST_FILE_CASES, ids=_TEST_FILE_IDS)
def test_is_test_file(path: str, expected: bool):
    assert bool(is_test_file(path)) is expected


def test_create_workflow_cli_basic():
    """Test CLI creation with a simple subcommand."""
    handler_called = {}

    def my_handler(args):
        handler_called['name'] = args.name
        return 0

    parser = create_workflow_cli(
        description='Test CLI',
        epilog='Example: test-cli greet --name World',
        subcommands=[
            {
                'name': 'greet',
                'help': 'Say hello',
                'handler': my_handler,
                'args': [{'flags': ['--name'], 'required': True, 'help': 'Name to greet'}],
            }
        ],
    )
    args = parser.parse_args(['greet', '--name', 'World'])
    rc = args.func(args)
    assert rc == 0
    assert handler_called['name'] == 'World'


def test_create_workflow_cli_multiple_subcommands():
    """Test CLI with multiple subcommands."""
    parser = create_workflow_cli(
        description='Multi CLI',
        epilog='',
        subcommands=[
            {'name': 'sub1', 'help': 'First', 'handler': lambda a: 0, 'args': []},
            {'name': 'sub2', 'help': 'Second', 'handler': lambda a: 1, 'args': []},
        ],
    )
    args1 = parser.parse_args(['sub1'])
    assert args1.func(args1) == 0

    args2 = parser.parse_args(['sub2'])
    assert args2.func(args2) == 1


def test_error_code_fetch_failure_exists():
    """Verify the FETCH_FAILURE error code is defined."""
    assert hasattr(ErrorCode, 'FETCH_FAILURE')
    assert ErrorCode.FETCH_FAILURE == 'FETCH_FAILURE'
