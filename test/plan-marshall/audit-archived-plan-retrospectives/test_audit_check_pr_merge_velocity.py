#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``pr-merge-velocity`` — the merge-latency verdict over archived plans carrying a
PR record, and the absent-record case.
"""

from pathlib import Path
from typing import Any

from _audit_fixtures import audit


def _write_velocity_plan(
    repo_root: Path,
    plan_id: str,
    runs: list[tuple[str, str | None, str | None]],
) -> Any:
    """Materialise a plan dir with ``artifacts/ci-runs/{run}/manifest.toon`` files.

    ``runs`` is a list of ``(run_subdir, pr_number, fetched_at)`` tuples; each
    tuple writes one manifest. A ``None`` pr_number / fetched_at omits that scalar
    line. ``check_pr_merge_velocity`` takes the min fetched_at as PR-open and the
    max as merge, computing the open-to-merge elapsed hours.
    """
    plan_dir = repo_root / '.plan' / 'temp' / 'velocity-corpus' / plan_id
    ci_runs = plan_dir / 'artifacts' / 'ci-runs'
    for run_subdir, pr_number, fetched_at in runs:
        run_dir = ci_runs / run_subdir
        run_dir.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        if pr_number is not None:
            lines.append(f'pr_number: {pr_number}')
        if fetched_at is not None:
            lines.append(f'fetched_at: {fetched_at}')
        (run_dir / 'manifest.toon').write_text(
            '\n'.join(lines) + '\n', encoding='utf-8'
        )
    return audit.collect_inputs(plan_dir)


class TestCheckPrMergeVelocity:
    """``check_pr_merge_velocity`` computes open-to-merge elapsed hours from the
    ci-runs manifests and flags review cycles over the 24h threshold."""

    def test_no_ci_runs_marks_inapplicable(self, tmp_path: Path):
        # a plan dir with no artifacts/ci-runs at all.
        plan_dir = tmp_path / '.plan' / 'temp' / 'velocity-corpus' / 'no-runs'
        plan_dir.mkdir(parents=True, exist_ok=True)
        inputs = audit.collect_inputs(plan_dir)

        result = audit.check_pr_merge_velocity(inputs)

        # no manifests → inapplicable, never flagged
        assert result['applicable'] == 'false'
        assert result['flagged'] == ''
        assert result['elapsed_hours'] == ''

    def test_fast_review_cycle_not_flagged(self, tmp_path: Path):
        # open 10:00, merge 12:00 same day → 2.0h, under the 24h ceiling.
        inputs = _write_velocity_plan(
            tmp_path,
            'fast',
            [
                ('run-1', '101', '2026-05-30T10:00:00Z'),
                ('run-2', '101', '2026-05-30T12:00:00Z'),
            ],
        )

        result = audit.check_pr_merge_velocity(inputs)

        assert result['applicable'] == 'true'
        assert result['pr_number'] == '101'
        assert result['elapsed_hours'] == '2.0'
        assert result['flagged'] == ''

    def test_slow_review_cycle_flagged(self, tmp_path: Path):
        # open 09:00 on the 28th, merge 09:00 on the 30th → 48.0h > 24h.
        inputs = _write_velocity_plan(
            tmp_path,
            'slow',
            [
                ('run-1', '202', '2026-05-28T09:00:00Z'),
                ('run-2', '202', '2026-05-30T09:00:00Z'),
            ],
        )

        result = audit.check_pr_merge_velocity(inputs)

        # 48h exceeds the 24h ceiling
        assert result['elapsed_hours'] == '48.0'
        assert result['flagged'] == 'true'

    def test_boundary_exactly_at_threshold_not_flagged(self, tmp_path: Path):
        # exactly 24.0h elapsed; the flag is a strict ``>`` comparison.
        inputs = _write_velocity_plan(
            tmp_path,
            'boundary',
            [
                ('run-1', '303', '2026-05-29T00:00:00Z'),
                ('run-2', '303', '2026-05-30T00:00:00Z'),
            ],
        )

        result = audit.check_pr_merge_velocity(inputs)

        # 24.0h is NOT > 24.0 → not flagged
        assert result['elapsed_hours'] == '24.0'
        assert result['flagged'] == ''

    def test_missing_pr_number_marks_inapplicable(self, tmp_path: Path):
        # manifests carry timestamps but no pr_number scalar.
        inputs = _write_velocity_plan(
            tmp_path,
            'no-pr',
            [
                ('run-1', None, '2026-05-28T09:00:00Z'),
                ('run-2', None, '2026-05-30T09:00:00Z'),
            ],
        )

        result = audit.check_pr_merge_velocity(inputs)

        # without a pr_number the check is inapplicable
        assert result['applicable'] == 'false'
        assert result['pr_number'] == ''

    def test_min_and_max_span_across_three_manifests(self, tmp_path: Path):
        # three runs; open is the earliest, merge the latest fetched_at.
        inputs = _write_velocity_plan(
            tmp_path,
            'span',
            [
                ('run-1', '404', '2026-05-30T08:00:00Z'),
                ('run-2', '404', '2026-05-30T20:00:00Z'),
                ('run-3', '404', '2026-05-30T14:00:00Z'),
            ],
        )

        result = audit.check_pr_merge_velocity(inputs)

        # 08:00 → 20:00 = 12.0h, under the ceiling
        assert result['elapsed_hours'] == '12.0'
        assert result['flagged'] == ''
