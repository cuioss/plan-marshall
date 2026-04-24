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
        title = set_terminal_title._build_title(
            'running', 'my-plan', '2-refine', short_description=None
        )
        self.assertEqual(title, '▶ pm:2-refine')

    def test_plan_active_empty_short_description(self):
        """An empty-string short_description is treated as missing (no trailing colon)."""
        title = set_terminal_title._build_title(
            'running', 'my-plan', '2-refine', short_description=''
        )
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
        self.assertEqual(title, '▶ pm:3-outline')

    def test_with_env_plan_and_short_description(self):
        plan_dir = self.temp_dir / '.plan' / 'local' / 'plans' / PLAN_ID
        _write_status(plan_dir, '4-plan', short_description='Refactor_title_handling')
        with mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None), \
             mock.patch.dict(os.environ, {'PLAN_ID': PLAN_ID}, clear=False):
            title = set_terminal_title.build_title('running', str(self.temp_dir))
        self.assertEqual(title, '▶ pm:4-plan:Refactor_title_handling')

    def test_fallback_when_no_plan(self):
        env = {k: v for k, v in os.environ.items() if k != 'PLAN_ID'}
        with mock.patch.dict(os.environ, env, clear=True):
            title = set_terminal_title.build_title('idle', str(self.temp_dir))
        self.assertEqual(title, '◯ claude')

    def test_fallback_when_status_missing(self):
        with mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None), \
             mock.patch.dict(os.environ, {'PLAN_ID': 'absent-plan'}, clear=False):
            title = set_terminal_title.build_title('running', str(self.temp_dir))
        self.assertEqual(title, '▶ claude')


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

    def test_falls_back_to_stdout_when_tty_unavailable(self):
        """When /dev/tty cannot be opened (TTY-less hook subprocess under
        VS Code), _emit_osc must emit the OSC escape to sys.stdout so the
        controlling terminal still sees the title update."""
        fake_stdout = io.StringIO()
        with mock.patch('builtins.open', side_effect=OSError('no tty')), \
             mock.patch.object(set_terminal_title.sys, 'stdout', fake_stdout):
            set_terminal_title._emit_osc('hello')

        captured = fake_stdout.getvalue()
        self.assertIn('\033]0;', captured)
        self.assertIn('\007', captured)
        self.assertIn('hello', captured)


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
        self.assertIn('pm:', result.stdout)
        self.assertTrue(result.stdout.startswith('▶ '))

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


class TestHookPayloadParsing(ScriptTestCase):
    """_read_hook_payload extracts cwd, prompt, and session_id from stdin."""

    bundle = 'plan-marshall'
    skill = 'plan-marshall'
    script = 'set_terminal_title.py'

    def test_returns_all_fields_when_present(self):
        payload = json.dumps({
            'cwd': '/tmp/repo',
            'prompt': '/plan-marshall list',
            'session_id': 'abc-123',
        })
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
        # Clearing a never-written session must not raise.
        with mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False):
            set_terminal_title._clear_active_command('phantom-sess')

    def test_read_aliases_plan_marshall_namespaced_token_to_pm(self):
        """Captured verbose token `plan-marshall:plan-marshall` renders as `pm`."""
        with mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False):
            set_terminal_title._write_active_command('sess-alias', 'plan-marshall:plan-marshall')
            self.assertEqual(
                set_terminal_title._read_active_command('sess-alias'), 'pm'
            )

    def test_read_passes_unaliased_tokens_through_unchanged(self):
        """Tokens without an alias entry are returned verbatim."""
        with mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False):
            set_terminal_title._write_active_command('sess-plain', 'sync-plugin-cache')
            self.assertEqual(
                set_terminal_title._read_active_command('sess-plain'), 'sync-plugin-cache'
            )


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
        with mock.patch.dict(os.environ, {'HOME': str(self.temp_dir)}, clear=False):
            set_terminal_title._write_active_command('sess-1', 'plan-marshall')
        with mock.patch.object(set_terminal_title, '_git_common_dir', return_value=None), \
             mock.patch.dict(os.environ, {'PLAN_ID': PLAN_ID, 'HOME': str(self.temp_dir)}, clear=False):
            title = set_terminal_title.build_title('running', str(self.temp_dir), 'sess-1')
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
        submit_payload = json.dumps({
            'cwd': str(self.temp_dir),
            'prompt': '/plan-marshall:plan-marshall foo',
            'session_id': 'sess-alias-cli',
        })
        env_overrides = {'PLAN_ID': '', 'HOME': str(self.temp_dir)}
        result = run_script(
            SCRIPT_PATH, 'running',
            input_data=submit_payload, cwd=str(self.temp_dir), env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)

        status_payload = json.dumps({'cwd': str(self.temp_dir), 'session_id': 'sess-alias-cli'})
        result = run_script(
            SCRIPT_PATH, '--statusline', 'idle',
            input_data=status_payload, cwd=str(self.temp_dir), env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), '◯ pm')

    def test_active_command_no_alias_passthrough(self):
        """A prompt starting with `/sync-plugin-cache` — a token with no alias —
        renders verbatim in the statusline."""
        submit_payload = json.dumps({
            'cwd': str(self.temp_dir),
            'prompt': '/sync-plugin-cache',
            'session_id': 'sess-plain-cli',
        })
        env_overrides = {'PLAN_ID': '', 'HOME': str(self.temp_dir)}
        result = run_script(
            SCRIPT_PATH, 'running',
            input_data=submit_payload, cwd=str(self.temp_dir), env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)

        status_payload = json.dumps({'cwd': str(self.temp_dir), 'session_id': 'sess-plain-cli'})
        result = run_script(
            SCRIPT_PATH, '--statusline', 'idle',
            input_data=status_payload, cwd=str(self.temp_dir), env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), '◯ sync-plugin-cache')

    def test_running_captures_command_and_statusline_reads_it(self):
        # 1. Simulate UserPromptSubmit hook: status=running, prompt=/plan-marshall, session_id=s1
        submit_payload = json.dumps({
            'cwd': str(self.temp_dir),
            'prompt': '/plan-marshall action=list',
            'session_id': 's1',
        })
        env_overrides = {'PLAN_ID': '', 'HOME': str(self.temp_dir)}
        result = run_script(
            SCRIPT_PATH, 'running',
            input_data=submit_payload, cwd=str(self.temp_dir), env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)

        # 2. Simulate statusLine query: status=idle, same session
        status_payload = json.dumps({'cwd': str(self.temp_dir), 'session_id': 's1'})
        result = run_script(
            SCRIPT_PATH, '--statusline', 'idle',
            input_data=status_payload, cwd=str(self.temp_dir), env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), '◯ plan-marshall')

        # 3. Simulate Stop hook: clears state
        result = run_script(
            SCRIPT_PATH, 'idle',
            input_data=status_payload, cwd=str(self.temp_dir), env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)

        # 4. statusLine now returns plain `claude`
        result = run_script(
            SCRIPT_PATH, '--statusline', 'idle',
            input_data=status_payload, cwd=str(self.temp_dir), env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), '◯ claude')

    def test_running_without_slash_prompt_does_not_create_state(self):
        payload = json.dumps({
            'cwd': str(self.temp_dir),
            'prompt': 'just a normal user message',
            'session_id': 's2',
        })
        env_overrides = {'PLAN_ID': '', 'HOME': str(self.temp_dir)}
        result = run_script(
            SCRIPT_PATH, 'running',
            input_data=payload, cwd=str(self.temp_dir), env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)

        # statusLine still returns `claude`, not the message text
        status_payload = json.dumps({'cwd': str(self.temp_dir), 'session_id': 's2'})
        result = run_script(
            SCRIPT_PATH, '--statusline', 'idle',
            input_data=status_payload, cwd=str(self.temp_dir), env_overrides=env_overrides,
        )
        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), '◯ claude')
