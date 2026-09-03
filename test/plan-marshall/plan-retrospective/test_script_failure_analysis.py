# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``script-failure-analysis.py``."""


from __future__ import annotations

from _plan_retrospective_fixtures import (
    setup_archived_plan,
    setup_live_plan,
    write_captured_real_log,
)
from _script_failure_analysis_fixtures import (
    SCRIPT_PATH,
    _failure,
    _header,
    _legacy_work_failure,
    _mod,
    _success,
    _work_failure,
    _work_status,
    _write_log,
    _write_work_log,
)

from conftest import run_script


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
    ``script-execution.log`` (see
    ``_plan_retrospective_fixtures.write_captured_real_log``) through
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


class TestUnrecognizedWorkLogLineSignal:
    """``cmd_run`` surfaces "recognised no line shape" distinctly from "no failures".

    Both states used to report ``total_failures: 0`` and were indistinguishable
    at the output boundary — which is how the ``stderr=`` → ``detail=`` producer
    rename survived undetected in this sink.
    """

    def test_clean_work_log_reports_zero_unrecognized(self, tmp_path, monkeypatch):
        """A work.log with no failure markers is a clean zero on BOTH counters."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-clean-worklog')
        _write_log(plan_dir, _success('01', 'plan-marshall:manage-files:manage-files', 'read') + '\n')
        _write_work_log(
            plan_dir,
            _work_status('01', 'Starting execute phase') + '\n'
            + _work_status('02', 'Active worktree set') + '\n',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['total_failures']) == 0
        assert int(data['work_log_unrecognized_lines']) == 0

    def test_retired_shape_reports_unrecognized_alongside_zero_failures(self, tmp_path, monkeypatch):
        """A retired-shape failure line reports zero failures AND a non-zero unmatched count."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-drifted-worklog')
        _write_log(plan_dir, _success('01', 'plan-marshall:manage-files:manage-files', 'read') + '\n')
        _write_work_log(
            plan_dir,
            _legacy_work_failure(
                '30', 'plan-marshall:manage-status:manage-status', 2, 'argparse_rejection',
            ) + '\n',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['total_failures']) == 0
        assert int(data['work_log_unrecognized_lines']) == 1


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
