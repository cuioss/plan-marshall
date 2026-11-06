#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The unmeasured arm leaves the per-task owed hold on EVERY task of the group.

The compose-time decision records which task owns a deliverable's owed rung
(`verification.owed_rung`). Its unmeasured arm — a configured `module-tests`
command that has never been observed, so the live resolve fails closed to
`orchestrator` without a measured over-ceiling stamp — places NOTHING: no
`owed_rung` stamp is written, so every task of the group runs its own rung and
hands it back, and each close legitimately opens its own owed hold. The measured
over-ceiling arm is the opposite shape: exactly one `chain_tail` task owns the
build and the earlier `deferred` tasks close without a hold.

This is the leaf side of the contract defined once in
``manage-execution-manifest/SKILL.md`` § "Deliverable chain-tail rung deferral".
A leaf that honoured the hold on a single task (a "one owed build per group"
stub) would pass the over-ceiling control and fail the unmeasured case, which is
what makes the pair a discriminating fixture rather than a restatement.
"""

import json
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

_step = load_script_module('plan-marshall', 'manage-tasks', '_cmd_step.py', register=False)

_GROUP_SIZE = 3
_RUNG_COMMAND = (
    'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
    'run --command-args "module-tests plan-marshall"'
)


def _write_task(plan_dir: Path, number: int, *, owed_rung: str | None = None) -> Path:
    """Write one composed task, optionally carrying a rung stamp."""
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    verification: dict = {'commands': []}
    if owed_rung is not None:
        verification['owed_rung'] = owed_rung
        verification['owed_rung_command'] = _RUNG_COMMAND
    task = {
        'number': number,
        'title': f'Group task {number}',
        'status': 'pending',
        'deliverable': 1,
        'depends_on': [f'TASK-{number - 1:03d}'] if number > 1 else [],
        'steps': [{'number': 1, 'target': f'src/File{number}.py', 'intent': 'write-new', 'status': 'pending'}],
        'verification': verification,
    }
    path = tasks_dir / f'TASK-{number:03d}.json'
    path.write_text(json.dumps(task, indent=2) + '\n', encoding='utf-8')
    return path


def _close(plan_id: str, number: int, *, owed: bool) -> dict:
    """Close one task's last step, optionally asking for the owed hold."""
    return _step.cmd_finalize_step(
        Namespace(
            plan_id=plan_id,
            task_number=number,
            step=1,
            outcome='done',
            reason=None,
            verification_owed=owed,
            verification_complete=False,
        )
    )


def _persisted(plan_dir: Path, number: int) -> dict:
    return json.loads((plan_dir / 'tasks' / f'TASK-{number:03d}.json').read_text(encoding='utf-8'))


class TestTheUnmeasuredArmHoldsOnEveryTaskOfTheGroup:
    """No stamp: each task hands its own orchestrator-tier rung back."""

    def test_each_task_opens_its_own_hold(self, plan_context):
        plan_id = 'unmeasured-rung-hold'
        plan_dir = plan_context.plan_dir_for(plan_id)
        for number in range(1, _GROUP_SIZE + 1):
            _write_task(plan_dir, number)

        for number in range(1, _GROUP_SIZE + 1):
            result = _close(plan_id, number, owed=True)

            assert result['status'] == 'success'
            assert result['task_complete'] is False
            assert result['verification_owed'] is True

        persisted = [_persisted(plan_dir, number) for number in range(1, _GROUP_SIZE + 1)]
        assert [task['status'] for task in persisted] == ['in_progress'] * _GROUP_SIZE
        assert all(task['verification_owed'] is True for task in persisted), (
            'the unmeasured arm must leave the hold on every task, not on one'
        )


class TestTheMeasuredOverCeilingArmDefersToTheChainTail:
    """A stamped group opens exactly one hold — on its chain tail."""

    def test_only_the_chain_tail_opens_a_hold(self, plan_context):
        plan_id = 'measured-rung-hold'
        plan_dir = plan_context.plan_dir_for(plan_id)
        _write_task(plan_dir, 1, owed_rung='deferred')
        _write_task(plan_dir, 2, owed_rung='deferred')
        _write_task(plan_dir, 3, owed_rung='chain_tail')

        for number in (1, 2):
            dropped = _close(plan_id, number, owed=True)

            assert dropped['status'] == 'success'
            assert dropped['task_complete'] is True
            assert dropped['owed_rung_deferred_dropped'] is True
            assert _persisted(plan_dir, number)['status'] == 'done'

        held = _close(plan_id, 3, owed=True)

        assert held['verification_owed'] is True
        assert _persisted(plan_dir, 3)['status'] == 'in_progress'


class TestTheContractIsDefinedOnceAndTheLeafPointsAtIt:
    _REPO_ROOT = Path(__file__).resolve().parents[3]
    _MANIFEST_SKILL = (
        _REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-execution-manifest' / 'SKILL.md'
    )
    _EXECUTE_TASK_SKILL = (
        _REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'execute-task' / 'SKILL.md'
    )

    def test_the_definition_appears_once_in_the_manifest_skill(self):
        text = self._MANIFEST_SKILL.read_text(encoding='utf-8')

        assert text.count('The owed rung — one definition.') == 1
        # The three arms are stated, including what the unmeasured one places.
        assert 'unmeasured (configured, never observed)' in text
        assert 'every task of the group can open one' in text

    def test_the_leaf_reads_the_stamp_instead_of_deriving_it(self):
        text = self._EXECUTE_TASK_SKILL.read_text(encoding='utf-8')

        assert 'Deliverable chain-tail rung deferral' in text, 'the leaf must point at the definition'
        assert "only when this task carries the deliverable's owed rung" not in text, (
            'the leaf must not claim the rung is carried only by one task: the unmeasured arm stamps none'
        )
