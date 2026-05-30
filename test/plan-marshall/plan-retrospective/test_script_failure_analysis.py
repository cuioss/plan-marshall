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


def _work_failure(ts_suffix: str, notation: str, exit_code: int, failure_kind: str, stderr: str) -> str:
    """Produce a work.log executor-failure line matching production shape.

    The executor mirrors every non-zero-exit call into the work log as a single
    physical line: ``[ts] [LEVEL] [hash] [ERROR] (...:execute-script:N)
    script_failure notation=... exit_code=N failure_kind=... stderr=...``.
    """
    return (
        f'[2026-05-26T11:00:{ts_suffix}Z] [ERROR] [wlog{ts_suffix}] '
        f'[ERROR] (plan-marshall:execute-script:{exit_code}) script_failure '
        f'notation={notation} exit_code={exit_code} failure_kind={failure_kind} '
        f'stderr={stderr}'
    )


def _work_status(ts_suffix: str, msg: str) -> str:
    """A non-failure work.log line (STATUS/ARTIFACT) — must never be parsed as a failure."""
    return f'[2026-05-26T11:00:{ts_suffix}Z] [INFO] [wlog{ts_suffix}] [STATUS] (plan-marshall:phase-5-execute) {msg}'


def _write_work_log(plan_dir: Path, content: str) -> None:
    logs_dir = plan_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / 'work.log').write_text(content, encoding='utf-8')


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
        # stderr that wraps across continuation lines is accumulated. An
        # indented line that looks like a field but is NOT one of the known
        # continuation keys (e.g. ``  details: ...``) must stay part of the
        # stderr blob — _FIELD_RE is restricted to the known keys so it does
        # not prematurely close stderr accumulation.
        lines = [
            _header('01', 'plan-marshall:manage-tasks:manage-tasks', 'add', level='ERROR'),
            '  exit_code: 2',
            '  args: add --plan-id x',
            '  stderr: usage: manage-tasks add',
            'manage-tasks: error: the following arguments are required: --title',
            '  details: some indented error details',
        ]
        failures = _mod.parse_failures(lines)
        assert len(failures) == 1
        assert failures[0]['exit_code'] == 2
        assert 'the following arguments are required' in failures[0]['stderr']
        # The indented field-like line must be captured, not silently dropped.
        assert 'details: some indented error details' in failures[0]['stderr']


class TestParseWorkLogFailures:
    """Unit coverage for the work.log executor-failure parser."""

    def test_captures_argparse_rejection_line(self):
        lines = [
            _work_failure(
                '01', 'plan-marshall:manage-status:manage-status', 2, 'argparse_rejection',
                "manage-status.py: error: unrecognized arguments: --field metadata",
            ),
        ]
        failures = _mod.parse_work_log_failures(lines)
        assert len(failures) == 1
        f = failures[0]
        assert f['notation'] == 'plan-marshall:manage-status:manage-status'
        assert f['exit_code'] == 2
        assert f['subcommand'] is None
        assert 'unrecognized arguments' in f['stderr']

    def test_classifies_via_shared_signatures(self):
        # The work.log-sourced stderr flows through the SAME classifier.
        lines = [
            _work_failure(
                '01', 'plan-marshall:manage-findings:manage-findings', 2, 'argparse_rejection',
                "manage-findings: error: invalid choice: 'query' (choose from 'add', 'list')",
            ),
        ]
        failures = _mod.parse_work_log_failures(lines)
        assert _mod.classify_failure(failures[0]) == ('anti-pattern', 'invented_subcommand')

    def test_ignores_non_failure_lines(self):
        lines = [
            _work_status('01', 'Starting execute phase'),
            _work_status('02', 'Active worktree set'),
        ]
        assert _mod.parse_work_log_failures(lines) == []

    def test_drops_exit_zero_lines(self):
        # An exit_code=0 executor line is an operation failure, never a script
        # failure — it must be dropped even if it carries a script_failure marker.
        lines = [
            _work_failure(
                '01', 'plan-marshall:manage-references:manage-references', 0, 'operation_failure',
                'field_not_found',
            ),
        ]
        assert _mod.parse_work_log_failures(lines) == []

    def test_handles_script_internal_failure_empty_stderr(self):
        lines = [
            _work_failure(
                '01', 'plan-marshall:manage-references:manage-references', 1,
                'script_internal_failure', '',
            ),
        ]
        failures = _mod.parse_work_log_failures(lines)
        assert len(failures) == 1
        assert failures[0]['exit_code'] == 1
        assert _mod.classify_failure(failures[0]) == ('bug', 'script_internal_error')


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


class TestDedupeMirroredFailures:
    """``dedupe_mirrored_failures`` drops work.log entries that mirror an
    script-execution.log entry on ``(notation, timestamp)`` so a single physical
    failure mirrored to both sinks is counted exactly once.
    """

    def test_drops_mirrored_work_failure(self):
        exec_failures = [
            {
                'notation': 'plan-marshall:manage-status:manage-status',
                'timestamp': '2026-05-26T10:00:01Z',
                'exit_code': 2,
                'stderr': 'unrecognized arguments: --field',
            },
        ]
        work_failures = [
            {
                'notation': 'plan-marshall:manage-status:manage-status',
                'timestamp': '2026-05-26T10:00:01Z',
                'exit_code': 2,
                'stderr': 'unrecognized arguments: --field',
            },
        ]
        # The mirrored work.log entry is dropped → empty residual.
        assert _mod.dedupe_mirrored_failures(exec_failures, work_failures) == []

    def test_retains_work_only_failure(self):
        # A work.log failure with no matching script-execution.log entry (the
        # originating-context gap) is retained.
        exec_failures = [
            {
                'notation': 'plan-marshall:manage-files:manage-files',
                'timestamp': '2026-05-26T10:00:01Z',
                'exit_code': 1,
                'stderr': 'boom',
            },
        ]
        work_failures = [
            {
                'notation': 'plan-marshall:manage-status:manage-status',
                'timestamp': '2026-05-26T11:00:30Z',
                'exit_code': 2,
                'stderr': 'unrecognized arguments: --field',
            },
        ]
        residual = _mod.dedupe_mirrored_failures(exec_failures, work_failures)
        assert len(residual) == 1
        assert residual[0]['notation'] == 'plan-marshall:manage-status:manage-status'

    def test_distinguishes_same_notation_different_timestamp(self):
        # Same notation but a DIFFERENT timestamp is a distinct physical event
        # and must be retained.
        exec_failures = [
            {
                'notation': 'plan-marshall:manage-tasks:manage-tasks',
                'timestamp': '2026-05-26T10:00:01Z',
                'exit_code': 2,
                'stderr': "invalid choice: 'foo'",
            },
        ]
        work_failures = [
            {
                'notation': 'plan-marshall:manage-tasks:manage-tasks',
                'timestamp': '2026-05-26T10:00:09Z',
                'exit_code': 2,
                'stderr': "invalid choice: 'bar'",
            },
        ]
        residual = _mod.dedupe_mirrored_failures(exec_failures, work_failures)
        assert len(residual) == 1
        assert residual[0]['timestamp'] == '2026-05-26T10:00:09Z'


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


class TestWorkLogSinkIntegration:
    """End-to-end coverage that ``cmd_run`` scans BOTH sinks and dedupes by (notation, subtype).

    ``setup_live_plan`` writes a happy-path ``work.log`` containing only
    STATUS/ARTIFACT lines (no ``script_failure`` markers), so each test
    overwrites ``work.log`` with the failure shape under test. The
    happy-path ``script-execution.log`` from the fixture carries no
    continuation-block failures, so it contributes zero unless a test also
    overwrites it via ``_write_log``.
    """

    def test_work_log_only_argparse_rejection_surfaces_finding(self, tmp_path, monkeypatch):
        """(a) work.log-only argparse_rejection (no script-execution.log entry) → finding."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-worklog-only')
        # Clean script-execution.log (no failures), failure lives only in work.log.
        _write_log(plan_dir, _success('01', 'plan-marshall:manage-files:manage-files', 'read') + '\n')
        _write_work_log(
            plan_dir,
            _work_failure(
                '30', 'plan-marshall:manage-status:manage-status', 2, 'argparse_rejection',
                "manage-status.py: error: unrecognized arguments: --field metadata",
            ) + '\n',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['total_failures']) == 1
        assert int(data['unique_failures']) == 1
        findings = data['findings']
        assert findings[0]['subtype'] == 'invented_flag'
        assert findings[0]['component'] == 'plan-marshall:manage-status:manage-status'

    def test_same_notation_subtype_in_both_sinks_collapses(self, tmp_path, monkeypatch):
        """(b) same (notation, subtype) in BOTH sinks → exactly one finding."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-both-sinks')
        # script-execution.log: invented_subcommand for manage-tasks.
        _write_log(
            plan_dir,
            _failure(
                '01', 'plan-marshall:manage-tasks:manage-tasks', 'nuke', 2,
                "argparse: invalid choice: 'nuke' (choose from 'add', 'read')",
            ) + '\n',
        )
        # work.log: SAME notation + SAME subtype (invented_subcommand).
        _write_work_log(
            plan_dir,
            _work_failure(
                '30', 'plan-marshall:manage-tasks:manage-tasks', 2, 'argparse_rejection',
                "manage-tasks: error: invalid choice: 'start' (choose from 'add', 'read')",
            ) + '\n',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        # Two raw failures across both sinks, collapsed to one finding.
        assert int(data['total_failures']) == 2
        assert int(data['unique_failures']) == 1
        findings = data['findings']
        assert findings[0]['subtype'] == 'invented_subcommand'
        assert findings[0]['occurrence_count'] == 2

    def test_originating_context_clean_exec_log_many_worklog_clusters(self, tmp_path, monkeypatch):
        """(c) clean script-execution.log + several work.log argparse clusters → non-zero totals."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-origin-ctx')
        # script-execution.log carries only successes.
        _write_log(
            plan_dir,
            _success('01', 'plan-marshall:manage-files:manage-files', 'read') + '\n'
            + _success('02', 'plan-marshall:manage-tasks:manage-tasks', 'list') + '\n',
        )
        # work.log carries three DISTINCT argparse-rejection clusters.
        _write_work_log(
            plan_dir,
            _work_failure(
                '10', 'plan-marshall:manage-status:manage-status', 2, 'argparse_rejection',
                "manage-status.py: error: unrecognized arguments: --field metadata",
            ) + '\n'
            + _work_failure(
                '20', 'plan-marshall:manage-findings:manage-findings', 2, 'argparse_rejection',
                "manage-findings: error: invalid choice: 'query' (choose from 'add', 'list')",
            ) + '\n'
            + _work_failure(
                '30', 'plan-marshall:manage-tasks:manage-tasks', 2, 'argparse_rejection',
                "manage-tasks: error: the following arguments are required: --title",
            ) + '\n',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['total_failures']) == 3
        assert int(data['unique_failures']) == 3
        subtypes = {f['subtype'] for f in data['findings']}
        assert subtypes == {'invented_flag', 'invented_subcommand', 'missing_required_flag'}

    def test_exec_log_only_no_work_log_failures_unchanged(self, tmp_path, monkeypatch):
        """(d) regression: script-execution.log failures, no work.log failures → behaves as before."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-exec-only')
        _write_log(
            plan_dir,
            _failure(
                '01', 'plan-marshall:manage-tasks:manage-tasks', 'nuke', 2,
                "argparse: invalid choice: 'nuke' (choose from 'add', 'read')",
            ) + '\n',
        )
        # work.log retains only the fixture's STATUS/ARTIFACT lines (no failures).
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['total_failures']) == 1
        assert int(data['unique_failures']) == 1
        assert data['findings'][0]['subtype'] == 'invented_subcommand'


class TestExitOneTwoOnlyCriterion:
    """D5: only exit 1 and exit 2 are script failures.

    An exit-0 ``status: error`` operation-failure entry — the common shape AFTER
    the D1 producer fix — must NOT be counted as a script failure in EITHER
    sink. These tests pin that boundary so a future regression that re-counts
    exit-0 entries (or re-introduces a stdout-when-stderr-empty classifier) is
    caught.
    """

    def test_exit_zero_continuation_block_not_counted(self, tmp_path, monkeypatch):
        """A script-execution.log entry whose continuation block reports exit_code 0 is ignored."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-exit0-exec')
        # An exit-0 entry that nonetheless carries a stderr-shaped continuation
        # (simulating a status:error operation failure logged at exit 0).
        _write_log(
            plan_dir,
            _failure(
                '01', 'plan-marshall:manage-references:manage-references', 'get', 0,
                'status: error\nerror: field_not_found',
            ) + '\n',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['total_failures']) == 0
        assert int(data['unique_failures']) == 0

    def test_exit_zero_work_log_line_not_counted(self, tmp_path, monkeypatch):
        """A work.log executor line with exit_code=0 is ignored (operation failure, not a crash)."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-exit0-worklog')
        _write_log(plan_dir, _success('01', 'plan-marshall:manage-files:manage-files', 'read') + '\n')
        _write_work_log(
            plan_dir,
            _work_failure(
                '30', 'plan-marshall:manage-references:manage-references', 0,
                'operation_failure', 'field_not_found',
            ) + '\n',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['total_failures']) == 0
        assert int(data['unique_failures']) == 0

    def test_classify_failure_only_assigns_for_exit_one_and_two(self):
        """classify_failure assigns subtypes only for exit 1 and exit 2."""
        # exit 2 → anti-pattern subtypes
        assert _mod.classify_failure({'exit_code': 2, 'stderr': "invalid choice: 'x'"}) == (
            'anti-pattern', 'invented_subcommand'
        )
        # exit 1 → script_internal_error
        assert _mod.classify_failure({'exit_code': 1, 'stderr': 'boom'}) == (
            'bug', 'script_internal_error'
        )
        # parse layer drops exit 0, so classify is never reached for exit-0
        # entries; the parser-level guard is the authoritative gate.
        assert _mod.parse_failures(
            [
                _header('01', 'plan-marshall:manage-references:manage-references', 'get', level='ERROR'),
                '  exit_code: 0',
                '  stderr: status: error',
            ]
        ) == []
