# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for ``analyze-logs.py``.

The sibling ``test_analyze_logs_*.py`` covers the phase-5 fact extractors and the
folded-global-log analyzer directly, but drives the top-level ``cmd_run``
orchestration only through ``run_script`` (subprocess — not counted for
coverage). This module fills the in-process gaps: ``cmd_run`` itself (and its
finding-emitting branches), the dispatch-boundary file parser's malformed/OSError
paths, the duration/percentile/notation extractors' skip branches, and the
``resolve_*`` helpers — each asserted against crafted ``tmp_path`` inputs.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module

_al = load_script_module('plan-marshall', 'plan-retrospective', 'analyze-logs.py', 'al_behavior_mod')


def _run_args(plan_dir: Path) -> Namespace:
    return Namespace(
        command='run',
        plan_id=None,
        archived_plan_path=str(plan_dir),
        mode='archived',
    )


def _line(ts: str, level: str, rest: str) -> str:
    return f'[{ts}] [{level}] [abc123] {rest}'


class TestResolvers:
    def test_resolve_plan_dir_live_requires_plan_id(self):
        with pytest.raises(ValueError, match='--plan-id is required'):
            _al.resolve_plan_dir('live', None, None)

    def test_resolve_plan_dir_archived_requires_path(self):
        with pytest.raises(ValueError, match='--archived-plan-path is required'):
            _al.resolve_plan_dir('archived', None, None)

    def test_resolve_plan_dir_unknown_mode(self):
        with pytest.raises(ValueError, match='Unknown mode'):
            _al.resolve_plan_dir('huh', 'p', None)

    def test_resolve_logs_dir_appends_logs(self, tmp_path):
        result = _al.resolve_logs_dir('archived', None, str(tmp_path))
        assert result == tmp_path / 'logs'


class TestPercentile:
    def test_empty_returns_zero(self):
        assert _al.percentile([], 50.0) == 0.0

    def test_single_value_returned(self):
        assert _al.percentile([42.0], 95.0) == 42.0

    def test_nearest_rank_picks_expected_element(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        assert _al.percentile(values, 0.0) == 10.0
        assert _al.percentile(values, 100.0) == 50.0
        assert _al.percentile(values, 50.0) == 30.0


class TestExtractScriptDurations:
    def test_skips_lines_without_duration(self):
        lines = ['plan-marshall:manage-tasks:manage-tasks add no-duration-here']
        assert _al.extract_script_durations(lines) == []

    def test_skips_lines_without_notation(self):
        lines = ['some prose with a (1.5s) duration but no notation']
        assert _al.extract_script_durations(lines) == []

    def test_parses_notation_and_milliseconds(self):
        lines = ['x plan-marshall:manage-files:manage-files read (2.5s)']
        out = _al.extract_script_durations(lines)
        assert out == [('plan-marshall:manage-files:manage-files', 2500.0)]


class TestTopNAndPhases:
    def test_top_n_returns_most_common(self):
        from collections import Counter

        counter = Counter(['A', 'A', 'B', 'C', 'C', 'C'])
        top = _al.top_n(counter, 2)
        assert top[0] == {'tag': 'C', 'count': 3}
        assert top[1] == {'tag': 'A', 'count': 2}

    def test_extract_phases_sorted_distinct(self):
        lines = [
            'plan-marshall:phase-5-execute did x',
            'plan-marshall:phase-1-init did y',
            'plan-marshall:phase-5-execute again',
        ]
        assert _al.extract_phases(lines) == ['1-init', '5-execute']


class TestParseIsoSeconds:
    def test_valid_timestamp_parses(self):
        assert _al._parse_iso_seconds('2026-04-17T10:00:00Z') is not None

    def test_invalid_timestamp_returns_none(self):
        assert _al._parse_iso_seconds('not-a-timestamp') is None


class TestParseDispatchBoundaryFile:
    def test_missing_file_reports_not_present(self, tmp_path):
        result = _al._parse_dispatch_boundary_file(tmp_path / 'nope.toon')
        assert result['present'] is False
        assert result['rows'] == []

    def test_directory_in_place_of_file_reports_not_present(self, tmp_path):
        # A directory at the artifact path means is_file() is False → not present.
        target = tmp_path / 'boundary'
        target.mkdir()
        result = _al._parse_dispatch_boundary_file(target)
        assert result['present'] is False

    def test_malformed_rows_skipped(self, tmp_path):
        """A LEGACY five-column fixture: short/non-int rows drop, the valid one stays.

        This is the file's coverage of BOTH the ``len(parts) < 5`` legacy floor
        and the appended-cell branch, so it also pins what the surviving legacy
        row says about its four appended columns: they are UNMEASURED (absent),
        not a measured ``0``. Asserting only ``len(rows) == 1`` would stay green
        across that representation change while proving nothing about it.
        """
        artifact = tmp_path / 'b.toon'
        artifact.write_text(
            'plan_id: demo\n'
            'phase: 5-execute\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            'too,few,fields\n'  # wrong field count → skipped
            'ts,unknown,not-an-int,2,1000\n'  # non-int LEGACY column → row skipped
            'ts2,clean_exit_queue_empty,100,2,1000\n',  # valid
            encoding='utf-8',
        )
        result = _al._parse_dispatch_boundary_file(artifact)
        assert result['present'] is True
        assert len(result['rows']) == 1
        assert result['clean_exit_queue_empty_count'] == 1

        # The legacy floor survives AND the surviving row's context-load columns
        # read as unmeasured rather than as measured zeros.
        row = result['rows'][0]
        assert row['total_tokens'] == 100
        for column in (
            'input_tokens',
            'output_tokens',
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ):
            assert column not in row, column
        assert row['unmeasured_columns'] == [
            'input_tokens',
            'output_tokens',
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ]
        # Nothing was UNRECOGNISED: a legacy row is a recognised shape whose
        # appended columns simply do not exist.
        assert row['unrecognised_columns'] == []

    def test_malformed_appended_cell_is_unrecognised_not_unmeasured(self, tmp_path):
        """A corrupt appended cell reads as unrecognised, keeping the row.

        The three-way distinction at its sharpest: a legacy row (nothing there),
        an ``unmeasured`` token (deliberately not measured) and a corrupt cell
        (a shape the reader failed to parse) must not collapse into one bucket.
        """
        artifact = tmp_path / 'b.toon'
        artifact.write_text(
            'plan_id: demo\n'
            'phase: 5-execute\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,'
            'input_tokens,output_tokens,cache_read_input_tokens,'
            'cache_creation_input_tokens}:\n'
            'ts,clean_exit_queue_empty,100,2,1000,0,not-an-int,unmeasured,90\n',
            encoding='utf-8',
        )
        result = _al._parse_dispatch_boundary_file(artifact)

        assert len(result['rows']) == 1
        row = result['rows'][0]
        # A MEASURED zero survives as 0 alongside a corrupt neighbour.
        assert row['input_tokens'] == 0
        assert row['cache_creation_input_tokens'] == 90
        assert 'output_tokens' not in row
        assert 'cache_read_input_tokens' not in row
        assert row['unrecognised_columns'] == ['output_tokens']
        assert row['unmeasured_columns'] == ['cache_read_input_tokens']

    def test_counts_unknown_termination(self, tmp_path):
        """Legacy five-column rows count by cause AND report unmeasured columns.

        Same fixture shape as ``test_malformed_rows_skipped``; the count
        assertion alone would not notice the representation change, so both rows'
        context-load reads are pinned here too.
        """
        artifact = tmp_path / 'b.toon'
        artifact.write_text(
            'plan_id: demo\n'
            'phase: 5-execute\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            'ts,unknown,100,2,1000\n'
            'ts2,unknown,200,4,2000\n',
            encoding='utf-8',
        )
        result = _al._parse_dispatch_boundary_file(artifact)
        assert result['unknown_count'] == 2

        assert [row['total_tokens'] for row in result['rows']] == [100, 200]
        for row in result['rows']:
            assert 'input_tokens' not in row
            assert len(row['unmeasured_columns']) == 4
            assert row['unrecognised_columns'] == []


class TestReadDispatchBoundariesPerPhase:
    def test_no_work_dir_returns_empty(self, tmp_path):
        assert _al.read_dispatch_boundaries_per_phase(tmp_path) == {}

    def test_non_matching_filename_ignored(self, tmp_path):
        work = tmp_path / 'work'
        work.mkdir()
        # Glob only matches metrics-dispatch-boundaries-*.toon; the trailing
        # ``-`` (empty phase stem) entry is also discarded.
        (work / 'metrics-dispatch-boundaries-.toon').write_text('x\n', encoding='utf-8')
        assert _al.read_dispatch_boundaries_per_phase(work.parent) == {}


class TestAnalyzeFoldedGlobalLogsReadError:
    def test_unreadable_log_skipped_but_counted_as_file(self, tmp_path):
        logs_dir = tmp_path / 'logs'
        logs_dir.mkdir()
        # A directory matching the folded-log glob raises OSError on read_text,
        # exercising the defensive ``except OSError: continue`` branch.
        (logs_dir / 'work-2026-06-01.log').mkdir()

        result = _al.analyze_folded_global_logs(logs_dir)

        assert result['logs_present'] is True
        assert result['folded_log_files'] == 1
        assert result['total_lines'] == 0


class TestCmdRunInProcess:
    def _write_logs(self, plan_dir: Path, work_lines: list[str]) -> None:
        logs = plan_dir / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        (logs / 'work.log').write_text('\n'.join(work_lines) + '\n', encoding='utf-8')
        (logs / 'decision.log').write_text('', encoding='utf-8')
        (logs / 'script-execution.log').write_text(
            _line('2026-04-17T10:00:01Z', 'INFO', 'plan-marshall:manage-tasks:manage-tasks add (0.5s)')
            + '\n'
            + _line('2026-04-17T10:00:05Z', 'ERROR', 'plan-marshall:manage-files:manage-files add (0.1s)')
            + '\n',
            encoding='utf-8',
        )

    def test_happy_counts_and_no_findings(self, tmp_path):
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        self._write_logs(
            plan_dir,
            [
                _line('2026-04-17T10:00:00Z', 'INFO', '[STATUS] (plan-marshall:phase-1-init) Starting'),
                _line('2026-04-17T10:01:00Z', 'INFO', '[ARTIFACT] (plan-marshall:phase-5-execute:1) wrote'),
            ],
        )
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['src/a.py']}), encoding='utf-8'
        )

        result = _al.cmd_run(_run_args(plan_dir))

        assert result['aspect'] == 'log_analysis'
        assert int(result['counts']['work_entries']) == 2
        assert int(result['counts']['errors_script']) == 1
        assert int(result['counts']['artifact_entries']) == 1
        # footprint declared AND an ARTIFACT entry present → no ARTIFACT finding.
        assert not any('ARTIFACT entries missing' in f['message'] for f in result['findings'])

    def test_footprint_without_artifact_emits_finding(self, tmp_path):
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        self._write_logs(
            plan_dir,
            [_line('2026-04-17T10:00:00Z', 'INFO', '[STATUS] (plan-marshall:phase-1-init) Starting')],
        )
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['src/a.py', 'src/b.py']}), encoding='utf-8'
        )

        result = _al.cmd_run(_run_args(plan_dir))

        assert int(result['counts']['artifact_entries']) == 0
        assert any(
            f['severity'] == 'error' and 'ARTIFACT entries missing' in f['message']
            for f in result['findings']
        )

    def test_unresolvable_footprint_reports_unmeasurable_not_silence(self, tmp_path):
        """A footprint no tier could resolve makes the check UNMEASURABLE, not clean.

        The plan's references carry no footprint key at all, so the resolver
        answers ``None``. Previously that arrived as an empty list and the
        ``if footprint and ...`` guard fell through silently — an un-run check
        presented as a passing one. It must now name the gap and its reason.
        """
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        self._write_logs(
            plan_dir,
            [_line('2026-04-17T10:00:00Z', 'INFO', '[STATUS] (plan-marshall:phase-1-init) Starting')],
        )
        (plan_dir / 'references.json').write_text(json.dumps({'domains': []}), encoding='utf-8')

        result = _al.cmd_run(_run_args(plan_dir))

        assert int(result['counts']['artifact_entries']) == 0
        unmeasurable = [
            f for f in result['findings'] if 'ARTIFACT_COVERAGE_UNMEASURABLE' in f['message']
        ]
        assert len(unmeasurable) == 1, 'the unmeasurable state must be reported, not skipped'
        assert unmeasurable[0]['severity'] == 'warning'
        # It is NOT the graded failure: nothing was measured, so nothing failed.
        assert not any('ARTIFACT entries missing' in f['message'] for f in result['findings'])

    def test_resolved_empty_footprint_stays_a_measured_zero(self, tmp_path):
        """The peer direction: an observed-empty footprint grades normally.

        A present-but-empty ``modified_files`` IS a measurement — the plan
        touched nothing, so no ARTIFACT entry is expected and there is no gap to
        report. A fix that routed every empty footprint to the unmeasurable
        finding would trade one false signal for another.
        """
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        self._write_logs(
            plan_dir,
            [_line('2026-04-17T10:00:00Z', 'INFO', '[STATUS] (plan-marshall:phase-1-init) Starting')],
        )
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': []}), encoding='utf-8'
        )

        result = _al.cmd_run(_run_args(plan_dir))

        assert not any('ARTIFACT_COVERAGE_UNMEASURABLE' in f['message'] for f in result['findings'])
        assert not any('ARTIFACT entries missing' in f['message'] for f in result['findings'])

    def test_voluntary_checkpoint_polling_finding(self, tmp_path):
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        self._write_logs(
            plan_dir,
            [
                _line('2026-04-17T10:00:00Z', 'INFO', '[ATTEMPT] (plan-marshall:execute-task) dispatch'),
                _line('2026-04-17T10:00:01Z', 'INFO', '[STATUS] launched run_in_background=true'),
            ],
        )

        result = _al.cmd_run(_run_args(plan_dir))

        gaps = result['phase5_logging_gaps']['voluntary_checkpoint_polling']
        assert gaps['precondition_met'] is True
        assert gaps['polling_pairs_count'] == 1
        assert any('VOLUNTARY_CHECKPOINT_POLLING' in f['message'] for f in result['findings'])

    def test_folded_global_log_error_and_leak_findings(self, tmp_path):
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        self._write_logs(
            plan_dir,
            [_line('2026-04-17T10:00:00Z', 'INFO', '[STATUS] (plan-marshall:phase-1-init) Starting')],
        )
        # Folded-in global logs carrying both an ERROR line and a fixture leak.
        (plan_dir / 'logs' / 'work-2026-06-01.log').write_text(
            _line('2026-06-01T10:00:00Z', 'ERROR', '[STATUS] (x) boom') + '\n'
            + _line('2026-06-01T10:00:01Z', 'INFO', '[STATUS] orphan-md-xyz123 leaked') + '\n',
            encoding='utf-8',
        )

        result = _al.cmd_run(_run_args(plan_dir))

        signals = result['global_log_signals']
        assert int(signals['error_count']) >= 1
        assert int(signals['fixture_leak_count']) == 1
        assert any('GLOBAL_LOG_ERRORS' in f['message'] for f in result['findings'])
        assert any('GLOBAL_LOG_FIXTURE_LEAK' in f['message'] for f in result['findings'])
