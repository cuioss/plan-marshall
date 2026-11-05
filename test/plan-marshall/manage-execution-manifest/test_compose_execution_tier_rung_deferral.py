# SPDX-License-Identifier: FSL-1.1-ALv2
"""A module whose test build always exceeds the per-task limit builds once per deliverable.

The operator ruling: when a deliverable's per-task ``module-tests`` rung resolves
``orchestrator`` from a MEASURED learned duration above the Bash ceiling, the
deliverable's LAST task in its chain carries the owed rung and the earlier tasks
close without the owed hold. Below the ceiling the rung runs inline on every
task, and an UNMEASURED command keeps today's behaviour — no deferral decision
is recorded, because a duration nobody has measured cannot say the build will
always exceed the limit.

The decision is recorded on the task ladder (`verification.owed_rung`) and
summarised in the manifest (`phase_5.owed_rung_deferral`).
"""

import json
from pathlib import Path

from _manage_execution_manifest_compose_execution_tier_fixtures import (
    _clear_arch_resolve_cache,
    _mem,
)

_MODULE_TESTS_COMMAND = 'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "module-tests plan-marshall"'


def _write_chain(tasks_dir: Path, count: int = 3, deliverable: int = 1) -> list[Path]:
    """Write a linear three-task deliverable chain (TASK-002 depends on 001, …)."""
    tasks_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for number in range(1, count + 1):
        task = {
            'number': number,
            'deliverable': deliverable,
            'depends_on': [f'TASK-{number - 1:03d}'] if number > 1 else [],
            'verification': {'commands': [_MODULE_TESTS_COMMAND]},
        }
        path = tasks_dir / f'TASK-{number:03d}.json'
        path.write_text(json.dumps(task, indent=2) + '\n', encoding='utf-8')
        paths.append(path)
    return paths


def _patch_resolve(monkeypatch, tmp_path: Path, toon: dict) -> list[str]:
    captured: list[str] = []
    monkeypatch.setattr(_mem, 'get_plan_dir', lambda pid: tmp_path)
    monkeypatch.setattr(_mem, '_resolve_command_tier', lambda cmd, pid: dict(toon))
    monkeypatch.setattr(_mem, '_emit_decision_log', lambda pid, msg: captured.append(msg))
    return captured


def _run_routing(plan_id: str = 'rung-fixture') -> dict:
    body: dict = {}
    _mutated, pending = _mem._route_task_verification_commands(plan_id, body)
    _mem._persist_task_rewrites(pending)
    return body


def _read(path: Path) -> dict:
    data: dict = json.loads(path.read_text(encoding='utf-8'))
    return data


class TestMeasuredOverCeilingDefersToTheChainTail:
    def test_exactly_the_last_task_carries_the_chain_tail_rung(self, monkeypatch, tmp_path):
        paths = _write_chain(tmp_path / 'tasks')
        _patch_resolve(
            monkeypatch,
            tmp_path,
            {'execution_tier': 'orchestrator', 'exceeds_bash_ceiling': True},
        )

        body = _run_routing()

        first, second, third = (_read(p) for p in paths)
        # Every task's rung keeps today's orchestrator-tier routing: dropped from
        # the task, the step appended once. Only the DECISION differs.
        assert first['verification']['commands'] == []
        assert first['verification']['owed_rung'] == 'deferred'
        assert second['verification']['commands'] == []
        assert second['verification']['owed_rung'] == 'deferred'
        assert third['verification']['commands'] == []
        assert third['verification']['owed_rung'] == 'chain_tail'

        # The orchestrator runs the step once.
        assert body['phase_5']['verification_steps'] == ['verify:module-tests']
        summary = body['phase_5']['owed_rung_deferral']
        assert len(summary) == 1
        assert summary[0]['deliverable'] == 1
        assert summary[0]['chain_tail_task'] == 3
        assert summary[0]['deferred_task_count'] == 2
        assert summary[0]['cause'] == 'measured_module_tests_above_ceiling'

    def test_recompose_is_stable_on_the_routed_state(self, monkeypatch, tmp_path):
        """A second compose over the persisted state re-derives the same tail."""
        paths = _write_chain(tmp_path / 'tasks')
        _patch_resolve(monkeypatch, tmp_path, {'execution_tier': 'orchestrator', 'exceeds_bash_ceiling': True})
        _run_routing()

        body = _run_routing()

        third = _read(paths[2])
        assert third['verification']['owed_rung'] == 'chain_tail'
        assert body['phase_5']['owed_rung_deferral'][0]['chain_tail_task'] == 3
        # The recorded decision still counts the tasks it covers, even though
        # their rung command was dropped by the first compose.
        assert body['phase_5']['owed_rung_deferral'][0]['deferred_task_count'] == 2

    def test_a_later_task_moves_the_chain_tail_and_restamps_the_old_one(self, monkeypatch, tmp_path):
        """A task added after the first compose becomes the new chain tail.

        The previous tail has no command left to re-measure, so its stamp must be
        rewritten by the decision, not left as a second `chain_tail` — two chain
        tails would hand the same module build back twice.
        """
        paths = _write_chain(tmp_path / 'tasks')
        _patch_resolve(monkeypatch, tmp_path, {'execution_tier': 'orchestrator', 'exceeds_bash_ceiling': True})
        _run_routing()
        assert _read(paths[2])['verification']['owed_rung'] == 'chain_tail'

        # A fourth task joins the deliverable after the previous tail.
        fourth = tmp_path / 'tasks' / 'TASK-004.json'
        fourth.write_text(
            json.dumps(
                {
                    'number': 4,
                    'deliverable': 1,
                    'depends_on': ['TASK-003'],
                    'verification': {'commands': [_MODULE_TESTS_COMMAND]},
                },
                indent=2,
            )
            + '\n',
            encoding='utf-8',
        )
        body = _run_routing()

        stamps = [_read(path)['verification'].get('owed_rung') for path in (*paths, fourth)]
        assert stamps == ['deferred', 'deferred', 'deferred', 'chain_tail']
        assert len([s for s in stamps if s == 'chain_tail']) == 1
        assert body['phase_5']['owed_rung_deferral'][0]['chain_tail_task'] == 4


class TestTheUnchangedArms:
    def test_below_the_ceiling_every_task_keeps_the_rung(self, monkeypatch, tmp_path):
        """Measured below the ceiling: the rung runs inline on all three tasks."""
        paths = _write_chain(tmp_path / 'tasks')
        _patch_resolve(
            monkeypatch,
            tmp_path,
            {'execution_tier': 'per_task', 'exceeds_bash_ceiling': False, 'bash_timeout_seconds': 300},
        )

        body = _run_routing()

        for path in paths:
            task = _read(path)
            assert task['verification']['commands'] == [_MODULE_TESTS_COMMAND]
            assert 'owed_rung' not in task['verification']
            assert task['verification']['bash_timeout_seconds'] == 300
        assert 'owed_rung_deferral' not in body['phase_5']

    def test_unmeasured_records_no_deferral_decision(self, monkeypatch, tmp_path):
        """Unmeasured fails closed to `orchestrator`, but nothing was measured.

        No deferral is recorded, and today's routing is untouched: each task's
        rung is dropped and the canonical step is appended once, with no stamp on
        any task. This is the arm the spec's bullet 3 pins ("A command key with no
        measurement keeps today's behaviour"); it is also the arm whose Done-when
        wording ("puts it on all three") cannot hold, because that routing is what
        today's behaviour IS.
        """
        paths = _write_chain(tmp_path / 'tasks')
        _patch_resolve(
            monkeypatch,
            tmp_path,
            {'execution_tier': 'orchestrator', 'exceeds_bash_ceiling': False},
        )

        body = _run_routing()

        for path in paths:
            task = _read(path)
            assert task['verification']['commands'] == []
            assert 'owed_rung' not in task['verification']
        assert body['phase_5']['verification_steps'] == ['verify:module-tests']
        assert 'owed_rung_deferral' not in body['phase_5']

    def test_a_stale_stamp_is_cleared_when_the_tier_moves_back_to_per_task(self, monkeypatch, tmp_path):
        """A re-compose that measures below the limit must not leave a deferral behind."""
        paths = _write_chain(tmp_path / 'tasks')
        _patch_resolve(monkeypatch, tmp_path, {'execution_tier': 'orchestrator', 'exceeds_bash_ceiling': True})
        _run_routing()
        assert _read(paths[0])['verification']['owed_rung'] == 'deferred'

        _patch_resolve(
            monkeypatch,
            tmp_path,
            {'execution_tier': 'per_task', 'exceeds_bash_ceiling': False, 'bash_timeout_seconds': 300},
        )
        _run_routing()

        assert 'owed_rung' not in _read(paths[0])['verification']
        # Neither the stamp nor the recorded rung survives: the decision is gone,
        # and the rung command itself was routed away by today's routing.
        assert 'owed_rung_command' not in _read(paths[0])['verification']
        assert _read(paths[0])['verification']['commands'] == []


class TestTheManifestKeepsOneTailCommandPerDeliverable:
    """A task carrying two modules' rungs records one rung and one tail."""

    _MODULE_A = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        'run --command-args "module-tests plan-marshall"'
    )
    _MODULE_B = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        'run --command-args "module-tests marketplace"'
    )

    def _write_tasks(self, tasks_dir: Path, tasks: list[dict]) -> list[Path]:
        tasks_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for task in tasks:
            path = tasks_dir / f'TASK-{task["number"]:03d}.json'
            path.write_text(json.dumps(task, indent=2) + '\n', encoding='utf-8')
            paths.append(path)
        return paths

    def _patch_by_command(self, monkeypatch, tmp_path: Path, by_command: dict[str, dict]) -> None:
        def _resolve(command: str, _plan_id: str) -> dict:
            return dict(by_command[command])

        monkeypatch.setattr(_mem, 'get_plan_dir', lambda pid: tmp_path)
        monkeypatch.setattr(_mem, '_resolve_command_tier', _resolve)
        monkeypatch.setattr(_mem, '_emit_decision_log', lambda pid, msg: None)

    def test_a_second_rung_command_does_not_overwrite_the_first(self, monkeypatch, tmp_path):
        """Both modules name the same task their tail; the field keeps the first."""
        over_ceiling = {'execution_tier': 'orchestrator', 'exceeds_bash_ceiling': True}
        paths = self._write_tasks(
            tmp_path / 'tasks',
            [
                {
                    'number': 1,
                    'deliverable': 1,
                    'depends_on': [],
                    'verification': {'commands': [self._MODULE_A]},
                },
                {
                    'number': 2,
                    'deliverable': 1,
                    'depends_on': ['TASK-001'],
                    'verification': {'commands': [self._MODULE_A, self._MODULE_B]},
                },
            ],
        )
        self._patch_by_command(monkeypatch, tmp_path, {self._MODULE_A: over_ceiling, self._MODULE_B: over_ceiling})

        body = _run_routing()

        first, second = (_read(path) for path in paths)
        assert first['verification']['owed_rung'] == 'deferred'
        assert second['verification']['owed_rung'] == 'chain_tail'
        assert second['verification']['owed_rung_command'] == self._MODULE_A, (
            'the later command of the same task must not overwrite the recorded rung'
        )
        stamps = [first['verification']['owed_rung'], second['verification']['owed_rung']]
        assert stamps.count('chain_tail') == 1
        # The candidate pass takes the task's FIRST rung command, so the group is
        # the one the decision was taken on — one record, one tail.
        assert [record['chain_tail_task'] for record in body['phase_5']['owed_rung_deferral']] == [2]

    def test_a_remeasured_module_clears_only_its_own_stamps(self, monkeypatch, tmp_path):
        """Staleness is per (deliverable, command), so module A survives module B."""
        over_ceiling = {'execution_tier': 'orchestrator', 'exceeds_bash_ceiling': True}
        per_task = {'execution_tier': 'per_task', 'exceeds_bash_ceiling': False, 'bash_timeout_seconds': 300}
        paths = self._write_tasks(
            tmp_path / 'tasks',
            [
                {
                    'number': 1,
                    'deliverable': 1,
                    'depends_on': [],
                    'verification': {'commands': [self._MODULE_A]},
                },
                {
                    'number': 2,
                    'deliverable': 1,
                    'depends_on': ['TASK-001'],
                    'verification': {'commands': [self._MODULE_B]},
                },
            ],
        )
        self._patch_by_command(monkeypatch, tmp_path, {self._MODULE_A: over_ceiling, self._MODULE_B: over_ceiling})
        _run_routing()
        assert _read(paths[1])['verification']['owed_rung'] == 'chain_tail'

        self._patch_by_command(monkeypatch, tmp_path, {self._MODULE_A: over_ceiling, self._MODULE_B: per_task})
        _run_routing()

        first, second = (_read(path) for path in paths)
        assert first['verification']['owed_rung'] == 'chain_tail', 'module A is still over the ceiling'
        assert 'owed_rung' not in second['verification'], "module B's stale stamp must be cleared"
        assert 'owed_rung_command' not in second['verification']

    def test_a_group_ordered_through_an_outside_task_puts_the_tail_last(self, monkeypatch, tmp_path):
        """A dependency chain through a non-group task still orders the group."""
        over_ceiling = {'execution_tier': 'orchestrator', 'exceeds_bash_ceiling': True}
        paths = self._write_tasks(
            tmp_path / 'tasks',
            [
                {
                    'number': 1,
                    'deliverable': 1,
                    'depends_on': ['TASK-002'],
                    'verification': {'commands': [self._MODULE_A]},
                },
                {'number': 2, 'deliverable': 2, 'depends_on': ['TASK-003'], 'verification': {'commands': []}},
                {
                    'number': 3,
                    'deliverable': 1,
                    'depends_on': [],
                    'verification': {'commands': [self._MODULE_A]},
                },
            ],
        )
        self._patch_by_command(monkeypatch, tmp_path, {self._MODULE_A: over_ceiling})

        body = _run_routing()

        task_one, _outside, task_three = (_read(path) for path in paths)
        assert body['phase_5']['owed_rung_deferral'][0]['chain_tail_task'] == 1
        assert task_one['verification']['owed_rung'] == 'chain_tail'
        assert task_three['verification']['owed_rung'] == 'deferred'


class TestTheLeafHonoursTheRecordedDecision:
    """The leaf-side rule is documented where the leaf reads it."""

    _REPO_ROOT = Path(__file__).resolve().parents[3]

    def test_execute_task_names_the_stamp_and_both_values(self):
        text = (
            self._REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'execute-task' / 'SKILL.md'
        ).read_text(encoding='utf-8')

        assert 'verification.owed_rung' in text
        assert 'chain_tail' in text and 'deferred' in text
        assert 'WITHOUT `--verification-owed`' in text

    def test_manifest_skill_documents_the_deferral(self):
        text = (
            self._REPO_ROOT
            / 'marketplace'
            / 'bundles'
            / 'plan-marshall'
            / 'skills'
            / 'manage-execution-manifest'
            / 'SKILL.md'
        ).read_text(encoding='utf-8')

        assert 'owed_rung_deferral' in text
        assert 'one full module build per deliverable' in text
