#!/usr/bin/env python3
"""Tests for manage-tasks rename-path subcommand.

Tier 2 (direct import) tests for path rename mapping and step target rewriting.
"""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

from conftest import PlanContext

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-tasks'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_rename = _load_module('_tasks_cmd_rename', '_cmd_rename.py')
_crud = _load_module('_tasks_cmd_crud', '_tasks_crud.py')

cmd_rename_path = _rename.cmd_rename_path
cmd_add = _crud.cmd_add


def _rename_ns(plan_id='rename-test', old_path='old/path', new_path='new/path'):
    return Namespace(plan_id=plan_id, old_path=old_path, new_path=new_path)


def _add_ns(plan_id='rename-test', content=''):
    return Namespace(plan_id=plan_id, content=content)


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
        lines.append(f'  - {step}')
    lines.append('depends_on: none')
    return '\n'.join(lines)


class TestRenamePath:
    """Tests for rename-path subcommand."""

    def test_single_mapping(self):
        """Adding a single rename mapping records it correctly."""
        with PlanContext(plan_id='rename-single'):
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

    def test_multiple_mappings(self):
        """Adding multiple mappings accumulates them."""
        with PlanContext(plan_id='rename-multi'):
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

    def test_identical_paths_error(self):
        """Error when old and new paths are identical."""
        with PlanContext(plan_id='rename-identical'):
            result = cmd_rename_path(
                _rename_ns(
                    plan_id='rename-identical',
                    old_path='same/path',
                    new_path='same/path',
                )
            )
            assert result['status'] == 'error'

    def test_rewrites_step_targets(self):
        """Rename-path rewrites matching step targets in pending tasks."""
        with PlanContext(plan_id='rename-rewrite'):
            # Create a task with steps targeting old paths
            content = _build_task_toon(
                title='Task with old paths',
                deliverable=1,
                steps=['providers/config.py', 'providers/auth.py', 'unrelated/file.py'],
            )
            cmd_add(_add_ns(plan_id='rename-rewrite', content=content))

            # Rename providers/ -> auth/providers/
            result = cmd_rename_path(
                _rename_ns(
                    plan_id='rename-rewrite',
                    old_path='providers',
                    new_path='auth/providers',
                )
            )

            assert result['status'] == 'success'
            assert result['rewritten_count'] == 2

            # Verify the rewritten entries
            rewritten_targets = {r['new_target'] for r in result['rewritten']}
            assert 'auth/providers/config.py' in rewritten_targets
            assert 'auth/providers/auth.py' in rewritten_targets

    def test_does_not_rewrite_done_steps(self):
        """Rename-path skips steps that are already done."""
        with PlanContext(plan_id='rename-done-steps') as ctx:
            content = _build_task_toon(
                title='Task with done steps',
                deliverable=1,
                steps=['providers/config.py'],
            )
            cmd_add(_add_ns(plan_id='rename-done-steps', content=content))

            # Mark the task's step as done by modifying the file directly
            tasks_dir = ctx.plan_dir / 'tasks'
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

    def test_mapping_file_toon_format(self):
        """Mapping file is written in valid TOON format."""
        with PlanContext(plan_id='rename-toon') as ctx:
            cmd_rename_path(
                _rename_ns(
                    plan_id='rename-toon',
                    old_path='old/path',
                    new_path='new/path',
                )
            )

            mapping_path = ctx.plan_dir / 'work' / 'rename_mapping.toon'
            assert mapping_path.exists()
            content = mapping_path.read_text()
            assert 'mapping_count: 1' in content
            assert 'mappings[1]{old_path,new_path}:' in content
            assert 'old/path,new/path' in content

    def test_no_tasks_no_error(self):
        """Rename-path succeeds even when no tasks exist."""
        with PlanContext(plan_id='rename-no-tasks'):
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
