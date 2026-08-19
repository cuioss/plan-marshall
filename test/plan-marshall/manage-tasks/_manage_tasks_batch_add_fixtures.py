#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `batch-add` subcommand of manage-tasks.

Covers:
  - successful multi-task atomic insertion (sequential numbering, persisted files)
  - empty array no-op
  - validation rejection (per-entry error reporting)
  - schema rejection (top-level type errors)
  - all-or-nothing semantics (one bad entry → no files written)
  - depends_on alternative encodings
"""




from argparse import Namespace

from conftest import load_script_module

# Load _tasks_crud directly via importlib (mirrors test_manage_tasks.py)


_crud = load_script_module('plan-marshall', 'manage-tasks', '_tasks_crud.py', '_tasks_cmd_crud_batch')


_core = load_script_module('plan-marshall', 'manage-tasks', '_tasks_core.py', '_tasks_core_for_parse_stdin')


cmd_batch_add = _crud.cmd_batch_add


parse_stdin_task = _core.parse_stdin_task


def _ns(plan_id, tasks_json=None, tasks_file=None):
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
    verification=None,
):
    """Build a valid batch entry dict (per task-contract.md schema).

    Bare-string ``steps`` are normalized to the required ``{target, intent}``
    object shape (default intent ``write-replace``) so existing call sites stay
    terse; a test may pass explicit ``{target, intent}`` dicts to pin an intent.
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
    entry = {
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
    if verification is not None:
        entry['verification'] = verification
    return entry


# =============================================================================
# Tests: parse_stdin_task accepts both bracketed and bare-block list forms
# =============================================================================
#
# Pins the stdin-parsing contract: ``parse_stdin_task``
# accepts BOTH the bare-block form (``steps:`` + indented ``- `` items) AND the
# bracketed length-declared form (``steps[N]:`` + same indented ``- `` items).
# Both shapes normalise to the same internal step list — no per-shape divergence.


_BARE_BLOCK_TASK_TOON = (
    'title: Bare-block form\n'
    'deliverable: 1\n'
    'domain: plan-marshall-plugin-dev\n'
    'description: Bare-block steps + skills + verification commands\n'
    'skills:\n'
    '  - pm-plugin-development:plugin-architecture\n'
    'steps:\n'
    '  - test/plan-marshall/manage-tasks/test_a.py (write-replace)\n'
    '  - test/plan-marshall/manage-tasks/test_b.py (write-replace)\n'
    'depends_on: none\n'
    'verification:\n'
    '  commands:\n'
    '    - python3 .plan/execute-script.py x:y:z run --command-args "module-tests"\n'
    '  criteria: green\n'
)


_BRACKETED_TASK_TOON = (
    'title: Bracketed form\n'
    'deliverable: 1\n'
    'domain: plan-marshall-plugin-dev\n'
    'description: Bracketed steps + skills + verification commands\n'
    'skills[1]:\n'
    '  - pm-plugin-development:plugin-architecture\n'
    'steps[2]:\n'
    '  - test/plan-marshall/manage-tasks/test_a.py (write-replace)\n'
    '  - test/plan-marshall/manage-tasks/test_b.py (write-replace)\n'
    'depends_on: none\n'
    'verification:\n'
    '  commands[1]:\n'
    '    - python3 .plan/execute-script.py x:y:z run --command-args "module-tests"\n'
    '  criteria: green\n'
)
