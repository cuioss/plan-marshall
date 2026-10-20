#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A status writer cannot overwrite the integrity record.

A ``write_status`` caller commits a whole document assembled from a snapshot read
taken before it takes the status guard. The outside-the-file keys
(``criteria_integrity`` and ``functional_review_override_heads``) are written by
their own owning verbs through that same guard, so a writer that read before such
a commit and writes after it would otherwise restore its stale copy and drop the
record. These tests reproduce that ordering directly.
"""

from __future__ import annotations

import json
from pathlib import Path

import _cmd_loop_back as _loop_back
import _criteria_snapshot as _snap
import _status_core as _core

PLAN_ID = 'lb77-integrity-carry-d1'
HEAD = 'a' * 40


def _plan(plan_context) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    status = {
        'title': 'fixture',
        'phases': [{'name': '1-init', 'status': 'in_progress'}],
        'current_phase': '1-init',
        'metadata': {'use_worktree': False},
    }
    (plan_dir / 'status.json').write_text(json.dumps(status), encoding='utf-8')
    return plan_dir


def _metadata(plan_dir: Path) -> dict:
    return json.loads((plan_dir / 'status.json').read_text(encoding='utf-8')).get('metadata') or {}


def test_a_writer_that_read_before_the_integrity_record_keeps_it(plan_context) -> None:
    """The block committed inside the guard survives the stale writer's commit.

    The writer's own unprotected mutation still lands, so the carry is surgical
    rather than a whole-document re-read that would discard the caller's intent.
    """
    plan_dir = _plan(plan_context)
    stale = _core.read_status(PLAN_ID)

    assert _snap.record_integrity(PLAN_ID, snapshot_frozen=True, snapshot_digest='deadbeef')
    stale['metadata']['change_type'] = 'feature'

    _core.write_status(PLAN_ID, stale)

    stored = _metadata(plan_dir)
    assert stored[_snap.INTEGRITY_KEY]['snapshot_frozen'] is True
    assert stored[_snap.INTEGRITY_KEY]['snapshot_digest'] == 'deadbeef'
    assert stored['change_type'] == 'feature'


def test_the_live_integrity_block_wins_over_the_callers_stale_copy(plan_context) -> None:
    """A stale copy of the block in the caller's document cannot resurrect itself."""
    plan_dir = _plan(plan_context)
    stale = _core.read_status(PLAN_ID)
    stale['metadata'][_snap.INTEGRITY_KEY] = {'snapshot_frozen': False}

    assert _snap.record_integrity(PLAN_ID, snapshot_frozen=True)

    _core.write_status(PLAN_ID, stale)

    assert _metadata(plan_dir)[_snap.INTEGRITY_KEY]['snapshot_frozen'] is True


def test_a_writer_cannot_drop_an_override_head_appended_meanwhile(plan_context) -> None:
    """``loop-back close``'s append survives a writer that read before it."""
    plan_dir = _plan(plan_context)
    stale = _core.read_status(PLAN_ID)

    changed, error = _loop_back._record_override_head(PLAN_ID, _loop_back.FUNCTIONAL_REVIEW_STEP, HEAD)
    assert (changed, error) == (True, None)

    _core.write_status(PLAN_ID, stale)

    assert _metadata(plan_dir)[_snap.OVERRIDE_HEADS_KEY] == [HEAD]
