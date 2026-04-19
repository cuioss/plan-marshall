#!/usr/bin/env python3
"""Tests for set_terminal_title.py — the plan-marshall terminal-title and
statusline emitter invoked from Claude Code hooks.

Uses Tier 2 (direct import) tests for the core logic and a small number of
subprocess tests to exercise the CLI plumbing + real stdout emission.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

from conftest import MARKETPLACE_ROOT, ScriptTestCase, run_script

import set_terminal_title  # type: ignore[import-not-found]  # noqa: E402

SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall' / 'scripts' / 'set_terminal_title.py'


PLAN_ID = 'my-plan'


def _write_status(plan_dir: Path, phase: str) -> Path:
    plan_dir.mkdir(parents=True, exist_ok=True)
    status = plan_dir / 'status.json'
    status.write_text(json.dumps({'current_phase': phase}), encoding='utf-8')
    return status


class TestPlanIdResolution(ScriptTestCase):
    """_resolve_plan_id: worktree regex vs $PLAN_ID env vs none."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_worktree_cwd_matches(self):
        cwd = '/Users/x/repo/.claude/worktrees/my-plan/marketplace'
        self.assertEqual(set_terminal_title._resolve_plan_id(cwd), 'my-plan')

    def test_worktree_cwd_without_trailing_path(self):
        cwd = '/repo/.claude/worktrees/only-id'
        self.assertEqual(set_terminal_title._resolve_plan_id(cwd), 'only-id')

    def test_env_fallback_when_no_worktree_match(self):
        with mock.patch.dict(os.environ, {'PLAN_ID': 'from-env'}, clear=False):
            self.assertEqual(set_terminal_title._resolve_plan_id('/tmp/not-a-worktree'), 'from-env')

    def test_worktree_wins_over_env(self):
        cwd = '/r/.claude/worktrees/from-cwd'
        with mock.patch.dict(os.environ, {'PLAN_ID': 'from-env'}, clear=False):
            self.assertEqual(set_terminal_title._resolve_plan_id(cwd), 'from-cwd')

    def test_no_plan_when_neither_present(self):
        env = {k: v for k, v in os.environ.items() if k != 'PLAN_ID'}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertIsNone(set_terminal_title._resolve_plan_id('/tmp/nowhere'))


class TestPlanShort(ScriptTestCase):
    """_plan_short truncation."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_short_verbatim(self):
        self.assertEqual(set_terminal_title._plan_short('short-id'), 'short-id')

    def test_at_boundary_verbatim(self):
        plan_id = 'a' * 20
        self.assertEqual(set_terminal_title._plan_short(plan_id), plan_id)

    def test_long_truncated_with_ellipsis(self):
        plan_id = 'dynamic-terminal-title-statusline'  # 32 chars
        result = set_terminal_title._plan_short(plan_id)
        self.assertTrue(result.startswith('\u2026'))
        self.assertEqual(len(result), 15)  # ellipsis (1) + tail (14)
        self.assertTrue(plan_id.endswith(result[1:]))


class TestBuildTitle(ScriptTestCase):
    """_build_title icon + plan-phase formatting."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_running_with_plan(self):
        title = set_terminal_title._build_title('running', 'my-plan', '5-execute')
        self.assertEqual(title, '\u25b6 my-plan:5-execute')

    def test_waiting_with_plan(self):
        title = set_terminal_title._build_title('waiting', 'my-plan', '2-refine')
        self.assertTrue(title.startswith('? '))
        self.assertIn(':2-refine', title)

    def test_idle_with_plan(self):
        title = set_terminal_title._build_title('idle', 'my-plan', '6-finalize')
        self.assertTrue(title.startswith('\u25ef '))

    def test_done_with_plan(self):
        title = set_terminal_title._build_title('done', 'my-plan', '6-finalize')
        self.assertTrue(title.startswith('\u2713 '))

    def test_no_plan_fallback(self):
        self.assertEqual(set_terminal_title._build_title('idle', None, None), '\u25ef claude')

    def test_no_phase_falls_back(self):
        self.assertEqual(set_terminal_title._build_title('running', 'my-plan', None), '\u25b6 my-plan:None' if False else '\u25b6 claude')


class TestStatusFileResolution(ScriptTestCase):
    """_resolve_status_file + _read_phase integration via walk-up path."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_walk_up_finds_plan_status(self):
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / PLAN_ID
        _write_status(plan_dir, '4-plan')
        nested = self.temp_dir / 'nested' / 'sub'
        nested.mkdir(parents=True)

        with mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None):
            status_file = set_terminal_title._resolve_status_file(str(nested), PLAN_ID)
            self.assertIsNotNone(status_file)
            self.assertEqual(set_terminal_title._read_phase(status_file), '4-plan')

    def test_missing_status_returns_none(self):
        nested = self.temp_dir / 'no-plan-here'
        nested.mkdir(parents=True)
        with mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None):
            self.assertIsNone(set_terminal_title._resolve_status_file(str(nested), PLAN_ID))

    def test_malformed_status_read_returns_none(self):
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / PLAN_ID
        plan_dir.mkdir(parents=True)
        bad = plan_dir / 'status.json'
        bad.write_text('not-json', encoding='utf-8')
        self.assertIsNone(set_terminal_title._read_phase(bad))


class TestBuildTitleEndToEnd(ScriptTestCase):
    """The top-level build_title function: cwd → plan_id → phase → title."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_with_env_plan_and_status_file(self):
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / PLAN_ID
        _write_status(plan_dir, '3-outline')
        with mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None), \
             mock.patch.dict(os.environ, {'PLAN_ID': PLAN_ID}, clear=False):
            title = set_terminal_title.build_title('running', str(self.temp_dir))
        self.assertEqual(title, '\u25b6 my-plan:3-outline')

    def test_fallback_when_no_plan(self):
        env = {k: v for k, v in os.environ.items() if k != 'PLAN_ID'}
        with mock.patch.dict(os.environ, env, clear=True):
            title = set_terminal_title.build_title('idle', str(self.temp_dir))
        self.assertEqual(title, '\u25ef claude')

    def test_fallback_when_status_missing(self):
        with mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None), \
             mock.patch.dict(os.environ, {'PLAN_ID': 'absent-plan'}, clear=False):
            title = set_terminal_title.build_title('running', str(self.temp_dir))
        self.assertEqual(title, '\u25b6 claude')


class TestEmitOsc(ScriptTestCase):
    """_emit_osc writes escape to /dev/tty and swallows OSError."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_oserror_is_swallowed(self):
        with mock.patch('builtins.open', side_effect=OSError('no tty')):
            # Must not raise.
            set_terminal_title._emit_osc('anything')

    def test_writes_escape_sequence_to_tty(self):
        written = []

        class FakeTTY:
            def __enter__(self_):
                return self_

            def __exit__(self_, *args):
                return False

            def write(self_, s):
                written.append(s)

            def flush(self_):
                pass

        with mock.patch('builtins.open', return_value=FakeTTY()):
            set_terminal_title._emit_osc('hello')

        self.assertEqual(written, ['\x1b]0;hello\x07'])


class TestCliIntegration(ScriptTestCase):
    """Subprocess tests for the --statusline path (stdout capture)."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_statusline_fallback_when_no_plan(self):
        env_overrides = {'PLAN_ID': ''}
        result = run_script(
            SCRIPT_PATH,
            '--statusline',
            'idle',
            input_data='',
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), '\u25ef claude')

    def test_statusline_reads_stdin_cwd(self):
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / PLAN_ID
        _write_status(plan_dir, '5-execute')
        # Make the temp_dir look like a git repo so the script can resolve
        # it without git subprocess interference: we supply cwd via stdin,
        # and rely on walk-up fallback to find .plan/.
        payload = json.dumps({'cwd': str(self.temp_dir / 'nested')})
        (self.temp_dir / 'nested').mkdir()

        env_overrides = {'PLAN_ID': PLAN_ID}
        result = run_script(
            SCRIPT_PATH,
            '--statusline',
            'running',
            input_data=payload,
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertIn(':5-execute', result.stdout)
        self.assertTrue(result.stdout.startswith('\u25b6 '))

    def test_exit_zero_on_missing_status_file(self):
        # No status.json anywhere → script must still exit 0 with fallback.
        env_overrides = {'PLAN_ID': 'nonexistent'}
        result = run_script(
            SCRIPT_PATH,
            '--statusline',
            'waiting',
            input_data='',
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        # PLAN_ID is set but status.json missing — falls back to `? claude`.
        self.assertEqual(result.stdout.strip(), '? claude')
