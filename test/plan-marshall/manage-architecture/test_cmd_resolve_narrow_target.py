#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``resolve --narrow-unit`` - a narrow unit made resolvable and bounded.

A narrow unit is a ``module-tests`` target narrower than its module: one test
directory, or one test file. Its run-config key is its own, so before it has run
it is unmeasured, and the ordinary tier derivation would fail it closed to the
orchestrator tier. ``resolve --narrow-unit`` instead bounds it from what is
known and names the source of the bound in a fifth field, ``bound_source``:

* ``module_bound`` - the module's own ``module-tests`` command is measured and
  its stamp is within the Bash ceiling, so the unit takes the module's stamp.
* ``narrow_default`` - the module's stamp is unusable (unmeasured, or beyond the
  ceiling), so the unit takes the stated default: the tool's own outer floor.
* ``measured`` - the unit's own key is measured; today's derivation, unchanged.

Run-config state is injected through an isolated ``run-configuration.json``, the
same seam ``test_cmd_resolve.py`` uses, so every case states exactly which keys
are measured. The stated default is never written here as a number: it is read
from the build skill's ``_CONFIG`` and passed through ``get_bash_timeout``, the
way production derives it.

Two further cases cover the parts that are not bound arithmetic: the argument is
declared on BOTH ``resolve`` parsers that reach the one handler, and a narrow
run that exceeds its bound is learned from, so the next resolve of the same key
reports ``measured``.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from _arch_fixtures import seed_project as _seed_project
from toon_parser import parse_toon

from conftest import get_scripts_dir, load_script_module, parse_ns

_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')
_pyproject_execute = load_script_module(
    'plan-marshall', 'build-pyproject', '_pyproject_execute.py', '_pyproject_execute'
)

cmd_resolve = _cmd_client.cmd_resolve

_MODULE = 'plan-marshall'
_NARROW_UNIT = 'plan-marshall/build-server'
_PARENT_ARGS = f'module-tests {_MODULE}'
_NARROW_ARGS = f'module-tests {_NARROW_UNIT}'

_EXECUTABLE_PREFIX = 'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args '
_PARENT_EXECUTABLE = f'{_EXECUTABLE_PREFIX}"{_PARENT_ARGS}"'
_NARROW_EXECUTABLE = f'{_EXECUTABLE_PREFIX}"{_NARROW_ARGS}"'

#: The plan the in-process build of the timeout case is attributed to.
_PLAN_ID = 'narrow-unit-resolve-test-plan'


def _build_modules() -> tuple[Any, Any]:
    """Return the ``_cmd_client_build`` and ``_build_execute_factory`` modules production uses."""
    return sys.modules['_cmd_client_build'], sys.modules['_build_execute_factory']


def _command_key(command_args: str) -> str:
    """Compute the run-config key for ``command_args`` the way a real run does."""
    _, factory = _build_modules()
    key: str = factory.compute_command_key(_pyproject_execute._CONFIG, command_args)
    return key


def _stamp(inner_timeout_seconds: int) -> int:
    """Turn an inner timeout into the stamp ``resolve`` reports, as production does."""
    from _build_shared import get_bash_timeout

    return get_bash_timeout(inner_timeout_seconds)


def _stated_default_stamp() -> int:
    """The stated default for an unmeasured narrow unit, read from the tool config."""
    return _stamp(_pyproject_execute._CONFIG.min_timeout)


def _per_task_hint(bash_timeout_seconds: int) -> str:
    """Render the per_task recognition token the way production renders it."""
    hint: str = _cmd_client._HINT_PER_TASK_TEMPLATE.format(ms=bash_timeout_seconds * 1000)
    return hint


def _resolve_args(project_dir: str, *extra: str):
    """Parse a ``resolve`` namespace through ``architecture.py``'s own parser."""
    return parse_ns(
        'plan-marshall',
        'manage-architecture',
        'architecture.py',
        '--project-dir',
        project_dir,
        'resolve',
        '--command',
        'module-tests',
        '--module',
        _MODULE,
        *extra,
        register=False,
    )


def _seed_module(project_dir: str, command: str = 'module-tests', executable: str = _PARENT_EXECUTABLE) -> None:
    """Seed one ``plan-marshall`` module exposing ``command``."""
    _seed_project(
        project_dir,
        {
            _MODULE: {
                'name': _MODULE,
                'build_systems': ['pyproject'],
                'paths': {'module': '.'},
                'commands': {command: executable},
            }
        },
    )


def _set_persisted_timeouts(plan_dir: Path, durations: dict[str, int]) -> None:
    """Write the measured keys to the isolated ``run-configuration.json``."""
    config = {
        'version': 1,
        'commands': {key: {'timeout_seconds': seconds} for key, seconds in durations.items()},
    }
    (plan_dir / 'run-configuration.json').write_text(json.dumps(config, indent=2))


@pytest.fixture
def isolated_run_config(monkeypatch, tmp_path):
    """Redirect ``run-configuration.json`` to an isolated directory."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    import _config_core

    monkeypatch.setattr(_config_core, 'PLAN_BASE_DIR', plan_dir)
    monkeypatch.setattr(_config_core, 'RUN_CONFIG_PATH', plan_dir / 'run-configuration.json')

    return plan_dir


def _resolve_narrow(narrow_unit: str = _NARROW_UNIT) -> dict[str, Any]:
    """Seed the module in a fresh project and resolve ``narrow_unit`` of it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module(tmpdir)
        result: dict[str, Any] = cmd_resolve(_resolve_args(tmpdir, '--narrow-unit', narrow_unit))
        return result


# =============================================================================
# The three bound sources
# =============================================================================


def test_unmeasured_unit_of_a_measured_module_takes_the_module_stamp(isolated_run_config):
    """Module measured and within the ceiling -> ``per_task``, the module's stamp, ``module_bound``."""
    _set_persisted_timeouts(isolated_run_config, {_command_key(_PARENT_ARGS): 360})
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module(tmpdir)
        module_result = cmd_resolve(_resolve_args(tmpdir))
        narrow_result = cmd_resolve(_resolve_args(tmpdir, '--narrow-unit', _NARROW_UNIT))

    # The witness: the module's stamp differs from the stated default, so the
    # assertion below cannot be satisfied by the default arriving by another road.
    module_stamp = module_result['bash_timeout_seconds']
    assert module_result['execution_tier'] == 'per_task'
    assert module_stamp != _stated_default_stamp()

    assert narrow_result['status'] == 'success'
    assert narrow_result['executable'] == _NARROW_EXECUTABLE
    assert narrow_result['bound_source'] == 'module_bound'
    assert narrow_result['bash_timeout_seconds'] == module_stamp
    assert narrow_result['exceeds_bash_ceiling'] is False
    assert narrow_result['execution_tier'] == 'per_task'
    assert narrow_result['hint'] == _per_task_hint(module_stamp)


def test_unmeasured_unit_of_a_module_beyond_the_ceiling_takes_the_stated_default(isolated_run_config):
    """Module measured but beyond the ceiling -> ``per_task``, the stated default, ``narrow_default``."""
    _set_persisted_timeouts(isolated_run_config, {_command_key(_PARENT_ARGS): 800})
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module(tmpdir)
        module_result = cmd_resolve(_resolve_args(tmpdir))
        narrow_result = cmd_resolve(_resolve_args(tmpdir, '--narrow-unit', _NARROW_UNIT))

    assert module_result['exceeds_bash_ceiling'] is True
    assert module_result['execution_tier'] == 'orchestrator'

    default_stamp = _stated_default_stamp()
    assert narrow_result['status'] == 'success'
    assert narrow_result['bound_source'] == 'narrow_default'
    assert narrow_result['bash_timeout_seconds'] == default_stamp
    assert narrow_result['exceeds_bash_ceiling'] is False
    assert narrow_result['execution_tier'] == 'per_task'
    assert narrow_result['hint'] == _per_task_hint(default_stamp)


def test_unmeasured_unit_of_an_unmeasured_module_takes_the_stated_default(isolated_run_config):
    """Nothing measured -> ``per_task``, the stated default, ``narrow_default``.

    The matched control is the module itself: with the same empty run-config it
    still fails closed to ``orchestrator``, so the narrow branch did not loosen
    the module-level rule.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module(tmpdir)
        module_result = cmd_resolve(_resolve_args(tmpdir))
        narrow_result = cmd_resolve(_resolve_args(tmpdir, '--narrow-unit', _NARROW_UNIT))

    assert module_result['execution_tier'] == 'orchestrator'
    assert module_result['hint'] == _cmd_client._HINT_UNMEASURED
    assert 'bound_source' not in module_result

    default_stamp = _stated_default_stamp()
    assert narrow_result['bound_source'] == 'narrow_default'
    assert narrow_result['bash_timeout_seconds'] == default_stamp
    assert narrow_result['execution_tier'] == 'per_task'


def test_a_measured_unit_keeps_its_own_measurement(isolated_run_config):
    """A measured narrow key is derived as before, whatever the module says.

    The module is measured at a different, larger value, so reading the
    module's stamp for the unit would show.
    """
    _set_persisted_timeouts(
        isolated_run_config,
        {_command_key(_NARROW_ARGS): 200, _command_key(_PARENT_ARGS): 360},
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module(tmpdir)
        module_result = cmd_resolve(_resolve_args(tmpdir))
        narrow_result = cmd_resolve(_resolve_args(tmpdir, '--narrow-unit', _NARROW_UNIT))
        handlers = sys.modules['_cmd_client_handlers']
        ordinary = handlers._augment_resolved({'executable': _NARROW_EXECUTABLE}, tmpdir)

    assert narrow_result['bound_source'] == 'measured'
    assert narrow_result['bash_timeout_seconds'] != module_result['bash_timeout_seconds']
    for field in ('bash_timeout_seconds', 'exceeds_bash_ceiling', 'execution_tier', 'hint'):
        assert narrow_result[field] == ordinary[field], f'{field} differs from the ordinary derivation'


def test_a_test_file_is_a_resolvable_narrow_unit(isolated_run_config):
    """A changed test file is a narrow unit too, not only a directory."""
    unit = f'{_NARROW_UNIT}/test_server.py'

    result = _resolve_narrow(unit)

    assert result['status'] == 'success'
    assert result['executable'] == f'{_EXECUTABLE_PREFIX}"module-tests {unit}"'
    assert result['bound_source'] == 'narrow_default'


# =============================================================================
# Refusals
# =============================================================================


@pytest.mark.parametrize(
    'narrow_unit',
    [
        pytest.param('pm-dev-python/pytest-testing', id='another_module'),
        pytest.param('plan-marshall-extra/build-server', id='name_that_only_starts_like_the_module'),
    ],
)
def test_a_narrow_unit_outside_the_named_module_is_refused(isolated_run_config, narrow_unit):
    """A unit that is not a part of the named module is a structured error."""
    result = _resolve_narrow(narrow_unit)

    assert result['status'] == 'error'
    assert result['error'] == 'narrow_unit_outside_module'
    assert result['narrow_unit'] == narrow_unit
    assert result['module'] == _MODULE
    assert result['test_target'] == _MODULE
    assert 'executable' not in result


@pytest.mark.parametrize(
    'narrow_unit',
    [
        pytest.param('plan-marshall', id='the_module_itself'),
        pytest.param('plan-marshall/../pm-dev-python', id='parent_segment'),
        pytest.param('plan-marshall/./build-server', id='interior_current_segment'),
        pytest.param('plan-marshall/build-server/.', id='trailing_current_segment'),
        pytest.param('plan-marshall/build server', id='whitespace'),
        pytest.param('plan-marshall/x;rm', id='shell_syntax'),
        pytest.param('plan-marshall/', id='trailing_separator'),
    ],
)
def test_a_malformed_narrow_unit_is_refused(isolated_run_config, narrow_unit):
    """A unit that is not a plain path below a test target never reaches a command."""
    result = _resolve_narrow(narrow_unit)

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_narrow_unit'
    assert 'executable' not in result


@pytest.mark.parametrize(
    'narrow_unit',
    [
        pytest.param('plan-marshall/a.b', id='directory_name_with_a_dot'),
        pytest.param('plan-marshall/build-server/test_x.py', id='file_name_with_a_dot'),
        pytest.param('plan-marshall/.hidden', id='segment_starting_with_a_dot'),
    ],
)
def test_a_segment_that_only_contains_a_dot_is_accepted(isolated_run_config, narrow_unit):
    """Only a segment that IS ``.`` or ``..`` is refused; a dotted name is a real name.

    The matched control for the ``.``-segment refusals above: the same character
    inside a longer segment still resolves, so the rejection is keyed on the
    segment, not on the dot.
    """
    result = _resolve_narrow(narrow_unit)

    assert result['status'] == 'success'
    assert result['executable'] == f'{_EXECUTABLE_PREFIX}"module-tests {narrow_unit}"'


def test_a_narrow_unit_is_refused_for_any_command_but_module_tests(isolated_run_config):
    """The argument is accepted for ``module-tests`` only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module(tmpdir, command='compile', executable=f'{_EXECUTABLE_PREFIX}"compile {_MODULE}"')
        args = parse_ns(
            'plan-marshall',
            'manage-architecture',
            'architecture.py',
            '--project-dir',
            tmpdir,
            'resolve',
            '--command',
            'compile',
            '--module',
            _MODULE,
            '--narrow-unit',
            _NARROW_UNIT,
            register=False,
        )
        result = cmd_resolve(args)

    assert result['status'] == 'error'
    assert result['error'] == 'narrow_unit_unsupported_command'
    assert result['command'] == 'compile'


# =============================================================================
# The argument is declared on both resolve parsers
# =============================================================================


def test_architecture_parser_declares_the_narrow_unit_argument():
    """``architecture.py`` parses ``--narrow-unit`` into ``narrow_unit``."""
    args = _resolve_args('.', '--narrow-unit', _NARROW_UNIT)

    assert args.narrow_unit == _NARROW_UNIT
    # Absent means None, which the handler reads as "no narrow unit".
    assert _resolve_args('.').narrow_unit is None


def test_query_architecture_parser_declares_the_narrow_unit_argument(isolated_run_config, monkeypatch, capsys):
    """``query-architecture.py`` builds its own parser and must declare it too.

    Driven end to end through that script's ``main`` so the namespace its own
    parser builds is the one the shared ``cmd_resolve`` handler receives. Without
    the declaration argparse rejects the flag before the handler runs.
    """
    script = get_scripts_dir('plan-marshall', 'script-shared') / 'query' / 'query-architecture.py'
    spec = importlib.util.spec_from_file_location('query_architecture_for_narrow_unit', script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module(tmpdir)
        monkeypatch.setattr(
            sys,
            'argv',
            [
                str(script),
                '--project-dir',
                tmpdir,
                'resolve',
                '--command',
                'module-tests',
                '--module',
                _MODULE,
                '--narrow-unit',
                _NARROW_UNIT,
            ],
        )
        try:
            module.main()
        except SystemExit as exit_signal:
            assert exit_signal.code in (0, None)

    out = parse_toon(capsys.readouterr().out)
    assert out['status'] == 'success'
    assert out['executable'] == _NARROW_EXECUTABLE
    assert out['bound_source'] == 'narrow_default'


# =============================================================================
# A narrow run that exceeds its bound is learned from
# =============================================================================


def test_a_narrow_run_that_times_out_is_measured_on_the_next_resolve(isolated_run_config, tmp_path):
    """Timeout -> the result names bound, source and key -> the next resolve is ``measured``.

    The build execute base is not changed by this plan; this pins, for a
    narrow-unit key, the behaviour ``resolve`` relies on: a run that outlives its
    bound returns ``timeout`` carrying the bound it ran under, where that bound
    came from and the key it was recorded against, and records a learned value
    for that key. The following resolve therefore leaves the unmeasured branch.
    """
    project_dir = tmp_path / 'project'
    project_dir.mkdir()
    wrapper = project_dir / 'pw'
    wrapper.write_text('#!/bin/bash\nsleep 1000\n')
    wrapper.chmod(0o755)
    command_key = _command_key(_NARROW_ARGS)
    config = _pyproject_execute._CONFIG

    with (
        patch(
            '_build_execute._run_bounded',
            side_effect=subprocess.TimeoutExpired(cmd=f'./pw {_NARROW_ARGS}', timeout=config.min_timeout),
        ),
        patch('_build_execute.create_log_file', return_value=str(tmp_path / 'narrow.log')),
    ):
        run_result = _pyproject_execute.execute_direct(
            args=_NARROW_ARGS,
            command_key=command_key,
            default_timeout=config.default_timeout,
            project_dir=str(project_dir),
            plan_id=_PLAN_ID,
        )

    assert run_result['status'] == 'timeout'
    assert run_result['command_key'] == command_key
    # Unmeasured, so the run executed under the engine floor - the same number
    # the stated default is built from.
    assert run_result['timeout_used_seconds'] == config.min_timeout
    assert run_result['timeout_source'] in {'explicit', 'learned', 'default', 'floor'}

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module(tmpdir)
        narrow_result = cmd_resolve(_resolve_args(tmpdir, '--narrow-unit', _NARROW_UNIT))
        handlers = sys.modules['_cmd_client_handlers']
        ordinary = handlers._augment_resolved({'executable': _NARROW_EXECUTABLE}, tmpdir)

    assert narrow_result['bound_source'] == 'measured'
    for field in ('bash_timeout_seconds', 'exceeds_bash_ceiling', 'execution_tier', 'hint'):
        assert narrow_result[field] == ordinary[field], f'{field} differs from the ordinary derivation'
    # The learned value is larger than the bound that just expired.
    assert narrow_result['bash_timeout_seconds'] > _stated_default_stamp()
