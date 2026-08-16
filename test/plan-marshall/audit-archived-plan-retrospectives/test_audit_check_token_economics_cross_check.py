#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``token-economics`` cross-plan check — corpus-level aggregation across
archived plans and the verdict it reports.
"""

from pathlib import Path

from _audit_fixtures import (
    _write_token_plan,
    audit,
)


class TestTokenEconomicsCrossCheck:
    """``cross_token_economics`` assembles per-plan rows, by-dimension aggregates,
    and the derived thresholds; ``emit_token_economics_block`` renders them."""

    def test_rows_sorted_descending_by_total_tokens(self, tmp_path: Path):
        inputs = [
            _write_token_plan(tmp_path, 'small', phase_tokens={'5-execute': 1_000}),
            _write_token_plan(tmp_path, 'large', phase_tokens={'5-execute': 9_000}),
            _write_token_plan(tmp_path, 'medium', phase_tokens={'5-execute': 5_000}),
        ]

        result = audit.cross_token_economics(inputs)

        # descending order, corpus count echoed
        assert result['plans_in_corpus'] == 3
        assert [r['plan_id'] for r in result['rows']] == ['large', 'medium', 'small']

    def test_by_change_type_aggregate_amortizes_tokens_per_file(self, tmp_path: Path):
        # two feature plans, one chore plan
        inputs = [
            _write_token_plan(
                tmp_path, 'feat-a', change_type='feature', files=2,
                phase_tokens={'5-execute': 4_000},
            ),
            _write_token_plan(
                tmp_path, 'feat-b', change_type='feature', files=2,
                phase_tokens={'5-execute': 6_000},
            ),
            _write_token_plan(
                tmp_path, 'chore-a', change_type='chore', files=5,
                phase_tokens={'5-execute': 5_000},
            ),
        ]

        result = audit.cross_token_economics(inputs)
        by_ct = {row['value']: row for row in result['by_change_type']}

        # feature: 2 plans, (4000+6000)//(2+2) tokens/file
        assert by_ct['feature']['n'] == 2
        assert by_ct['feature']['avg_tokens'] == 5_000  # (4000+6000)//2
        assert by_ct['feature']['tokens_per_file'] == 2_500  # 10000 // 4
        assert by_ct['chore']['n'] == 1
        assert by_ct['chore']['tokens_per_file'] == 1_000  # 5000 // 5

    def test_by_scope_aggregate_groups_on_scope_estimate(self, tmp_path: Path):
        # two scopes
        inputs = [
            _write_token_plan(
                tmp_path, 'surg-a', scope_estimate='surgical',
                phase_tokens={'5-execute': 3_000},
            ),
            _write_token_plan(
                tmp_path, 'surg-b', scope_estimate='surgical',
                phase_tokens={'5-execute': 5_000},
            ),
            _write_token_plan(
                tmp_path, 'mm-a', scope_estimate='multi_module',
                phase_tokens={'5-execute': 9_000},
            ),
        ]

        result = audit.cross_token_economics(inputs)
        by_scope = {row['value']: row for row in result['by_scope']}

        assert by_scope['surgical']['n'] == 2
        assert by_scope['multi_module']['n'] == 1

    def test_empty_corpus_yields_zero_aggregates_no_rows(self):
        # no plans carrying metrics
        result = audit.cross_token_economics([])

        # best-effort empty result, never raises
        assert result['plans_in_corpus'] == 0
        assert result['rows'] == []
        assert result['by_change_type'] == []
        assert result['by_scope'] == []

    def test_emit_block_carries_derived_thresholds_and_genuine_count(
        self, tmp_path: Path
    ):
        # a corpus with exactly one clearly-flagged plan (long session).
        # The token/file footprint is deliberately UNIFORM across all four plans so
        # the corpus-relative floor/big-spend outlier flags correctly suppress (no
        # cheap tail, no plan outspending the median) — only the genuine session
        # outlier should be flagged. The three baseline plans record no
        # `session_message_count`, so they are excluded from the message-count p75
        # distribution and cannot trip `long_session`; the marathon plan alone sets
        # the p75 and exceeds it.
        short = [
            _write_token_plan(
                tmp_path, f'short-{i}',
                phase_tokens={'5-execute': 5_000},
            )
            for i in range(3)
        ]
        flagged = _write_token_plan(
            tmp_path, 'flagged', session_message_count=999,
            phase_tokens={'5-execute': 5_000},
        )
        result = audit.cross_token_economics([*short, flagged])

        block = audit.emit_token_economics_block(result)

        # header, derived (floating) thresholds, and the genuine count
        assert 'check: token-economics' in block
        assert 'status: success' in block
        assert 'floor_band_p10_tokens:' in block
        assert 'median_total_tokens:' in block
        assert 'long_session_p75_msgs:' in block
        assert 'genuine_signal_count: 1' in block
        # the flagged plan's row carries the genuine severity stamp
        assert 'genuine' in block

    def test_emit_block_includes_by_change_type_and_by_scope_tables(
        self, tmp_path: Path
    ):
        inputs = [
            _write_token_plan(
                tmp_path, 'a', change_type='feature', scope_estimate='surgical',
                phase_tokens={'5-execute': 5_000},
            ),
            _write_token_plan(
                tmp_path, 'b', change_type='fix', scope_estimate='multi_module',
                phase_tokens={'5-execute': 7_000},
            ),
        ]
        result = audit.cross_token_economics(inputs)

        block = audit.emit_token_economics_block(result)

        # both aggregate tables are rendered with their column headers
        assert 'by_change_type[' in block
        assert 'by_scope[' in block
        assert 'tokens_per_file' in block

    def test_thresholds_are_corpus_derived_not_hard_coded(self, tmp_path: Path):
        # two corpora with disjoint scales must yield different floors,
        # proving the cut-points float with the live distribution (no magic number).
        small_rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(
                    tmp_path, f'sm-{i}', phase_tokens={'5-execute': (i + 1) * 100}
                )
                for i in range(10)
            ]
        )
        big_rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(
                    tmp_path, f'bg-{i}', phase_tokens={'5-execute': (i + 1) * 100_000}
                )
                for i in range(10)
            ]
        )

        small_thr = audit._derive_token_economics_thresholds(small_rows)
        big_thr = audit._derive_token_economics_thresholds(big_rows)

        # the floor band scales with the corpus, it is not a constant
        assert small_thr['floor_band'] != big_thr['floor_band']
        assert big_thr['floor_band'] == small_thr['floor_band'] * 1_000
