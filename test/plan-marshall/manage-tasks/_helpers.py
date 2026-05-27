#!/usr/bin/env python3
"""Shared imports, helpers, and Namespace builders for manage-tasks tests.

Sibling of the split test_manage_tasks_*.py files. Imported explicitly per
the dev-general-module-testing _fixtures.py / _helpers.py convention.
"""

import importlib.util
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path

# Script path for subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-tasks', 'manage-tasks.py')

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


_crud = _load_module('_tasks_cmd_crud', '_tasks_crud.py')
_query = _load_module('_tasks_cmd_query', '_tasks_query.py')
_step = _load_module('_tasks_cmd_step', '_cmd_step.py')
_core = _load_module('_tasks_cmd_core', '_tasks_core.py')

parse_stdin_task = _core.parse_stdin_task

cmd_prepare_add = _crud.cmd_prepare_add
cmd_commit_add = _crud.cmd_commit_add
cmd_remove = _crud.cmd_remove
cmd_update = _crud.cmd_update

cmd_read = _query.cmd_read
cmd_list = _query.cmd_list
cmd_next = _query.cmd_next
cmd_exists = _query.cmd_exists
cmd_loop_exit_guard = _query.cmd_loop_exit_guard
cmd_next_tasks = _query.cmd_next_tasks

cmd_add_step = _step.cmd_add_step
cmd_finalize_step = _step.cmd_finalize_step
cmd_remove_step = _step.cmd_remove_step


# =============================================================================
# Test Helpers
# =============================================================================


def build_task_toon(
    title='Test task',
    deliverable=None,
    domain='java',
    description='Task description',
    steps=None,
    depends_on='none',
    verification_commands=None,
    verification_criteria='',
    origin=None,
):
    """Build TOON content for task definition via stdin.

    Steps MUST be file paths per task contract (plan-type-api/standards/task-contract.md).
    """
    if deliverable is None:
        deliverable = 1
    if steps is None:
        steps = ['src/main/java/TestFile.java']
    if verification_commands is None:
        verification_commands = []

    lines = [
        f'title: {title}',
        f'deliverable: {deliverable}',
        f'domain: {domain}',
        f'description: {description}',
        'steps:',
    ]

    if origin is not None:
        lines.insert(3, f'origin: {origin}')

    for step in steps:
        lines.append(f'  - {step}')

    lines.append(f'depends_on: {depends_on}')

    if verification_commands or verification_criteria:
        lines.append('verification:')
        if verification_commands:
            lines.append('  commands:')
            for cmd in verification_commands:
                lines.append(f'    - {cmd}')
        if verification_criteria:
            lines.append(f'  criteria: {verification_criteria}')

    return '\n'.join(lines)


def _add_ns(plan_id='test-plan', content=''):
    """Compatibility Namespace for legacy `cmd_add` call shape."""
    return Namespace(plan_id=plan_id, content=content)


def _prepare_add_ns(plan_id='test-plan', slot=None):
    return Namespace(plan_id=plan_id, slot=slot)


def _commit_add_ns(plan_id='test-plan', slot=None):
    return Namespace(plan_id=plan_id, slot=slot)


def _add_task(plan_id, toon_text, slot=None):
    """Run the three-step add flow end-to-end and return the commit result."""
    prep = cmd_prepare_add(_prepare_add_ns(plan_id=plan_id, slot=slot))
    if prep.get('status') != 'success':
        return prep
    Path(prep['path']).write_text(toon_text, encoding='utf-8')
    return cmd_commit_add(_commit_add_ns(plan_id=plan_id, slot=slot))


def _add_task_empty(plan_id, slot=None):
    """Run prepare-add and commit-add with an empty scratch file."""
    prep = cmd_prepare_add(_prepare_add_ns(plan_id=plan_id, slot=slot))
    if prep.get('status') != 'success':
        return prep
    Path(prep['path']).write_text('', encoding='utf-8')
    return cmd_commit_add(_commit_add_ns(plan_id=plan_id, slot=slot))


def cmd_add(ns):
    """Test shim: drive the three-step path-allocate add flow."""
    text = (ns.content or '').replace('\\n', '\n')
    if not text.strip():
        return _add_task_empty(ns.plan_id)
    return _add_task(ns.plan_id, text)


def _read_ns(plan_id='test-plan', number=1):
    return Namespace(plan_id=plan_id, task_number=number)


def _exists_ns(plan_id='test-plan', number=1):
    return Namespace(plan_id=plan_id, task_number=number)


def _list_ns(plan_id='test-plan', status='all', deliverable=None, ready=False, domain=None, profile=None):
    return Namespace(
        plan_id=plan_id, status=status, deliverable=deliverable, ready=ready, domain=domain, profile=profile
    )


def _next_ns(plan_id='test-plan', include_context=False, ignore_deps=False):
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


def _remove_ns(plan_id='test-plan', number=1):
    return Namespace(plan_id=plan_id, task_number=number)


def _finalize_step_ns(plan_id='test-plan', task=1, step=1, outcome='done', reason=None):
    return Namespace(plan_id=plan_id, task_number=task, step=step, outcome=outcome, reason=reason)


def _add_step_ns(plan_id='test-plan', task=1, target='New Step', after=None):
    return Namespace(plan_id=plan_id, task_number=task, target=target, after=after)


def _remove_step_ns(plan_id='test-plan', task=1, step=1):
    return Namespace(plan_id=plan_id, task_number=task, step=step)


def _next_tasks_ns(plan_id='test-plan'):
    return Namespace(plan_id=plan_id)


def add_basic_task(
    plan_id='test-plan',
    title='Test task',
    deliverable=1,
    domain='java',
    description='Task description',
    steps=None,
    depends_on='none',
    origin=None,
):
    """Helper to add a task with minimal required params via direct import."""
    toon = build_task_toon(
        title=title,
        deliverable=deliverable,
        domain=domain,
        description=description,
        steps=steps,
        depends_on=depends_on,
        origin=origin,
    )
    return cmd_add(_add_ns(plan_id=plan_id, content=toon.replace('\n', '\\n')))
