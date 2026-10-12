#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The scope-creep guard resolves its threshold from the flag, marshal.json, then the default.

The marshal.json key is ``plan.phase-5-execute.scope_creep_threshold``. The
cases write a real marshal.json under the test's temporary directory and point
``manage-config``'s reader at it, so the guard's own read runs for real through
that reader; nothing here stubs the read itself.

Three states of the configuration are kept apart: a usable value, nothing
configured, and a value that is present but unusable. The last falls back to the
default and says so - in particular it never becomes ``0``, which would switch
the guard off.
"""

from __future__ import annotations

import json
from pathlib import Path

import _config_core
import file_ops
import pytest
import scope_creep_check as scc
from _resolve_project_dir_fixtures import worktree_query_result
from toon_parser import parse_toon

from conftest import parse_ns

_PLAN_ID = 'scope-creep-threshold'

#: Six undeclared files: over the default threshold of five, under a raised one.
_RESIDUAL = [f'extra/{index}.py' for index in range(6)]


def _check_args(*extra: str):
    """Parse a ``check`` namespace through the script's own parser."""
    return parse_ns(
        'plan-marshall',
        'phase-5-execute',
        'scope_creep_check.py',
        'check',
        '--plan-id',
        _PLAN_ID,
        *extra,
        register=False,
    )


@pytest.fixture
def marshal_path(tmp_path, monkeypatch) -> Path:
    """Point the marshal.json reader at a path under the temporary directory.

    The file is not created: a case that wants a configuration writes one.
    """
    path: Path = tmp_path / 'marshal.json'
    monkeypatch.setattr(_config_core, 'MARSHAL_PATH', path)
    return path


def _write_threshold(marshal_path: Path, value: object) -> None:
    """Write a marshal.json whose phase-5 section carries ``value`` as the threshold."""
    marshal_path.write_text(json.dumps({'plan': {'phase-5-execute': {'scope_creep_threshold': value}}}))


@pytest.fixture
def persisted(plan_context, monkeypatch, marshal_path) -> list[dict]:
    """A plan whose branch carries ``_RESIDUAL`` undeclared; returns the persist calls."""
    plan_dir = plan_context.plan_dir_for(_PLAN_ID)
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main', 'affected_files': []}))
    monkeypatch.setattr(scc, '_resolve_merge_base', lambda worktree, base_branch: 'mergebase123')
    monkeypatch.setattr(scc, '_git_diff_files', lambda worktree, sha: list(_RESIDUAL))
    monkeypatch.setattr(file_ops, '_query_worktree_path', lambda plan_id: worktree_query_result(True, str(Path.cwd())))
    calls: list[dict] = []

    def _persist(**kwargs):
        calls.append(kwargs)
        return {'status': 'success', 'hash_id': 'abc123'}

    monkeypatch.setattr(scc, 'add_qgate_finding', _persist)
    return calls


def _run(capsys, *extra: str) -> dict:
    """Run the guard and return its parsed output."""
    assert scc.cmd_check(_check_args(*extra)) == 0
    return parse_toon(capsys.readouterr().out)


# ---------------------------------------------------------------------------
# The three sources, in precedence order
# ---------------------------------------------------------------------------


def test_nothing_configured_runs_at_the_default(persisted, marshal_path, capsys):
    """CONTROL: with no marshal.json the six-file residual is over the default and is filed."""
    out = _run(capsys)

    assert out['threshold'] == scc.DEFAULT_THRESHOLD
    assert out['threshold_source'] == 'default'
    assert 'threshold_config_error' not in out
    assert out['finding_emitted'] is True
    assert len(persisted) == 1


def test_a_raised_configured_value_is_honoured(persisted, marshal_path, capsys):
    """The same residual is under a configured threshold of ten, so nothing is filed."""
    _write_threshold(marshal_path, 10)

    out = _run(capsys)

    assert out['threshold'] == 10
    assert out['threshold_source'] == 'config'
    assert out['residual_count'] == len(_RESIDUAL)
    assert out['finding_emitted'] is False
    assert persisted == []


def test_a_configured_zero_disables_the_guard(persisted, marshal_path, capsys):
    """A configured ``0`` reports the guard as switched off and measures nothing."""
    _write_threshold(marshal_path, 0)

    out = _run(capsys)

    assert out['status'] == 'could_not_look'
    assert out['reason'] == 'guard_disabled'
    assert out['threshold'] == 0
    assert out['threshold_source'] == 'config'
    assert 'residual_count' not in out
    assert persisted == []


def test_the_explicit_flag_wins_over_the_configured_value(persisted, marshal_path, capsys):
    """The flag is used although marshal.json configures a threshold that would file nothing."""
    _write_threshold(marshal_path, 10)

    out = _run(capsys, '--threshold', '2')

    assert out['threshold'] == 2
    assert out['threshold_source'] == 'flag'
    assert out['finding_emitted'] is True


def test_the_explicit_flag_never_reads_an_unreadable_configuration(persisted, marshal_path, capsys):
    """A run that states its threshold reports no configuration problem."""
    marshal_path.write_text('{ not json')

    out = _run(capsys, '--threshold', '10')

    assert out['threshold'] == 10
    assert out['threshold_source'] == 'flag'
    assert 'threshold_config_error' not in out


# ---------------------------------------------------------------------------
# The flag obeys the same non-negative rule as marshal.json
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'value',
    [
        pytest.param('-1', id='negative'),
        pytest.param('ten', id='not_an_integer'),
    ],
)
def test_the_flag_rejects_a_value_that_is_not_a_non_negative_integer(persisted, capsys, value):
    """The parser refuses the value with a usage error that names the flag; nothing is measured.

    A negative threshold would make every measured run file a finding, the
    empty residual included, so the flag refuses it exactly as the marshal.json
    reader does.
    """
    with pytest.raises(SystemExit) as excinfo:
        scc.main(['check', '--plan-id', _PLAN_ID, '--threshold', value])

    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert '--threshold' in captured.err
    assert repr(value) in captured.err
    assert captured.out == ''
    assert persisted == []


def test_a_flag_zero_still_disables_the_guard(persisted, capsys):
    """CONTROL: ``--threshold 0`` passes the parser and reaches the guard-disabled could-not-look."""
    assert scc.main(['check', '--plan-id', _PLAN_ID, '--threshold', '0']) == 0
    out = parse_toon(capsys.readouterr().out)

    assert out['status'] == 'could_not_look'
    assert out['reason'] == 'guard_disabled'
    assert out['threshold'] == 0
    assert out['threshold_source'] == 'flag'
    assert 'residual_count' not in out
    assert persisted == []


# ---------------------------------------------------------------------------
# Present but unusable: the default, said out loud
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('content', 'named'),
    [
        pytest.param('{ not json', 'marshal.json could not be read', id='malformed_json'),
        pytest.param('[]', 'marshal.json could not be read', id='top_level_not_an_object'),
        pytest.param(json.dumps({'plan': []}), 'plan in marshal.json is not an object', id='plan_not_an_object'),
        pytest.param(
            json.dumps({'plan': {'phase-5-execute': 7}}),
            'plan.phase-5-execute in marshal.json is not an object',
            id='phase_section_not_an_object',
        ),
        pytest.param(
            json.dumps({'plan': {'phase-5-execute': {'scope_creep_threshold': 'ten'}}}),
            'must be a non-negative integer',
            id='value_is_a_string',
        ),
        pytest.param(
            json.dumps({'plan': {'phase-5-execute': {'scope_creep_threshold': -1}}}),
            'must be a non-negative integer',
            id='value_is_negative',
        ),
        pytest.param(
            json.dumps({'plan': {'phase-5-execute': {'scope_creep_threshold': False}}}),
            'must be a non-negative integer',
            id='value_is_false_not_zero',
        ),
        pytest.param(
            json.dumps({'plan': {'phase-5-execute': {'scope_creep_threshold': None}}}),
            'must be a non-negative integer',
            id='value_is_null',
        ),
    ],
)
def test_an_unusable_configuration_falls_back_to_the_default_and_says_so(
    persisted, marshal_path, capsys, content, named
):
    """The guard still measures, at the default, and names what was wrong.

    ``value_is_false_not_zero`` is the case the fallback exists for: ``False``
    equals ``0`` in Python, and reading it as a threshold would switch the guard
    off on a value nobody wrote as a count.
    """
    marshal_path.write_text(content)

    out = _run(capsys)

    assert out['status'] == 'success'
    assert out['threshold'] == scc.DEFAULT_THRESHOLD
    assert out['threshold_source'] == 'default'
    assert named in out['threshold_config_error']
    assert out['finding_emitted'] is True
    assert len(persisted) == 1


@pytest.mark.parametrize(
    'config',
    [
        pytest.param({}, id='no_plan_section'),
        pytest.param({'plan': {}}, id='no_phase_section'),
        pytest.param({'plan': {'phase-5-execute': {'max_iterations': 5}}}, id='no_threshold_key'),
    ],
)
def test_an_absent_key_is_not_a_configuration_problem(persisted, marshal_path, capsys, config):
    """NEGATIVE CONTROL: a readable marshal.json without the key selects the default silently."""
    marshal_path.write_text(json.dumps(config))

    out = _run(capsys)

    assert out['threshold'] == scc.DEFAULT_THRESHOLD
    assert out['threshold_source'] == 'default'
    assert 'threshold_config_error' not in out


def test_a_reader_that_cannot_be_loaded_falls_back_to_the_default_and_says_so(persisted, monkeypatch, capsys):
    """A marshal.json reader that fails while importing is reported, not absorbed."""
    import builtins

    real_import = builtins.__import__

    def _refuse_config_core(name, *args, **kwargs):
        if name == '_config_core':
            raise RuntimeError('no plan root resolvable')
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', _refuse_config_core)

    out = _run(capsys)

    assert out['threshold'] == scc.DEFAULT_THRESHOLD
    assert out['threshold_source'] == 'default'
    assert 'no plan root resolvable' in out['threshold_config_error']
