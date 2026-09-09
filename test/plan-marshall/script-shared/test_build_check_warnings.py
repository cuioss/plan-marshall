# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _build_check_warnings module — CLI layer for warning classification.

Tests the factory function, argparse integration, JSON input parsing,
and exit code semantics.
"""

import json
from types import SimpleNamespace

# Both modules live in marketplace ``scripts/`` directories the root conftest
# already puts on ``sys.path``, so they import plainly with no bootstrap.
import _build_check_warnings as _bcw
import pytest
from toon_parser import parse_toon


def _warn(message: str, wtype: str = 'other', severity: str = 'WARNING') -> dict:
    """Build a minimal warning dict."""
    return {'type': wtype, 'message': message, 'severity': severity}


def _args(warnings_json: str | None = None, acceptable_json: str | None = None) -> SimpleNamespace:
    """Build a minimal argparse-like namespace."""
    return SimpleNamespace(
        warnings=warnings_json,
        acceptable_warnings=acceptable_json,
    )


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
        assert output['total'] == 2
        assert output['acceptable'] == 1


#: ``(warnings, acceptable patterns, expected exit code)``. ``substring`` is the
#: function's own default matcher, so passing it explicitly on every row leaves
#: each case exercising the classification it did before.
_EXIT_CODE_CASES = [
    ([_warn('known issue')], {'g': ['known issue']}, 0),
    ([_warn('javadoc problem', wtype='javadoc_warning')], None, 1),
    ([_warn('mystery warning', wtype='other')], {'g': ['no match']}, 1),
    ([], None, 0),
]

_EXIT_CODE_IDS = [
    'every-warning-acceptable',
    'a-fixable-warning',
    'an-unknown-warning',
    'no-warnings-at-all',
]


class TestExitCodes:
    """Exit code 0 means no fixable/unknown, 1 otherwise."""

    @pytest.mark.parametrize(
        'warnings,acceptable,expected_exit_code', _EXIT_CODE_CASES, ids=_EXIT_CODE_IDS
    )
    def test_the_exit_code_reports_whether_anything_is_actionable(
        self, warnings: list[dict], acceptable: dict | None, expected_exit_code: int
    ):
        args = _args(
            warnings_json=json.dumps(warnings),
            acceptable_json=None if acceptable is None else json.dumps(acceptable),
        )

        assert _bcw.cmd_check_warnings_base(args, matcher='substring') == expected_exit_code


#: ``(--warnings value, --acceptable-warnings value, error fragment)``. Every row
#: is a refusal, so the exit code and the ``status: error`` envelope are the same
#: in each and only the fragment naming the fault varies.
_REFUSED_INPUT_CASES = [
    (None, None, 'No input provided'),
    ('not valid json', None, 'Invalid JSON'),
    (json.dumps([_warn('msg')]), 'bad json', 'Invalid JSON'),
    (json.dumps({'not': 'array'}), None, 'must be an array'),
]

_REFUSED_INPUT_IDS = [
    'no-warnings-argument-at-all',
    'warnings-is-not-json',
    'acceptable-warnings-is-not-json',
    'warnings-json-is-not-an-array',
]


class TestRefusedInput:
    """A missing or malformed input is refused with exit 1 and a named reason."""

    @pytest.mark.parametrize(
        'warnings_json,acceptable_json,error_fragment',
        _REFUSED_INPUT_CASES,
        ids=_REFUSED_INPUT_IDS,
    )
    def test_a_refused_input_names_what_was_wrong(
        self,
        capsys,
        warnings_json: str | None,
        acceptable_json: str | None,
        error_fragment: str,
    ):
        args = _args(warnings_json=warnings_json, acceptable_json=acceptable_json)

        exit_code = _bcw.cmd_check_warnings_base(args)

        output = parse_toon(capsys.readouterr().out)
        assert exit_code == 1
        assert output['status'] == 'error'
        assert error_fragment in output['error']


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
