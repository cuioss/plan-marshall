# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``analyze-logs.py``."""


from __future__ import annotations

import json

import pytest
from _analyze_logs_fixtures import (
    SCRIPT_PATH,
    _analyze_logs,
    _build_row,
    _hot_and_slow_log_lines,
    _line,
    _write_folded_log,
    _write_ledger,
)
from _plan_retrospective_fixtures import setup_live_plan  # noqa: E402

from conftest import run_script  # noqa: E402


class TestArtifactEmissionPopulation:
    """D4 — per-task ARTIFACT emission published as an N-of-M population.

    A count-based floor (``artifact_entries == 0``) cannot guard a per-item
    emission defect: it is satisfied by any single artifact even when most
    completed tasks emitted none. These tests pin the population statement that
    makes that partiality legible.
    """

    def _setup(self, tmp_path, monkeypatch, *, done_tasks, artifact_task_nums, plan_id):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id=plan_id)
        tasks_dir = plan_dir / 'tasks'
        for existing in tasks_dir.glob('TASK-*.json'):
            existing.unlink()
        for num in done_tasks:
            (tasks_dir / f'TASK-{num:03d}.json').write_text(
                json.dumps({'number': num, 'deliverable': 1, 'status': 'done'}),
                encoding='utf-8',
            )
        lines = [
            '[2026-04-17T10:00:00Z] [INFO] [aaaaaa] [STATUS] '
            '(plan-marshall:phase-1-init) Starting'
        ]
        for num in artifact_task_nums:
            lines.append(
                f'[2026-04-17T10:0{num}:00Z] [INFO] [bbbbbb] [ARTIFACT] '
                f'(plan-marshall:phase-5-execute:{num}) Wrote src/f{num}.py'
            )
        (plan_dir / 'logs' / 'work.log').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return plan_id, plan_dir

    def test_partial_emission_reported_as_population(self, tmp_path, monkeypatch):
        # 3 completed tasks, only task 1 emitted a per-task [ARTIFACT] line.
        plan_id, _ = self._setup(
            tmp_path, monkeypatch, done_tasks=[1, 2, 3], artifact_task_nums=[1],
            plan_id='retro-artifact-partial',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        emission = data['artifact_emission']
        assert int(emission['completed_tasks']) == 3
        assert int(emission['tasks_with_artifacts']) == 1
        # The bare non-zero floor is SATISFIED (>= 1 artifact), yet partiality is
        # surfaced — the exact defect D4 closes.
        assert int(data['counts']['artifact_entries']) >= 1
        findings = data.get('findings') or []
        assert any('ARTIFACT_EMISSION_PARTIAL' in f.get('message', '') for f in findings), findings

    def test_complete_emission_raises_no_partial_finding(self, tmp_path, monkeypatch):
        plan_id, _ = self._setup(
            tmp_path, monkeypatch, done_tasks=[1, 2], artifact_task_nums=[1, 2],
            plan_id='retro-artifact-complete',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        emission = data['artifact_emission']
        assert int(emission['completed_tasks']) == 2
        assert int(emission['tasks_with_artifacts']) == 2
        findings = data.get('findings') or []
        assert not any('ARTIFACT_EMISSION_PARTIAL' in f.get('message', '') for f in findings), findings

    def test_population_always_published_even_with_no_per_task_emission(self, tmp_path, monkeypatch):
        # Population is published even at N == 0 so a consumer reads N-of-M
        # rather than inferring a total from a floor; no partiality finding at 0.
        plan_id, _ = self._setup(
            tmp_path, monkeypatch, done_tasks=[1, 2], artifact_task_nums=[],
            plan_id='retro-artifact-none',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        emission = data['artifact_emission']
        assert int(emission['completed_tasks']) == 2
        assert int(emission['tasks_with_artifacts']) == 0
        findings = data.get('findings') or []
        assert not any('ARTIFACT_EMISSION_PARTIAL' in f.get('message', '') for f in findings), findings


class TestBuildTimeFromLedger:
    """D3: ``analyze-logs.py`` sums the plan's build time from the change-ledger —
    the build-time ORACLE — into a ``build_time`` block the ``plan_efficiency``
    aspect reads into its totals.

    Each test would FAIL pre-fix: pre-fix ``analyze-logs.py`` never read the ledger
    and its output carried no ``build_time`` block at all (``KeyError``)."""

    def test_total_build_seconds_sums_valid_durations(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        _write_ledger(tmp_path / 'base', [
            _build_row(plan_id, dur=30.0),
            _build_row(plan_id, dur=250.0),
        ])
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        bt = result.toon()['build_time']
        assert float(bt['total_build_seconds']) == 280.0
        assert int(bt['build_count']) == 2

    def test_suspect_zero_not_summed(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        _write_ledger(tmp_path / 'base', [
            _build_row(plan_id, dur=300.0),
            _build_row(plan_id, dur=0.0),      # killed-as-0 / cache-hit shape
        ])
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        bt = result.toon()['build_time']
        assert float(bt['total_build_seconds']) == 300.0   # the 0 is NOT averaged in
        assert int(bt['suspect_count']) == 1

    def test_killed_separate_from_error(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        _write_ledger(tmp_path / 'base', [
            _build_row(plan_id, dur=10.0, status='error'),
            _build_row(plan_id, dur=10.0, status='killed'),
            _build_row(plan_id, dur=10.0, status='killed'),
        ])
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        bt = result.toon()['build_time']
        assert int(bt['error']) == 1     # killed is NOT folded into error
        assert int(bt['killed']) == 2

    def test_non_pyproject_build_counted(self, tmp_path, monkeypatch):
        # the single-tool blindness is closed: a Maven build is counted here too.
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        _write_ledger(tmp_path / 'base', [
            _build_row(
                plan_id, dur=200.0,
                notation='plan-marshall:build-maven:maven_build', command='mvn verify',
            ),
        ])
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        bt = result.toon()['build_time']
        assert float(bt['total_build_seconds']) == 200.0
        assert int(bt['build_count']) == 1

    def test_no_ledger_rows_all_zero(self, tmp_path, monkeypatch):
        # absent is not zero: no rows => build_count 0 (unavailable), total 0.
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        bt = result.toon()['build_time']
        assert int(bt['build_count']) == 0
        assert float(bt['total_build_seconds']) == 0.0

    def test_other_plan_rows_not_attributed(self, tmp_path, monkeypatch):
        # rows for a different plan_id are not summed into this plan.
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        _write_ledger(tmp_path / 'base', [
            _build_row(plan_id, dur=100.0),
            _build_row('some-other-plan', dur=999.0),
        ])
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        bt = result.toon()['build_time']
        assert float(bt['total_build_seconds']) == 100.0
        assert int(bt['build_count']) == 1


class TestScriptCostRollup:
    """The roll-up ranks a many-fast-calls script above a few-slow-calls one."""

    def test_ranks_many_fast_above_few_slow(self, tmp_path):
        logs_dir = tmp_path / 'logs'
        _write_folded_log(logs_dir, 'script-execution-2026-06-01.log', _hot_and_slow_log_lines())

        rollup = _analyze_logs.analyze_folded_global_logs(logs_dir)['cost_rollup']

        # The dominant-but-fast script outranks the rare-but-slow one.
        assert rollup['ranked'][0]['notation'] == 'pm:hot:hot'
        assert rollup['ranked'][0]['calls'] == 100
        assert rollup['ranked'][0]['cumulative_ms'] == pytest.approx(20000.0)
        assert rollup['ranked'][1]['notation'] == 'pm:slow:slow'
        assert rollup['ranked'][1]['calls'] == 1

    def test_ceiling_is_blind_to_the_script_the_rollup_ranks_first(self, tmp_path):
        # The "read them together" assertion: the ceiling reports NOTHING slow
        # while the roll-up reports one script owning the majority of the time.
        logs_dir = tmp_path / 'logs'
        _write_folded_log(logs_dir, 'script-execution-2026-06-01.log', _hot_and_slow_log_lines())

        signals = _analyze_logs.analyze_folded_global_logs(logs_dir)

        assert signals['slow_call_count'] == 0
        assert signals['cost_rollup']['calls_at_or_over_ceiling'] == 0
        assert signals['cost_rollup']['ranked'][0]['share_pct'] == pytest.approx(80.0)

    def test_share_pct_is_a_share_of_the_published_total(self, tmp_path):
        logs_dir = tmp_path / 'logs'
        _write_folded_log(logs_dir, 'script-execution-2026-06-01.log', _hot_and_slow_log_lines())

        rollup = _analyze_logs.analyze_folded_global_logs(logs_dir)['cost_rollup']

        assert rollup['total_calls'] == 101
        assert rollup['total_duration_ms'] == pytest.approx(25000.0)
        assert rollup['distinct_scripts'] == 2
        # Every ranked share is a share of the SAME published denominator.
        recomputed = [
            round(row['cumulative_ms'] / rollup['total_duration_ms'] * 100.0, 3)
            for row in rollup['ranked']
        ]
        assert [row['share_pct'] for row in rollup['ranked']] == recomputed

    def test_truncation_is_visible_never_silent(self, tmp_path):
        # 15 distinct scripts, ranked list capped at 10: the cap must be legible
        # from the fragment (distinct_scripts > ranked_count), never silent.
        logs_dir = tmp_path / 'logs'
        lines = [
            _line('2026-06-01T10:00:00Z', 'INFO', f'pm:s{i:02d}:s{i:02d} run ({i + 1}.0s)')
            for i in range(15)
        ]
        _write_folded_log(logs_dir, 'script-execution-2026-06-01.log', lines)

        rollup = _analyze_logs.analyze_folded_global_logs(logs_dir)['cost_rollup']

        assert rollup['distinct_scripts'] == 15
        assert rollup['ranked_count'] == 10
        assert len(rollup['ranked']) == 10
        # The published total still spans ALL 15, so the residual is derivable.
        assert rollup['total_calls'] == 15

    def test_unattributable_calls_bounds_the_population_gap(self, tmp_path):
        # A duration-bearing line with no parseable notation is counted by the
        # ceiling but cannot be attributed to any script, so the roll-up excludes
        # it. The count BOUNDS the ceiling/roll-up gap rather than equalling it:
        # here the only unnamed call is fast, so the gap is 0 while the count is 1.
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'script-execution-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', 'pm:named:named run (40.0s)'),
                _line('2026-06-01T10:00:01Z', 'INFO', 'no notation here at all (1.0s)'),
            ],
        )

        signals = _analyze_logs.analyze_folded_global_logs(logs_dir)

        assert signals['unattributable_calls'] == 1
        assert signals['slow_call_count'] == 1
        assert signals['cost_rollup']['calls_at_or_over_ceiling'] == 1
        gap = signals['slow_call_count'] - signals['cost_rollup']['calls_at_or_over_ceiling']
        assert gap == 0
        assert gap <= signals['unattributable_calls']
        # The unnamed call contributes to neither the ranking nor its total.
        assert signals['cost_rollup']['total_calls'] == 1

    def test_unattributable_slow_call_is_seen_by_the_ceiling_only(self, tmp_path):
        # When the unnamed call IS over the ceiling, the ceiling counts it and
        # the roll-up cannot — this is the case where the gap is nonzero.
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'script-execution-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'no notation here at all (40.0s)')],
        )

        signals = _analyze_logs.analyze_folded_global_logs(logs_dir)

        assert signals['slow_call_count'] == 1
        assert signals['cost_rollup']['calls_at_or_over_ceiling'] == 0
        assert signals['unattributable_calls'] == 1
        gap = signals['slow_call_count'] - signals['cost_rollup']['calls_at_or_over_ceiling']
        assert gap <= signals['unattributable_calls']

    def test_ceiling_count_spans_the_whole_population_not_the_ranked_cap(self, tmp_path):
        # `ranked` is capped; `calls_at_or_over_ceiling` is not. A ceiling-crossing
        # call belonging to a script the cap excluded is still counted, so the
        # count can exceed what the visible rows account for.
        logs_dir = tmp_path / 'logs'
        lines = [
            _line('2026-06-01T10:00:00Z', 'INFO', f'pm:s{i:02d}:s{i:02d} run (31.0s)')
            for i in range(12)
        ]
        _write_folded_log(logs_dir, 'script-execution-2026-06-01.log', lines)

        rollup = _analyze_logs.analyze_folded_global_logs(logs_dir)['cost_rollup']

        assert rollup['ranked_count'] == 10
        assert rollup['distinct_scripts'] == 12
        assert rollup['calls_at_or_over_ceiling'] == 12

    def test_malformed_duration_is_refused_not_counted_as_zero(self, tmp_path):
        # A malformed body like `(1.2.3s)` carries no usable duration. Matching
        # it and coercing the parse failure to 0.0 would put a call that
        # contributed nothing measured into the total it was counted in — the
        # absent-read-as-zero defect this roll-up exists to avoid.
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'script-execution-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', 'pm:good:good run (2.0s)'),
                _line('2026-06-01T10:00:01Z', 'INFO', 'pm:bad:bad run (1.2.3s)'),
            ],
        )

        rollup = _analyze_logs.analyze_folded_global_logs(logs_dir)['cost_rollup']

        assert rollup['total_calls'] == 1
        assert rollup['total_duration_ms'] == pytest.approx(2000.0)
        assert [row['notation'] for row in rollup['ranked']] == ['pm:good:good']

    def test_sub_precision_calls_are_counted_so_the_total_reads_as_a_floor(self, tmp_path):
        # `manage-logging` formats durations `%.2f`, so a sub-5ms call is written
        # as `0.00s` and adds nothing to the cumulative total. Counting them is
        # what makes the total legible as a FLOOR rather than a measurement.
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'script-execution-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', 'pm:tiny:tiny run (0.00s)'),
                _line('2026-06-01T10:00:01Z', 'INFO', 'pm:tiny:tiny run (0.00s)'),
                _line('2026-06-01T10:00:02Z', 'INFO', 'pm:real:real run (1.00s)'),
            ],
        )

        rollup = _analyze_logs.analyze_folded_global_logs(logs_dir)['cost_rollup']

        assert rollup['sub_precision_calls'] == 2
        tiny = next(r for r in rollup['ranked'] if r['notation'] == 'pm:tiny:tiny')
        assert tiny['calls'] == 2
        assert tiny['cumulative_ms'] == pytest.approx(0.0)
        assert tiny['sub_precision_calls'] == 2
        real = next(r for r in rollup['ranked'] if r['notation'] == 'pm:real:real')
        assert real['sub_precision_calls'] == 0

    def test_empty_corpus_publishes_zero_not_absence(self, tmp_path):
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'work-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] (x) no duration here')],
        )

        rollup = _analyze_logs.analyze_folded_global_logs(logs_dir)['cost_rollup']

        assert rollup['total_calls'] == 0
        assert rollup['total_duration_ms'] == 0.0
        assert rollup['ranked'] == []

    def test_rollup_surfaces_in_the_toon_fragment(self, tmp_path, monkeypatch):
        # End-to-end: the plan's own script-execution.log roll-up reaches output.
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        rollup = data['script_cost_rollup']
        assert rollup['population'] == 'plan_script_execution_log'
        assert int(rollup['total_calls']) == 3
        # manage-status ran 2.5s of the 2.67s total -> it ranks first here too,
        # but by CUMULATIVE time rather than by single-call duration.
        assert rollup['ranked'][0]['notation'] == 'plan-marshall:manage-status:manage-status'
