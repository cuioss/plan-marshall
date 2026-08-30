# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for ``analyze-logs.py``.

The siblings ``test_analyze_logs_phase5_logging_gap_extractors.py`` and
``test_analyze_logs_analyze_folded_global.py`` cover the phase-5 fact extractors
and the folded-global-log analyzer directly, but drive the top-level ``cmd_run``
orchestration only through ``run_script`` (subprocess — not counted for
coverage). This module fills the in-process gaps: ``cmd_run`` itself (and its
finding-emitting branches), the dispatch-boundary file parser's malformed/OSError
paths, the duration/percentile/notation extractors' skip branches, and the
``resolve_*`` helpers — each asserted against crafted ``tmp_path`` inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from _plan_retrospective_fixtures import _run_args

from conftest import load_script_module

_al = load_script_module('plan-marshall', 'plan-retrospective', 'analyze-logs.py', 'al_behavior_mod')


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

    def test_only_the_length_floor_drops_a_row(self, tmp_path):
        """A LEGACY five-column fixture: the short row drops, the corrupt one does NOT.

        Two malformations, two DIFFERENT outcomes, and the difference is the
        point. A row too short to carry the legacy five gives the reader no way
        to position its cells, so the ``len(parts) < _LEGACY_COLUMN_COUNT`` floor
        drops it. A row of the right WIDTH whose ``total_tokens`` cell is corrupt
        is KEPT: that one cell degrades to ``0`` and every other cell on the row
        — including its context-load cells — stays readable. Dropping the row
        would discard measurements the reader parsed perfectly well, and would
        disagree with the audit reader, which keeps such a row and measures its
        context-load cells.

        This is also the file's coverage of what a surviving legacy row says
        about its four appended columns: they are UNMEASURED (absent), not a
        measured ``0``. Asserting only a row count would stay green across that
        representation change while proving nothing about it.
        """
        artifact = tmp_path / 'b.toon'
        artifact.write_text(
            'plan_id: demo\n'
            'phase: 5-execute\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            'too,few,fields\n'  # under the five-column floor → dropped
            'ts,unknown,not-an-int,2,1000\n'  # corrupt LEGACY cell → kept, degraded
            'ts2,clean_exit_queue_empty,100,2,1000\n',  # valid
            encoding='utf-8',
        )
        result = _al._parse_dispatch_boundary_file(artifact)
        assert result['present'] is True

        # Exactly one row was dropped, and it was the short one.
        assert len(result['rows']) == 2
        assert result['clean_exit_queue_empty_count'] == 1
        assert result['unknown_count'] == 1

        degraded, valid = result['rows']
        # The corrupt cell degrades to 0 rather than taking its row with it...
        assert degraded['termination_cause'] == 'unknown'
        assert degraded['total_tokens'] == 0
        # ...and its intact neighbours on the same row survive the degrade.
        assert degraded['tool_uses'] == 2
        assert degraded['duration_ms'] == 1000
        assert valid['total_tokens'] == 100

        # The legacy floor survives AND each surviving row's context-load columns
        # read as unmeasured rather than as measured zeros.
        for row in (degraded, valid):
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

        A corrupt appended cell is ``unrecognised`` and the row is KEPT — the
        distinction this fixture pins.

        ⛔ Two PROVENANCE cases, not two buckets: a legacy row (the column is
        absent) and an explicit ``unmeasured`` token are reported through the
        SAME ``unmeasured_columns`` output by ``analyze-logs.py``. They differ in
        why the value is missing, not in where the reader files it, and this
        fixture creates no legacy row at all — that case is covered by the
        legacy-row test. Naming them as separate reader buckets here described an
        output shape the parser does not produce. A fourth, ``indeterminate``, exists for a literal ``0`` the
        reader cannot date; this row carries a nonzero cell, which dates it, so
        its zeros are measured rather than indeterminate.
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

    def _write_tasks(self, plan_dir: Path, changed_by_num: dict[int, list[str]]) -> None:
        """Write ``status: done`` task records carrying a RECORDED ``changed_files``.

        An empty list is a recorded no-op — "this task changed nothing", which is
        a measurement. Omitting the key entirely is a different state (nothing
        was recorded), and no fixture here reaches it by accident.
        """
        tasks_dir = plan_dir / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)
        for num, changed in changed_by_num.items():
            (tasks_dir / f'TASK-{num:03d}.json').write_text(
                json.dumps(
                    {
                        'number': num,
                        'deliverable': 1,
                        'status': 'done',
                        'changed_files': changed,
                    }
                ),
                encoding='utf-8',
            )

    def test_no_completed_tasks_reports_unavailable_attribution_not_a_finding(self, tmp_path):
        """A plan with no completed task has nothing to attribute, and says so.

        The per-task ``[ARTIFACT]`` guard is drawn from the CHANGE-QUALIFIED
        population, which exists only when some completed task record carries a
        ``changed_files`` list. With no completed tasks at all no record can carry
        one, so attribution is reported UNAVAILABLE and the guard short-circuits
        before any population comparison — the honest reading of "nothing to
        attribute", never a measured empty set.

        This plan has a non-empty footprint and zero per-task artifact lines, the
        shape the guard reacts to, so what is pinned here is the attribution gate.
        Its measured peer — a real shortfall over a qualified population, where
        the guard must still bite — is the test beneath it; either alone would be
        single-direction.
        """
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        self._write_logs(
            plan_dir,
            [_line('2026-04-17T10:00:00Z', 'INFO', '[STATUS] (plan-marshall:phase-1-init) Starting')],
        )
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['src/a.py']}), encoding='utf-8'
        )

        result = _al.cmd_run(_run_args(plan_dir))
        emission = result['artifact_emission']

        assert emission['completed_tasks'] == 0
        assert emission['tasks_with_artifacts'] == 0
        assert emission['change_attribution'] == 'unavailable'
        for key in ('eligible_tasks', 'eligible_tasks_with_artifacts'):
            assert key not in emission, (
                f'{key} must be ABSENT when attribution is unavailable — a zero '
                'there is indistinguishable from a measured empty population'
            )
        assert not any('ARTIFACT_EMISSION' in f['message'] for f in result['findings'])

    def test_change_qualified_shortfall_emits_partial_over_the_eligible_population(
        self, tmp_path
    ):
        """⛔ The measured peer: the guard still BITES, over the eligible set only.

        Three completed tasks — two recorded as having changed a file (one of
        which emitted its ``[ARTIFACT]`` line and one of which did not) and one
        recorded NO-OP with an empty ``changed_files``. The finding is drawn from
        the eligible two, so it reads ``1 of 2``: quoting the raw ``1 of 3`` would
        charge the compliant no-op task as an emission gap, and staying silent
        because a no-op is present would mute a real shortfall.

        In-process because this is a ``cmd_run`` finding-emitting branch, which
        the subprocess siblings drive but do not cover.
        """
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        self._write_logs(
            plan_dir,
            [
                _line('2026-04-17T10:00:00Z', 'INFO', '[STATUS] (plan-marshall:phase-1-init) Starting'),
                _line('2026-04-17T10:01:00Z', 'INFO', '[ARTIFACT] (plan-marshall:phase-5-execute:1) wrote'),
            ],
        )
        self._write_tasks(plan_dir, {1: ['src/a.py'], 2: ['src/b.py'], 3: []})
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['src/a.py', 'src/b.py']}), encoding='utf-8'
        )

        result = _al.cmd_run(_run_args(plan_dir))
        emission = result['artifact_emission']

        # The raw and eligible populations are staged as genuinely different
        # numbers, which is what makes the message assertion a test of WHICH one
        # the finding follows rather than a restatement of one of them.
        assert emission['completed_tasks'] == 3
        assert emission['change_attribution'] == 'measured'
        assert emission['eligible_tasks'] == 2
        assert emission['eligible_tasks_with_artifacts'] == 1

        partial = [f for f in result['findings'] if 'ARTIFACT_EMISSION_PARTIAL' in f['message']]
        assert len(partial) == 1, result['findings']
        assert '1 of 2 change-qualified' in partial[0]['message']
        assert '1 of 3' not in partial[0]['message']

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
