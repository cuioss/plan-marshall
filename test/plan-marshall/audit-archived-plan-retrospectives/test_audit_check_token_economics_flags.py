#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``token-economics`` flagging — which per-plan token profiles raise a genuine
signal and which are informational.
"""

from pathlib import Path

from _audit_fixtures import (
    _write_token_plan,
    audit,
)


class TestTokenEconomicsFlags:
    """``_token_economics_flags`` derives each anti-pattern flag from the
    corpus-relative cut-points — no flag string carries a hard-coded comparand."""

    def test_fixed_overhead_floor_fires_on_cheapest_tiny_plan(self, tmp_path: Path):
        # a corpus where one plan sits in the bottom decile AND the
        # bottom file-count quartile (the non-amortizing 6-phase tax).
        corpus = [
            _write_token_plan(
                tmp_path, f'big-{i}', files=20, phase_tokens={'5-execute': 50_000}
            )
            for i in range(9)
        ]
        floor = _write_token_plan(
            tmp_path, 'floor', files=1, phase_tokens={'5-execute': 500}
        )
        rows = audit._collect_token_economics_rows([*corpus, floor])
        thr = audit._derive_token_economics_thresholds(rows)
        floor_row = next(r for r in rows if r.plan_id == 'floor')

        flags = audit._token_economics_flags(floor_row, thr)

        # flag present and annotates the floating p10 / p25 cut-points
        assert any(f.startswith('fixed_overhead_floor(') for f in flags)
        assert any('p10=' in f and 'p25=' in f for f in flags)

    def test_planning_gt_exec_fires_above_median_ratio(self, tmp_path: Path):
        # corpus median planning/exec ratio is low; one plan blows past it
        baseline = [
            _write_token_plan(
                tmp_path, f'bal-{i}',
                phase_tokens={'2-refine': 1_000, '5-execute': 10_000},
            )
            for i in range(3)
        ]
        heavy = _write_token_plan(
            tmp_path, 'planheavy',
            phase_tokens={'2-refine': 8_000, '4-plan': 8_000, '5-execute': 2_000},
        )
        rows = audit._collect_token_economics_rows([*baseline, heavy])
        thr = audit._derive_token_economics_thresholds(rows)
        heavy_row = next(r for r in rows if r.plan_id == 'planheavy')

        flags = audit._token_economics_flags(heavy_row, thr)

        # ratio 8.0x exceeds the corpus median, annotated against it
        assert any(f.startswith('planning_gt_exec(') and '>median=' in f for f in flags)

    def test_planning_gt_exec_suppressed_for_blind_plan(self, tmp_path: Path):
        # an execute-blind plan must never get planning_gt_exec even
        # though its planning spend is enormous (execute is unmeasured, not zero).
        rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(
                    tmp_path, 'm',
                    phase_tokens={'2-refine': 1_000, '5-execute': 5_000},
                ),
                _write_token_plan(
                    tmp_path, 'blind',
                    phase_tokens={'2-refine': 9_000, '4-plan': 9_000},
                ),
            ]
        )
        thr = audit._derive_token_economics_thresholds(rows)
        blind_row = next(r for r in rows if r.plan_id == 'blind')

        flags = audit._token_economics_flags(blind_row, thr)

        # no planning_gt_exec, but the exec_metrics_blind floor IS present
        assert not any(f.startswith('planning_gt_exec(') for f in flags)
        assert any(f.startswith('exec_metrics_blind(') for f in flags)

    def test_outline_refine_finalize_heavy_fire_at_phase_p75(self, tmp_path: Path):
        # the baseline plans carry a MODEST outline/refine/finalize share
        # (1,000 of 10,000 each = 10%) so each phase-share distribution has genuine
        # spread and its p75 is a positive cut-point set by the corpus, not zero.
        # One plan is dominated by outline+refine+finalize (30% each) so its share
        # lands strictly above each phase's p75. (A corpus where only ONE plan ever
        # touches a phase has no distribution — p75 collapses to zero and the
        # `cut > 0` guard correctly declines to call that lone plan "heavy".)
        light = [
            _write_token_plan(
                tmp_path, f'exec-{i}',
                phase_tokens={
                    '2-refine': 1_000,
                    '3-outline': 1_000,
                    '6-finalize': 1_000,
                    '5-execute': 7_000,
                },
            )
            for i in range(3)
        ]
        heavy = _write_token_plan(
            tmp_path, 'phaseheavy',
            phase_tokens={
                '2-refine': 3_000,
                '3-outline': 3_000,
                '6-finalize': 3_000,
                '5-execute': 1_000,
            },
        )
        rows = audit._collect_token_economics_rows([*light, heavy])
        thr = audit._derive_token_economics_thresholds(rows)
        heavy_row = next(r for r in rows if r.plan_id == 'phaseheavy')

        flags = audit._token_economics_flags(heavy_row, thr)

        # all three phase-heavy flags fire, each annotated against >=p75
        labels = {f.split('(')[0] for f in flags}
        assert {'outline_heavy', 'refine_heavy', 'finalize_heavy'} <= labels
        assert all('>=p75=' in f for f in flags if f.split('(')[0].endswith('_heavy'))

    def test_big_spend_tiny_footprint_fires_on_inversion(self, tmp_path: Path):
        # a plan at/above the corpus median total but with a footprint
        # in the bottom file-count quartile (the tokens/file inversion).
        small_cheap = [
            _write_token_plan(
                tmp_path, f'sm-{i}', files=2, phase_tokens={'5-execute': 1_000}
            )
            for i in range(3)
        ]
        big_tiny = _write_token_plan(
            tmp_path, 'inversion', files=2, phase_tokens={'5-execute': 80_000}
        )
        wide = [
            _write_token_plan(
                tmp_path, f'wide-{i}', files=40, phase_tokens={'5-execute': 5_000}
            )
            for i in range(3)
        ]
        rows = audit._collect_token_economics_rows([*small_cheap, big_tiny, *wide])
        thr = audit._derive_token_economics_thresholds(rows)
        inv_row = next(r for r in rows if r.plan_id == 'inversion')

        flags = audit._token_economics_flags(inv_row, thr)

        assert any(
            f.startswith('big_spend_tiny_footprint(')
            and '>=median=' in f
            and 'p25=' in f
            for f in flags
        )

    def test_long_session_fires_at_message_p75(self, tmp_path: Path):
        # three short sessions, one long one at/above the corpus p75
        short = [
            _write_token_plan(
                tmp_path, f'short-{i}', session_message_count=50,
                phase_tokens={'5-execute': 5_000},
            )
            for i in range(3)
        ]
        long_plan = _write_token_plan(
            tmp_path, 'marathon', session_message_count=900,
            phase_tokens={'5-execute': 5_000},
        )
        rows = audit._collect_token_economics_rows([*short, long_plan])
        thr = audit._derive_token_economics_thresholds(rows)
        long_row = next(r for r in rows if r.plan_id == 'marathon')

        flags = audit._token_economics_flags(long_row, thr)

        # annotated against the floating message-count p75
        assert any(f.startswith('long_session(') and '>=p75=' in f for f in flags)

    def test_exec_metrics_blind_floor_annotation_listed_first(self, tmp_path: Path):
        # an execute-blind plan; the blindness flag must lead the list
        # so the reader knows every downstream number is a floor.
        rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(
                    tmp_path, 'blind', phase_tokens={'2-refine': 4_000, '4-plan': 6_000}
                ),
            ]
        )
        thr = audit._derive_token_economics_thresholds(rows)

        flags = audit._token_economics_flags(rows[0], thr)

        # the blindness annotation is the first flag and names the floors
        assert flags[0].startswith('exec_metrics_blind(5-execute=0;floors:')

    def test_clean_plan_has_no_flags(self, tmp_path: Path):
        # a corpus of identical, unremarkable plans: nothing crosses any
        # corpus-relative cut-point (every plan IS the corpus). Because the
        # distribution is uniform on every dimension, the corpus-relative outlier
        # flags must all suppress: the floor band collapses onto the median (no cheap
        # tail), no plan outspends the median (no big-spend outlier), and no session
        # outlier exists (no plan records a `session_message_count`, so the long-
        # session distribution is empty). A representative member is therefore clean.
        rows = audit._collect_token_economics_rows(
            [
                _write_token_plan(
                    tmp_path, f'clean-{i}', files=10,
                    phase_tokens={'5-execute': 10_000},
                )
                for i in range(5)
            ]
        )
        thr = audit._derive_token_economics_thresholds(rows)

        flags = audit._token_economics_flags(rows[0], thr)

        # a representative corpus member trips none of the anti-patterns
        assert flags == []
