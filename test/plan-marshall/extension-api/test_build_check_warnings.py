"""Tests for _build_check_warnings module — CLI layer for warning classification.

Tests the factory function, argparse integration, JSON input parsing,
stdin handling, and exit code semantics.
"""

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# Add script path for imports
_SCRIPT_DIR = Path(__file__).resolve().parents[3] / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'extension-api' / 'scripts'
sys.path.insert(0, str(_SCRIPT_DIR))

# Also add toon_parser path
_TOON_DIR = Path(__file__).resolve().parents[3] / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'ref-toon-format' / 'scripts'
sys.path.insert(0, str(_TOON_DIR))

_bcw = importlib.import_module('_build_check_warnings')

from toon_parser import parse_toon  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _warn(message: str, wtype: str = 'other', severity: str = 'WARNING') -> dict:
    """Build a minimal warning dict."""
    return {'type': wtype, 'message': message, 'severity': severity}


def _args(warnings_json: str | None = None,
          acceptable_json: str | None = None,
          patterns_json: str | None = None) -> SimpleNamespace:
    """Build a minimal argparse-like namespace."""
    return SimpleNamespace(
        warnings=warnings_json,
        acceptable_warnings=acceptable_json,
        patterns=patterns_json,
    )


# ---------------------------------------------------------------------------
# create_check_warnings_handler factory
# ---------------------------------------------------------------------------

class TestFactory:
    """Tests for create_check_warnings_handler()."""

    def test_returns_callable(self):
        handler = _bcw.create_check_warnings_handler()
        assert callable(handler)

    def test_handler_passes_matcher(self, capsys):
        handler = _bcw.create_check_warnings_handler(matcher='wildcard')
        warnings = [_warn('com.example.Foo is deprecated')]
        args = _args(
            warnings_json=json.dumps(warnings),
            acceptable_json=json.dumps({'dep': ['com.example.*']}),
        )
        exit_code = handler(args)
        output = parse_toon(capsys.readouterr().out)
        assert exit_code == 0
        assert output['acceptable'] == 1

    def test_handler_passes_filter_severity(self, capsys):
        handler = _bcw.create_check_warnings_handler(filter_severity='WARNING')
        warnings = [
            _warn('warn msg', severity='WARNING'),
            _warn('error msg', severity='ERROR'),
        ]
        args = _args(
            warnings_json=json.dumps(warnings),
            acceptable_json=json.dumps({'g': ['warn msg', 'error msg']}),
        )
        handler(args)
        output = parse_toon(capsys.readouterr().out)
        # Only the WARNING-severity item should be processed
        assert output['total'] == 2
        assert output['acceptable'] == 1


# ---------------------------------------------------------------------------
# Exit code semantics
# ---------------------------------------------------------------------------

class TestExitCodes:
    """Exit code 0 means no fixable/unknown, 1 otherwise."""

    def test_all_acceptable_returns_0(self, capsys):
        warnings = [_warn('known issue')]
        args = _args(
            warnings_json=json.dumps(warnings),
            acceptable_json=json.dumps({'g': ['known issue']}),
        )
        exit_code = _bcw.cmd_check_warnings_base(args, matcher='substring')
        assert exit_code == 0

    def test_fixable_returns_1(self, capsys):
        warnings = [_warn('javadoc problem', wtype='javadoc_warning')]
        args = _args(warnings_json=json.dumps(warnings))
        exit_code = _bcw.cmd_check_warnings_base(args, matcher='substring')
        assert exit_code == 1

    def test_unknown_returns_1(self, capsys):
        warnings = [_warn('mystery warning', wtype='other')]
        args = _args(
            warnings_json=json.dumps(warnings),
            acceptable_json=json.dumps({'g': ['no match']}),
        )
        exit_code = _bcw.cmd_check_warnings_base(args, matcher='substring')
        assert exit_code == 1

    def test_empty_warnings_returns_0(self, capsys):
        args = _args(warnings_json=json.dumps([]))
        exit_code = _bcw.cmd_check_warnings_base(args)
        assert exit_code == 0


# ---------------------------------------------------------------------------
# JSON input parsing
# ---------------------------------------------------------------------------

class TestJsonInput:
    """Tests for --warnings and --acceptable-warnings JSON parsing."""

    def test_invalid_warnings_json(self, capsys):
        args = _args(warnings_json='not valid json')
        exit_code = _bcw.cmd_check_warnings_base(args)
        assert exit_code == 1
        output = parse_toon(capsys.readouterr().out)
        assert output['status'] == 'error'
        assert 'Invalid JSON' in output['error']

    def test_invalid_acceptable_warnings_json(self, capsys):
        args = _args(
            warnings_json=json.dumps([_warn('msg')]),
            acceptable_json='bad json',
        )
        exit_code = _bcw.cmd_check_warnings_base(args)
        assert exit_code == 1
        output = parse_toon(capsys.readouterr().out)
        assert 'Invalid JSON' in output['error']

    def test_warnings_must_be_array(self, capsys):
        args = _args(warnings_json=json.dumps({'not': 'array'}))
        exit_code = _bcw.cmd_check_warnings_base(args)
        assert exit_code == 1
        output = parse_toon(capsys.readouterr().out)
        assert 'must be an array' in output['error']


# ---------------------------------------------------------------------------
# Stdin input
# ---------------------------------------------------------------------------

class TestStdinInput:
    """Tests for stdin JSON input path."""

    def test_stdin_json_input(self, capsys):
        input_data = json.dumps({
            'warnings': [_warn('known', wtype='other')],
            'acceptable_warnings': {'g': ['known']},
        })
        args = _args()  # no --warnings
        with patch('sys.stdin', __class__=type(sys.stdin)):
            import io
            fake_stdin = io.StringIO(input_data)
            fake_stdin.isatty = lambda: False
            with patch.object(sys, 'stdin', fake_stdin):
                exit_code = _bcw.cmd_check_warnings_base(args, matcher='substring')
        assert exit_code == 0

    def test_tty_stdin_without_warnings_arg_returns_error(self, capsys):
        args = _args()
        with patch.object(sys, 'stdin') as mock_stdin:
            mock_stdin.isatty.return_value = True
            exit_code = _bcw.cmd_check_warnings_base(args)
        assert exit_code == 1
        output = parse_toon(capsys.readouterr().out)
        assert 'No input provided' in output['error']


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:
    """Verify output JSON has required fields."""

    def test_success_output_fields(self, capsys):
        warnings = [
            _warn('acceptable msg'),
            _warn('javadoc issue', wtype='javadoc_warning'),
        ]
        args = _args(
            warnings_json=json.dumps(warnings),
            acceptable_json=json.dumps({'g': ['acceptable msg']}),
        )
        _bcw.cmd_check_warnings_base(args, matcher='substring')
        output = parse_toon(capsys.readouterr().out)
        assert output['status'] == 'success'
        assert 'total' in output
        assert 'acceptable' in output
        assert 'fixable' in output
        assert 'unknown' in output
        assert 'categorized' in output
        assert isinstance(output['categorized'], dict)
        assert set(output['categorized'].keys()) == {'acceptable', 'fixable', 'unknown'}


# ---------------------------------------------------------------------------
# supports_patterns_arg mode
# ---------------------------------------------------------------------------

class TestPatternsArg:
    """Tests for supports_patterns_arg=True (flat list input)."""

    def test_patterns_arg_flat_list(self, capsys):
        warnings = [_warn('issue A'), _warn('issue B')]
        args = _args(
            warnings_json=json.dumps(warnings),
            patterns_json=json.dumps(['issue A', 'issue B']),
        )
        exit_code = _bcw.cmd_check_warnings_base(args, matcher='substring', supports_patterns_arg=True)
        assert exit_code == 0
        output = parse_toon(capsys.readouterr().out)
        assert output['acceptable'] == 2

    def test_invalid_patterns_json(self, capsys):
        args = _args(
            warnings_json=json.dumps([_warn('msg')]),
            patterns_json='invalid',
        )
        exit_code = _bcw.cmd_check_warnings_base(args, matcher='substring', supports_patterns_arg=True)
        assert exit_code == 1
        output = parse_toon(capsys.readouterr().out)
        assert 'Invalid JSON' in output['error']

    def test_acceptable_warnings_flattened_when_patterns_arg(self, capsys):
        warnings = [_warn('known')]
        args = _args(
            warnings_json=json.dumps(warnings),
            acceptable_json=json.dumps({'group': ['known']}),
        )
        exit_code = _bcw.cmd_check_warnings_base(args, matcher='substring', supports_patterns_arg=True)
        assert exit_code == 0
