#!/usr/bin/env python3
"""Tests for set_terminal_title.py — the plan-marshall terminal-title and
statusline emitter invoked from Claude Code hooks.

Uses Tier 2 (direct import) tests for the core logic and a small number of
subprocess tests to exercise the CLI plumbing + real stdout emission.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from unittest import mock

import set_terminal_title  # type: ignore[import-not-found]  # noqa: E402

from conftest import MARKETPLACE_ROOT, ScriptTestCase, run_script  # noqa: E402

SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall' / 'scripts' / 'set_terminal_title.py'


PLAN_ID = 'my-plan'


def _write_status(plan_dir: Path, phase: str, short_description: str | None = None) -> Path:
    plan_dir.mkdir(parents=True, exist_ok=True)
    status = plan_dir / 'status.json'
    payload: dict[str, str] = {'current_phase': phase}
    if short_description is not None:
        payload['short_description'] = short_description
    status.write_text(json.dumps(payload), encoding='utf-8')
    return status


class TestPlanIdResolution(ScriptTestCase):
    """_resolve_plan_id: worktree-cwd regex is the sole plan-id source.

    The $PLAN_ID environment variable strategy was removed to prevent
    cross-tab title pollution: an inherited $PLAN_ID from a parent shell
    would render an unrelated plan's title in a freshly opened Claude
    Code tab. The hook payload's cwd is per-session and cannot leak
    across tabs, so the worktree-cwd regex is the only safe input.
    """

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_worktree_cwd_matches(self):
        # Worktree-cwd strategy requires the cwd to exist on disk (liveness
        # guard); use a real worktree path under self.temp_dir.
        cwd = self.temp_dir / '.plan' / 'local' / 'worktrees' / 'my-plan' / 'marketplace'
        cwd.mkdir(parents=True)
        self.assertEqual(set_terminal_title._resolve_plan_id(str(cwd)), 'my-plan')

    def test_worktree_cwd_without_trailing_path(self):
        cwd = self.temp_dir / '.plan' / 'local' / 'worktrees' / 'only-id'
        cwd.mkdir(parents=True)
        self.assertEqual(set_terminal_title._resolve_plan_id(str(cwd)), 'only-id')

    def test_legacy_claude_worktrees_no_longer_matches(self):
        """Legacy .claude/worktrees/ cwd is intentionally NOT recognized.

        Worktrees migrated to ``.plan/local/worktrees/`` with no compatibility
        fallback (compatibility: breaking). A legacy cwd must resolve to None.
        """
        cwd = self.temp_dir / '.claude' / 'worktrees' / 'old-plan' / 'marketplace'
        cwd.mkdir(parents=True)
        self.assertIsNone(set_terminal_title._resolve_plan_id(str(cwd)))

    def test_env_plan_id_is_ignored_when_cwd_outside_worktree(self):
        """Cross-tab isolation regression: an inherited $PLAN_ID env var MUST
        NOT influence plan-id resolution. A freshly opened Claude Code tab
        with $PLAN_ID exported by the parent shell but a cwd outside any
        worktree directory must resolve to None — never to the env-var value.

        This is the core invariant that prevents one tab's plan title from
        leaking into another tab's terminal.
        """
        with mock.patch.dict(os.environ, {'PLAN_ID': 'leaked-from-parent'}, clear=False):
            self.assertIsNone(set_terminal_title._resolve_plan_id('/tmp/not-a-worktree'))

    def test_env_plan_id_is_ignored_even_when_cwd_matches_worktree(self):
        """When the cwd matches a live worktree, the worktree directory name
        is the plan_id — the $PLAN_ID env var is ignored entirely.
        """
        cwd = self.temp_dir / '.plan' / 'local' / 'worktrees' / 'from-cwd'
        cwd.mkdir(parents=True)
        with mock.patch.dict(os.environ, {'PLAN_ID': 'leaked-from-parent'}, clear=False):
            self.assertEqual(set_terminal_title._resolve_plan_id(str(cwd)), 'from-cwd')

    def test_no_plan_when_cwd_outside_worktree(self):
        """When the cwd does not match a live worktree path, _resolve_plan_id
        returns None regardless of which plans live under .plan/local/plans/
        or which env vars are set. This is the fresh-session safety guarantee.
        """
        env = {k: v for k, v in os.environ.items() if k != 'PLAN_ID'}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertIsNone(set_terminal_title._resolve_plan_id('/tmp/nowhere'))

    def test_dead_worktree_cwd_falls_through(self):
        """The worktree-cwd strategy must verify the directory exists on disk.

        A stale cwd that string-matches a removed worktree path must resolve
        to None (the liveness guard rejects the regex match).
        """
        dead_cwd = '/nonexistent/repo/.plan/local/worktrees/ghost-plan/sub'
        self.assertIsNone(set_terminal_title._resolve_plan_id(dead_cwd))

    def test_windows_style_backslash_cwd_matches(self):
        """A Windows-style cwd with backslash separators must still resolve.

        Claude Code hooks running on Windows surface the cwd with native
        backslash separators. The regex uses forward slashes, so the
        resolver normalizes via Path(cwd).as_posix() before matching.

        The liveness guard (os.path.isdir) is mocked because the backslash
        path is not a real on-disk directory on POSIX hosts; the behaviour
        under test is regex normalization, not the liveness guard.
        """
        cwd = r'C:\Users\dev\repo\.plan\local\worktrees\my-plan\marketplace'
        with mock.patch.object(set_terminal_title.os.path, 'isdir', return_value=True):
            self.assertEqual(set_terminal_title._resolve_plan_id(cwd), 'my-plan')

    def test_path_traversal_double_dot_returns_none(self):
        """The regex character class [^/]+ accepts '..' as a path segment.

        A hostile or malformed cwd whose worktree segment is '..' would let
        the constructed status-file path escape the .plan/local/plans/ tree.
        The resolver must reject this explicitly and return None.

        The liveness guard is mocked so we exercise the traversal guard
        specifically (a '..' segment on disk is not a normal directory the
        test fixture sets up).
        """
        cwd = '/tmp/repo/.plan/local/worktrees/..'
        with mock.patch.object(set_terminal_title.os.path, 'isdir', return_value=True):
            self.assertIsNone(set_terminal_title._resolve_plan_id(cwd))

    def test_path_traversal_single_dot_returns_none(self):
        """Same rationale as '..': '.' as a plan_id segment would alias the
        current directory and bypass the per-plan isolation invariant. The
        resolver must reject single-dot too.
        """
        cwd = '/tmp/repo/.plan/local/worktrees/.'
        with mock.patch.object(set_terminal_title.os.path, 'isdir', return_value=True):
            self.assertIsNone(set_terminal_title._resolve_plan_id(cwd))


class TestBuildTitle(ScriptTestCase):
    """_build_title icon + plan-phase formatting."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_running_with_plan(self):
        title = set_terminal_title._build_title('running', 'my-plan', '5-execute')
        self.assertEqual(title, '▶ pm:5-execute')

    def test_waiting_with_plan(self):
        title = set_terminal_title._build_title('waiting', 'my-plan', '2-refine')
        self.assertTrue(title.startswith('? '))
        self.assertIn(':2-refine', title)
        self.assertIn('pm:', title)

    def test_idle_with_plan(self):
        title = set_terminal_title._build_title('idle', 'my-plan', '6-finalize')
        self.assertTrue(title.startswith('◯ '))

    def test_done_with_plan(self):
        title = set_terminal_title._build_title('done', 'my-plan', '6-finalize')
        self.assertTrue(title.startswith('✓ '))

    def test_no_plan_fallback(self):
        self.assertEqual(set_terminal_title._build_title('idle', None, None), '◯ claude')

    def test_no_phase_falls_back(self):
        # When phase is missing, plan-active branch does not render; falls through to claude.
        self.assertEqual(set_terminal_title._build_title('running', 'my-plan', None), '▶ claude')

    def test_plan_active_with_short_description(self):
        """A non-empty short_description is appended after `pm:{phase}`."""
        title = set_terminal_title._build_title(
            'running', 'my-plan', '4-plan', short_description='Refactor_title_handling'
        )
        self.assertEqual(title, '▶ pm:4-plan:Refactor_title_handling')

    def test_plan_active_missing_short_description(self):
        """A None short_description yields the 2-segment plan-active form."""
        title = set_terminal_title._build_title('running', 'my-plan', '2-refine', short_description=None)
        self.assertEqual(title, '▶ pm:2-refine')

    def test_plan_active_empty_short_description(self):
        """An empty-string short_description is treated as missing (no trailing colon)."""
        title = set_terminal_title._build_title('running', 'my-plan', '2-refine', short_description='')
        self.assertEqual(title, '▶ pm:2-refine')


class TestReadPlanMeta(ScriptTestCase):
    """_read_plan_meta extracts (current_phase, short_description) from status.json."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_returns_both_fields_when_present(self):
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / PLAN_ID
        status = _write_status(plan_dir, '4-plan', short_description='Refactor_title_handling')
        phase, short = set_terminal_title._read_plan_meta(status)
        self.assertEqual(phase, '4-plan')
        self.assertEqual(short, 'Refactor_title_handling')

    def test_returns_phase_only_when_short_description_missing(self):
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / PLAN_ID
        status = _write_status(plan_dir, '2-refine')
        phase, short = set_terminal_title._read_plan_meta(status)
        self.assertEqual(phase, '2-refine')
        self.assertIsNone(short)

    def test_empty_short_description_treated_as_none(self):
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / PLAN_ID
        status = _write_status(plan_dir, '3-outline', short_description='')
        phase, short = set_terminal_title._read_plan_meta(status)
        self.assertEqual(phase, '3-outline')
        self.assertIsNone(short)

    def test_malformed_json_returns_none_tuple(self):
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / PLAN_ID
        plan_dir.mkdir(parents=True)
        bad = plan_dir / 'status.json'
        bad.write_text('not-json', encoding='utf-8')
        self.assertEqual(set_terminal_title._read_plan_meta(bad), (None, None))

    def test_non_dict_payload_returns_none_tuple(self):
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / PLAN_ID
        plan_dir.mkdir(parents=True)
        bad = plan_dir / 'status.json'
        bad.write_text('[1,2,3]', encoding='utf-8')
        self.assertEqual(set_terminal_title._read_plan_meta(bad), (None, None))


class TestStatusFileResolution(ScriptTestCase):
    """_resolve_status_file + _read_plan_meta integration via walk-up path."""

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
            phase, _ = set_terminal_title._read_plan_meta(status_file)
            self.assertEqual(phase, '4-plan')

    def test_missing_status_returns_none(self):
        nested = self.temp_dir / 'no-plan-here'
        nested.mkdir(parents=True)
        with mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None):
            self.assertIsNone(set_terminal_title._resolve_status_file(str(nested), PLAN_ID))


class TestBuildTitleEndToEnd(ScriptTestCase):
    """The top-level build_title function: cwd → plan_id → phase → title.

    Plan-id resolution is cwd-driven (worktree path). The $PLAN_ID env var
    is NOT a resolution input — these tests verify that invariant alongside
    the happy-path worktree-cwd rendering.
    """

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_worktree_cwd_with_status_file(self):
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / PLAN_ID
        _write_status(plan_dir, '3-outline')
        cwd = self.temp_dir / '.plan' / 'local' / 'worktrees' / PLAN_ID
        cwd.mkdir(parents=True)
        with mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None):
            title = set_terminal_title.build_title('running', str(cwd))
        self.assertEqual(title, '▶ pm:3-outline')

    def test_worktree_cwd_with_short_description(self):
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / PLAN_ID
        _write_status(plan_dir, '4-plan', short_description='Refactor_title_handling')
        cwd = self.temp_dir / '.plan' / 'local' / 'worktrees' / PLAN_ID
        cwd.mkdir(parents=True)
        with mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None):
            title = set_terminal_title.build_title('running', str(cwd))
        self.assertEqual(title, '▶ pm:4-plan:Refactor_title_handling')

    def test_fallback_when_no_plan(self):
        env = {k: v for k, v in os.environ.items() if k != 'PLAN_ID'}
        with mock.patch.dict(os.environ, env, clear=True):
            title = set_terminal_title.build_title('idle', str(self.temp_dir))
        self.assertEqual(title, '◯ claude')

    def test_cross_tab_isolation_regression(self):
        """Cross-tab title leak regression test.

        Scenario: Tab #1 runs a plan and exports $PLAN_ID into its parent
        shell. Tab #3 inherits the env var but its cwd is OUTSIDE any
        ``.plan/local/worktrees/{id}/`` path (e.g., the repo root or an
        unrelated directory). Tab #3 MUST render the ``◯ claude`` fallback
        regardless of whether a plan matching $PLAN_ID exists on disk.

        This is the core invariant that prevents one Claude Code tab's plan
        title from polluting another tab's terminal.
        """
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / 'leaked-plan'
        _write_status(plan_dir, '5-execute', short_description='Other_tab_plan')
        with (
            mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None),
            mock.patch.dict(os.environ, {'PLAN_ID': 'leaked-plan'}, clear=False),
        ):
            title = set_terminal_title.build_title('idle', str(self.temp_dir))
        self.assertEqual(title, '◯ claude')

    def test_cross_tab_isolation_for_nonexistent_plan_id(self):
        """An inherited $PLAN_ID with no on-disk plan also renders fallback.

        Pairs with ``test_cross_tab_isolation_regression`` to confirm the env
        var is unread regardless of whether the value resolves to an on-disk
        plan directory.
        """
        with mock.patch.dict(os.environ, {'PLAN_ID': 'no-such-plan'}, clear=False):
            title = set_terminal_title.build_title('idle', str(self.temp_dir))
        self.assertEqual(title, '◯ claude')

    def test_fallback_when_status_missing(self):
        """A worktree-cwd that matches the regex but lacks a status.json
        renders the fallback (no plan/phase context available).
        """
        cwd = self.temp_dir / '.plan' / 'local' / 'worktrees' / 'absent-plan'
        cwd.mkdir(parents=True)
        with mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None):
            title = set_terminal_title.build_title('running', str(cwd))
        self.assertEqual(title, '▶ claude')

    def test_dead_worktree_cwd_end_to_end_falls_through(self):
        """Worktree-cwd liveness guard regression test (end-to-end)."""
        dead_cwd = '/nonexistent/repo/.plan/local/worktrees/ghost-plan/sub'
        env = {k: v for k, v in os.environ.items() if k != 'PLAN_ID'}
        with mock.patch.dict(os.environ, env, clear=True):
            title = set_terminal_title.build_title('idle', dead_cwd)
        self.assertEqual(title, '◯ claude')

    def test_worktree_cwd_with_terminal_phase_falls_through(self):
        """When the resolved plan's current_phase is in the terminal set
        ({'complete', 'archived'}), build_title falls through as if no
        plan/phase were found.
        """
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / 'finished-plan'
        _write_status(plan_dir, 'complete', short_description='Done_label')
        cwd = self.temp_dir / '.plan' / 'local' / 'worktrees' / 'finished-plan'
        cwd.mkdir(parents=True)
        with mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None):
            title = set_terminal_title.build_title('idle', str(cwd))
        self.assertEqual(title, '◯ claude')

    def test_worktree_cwd_with_archived_phase_falls_through(self):
        """Terminal-phase rejection — 'archived' phase variant."""
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / 'finished-plan-2'
        _write_status(plan_dir, 'archived', short_description='Done_label')
        cwd = self.temp_dir / '.plan' / 'local' / 'worktrees' / 'finished-plan-2'
        cwd.mkdir(parents=True)
        with mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None):
            title = set_terminal_title.build_title('idle', str(cwd))
        self.assertEqual(title, '◯ claude')


class TestEmitTerminalSequence(ScriptTestCase):
    """_emit_terminal_sequence writes ``{"terminalSequence": "<OSC>"}``
    JSON to sys.stdout per the Claude Code 2.1.141+ hook output contract.
    """

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_writes_json_payload_to_stdout(self):
        fake_stdout = io.StringIO()
        with mock.patch.object(set_terminal_title.sys, 'stdout', fake_stdout):
            set_terminal_title._emit_terminal_sequence('hello')

        payload = json.loads(fake_stdout.getvalue())
        self.assertEqual(payload, {'terminalSequence': '\x1b]0;hello\x07'})

    def test_oserror_is_swallowed(self):
        """When stdout write fails, _emit_terminal_sequence must not raise."""

        class _RaisingStdout:
            def write(self, _s):
                raise OSError('broken pipe')

            def flush(self):
                raise OSError('broken pipe')

        with mock.patch.object(set_terminal_title.sys, 'stdout', _RaisingStdout()):
            # Must not raise.
            set_terminal_title._emit_terminal_sequence('anything')

    def test_hook_path_emits_terminal_sequence_json_running(self):
        """End-to-end via main(): a hook invocation with running status
        produces ``{"terminalSequence": ...}`` JSON on stdout and exits 0.
        """
        fake_stdout = io.StringIO()
        env = {k: v for k, v in os.environ.items() if k != 'PLAN_ID'}
        with (
            mock.patch.object(set_terminal_title.sys, 'stdout', fake_stdout),
            mock.patch.object(set_terminal_title.sys, 'stdin', io.StringIO('')),
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.object(set_terminal_title, '_resolve_plan_id', return_value=None),
        ):
            exit_code = set_terminal_title.main(['running'])

        self.assertEqual(exit_code, 0)
        payload = json.loads(fake_stdout.getvalue())
        self.assertIn('terminalSequence', payload)
        self.assertEqual(payload['terminalSequence'], '\x1b]0;▶ claude\x07')

    def test_hook_path_emits_terminal_sequence_json_idle(self):
        """Same shape with idle status — the Notification/Stop hooks fire
        this path and produce JSON on stdout."""
        fake_stdout = io.StringIO()
        env = {k: v for k, v in os.environ.items() if k != 'PLAN_ID'}
        with (
            mock.patch.object(set_terminal_title.sys, 'stdout', fake_stdout),
            mock.patch.object(set_terminal_title.sys, 'stdin', io.StringIO('')),
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.object(set_terminal_title, '_resolve_plan_id', return_value=None),
        ):
            exit_code = set_terminal_title.main(['idle'])

        self.assertEqual(exit_code, 0)
        payload = json.loads(fake_stdout.getvalue())
        self.assertIn('terminalSequence', payload)
        self.assertEqual(payload['terminalSequence'], '\x1b]0;◯ claude\x07')


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
        self.assertEqual(result.stdout.strip(), '◯ claude')

    def test_statusline_reads_stdin_cwd(self):
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / PLAN_ID
        _write_status(plan_dir, '5-execute')
        # Drive plan-id resolution via the hook's cwd payload: the worktree
        # path encodes the plan id and walk-up finds the status.json under
        # the temp_dir .plan/local/plans/{plan_id}/ directory.
        worktree_cwd = self.temp_dir / '.plan' / 'local' / 'worktrees' / PLAN_ID
        worktree_cwd.mkdir(parents=True)
        payload = json.dumps({'cwd': str(worktree_cwd)})

        env_overrides = {'PLAN_ID': ''}
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
        self.assertIn('pm:', result.stdout)
        self.assertTrue(result.stdout.startswith('▶ '))

    def test_exit_zero_when_no_plan_context(self):
        # Cwd is outside any worktree → no plan-id resolved → script must
        # still exit 0 with the fallback title.
        env_overrides = {'PLAN_ID': ''}
        result = run_script(
            SCRIPT_PATH,
            '--statusline',
            'waiting',
            input_data='',
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), '? claude')

    def test_inherited_plan_id_env_var_does_not_render_plan_title(self):
        """Cross-tab isolation regression at the CLI level.

        Tab #3 starts with an inherited $PLAN_ID=tab-1-plan from the parent
        shell. Its cwd is the repo root (not inside any worktree). Even with
        a matching status.json on disk, the statusline must render the
        fallback — $PLAN_ID is no longer a resolution input.
        """
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / 'tab-1-plan'
        _write_status(plan_dir, '5-execute', short_description='Other_tabs_plan')
        env_overrides = {'PLAN_ID': 'tab-1-plan'}
        result = run_script(
            SCRIPT_PATH,
            '--statusline',
            'idle',
            input_data='',
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), '◯ claude')


class TestHookPayloadParsing(ScriptTestCase):
    """_read_hook_payload extracts cwd, prompt, and session_id from stdin."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_returns_all_fields_when_present(self):
        payload = json.dumps(
            {
                'cwd': '/tmp/repo',
                'prompt': '/plan-marshall list',
                'session_id': 'abc-123',
            }
        )
        with mock.patch.object(set_terminal_title.sys, 'stdin', io.StringIO(payload)):
            result = set_terminal_title._read_hook_payload()
        self.assertEqual(result['cwd'], '/tmp/repo')
        self.assertEqual(result['prompt'], '/plan-marshall list')
        self.assertEqual(result['session_id'], 'abc-123')

    def test_returns_none_values_for_empty_stdin(self):
        with mock.patch.object(set_terminal_title.sys, 'stdin', io.StringIO('')):
            result = set_terminal_title._read_hook_payload()
        self.assertIsNone(result['cwd'])
        self.assertIsNone(result['prompt'])
        self.assertIsNone(result['session_id'])

    def test_returns_none_values_for_malformed_json(self):
        with mock.patch.object(set_terminal_title.sys, 'stdin', io.StringIO('{not-json')):
            result = set_terminal_title._read_hook_payload()
        self.assertEqual(result, {'cwd': None, 'prompt': None, 'session_id': None})

    def test_returns_none_for_non_dict_payload(self):
        with mock.patch.object(set_terminal_title.sys, 'stdin', io.StringIO('[1,2,3]')):
            result = set_terminal_title._read_hook_payload()
        self.assertEqual(result, {'cwd': None, 'prompt': None, 'session_id': None})

    def test_rejects_non_string_prompt(self):
        payload = json.dumps({'cwd': '/r', 'prompt': 42, 'session_id': 's'})
        with mock.patch.object(set_terminal_title.sys, 'stdin', io.StringIO(payload)):
            result = set_terminal_title._read_hook_payload()
        self.assertIsNone(result['prompt'])
        self.assertEqual(result['cwd'], '/r')
        self.assertEqual(result['session_id'], 's')


class TestCommandTokenExtraction(ScriptTestCase):
    """_extract_command_token parses leading /command from prompt text."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_simple_command(self):
        self.assertEqual(set_terminal_title._extract_command_token('/plan-marshall'), 'plan-marshall')

    def test_command_with_args(self):
        self.assertEqual(
            set_terminal_title._extract_command_token('/plan-marshall action=execute plan=foo'),
            'plan-marshall',
        )

    def test_namespaced_command(self):
        self.assertEqual(
            set_terminal_title._extract_command_token('/plan-marshall:plan-marshall'),
            'plan-marshall:plan-marshall',
        )

    def test_leading_whitespace_stripped(self):
        self.assertEqual(set_terminal_title._extract_command_token('   /sync-plugin-cache'), 'sync-plugin-cache')

    def test_no_slash_returns_none(self):
        self.assertIsNone(set_terminal_title._extract_command_token('just some text'))

    def test_empty_string_returns_none(self):
        self.assertIsNone(set_terminal_title._extract_command_token(''))

    def test_only_slash_returns_none(self):
        self.assertIsNone(set_terminal_title._extract_command_token('/'))

    def test_non_string_returns_none(self):
        self.assertIsNone(set_terminal_title._extract_command_token(None))  # type: ignore[arg-type]
        self.assertIsNone(set_terminal_title._extract_command_token(42))  # type: ignore[arg-type]

    def test_too_long_returns_none(self):
        self.assertIsNone(set_terminal_title._extract_command_token('/' + 'a' * 100))


class TestActiveCommandState(ScriptTestCase):
    """Round-trip for _command_state_path, _write_active_command, _read_active_command, _clear."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_roundtrip_write_read_clear(self):
        with mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False):
            set_terminal_title._write_active_command('sess-1', 'plan-marshall')
            self.assertEqual(set_terminal_title._read_active_command('sess-1'), 'plan-marshall')
            set_terminal_title._clear_active_command('sess-1')
            self.assertIsNone(set_terminal_title._read_active_command('sess-1'))

    def test_read_returns_none_when_missing(self):
        with mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False):
            self.assertIsNone(set_terminal_title._read_active_command('never-wrote'))

    def test_read_returns_none_for_empty_session(self):
        self.assertIsNone(set_terminal_title._read_active_command(None))
        self.assertIsNone(set_terminal_title._read_active_command(''))

    def test_path_rejects_traversal(self):
        self.assertIsNone(set_terminal_title._command_state_path('../evil'))
        self.assertIsNone(set_terminal_title._command_state_path('a/b'))
        self.assertIsNone(set_terminal_title._command_state_path('..'))
        self.assertIsNone(set_terminal_title._command_state_path(''))

    def test_sessions_are_isolated(self):
        with mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False):
            set_terminal_title._write_active_command('sess-a', 'cmd-a')
            set_terminal_title._write_active_command('sess-b', 'cmd-b')
            self.assertEqual(set_terminal_title._read_active_command('sess-a'), 'cmd-a')
            self.assertEqual(set_terminal_title._read_active_command('sess-b'), 'cmd-b')
            set_terminal_title._clear_active_command('sess-a')
            self.assertIsNone(set_terminal_title._read_active_command('sess-a'))
            # sess-b unaffected
            self.assertEqual(set_terminal_title._read_active_command('sess-b'), 'cmd-b')

    def test_read_rejects_oversized_state_file(self):
        with mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False):
            path = set_terminal_title._command_state_path('sess-big')
            assert path is not None
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('a' * 200, encoding='utf-8')
            self.assertIsNone(set_terminal_title._read_active_command('sess-big'))

    def test_clear_is_idempotent(self):
        # Clearing a never-written session must not raise even when the per-session
        # parent directory does not exist.
        with mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False):
            set_terminal_title._clear_active_command('phantom-sess')

    def test_clear_removes_empty_parent_directory(self):
        with mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False):
            set_terminal_title._write_active_command('sess-empty', 'cmd')
            path = set_terminal_title._command_state_path('sess-empty')
            assert path is not None
            self.assertTrue(path.exists())
            self.assertTrue(path.parent.exists())

            set_terminal_title._clear_active_command('sess-empty')

            self.assertFalse(path.exists())
            self.assertFalse(path.parent.exists())

    def test_clear_preserves_non_empty_parent_directory(self):
        # If something else (future state file, debug artifact) lives alongside
        # active-command, rmdir must silently fail and leave the sibling intact.
        with mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False):
            set_terminal_title._write_active_command('sess-shared', 'cmd')
            path = set_terminal_title._command_state_path('sess-shared')
            assert path is not None
            sibling = path.parent / 'other-state'
            sibling.write_text('x', encoding='utf-8')

            set_terminal_title._clear_active_command('sess-shared')

            self.assertFalse(path.exists())
            self.assertTrue(path.parent.exists())
            self.assertTrue(sibling.exists())

    def test_read_aliases_plan_marshall_namespaced_token_to_pm(self):
        """Captured verbose token `plan-marshall:plan-marshall` renders as `pm`."""
        with mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False):
            set_terminal_title._write_active_command('sess-alias', 'plan-marshall:plan-marshall')
            self.assertEqual(set_terminal_title._read_active_command('sess-alias'), 'pm')

    def test_read_passes_unaliased_tokens_through_unchanged(self):
        """Tokens without an alias entry are returned verbatim."""
        with mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False):
            set_terminal_title._write_active_command('sess-plain', 'sync-plugin-cache')
            self.assertEqual(set_terminal_title._read_active_command('sess-plain'), 'sync-plugin-cache')


class TestBuildTitlePrecedence(ScriptTestCase):
    """Precedence: plan+phase > active_command > claude."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_plan_phase_wins_over_command(self):
        title = set_terminal_title._build_title('running', 'my-plan', '5-execute', 'plan-marshall')
        self.assertEqual(title, '▶ pm:5-execute')

    def test_command_when_no_plan(self):
        title = set_terminal_title._build_title('running', None, None, 'plan-marshall')
        self.assertEqual(title, '▶ plan-marshall')

    def test_command_fallback_with_waiting_icon(self):
        title = set_terminal_title._build_title('waiting', None, None, 'marshall-steward')
        self.assertTrue(title.startswith('? '))
        self.assertTrue(title.endswith(' marshall-steward'))

    def test_falls_back_to_claude_when_no_command_or_plan(self):
        self.assertEqual(set_terminal_title._build_title('idle', None, None, None), '◯ claude')

    def test_empty_command_falls_through_to_claude(self):
        self.assertEqual(set_terminal_title._build_title('idle', None, None, ''), '◯ claude')


class TestBuildTitleWithSession(ScriptTestCase):
    """build_title end-to-end with session-scoped active command."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_uses_active_command_when_no_plan(self):
        with mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False):
            set_terminal_title._write_active_command('sess-1', 'plan-marshall')
            env = {k: v for k, v in os.environ.items() if k != 'PLAN_ID'}
            env['HOME'] = str(self.temp_dir)
            with mock.patch.dict(os.environ, env, clear=True):
                title = set_terminal_title.build_title('running', str(self.temp_dir), 'sess-1')
        self.assertEqual(title, '▶ plan-marshall')

    def test_plan_phase_beats_active_command(self):
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / PLAN_ID
        _write_status(plan_dir, '3-outline')
        worktree_cwd = self.temp_dir / '.plan' / 'local' / 'worktrees' / PLAN_ID
        worktree_cwd.mkdir(parents=True)
        with mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False):
            set_terminal_title._write_active_command('sess-1', 'plan-marshall')
        with (
            mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None),
            mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False),
        ):
            title = set_terminal_title.build_title('running', str(worktree_cwd), 'sess-1')
        self.assertEqual(title, '▶ pm:3-outline')

    def test_falls_back_to_claude_when_no_session_nor_plan(self):
        env = {k: v for k, v in os.environ.items() if k != 'PLAN_ID'}
        with mock.patch.dict(os.environ, env, clear=True):
            title = set_terminal_title.build_title('idle', str(self.temp_dir), None)
        self.assertEqual(title, '◯ claude')


class TestCliCommandCapture(ScriptTestCase):
    """Subprocess integration: UserPromptSubmit captures command, Stop clears, statusLine reads."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_active_command_alias_pm(self):
        """A UserPromptSubmit carrying `/plan-marshall:plan-marshall foo` renders
        the active-command segment of the title as `pm`, not the verbose token."""
        submit_payload = json.dumps(
            {
                'cwd': str(self.temp_dir),
                'prompt': '/plan-marshall:plan-marshall foo',
                'session_id': 'sess-alias-cli',
            }
        )
        env_overrides = {'PLAN_ID': '', 'HOME': str(self.temp_dir)}
        result = run_script(
            SCRIPT_PATH,
            'running',
            input_data=submit_payload,
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)

        status_payload = json.dumps({'cwd': str(self.temp_dir), 'session_id': 'sess-alias-cli'})
        result = run_script(
            SCRIPT_PATH,
            '--statusline',
            'idle',
            input_data=status_payload,
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), '◯ pm')

    def test_active_command_no_alias_passthrough(self):
        """A prompt starting with `/sync-plugin-cache` — a token with no alias —
        renders verbatim in the statusline."""
        submit_payload = json.dumps(
            {
                'cwd': str(self.temp_dir),
                'prompt': '/sync-plugin-cache',
                'session_id': 'sess-plain-cli',
            }
        )
        env_overrides = {'PLAN_ID': '', 'HOME': str(self.temp_dir)}
        result = run_script(
            SCRIPT_PATH,
            'running',
            input_data=submit_payload,
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)

        status_payload = json.dumps({'cwd': str(self.temp_dir), 'session_id': 'sess-plain-cli'})
        result = run_script(
            SCRIPT_PATH,
            '--statusline',
            'idle',
            input_data=status_payload,
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), '◯ sync-plugin-cache')

    def test_running_captures_command_and_statusline_reads_it(self):
        # 1. Simulate UserPromptSubmit hook: status=running, prompt=/plan-marshall, session_id=s1
        submit_payload = json.dumps(
            {
                'cwd': str(self.temp_dir),
                'prompt': '/plan-marshall action=list',
                'session_id': 's1',
            }
        )
        env_overrides = {'PLAN_ID': '', 'HOME': str(self.temp_dir)}
        result = run_script(
            SCRIPT_PATH,
            'running',
            input_data=submit_payload,
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)

        # 2. Simulate statusLine query: status=idle, same session
        status_payload = json.dumps({'cwd': str(self.temp_dir), 'session_id': 's1'})
        result = run_script(
            SCRIPT_PATH,
            '--statusline',
            'idle',
            input_data=status_payload,
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), '◯ plan-marshall')

        # 3. Simulate Stop hook: clears state
        result = run_script(
            SCRIPT_PATH,
            'idle',
            input_data=status_payload,
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)

        # 4. statusLine now returns plain `claude`
        result = run_script(
            SCRIPT_PATH,
            '--statusline',
            'idle',
            input_data=status_payload,
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), '◯ claude')

    def test_running_without_slash_prompt_does_not_create_state(self):
        payload = json.dumps(
            {
                'cwd': str(self.temp_dir),
                'prompt': 'just a normal user message',
                'session_id': 's2',
            }
        )
        env_overrides = {'PLAN_ID': '', 'HOME': str(self.temp_dir)}
        result = run_script(
            SCRIPT_PATH,
            'running',
            input_data=payload,
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)

        # statusLine still returns `claude`, not the message text
        status_payload = json.dumps({'cwd': str(self.temp_dir), 'session_id': 's2'})
        result = run_script(
            SCRIPT_PATH,
            '--statusline',
            'idle',
            input_data=status_payload,
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), '◯ claude')


class TestPlanLabelSanitize(ScriptTestCase):
    """_sanitize_plan_label: length, control chars, whitespace handling."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_accepts_typical_short_description(self):
        self.assertEqual(
            set_terminal_title._sanitize_plan_label('Refactor_title_handling'),
            'Refactor_title_handling',
        )

    def test_strips_surrounding_whitespace(self):
        self.assertEqual(
            set_terminal_title._sanitize_plan_label('  padded  '),
            'padded',
        )

    def test_none_and_empty_return_none(self):
        self.assertIsNone(set_terminal_title._sanitize_plan_label(None))
        self.assertIsNone(set_terminal_title._sanitize_plan_label(''))
        self.assertIsNone(set_terminal_title._sanitize_plan_label('   '))

    def test_rejects_oversized_label(self):
        self.assertIsNone(set_terminal_title._sanitize_plan_label('x' * 100))

    def test_rejects_control_characters(self):
        self.assertIsNone(set_terminal_title._sanitize_plan_label('bad\x00label'))
        self.assertIsNone(set_terminal_title._sanitize_plan_label('bad\nlabel'))
        self.assertIsNone(set_terminal_title._sanitize_plan_label('bad\x07label'))

    def test_allows_ellipsis_tail(self):
        # short_description truncation can leave a unicode ellipsis at the end.
        self.assertEqual(
            set_terminal_title._sanitize_plan_label('truncated_label…'),
            'truncated_label…',
        )


class TestBuildTitleDoneEmission(ScriptTestCase):
    """Terminal 'done' emission with --plan-label bypasses resolution chain."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_done_with_plan_label_bypasses_resolution(self):
        title = set_terminal_title._build_title(
            'done',
            None,
            None,
            None,
            None,
            plan_label='Refactor_title_handling',
        )
        self.assertEqual(title, '✓ pm:done:Refactor_title_handling')

    def test_plan_label_ignored_on_running_status(self):
        # Only 'done' honours --plan-label; other statuses fall through to the
        # normal resolution chain (empty here → claude fallback).
        title = set_terminal_title._build_title(
            'running',
            None,
            None,
            None,
            None,
            plan_label='ignored',
        )
        self.assertEqual(title, '▶ claude')

    def test_done_without_plan_label_falls_back_to_resolution(self):
        # No explicit label → normal chain; with no plan context this lands on claude.
        title = set_terminal_title._build_title('done', None, None, None, None)
        self.assertEqual(title, '✓ claude')

    def test_build_title_wrapper_shortcircuits_on_done_label(self):
        # Even with a resolvable plan via worktree-cwd + status.json,
        # done+label short-circuits so the caller's label wins over any
        # ambient resolution.
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / PLAN_ID
        _write_status(plan_dir, '6-finalize', short_description='Old_derived')
        worktree_cwd = self.temp_dir / '.plan' / 'local' / 'worktrees' / PLAN_ID
        worktree_cwd.mkdir(parents=True)
        with mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None):
            title = set_terminal_title.build_title(
                'done',
                str(worktree_cwd),
                plan_label='Explicit_label',
            )
        self.assertEqual(title, '✓ pm:done:Explicit_label')

    def test_cli_done_with_plan_label_statusline(self):
        # Subprocess path: --plan-label is wired through argparse → build_title.
        env_overrides = {'PLAN_ID': '', 'HOME': str(self.temp_dir)}
        result = run_script(
            SCRIPT_PATH,
            '--statusline',
            'done',
            '--plan-label',
            'Wired_through_cli',
            input_data='',
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), '✓ pm:done:Wired_through_cli')

    def test_cli_done_with_malformed_plan_label_falls_back(self):
        # A control character in the label is rejected → normal resolution →
        # fallback to claude (no plan context here).
        env_overrides = {'PLAN_ID': '', 'HOME': str(self.temp_dir)}
        result = run_script(
            SCRIPT_PATH,
            '--statusline',
            'done',
            '--plan-label',
            'bad\x07label',
            input_data='',
            cwd=str(self.temp_dir),
            env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), '✓ claude')
