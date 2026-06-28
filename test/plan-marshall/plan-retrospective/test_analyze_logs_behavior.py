# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for ``analyze-logs.py``.

The sibling ``test_analyze_logs.py`` covers the phase-5 fact extractors and the
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
        artifact = tmp_path / 'b.toon'
        artifact.write_text(
            'plan_id: demo\n'
            'phase: 5-execute\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            'too,few,fields\n'  # wrong field count → skipped
            'ts,unknown,not-an-int,2,1000\n'  # non-int → skipped
            'ts2,clean_exit_queue_empty,100,2,1000\n',  # valid
            encoding='utf-8',
        )
        result = _al._parse_dispatch_boundary_file(artifact)
        assert result['present'] is True
        assert len(result['rows']) == 1
        assert result['clean_exit_queue_empty_count'] == 1

    def test_counts_unknown_termination(self, tmp_path):
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
