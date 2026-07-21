#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the field-only ``title-token`` verb of manage-status.py.

The ``title-token`` verb persists a bare state string into
``status.title_token`` and performs NO rendering — the composition (glyph
vocabulary + ``{icon} {body}`` assembly) lives in ``manage-terminal-title``.
These tests cover:

- ``set`` writes each of the three ``TITLE_TOKEN_STATES`` into status.json.
- ``clear`` removes the ``title_token`` field, and is idempotent when the
  field is already absent.
- An invalid ``--state`` is rejected by argparse (exit code 2) before the
  command body runs.
- The verb writes NO ``title-body.txt`` rendering artifact — manage-status is
  field-only.
"""

import json
import logging
import subprocess
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
cmd_transition = _lifecycle.cmd_transition
cmd_title_token = _query.cmd_title_token
cmd_set_phase = _query.cmd_set_phase
TITLE_TOKEN_STATES = _core.TITLE_TOKEN_STATES

# A multi-phase plan whose adjacent transitions never reach the 6-finalize
# blocking boundary, so cmd_transition performs a plain phase advance (no
# strict-verify guard) — the surface these build-busy clearing tests exercise.
_PHASES = '1-init,2-refine,3-outline'

# The three canonical title-token states: the two lock-coordination phases
# (lock-waiting / lock-owned) plus the orchestration-busy state (build-busy).
# Asserted explicitly here so a silent change to TITLE_TOKEN_STATES surfaces
# as a test failure rather than passing vacuously.
EXPECTED_STATES = frozenset({'lock-waiting', 'lock-owned', 'build-busy'})


def _read_status(plan_context, plan_id):
    """Read the on-disk status.json for ``plan_id`` as a dict."""
    status_file = plan_context.plan_dir_for(plan_id) / 'status.json'
    return json.loads(status_file.read_text(encoding='utf-8'))


# =============================================================================
# Guard: the state vocabulary is exactly the two documented states
# =============================================================================


def test_title_token_states_are_the_three_documented_states():
    """``TITLE_TOKEN_STATES`` is exactly the two lock-coordination phase states
    plus the orchestration-busy ``build-busy`` state."""
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


def test_set_build_busy_writes_title_token(plan_context):
    """``title-token set --state build-busy`` persists the bare state string.

    build-busy is the orchestration-busy state — written by the orchestration
    layer (not the lock machinery) for the duration of a long-running build
    Bash call. manage-status persists it field-only, identically to the lock
    states; the 🔨 icon-slot override is applied downstream by
    ``manage-terminal-title``.
    """
    cmd_create(Namespace(plan_id='tt-build-busy', title='Test', phases='1-init', force=False))
    result = cmd_title_token(Namespace(plan_id='tt-build-busy', token_verb='set', state='build-busy'))

    assert result['status'] == 'success'
    assert result['title_token'] == 'build-busy'

    stored = _read_status(plan_context, 'tt-build-busy')
    assert stored['title_token'] == 'build-busy'


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


def test_set_build_busy_accepted_by_argparse(plan_context):
    """``title-token set --state build-busy`` is accepted by argparse.

    The ``--state`` choices are derived from ``sorted(TITLE_TOKEN_STATES)``, so
    this end-to-end CLI run proves build-busy reaches the choices list — the
    positive counterpart to the invalid-state rejection above. A created plan
    is required so the command body runs to a clean (exit 0) success rather
    than aborting on a missing status.json.
    """
    cmd_create(Namespace(plan_id='tt-argparse-build-busy', title='Test', phases='1-init', force=False))
    result = run_script(
        SCRIPT_PATH,
        'title-token',
        'set',
        '--plan-id',
        'tt-argparse-build-busy',
        '--state',
        'build-busy',
    )
    assert result.returncode == 0

    stored = _read_status(plan_context, 'tt-argparse-build-busy')
    assert stored['title_token'] == 'build-busy'


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


def test_archive_pops_build_busy_title_token(plan_context):
    """cmd_archive must pop a pre-set build-busy title_token before archiving.

    A build-busy token left behind on an archived plan would persist a stale
    🔨 build glyph in the archived snapshot — the same stale-glyph hazard the
    lock-token variant guards against. cmd_archive pops the field
    token-agnostically, so a single pop covers every TITLE_TOKEN_STATES value
    including the orchestration-busy state.
    """
    plan_id = 'tt-archive-build-busy-token'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases='1-init', force=False))
    # An in-flight build-busy token represents an orchestration build state held
    # by the now-gone live session.
    cmd_title_token(Namespace(plan_id=plan_id, token_verb='set', state='build-busy'))

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False))

    assert result['status'] == 'success', f'archive failed: {result}'
    archived_status = _read_archived_status(result)
    assert 'title_token' not in archived_status, (
        f"Expected title_token absent from archived status.json after archiving "
        f"with a pre-set build-busy token, but found "
        f"{archived_status.get('title_token')!r}. cmd_archive must pop "
        f"title_token before write_status/shutil.move."
    )


# =============================================================================
# phase writers: cmd_transition / cmd_set_phase clear a stale build-busy token
# =============================================================================
#
# build-busy is armed by the orchestration layer for the duration of a
# long-running build/push/CI-wait Bash call and is meant to be cleared when
# that call returns. If the call is interrupted (a killed detached build whose
# completion never arrives), the token is left armed and would otherwise freeze
# a stale 🔨 in the title bar across the next phase transition. The phase
# writers therefore clear a stale build-busy token before persisting each
# current_phase write. The clear is scoped to build-busy only — the live
# lock-coordination tokens (lock-waiting / lock-owned) must survive untouched.


def test_transition_clears_stale_build_busy_token(plan_context):
    """``cmd_transition`` pops a stale build-busy token before the phase write."""
    plan_id = 'tt-transition-build-busy'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases=_PHASES, force=False))
    cmd_title_token(Namespace(plan_id=plan_id, token_verb='set', state='build-busy'))

    result = cmd_transition(Namespace(plan_id=plan_id, completed='1-init'))

    assert result['status'] == 'success', f'transition failed: {result}'
    stored = _read_status(plan_context, plan_id)
    assert stored['current_phase'] == '2-refine'
    assert 'title_token' not in stored, (
        f"Expected build-busy title_token cleared after transition, but found "
        f"{stored.get('title_token')!r}."
    )


def test_set_phase_forward_and_loopback_clear_build_busy(plan_context):
    """``cmd_set_phase`` clears build-busy on both a forward move and a
    backward loop-back re-entry."""
    plan_id = 'tt-set-phase-build-busy'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases=_PHASES, force=False))

    # Forward move: 1-init -> 3-outline.
    cmd_title_token(Namespace(plan_id=plan_id, token_verb='set', state='build-busy'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='3-outline'))
    stored = _read_status(plan_context, plan_id)
    assert stored['current_phase'] == '3-outline'
    assert 'title_token' not in stored, (
        f"Expected build-busy cleared after forward set-phase, found "
        f"{stored.get('title_token')!r}."
    )

    # Backward loop-back: 3-outline -> 2-refine.
    cmd_title_token(Namespace(plan_id=plan_id, token_verb='set', state='build-busy'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))
    stored = _read_status(plan_context, plan_id)
    assert stored['current_phase'] == '2-refine'
    assert 'title_token' not in stored, (
        f"Expected build-busy cleared after loop-back set-phase, found "
        f"{stored.get('title_token')!r}."
    )


def test_lock_tokens_preserved_across_transition_and_set_phase(plan_context):
    """The clear is scoped to build-busy — a live lock token survives both
    phase writers untouched (the live coordination signal is not weakened)."""
    # lock-owned survives cmd_transition.
    plan_id = 'tt-lock-owned-preserved'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases=_PHASES, force=False))
    cmd_title_token(Namespace(plan_id=plan_id, token_verb='set', state='lock-owned'))
    cmd_transition(Namespace(plan_id=plan_id, completed='1-init'))
    stored = _read_status(plan_context, plan_id)
    assert stored['title_token'] == 'lock-owned', (
        f"Expected lock-owned preserved across transition, found "
        f"{stored.get('title_token')!r}."
    )

    # lock-waiting survives cmd_set_phase.
    plan_id = 'tt-lock-waiting-preserved'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases=_PHASES, force=False))
    cmd_title_token(Namespace(plan_id=plan_id, token_verb='set', state='lock-waiting'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))
    stored = _read_status(plan_context, plan_id)
    assert stored['title_token'] == 'lock-waiting', (
        f"Expected lock-waiting preserved across set-phase, found "
        f"{stored.get('title_token')!r}."
    )


def test_killed_detached_build_busy_token_does_not_stay_armed(plan_context):
    """Killed-detached-build repro: arm build-busy, take no clear action (the
    orchestration call whose completion never arrives), then transition — the
    token must not stay armed indefinitely."""
    plan_id = 'tt-killed-detached-build'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases=_PHASES, force=False))
    # Arm build-busy as the orchestration layer would before a long-running
    # build, then simulate the killed detached build: no clear ever fires.
    cmd_title_token(Namespace(plan_id=plan_id, token_verb='set', state='build-busy'))
    armed = _read_status(plan_context, plan_id)
    assert armed['title_token'] == 'build-busy'

    # The next phase transition must not carry the stale token forward.
    cmd_transition(Namespace(plan_id=plan_id, completed='1-init'))
    stored = _read_status(plan_context, plan_id)
    assert 'title_token' not in stored, (
        f"A killed detached build left build-busy armed and the transition "
        f"failed to clear it — found {stored.get('title_token')!r}."
    )


# =============================================================================
# drive seam: a non-delivered title repaint is observable, not DEBUG-swallowed
# =============================================================================
#
# ``_drive_repaint`` delegates the push to platform-runtime through the executor.
# When the delegate reports ``pushed: false`` with a reason OTHER than
# ``no_title_state`` — in practice ``no_controlling_tty``, the /dev/tty fallback
# channel failing to reach a terminal — the seam emits ONE WARNING naming the
# plan and the reason. Every other path stays at DEBUG, and the seam never alters
# the command's status or exit code.

_LOGGER_NAME = _core.logger.name


def _repaint_reply(**fields):
    """Build a CompletedProcess carrying a push-title-token TOON reply."""
    lines = ['status: success', 'operation: session push-title-token']
    lines += [f'{key}: {value}' for key, value in fields.items()]
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout='\n'.join(lines) + '\n', stderr=''
    )


def test_repaint_warns_when_delegate_reports_no_controlling_tty(monkeypatch, caplog):
    """A ``no_controlling_tty`` reply emits exactly one WARNING naming plan + reason."""
    monkeypatch.setattr(
        _core,
        '_run_executor',
        lambda *_args: _repaint_reply(
            plan_id='tt-repaint-warn',
            pushed='false',
            reason='no_controlling_tty',
            delivery='dev_tty_fallback',
        ),
    )

    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        _core._drive_repaint('tt-repaint-warn')

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert 'tt-repaint-warn' in message
    assert 'no_controlling_tty' in message


def test_repaint_does_not_warn_when_delegate_reports_no_title_state(monkeypatch, caplog):
    """``no_title_state`` is the ordinary nothing-to-paint case — no WARNING."""
    monkeypatch.setattr(
        _core,
        '_run_executor',
        lambda *_args: _repaint_reply(plan_id='tt-repaint-nostate', pushed='false', reason='no_title_state'),
    )

    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        _core._drive_repaint('tt-repaint-nostate')

    assert [r for r in caplog.records if r.levelno == logging.WARNING] == []


def test_repaint_does_not_warn_on_successful_push(monkeypatch, caplog):
    """A landed push (``pushed: true``) emits no WARNING."""
    monkeypatch.setattr(
        _core,
        '_run_executor',
        lambda *_args: _repaint_reply(
            plan_id='tt-repaint-ok', pushed='true', delivery='dev_tty_fallback'
        ),
    )

    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        _core._drive_repaint('tt-repaint-ok')

    assert [r for r in caplog.records if r.levelno == logging.WARNING] == []


def test_repaint_does_not_warn_when_delegate_was_skipped(monkeypatch, caplog):
    """A skipped spawn (``_run_executor`` returned None) emits no WARNING."""
    monkeypatch.setattr(_core, '_run_executor', lambda *_args: None)

    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        _core._drive_repaint('tt-repaint-skipped')

    assert [r for r in caplog.records if r.levelno == logging.WARNING] == []


def test_crashing_delegate_leaves_transition_outcome_unchanged(plan_context, monkeypatch):
    """A delegate that crashes outright never changes the status-write outcome.

    ``_surface_drive`` is fully exception-swallowing, so a raising delegate must
    leave ``cmd_transition`` returning ``status: success`` with the phase advanced
    exactly as it would with a healthy seam.
    """

    def _boom(*_args):
        raise RuntimeError('delegate exploded')

    # Patch the seam's own module globals so the substitution reaches the
    # _status_core instance cmd_transition actually calls into.
    monkeypatch.setitem(_lifecycle._surface_drive.__globals__, '_run_executor', _boom)

    plan_id = 'tt-repaint-crash'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases=_PHASES, force=False))
    result = cmd_transition(Namespace(plan_id=plan_id, completed='1-init'))

    assert result['status'] == 'success'
    stored = _read_status(plan_context, plan_id)
    assert stored['current_phase'] == '2-refine'
