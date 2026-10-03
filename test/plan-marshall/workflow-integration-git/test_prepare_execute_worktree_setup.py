#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for prepare_execute's project-declared worktree setup seam.

Contract under test (``plan.phase-5-execute.worktree_setup_commands``):

* An absent or empty key is a no-op — ``worktree_setup[]`` is empty and no
  command runs.
* A key present with a non-list value — JSON ``null`` included — is reported
  and runs nothing.
* A declared argv list runs with ``cwd`` pinned to the worktree, no shell,
  stdout discarded and in its own session — asserted at the
  ``subprocess.Popen`` primitive.
* A failing command is reported (exit code + last stderr line) while the move-in
  still returns ``status: success`` and the plan dir stays moved in.
* A command that times out has its whole process group killed and is then
  reaped, and is reported as timed out.
* The re-entry responder (``noop`` and ``healed``) runs the commands too.
* manage-config seeds the key with an empty list.

Isolation mirrors ``test_prepare_execute_prepare_core.py``: an isolated main
checkout + worktree root under ``tmp_path``, ``cmd_worktree_create`` and the
executor generation stubbed, and ``subprocess.Popen`` and ``os.killpg``
replaced by recorders so no declared command ever really executes and no real
process group is ever signalled.
"""

from __future__ import annotations

import json
import signal
import subprocess
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest

from conftest import load_script_module

prepare_execute = load_script_module(
    'plan-marshall',
    'workflow-integration-git',
    'prepare_execute.py',
    'prepare_execute_for_worktree_setup_test',
)

_config_defaults_mod = load_script_module(
    'plan-marshall',
    'manage-config',
    '_config_defaults.py',
    module_name='_config_defaults_for_worktree_setup_test',
)

PLAN_ID = 'sample-plan'
GENERATE_ARGV = ['./pw', 'generate', '--target', 'all', '--output', 'target']
FAKE_PID = 424242


# =============================================================================
# Fixtures
# =============================================================================


def _write_marshal(worktree_path: Path, phase_5: dict[str, Any] | None) -> None:
    """Write the worktree's tracked ``.plan/marshal.json`` (``None`` = no file)."""
    if phase_5 is None:
        return
    marshal = worktree_path / '.plan' / 'marshal.json'
    marshal.parent.mkdir(parents=True, exist_ok=True)
    marshal.write_text(json.dumps({'plan': {'phase-5-execute': phase_5}}, indent=2) + '\n', encoding='utf-8')


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Stage main + worktree root and record every ``subprocess.Popen`` launch.

    ``env['phase_5']`` is the ``plan.phase-5-execute`` block the stubbed
    ``worktree-create`` writes into the fresh worktree's marshal.json (``None``
    writes no file). ``env['calls']`` collects ``(argv, kwargs)`` per recorded
    launch; ``env['result']`` is the command's outcome — a ``CompletedProcess``
    to report, a ``TimeoutExpired`` the wait raises, or any other exception the
    launch itself raises. ``env['events']`` records the wait / kill / reap
    sequence, and ``env['killpg_error']`` is raised by the recorded
    ``os.killpg`` when set.
    """
    main = tmp_path / 'main'
    plan_dir = main / '.plan' / 'local' / 'plans' / PLAN_ID
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text('{}\n')
    (main / '.plan' / 'execute-script.py').write_text('#!/usr/bin/env python3\n')
    worktrees_root = tmp_path / 'worktrees'
    worktrees_root.mkdir()
    monkeypatch.chdir(main)

    state: dict[str, Any] = {
        'main': main,
        'plan_dir': plan_dir,
        'worktree_path': worktrees_root / PLAN_ID,
        'phase_5': None,
        'calls': [],
        'result': None,
        'events': [],
        'killpg_error': None,
    }

    monkeypatch.setattr(prepare_execute, 'get_plan_dir', lambda pid: main / '.plan' / 'local' / 'plans' / pid)
    monkeypatch.setattr(prepare_execute, 'get_worktree_root', lambda: worktrees_root)

    def fake_generate(worktree_path: Path, plan_id: str) -> tuple[bool, str]:
        wt_exec = worktree_path / '.plan' / 'execute-script.py'
        wt_exec.parent.mkdir(parents=True, exist_ok=True)
        wt_exec.write_text('#!/usr/bin/env python3\n# worktree-bound\n')
        return True, f'worktree executor generated at {wt_exec}'

    monkeypatch.setattr(prepare_execute, '_generate_worktree_executor', fake_generate)

    def fake_worktree_create(args: Namespace) -> dict:
        target = worktrees_root / args.plan_id
        (target / '.plan' / 'local').mkdir(parents=True, exist_ok=True)
        _write_marshal(target, state['phase_5'])
        return {'status': 'success', 'plan_id': args.plan_id, 'worktree_path': str(target)}

    fake_module = type('M', (), {'cmd_worktree_create': staticmethod(fake_worktree_create)})()
    monkeypatch.setattr(prepare_execute, '_load_git_workflow', lambda: fake_module)

    class RecordingPopen:
        """Stand-in for ``subprocess.Popen`` that never starts a process.

        A ``TimeoutExpired`` outcome is raised by the first ``communicate``
        only: the code under test kills the group and then reaps, and the reap
        must return.
        """

        pid = FAKE_PID

        def __init__(self, argv: Any, **kwargs: Any) -> None:
            state['calls'].append((argv, kwargs))
            outcome = state['result']
            if isinstance(outcome, BaseException) and not isinstance(outcome, subprocess.TimeoutExpired):
                raise outcome
            self._outcome = outcome
            self._timed_out = False
            self.returncode: int | None = None
            self.stderr = None

        def communicate(self, timeout: float | None = None) -> tuple[None, str]:
            state['events'].append(('communicate', timeout))
            if isinstance(self._outcome, subprocess.TimeoutExpired) and not self._timed_out:
                self._timed_out = True
                raise self._outcome
            if isinstance(self._outcome, subprocess.CompletedProcess):
                self.returncode = self._outcome.returncode
                return None, self._outcome.stderr
            self.returncode = -9 if self._timed_out else 0
            return None, ''

    def recording_killpg(pgid: int, sig: int) -> None:
        state['events'].append(('killpg', pgid, sig))
        if state['killpg_error'] is not None:
            raise state['killpg_error']

    monkeypatch.setattr(prepare_execute.subprocess, 'Popen', RecordingPopen)
    # Always replaced: FAKE_PID names no process of this test, so a real
    # os.killpg must never be reachable from here.
    monkeypatch.setattr(prepare_execute.os, 'killpg', recording_killpg)
    return state


def _prepare() -> dict[str, Any]:
    result: dict[str, Any] = prepare_execute.run_prepare_execute(
        Namespace(plan_id=PLAN_ID, branch=f'feature/{PLAN_ID}', base=None)
    )
    return result


# =============================================================================
# (a) absent / empty key is a no-op
# =============================================================================


class TestNoDeclaredCommands:
    @pytest.mark.parametrize(
        'phase_5',
        [None, {}, {'worktree_setup_commands': []}],
        ids=['no-marshal-json', 'key-absent', 'empty-list'],
    )
    def test_absent_or_empty_key_runs_nothing(self, env: dict[str, Any], phase_5: dict[str, Any] | None) -> None:
        env['phase_5'] = phase_5

        result = _prepare()

        assert result['status'] == 'success', result
        assert result['action'] == 'moved'
        assert result['worktree_setup'] == []
        assert env['calls'] == []


# =============================================================================
# (b) a declared command runs with cwd = worktree, no shell
# =============================================================================


class TestDeclaredCommandRuns:
    def test_command_runs_in_worktree_without_shell(self, env: dict[str, Any]) -> None:
        env['phase_5'] = {'worktree_setup_commands': [GENERATE_ARGV]}

        result = _prepare()

        assert result['status'] == 'success', result
        assert len(env['calls']) == 1
        argv, kwargs = env['calls'][0]
        assert argv == GENERATE_ARGV
        assert kwargs['cwd'] == str(env['worktree_path'])
        assert kwargs.get('shell', False) is False
        assert result['worktree_setup'] == [
            {'command': './pw generate --target all --output target', 'exit_code': 0, 'detail': 'ok'}
        ]
        assert env['events'] == [('communicate', prepare_execute._SETUP_COMMAND_TIMEOUT_SECONDS)]

    def test_command_is_launched_with_stdout_discarded_in_a_new_session(self, env: dict[str, Any]) -> None:
        env['phase_5'] = {'worktree_setup_commands': [GENERATE_ARGV]}

        _prepare()

        _, kwargs = env['calls'][0]
        assert (kwargs['stdout'], kwargs['stderr'], kwargs['start_new_session']) == (
            subprocess.DEVNULL,
            subprocess.PIPE,
            True,
        )

    def test_malformed_entry_is_reported_and_never_run(self, env: dict[str, Any]) -> None:
        env['phase_5'] = {'worktree_setup_commands': ['./pw generate', [], GENERATE_ARGV]}

        result = _prepare()

        assert result['status'] == 'success', result
        # Only the well-formed argv list reached the subprocess primitive.
        assert [argv for argv, _ in env['calls']] == [GENERATE_ARGV]
        setup = result['worktree_setup']
        assert [record['exit_code'] for record in setup] == [None, None, 0]
        assert setup[0]['detail'].startswith('skipped:')
        assert setup[1]['detail'].startswith('skipped:')

    @pytest.mark.parametrize('value', ['./pw generate', None], ids=['string', 'json-null'])
    def test_non_list_key_is_reported_without_running(self, env: dict[str, Any], value: Any) -> None:
        """A key that is present with a non-list value is reported, ``null`` included.

        Its matched control is the ``key-absent`` case above: the same config
        without the key runs nothing and reports nothing.
        """
        env['phase_5'] = {'worktree_setup_commands': value}

        result = _prepare()

        assert result['status'] == 'success', result
        assert env['calls'] == []
        assert len(result['worktree_setup']) == 1
        assert result['worktree_setup'][0]['exit_code'] is None
        assert 'not a list' in result['worktree_setup'][0]['detail']

    def test_invalid_utf8_marshal_is_reported_as_unreadable(self, tmp_path: Path) -> None:
        """A marshal.json that is not valid UTF-8 is a read failure, not a crash.

        ``read_text`` raises ``UnicodeDecodeError``, which is not an ``OSError``;
        it must reach the same ``cannot read`` record instead of escaping.
        """
        marshal = tmp_path / '.plan' / 'marshal.json'
        marshal.parent.mkdir(parents=True)
        marshal.write_bytes(b'{"plan": "\xff\xfe"}')

        entries, error = prepare_execute._read_worktree_setup_commands(tmp_path)

        assert entries == []
        assert error is not None
        assert error.startswith(f'cannot read {marshal}:')


# =============================================================================
# (c) a failing command is reported; the move-in is neither failed nor rolled back
# =============================================================================


class TestFailingCommandIsNonFatal:
    def _assert_still_moved_in(self, env: dict[str, Any], result: dict[str, Any]) -> None:
        assert result['status'] == 'success', result
        assert result['action'] == 'moved'
        wt_plan_dir = env['worktree_path'] / '.plan' / 'local' / 'plans' / PLAN_ID
        assert wt_plan_dir.is_dir()
        assert not env['plan_dir'].exists()

    def test_non_zero_exit_reported_with_last_stderr_line(self, env: dict[str, Any]) -> None:
        env['phase_5'] = {'worktree_setup_commands': [GENERATE_ARGV]}
        env['result'] = subprocess.CompletedProcess(GENERATE_ARGV, 3, stdout='', stderr='first\nlast line\n')

        result = _prepare()

        self._assert_still_moved_in(env, result)
        assert result['worktree_setup'] == [
            {'command': './pw generate --target all --output target', 'exit_code': 3, 'detail': 'last line'}
        ]

    def test_launch_failure_reported_with_null_exit_code(self, env: dict[str, Any]) -> None:
        env['phase_5'] = {'worktree_setup_commands': [GENERATE_ARGV]}
        env['result'] = FileNotFoundError(2, 'No such file or directory', './pw')

        result = _prepare()

        self._assert_still_moved_in(env, result)
        assert len(result['worktree_setup']) == 1
        record = result['worktree_setup'][0]
        assert record['exit_code'] is None
        assert record['detail'].startswith('failed to launch:')

    @pytest.mark.parametrize(
        'killpg_error',
        [None, ProcessLookupError(3, 'No such process')],
        ids=['group-killed', 'group-already-gone'],
    )
    def test_timeout_kills_the_process_group_then_reaps(
        self, env: dict[str, Any], killpg_error: BaseException | None
    ) -> None:
        """A timed-out command takes its whole process group down with it.

        The command is its own session leader, so its pid is the group id the
        kill is sent to. The reap follows the kill, and a group that is already
        gone changes nothing about the reported outcome.
        """
        env['phase_5'] = {'worktree_setup_commands': [GENERATE_ARGV]}
        env['result'] = subprocess.TimeoutExpired(GENERATE_ARGV, 900)
        env['killpg_error'] = killpg_error

        result = _prepare()

        self._assert_still_moved_in(env, result)
        assert result['worktree_setup'] == [
            {
                'command': './pw generate --target all --output target',
                'exit_code': None,
                'detail': f'timed out after {prepare_execute._SETUP_COMMAND_TIMEOUT_SECONDS}s',
            }
        ]
        assert env['events'] == [
            ('communicate', prepare_execute._SETUP_COMMAND_TIMEOUT_SECONDS),
            ('killpg', FAKE_PID, signal.SIGKILL),
            ('communicate', prepare_execute._SETUP_REAP_TIMEOUT_SECONDS),
        ]

    def test_a_command_that_finishes_in_time_is_never_signalled(self, env: dict[str, Any]) -> None:
        """Matched control for the timeout kill: no timeout, no signal."""
        env['phase_5'] = {'worktree_setup_commands': [GENERATE_ARGV]}

        _prepare()

        assert [event[0] for event in env['events']] == ['communicate']


# =============================================================================
# (d) the re-entry responder runs the commands too
# =============================================================================


class TestReEntryRunsCommands:
    @pytest.mark.parametrize(
        ('drop_executor', 'expected_action'),
        [(False, 'noop'), (True, 'healed')],
        ids=['noop', 'healed'],
    )
    def test_re_entry_runs_declared_commands(
        self, env: dict[str, Any], drop_executor: bool, expected_action: str
    ) -> None:
        # First run moves in with nothing declared.
        first = _prepare()
        assert first['action'] == 'moved'
        assert env['calls'] == []

        # The worktree now declares a command; a re-run of prepare builds it.
        _write_marshal(env['worktree_path'], {'worktree_setup_commands': [GENERATE_ARGV]})
        if drop_executor:
            (env['worktree_path'] / '.plan' / 'execute-script.py').unlink()

        second = _prepare()

        assert second['status'] == 'success', second
        assert second['action'] == expected_action
        assert len(env['calls']) == 1
        argv, kwargs = env['calls'][0]
        assert argv == GENERATE_ARGV
        assert kwargs['cwd'] == str(env['worktree_path'])
        assert second['worktree_setup'][0]['exit_code'] == 0


# =============================================================================
# (e) manage-config seeds the key with an empty list
# =============================================================================


class TestConfigDefault:
    def test_default_is_empty_list(self) -> None:
        assert _config_defaults_mod.DEFAULT_PLAN_EXECUTE['worktree_setup_commands'] == []

    def test_seeded_default_config_carries_empty_list(self) -> None:
        seeded = _config_defaults_mod.get_default_config()
        assert seeded['plan']['phase-5-execute']['worktree_setup_commands'] == []
