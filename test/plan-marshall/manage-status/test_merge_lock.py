#!/usr/bin/env python3
"""Tests for manage-status.py merge-lock subcommand.

The merge-lock verb (``acquire`` / ``check`` / ``release``) implements the
cross-plan merge-coordination mutex from the phase-6-finalize merge
coordination deliverable. The marker is a cooperative field under
``status.metadata`` of the acquiring plan; ``acquire`` blocks via a
``time.sleep`` poll loop whose window and interval are module-level
constants the tests monkeypatch to keep the suite fast.

Each test uses a unique ``plan_id`` (with the ``plan_context`` fixture's
``plan_dir_for`` helper) so ``PlanContext`` isolation holds even when the
fixture directory is shared across tests.
"""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

from conftest import PROJECT_ROOT

_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-status'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module('_cmd_merge_lock_under_test', '_cmd_merge_lock.py')
cmd_merge_lock_acquire = _mod.cmd_merge_lock_acquire
cmd_merge_lock_check = _mod.cmd_merge_lock_check
cmd_merge_lock_release = _mod.cmd_merge_lock_release


def _ns(plan_id: str) -> Namespace:
    return Namespace(plan_id=plan_id)


def _write_status(plan_dir: Path, *, metadata: dict | None = None) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps(
            {
                'plan_id': plan_dir.name,
                'title': plan_dir.name,
                'current_phase': '6-finalize',
                'phases': [],
                'metadata': metadata or {},
            }
        ),
        encoding='utf-8',
    )


def _read_metadata(plan_dir: Path) -> dict:
    data = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    return data.get('metadata', {})


# =============================================================================
# acquire on free lock
# =============================================================================


def test_acquire_on_free_returns_acquired_and_writes_marker(plan_context):
    plan_dir = plan_context.plan_dir_for('ml-acquire-free')
    _write_status(plan_dir)

    result = cmd_merge_lock_acquire(_ns('ml-acquire-free'))

    assert result['status'] == 'acquired'
    assert result['plan_id'] == 'ml-acquire-free'
    assert 'acquired_at' in result

    metadata = _read_metadata(plan_dir)
    assert metadata['merging_on_main'] is True
    assert metadata['merge_lock_acquired_at'] == result['acquired_at']


def test_acquire_missing_plan_dir_returns_error(plan_context):
    # No status written → plan dir does not exist.
    result = cmd_merge_lock_acquire(_ns('ml-no-such-plan'))
    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


# =============================================================================
# check
# =============================================================================


def test_check_reflects_free_when_no_holder(plan_context):
    plan_dir = plan_context.plan_dir_for('ml-check-free')
    _write_status(plan_dir)

    result = cmd_merge_lock_check(_ns('ml-check-free'))

    assert result['status'] == 'free'
    assert result['plan_id'] == 'ml-check-free'


def test_check_reflects_self_held(plan_context):
    plan_dir = plan_context.plan_dir_for('ml-check-self')
    _write_status(plan_dir)
    cmd_merge_lock_acquire(_ns('ml-check-self'))

    result = cmd_merge_lock_check(_ns('ml-check-self'))

    assert result['status'] == 'held'
    assert result['holder_plan_id'] == 'ml-check-self'


def test_check_reflects_other_holder(plan_context):
    holder_dir = plan_context.plan_dir_for('ml-check-holder')
    querier_dir = plan_context.plan_dir_for('ml-check-querier')
    _write_status(holder_dir)
    _write_status(querier_dir)
    cmd_merge_lock_acquire(_ns('ml-check-holder'))

    result = cmd_merge_lock_check(_ns('ml-check-querier'))

    assert result['status'] == 'held'
    assert result['holder_plan_id'] == 'ml-check-holder'


# =============================================================================
# release (and idempotence)
# =============================================================================


def test_release_clears_marker(plan_context):
    plan_dir = plan_context.plan_dir_for('ml-release')
    _write_status(plan_dir)
    cmd_merge_lock_acquire(_ns('ml-release'))

    result = cmd_merge_lock_release(_ns('ml-release'))

    assert result['status'] == 'success'
    assert result['released'] is True
    metadata = _read_metadata(plan_dir)
    assert 'merging_on_main' not in metadata
    assert 'merge_lock_acquired_at' not in metadata


def test_release_idempotent_second_release_is_noop(plan_context):
    plan_dir = plan_context.plan_dir_for('ml-release-idem')
    _write_status(plan_dir)
    cmd_merge_lock_acquire(_ns('ml-release-idem'))
    cmd_merge_lock_release(_ns('ml-release-idem'))

    # Second release: marker already gone → no-op, released False.
    result = cmd_merge_lock_release(_ns('ml-release-idem'))

    assert result['status'] == 'success'
    assert result['released'] is False


def test_release_when_never_held_is_noop(plan_context):
    plan_dir = plan_context.plan_dir_for('ml-release-never')
    _write_status(plan_dir)

    result = cmd_merge_lock_release(_ns('ml-release-never'))

    assert result['status'] == 'success'
    assert result['released'] is False


# =============================================================================
# contention (blocked path with patched short window)
# =============================================================================


def test_acquire_while_held_returns_blocked(plan_context, monkeypatch):
    holder_dir = plan_context.plan_dir_for('ml-contend-holder')
    waiter_dir = plan_context.plan_dir_for('ml-contend-waiter')
    _write_status(holder_dir)
    _write_status(waiter_dir)

    # Plan A holds the lock.
    cmd_merge_lock_acquire(_ns('ml-contend-holder'))

    # Patch the poll window/interval to sub-second values so the blocked path
    # resolves fast instead of waiting the full 5 minutes.
    monkeypatch.setattr(_mod, 'MERGE_LOCK_POLL_WINDOW_SECONDS', 0.05)
    monkeypatch.setattr(_mod, 'MERGE_LOCK_POLL_INTERVAL_SECONDS', 0.01)

    result = cmd_merge_lock_acquire(_ns('ml-contend-waiter'))

    assert result['status'] == 'blocked'
    assert result['blocking_plan_id'] == 'ml-contend-holder'
    # Waiter must NOT have written its own marker on the blocked path.
    assert 'merging_on_main' not in _read_metadata(waiter_dir)


def test_release_then_acquire_succeeds(plan_context, monkeypatch):
    holder_dir = plan_context.plan_dir_for('ml-rta-holder')
    waiter_dir = plan_context.plan_dir_for('ml-rta-waiter')
    _write_status(holder_dir)
    _write_status(waiter_dir)

    cmd_merge_lock_acquire(_ns('ml-rta-holder'))
    cmd_merge_lock_release(_ns('ml-rta-holder'))

    monkeypatch.setattr(_mod, 'MERGE_LOCK_POLL_WINDOW_SECONDS', 0.05)
    monkeypatch.setattr(_mod, 'MERGE_LOCK_POLL_INTERVAL_SECONDS', 0.01)

    # With the holder released, the waiter acquires immediately.
    result = cmd_merge_lock_acquire(_ns('ml-rta-waiter'))

    assert result['status'] == 'acquired'
    assert _read_metadata(waiter_dir)['merging_on_main'] is True


# =============================================================================
# concurrent-acquire TOCTOU tiebreaker
# =============================================================================
#
# Two plans can both observe holder=None and both write their marker before
# either re-reads (check-then-act race). The fix re-reads after writing and
# resolves the contention deterministically: the lexicographically LARGER
# plan_id yields (clears its marker, keeps polling); the smaller wins.
#
# The race is simulated single-threaded by monkeypatching _write_marker so the
# competing plan's marker materialises during the window between the calling
# plan's first holder check (None) and the post-write double-check.


def _inject_competitor_on_write(monkeypatch, *, competitor_plan_id):
    """Patch _write_marker so the competitor's marker appears concurrently.

    Wraps the real _write_marker: after the calling plan writes its own marker,
    the competitor's marker is also written directly into the competitor's
    status.json — reproducing the state where both plans wrote in the same
    check-then-act window. Done only once (subsequent writes pass through) so
    later poll iterations see a stable world.
    """
    real_write_marker = _mod._write_marker
    state = {'injected': False}

    def _patched(plan_id):
        acquired_at = real_write_marker(plan_id)
        if not state['injected'] and plan_id != competitor_plan_id:
            state['injected'] = True
            comp_status = _mod.read_status(competitor_plan_id)
            comp_status.setdefault('metadata', {})
            comp_status['metadata'][_mod._MARKER_FIELD] = True
            comp_status['metadata'][_mod._ACQUIRED_AT_FIELD] = acquired_at
            _mod.write_status(competitor_plan_id, comp_status)
        return acquired_at

    monkeypatch.setattr(_mod, '_write_marker', _patched)


def test_concurrent_acquire_larger_plan_id_yields(plan_context, monkeypatch):
    # 'ml-tie-bbb' (larger) races against 'ml-tie-aaa' (smaller). The larger
    # plan_id must yield: clear its marker and end up blocked, since the
    # competitor holds the lock for the remainder of the poll window.
    aaa_dir = plan_context.plan_dir_for('ml-tie-aaa')
    bbb_dir = plan_context.plan_dir_for('ml-tie-bbb')
    _write_status(aaa_dir)
    _write_status(bbb_dir)

    monkeypatch.setattr(_mod, 'MERGE_LOCK_POLL_WINDOW_SECONDS', 0.05)
    monkeypatch.setattr(_mod, 'MERGE_LOCK_POLL_INTERVAL_SECONDS', 0.01)
    # When 'ml-tie-bbb' writes its marker, 'ml-tie-aaa' concurrently writes too.
    _inject_competitor_on_write(monkeypatch, competitor_plan_id='ml-tie-aaa')

    result = cmd_merge_lock_acquire(_ns('ml-tie-bbb'))

    # The larger plan_id yields → it cleared its own marker and (since the
    # competitor still holds) eventually times out blocked.
    assert result['status'] == 'blocked'
    assert result['blocking_plan_id'] == 'ml-tie-aaa'
    assert 'merging_on_main' not in _read_metadata(bbb_dir)


def test_concurrent_acquire_smaller_plan_id_wins(plan_context, monkeypatch):
    # 'ml-tie2-aaa' (smaller) races against 'ml-tie2-bbb' (larger). The smaller
    # plan_id keeps its marker and returns acquired even though a competitor
    # wrote concurrently.
    aaa_dir = plan_context.plan_dir_for('ml-tie2-aaa')
    bbb_dir = plan_context.plan_dir_for('ml-tie2-bbb')
    _write_status(aaa_dir)
    _write_status(bbb_dir)

    monkeypatch.setattr(_mod, 'MERGE_LOCK_POLL_WINDOW_SECONDS', 0.05)
    monkeypatch.setattr(_mod, 'MERGE_LOCK_POLL_INTERVAL_SECONDS', 0.01)
    # When 'ml-tie2-aaa' writes, 'ml-tie2-bbb' concurrently writes too.
    _inject_competitor_on_write(monkeypatch, competitor_plan_id='ml-tie2-bbb')

    result = cmd_merge_lock_acquire(_ns('ml-tie2-aaa'))

    # The smaller plan_id wins: keeps its marker, returns acquired.
    assert result['status'] == 'acquired'
    assert _read_metadata(aaa_dir)['merging_on_main'] is True


def test_concurrent_acquire_no_competitor_returns_acquired(plan_context, monkeypatch):
    # Sanity: when the post-write double-check finds no competitor (the common
    # case), acquire returns acquired with the marker intact — the new
    # re-read path must not regress the uncontended fast path.
    plan_dir = plan_context.plan_dir_for('ml-tie-solo')
    _write_status(plan_dir)

    monkeypatch.setattr(_mod, 'MERGE_LOCK_POLL_WINDOW_SECONDS', 0.05)
    monkeypatch.setattr(_mod, 'MERGE_LOCK_POLL_INTERVAL_SECONDS', 0.01)

    result = cmd_merge_lock_acquire(_ns('ml-tie-solo'))

    assert result['status'] == 'acquired'
    assert _read_metadata(plan_dir)['merging_on_main'] is True
