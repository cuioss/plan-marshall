#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``lesson id reference validation`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


import sys
from argparse import Namespace

from conftest import load_script_module

# =============================================================================
# Module loading — load _tasks_crud directly via importlib so we can patch
# the module-level scan/verify bindings rather than the source bindings in
# input_validation. Mirrors the pattern in test_manage_tasks_batch_add.py.
# =============================================================================


_crud = load_script_module('plan-marshall', 'manage-tasks', '_tasks_crud.py', '_tasks_cmd_crud_lesson_ref')


cmd_commit_add = _crud.cmd_commit_add


cmd_batch_add = _crud.cmd_batch_add


# Resolve the input_validation module already loaded by _tasks_crud's import.
# The runtime regex anchor lives there (verify_lesson_id_regex_against_inventory),
# and scan_lesson_id_tokens triggers it on first use per process. Tests must
# short-circuit the anchor so they exercise only the regex+membership path
# instead of subprocessing `manage-lessons list` from the test environment.
_input_validation = _crud.scan_lesson_id_tokens.__module__


_iv = sys.modules[_input_validation]


# =============================================================================
# Fixture data — sample IDs sourced from real `manage-lessons list` output.
# PHANTOM_IDS are syntactically valid lesson
# IDs that do NOT exist in the live inventory.
# =============================================================================

REAL_LESSON_IDS = (
    '2026-04-29-10-001',
    '2026-05-03-21-002',
    '2026-04-26-11-001',
)


PHANTOM_IDS = (
    '2099-01-01-00-001',
    '2099-12-31-23-999',
)


# =============================================================================
# Helpers
# =============================================================================


def _commit_ns(plan_id, slot=None):
    """Build a Namespace for cmd_commit_add."""
    return Namespace(plan_id=plan_id, slot=slot)


def _batch_ns(plan_id, tasks_json=None, tasks_file=None):
    """Build a Namespace for cmd_batch_add."""
    return Namespace(plan_id=plan_id, tasks_json=tasks_json, tasks_file=tasks_file)


def _entry(
    title='Task',
    deliverable=1,
    domain='java',
    profile='implementation',
    steps=None,
    depends_on=None,
    skills=None,
    description='',
    origin='plan',
):
    """Build a valid batch entry dict (per task-contract.md schema).

    Bare-string ``steps`` are normalized to the required ``{target, intent}``
    object shape (default intent ``write-replace``).
    """
    if steps is None:
        steps = ['src/main/java/Foo.java']
    if depends_on is None:
        depends_on = []
    if skills is None:
        skills = []
    normalized_steps = [
        s if isinstance(s, dict) else {'target': s, 'intent': 'write-replace'} for s in steps
    ]
    return {
        'title': title,
        'deliverable': deliverable,
        'domain': domain,
        'profile': profile,
        'steps': normalized_steps,
        'depends_on': depends_on,
        'skills': skills,
        'description': description,
        'origin': origin,
    }


def _toon_task_body(
    title='Task',
    deliverable=1,
    domain='java',
    profile='implementation',
    steps=None,
    description='',
):
    """Build a task definition body in the format ``parse_stdin_task`` accepts.

    Matches the legacy fixture format used by ``test_manage_tasks.py``:
    plain ``steps:`` (NOT ``steps[N]:``), unquoted step items, raw
    description (no surrounding quotes). Inner quotes inside title/description
    are not used here to keep the parser path deterministic.
    """
    if steps is None:
        steps = ['src/main/java/Foo.java']
    lines = [
        f'title: {title}',
        f'deliverable: {deliverable}',
        f'domain: {domain}',
        f'profile: {profile}',
        'origin: plan',
        f'description: {description}',
        'steps:',
    ]
    for step in steps:
        marked = step if str(step).rstrip().endswith(')') else f'{step} (write-replace)'
        lines.append(f'  - {marked}')
    lines.append('depends_on: none')
    lines.append('skills:')
    return '\n'.join(lines) + '\n'


def _seed_pending(plan_dir, body, slot='default'):
    """Write a TOON scratch file under the plan's pending-tasks dir so
    cmd_commit_add can consume it (mimics prepare-add → main-context Write)."""
    pending_dir = plan_dir / 'work' / 'pending-tasks'
    pending_dir.mkdir(parents=True, exist_ok=True)
    path = pending_dir / f'{slot}.toon'
    path.write_text(body, encoding='utf-8')
    return path


def _make_inventory_stub(present_ids):
    """Return a verify_lesson_ids_exist replacement: every queried token
    maps to True iff it is in ``present_ids``."""
    present = set(present_ids)

    def _stub(tokens):
        return {tok: tok in present for tok in tokens}

    return _stub


def _seed_plan_dir_lesson(plan_dir, lesson_id, body='# converted lesson\n'):
    """Seed a plan-dir converted-lesson artifact at
    ``{plan_dir}/lesson-{lesson_id}.md`` — the tier-2 resolution path
    ``_scan_unresolved_lesson_ids`` consults via ``get_plan_dir(plan_id)``.

    A token whose artifact exists here is a legitimate reference even when the
    active manage-lessons inventory reports it absent."""
    path = plan_dir / f'lesson-{lesson_id}.md'
    path.write_text(body, encoding='utf-8')
    return path
