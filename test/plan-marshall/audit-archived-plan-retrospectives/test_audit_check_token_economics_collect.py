#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``token-economics`` collection and thresholds — per-plan token figures are
collected from the metrics store and compared against the centralized thresholds.
"""

from pathlib import Path

from _audit_fixtures import (
    _write_token_plan,
    audit,
)


class TestTokenEconomicsCollect:
    """``_collect_token_economics_rows`` joins per-plan metrics, the TASK count,
    and the references/status fields into one efficiency row per plan."""

    def test_per_plan_join_yields_tokens_per_file_and_task(self, tmp_path: Path):
        # 12,000 tokens, 4 files, 3 tasks → floor-divided ratios
        inputs = _write_token_plan(
            tmp_path,
            'plan-join',
            files=4,
            task_count=3,
            phase_tokens={'5-execute': 12_000},
        )

        rows = audit._collect_token_economics_rows([inputs])

        # single row, ratios floor-divided, fields joined from artefacts
        assert len(rows) == 1
        row = rows[0]
        assert row.plan_id == 'plan-join'
        assert row.change_type == 'feature'
        assert row.scope_estimate == 'surgical'
        assert row.files == 4
        assert row.tasks == 3
        assert row.total_tokens == 12_000
        assert row.tokens_per_file == 3_000  # 12000 // 4
        assert row.tokens_per_task == 4_000  # 12000 // 3

    def test_zero_files_and_tasks_yield_zero_ratios(self, tmp_path: Path):
        # empty footprint must not raise ZeroDivisionError
        inputs = _write_token_plan(
            tmp_path, 'plan-empty', files=0, task_count=0,
            phase_tokens={'5-execute': 5_000},
        )

        rows = audit._collect_token_economics_rows([inputs])

        # guarded division returns 0, not an exception
        assert rows[0].tokens_per_file == 0
        assert rows[0].tokens_per_task == 0

    def test_plan_without_metrics_is_excluded_from_corpus(self, tmp_path: Path):
        # a plan whose metrics.toon has no parseable phase block
        good = _write_token_plan(tmp_path, 'plan-good', phase_tokens={'5-execute': 9_000})
        empty_dir = tmp_path / '.plan' / 'temp' / 'token-corpus' / 'plan-nometrics'
        (empty_dir / 'work').mkdir(parents=True, exist_ok=True)
        bad = audit.collect_inputs(empty_dir)

        rows = audit._collect_token_economics_rows([good, bad])

        # only the plan carrying phase metrics survives
        assert {r.plan_id for r in rows} == {'plan-good'}

    def test_exec_metrics_blind_set_when_execute_phase_absent(self, tmp_path: Path):
        # planning-only metrics, no 5-execute token block
        inputs = _write_token_plan(
            tmp_path, 'plan-blind',
            phase_tokens={'2-refine': 4_000, '4-plan': 6_000},
        )

        rows = audit._collect_token_economics_rows([inputs])

        # execute total == 0 → structural blindness flag
        assert rows[0].exec_metrics_blind is True

    def test_session_message_count_read_from_top_level_scalar(self, tmp_path: Path):
        # the scalar lives above the first [phase] section
        inputs = _write_token_plan(
            tmp_path, 'plan-msgs', session_message_count=412,
            phase_tokens={'5-execute': 8_000},
        )

        rows = audit._collect_token_economics_rows([inputs])

        assert rows[0].session_message_count == 412


class TestTokenEconomicsThresholds:
    """``_derive_token_economics_thresholds`` measures every cut-point from the
    LIVE corpus distribution — none are hard-coded magic numbers."""

    def test_empty_corpus_yields_all_zero_thresholds(self):
        thr = audit._derive_token_economics_thresholds([])

        # an empty corpus can flag nothing
        assert all(v == 0.0 for v in thr.values())
        assert thr['floor_band'] == 0.0
        assert thr['median_total'] == 0.0

    def test_floor_band_is_corpus_tenth_percentile(self, tmp_path: Path):
        # ten plans with distinct totals so p10 is determinate
        rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(
                    tmp_path, f'p-{i}', phase_tokens={'5-execute': (i + 1) * 1_000}
                )
                for i in range(10)
            ]
        )

        thr = audit._derive_token_economics_thresholds(rows)

        # nearest-rank p10 of [1000..10000] equals the manual computation
        totals = sorted(float(r.total_tokens) for r in rows)
        assert thr['floor_band'] == audit.percentile(totals, 10)
        assert thr['median_total'] == audit.median(totals)

    def test_median_total_matches_manual_median(self, tmp_path: Path):
        # three plans, odd count → middle value is the median
        rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(tmp_path, 'lo', phase_tokens={'5-execute': 1_000}),
                _write_token_plan(tmp_path, 'mid', phase_tokens={'5-execute': 5_000}),
                _write_token_plan(tmp_path, 'hi', phase_tokens={'5-execute': 9_000}),
            ]
        )

        thr = audit._derive_token_economics_thresholds(rows)

        assert thr['median_total'] == 5_000.0

    def test_planning_exec_ratio_excludes_blind_plans(self, tmp_path: Path):
        # one measured plan (ratio 2.0) and one execute-blind plan that
        # must NOT contribute to the median ratio distribution.
        measured = _write_token_plan(
            tmp_path, 'measured',
            phase_tokens={'2-refine': 2_000, '4-plan': 2_000, '5-execute': 2_000},
        )
        blind = _write_token_plan(
            tmp_path, 'blind',
            phase_tokens={'2-refine': 9_000, '4-plan': 9_000},
        )

        # collect the per-plan rows first (the threshold deriver consumes
        # _TokenEconomicsRow, not raw PlanInputs)
        rows = audit._collect_token_economics_rows([measured, blind])
        thr = audit._derive_token_economics_thresholds(rows)

        # planning 4000 / execute 2000 = 2.0, blind plan excluded
        assert thr['median_planning_exec_ratio'] == 2.0

    def test_corpus_phase_shares_sum_over_grand_total(self, tmp_path: Path):
        # two plans, all spend in one phase each
        rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(tmp_path, 'a', phase_tokens={'3-outline': 4_000}),
                _write_token_plan(tmp_path, 'b', phase_tokens={'5-execute': 6_000}),
            ]
        )

        # grand total 10,000: outline 4000/10000, execute 6000/10000
        thr = audit._derive_token_economics_thresholds(rows)

        assert thr['corpus_outline_share'] == 0.4
        assert thr['corpus_execute_share'] == 0.6
