#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Error / edge-branch coverage for manage-tasks _tasks_crud.py handlers.

The happy paths and the most common rejections for ``prepare-add`` /
``commit-add`` / ``batch-add`` / ``update`` / ``remove`` are already covered by
the sibling suites (test_manage_tasks_add.py, test_manage_tasks_batch_add.py,
test_manage_tasks_update_remove.py, test_tasks_writeback.py). This module fills
the remaining branches in ``_tasks_crud.py``:

* ``cmd_prepare_add`` — invalid-slot rejection and the "scratch already on
  disk" resolved-path branch.
* ``cmd_commit_add`` — invalid-slot rejection and the "no prepared file"
  rejection driven in-process (the CLI suite drives it via subprocess, which
  does not attribute coverage).
* ``cmd_update`` — task-not-found, description/domain write-through, the
  whitespace-profile / bad-skill / non-integer-deliverable validation
  rejections, and the comma-separated skills write path.
* ``cmd_remove`` — task-not-found.
* ``_validate_batch_entry`` — the per-field type guards (non-dict entry,
  non-string description, empty profile, non-string origin, missing
  deliverable, non-list steps, the depends_on encodings, and the verification
  shape guards) reached through ``cmd_batch_add``.

All assertions check the typed error discriminator and/or the human message,
never merely that a value is non-None.
"""

import json
from argparse import Namespace

from conftest import load_script_module

from _helpers import (
    _commit_add_ns,
    _prepare_add_ns,
    _read_ns,
    _remove_ns,
    _update_ns,
    add_basic_task,
    cmd_commit_add,
    cmd_prepare_add,
    cmd_read,
    cmd_remove,
    cmd_update,
)

# cmd_batch_add is not re-exported by _helpers; load _tasks_crud directly. The
# duplicate module object shares the same source file, so coverage merges.
_crud = load_script_module('plan-marshall', 'manage-tasks', '_tasks_crud.py', 'crud_branch_mod')
cmd_batch_add = _crud.cmd_batch_add


# =============================================================================
# cmd_prepare_add
# =============================================================================


def test_prepare_add_invalid_slot_returns_error(plan_context):
    """A slot that violates the slot regex is rejected with a status: error."""
    result = cmd_prepare_add(Namespace(plan_id='prep-bad-slot', slot='Bad Slot!'))

    assert result['status'] == 'error'
    assert 'slot' in result['message'].lower()


def test_prepare_add_reports_existing_scratch_with_resolved_path(plan_context):
    """A second prepare-add after the scratch is written reports exists=true.

    The first call allocates the path (the file does not yet exist); once the
    caller writes the scratch, a re-issued prepare-add takes the ``path.exists()``
    branch and returns the resolved absolute path with ``exists: True``.
    """
    first = cmd_prepare_add(_prepare_add_ns(plan_id='prep-existing'))
    assert first['status'] == 'success'
    assert first['exists'] is False

    from pathlib import Path

    Path(first['path']).write_text('title: x\n', encoding='utf-8')

    second = cmd_prepare_add(_prepare_add_ns(plan_id='prep-existing'))

    assert second['status'] == 'success'
    assert second['exists'] is True
    assert Path(second['path']).is_absolute()


# =============================================================================
# cmd_commit_add
# =============================================================================


def test_commit_add_without_prepare_returns_error(plan_context):
    """commit-add with no prepared scratch file is rejected and names prepare-add."""
    result = cmd_commit_add(_commit_add_ns(plan_id='commit-no-prep'))

    assert result['status'] == 'error'
    assert 'prepare-add' in result['message']


def test_commit_add_invalid_slot_returns_error(plan_context):
    """commit-add with a malformed slot is rejected at slot validation."""
    result = cmd_commit_add(Namespace(plan_id='commit-bad-slot', slot='NOT valid'))

    assert result['status'] == 'error'
    assert 'slot' in result['message'].lower()


# =============================================================================
# cmd_update — not-found and field write-through / rejection branches
# =============================================================================


def test_update_missing_task_returns_error(plan_context):
    """Updating a task that does not exist returns a not-found error."""
    result = cmd_update(_update_ns(plan_id='upd-missing', number=7, title='X'))

    assert result['status'] == 'error'
    assert 'not found' in result['message'].lower()


def test_update_description_persists(plan_context):
    """update --description writes the new description through to disk."""
    add_basic_task(plan_id='upd-desc', title='Task', deliverable=1)

    result = cmd_update(_update_ns(plan_id='upd-desc', number=1, description='Rewritten description'))

    assert result['status'] == 'success'
    read_back = cmd_read(_read_ns(plan_id='upd-desc', number=1))
    assert read_back['task']['description'] == 'Rewritten description'


def test_update_domain_persists(plan_context):
    """update --domain writes the new domain through to disk."""
    add_basic_task(plan_id='upd-domain', title='Task', deliverable=1, domain='java')

    result = cmd_update(_update_ns(plan_id='upd-domain', number=1, domain='python'))

    assert result['status'] == 'success'
    assert result['task']['domain'] == 'python'


def test_update_whitespace_profile_rejected(plan_context):
    """A whitespace-only profile fails validate_profile and is rejected."""
    add_basic_task(plan_id='upd-ws-profile', title='Task', deliverable=1)

    result = cmd_update(_update_ns(plan_id='upd-ws-profile', number=1, profile='   '))

    assert result['status'] == 'error'
    assert 'profile' in result['message'].lower()


def test_update_invalid_skill_format_rejected(plan_context):
    """A skill without the bundle:skill colon is rejected by validate_skills."""
    add_basic_task(plan_id='upd-bad-skill', title='Task', deliverable=1)

    result = cmd_update(_update_ns(plan_id='upd-bad-skill', number=1, skills='nocolon'))

    assert result['status'] == 'error'
    assert 'skill format' in result['message']


def test_update_comma_separated_skills_persist(plan_context):
    """Comma-separated skills are split, validated, and persisted as a list."""
    add_basic_task(plan_id='upd-skills-csv', title='Task', deliverable=1)

    result = cmd_update(
        _update_ns(plan_id='upd-skills-csv', number=1, skills='bundle:skill-a, bundle:skill-b')
    )

    assert result['status'] == 'success'
    assert result['task']['skills'] == ['bundle:skill-a', 'bundle:skill-b']


def test_update_non_integer_deliverable_rejected(plan_context):
    """A non-integer --deliverable fails the int() coercion in the handler."""
    add_basic_task(plan_id='upd-bad-del', title='Task', deliverable=1)

    result = cmd_update(_update_ns(plan_id='upd-bad-del', number=1, deliverable='not-a-number'))

    assert result['status'] == 'error'
    assert 'deliverable' in result['message'].lower()


# =============================================================================
# cmd_remove — not-found
# =============================================================================


def test_remove_missing_task_returns_error(plan_context):
    """Removing a task that does not exist returns a not-found error."""
    result = cmd_remove(_remove_ns(plan_id='rm-missing', number=3))

    assert result['status'] == 'error'
    assert 'not found' in result['message'].lower()


# =============================================================================
# _validate_batch_entry — per-field type guards (via cmd_batch_add)
# =============================================================================

_DROP = object()

_BASE_ENTRY = {
    'title': 'T',
    'description': 'd',
    'domain': 'java',
    'profile': 'implementation',
    'origin': 'plan',
    'deliverable': 1,
    'steps': [{'target': 'src/A.java', 'intent': 'write-replace'}],
    'depends_on': [],
    'skills': [],
    'verification': {},
}


def _entry(**over):
    """Build a valid batch entry with selected fields overridden or dropped."""
    e = dict(_BASE_ENTRY)
    for key, value in over.items():
        if value is _DROP:
            e.pop(key, None)
        else:
            e[key] = value
    return e


def _batch(plan_id, entries):
    return cmd_batch_add(Namespace(plan_id=plan_id, tasks_json=json.dumps(entries), tasks_file=None))


def test_batch_entry_non_dict_rejected(plan_context):
    """A non-object array element is rejected with a typed message."""
    result = _batch('batch-nondict', [42])

    assert result['status'] == 'error'
    assert 'expected JSON object' in result['message']


def test_batch_entry_non_string_description_rejected(plan_context):
    """A non-string description is rejected per-entry."""
    result = _batch('batch-desc', [_entry(description=5)])

    assert result['status'] == 'error'
    assert 'description must be a string' in result['message']


def test_batch_entry_empty_profile_rejected(plan_context):
    """An empty profile string is rejected per-entry."""
    result = _batch('batch-profile', [_entry(profile='')])

    assert result['status'] == 'error'
    assert 'profile must be a non-empty string' in result['message']


def test_batch_entry_non_string_origin_rejected(plan_context):
    """A non-string origin is rejected per-entry."""
    result = _batch('batch-origin', [_entry(origin=5)])

    assert result['status'] == 'error'
    assert 'origin must be a string' in result['message']


def test_batch_entry_missing_deliverable_rejected(plan_context):
    """A non-holistic entry that omits deliverable defaults to 0 and is rejected."""
    result = _batch('batch-no-del', [_entry(deliverable=_DROP)])

    assert result['status'] == 'error'
    assert 'deliverable' in result['message'].lower()


def test_batch_entry_steps_not_list_rejected(plan_context):
    """A non-array steps value is rejected per-entry."""
    result = _batch('batch-steps', [_entry(steps='not-a-list')])

    assert result['status'] == 'error'
    assert 'steps must be a JSON array' in result['message']


def test_batch_entry_depends_on_invalid_token_rejected(plan_context):
    """An unparseable depends_on token is rejected per-entry."""
    result = _batch('batch-dep-tok', [_entry(depends_on=['bogus'])])

    assert result['status'] == 'error'
    assert 'depends_on' in result['message']


def test_batch_entry_depends_on_non_string_element_rejected(plan_context):
    """A non-string element inside the depends_on array is rejected."""
    result = _batch('batch-dep-elem', [_entry(depends_on=[5])])

    assert result['status'] == 'error'
    assert 'depends_on entries must be strings' in result['message']


def test_batch_entry_depends_on_wrong_type_rejected(plan_context):
    """A depends_on that is neither array, string, nor 'none' is rejected."""
    result = _batch('batch-dep-type', [_entry(depends_on=5)])

    assert result['status'] == 'error'
    assert 'depends_on must be an array' in result['message']


def test_batch_entry_verification_not_dict_rejected(plan_context):
    """A non-object verification block is rejected per-entry."""
    result = _batch('batch-verif', [_entry(verification='nope')])

    assert result['status'] == 'error'
    assert 'verification must be a JSON object' in result['message']


def test_batch_entry_verification_commands_not_list_rejected(plan_context):
    """A non-array verification.commands is rejected per-entry."""
    result = _batch('batch-verif-cmds', [_entry(verification={'commands': 'x'})])

    assert result['status'] == 'error'
    assert 'verification.commands must be an array' in result['message']


def test_batch_entry_verification_command_non_string_rejected(plan_context):
    """A non-string verification.commands element is rejected per-entry."""
    result = _batch('batch-verif-cmd-el', [_entry(verification={'commands': [5]})])

    assert result['status'] == 'error'
    assert 'verification.commands entries must be strings' in result['message']
