#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A status writer cannot overwrite the integrity record.

A ``write_status`` caller commits a whole document assembled from a snapshot read
taken before it takes the status guard. The outside-the-file keys
(``criteria_integrity`` and ``functional_review_override_heads``) are written by
their own owning verbs through that same guard, so a writer that read before such
a commit and writes after it would otherwise restore its stale copy and drop the
record. These tests reproduce that ordering directly.

The tests drive the seam the fix lives in — ``write_status`` — rather than the
CLI verbs: ``loop-back close`` and ``mark-step-done`` are two of the
full-document writers that commit through this one seam, and the seam is what
covers every one of them. The writers are enumerated in ``write_status``'s own
docstring, and
``test_every_full_document_writer_is_named_in_the_write_status_docstring``
derives that set from the source so the list cannot go stale.

Two failure modes are covered here besides the lost-update race: a write whose
in-guard read FAILED (which is not the same as a document that holds no keys),
and the ``create --force`` seed, whose clean slate is the one write that
deliberately does not carry.
"""

from __future__ import annotations

import json
import re
from contextlib import contextmanager
from pathlib import Path

import _cmd_loop_back as _loop_back
import _criteria_snapshot as _snap
import _locks_core as _locks
import _status_core as _core
import pytest

from conftest import MARKETPLACE_ROOT, load_script_module, parse_ns

PLAN_ID = 'lb77-integrity-carry-d1'
HEAD = 'a' * 40

_STEP_ID = 'default:sonar-roundtrip'
_FINALIZE_STEPS = load_script_module(
    'plan-marshall', 'manage-config', '_cmd_finalize_steps.py', '_rb_lb82_finalize_steps'
)
_LIFECYCLE = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_rb_lb82_lifecycle')


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


def test_a_key_absent_on_disk_is_removed_from_the_callers_stale_copy(plan_context) -> None:
    """Live absence wins: a write cannot resurrect a key the document no longer holds."""
    plan_dir = _plan(plan_context)
    stale = _core.read_status(PLAN_ID)
    stale['metadata'][_snap.INTEGRITY_KEY] = {'snapshot_frozen': True}
    stale['metadata'][_snap.OVERRIDE_HEADS_KEY] = [HEAD]

    _core.write_status(PLAN_ID, stale)

    stored = _metadata(plan_dir)
    assert _snap.INTEGRITY_KEY not in stored
    assert _snap.OVERRIDE_HEADS_KEY not in stored


def test_an_archive_style_write_still_carries_the_integrity_record(plan_context) -> None:
    """Dropping the title token does not authorise dropping the integrity record."""
    plan_dir = _plan(plan_context)
    stale = _core.read_status(PLAN_ID)
    assert _snap.record_integrity(PLAN_ID, snapshot_frozen=True)

    _core.write_status(PLAN_ID, stale, preserve_title_token=False)

    assert _metadata(plan_dir)[_snap.INTEGRITY_KEY]['snapshot_frozen'] is True


# =============================================================================
# A failed in-guard read is not "the keys are gone"
# =============================================================================


def _plan_with_both_keys(plan_context) -> Path:
    """A plan whose document carries both protected keys."""
    plan_dir = _plan(plan_context)
    assert _snap.record_integrity(PLAN_ID, snapshot_frozen=True, snapshot_digest='deadbeef')
    changed, error = _loop_back._record_override_head(PLAN_ID, _loop_back.FUNCTIONAL_REVIEW_STEP, HEAD)
    assert (changed, error) == (True, None)
    return plan_dir


def _stored(plan_dir: Path) -> dict:
    parsed = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    assert isinstance(parsed, dict)
    return parsed


@pytest.mark.parametrize(
    'reason',
    [_locks.READ_MISSING, _locks.READ_UNREADABLE, _locks.READ_CORRUPT, _locks.READ_NOT_OBJECT],
    ids=['missing', 'unreadable', 'corrupt', 'not_object'],
)
def test_a_failed_in_guard_read_refuses_the_write_and_keeps_the_keys(plan_context, monkeypatch, reason) -> None:
    """No read, no carry: an unreadable document is never rewritten as key-less.

    The failure is injected at the read seam so the document on disk keeps its
    keys in every case — that is the state a writer must not destroy, and a
    writer that read a different failure into it is exactly what this guards.
    """
    plan_dir = _plan_with_both_keys(plan_context)
    stale = _core.read_status(PLAN_ID)
    before = (plan_dir / 'status.json').read_bytes()

    monkeypatch.setattr(_locks, '_read_json_state', lambda path: ({}, reason))

    with pytest.raises(_locks.StateReadFailed) as refused:
        _core.write_status(PLAN_ID, stale)

    assert refused.value.reason == reason
    assert (plan_dir / 'status.json').read_bytes() == before
    stored = _metadata(plan_dir)
    assert stored[_snap.INTEGRITY_KEY]['snapshot_digest'] == 'deadbeef'
    assert stored[_snap.OVERRIDE_HEADS_KEY] == [HEAD]


def test_a_corrupt_document_is_reported_and_left_alone(plan_context) -> None:
    """A document that does not parse is refused, not replaced by the caller's copy."""
    plan_dir = _plan(plan_context)
    corrupt = b'{"title": "half-writ'
    (plan_dir / 'status.json').write_bytes(corrupt)
    stale = _core.read_status(PLAN_ID)

    with pytest.raises(_locks.StateReadFailed) as refused:
        _core.write_status(PLAN_ID, stale)

    assert refused.value.reason == _locks.READ_CORRUPT
    assert (plan_dir / 'status.json').read_bytes() == corrupt


def test_a_write_for_a_plan_with_no_status_document_commits_nothing(plan_context) -> None:
    """A full-document write never invents the document it was meant to update."""
    plan_dir = plan_context.plan_dir_for('lb77-no-status-document')
    assert not (plan_dir / 'status.json').exists()

    with pytest.raises(_locks.StateReadFailed) as refused:
        _core.write_status('lb77-no-status-document', {'title': 'invented'})

    assert refused.value.reason == _locks.READ_MISSING
    assert not (plan_dir / 'status.json').exists()


# =============================================================================
# create --force starts from a clean slate
# =============================================================================


def test_create_force_yields_a_status_without_the_protected_keys(plan_context) -> None:
    """The re-seed does not inherit the overwritten plan's protected keys."""
    plan_dir = _plan_with_both_keys(plan_context)
    assert _metadata(plan_dir)[_snap.INTEGRITY_KEY]

    args = parse_ns(
        'plan-marshall',
        'manage-status',
        'manage-status.py',
        'create',
        '--plan-id',
        PLAN_ID,
        '--title',
        'Re-seeded',
        '--phases',
        '1-init',
        '--force',
    )
    result = _LIFECYCLE.cmd_create(args)

    assert result['status'] == 'success'
    stored = _metadata(plan_dir)
    assert _snap.INTEGRITY_KEY not in stored
    assert _snap.OVERRIDE_HEADS_KEY not in stored
    assert _stored(plan_dir)['title'] == 'Re-seeded'


# =============================================================================
# manage-config finalize-steps set-lane commits through the guarded seam
# =============================================================================


_REAL_HELD_GUARD = _locks.held_guard


@contextmanager
def _guard_with_concurrent_commit(guard_path: Path, armed: list[bool]):
    """Take the guard, after the owning writer commits inside the same window.

    The commit is performed by the REAL ``record_integrity`` BEFORE the guard is
    taken — the only ordering a concurrent owner can actually achieve, since the
    owner takes the same guard. A writer that reads outside the guard has already
    read by this point, so it writes the pre-commit state back; a writer that
    reads inside the guard sees the commit and keeps it.
    """
    if not armed:
        armed.append(True)
        assert _snap.record_integrity(PLAN_ID, snapshot_frozen=True, snapshot_digest='cafebabe')
    with _REAL_HELD_GUARD(guard_path):
        yield


def test_a_block_committed_while_the_lane_write_enters_the_guard_survives(plan_context, monkeypatch) -> None:
    """``finalize-steps set-lane`` does not clobber a commit that beat it to the guard."""
    plan_dir = _plan(plan_context)
    armed: list[bool] = []

    # The wrapper delegates to the real guard through a captured reference, so
    # patching the module attribute cannot recurse into itself.
    monkeypatch.setattr(
        _locks,
        'held_guard',
        lambda guard_path: _guard_with_concurrent_commit(guard_path, armed),
    )

    result = _FINALIZE_STEPS._set_lane_plan_local(PLAN_ID, _STEP_ID, 'standard')

    assert result['status'] == 'success', result
    stored = _metadata(plan_dir)
    assert stored[_snap.INTEGRITY_KEY]['snapshot_digest'] == 'cafebabe'
    assert stored[_FINALIZE_STEPS._PLAN_LOCAL_STEP_MAP_KEY][_STEP_ID]['lane'] == 'standard'


def test_the_lane_write_commits_through_the_guarded_read_modify_write(plan_context, monkeypatch) -> None:
    """The status document is read INSIDE the guard, not before it."""
    plan_dir = _plan_with_both_keys(plan_context)
    calls: list[dict] = []
    real_rmw = _locks.rmw_json

    def _spy(path, mutate, **kwargs):
        calls.append({'path': Path(path), 'kwargs': kwargs})
        return real_rmw(path, mutate, **kwargs)

    monkeypatch.setattr(_locks, 'rmw_json', _spy)
    monkeypatch.setattr(_FINALIZE_STEPS, 'rmw_json', _spy)

    result = _FINALIZE_STEPS._set_lane_plan_local(PLAN_ID, _STEP_ID, 'full')

    assert result['status'] == 'success', result
    assert [call['path'].name for call in calls] == ['status.json']
    assert calls[0]['kwargs'].get('require_readable_state') is True
    stored = _metadata(plan_dir)
    assert stored[_snap.INTEGRITY_KEY]['snapshot_digest'] == 'deadbeef'
    assert stored[_FINALIZE_STEPS._PLAN_LOCAL_STEP_MAP_KEY][_STEP_ID]['lane'] == 'full'


def test_a_malformed_override_map_is_refused_without_touching_the_document(plan_context) -> None:
    """The shape refusal still aborts the write — now from inside the mutator."""
    plan_dir = _plan(plan_context)
    document = _stored(plan_dir)
    document['metadata'][_FINALIZE_STEPS._PLAN_LOCAL_STEP_MAP_KEY] = 'not-a-map'
    (plan_dir / 'status.json').write_text(json.dumps(document), encoding='utf-8')
    before = (plan_dir / 'status.json').read_bytes()

    result = _FINALIZE_STEPS._set_lane_plan_local(PLAN_ID, _STEP_ID, 'off')

    assert result['status'] == 'error'
    assert _FINALIZE_STEPS._PLAN_LOCAL_STEP_MAP_KEY in result['error']
    assert (plan_dir / 'status.json').read_bytes() == before


# =============================================================================
# The writer list in write_status's docstring stays true
# =============================================================================

#: ``write_status(`` at the start of a statement — a CALL. Prose and import lines
#: are excluded, so the scan names only files that commit a whole document.
_WRITE_CALL_RE = re.compile(r'^\s*write_status\(', re.MULTILINE)


def test_every_full_document_writer_is_named_in_the_write_status_docstring() -> None:
    """A new full-document writer is discoverable from the seam's own docstring.

    Derived from the source rather than pinned as a literal: the point of the
    list is that adding a writer without naming it here is a test failure, and a
    hand-maintained expected set would invert that.
    """
    docstring = _core.write_status.__doc__ or ''
    callers = {
        path.stem
        for path in MARKETPLACE_ROOT.glob('*/skills/*/scripts/*.py')
        if _WRITE_CALL_RE.search(path.read_text(encoding='utf-8'))
    }
    callers.discard('_status_core')  # the seam itself

    unnamed = sorted(stem for stem in callers if stem not in docstring)

    assert not unnamed, f'write_status docstring does not name these callers: {unnamed}'
