#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``task-graph-redundancy`` — repeated heavy build commands and duplicated write
targets across a plan's task graph are detected and threshold-gated.
"""

from pathlib import Path
from typing import Any

from _audit_fixtures import audit

_HEAVY_BUILD_CMD = (
    'python3 .plan/execute-script.py '
    'plan-marshall:build-pyproject:pyproject_build run '
    '--command-args "module-tests plan-marshall"'
)


_LIGHT_CMD = (
    'python3 .plan/execute-script.py '
    'plan-marshall:manage-tasks:manage-tasks list --plan-id p'
)


def _write_task_graph_plan(
    repo_root: Path,
    plan_id: str,
    tasks: list[dict[str, Any]],
) -> Any:
    """Materialise a plan dir with ``tasks/TASK-NNN.json`` and return PlanInputs.

    Each entry in ``tasks`` is a task dict (``number`` / ``profile`` /
    ``deliverable`` / ``steps`` / ``verification`` keys as the test needs). The
    files are written under ``{repo_root}/.plan/temp/tgr-corpus/{plan_id}/tasks``
    (never the live ``.plan/local`` tree). ``check_task_graph_redundancy`` reads
    only ``plan_dir`` from disk, so the returned instance is constructed directly.
    """
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'tgr-corpus' / plan_id
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    for t in tasks:
        number = int(t['number'])
        (tasks_dir / f'TASK-{number:03d}.json').write_text(
            _json.dumps(t), encoding='utf-8'
        )
    return audit.PlanInputs(plan_id=plan_id, plan_dir=plan_dir)


def _step(target: str, intent: str = 'write-replace') -> dict[str, Any]:
    return {'target': target, 'intent': intent}


def _task(
    number: int,
    *,
    profile: str = 'implementation',
    deliverable: int = 1,
    targets: list[str] | None = None,
    steps: list[dict[str, Any]] | None = None,
    commands: list[str] | None = None,
) -> dict[str, Any]:
    """Build a minimal TASK dict for the task-graph fixture."""
    if steps is None:
        steps = [_step(tgt) for tgt in (targets or [])]
    return {
        'number': number,
        'profile': profile,
        'deliverable': deliverable,
        'steps': steps,
        'verification': {'commands': commands or []},
    }


class TestTaskGraphRedundancy:
    """The five redundancy signals over a reconstructed task graph."""

    def test_duplicate_task_and_in_task_build_both_genuine(self, tmp_path: Path):
        # two tasks edit the SAME file (multi_task_file) and one bakes a
        # HEAVY build into its verification (in_task_build).
        inputs = _write_task_graph_plan(
            tmp_path,
            'p-dup-build',
            [
                _task(1, targets=['src/foo.py']),
                _task(
                    2,
                    targets=['src/foo.py'],
                    commands=[_HEAVY_BUILD_CMD],
                ),
            ],
        )

        row = audit.check_task_graph_redundancy(inputs)

        # both signals populated, and the row is genuine
        assert row['multi_task_file'] == 'src/foo.py'
        assert 'T2:module-tests plan-marshall' in row['in_task_build']
        assert audit._task_graph_redundancy_genuine(row) is True

    def test_clean_plan_flags_none_and_is_informational(self, tmp_path: Path):
        # distinct targets, a single light verification, balanced fanout
        inputs = _write_task_graph_plan(
            tmp_path,
            'p-clean',
            [
                _task(1, deliverable=1, targets=['src/a.py'], commands=[_LIGHT_CMD]),
                _task(2, deliverable=2, targets=['src/b.py']),
            ],
        )

        rows = [audit.check_task_graph_redundancy(inputs)]
        # deliverable_fanout needs the corpus median stamped
        audit._finalize_deliverable_fanout(rows)
        row = rows[0]

        # every signal empty; informational
        assert row['multi_task_file'] == ''
        assert row['dup_substep'] == ''
        assert row['in_task_build'] == ''
        assert row['verif_task_fanout'] == ''
        assert row['deliverable_fanout'] == ''
        assert audit._task_graph_redundancy_genuine(row) is False

    def test_dup_substep_same_target_intent_in_two_tasks(self, tmp_path: Path):
        # the SAME (target, intent) baked into two tasks
        inputs = _write_task_graph_plan(
            tmp_path,
            'p-dupstep',
            [
                _task(1, steps=[_step('src/x.py', 'refactor')]),
                _task(2, steps=[_step('src/x.py', 'refactor')]),
            ],
        )

        row = audit.check_task_graph_redundancy(inputs)

        # the (target, intent) pair is surfaced
        assert 'src/x.py [refactor]' in row['dup_substep']
        assert audit._task_graph_redundancy_genuine(row) is True

    def test_verif_task_fanout_more_than_one_test_task(self, tmp_path: Path):
        # two test/verification tasks (a collapse candidate)
        inputs = _write_task_graph_plan(
            tmp_path,
            'p-fanout',
            [
                _task(1, profile='implementation', targets=['src/a.py']),
                _task(2, profile='module_testing', targets=['test/a.py']),
                _task(3, profile='verification', targets=['test/b.py']),
            ],
        )

        row = audit.check_task_graph_redundancy(inputs)

        # both test/verification task numbers listed
        assert row['verif_task_fanout'] == '2;3'
        assert audit._task_graph_redundancy_genuine(row) is True

    def test_deliverable_fanout_against_per_run_median(self, tmp_path: Path):
        # a corpus where one plan's per-deliverable task count is a high
        # outlier relative to the per-run median. The lean plans set a low median
        # (1 task/deliverable) so the threshold is max(3, 1*2)=3; the busy plan's
        # single deliverable carries 4 tasks (>=3 → flagged).
        lean_a = audit.check_task_graph_redundancy(
            _write_task_graph_plan(
                tmp_path, 'lean-a', [_task(1, deliverable=1, targets=['a.py'])]
            )
        )
        lean_b = audit.check_task_graph_redundancy(
            _write_task_graph_plan(
                tmp_path, 'lean-b', [_task(1, deliverable=1, targets=['b.py'])]
            )
        )
        busy = audit.check_task_graph_redundancy(
            _write_task_graph_plan(
                tmp_path,
                'busy',
                [
                    _task(1, deliverable=1, targets=['c1.py']),
                    _task(2, deliverable=1, targets=['c2.py']),
                    _task(3, deliverable=1, targets=['c3.py']),
                    _task(4, deliverable=1, targets=['c4.py']),
                ],
            )
        )
        rows = [lean_a, lean_b, busy]

        threshold = audit._finalize_deliverable_fanout(rows)

        # threshold is the corpus floor; only the busy plan is flagged
        assert threshold == 3
        assert lean_a['deliverable_fanout'] == ''
        assert lean_b['deliverable_fanout'] == ''
        assert busy['deliverable_fanout'] != ''
        assert audit._task_graph_redundancy_genuine(busy) is True

    def test_is_heavy_build_cmd_distinguishes_heavy_from_light(self):
        # Heavy: a build runner + a HEAVY token
        assert audit.is_heavy_build_cmd(_HEAVY_BUILD_CMD) is True
        # Heavy: full-suite verify verb
        assert audit.is_heavy_build_cmd(
            'pyproject_build run --command-args "verify plan-marshall"'
        ) is True
        # Light: a manage-* call is never a heavy build
        assert audit.is_heavy_build_cmd(_LIGHT_CMD) is False

    def test_check_registered_in_check_names_only(self):
        # Per-plan check: in CHECK_NAMES, NOT in CROSS_PLAN_CHECKS
        assert 'task-graph-redundancy' in audit.CHECK_NAMES
        assert 'task-graph-redundancy' not in audit.CROSS_PLAN_CHECKS

    def test_emit_block_shape_and_severity_column(self, tmp_path: Path):
        # one genuine plan (multi_task_file) + one clean plan
        genuine = audit.check_task_graph_redundancy(
            _write_task_graph_plan(
                tmp_path,
                'g',
                [
                    _task(1, targets=['src/dup.py']),
                    _task(2, targets=['src/dup.py']),
                ],
            )
        )
        clean = audit.check_task_graph_redundancy(
            _write_task_graph_plan(
                tmp_path, 'c', [_task(1, deliverable=1, targets=['src/solo.py'])]
            )
        )
        rows = [genuine, clean]
        threshold = audit._finalize_deliverable_fanout(rows)

        block = audit.emit_task_graph_redundancy_block(rows, threshold)

        # header, corpus totals, column header, and severity cells
        assert 'check: task-graph-redundancy' in block
        assert 'status: success' in block
        assert 'plans_scanned: 2' in block
        assert 'multi_task_file_plans: 1' in block
        assert f'deliverable_fanout_threshold: {threshold}' in block
        assert 'genuine_signal_count: 1' in block
        assert (
            'rows[2]{plan_id,tasks,multi_task_file,dup_substep,in_task_build,'
            'verif_task_fanout,deliverable_fanout,severity}' in block
        )
        # the genuine plan's row ends in ,genuine; the clean one in ,informational
        assert ',genuine' in block
        assert ',informational' in block
