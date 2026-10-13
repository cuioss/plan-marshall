#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Write-outcome contract of the manage-logging write verbs.

The ``work`` and ``decision`` verbs report a write that did not land — a
``status: error`` / ``error: write_failed`` payload and exit 1 — and stay silent
with exit 0 when the entry is written. The ``script`` verb and the in-process
``log_entry`` stay best-effort: a failed write is swallowed. Logging disabled is
not a failure, and the orchestrator store's typed refusal is not converted into
``write_failed``.

A failed write is produced by placing a directory where the log file belongs, so
the append fails for every user, root included.
"""

from __future__ import annotations

import json
from pathlib import Path

import plan_logging
import pytest
from file_ops import OrchestratorStoreUnavailable

from conftest import get_script_path, load_script_module, parse_ns, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-logging', 'manage-logging.py')

_mod = load_script_module('plan-marshall', 'manage-logging', 'manage-logging.py', 'manage_logging')
handle_write = _mod.handle_write

#: The verbs that report a failed write, read from the script's own declaration.
CHECKED_VERBS: tuple[str, ...] = tuple(_mod.CHECKED_WRITE_TYPES)
_LOG_FILE = {'work': 'work.log', 'decision': 'decision.log', 'script': 'script-execution.log'}
_PLAN_ID = 'log-write-outcome'


def _init_plan(plan_context) -> Path:
    """An initialized plan dir (status.json sentinel), so the log path is plan-scoped."""
    plan_dir: Path = plan_context.plan_dir_for(_PLAN_ID)
    (plan_dir / 'status.json').write_text(json.dumps({'plan_id': _PLAN_ID}), encoding='utf-8')
    return plan_dir


def _block_log_file(plan_dir: Path, verb: str) -> Path:
    """Put a directory where the verb's log file belongs, so appending to it fails."""
    blocked = plan_dir / 'logs' / _LOG_FILE[verb]
    blocked.mkdir(parents=True)
    return blocked


def _write_args(verb: str, message: str = 'entry'):
    return parse_ns(
        'plan-marshall',
        'manage-logging',
        'manage-logging.py',
        verb,
        '--plan-id',
        _PLAN_ID,
        '--level',
        'INFO',
        '--message',
        message,
    )


def _run_cli(plan_context, verb: str):
    return run_script(
        SCRIPT_PATH,
        verb,
        '--plan-id',
        _PLAN_ID,
        '--level',
        'INFO',
        '--message',
        f'{verb} entry through the CLI',
        env_overrides={'PLAN_BASE_DIR': str(plan_context.fixture_dir)},
    )


def test_checked_verbs_are_a_non_empty_set_of_write_verbs():
    """Control: the derived parametrization is not vacuous, and the best-effort script verb is outside it."""
    assert CHECKED_VERBS, 'an empty CHECKED_WRITE_TYPES would skip every parametrized test below'
    assert set(CHECKED_VERBS) <= set(_LOG_FILE)
    assert 'script' not in CHECKED_VERBS


@pytest.mark.parametrize('verb', CHECKED_VERBS)
def test_failed_write_returns_write_failed(plan_context, verb):
    _block_log_file(_init_plan(plan_context), verb)

    result = handle_write(_write_args(verb))

    assert result is not None, 'a write that did not land must not report success'
    assert result['status'] == 'error'
    assert result['error'] == 'write_failed'
    assert result['log_type'] == verb
    assert result['plan_id'] == _PLAN_ID
    assert 'was not written' in result['message']


@pytest.mark.parametrize('verb', CHECKED_VERBS)
def test_cli_failed_write_prints_error_and_exits_1(plan_context, verb):
    _block_log_file(_init_plan(plan_context), verb)

    result = _run_cli(plan_context, verb)

    assert result.returncode == 1, f'stdout={result.stdout!r} stderr={result.stderr!r}'
    data = result.toon()
    assert data.get('status') == 'error'
    assert data.get('error') == 'write_failed'


@pytest.mark.parametrize('verb', CHECKED_VERBS)
def test_cli_successful_write_is_silent_and_exits_0(plan_context, verb):
    plan_dir = _init_plan(plan_context)

    result = _run_cli(plan_context, verb)

    assert result.returncode == 0, f'stdout={result.stdout!r} stderr={result.stderr!r}'
    assert result.stdout.strip() == ''
    assert f'{verb} entry through the CLI' in (plan_dir / 'logs' / _LOG_FILE[verb]).read_text(encoding='utf-8')


def test_script_verb_stays_best_effort_on_a_failed_write(plan_context):
    blocked = _block_log_file(_init_plan(plan_context), 'script')

    result = handle_write(_write_args('script'))

    assert result is None
    assert blocked.is_dir(), 'control: the log path must still be the blocking directory'


@pytest.mark.parametrize('verb', CHECKED_VERBS)
def test_log_entry_stays_best_effort_on_the_same_failing_path(plan_context, verb):
    blocked = _block_log_file(_init_plan(plan_context), verb)

    assert plan_logging.log_entry(verb, _PLAN_ID, 'INFO', 'in-process entry') is None
    with pytest.raises(OSError):
        plan_logging.write_log_entry(verb, _PLAN_ID, 'INFO', 'in-process entry')
    assert blocked.is_dir()


@pytest.mark.parametrize('verb', CHECKED_VERBS)
def test_disabled_logging_is_not_a_failure(plan_context, monkeypatch, verb):
    _block_log_file(_init_plan(plan_context), verb)
    monkeypatch.setattr(plan_logging, 'LOG_ENABLED', False)

    assert handle_write(_write_args(verb)) is None


@pytest.mark.parametrize('verb', CHECKED_VERBS)
def test_orchestrator_store_refusal_is_not_converted_into_write_failed(plan_context, monkeypatch, verb):
    def _refuse(*_args, **_kwargs):
        raise OrchestratorStoreUnavailable('ledger_cutover_refused', 'store refused')

    monkeypatch.setattr(plan_logging, 'get_store_dir', _refuse)
    args = parse_ns(
        'plan-marshall',
        'manage-logging',
        'manage-logging.py',
        verb,
        '--plan-id',
        'refused-epic',
        '--level',
        'INFO',
        '--message',
        'orchestrator entry',
        '--store',
        'orchestrator',
    )

    with pytest.raises(OrchestratorStoreUnavailable) as refusal:
        handle_write(args)
    assert refusal.value.code == 'ledger_cutover_refused'
