#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the field-only ``title-token`` verb of manage-status.py.

The ``title-token`` verb persists a bare state string into
``status.title_token`` and performs NO rendering — the composition (glyph
vocabulary + ``{icon} {body}`` assembly) lives in ``manage-terminal-title``.
These tests cover:

- ``set`` writes each of the two ``TITLE_TOKEN_STATES`` into status.json.
- ``clear`` removes the ``title_token`` field, and is idempotent when the
  field is already absent.
- An invalid ``--state`` is rejected by argparse (exit code 2) before the
  command body runs.
- The verb writes NO ``title-body.txt`` rendering artifact — manage-status is
  field-only.
"""

import json
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

# Script path for the argparse-rejection CLI test.
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_cmd_lifecycle')
_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_status_cmd_query')
_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_status_cmd_core')

cmd_create = _lifecycle.cmd_create
cmd_archive = _lifecycle.cmd_archive
cmd_title_token = _query.cmd_title_token
TITLE_TOKEN_STATES = _core.TITLE_TOKEN_STATES

# The two canonical title-token states (lock-coordination phases). Asserted
# explicitly here so a silent change to TITLE_TOKEN_STATES surfaces as a
# test failure rather than passing vacuously.
EXPECTED_STATES = frozenset({'lock-waiting', 'lock-owned'})


def _read_status(plan_context, plan_id):
    """Read the on-disk status.json for ``plan_id`` as a dict."""
    status_file = plan_context.plan_dir_for(plan_id) / 'status.json'
    return json.loads(status_file.read_text(encoding='utf-8'))


# =============================================================================
# Guard: the state vocabulary is exactly the two documented states
# =============================================================================


def test_title_token_states_are_the_two_documented_states():
    """``TITLE_TOKEN_STATES`` is exactly the two lock-coordination phase states."""
    assert TITLE_TOKEN_STATES == EXPECTED_STATES


# =============================================================================
# set: each of the two states writes status.title_token
# =============================================================================


def test_set_lock_waiting_writes_title_token(plan_context):
    """``title-token set --state lock-waiting`` persists the bare state string."""
    cmd_create(Namespace(plan_id='tt-lock-waiting', title='Test', phases='1-init', force=False))
    result = cmd_title_token(Namespace(plan_id='tt-lock-waiting', token_verb='set', state='lock-waiting'))

    assert result['status'] == 'success'
    assert result['title_token'] == 'lock-waiting'

    stored = _read_status(plan_context, 'tt-lock-waiting')
    assert stored['title_token'] == 'lock-waiting'


def test_set_lock_owned_writes_title_token(plan_context):
    """``title-token set --state lock-owned`` persists the bare state string."""
    cmd_create(Namespace(plan_id='tt-lock-owned', title='Test', phases='1-init', force=False))
    result = cmd_title_token(Namespace(plan_id='tt-lock-owned', token_verb='set', state='lock-owned'))

    assert result['status'] == 'success'
    assert result['title_token'] == 'lock-owned'

    stored = _read_status(plan_context, 'tt-lock-owned')
    assert stored['title_token'] == 'lock-owned'


def test_set_overwrites_existing_token(plan_context):
    """A second ``set`` overwrites the prior title_token value."""
    cmd_create(Namespace(plan_id='tt-overwrite', title='Test', phases='1-init', force=False))
    cmd_title_token(Namespace(plan_id='tt-overwrite', token_verb='set', state='lock-waiting'))
    cmd_title_token(Namespace(plan_id='tt-overwrite', token_verb='set', state='lock-owned'))

    stored = _read_status(plan_context, 'tt-overwrite')
    assert stored['title_token'] == 'lock-owned'


# =============================================================================
# clear: removes the field, idempotent when unset
# =============================================================================


def test_clear_removes_title_token_field(plan_context):
    """``title-token clear`` removes a previously-set title_token field."""
    cmd_create(Namespace(plan_id='tt-clear', title='Test', phases='1-init', force=False))
    cmd_title_token(Namespace(plan_id='tt-clear', token_verb='set', state='lock-owned'))

    result = cmd_title_token(Namespace(plan_id='tt-clear', token_verb='clear'))

    assert result['status'] == 'success'
    assert result['title_token'] is None
    assert result['cleared'] is True

    stored = _read_status(plan_context, 'tt-clear')
    assert 'title_token' not in stored


def test_clear_is_idempotent_when_unset(plan_context):
    """``title-token clear`` is a no-op when no title_token field exists."""
    cmd_create(Namespace(plan_id='tt-clear-noop', title='Test', phases='1-init', force=False))

    result = cmd_title_token(Namespace(plan_id='tt-clear-noop', token_verb='clear'))

    assert result['status'] == 'success'
    assert result['title_token'] is None
    assert result['cleared'] is False

    stored = _read_status(plan_context, 'tt-clear-noop')
    assert 'title_token' not in stored


def test_clear_twice_is_idempotent(plan_context):
    """Clearing twice in a row leaves the field absent and reports cleared=False."""
    cmd_create(Namespace(plan_id='tt-clear-twice', title='Test', phases='1-init', force=False))
    cmd_title_token(Namespace(plan_id='tt-clear-twice', token_verb='set', state='lock-waiting'))

    first = cmd_title_token(Namespace(plan_id='tt-clear-twice', token_verb='clear'))
    second = cmd_title_token(Namespace(plan_id='tt-clear-twice', token_verb='clear'))

    assert first['cleared'] is True
    assert second['cleared'] is False
    assert second['title_token'] is None

    stored = _read_status(plan_context, 'tt-clear-twice')
    assert 'title_token' not in stored


# =============================================================================
# argparse: invalid --state is rejected with exit code 2
# =============================================================================


def test_set_invalid_state_rejected_by_argparse():
    """``title-token set --state <bad>`` is rejected by argparse (exit code 2)."""
    result = run_script(
        SCRIPT_PATH,
        'title-token',
        'set',
        '--plan-id',
        'tt-argparse',
        '--state',
        'not-a-valid-state',
    )
    assert result.returncode == 2


# =============================================================================
# no rendering: the verb writes no title-body.txt artifact
# =============================================================================


def test_set_writes_no_title_body_artifact(plan_context):
    """``set`` persists only status.title_token — no title-body.txt rendering."""
    cmd_create(Namespace(plan_id='tt-no-render', title='Test', phases='1-init', force=False))
    cmd_title_token(Namespace(plan_id='tt-no-render', token_verb='set', state='lock-waiting'))

    plan_dir = plan_context.plan_dir_for('tt-no-render')
    assert not (plan_dir / 'title-body.txt').exists()


def test_clear_writes_no_title_body_artifact(plan_context):
    """``clear`` persists only status.json — no title-body.txt rendering."""
    cmd_create(Namespace(plan_id='tt-no-render-clear', title='Test', phases='1-init', force=False))
    cmd_title_token(Namespace(plan_id='tt-no-render-clear', token_verb='set', state='lock-owned'))
    cmd_title_token(Namespace(plan_id='tt-no-render-clear', token_verb='clear'))

    plan_dir = plan_context.plan_dir_for('tt-no-render-clear')
    assert not (plan_dir / 'title-body.txt').exists()


# =============================================================================
# archive: cmd_archive pops title_token before writing the archived status.json
# =============================================================================
#
# An archived plan has no live session driving its terminal title, so any
# in-flight title_token (a lock state) left behind would persist a stale lock
# glyph in the archived snapshot. cmd_archive must pop the field
# token-agnostically — a single pop covers every TITLE_TOKEN_STATES value.
# This test asserts the field is absent from the archived status.json after
# archiving with a pre-set merge token.


def _read_archived_status(result):
    """Read the archived status.json from a cmd_archive result dict."""
    archived_status_path = Path(result['archived_to']) / 'status.json'
    assert archived_status_path.exists(), (
        f'archived status.json missing at {archived_status_path} — '
        f'either move failed or archived_to points to wrong path'
    )
    return json.loads(archived_status_path.read_text(encoding='utf-8'))


def test_archive_pops_merge_lock_title_token(plan_context):
    """cmd_archive must pop a pre-set merge-lock title_token before archiving."""
    plan_id = 'tt-archive-merge-token'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases='1-init', force=False))
    # A merge-lock token represents an in-flight lock state held by the now-gone
    # live session.
    cmd_title_token(Namespace(plan_id=plan_id, token_verb='set', state='lock-owned'))

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False))

    assert result['status'] == 'success', f'archive failed: {result}'
    archived_status = _read_archived_status(result)
    assert 'title_token' not in archived_status, (
        f"Expected title_token absent from archived status.json after archiving "
        f"with a pre-set merge token, but found "
        f"{archived_status.get('title_token')!r}. cmd_archive must pop "
        f"title_token before write_status/shutil.move."
    )
