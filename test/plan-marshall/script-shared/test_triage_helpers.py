#!/usr/bin/env python3
"""Tests for triage_helpers.py shared module."""

import json

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
    safe_main,
)

# =============================================================================
# Test: make_error
# =============================================================================


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


# =============================================================================
# Test: print_toon
# =============================================================================


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


# =============================================================================
# Test: print_error
# =============================================================================


def test_print_error(capsys):
    """Test print_error always returns 0 (exit code reserved for uncaught exceptions)."""
    rc = print_error('oops', code=ErrorCode.INVALID_INPUT)
    assert rc == 0
    captured = capsys.readouterr()
    result = parse_toon(captured.out)
    assert result['error'] == 'oops'
    assert result['error_code'] == 'INVALID_INPUT'


# =============================================================================
# Test: safe_main
# =============================================================================


def test_safe_main_success():
    """Test safe_main passes through successful return code."""
    rc = safe_main(lambda: 0)
    assert rc == 0


def test_safe_main_nonzero():
    """Test safe_main passes through non-zero return code."""
    rc = safe_main(lambda: 42)
    assert rc == 42


def test_safe_main_exception(capsys):
    """Test safe_main catches exceptions and produces TOON error."""

    def boom():
        raise ValueError('test explosion')

    rc = safe_main(boom)
    assert rc == 1
    captured = capsys.readouterr()
    result = parse_toon(captured.out)
    assert 'test explosion' in result['error']
    # A9: traceback should be included
    assert 'traceback' in captured.out.lower() or 'ValueError' in captured.out


# =============================================================================
# Test: parse_json_arg
# =============================================================================


def test_parse_json_arg_success():
    """Test valid JSON parsing."""
    val, err = parse_json_arg('{"key": "val"}', '--data')
    assert err is None
    assert val == {'key': 'val'}


def test_parse_json_arg_invalid(capsys):
    """Test invalid JSON returns error dict."""
    val, err = parse_json_arg('not-json', '--data')
    assert err is not None
    assert err['status'] == 'error'
    assert val is None


def test_parse_json_arg_array():
    """Test JSON array parsing."""
    val, err = parse_json_arg('[1, 2, 3]', '--items')
    assert err is None
    assert val == [1, 2, 3]


# =============================================================================
# Test: load_config_file
# =============================================================================


def test_load_config_file_missing(tmp_path):
    """Test loading a missing config file returns empty dict."""
    result = load_config_file(tmp_path / 'nonexistent.json', 'test')
    assert result == {}


def test_load_config_file_valid(tmp_path):
    """Test loading a valid config file."""
    config = {'key': 'value', 'count': 42}
    config_path = tmp_path / 'test.json'
    config_path.write_text(json.dumps(config))
    result = load_config_file(config_path, 'test')
    assert result == config


def test_load_config_file_invalid_json(tmp_path):
    """Test loading an invalid JSON file returns empty dict."""
    config_path = tmp_path / 'bad.json'
    config_path.write_text('not json {{{')
    result = load_config_file(config_path, 'test')
    assert result == {}


# =============================================================================
# Test: load_skill_config
# =============================================================================


def test_load_skill_config_resolves_path(tmp_path):
    """Test load_skill_config computes correct path from script location."""
    # Create: tmp_path/skill-name/scripts/script.py
    #         tmp_path/skill-name/standards/config.json
    scripts_dir = tmp_path / 'skill-name' / 'scripts'
    scripts_dir.mkdir(parents=True)
    standards_dir = tmp_path / 'skill-name' / 'standards'
    standards_dir.mkdir(parents=True)

    config = {'setting': True}
    (standards_dir / 'my-config.json').write_text(json.dumps(config))

    script_file = str(scripts_dir / 'my_script.py')
    result = load_skill_config(script_file, 'my-config.json')
    assert result == config


# =============================================================================
# Test: calculate_priority
# =============================================================================


def test_calculate_priority_no_boost():
    """Test priority without boost."""
    assert calculate_priority('low') == 'low'
    assert calculate_priority('critical') == 'critical'


def test_calculate_priority_boost_up():
    """Test priority escalation."""
    assert calculate_priority('low', 1) == 'medium'
    assert calculate_priority('medium', 1) == 'high'
    assert calculate_priority('high', 1) == 'critical'


def test_calculate_priority_boost_down():
    """Test priority de-escalation."""
    assert calculate_priority('critical', -1) == 'high'
    assert calculate_priority('medium', -1) == 'low'


def test_calculate_priority_clamps():
    """Test priority clamping at boundaries."""
    assert calculate_priority('critical', 5) == 'critical'
    assert calculate_priority('low', -5) == 'low'


# =============================================================================
# Test: is_test_file
# =============================================================================


def test_is_test_file_java():
    """Test Java test file detection."""
    assert is_test_file('src/test/java/com/example/FooTest.java')
    assert is_test_file('FooTest.java')
    assert is_test_file('FooIT.java')
    assert not is_test_file('src/main/java/com/example/Foo.java')


def test_is_test_file_python():
    """Test Python test file detection."""
    assert is_test_file('test_foo.py')
    assert is_test_file('tests/test_bar.py')
    assert not is_test_file('foo.py')


def test_is_test_file_javascript():
    """Test JavaScript/TypeScript test file detection."""
    assert is_test_file('Component.test.js')
    assert is_test_file('Component.spec.tsx')
    assert is_test_file('src/__tests__/Component.js')
    assert not is_test_file('Component.js')


def test_is_test_file_go():
    """Test Go test file detection."""
    assert is_test_file('handler_test.go')
    assert not is_test_file('handler.go')


# =============================================================================
# Test: create_workflow_cli
# =============================================================================


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


# =============================================================================
# Test: ErrorCode constants
# =============================================================================


def test_error_code_fetch_failure_exists():
    """A3: Verify FETCH_FAILURE error code was added."""
    assert hasattr(ErrorCode, 'FETCH_FAILURE')
    assert ErrorCode.FETCH_FAILURE == 'FETCH_FAILURE'
