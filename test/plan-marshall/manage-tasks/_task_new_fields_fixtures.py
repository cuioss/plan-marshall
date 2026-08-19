#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``task new fields`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, load_script_module

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-tasks', 'manage-tasks.py')


_crud = load_script_module('plan-marshall', 'manage-tasks', '_tasks_crud.py', '_tasks_cmd_crud_nf')


_query = load_script_module('plan-marshall', 'manage-tasks', '_tasks_query.py', '_tasks_cmd_query_nf')


_step = load_script_module('plan-marshall', 'manage-tasks', '_cmd_step.py', '_tasks_cmd_step_nf')


cmd_prepare_add = _crud.cmd_prepare_add


cmd_commit_add = _crud.cmd_commit_add


cmd_update = _crud.cmd_update


def _add_task_pathalloc(plan_id, toon_text, slot=None):
    """Run the path-allocate add flow end-to-end."""
    prep = cmd_prepare_add(Namespace(plan_id=plan_id, slot=slot))
    if prep.get('status') != 'success':
        return prep
    Path(prep['path']).write_text(toon_text, encoding='utf-8')
    return cmd_commit_add(Namespace(plan_id=plan_id, slot=slot))


def cmd_add(ns):
    """Test shim: drive the three-step path-allocate add flow.

    Accepts the legacy `Namespace(plan_id, content)` shape where `content`
    is a newline-escaped TOON string.
    """
    text = (ns.content or '').replace('\\n', '\n')
    return _add_task_pathalloc(ns.plan_id, text)


cmd_read, cmd_list, cmd_next = _query.cmd_read, _query.cmd_list, _query.cmd_next


cmd_next_tasks = _query.cmd_next_tasks


cmd_finalize_step = _step.cmd_finalize_step


# =============================================================================
# Test Helpers
# =============================================================================


def build_task_toon_with_new_fields(
    title='Test task',
    deliverable=1,
    domain='java',
    profile='implementation',
    skills=None,
    origin='plan',
    description='Task description',
    steps=None,
    depends_on='none',
):
    """Build TOON content for task with new fields."""
    if steps is None:
        steps = ['src/main/java/TestFile.java']
    if skills is None:
        skills = ['pm-dev-java:java-core']

    lines = [
        f'title: {title}',
        f'deliverable: {deliverable}',
        f'domain: {domain}',
        f'profile: {profile}',
        f'origin: {origin}',
        f'description: {description}',
        'skills:',
    ]

    for skill in skills:
        lines.append(f'  - {skill}')

    lines.append('steps:')
    for step in steps:
        marked = step if str(step).rstrip().endswith(')') else f'{step} (write-replace)'
        lines.append(f'  - {marked}')

    lines.append(f'depends_on: {depends_on}')

    return '\n'.join(lines)


def _add_ns(plan_id='test-plan', content=''):
    """Build Namespace for cmd_add."""
    return Namespace(plan_id=plan_id, content=content)


def _read_ns(plan_id='test-plan', number=1):
    """Build Namespace for cmd_read."""
    return Namespace(plan_id=plan_id, task_number=number)


def _list_ns(plan_id='test-plan', status='all', deliverable=None, ready=False, domain=None, profile=None):
    """Build Namespace for cmd_list."""
    return Namespace(
        plan_id=plan_id, status=status, deliverable=deliverable, ready=ready, domain=domain, profile=profile
    )


def _next_ns(plan_id='test-plan', include_context=False, ignore_deps=False):
    """Build Namespace for cmd_next."""
    return Namespace(plan_id=plan_id, include_context=include_context, ignore_deps=ignore_deps)


def _update_ns(
    plan_id='test-plan',
    number=1,
    title=None,
    description=None,
    depends_on=None,
    status=None,
    domain=None,
    profile=None,
    skills=None,
    deliverable=None,
):
    """Build Namespace for cmd_update."""
    return Namespace(
        plan_id=plan_id,
        task_number=number,
        title=title,
        description=description,
        depends_on=depends_on,
        status=status,
        domain=domain,
        profile=profile,
        skills=skills,
        deliverable=deliverable,
    )


def _finalize_step_ns(plan_id='test-plan', task=1, step=1, outcome='done', reason=None):
    """Build Namespace for cmd_finalize_step."""
    return Namespace(plan_id=plan_id, task_number=task, step=step, outcome=outcome, reason=reason)


def _next_tasks_ns(plan_id='test-plan'):
    """Build Namespace for cmd_next_tasks."""
    return Namespace(plan_id=plan_id)


def add_task_with_fields(plan_id='test-plan', **kwargs):
    """Helper to add a task with new fields."""
    toon = build_task_toon_with_new_fields(**kwargs)
    return cmd_add(_add_ns(plan_id=plan_id, content=toon.replace('\n', '\\n')))
