#!/usr/bin/env python3
"""End-to-end regression for the set_terminal_title.py hook-delivery path.

These tests pin the contract introduced by deliverable 1: when the hook
subprocess runs without a controlling terminal (Claude Code's captured-stdio
shape — SessionStart / UserPromptSubmit / Notification / PostToolUse /
Stop hooks), no OSC title bytes (``\\033]0;...\\007``) MUST leak to
``sys.stdout``. The ``--statusline`` path is the only legitimate
stdout-writing channel and is exercised as a positive control.

The captured-stdio shape is forced by ``start_new_session=True`` on the
subprocess: the child detaches from the controlling terminal, so
``open('/dev/tty', 'w')`` inside the script raises ``OSError`` and the
fallback branch (which is now silent — see deliverable 1) is taken.
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
# as ``\033]0;{title}\007``. Tests assert these bytes are NEVER on stdout
# under the captured-stdio shape.
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
    detaches the child from the parent's controlling terminal so that
    ``open('/dev/tty', 'w')`` inside the script raises ``OSError`` (ENXIO).
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


class TestHookDeliveryNeverLeaksOscBytes(TestCase):
    """Cases (a)–(c): every hook-status invocation under captured-stdio
    exits 0 with empty stdout and empty stderr — the production
    contract introduced by deliverable 1. Case (d) is the positive control
    that the --statusline path STILL emits the rendered title to stdout."""

    def setUp(self) -> None:
        # PLAN_ID='' suppresses the env-fallback plan resolution so case (a)
        # genuinely sees "no plan worktree" and falls through to the
        # ``◯ claude`` / ``▶ claude`` rendering.
        self.base_env: dict[str, str] = {'PLAN_ID': ''}

    def _assert_clean_hook_run(self, result: subprocess.CompletedProcess) -> None:
        self.assertEqual(
            result.returncode,
            0,
            msg=f'non-zero exit: rc={result.returncode}, stderr={result.stderr!r}',
        )
        self.assertEqual(
            result.stdout,
            '',
            msg=f'unexpected stdout output: {result.stdout!r}',
        )
        self.assertNotIn(
            OSC_PREFIX,
            result.stdout,
            msg=f'OSC prefix leaked to stdout: {result.stdout!r}',
        )
        self.assertNotIn(
            OSC_TERMINATOR,
            result.stdout,
            msg=f'OSC terminator (BEL) leaked to stdout: {result.stdout!r}',
        )
        self.assertEqual(
            result.stderr,
            '',
            msg=f'unexpected stderr output: {result.stderr!r}',
        )

    def test_running_status_no_plan_worktree(self) -> None:
        """Case (a): a UserPromptSubmit hook fires with no active plan.

        Subprocess cwd is forced to ``/`` so the cwd-driven resolver
        cannot match the worktree regex; PLAN_ID='' suppresses the env
        fallback. The script's resolution chain lands on ``▶ claude``;
        under captured-stdio (``start_new_session=True``) the OSC bytes
        are silently dropped — stdout and stderr are empty, exit 0.
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
        self._assert_clean_hook_run(result)

    def test_idle_status_from_plan_worktree_cwd(self) -> None:
        """Case (b): a Notification/Stop hook fires from inside a plan
        worktree. The on-stdin ``cwd`` mimics a real worktree path; the
        in-script regex (`_resolve_plan_id`) extracts ``sample-plan``
        from that string, and the subsequent status.json walk-up fails
        (no .plan tree at the synthetic location). The title resolution
        lands on the ``claude`` fallback. Even in the alternate branch
        where a status.json existed, the contract under captured-stdio
        is unchanged: no OSC bytes on stdout, exit 0, empty stderr.

        ``cwd=/`` for the subprocess itself keeps the script's own
        ``os.getcwd()`` from accidentally matching the host worktree.
        """
        cwd_payload = '/tmp/repo/.plan/local/worktrees/sample-plan'
        payload = json.dumps(
            {
                'cwd': cwd_payload,
                'session_id': 's-idle-plan',
            }
        )
        result = _run_hook_subprocess(
            'idle',
            stdin_payload=payload,
            cwd=Path('/'),
            env_overrides=self.base_env,
        )
        self._assert_clean_hook_run(result)

    def test_waiting_status_captured_stdio(self) -> None:
        """Case (c): the AskUserQuestion PostToolUse hook fires with
        ``waiting``. Captured-stdio shape, same contract — no OSC bytes
        on stdout, exit 0, empty stderr."""
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
        self._assert_clean_hook_run(result)

    def test_statusline_idle_positive_control(self) -> None:
        """Case (d): the ``--statusline`` path is the legitimate Claude Code
        statusLine contract — it MUST write the rendered title to stdout.

        This is the positive control: it confirms the test harness can
        observe stdout output when the production path is supposed to
        emit it, ruling out a false-green for cases (a)–(c).

        The subprocess cwd is forced to ``/`` so neither the worktree
        regex nor walk-up resolution finds a live plan; the rendered
        title is the stable fallback ``◯ claude``.
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
        # rendered plain-text title is written.
        self.assertNotIn(OSC_PREFIX, result.stdout)
        self.assertNotIn(OSC_TERMINATOR, result.stdout)
        self.assertEqual(result.stderr, '')
