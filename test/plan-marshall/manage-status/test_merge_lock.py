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
