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

from _fixtures import setup_archived_plan, setup_live_plan  # noqa: E402

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

_LOG_HEADER_TS = '[2026-05-26T10:00:00Z]'


def _line(ts_suffix: str, notation: str, sub: str, exit_code: int) -> str:
    """Produce a script-execution.log header matching production shape."""
    return (
        f'[2026-05-26T10:00:{ts_suffix}Z] [INFO] [abc123] '
        f'{notation} {sub} (0.12s) exit_code={exit_code}'
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
        lines = [
            _line('01', 'plan-marshall:manage-files:manage-files', 'read', 0),
            _line('02', 'plan-marshall:manage-tasks:manage-tasks', 'list', 0),
        ]
        assert _mod.parse_failures(lines) == []

    def test_captures_failure_with_stderr_block(self):
        lines = [
            _line('01', 'plan-marshall:manage-tasks:manage-tasks', 'invalid-sub', 2),
            "    argparse: invalid choice: 'invalid-sub' (choose from 'add', 'read')",
            _line('05', 'plan-marshall:manage-files:manage-files', 'read', 0),
        ]
        failures = _mod.parse_failures(lines)
        assert len(failures) == 1
        f = failures[0]
        assert f['notation'] == 'plan-marshall:manage-tasks:manage-tasks'
        assert f['subcommand'] == 'invalid-sub'
        assert f['exit_code'] == 2
        assert 'invalid choice' in f['stderr']


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
            _line('01', 'plan-marshall:manage-tasks:manage-tasks', 'nuke', 2) + '\n'
            + "    argparse: invalid choice: 'nuke' (choose from 'add', 'read', 'list')\n"
            + _line('05', 'plan-marshall:manage-files:manage-files', 'read', 0) + '\n'
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
            _line('01', 'plan-marshall:manage-tasks:manage-tasks', 'nuke', 2) + '\n'
            + "    argparse: error: invalid choice: 'nuke'\n"
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
