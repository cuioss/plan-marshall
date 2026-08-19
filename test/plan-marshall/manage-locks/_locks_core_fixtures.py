#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``locks core`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from __future__ import annotations

from conftest import load_script_module

_mod = load_script_module('plan-marshall', 'manage-locks', '_locks_core.py', '_locks_core_under_test')


holder_is_dead = _mod.holder_is_dead


holder_has_live_worktree = _mod.holder_has_live_worktree


holder_staleness = _mod.holder_staleness


rmw_json = _mod.rmw_json


_read_json_or_empty = _mod._read_json_or_empty


_acquire_guard = _mod._acquire_guard


_atomic_write_json = _mod._atomic_write_json


log_lock_event = _mod.log_lock_event


_resolve_lock_log_path = _mod._resolve_lock_log_path


# =============================================================================
# [LOCK] event emission — log_lock_event + _resolve_lock_log_path
# =============================================================================
#
# These tests stage their OWN isolated main-anchored base under tmp_path (the
# same `tmp_path/main/.plan/local` PLAN_BASE_DIR pattern the merge_lock /
# build_queue suites use). The autouse `plan_context` redirect points
# PLAN_BASE_DIR at the shared `tmp_path`, whose `.parent/logs` dir would be
# shared across tests — so a per-test isolated base is required for the
# exact-content assertions below to be deterministic under `-n auto`.


def _lock_log_base(tmp_path, monkeypatch):
    """Stage an isolated PLAN_BASE_DIR; return (base, lock_log_path).

    Under PLAN_BASE_DIR the [LOCK] log resolves to
    ``<base>.parent / logs / lock-{date}.log`` (i.e. ``<tmp>/main/.plan/logs``),
    unique per test so the append/content assertions are deterministic.
    """
    base = tmp_path / 'main' / '.plan' / 'local'
    base.mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return base, _resolve_lock_log_path()
