#!/usr/bin/env python3
"""End-to-end regression for the set_terminal_title.py hook-delivery path.

These tests pin the contract introduced by Claude Code 2.1.141: hook
subprocesses emit ``{"terminalSequence": "<OSC>"}`` JSON on stdout, and
Claude Code's hook-output parser forwards the escape sequence to the
controlling terminal. The pre-2.1.139 ``/dev/tty`` write path is gone.

The captured-stdio shape (no controlling TTY) is forced by
``start_new_session=True`` on the subprocess; the script's emission path
no longer touches ``/dev/tty`` regardless, so the contract is purely
about the JSON payload on stdout.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import TestCase

from conftest import MARKETPLACE_ROOT  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-marshall'
    / 'scripts'
    / 'set_terminal_title.py'
)

# Hard byte constants — the production path renders the OSC escape exactly
# as ``\033]0;{title}\007`` inside the terminalSequence JSON value.
OSC_PREFIX = '\033]0;'
OSC_TERMINATOR = '\x07'


def _run_hook_subprocess(
    *script_args: str,
    stdin_payload: str = '',
    cwd: Path | None = None,
    env_overrides: dict[str, str] | None = None,
    timeout: int = 15,
) -> subprocess.CompletedProcess:
    """Spawn the title script in a fresh session (no controlling TTY).

    Mirrors Claude Code's hook-invocation shape: stdin carries the hook
    payload as JSON, stdout/stderr are captured, and ``start_new_session``
    detaches the child from the parent's controlling terminal. The
    captured stdout is parsed as JSON by callers to assert the
    terminalSequence contract.
    """
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *script_args],
        input=stdin_payload,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd is not None else None,
        env=env,
        timeout=timeout,
        start_new_session=True,
        check=False,
    )


class TestHookDeliveryEmitsTerminalSequenceJson(TestCase):
    """Cases (a)-(c): every hook-status invocation emits a JSON object on
    stdout containing key ``terminalSequence`` whose value is the OSC
    escape ``\\033]0;{title}\\007`` for the resolved title. Case (d) is
    the positive control that the ``--statusline`` path STILL emits the
    plain rendered title (no JSON, no OSC bytes)."""

    def setUp(self) -> None:
        # PLAN_ID='' suppresses the env-fallback plan resolution so the
        # main-checkout cases genuinely see "no plan worktree" and fall
        # through to the ``◯ claude`` / ``▶ claude`` rendering. The
        # active-plan scan is also suppressed because cwd is forced to a
        # directory with no ``.plan`` tree.
        self.base_env: dict[str, str] = {'PLAN_ID': ''}

    def _parse_payload(self, result: subprocess.CompletedProcess) -> dict:
        self.assertEqual(
            result.returncode,
            0,
            msg=f'non-zero exit: rc={result.returncode}, stderr={result.stderr!r}',
        )
        self.assertEqual(
            result.stderr,
            '',
            msg=f'unexpected stderr output: {result.stderr!r}',
        )
        try:
            payload = json.loads(result.stdout)
        except ValueError as exc:
            self.fail(
                f'stdout is not valid JSON: {result.stdout!r} ({exc})'
            )
        self.assertIsInstance(payload, dict)
        return payload

    def _assert_terminal_sequence(
        self,
        result: subprocess.CompletedProcess,
        expected_title: str,
    ) -> None:
        payload = self._parse_payload(result)
        self.assertIn('terminalSequence', payload)
        self.assertEqual(
            payload['terminalSequence'],
            f'{OSC_PREFIX}{expected_title}{OSC_TERMINATOR}',
        )

    def test_running_status_no_plan_worktree(self) -> None:
        """Case (a): UserPromptSubmit hook with no active plan.

        Subprocess cwd is forced to ``/`` so neither the cwd-driven
        worktree regex nor the active-plan scan matches; PLAN_ID=''
        suppresses the env fallback. The script's resolution chain
        lands on ``▶ claude`` and emits the JSON payload on stdout.
        """
        payload = json.dumps(
            {
                'cwd': '/tmp/no-plan-here',
                'prompt': 'just a normal user message',
                'session_id': 's-running-no-plan',
            }
        )
        result = _run_hook_subprocess(
            'running',
            stdin_payload=payload,
            cwd=Path('/'),
            env_overrides=self.base_env,
        )
        self._assert_terminal_sequence(result, '▶ claude')

    def test_idle_status_no_plan_worktree(self) -> None:
        """Case (b): a Notification/Stop hook fires with idle status and
        no resolvable plan. The contract is identical to case (a):
        valid JSON on stdout containing the terminalSequence for
        ``◯ claude``.
        """
        payload = json.dumps(
            {
                'cwd': '/tmp/elsewhere',
                'session_id': 's-idle-no-plan',
            }
        )
        result = _run_hook_subprocess(
            'idle',
            stdin_payload=payload,
            cwd=Path('/'),
            env_overrides=self.base_env,
        )
        self._assert_terminal_sequence(result, '◯ claude')

    def test_waiting_status_captured_stdio(self) -> None:
        """Case (c): the AskUserQuestion PostToolUse hook fires with
        ``waiting`` and no resolvable plan. Same contract — JSON
        on stdout containing the terminalSequence for ``? claude``."""
        payload = json.dumps(
            {
                'cwd': '/tmp/elsewhere',
                'session_id': 's-waiting',
            }
        )
        result = _run_hook_subprocess(
            'waiting',
            stdin_payload=payload,
            cwd=Path('/'),
            env_overrides=self.base_env,
        )
        self._assert_terminal_sequence(result, '? claude')

    def test_statusline_idle_positive_control(self) -> None:
        """Case (d): the ``--statusline`` path is the legitimate Claude
        Code statusLine contract — it MUST write the plain rendered
        title to stdout (NOT JSON, NOT OSC bytes).

        This is the positive control: confirms the test harness can
        observe stdout output when the production path is supposed to
        emit plain text, ruling out a false-green for cases (a)-(c).

        Subprocess cwd is forced to ``/`` so neither the worktree
        regex, env fallback, nor active-plan scan finds a live plan;
        the rendered title is the stable fallback ``◯ claude``.
        """
        result = _run_hook_subprocess(
            '--statusline',
            'idle',
            stdin_payload='',
            cwd=Path('/'),
            env_overrides=self.base_env,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f'statusline exit: rc={result.returncode}, stderr={result.stderr!r}',
        )
        self.assertEqual(result.stdout.strip(), '◯ claude')
        # OSC escape bytes are never used on the statusline path — only the
        # rendered plain-text title is written. JSON is the hook-mode
        # contract; --statusline bypasses it.
        self.assertNotIn(OSC_PREFIX, result.stdout)
        self.assertNotIn(OSC_TERMINATOR, result.stdout)
        self.assertEqual(result.stderr, '')
