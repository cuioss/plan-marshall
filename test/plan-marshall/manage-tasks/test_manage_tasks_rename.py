#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-tasks rename-path subcommand.

Tier 2 (direct import) tests for path rename mapping and step target rewriting.
"""

import json
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

_rename = load_script_module('plan-marshall', 'manage-tasks', '_cmd_rename.py', '_tasks_cmd_rename')
_crud = load_script_module('plan-marshall', 'manage-tasks', '_tasks_crud.py', '_tasks_cmd_crud')

cmd_rename_path = _rename.cmd_rename_path
cmd_prepare_add = _crud.cmd_prepare_add
cmd_commit_add = _crud.cmd_commit_add


def _rename_ns(
    plan_id='rename-test', old_path='old/path', new_path='new/path', include_completed=False
):
    return Namespace(
        plan_id=plan_id,
        old_path=old_path,
        new_path=new_path,
        include_completed=include_completed,
    )


def _add_task(plan_id, toon_text, slot=None):
    """Run the path-allocate add flow end-to-end."""
    prep = cmd_prepare_add(Namespace(plan_id=plan_id, slot=slot))
    assert prep.get('status') == 'success', prep
    Path(prep['path']).write_text(toon_text, encoding='utf-8')
    return cmd_commit_add(Namespace(plan_id=plan_id, slot=slot))


def _build_task_toon(title='Test task', deliverable=1, steps=None):
    if steps is None:
        steps = ['src/main/java/File.java']
    lines = [
        f'title: {title}',
        f'deliverable: {deliverable}',
        'domain: java',
        'steps:',
    ]
    for step in steps:
        marked = step if str(step).rstrip().endswith(')') else f'{step} (write-replace)'
        lines.append(f'  - {marked}')
    lines.append('depends_on: none')
    return '\n'.join(lines)


class TestRenamePath:
    """Tests for rename-path subcommand."""

    def test_single_mapping(self, plan_context):
        """Adding a single rename mapping records it correctly."""
        result = cmd_rename_path(
            _rename_ns(
                plan_id='rename-single',
                old_path='providers/',
                new_path='auth/providers/',
            )
        )
        assert result['status'] == 'success'
        assert result['mapping']['old_path'] == 'providers'
        assert result['mapping']['new_path'] == 'auth/providers'
        assert result['mapping_count'] == 1

    def test_multiple_mappings(self, plan_context):
        """Adding multiple mappings accumulates them."""
        cmd_rename_path(
            _rename_ns(
                plan_id='rename-multi',
                old_path='old/a',
                new_path='new/a',
            )
        )
        result = cmd_rename_path(
            _rename_ns(
                plan_id='rename-multi',
                old_path='old/b',
                new_path='new/b',
            )
        )
        assert result['status'] == 'success'
        assert result['mapping_count'] == 2

    def test_identical_paths_error(self, plan_context):
        """Error when old and new paths are identical."""
        result = cmd_rename_path(
            _rename_ns(
                plan_id='rename-identical',
                old_path='same/path',
                new_path='same/path',
            )
        )
        assert result['status'] == 'error'

    def test_rewrites_step_targets(self, plan_context):
        """Rename-path rewrites matching step targets in pending tasks."""
        content = _build_task_toon(
            title='Task with old paths',
            deliverable=1,
            steps=['providers/config.py', 'providers/auth.py', 'unrelated/file.py'],
        )
        _add_task('rename-rewrite', content)

        result = cmd_rename_path(
            _rename_ns(
                plan_id='rename-rewrite',
                old_path='providers',
                new_path='auth/providers',
            )
        )

        assert result['status'] == 'success'
        assert result['rewritten_count'] == 2

        rewritten_targets = {r['new_target'] for r in result['rewritten']}
        assert 'auth/providers/config.py' in rewritten_targets
        assert 'auth/providers/auth.py' in rewritten_targets

    def test_does_not_rewrite_done_steps(self, plan_context):
        """By DEFAULT rename-path skips steps that are already done.

        The negative control matching ``test_include_completed_rewrites_a_done_step``:
        the two run the same rename over the same shape and differ only in the
        flag, so the flag is proved to be what lifts the guard.
        """
        content = _build_task_toon(
            title='Task with done steps',
            deliverable=1,
            steps=['providers/config.py'],
        )
        _add_task('rename-done-steps', content)

        # Mark the task's step as done by modifying the file directly
        tasks_dir = plan_context.plan_dir_for('rename-done-steps') / 'tasks'
        task_file = next(tasks_dir.glob('TASK-*.json'))
        task_data = json.loads(task_file.read_text())
        task_data['steps'][0]['status'] = 'done'
        task_file.write_text(json.dumps(task_data, indent=2))

        result = cmd_rename_path(
            _rename_ns(
                plan_id='rename-done-steps',
                old_path='providers',
                new_path='auth/providers',
            )
        )

        assert result['status'] == 'success'
        assert result['rewritten_count'] == 0
        assert result['rewritten_completed_count'] == 0

    def test_mapping_file_toon_format(self, plan_context):
        """Mapping file is written in valid TOON format."""
        cmd_rename_path(
            _rename_ns(
                plan_id='rename-toon',
                old_path='old/path',
                new_path='new/path',
            )
        )

        mapping_path = plan_context.plan_dir_for('rename-toon') / 'work' / 'rename_mapping.toon'
        assert mapping_path.exists()
        content = mapping_path.read_text()
        assert 'mapping_count: 1' in content
        assert 'mappings[1]{old_path,new_path}:' in content
        assert 'old/path,new/path' in content

    def test_no_tasks_no_error(self, plan_context):
        """Rename-path succeeds even when no tasks exist."""
        result = cmd_rename_path(
            _rename_ns(
                plan_id='rename-no-tasks',
                old_path='old/path',
                new_path='new/path',
            )
        )
        assert result['status'] == 'success'
        assert result['rewritten_count'] == 0
        assert result['mapping_count'] == 1


class TestRenamePathIncludeCompleted:
    """`--include-completed` lifts BOTH guards that protect finished work.

    The guards are two, not one — a `done` TASK is skipped whole, and within any
    other task a non-`pending` STEP is skipped — so each is given its own matched
    pair against the default. Without the flag the default behaviour above stays
    exactly as it was; the flag exists for the case the default cannot serve, an
    upstream rename landing mid-plan that leaves a completed step naming a path
    which no longer exists.
    """

    @staticmethod
    def _mark(plan_context, plan_id, *, task_status=None, step_status=None):
        """Set the task and/or first-step status on the plan's single task file."""
        tasks_dir = plan_context.plan_dir_for(plan_id) / 'tasks'
        task_file = next(tasks_dir.glob('TASK-*.json'))
        task_data = json.loads(task_file.read_text())
        if task_status is not None:
            task_data['status'] = task_status
        if step_status is not None:
            task_data['steps'][0]['status'] = step_status
        task_file.write_text(json.dumps(task_data, indent=2))
        return task_file

    def test_include_completed_rewrites_a_done_step(self, plan_context):
        """The step-level guard is lifted: a `done` step's target is rewritten.

        Positive control matching `TestRenamePath.test_does_not_rewrite_done_steps`
        — same shape, same rename, flag flipped.
        """
        _add_task(
            'rename-inc-step',
            _build_task_toon(deliverable=1, steps=['providers/config.py']),
        )
        task_file = self._mark(plan_context, 'rename-inc-step', step_status='done')

        result = cmd_rename_path(
            _rename_ns(
                plan_id='rename-inc-step',
                old_path='providers',
                new_path='auth/providers',
                include_completed=True,
            )
        )

        assert result['status'] == 'success'
        assert result['rewritten_count'] == 1
        # The rewrite reached disk, not merely the returned report.
        written = json.loads(task_file.read_text())
        assert written['steps'][0]['target'] == 'auth/providers/config.py'

    def test_include_completed_rewrites_steps_of_a_done_task(self, plan_context):
        """The task-level guard is lifted: a `done` task is no longer skipped whole.

        Distinct from the step-level guard above — a task can be `done` while the
        step rows still read `pending`, and that shape is skipped by the OTHER
        `continue`, so it needs its own pair.
        """
        _add_task(
            'rename-inc-task',
            _build_task_toon(deliverable=1, steps=['providers/config.py']),
        )
        task_file = self._mark(plan_context, 'rename-inc-task', task_status='done')

        result = cmd_rename_path(
            _rename_ns(
                plan_id='rename-inc-task',
                old_path='providers',
                new_path='auth/providers',
                include_completed=True,
            )
        )

        assert result['rewritten_count'] == 1
        written = json.loads(task_file.read_text())
        assert written['steps'][0]['target'] == 'auth/providers/config.py'

    def test_done_task_with_pending_steps_is_counted_as_completed_work(self, plan_context):
        """A done TASK whose step rows read `pending` still counts as finished work.

        The regression this pins: reading only `step_status` reports this shape
        as an ordinary pending rewrite — `rewritten_completed_count` 0 and no log
        marker — even though the rewrite edited a finished task's record. The two
        guards are independent, so the count must fire when EITHER is finished,
        and the entry must carry both statuses to show which one it was.
        """
        _add_task(
            'rename-inc-task-count',
            _build_task_toon(deliverable=1, steps=['providers/config.py']),
        )
        self._mark(plan_context, 'rename-inc-task-count', task_status='done')

        result = cmd_rename_path(
            _rename_ns(
                plan_id='rename-inc-task-count',
                old_path='providers',
                new_path='auth/providers',
                include_completed=True,
            )
        )

        assert result['rewritten_count'] == 1
        assert result['rewritten_completed_count'] == 1
        # The step really was pending — the count fired on the TASK status, which
        # is the whole point of recording both.
        assert [r['step_status'] for r in result['rewritten']] == ['pending']
        assert [r['task_status'] for r in result['rewritten']] == ['done']

    def test_done_task_is_skipped_without_the_flag(self, plan_context):
        """Negative control for the task-level guard: the default still skips it."""
        _add_task(
            'rename-inc-task-default',
            _build_task_toon(deliverable=1, steps=['providers/config.py']),
        )
        task_file = self._mark(plan_context, 'rename-inc-task-default', task_status='done')

        result = cmd_rename_path(
            _rename_ns(
                plan_id='rename-inc-task-default',
                old_path='providers',
                new_path='auth/providers',
            )
        )

        assert result['rewritten_count'] == 0
        written = json.loads(task_file.read_text())
        assert written['steps'][0]['target'] == 'providers/config.py'

    def test_report_names_the_status_the_step_had_before_the_rewrite(self, plan_context):
        """`step_status` is the PRE-rewrite status, and completed edits are counted.

        The count alone cannot distinguish an edit to finished work from an
        ordinary pending rewrite, so the report carries both: a per-entry
        `step_status` and a `rewritten_completed_count`. Asserting the recorded
        status is `done` — not the flag that was passed — is what makes the entry
        an audit record rather than a restatement of the caller's intent.
        """
        _add_task(
            'rename-inc-report',
            _build_task_toon(deliverable=1, steps=['providers/config.py']),
        )
        self._mark(plan_context, 'rename-inc-report', step_status='done')

        result = cmd_rename_path(
            _rename_ns(
                plan_id='rename-inc-report',
                old_path='providers',
                new_path='auth/providers',
                include_completed=True,
            )
        )

        assert result['rewritten_completed_count'] == 1
        assert [r['step_status'] for r in result['rewritten']] == ['done']
        assert [r['task_status'] for r in result['rewritten']] == ['pending']

    def test_pending_rewrite_is_not_counted_as_completed(self, plan_context):
        """A pending step rewritten under the flag does not inflate the completed count.

        Guards `rewritten_completed_count` against being a copy of
        `rewritten_count` whenever the flag is set — it must count the steps that
        were actually finished, not the invocations that allowed finished ones.
        """
        _add_task(
            'rename-inc-pending',
            _build_task_toon(deliverable=1, steps=['providers/config.py']),
        )

        result = cmd_rename_path(
            _rename_ns(
                plan_id='rename-inc-pending',
                old_path='providers',
                new_path='auth/providers',
                include_completed=True,
            )
        )

        assert result['rewritten_count'] == 1
        assert result['rewritten_completed_count'] == 0
        assert [r['step_status'] for r in result['rewritten']] == ['pending']
