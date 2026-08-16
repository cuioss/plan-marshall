#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``task-count`` efficiency — the per-plan task-count verdict and its thresholds.
"""

from pathlib import Path
from typing import Any

from _audit_fixtures import audit


def _write_task_count_plan(
    repo_root: Path,
    plan_id: str,
    *,
    task_count: int,
    deliverables: list[Any] | None = None,
    task_deliverable_ids: list[Any] | None = None,
) -> Any:
    """Materialise a plan dir carrying ``tasks/TASK-*.json`` + ``references.json``.

    ``check_task_count`` globs ``tasks/TASK-*.json`` and resolves the deliverable
    count via ``_deliverable_count`` (``references.json::deliverables`` first, then
    the distinct ``deliverable`` ids referenced by tasks). ``deliverables`` seeds
    the explicit list; ``task_deliverable_ids`` seeds the per-task fallback ids.
    """
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'tc-corpus' / plan_id
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    for n in range(1, task_count + 1):
        body: dict[str, Any] = {}
        if task_deliverable_ids is not None and n - 1 < len(task_deliverable_ids):
            body['deliverable'] = task_deliverable_ids[n - 1]
        (tasks_dir / f'TASK-{n:03d}.json').write_text(
            _json.dumps(body), encoding='utf-8'
        )
    refs: dict[str, Any] = {}
    if deliverables is not None:
        refs['deliverables'] = deliverables
    (plan_dir / 'references.json').write_text(_json.dumps(refs), encoding='utf-8')
    return audit.collect_inputs(plan_dir)


class TestCheckTaskCount:
    """``check_task_count`` flags under- and over-decomposition relative to the
    deliverable count, derives deliverables from references or the task fallback,
    and stays silent when no deliverables exist."""

    def test_balanced_ratio_not_flagged(self, tmp_path: Path):
        # 4 tasks over 2 deliverables → ratio 2.0, inside [0.5, 4.0].
        inputs = _write_task_count_plan(
            tmp_path, 'balanced', task_count=4, deliverables=['d1', 'd2']
        )

        result = audit.check_task_count(inputs)

        assert result['task_count'] == 4
        assert result['deliverable_count'] == 2
        assert result['outlier'] == ''

    def test_under_decomposition_flagged(self, tmp_path: Path):
        # 2 tasks over 8 deliverables → ratio 0.25 < 0.5.
        inputs = _write_task_count_plan(
            tmp_path,
            'under',
            task_count=2,
            deliverables=[f'd{i}' for i in range(8)],
        )

        result = audit.check_task_count(inputs)

        assert 'under_decomposed' in result['outlier']
        assert 'ratio=0.25' in result['outlier']

    def test_over_decomposition_flagged(self, tmp_path: Path):
        # 10 tasks over 2 deliverables → ratio 5.0 > 4.0.
        inputs = _write_task_count_plan(
            tmp_path, 'over', task_count=10, deliverables=['d1', 'd2']
        )

        result = audit.check_task_count(inputs)

        assert 'over_decomposed' in result['outlier']
        assert 'ratio=5.00' in result['outlier']

    def test_deliverables_derived_from_tasks_when_absent_in_references(
        self, tmp_path: Path
    ):
        # references.json has no deliverables list; the per-task
        # ``deliverable`` ids supply the distinct-count fallback (2 distinct ids).
        inputs = _write_task_count_plan(
            tmp_path,
            'task-fallback',
            task_count=2,
            deliverables=None,
            task_deliverable_ids=[7, 9],
        )

        result = audit.check_task_count(inputs)

        # distinct ids {7, 9} → 2 deliverables, ratio 1.0, not flagged
        assert result['deliverable_count'] == 2
        assert result['outlier'] == ''

    def test_zero_deliverables_short_circuits_no_flag(self, tmp_path: Path):
        # tasks present but no deliverables list and no task ids.
        inputs = _write_task_count_plan(
            tmp_path,
            'no-deliverables',
            task_count=3,
            deliverables=None,
            task_deliverable_ids=None,
        )

        result = audit.check_task_count(inputs)

        # deliverable_count 0 → ratio guard skipped, never flagged
        assert result['deliverable_count'] == 0
        assert result['outlier'] == ''

    def test_no_tasks_dir_reports_zero(self, tmp_path: Path):
        # a plan dir with references.json but no tasks/ directory.
        import json as _json

        plan_dir = tmp_path / '.plan' / 'temp' / 'tc-corpus' / 'no-tasks'
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / 'references.json').write_text(
            _json.dumps({'deliverables': ['d1']}), encoding='utf-8'
        )
        inputs = audit.collect_inputs(plan_dir)

        result = audit.check_task_count(inputs)

        # missing tasks/ → 0 tasks; ratio 0.0 < 0.5 → under_decomposed
        assert result['task_count'] == 0
        assert 'under_decomposed' in result['outlier']
