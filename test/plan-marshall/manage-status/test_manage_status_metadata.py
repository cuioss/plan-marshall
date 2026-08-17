#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py metadata + get-context commands.

Split from test_manage_status.py: covers cmd_metadata (set/get/coercion) and
cmd_get_context (which composes metadata + phase progress).
"""

import json
from argparse import Namespace

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_cmd_lifecycle')
_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_status_cmd_query')
_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_status_cmd_core')

cmd_create = _lifecycle.cmd_create
cmd_get_context = _query.cmd_get_context
cmd_metadata = _query.cmd_metadata
cmd_set_phase = _query.cmd_set_phase
cmd_update_phase = _query.cmd_update_phase


# =============================================================================
# Test: Metadata Commands
# =============================================================================


def test_metadata_set(plan_context):
    """Test setting a metadata field."""
    cmd_create(Namespace(plan_id='metadata-plan', title='Metadata Test', phases='1-init,2-refine', force=False))
    result = cmd_metadata(
        Namespace(plan_id='metadata-plan', set=True, get=False, field='change_type', value='feature')
    )
    assert result['status'] == 'success'
    assert result['field'] == 'change_type'
    assert result['value'] == 'feature'


def test_metadata_get(plan_context):
    """Test getting a metadata field."""
    cmd_create(Namespace(plan_id='metadata-get-plan', title='Metadata Test', phases='1-init,2-refine', force=False))
    # Set metadata first
    cmd_metadata(Namespace(plan_id='metadata-get-plan', set=True, get=False, field='change_type', value='bug_fix'))
    # Get metadata
    result = cmd_metadata(
        Namespace(plan_id='metadata-get-plan', set=False, get=True, field='change_type', value=None)
    )
    assert result['status'] == 'success'
    assert result['field'] == 'change_type'
    assert result['value'] == 'bug_fix'


def test_metadata_get_not_found(plan_context):
    """Test getting a non-existent metadata field."""
    cmd_create(Namespace(plan_id='metadata-notfound-plan', title='Test', phases='1-init', force=False))
    result = cmd_metadata(
        Namespace(plan_id='metadata-notfound-plan', set=False, get=True, field='nonexistent', value=None)
    )
    assert result['status'] == 'not_found'
    assert result['field'] == 'nonexistent'


def test_metadata_update_existing(plan_context):
    """Test updating an existing metadata field."""
    cmd_create(Namespace(plan_id='metadata-update-plan', title='Test', phases='1-init', force=False))
    # Set initial value
    cmd_metadata(
        Namespace(plan_id='metadata-update-plan', set=True, get=False, field='change_type', value='feature')
    )
    # Update value
    result = cmd_metadata(
        Namespace(plan_id='metadata-update-plan', set=True, get=False, field='change_type', value='bug_fix')
    )
    assert result['value'] == 'bug_fix'
    assert result['previous_value'] == 'feature'


def test_metadata_set_use_worktree_coerces_string_true_to_bool(plan_context):
    """Setting use_worktree via the CLI stores a JSON boolean, not a string.

    The ``--set`` CLI receives every value as a raw string. For the
    boolean-typed key ``use_worktree`` the raw ``"true"`` must be coerced
    to the JSON boolean ``True`` so downstream consumers (phase_handshake
    worktree drift checks) see a proper boolean.
    """
    cmd_create(Namespace(plan_id='metadata-bool-true-plan', title='Test', phases='1-init', force=False))
    result = cmd_metadata(
        Namespace(plan_id='metadata-bool-true-plan', set=True, get=False, field='use_worktree', value='true')
    )
    assert result['status'] == 'success'
    assert result['value'] is True

    status_file = plan_context.plan_dir_for('metadata-bool-true-plan') / 'status.json'
    content = json.loads(status_file.read_text(encoding='utf-8'))
    stored = content['metadata']['use_worktree']
    assert stored is True
    assert isinstance(stored, bool)


def test_metadata_set_use_worktree_coerces_string_false_to_bool(plan_context):
    """Setting use_worktree to "false" via the CLI stores JSON boolean False."""
    cmd_create(Namespace(plan_id='metadata-bool-false-plan', title='Test', phases='1-init', force=False))
    result = cmd_metadata(
        Namespace(plan_id='metadata-bool-false-plan', set=True, get=False, field='use_worktree', value='false')
    )
    assert result['status'] == 'success'
    assert result['value'] is False

    status_file = plan_context.plan_dir_for('metadata-bool-false-plan') / 'status.json'
    content = json.loads(status_file.read_text(encoding='utf-8'))
    stored = content['metadata']['use_worktree']
    assert stored is False
    assert isinstance(stored, bool)


def test_metadata_set_non_boolean_field_keeps_string_storage(plan_context):
    """Non-allowlisted fields are unaffected by boolean coercion.

    Coercion is restricted to the boolean-typed allowlist; every other
    field — including string values that happen to read like booleans —
    keeps verbatim string storage.
    """
    cmd_create(Namespace(plan_id='metadata-nonbool-plan', title='Test', phases='1-init', force=False))
    result = cmd_metadata(
        Namespace(plan_id='metadata-nonbool-plan', set=True, get=False, field='change_type', value='true')
    )
    assert result['status'] == 'success'
    assert result['value'] == 'true'

    status_file = plan_context.plan_dir_for('metadata-nonbool-plan') / 'status.json'
    content = json.loads(status_file.read_text(encoding='utf-8'))
    stored = content['metadata']['change_type']
    assert stored == 'true'
    assert isinstance(stored, str)


def test_metadata_set_boolean_field_with_none_value_stores_none(plan_context):
    """Boolean-typed field coercion is skipped when raw_value is None.

    When ``--value`` is omitted, argparse supplies ``None``. The coercion
    function must not call ``.strip()`` on a ``None`` value — the
    ``isinstance(raw_value, str)`` guard ensures the value is stored
    verbatim rather than raising ``AttributeError``.
    """
    cmd_create(Namespace(plan_id='metadata-none-plan', title='Test', phases='1-init', force=False))
    result = cmd_metadata(
        Namespace(plan_id='metadata-none-plan', set=True, get=False, field='use_worktree', value=None)
    )
    assert result['status'] == 'success'
    assert result['value'] is None

    status_file = plan_context.plan_dir_for('metadata-none-plan') / 'status.json'
    content = json.loads(status_file.read_text(encoding='utf-8'))
    stored = content['metadata']['use_worktree']
    assert stored is None


# =============================================================================
# Test: Get-Context Command
# =============================================================================


def test_get_context(plan_context):
    """Test get-context returns combined status context."""
    cmd_create(
        Namespace(
            plan_id='context-plan',
            title='Context Test',
            phases='1-init,2-refine,3-outline,4-plan',
            force=False,
        )
    )
    # Set some metadata
    cmd_metadata(Namespace(plan_id='context-plan', set=True, get=False, field='change_type', value='feature'))
    # Mark first phase as done
    cmd_update_phase(Namespace(plan_id='context-plan', phase='1-init', status='done'))
    cmd_set_phase(Namespace(plan_id='context-plan', phase='2-refine'))

    result = cmd_get_context(Namespace(plan_id='context-plan'))
    assert result['status'] == 'success'
    # Should have phase info
    assert result['current_phase'] == '2-refine'
    # Should have progress
    assert result['total_phases'] == 4
    assert result['completed_phases'] == 1
    # Should have metadata
    assert result['change_type'] == 'feature'


def test_get_context_not_found(plan_context):
    """Test get-context returns None for missing plan (TOON error already output)."""
    result = cmd_get_context(Namespace(plan_id='nonexistent'))
    assert result is None


# =============================================================================
# Test: Metadata Append (list-valued fields)
# =============================================================================


def _append(plan_id, field, value):
    return cmd_metadata(
        Namespace(plan_id=plan_id, set=True, get=False, append=True, field=field, value=value)
    )


def _get(plan_id, field):
    return cmd_metadata(
        Namespace(plan_id=plan_id, set=False, get=True, append=False, field=field, value=None)
    )


def _new_plan(plan_id):
    cmd_create(Namespace(plan_id=plan_id, title='Append Test', phases='1-init,2-refine', force=False))


def test_metadata_append_creates_the_list_when_the_field_is_absent(plan_context):
    _new_plan('append-absent')
    result = _append('append-absent', 'session_ids', 'sess-1')
    assert result['status'] == 'success'
    assert result['value'] == ['sess-1']
    assert result['appended'] is True


def test_metadata_append_preserves_the_earlier_value(plan_context):
    """REGRESSION (D4): the multi-session case the scalar field destroyed.

    A plan legitimately spans several sessions. Held as a scalar the field had
    ONE slot, so a second writer — a resume, or an observing process capturing
    against the plan it is measuring — overwrote the first identity outright,
    and the surviving value was well-formed so nothing downstream rejected it.
    """
    _new_plan('append-multi')
    _append('append-multi', 'session_ids', 'sess-measured')
    result = _append('append-multi', 'session_ids', 'sess-observer')

    assert result['value'] == ['sess-measured', 'sess-observer']
    # The measured plan's own identity SURVIVES the observer's write.
    assert 'sess-measured' in _get('append-multi', 'session_ids')['value']


def test_metadata_append_is_idempotent(plan_context):
    _new_plan('append-idem')
    _append('append-idem', 'session_ids', 'sess-1')
    result = _append('append-idem', 'session_ids', 'sess-1')
    assert result['value'] == ['sess-1']
    assert result['appended'] is False


def test_metadata_append_order_is_capture_order(plan_context):
    _new_plan('append-order')
    for sid in ('a', 'b', 'c'):
        _append('append-order', 'session_ids', sid)
    assert _get('append-order', 'session_ids')['value'] == ['a', 'b', 'c']


def test_metadata_append_refuses_a_non_list_field_and_leaves_the_document_identical(plan_context):
    """A scalar is never silently coerced into a container.

    Asserts BYTE-identity rather than just the field's value: ``rmw_json``
    commits unconditionally, so "the error path changed nothing" is a claim about
    the whole document — including the ``updated`` stamp — not only the field the
    caller named.
    """
    _new_plan('append-scalar')
    cmd_metadata(
        Namespace(plan_id='append-scalar', set=True, get=False, append=False,
                  field='change_type', value='feature')
    )
    status_path = _core.get_status_path('append-scalar')
    before = status_path.read_bytes()

    result = _append('append-scalar', 'change_type', 'bug_fix')

    assert result['status'] == 'error'
    assert result['error'] == 'metadata_field_not_a_list'
    assert status_path.read_bytes() == before
    assert _get('append-scalar', 'change_type')['value'] == 'feature'


def test_metadata_append_without_set_is_an_error(plan_context):
    _new_plan('append-no-set')
    result = cmd_metadata(
        Namespace(plan_id='append-no-set', set=False, get=False, append=True,
                  field='session_ids', value='sess-1')
    )
    assert result['status'] == 'error'
    assert result['error'] == 'append_without_set'


def test_metadata_append_without_value_is_an_error(plan_context):
    _new_plan('append-no-value')
    result = cmd_metadata(
        Namespace(plan_id='append-no-value', set=True, get=False, append=True,
                  field='session_ids', value=None)
    )
    assert result['status'] == 'error'
    assert result['error'] == 'missing_value'


def test_metadata_set_without_append_still_replaces(plan_context):
    """The default --set path is unchanged: last write wins, no list."""
    _new_plan('append-default')
    cmd_metadata(
        Namespace(plan_id='append-default', set=True, get=False, append=False,
                  field='change_type', value='feature')
    )
    cmd_metadata(
        Namespace(plan_id='append-default', set=True, get=False, append=False,
                  field='change_type', value='bug_fix')
    )
    assert _get('append-default', 'change_type')['value'] == 'bug_fix'


def test_metadata_append_leaves_sibling_metadata_untouched(plan_context):
    _new_plan('append-siblings')
    cmd_metadata(
        Namespace(plan_id='append-siblings', set=True, get=False, append=False,
                  field='change_type', value='feature')
    )
    _append('append-siblings', 'session_ids', 'sess-1')
    assert _get('append-siblings', 'change_type')['value'] == 'feature'
    assert _get('append-siblings', 'session_ids')['value'] == ['sess-1']
