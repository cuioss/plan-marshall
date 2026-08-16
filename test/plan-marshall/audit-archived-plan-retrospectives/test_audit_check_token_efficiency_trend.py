#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``cross_token_trend`` positive path — the corpus token trend and the verdict it
reports.
"""

from pathlib import Path

from _audit_fixtures import audit


class TestTokenTrendCore:
    """``cross_token_trend`` orders plans chronologically and flags a sustained
    upward trend in tokens-per-phase across the corpus."""

    def test_upward_trend_flags_regression(self, tmp_path: Path):
        # six plans (date-prefixed for chronological ordering) whose
        # tokens-per-phase climb steeply from first third to last third.
        import json as _json

        all_inputs = []
        token_totals = [1000, 1100, 1200, 4000, 4500, 5000]
        for idx, total in enumerate(token_totals):
            plan_id = f'2026-05-{idx + 10:02d}-trend'
            plan_dir = tmp_path / '.plan' / 'temp' / 'tt-corpus' / plan_id
            work_dir = plan_dir / 'work'
            work_dir.mkdir(parents=True, exist_ok=True)
            (work_dir / 'metrics.toon').write_text(
                f'[5-execute]\n  total_tokens: {total}\n', encoding='utf-8'
            )
            (plan_dir / 'references.json').write_text(
                _json.dumps({}), encoding='utf-8'
            )
            all_inputs.append(audit.collect_inputs(plan_dir))

        result = audit.cross_token_trend(all_inputs)

        # first-third mean ~1000, last-third mean ~5000 → regression flagged
        assert result['plans_in_series'] == 6
        assert result['regression'] != ''
        assert 'rose' in result['regression']

    def test_flat_trend_no_regression(self, tmp_path: Path):
        # six plans all at the same tokens-per-phase.
        import json as _json

        all_inputs = []
        for idx in range(6):
            plan_id = f'2026-05-{idx + 10:02d}-flat'
            plan_dir = tmp_path / '.plan' / 'temp' / 'tt-corpus' / plan_id
            work_dir = plan_dir / 'work'
            work_dir.mkdir(parents=True, exist_ok=True)
            (work_dir / 'metrics.toon').write_text(
                '[5-execute]\n  total_tokens: 1000\n', encoding='utf-8'
            )
            (plan_dir / 'references.json').write_text(
                _json.dumps({}), encoding='utf-8'
            )
            all_inputs.append(audit.collect_inputs(plan_dir))

        result = audit.cross_token_trend(all_inputs)

        # no rise → empty regression
        assert result['plans_in_series'] == 6
        assert result['regression'] == ''

    def test_fewer_than_three_plans_no_regression(self, tmp_path: Path):
        # only two plans; the regression rule needs >= 3.
        import json as _json

        all_inputs = []
        for idx, total in enumerate([1000, 9000]):
            plan_id = f'2026-05-{idx + 10:02d}-short'
            plan_dir = tmp_path / '.plan' / 'temp' / 'tt-corpus' / plan_id
            work_dir = plan_dir / 'work'
            work_dir.mkdir(parents=True, exist_ok=True)
            (work_dir / 'metrics.toon').write_text(
                f'[5-execute]\n  total_tokens: {total}\n', encoding='utf-8'
            )
            (plan_dir / 'references.json').write_text(
                _json.dumps({}), encoding='utf-8'
            )
            all_inputs.append(audit.collect_inputs(plan_dir))

        result = audit.cross_token_trend(all_inputs)

        # under the 3-plan floor, regression stays empty
        assert result['plans_in_series'] == 2
        assert result['regression'] == ''

    def test_plan_without_metrics_excluded_from_series(self, tmp_path: Path):
        # one plan has no metrics.toon and must be skipped.
        import json as _json

        all_inputs = []
        # two plans WITH metrics
        for idx in range(2):
            plan_id = f'2026-05-{idx + 10:02d}-has'
            plan_dir = tmp_path / '.plan' / 'temp' / 'tt-corpus' / plan_id
            work_dir = plan_dir / 'work'
            work_dir.mkdir(parents=True, exist_ok=True)
            (work_dir / 'metrics.toon').write_text(
                '[5-execute]\n  total_tokens: 1000\n', encoding='utf-8'
            )
            (plan_dir / 'references.json').write_text(
                _json.dumps({}), encoding='utf-8'
            )
            all_inputs.append(audit.collect_inputs(plan_dir))
        # one plan WITHOUT metrics
        bare_dir = tmp_path / '.plan' / 'temp' / 'tt-corpus' / '2026-05-20-bare'
        bare_dir.mkdir(parents=True, exist_ok=True)
        (bare_dir / 'references.json').write_text(_json.dumps({}), encoding='utf-8')
        all_inputs.append(audit.collect_inputs(bare_dir))

        result = audit.cross_token_trend(all_inputs)

        # only the two metric-bearing plans land in the series
        assert result['plans_in_series'] == 2
        assert all(r['plan_id'].endswith('-has') for r in result['rows'])
