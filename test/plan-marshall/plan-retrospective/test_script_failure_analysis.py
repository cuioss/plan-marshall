"""Tests for ``script-failure-analysis.py``.

The script classifies non-zero-exit script calls in
``script-execution.log`` by stderr signature (invented_subcommand,
missing_required_flag, invented_flag, script_internal_error) and emits a
deduped TOON fragment for the retrospective compile-report consumer.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _fixtures import (  # noqa: E402
    setup_archived_plan,
    setup_live_plan,
    write_captured_real_log,
)

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'scripts'
    / 'script-failure-analysis.py'
)

# Direct module load so unit tests can poke the pure helpers.
_spec = importlib.util.spec_from_file_location('script_failure_analysis', str(SCRIPT_PATH))
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


# ---------------------------------------------------------------------------
# Fixture log builders
# ---------------------------------------------------------------------------

def _header(ts_suffix: str, notation: str, sub: str, level: str = 'INFO') -> str:
    """Produce a script-execution.log header line matching production shape.

    Per ``manage-logging/standards/log-format.md`` the header carries NO
    inline ``exit_code`` token — the exit code lives on a two-space-indented
    continuation line for error entries.
    """
    return f'[2026-05-26T10:00:{ts_suffix}Z] [{level}] [abc123] {notation} {sub} (0.12s)'


def _success(ts_suffix: str, notation: str, sub: str) -> str:
    """A successful (exit-zero) call: a bare header with no continuation block."""
    return _header(ts_suffix, notation, sub)


def _failure(ts_suffix: str, notation: str, sub: str, exit_code: int, stderr: str) -> str:
    """A failed call: header plus a two-space-indented continuation block.

    Matches the documented Error Entry shape (``exit_code: N`` colon + space,
    ``args:``, ``stderr:`` continuation fields).
    """
    return (
        f'{_header(ts_suffix, notation, sub, level="ERROR")}\n'
        f'  exit_code: {exit_code}\n'
        f'  args: {sub}\n'
        f'  stderr: {stderr}'
    )


def _write_log(plan_dir: Path, content: str) -> None:
    logs_dir = plan_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / 'script-execution.log').write_text(content, encoding='utf-8')


# ---------------------------------------------------------------------------
# Unit tests (pure helpers)
# ---------------------------------------------------------------------------


class TestClassifyFailure:
    def test_invented_subcommand_signature(self):
        f = {'exit_code': 2, 'stderr': "argparse: invalid choice: 'nuke' (choose from 'add', 'read')"}
        assert _mod.classify_failure(f) == ('anti-pattern', 'invented_subcommand')

    def test_missing_required_flag_signature(self):
        f = {'exit_code': 2, 'stderr': 'usage: foo\nfoo: error: the following arguments are required: --plan-id'}
        assert _mod.classify_failure(f) == ('anti-pattern', 'missing_required_flag')

    def test_invented_flag_signature(self):
        f = {'exit_code': 2, 'stderr': 'foo: error: unrecognized arguments: --made-up-flag'}
        assert _mod.classify_failure(f) == ('anti-pattern', 'invented_flag')

    def test_argparse_other_falls_through(self):
        f = {'exit_code': 2, 'stderr': 'something weird argparse said'}
        assert _mod.classify_failure(f) == ('anti-pattern', 'argparse_other')

    def test_script_internal_error_on_exit_one(self):
        f = {'exit_code': 1, 'stderr': 'Traceback (most recent call last)'}
        assert _mod.classify_failure(f) == ('bug', 'script_internal_error')


class TestParseFailures:
    def test_skips_successful_calls(self):
        lines = (
            _success('01', 'plan-marshall:manage-files:manage-files', 'read') + '\n'
            + _success('02', 'plan-marshall:manage-tasks:manage-tasks', 'list')
        ).splitlines()
        assert _mod.parse_failures(lines) == []

    def test_captures_failure_with_stderr_block(self):
        lines = (
            _failure(
                '01', 'plan-marshall:manage-tasks:manage-tasks', 'invalid-sub', 2,
                "argparse: invalid choice: 'invalid-sub' (choose from 'add', 'read')",
            ) + '\n'
            + _success('05', 'plan-marshall:manage-files:manage-files', 'read')
        ).splitlines()
        failures = _mod.parse_failures(lines)
        assert len(failures) == 1
        f = failures[0]
        assert f['notation'] == 'plan-marshall:manage-tasks:manage-tasks'
        assert f['subcommand'] == 'invalid-sub'
        assert f['exit_code'] == 2
        assert 'invalid choice' in f['stderr']

    def test_skips_header_with_zero_exit_code_continuation(self):
        # A header whose continuation block reports exit_code 0 is a success.
        lines = (
            _failure(
                '01', 'plan-marshall:manage-files:manage-files', 'read', 0, 'ignored',
            )
        ).splitlines()
        assert _mod.parse_failures(lines) == []

    def test_captures_multiline_stderr_blob(self):
        # stderr that wraps across continuation lines is accumulated.
        lines = [
            _header('01', 'plan-marshall:manage-tasks:manage-tasks', 'add', level='ERROR'),
            '  exit_code: 2',
            '  args: add --plan-id x',
            '  stderr: usage: manage-tasks add',
            'manage-tasks: error: the following arguments are required: --title',
        ]
        failures = _mod.parse_failures(lines)
        assert len(failures) == 1
        assert failures[0]['exit_code'] == 2
        assert 'the following arguments are required' in failures[0]['stderr']


class TestDedupeFindings:
    def test_collapses_recurring_same_subtype(self):
        failures = [
            {
                'notation': 'plan-marshall:manage-tasks:manage-tasks',
                'exit_code': 2,
                'stderr': "invalid choice: 'foo'",
                'timestamp': 't1',
                'subcommand': 'foo',
            },
            {
                'notation': 'plan-marshall:manage-tasks:manage-tasks',
                'exit_code': 2,
                'stderr': "invalid choice: 'bar'",
                'timestamp': 't2',
                'subcommand': 'bar',
            },
        ]
        findings = _mod.dedupe_findings(failures)
        assert len(findings) == 1
        assert findings[0]['occurrence_count'] == 2
        assert findings[0]['subtype'] == 'invented_subcommand'

    def test_distinct_subtypes_kept_separate(self):
        failures = [
            {
                'notation': 'plan-marshall:manage-tasks:manage-tasks',
                'exit_code': 2,
                'stderr': "invalid choice: 'foo'",
                'timestamp': 't1',
                'subcommand': 'foo',
            },
            {
                'notation': 'plan-marshall:manage-tasks:manage-tasks',
                'exit_code': 2,
                'stderr': 'unrecognized arguments: --nope',
                'timestamp': 't2',
                'subcommand': 'add',
            },
        ]
        findings = _mod.dedupe_findings(failures)
        assert len(findings) == 2
        subtypes = {f['subtype'] for f in findings}
        assert subtypes == {'invented_subcommand', 'invented_flag'}


class TestBuildSeedLessons:
    def test_one_seed_per_finding_with_titles(self):
        findings = [
            {
                'type': 'anti-pattern',
                'subtype': 'invented_subcommand',
                'component': 'plan-marshall:manage-tasks:manage-tasks',
                'occurrence_count': 3,
            },
            {
                'type': 'bug',
                'subtype': 'script_internal_error',
                'component': 'plan-marshall:manage-files:manage-files',
                'occurrence_count': 1,
            },
        ]
        seeds = _mod.build_seed_lessons(findings)
        assert len(seeds) == 2
        titles = {s['title'] for s in seeds}
        assert any('Invented subcommand drift' in t for t in titles)
        assert any('Script-internal error' in t for t in titles)


# ---------------------------------------------------------------------------
# Integration tests (subprocess + fixture)
# ---------------------------------------------------------------------------


class TestCmdRunLiveMode:
    def test_emits_finding_for_invented_subcommand_pattern(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-script-fail')
        log = (
            _failure(
                '01', 'plan-marshall:manage-tasks:manage-tasks', 'nuke', 2,
                "argparse: invalid choice: 'nuke' (choose from 'add', 'read', 'list')",
            ) + '\n'
            + _success('05', 'plan-marshall:manage-files:manage-files', 'read') + '\n'
        )
        _write_log(plan_dir, log)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert data['aspect'] == 'script-failure-analysis'
        assert int(data['total_failures']) == 1
        assert int(data['unique_failures']) == 1
        findings = data['findings']
        assert findings[0]['subtype'] == 'invented_subcommand'
        assert findings[0]['component'] == 'plan-marshall:manage-tasks:manage-tasks'
        lessons = data['lessons']
        assert len(lessons) == 1
        assert lessons[0]['category'] == 'anti-pattern'

    def test_zero_failures_when_log_is_empty(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-no-fail')
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['total_failures']) == 0
        assert int(data['unique_failures']) == 0

    def test_missing_log_file_returns_zero(self, tmp_path, monkeypatch):
        # setup_broken_plan creates a plan with no logs/ dir at all — the
        # script must not crash and must emit zero counts.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-no-log')
        # Wipe the logs dir to simulate the absent-log case.
        log_path = plan_dir / 'logs' / 'script-execution.log'
        if log_path.exists():
            log_path.unlink()
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['total_failures']) == 0


class TestCmdRunArchivedMode:
    def test_archived_plan_path_reads_logs(self, tmp_path):
        archived = setup_archived_plan(tmp_path)
        log = (
            _failure(
                '01', 'plan-marshall:manage-tasks:manage-tasks', 'nuke', 2,
                "argparse: error: invalid choice: 'nuke'",
            ) + '\n'
        )
        _write_log(archived, log)
        result = run_script(
            SCRIPT_PATH, 'run',
            '--archived-plan-path', str(archived),
            '--mode', 'archived',
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['aspect'] == 'script-failure-analysis'
        assert int(data['total_failures']) == 1


class TestRegressionRealLogShape:
    """Regression guard: the pre-fix parser required an inline ``exit_code=`` token and silently dropped real continuation-line failures.

    Replays a frozen, verbatim-shape excerpt of a production
    ``script-execution.log`` (see ``_fixtures.write_captured_real_log``) through
    the aspect. Under the documented Error Entry format the exit code lives ONLY
    on a two-space-indented continuation line; the pre-fix parser required an
    inline ``exit_code=N`` token on the header and therefore dropped every
    failure, reporting ``total_failures: 0``. This test asserts the corrected
    continuation-line parser surfaces the real rejections — it FAILS if the
    parser ever reverts to the inline coupling.
    """

    def test_captured_real_log_surfaces_argparse_rejections(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-real-log')
        write_captured_real_log(plan_dir)

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        # The captured log carries three continuation-block failures; the
        # pre-fix inline-exit_code= parser would report zero.
        assert int(data['total_failures']) > 0, (
            'parser regressed to inline exit_code= coupling — real-shape '
            'continuation-line failures were dropped'
        )
        assert int(data['unique_failures']) > 0

        findings = data['findings']
        subtypes = {f['subtype'] for f in findings}
        assert 'invented_subcommand' in subtypes, (
            "captured 'invalid choice:' rejection not classified as "
            'invented_subcommand'
        )

    def test_captured_real_log_emits_seed_lessons(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-real-log-seed')
        write_captured_real_log(plan_dir)

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        lessons = data['lessons']
        assert len(lessons) > 0
        assert any(lesson['category'] == 'anti-pattern' for lesson in lessons)
