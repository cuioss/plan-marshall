#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for truthful evidence on a timeout-killed build.

Two defects are locked here, both of which made a killed build lie about what
it had actually proven:

1. **Bound ordering.** The outer wrapper timeout could expire before pytest's
   own inner per-test backstop, so a hang surfaced as an opaque process kill
   instead of the inner backstop's attributable traceback. The pyproject build
   now floors its outer timeout at ``PYTEST_OUTER_FLOOR_SECONDS``, which MUST
   stay strictly greater than ``[tool.pytest.ini_options] timeout``.

2. **Discarded evidence.** The timeout branch of ``cmd_run_common`` emitted a
   bare timeout result without ever parsing the log, so a suite that ran fully
   green and then hung in teardown was indistinguishable from one that never
   finished. The branch now parses and attaches the zero-failure ``tests``
   summary plus ``tool_duration_seconds``.

The bound assertions read the inner backstop out of ``pyproject.toml`` at test
time (authoritative, never edited here) and never encode a learned adaptive
timeout figure — those are rewritten by the run-config weighted average after
every run, so a literal would be stale by construction. Where a floor
comparison needs a learned value, ``timeout_get`` is stubbed with an arbitrary
fixture figure; the shared ``.plan/run-configuration.json`` is never read or
mutated.
"""

import subprocess
import tempfile
import tomllib
import types
from pathlib import Path

import _build_execute
import _build_shared
import pytest
from _build_execute_factory import _daemon_result_to_direct
from _build_result import DirectCommandResult, TruthfulStatusError, assert_truthful_status, timeout_result

from conftest import load_script_module

_pyproject_execute = load_script_module(
    'plan-marshall', 'build-pyproject', '_pyproject_execute.py', '_pyproject_execute'
)
_pyproject_cmd_parse = load_script_module(
    'plan-marshall', 'build-pyproject', '_pyproject_cmd_parse.py', '_pyproject_cmd_parse'
)
parse_log = _pyproject_cmd_parse.parse_log

# A green pytest tail: the suite completed with zero failures, and the tool's
# own duration is well under the wall clock of the run that was later killed.
_GREEN_PYTEST_TAIL = '==================== 118 passed, 2 skipped in 87.5s ====================\n'
_TOOL_DURATION = 87.5
_WALL_CLOCK_SECONDS = 600


def _repo_root() -> Path:
    """Walk up from this file to the checkout root that owns pyproject.toml."""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / 'pyproject.toml').is_file():
            return candidate
    raise AssertionError('pyproject.toml not found above the test file')


def _inner_backstop_seconds() -> int:
    """Read the authoritative pytest inner backstop from pyproject.toml."""
    with (_repo_root() / 'pyproject.toml').open('rb') as handle:
        config = tomllib.load(handle)
    timeout = config['tool']['pytest']['ini_options']['timeout']
    assert isinstance(timeout, int)
    return timeout


def _parse_pytest_text(text: str):
    """Parse pytest output supplied as text by staging it through a temp log."""
    with tempfile.NamedTemporaryFile('w', suffix='.log', delete=False) as handle:
        handle.write(text)
        path = handle.name
    try:
        return parse_log(path)
    finally:
        Path(path).unlink()


def _green_log(tmp_path: Path) -> str:
    log = tmp_path / 'python-timeout.log'
    log.write_text('collected 120 items\n\n' + _GREEN_PYTEST_TAIL)
    return str(log)


def _timeout_input(log_file: str) -> DirectCommandResult:
    """An in-process DirectCommandResult for a run killed at the wall clock."""
    result: DirectCommandResult = {
        'status': 'timeout',
        'exit_code': -1,
        'duration_seconds': _WALL_CLOCK_SECONDS,
        'timeout_used_seconds': _WALL_CLOCK_SECONDS,
        'log_file': log_file,
        'command': './pw module-tests',
    }
    return result


def _toon_scalars(emitted: str) -> dict[str, str]:
    """Collect the top-level `key: value` scalar lines of a TOON emission."""
    scalars: dict[str, str] = {}
    for line in emitted.splitlines():
        if not line or line[0].isspace() or ': ' not in line:
            continue
        key, value = line.split(': ', 1)
        scalars[key] = value
    return scalars


def _tests_block(emitted: str) -> dict[str, str]:
    """Collect the indented `tests:` sub-block of a TOON emission."""
    block: dict[str, str] = {}
    inside = False
    for line in emitted.splitlines():
        if line.rstrip() == 'tests:':
            inside = True
            continue
        if inside:
            if not line[:1].isspace():
                break
            key, value = line.strip().split(': ', 1)
            block[key] = value
    return block


# =============================================================================
# 1. Bound-ordering drift guard
# =============================================================================


def test_outer_floor_strictly_exceeds_inner_pytest_backstop():
    """The outer wrapper floor must outlast pytest's own per-test backstop.

    If the outer bound can fire first it kills the process before the inner
    backstop can name the hanging test, turning a diagnosable failure into an
    opaque one — the exact regression this guard exists to catch.
    """
    assert _pyproject_execute.PYTEST_OUTER_FLOOR_SECONDS > _inner_backstop_seconds()


def test_pyproject_config_wires_the_outer_floor():
    """The floor is actually wired into the pyproject ExecuteConfig, not just declared."""
    assert _pyproject_execute._CONFIG.min_timeout == _pyproject_execute.PYTEST_OUTER_FLOOR_SECONDS


def test_learned_value_below_the_backstop_is_raised_to_the_floor(monkeypatch, tmp_path):
    """A learned timeout under the inner backstop still yields a deadline at/above the floor.

    The learned value is stubbed with an arbitrary fixture figure below the
    backstop — the shared run-configuration is never consulted, and no learned
    figure is encoded here.
    """
    floor = _pyproject_execute.PYTEST_OUTER_FLOOR_SECONDS
    stub_learned = _inner_backstop_seconds() - 1
    observed: dict[str, int] = {}

    def _fake_run(cmd_parts, **kwargs):
        observed['timeout'] = kwargs['timeout']
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(_build_execute, 'create_log_file', lambda *a, **k: str(tmp_path / 'run.log'))
    monkeypatch.setattr(_build_execute, 'timeout_get', lambda *a, **k: stub_learned)
    monkeypatch.setattr(_build_execute, 'timeout_set', lambda *a, **k: None)
    monkeypatch.setattr(
        _build_execute,
        'subprocess',
        types.SimpleNamespace(
            run=_fake_run,
            TimeoutExpired=subprocess.TimeoutExpired,
            STDOUT=subprocess.STDOUT,
        ),
    )

    result = _build_execute.execute_direct_base(
        args='module-tests',
        command_key='python:module_tests',
        default_timeout=stub_learned,
        project_dir=str(tmp_path),
        tool_name='python',
        build_command_fn=lambda wrapper, args, log_file: ([wrapper, args], f'{wrapper} {args}'),
        wrapper='./pw',
        min_timeout=floor,
    )

    assert observed['timeout'] >= floor
    assert result['timeout_used_seconds'] >= floor


# =============================================================================
# 2. In-process timeout carries the evidence its log proves
# =============================================================================


def test_in_process_timeout_attaches_green_evidence(capsys, tmp_path):
    """A killed-after-green in-process run reports its zero-failure suite."""
    exit_code = _build_shared.cmd_run_common(
        _timeout_input(_green_log(tmp_path)), parse_log, 'python'
    )
    emitted = capsys.readouterr().out

    assert exit_code == 0
    scalars = _toon_scalars(emitted)
    assert scalars['status'] == 'timeout'
    assert scalars['tool_duration_seconds'] == str(_TOOL_DURATION)
    # Wall clock and tool duration are DISTINCT: the wall clock is the timeout
    # the run was killed at, the tool duration is how long the suite took.
    assert scalars['duration_seconds'] == str(_WALL_CLOCK_SECONDS)
    assert scalars['duration_seconds'] != scalars['tool_duration_seconds']

    tests = _tests_block(emitted)
    assert tests['failed'] == '0'
    assert int(tests['passed']) > 0
    assert tests['duration_seconds'] == str(_TOOL_DURATION)


# =============================================================================
# 3. The routed path shares the single choke point
# =============================================================================


def test_daemon_routed_timeout_attaches_identical_evidence(capsys, tmp_path):
    """A daemon-routed timeout attaches the same evidence as the in-process one.

    Routed and in-process builds are claimed to share ONE rendering choke point
    (``cmd_run_common``); this drives the routed shape through
    ``_daemon_result_to_direct`` and asserts the claim rather than assuming it.
    """
    log_file = _green_log(tmp_path)
    waited = {
        'job_status': 'timeout',
        'duration_seconds': _WALL_CLOCK_SECONDS,
        'log_file': log_file,
        'exit_code': -1,
    }

    routed = _daemon_result_to_direct(waited, './pw module-tests')
    assert routed['status'] == 'timeout'

    exit_code = _build_shared.cmd_run_common(routed, parse_log, 'python')
    emitted = capsys.readouterr().out

    assert exit_code == 0
    scalars = _toon_scalars(emitted)
    assert scalars['status'] == 'timeout'
    assert scalars['tool_duration_seconds'] == str(_TOOL_DURATION)

    tests = _tests_block(emitted)
    assert tests['failed'] == '0'
    assert int(tests['passed']) > 0


# =============================================================================
# 4. The green-lying guard is unaffected
# =============================================================================


def test_truthful_status_guard_still_rejects_success_over_nonzero_exit():
    """Recovering timeout evidence must not loosen the success-over-error guard."""
    with pytest.raises(TruthfulStatusError):
        assert_truthful_status({'status': 'success', 'exit_code': 1, 'command': './pw verify'})


def test_timeout_result_carrying_evidence_does_not_trip_the_guard():
    """A timeout result holding recovered evidence is not an untruthful success."""
    _, summary, _ = _parse_pytest_text(_GREEN_PYTEST_TAIL)
    recovered = timeout_result(
        timeout_used_seconds=_WALL_CLOCK_SECONDS,
        duration_seconds=_WALL_CLOCK_SECONDS,
        log_file='/tmp/does-not-matter.log',
        command='./pw module-tests',
        tests=summary,
        tool_duration_seconds=_TOOL_DURATION,
    )

    assert_truthful_status(recovered)  # must not raise
    assert recovered['status'] == 'timeout'
