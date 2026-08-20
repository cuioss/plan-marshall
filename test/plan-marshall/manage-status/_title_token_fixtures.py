#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``title token`` test modules.

Holds the module-level loads, constants and helpers those modules
share. The contract they pin, in full:

Tests for the field-only ``title-token`` verb of manage-status.py.

The ``title-token`` verb persists a structured ``{owner, state, set_at}``
record into ``status.title_token`` and performs NO rendering — the composition
(glyph vocabulary + ``{icon} {body}`` assembly) lives in
``manage-terminal-title``. These tests cover:

- ``set`` writes the record for each of the three ``TITLE_TOKEN_STATES``,
  stamped with the caller's owner and a fresh ``set_at``.
- Last-writer arbitration: a ``set`` from ANY owner replaces the record
  wholesale, while ``clear`` is OWNER-SCOPED — a foreign clear is a reported
  no-op.
- Aged-token staleness: a record older than
  ``TITLE_TOKEN_STALE_AFTER_SECONDS`` reads as absent and may be cleared by
  ANY owner. Staleness is READ-side — the phase writers perform no sweep.
- ``clear`` removes the ``title_token`` field, and is idempotent when the
  field is already absent.
- An invalid ``--state`` / ``--owner`` is rejected by argparse (exit code 2)
  before the command body runs.
- The verb writes NO ``title-body.txt`` rendering artifact — manage-status is
  field-only.

The record shape, owner vocabulary, arbitration rule, and staleness threshold
are specified in
``manage-terminal-title/standards/terminal-title-architecture.md``
§ Channel Delivery Contract ruling (c).
"""


import json
import subprocess
from argparse import Namespace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from conftest import get_script_path, load_script_module

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


TITLE_TOKEN_OWNERS = _core.TITLE_TOKEN_OWNERS


TITLE_TOKEN_STALE_AFTER_SECONDS = _core.TITLE_TOKEN_STALE_AFTER_SECONDS


title_token_is_stale = _core.title_token_is_stale


read_title_token = _core.read_title_token


# A multi-phase plan whose adjacent transitions never reach the 6-finalize
# blocking boundary, so cmd_transition performs a plain phase advance (no
# strict-verify guard) — the surface the phase-writer tests exercise.
_PHASES = '1-init,2-refine,3-outline'


# The three canonical title-token states: the two lock-coordination phases
# (lock-waiting / lock-owned) plus the orchestration-busy state (build-busy).
# Asserted explicitly here so a silent change to TITLE_TOKEN_STATES surfaces
# as a test failure rather than passing vacuously.
EXPECTED_STATES = frozenset({'lock-waiting', 'lock-owned', 'build-busy'})


# The three owners that may write a title token, likewise asserted explicitly.
EXPECTED_OWNERS = frozenset({'build-hook', 'merge-lock', 'cli'})


def _read_status(plan_context, plan_id):
    """Read the on-disk status.json for ``plan_id`` as a dict."""
    status_file = plan_context.plan_dir_for(plan_id) / 'status.json'
    return json.loads(status_file.read_text(encoding='utf-8'))


def _set(plan_id, state, owner='cli'):
    """Invoke ``title-token set`` for ``plan_id`` as ``owner``."""
    return cmd_title_token(
        Namespace(plan_id=plan_id, token_verb='set', state=state, owner=owner)
    )


def _clear(plan_id, owner='cli'):
    """Invoke ``title-token clear`` for ``plan_id`` as ``owner``."""
    return cmd_title_token(Namespace(plan_id=plan_id, token_verb='clear', owner=owner))


def _age_token(plan_context, plan_id, seconds):
    """Backdate the stored token's ``set_at`` by ``seconds``, in place."""
    status_file = plan_context.plan_dir_for(plan_id) / 'status.json'
    status = json.loads(status_file.read_text(encoding='utf-8'))
    aged = datetime.now(UTC) - timedelta(seconds=seconds)
    status['title_token']['set_at'] = aged.strftime('%Y-%m-%dT%H:%M:%SZ')
    status_file.write_text(json.dumps(status), encoding='utf-8')


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


# =============================================================================
# drive seam: the state settle reports no delivery, because it delivers nothing
# =============================================================================
#
# ``_drive_repaint`` delegates a ``session push-title-token`` to platform-runtime
# through the executor. That seam BINDS AND PERSISTS — it does not repaint: the
# direct /dev/tty write is deleted, so the paired repaint is deferred to the next
# hook render event. The seam consequently has NO delivery outcome to report and
# writes NO non-delivery work-log entry: the only reply it can receive is the
# ordinary ``no_title_state`` nothing-to-settle case, which stays at DEBUG. The
# seam never alters the command's status or exit code.


def _log_entry_spy():
    """Build a ``log_entry`` spy plus the list it appends each call to.

    Returns ``(calls, spy)`` where ``spy`` matches ``plan_logging.log_entry``'s
    signature and records ``(log_type, plan_id, level, message)`` per call. The
    caller installs the spy in the namespace the code under test resolves
    ``log_entry`` from — ``_core`` for the direct drive-seam unit tests, or
    ``_lifecycle._drive_*.__globals__`` for the cmd_archive integration test —
    so the substitution reaches the instance actually called.
    """
    calls: list[tuple[str, str, str, str]] = []

    def spy(log_type, plan_id, level, message, store='plans'):
        calls.append((log_type, plan_id, level, message))

    return calls, spy


def _read_work_log(plan_context, plan_id):
    """Return the plan's persisted work.log text (empty string when absent)."""
    log_file = plan_context.plan_dir_for(plan_id) / 'logs' / 'work.log'
    if not log_file.exists():
        return ''
    return log_file.read_text(encoding='utf-8')


def _repaint_reply(**fields):
    """Build a CompletedProcess carrying a push-title-token TOON reply."""
    lines = ['status: success', 'operation: session push-title-token']
    lines += [f'{key}: {value}' for key, value in fields.items()]
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout='\n'.join(lines) + '\n', stderr=''
    )
