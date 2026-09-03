#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for ``manage-locks/build_queue.py`` — the bounded-``k``-slot build-queue
concurrency limiter with a FIFO waiting queue.
"""


from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest
from _build_queue_fixtures import (
    SCRIPT_PATH,
    _init_git_repo,
    _make_live_plan,
    _read_queue,
    _set_max_slots,
    _write_queue,
    build_queue,
    isolated_base,
)

# =============================================================================
# Corrupt / missing file resilience
# =============================================================================


class TestCorruptFileAsEmpty:
    def test_missing_queue_file_treated_as_empty(self, isolated_base: dict) -> None:
        # No queue file exists yet — the first acquire builds it from scratch.
        assert not isolated_base['queue_path'].exists()
        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert result['admission'] == 'admitted'
        assert isolated_base['queue_path'].is_file()

    def test_corrupt_queue_file_treated_as_empty(self, isolated_base: dict) -> None:
        isolated_base['queue_path'].write_text('{ not json', encoding='utf-8')
        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert result['admission'] == 'admitted'
        assert result['active_count'] == 1


# =============================================================================
# Dead-holder reclamation (liveness via the shared _locks_core.holder_is_dead)
# =============================================================================


class TestDeadHolderReclamation:
    def test_dead_active_holder_is_pruned_freeing_a_slot(self, isolated_base: dict) -> None:
        _set_max_slots(isolated_base['base'], 1)
        # plan-dead acquires the only slot but its plan dir is NEVER created → dead.
        build_queue.run_acquire(Namespace(plan_id='plan-dead'))

        # plan-live acquires: the dead holder is pruned, freeing the slot → admitted.
        _make_live_plan(isolated_base['base'], 'plan-live')
        result = build_queue.run_acquire(Namespace(plan_id='plan-live'))
        assert result['admission'] == 'admitted'
        assert result['active_count'] == 1

        state = _read_queue(isolated_base['queue_path'])
        assert [e['plan_id'] for e in state['active']] == ['plan-live']

    def test_live_active_holder_is_not_pruned(self, isolated_base: dict) -> None:
        _set_max_slots(isolated_base['base'], 1)
        _make_live_plan(isolated_base['base'], 'plan-live')
        build_queue.run_acquire(Namespace(plan_id='plan-live'))

        # A second live plan finds the slot occupied by a LIVE holder → blocked.
        _make_live_plan(isolated_base['base'], 'plan-b')
        result = build_queue.run_acquire(Namespace(plan_id='plan-b'))
        assert result['admission'] == 'blocked'


# =============================================================================
# Foreign-project holder pruning (machine-global project_root stamping)
# =============================================================================
#
# The machine-global queue records holders from multiple checkouts. Each active
# entry's stamped project_root judges its liveness against the checkout it
# originated in, so a foreign project's LIVE holder is never reclaimed by a
# session running in a different repo, while a foreign DEAD holder still is.


class TestForeignProjectHolderPrune:
    def test_foreign_project_live_holder_is_not_pruned(
        self, isolated_base: dict, tmp_path: Path
    ) -> None:
        import time

        base = isolated_base['base']
        _set_max_slots(base, 1)

        # A holder recorded by project A, LIVE under A's checkout (a DIFFERENT
        # checkout than this session's isolated_base['main_repo']).
        foreign_root = tmp_path / 'foreign-project'
        (foreign_root / '.plan' / 'local' / 'plans' / 'foreign-holder').mkdir(parents=True)
        foreign_id = 'foreign-holder:foreign-uuid'
        _write_queue(
            isolated_base['queue_path'],
            {
                'active': [
                    {
                        'id': foreign_id,
                        'plan_id': 'foreign-holder',
                        'ts': 0.0,
                        'active_since': time.time(),
                        'project_root': str(foreign_root),
                    }
                ],
                'waiting': [],
                'run_log': [],
            },
        )

        # A local plan acquires: the foreign holder is judged against ITS
        # project_root (where it is live) → NOT pruned → the single slot stays
        # held → local plan is blocked.
        _make_live_plan(base, 'local-plan')
        result = build_queue.run_acquire(Namespace(plan_id='local-plan'))
        assert result['admission'] == 'blocked'

        state = _read_queue(isolated_base['queue_path'])
        assert foreign_id in [e['id'] for e in state['active']]

    def test_foreign_project_dead_holder_is_pruned(
        self, isolated_base: dict, tmp_path: Path
    ) -> None:
        import time

        base = isolated_base['base']
        _set_max_slots(base, 1)

        # A holder recorded by project A but ABSENT under A's checkout → dead.
        foreign_root = tmp_path / 'foreign-project'
        (foreign_root / '.plan' / 'local' / 'plans').mkdir(parents=True)  # no holder dir
        dead_id = 'foreign-dead:foreign-uuid'
        _write_queue(
            isolated_base['queue_path'],
            {
                'active': [
                    {
                        'id': dead_id,
                        'plan_id': 'foreign-dead',
                        'ts': 0.0,
                        'active_since': time.time(),
                        'project_root': str(foreign_root),
                    }
                ],
                'waiting': [],
                'run_log': [],
            },
        )

        # The dead foreign holder is pruned against its own project_root, freeing
        # the slot for the local acquirer.
        _make_live_plan(base, 'local-plan')
        result = build_queue.run_acquire(Namespace(plan_id='local-plan'))
        assert result['admission'] == 'admitted'

        state = _read_queue(isolated_base['queue_path'])
        assert dead_id not in [e['id'] for e in state['active']]


# =============================================================================
# Shared-core delegation guard — no re-implemented liveness / resolution
# =============================================================================


class TestSharedCoreDelegation:
    def test_imports_shared_liveness_predicate(self) -> None:
        assert hasattr(build_queue, 'holder_is_dead')

    def test_imports_shared_rmw(self) -> None:
        assert hasattr(build_queue, 'rmw_json')

    def test_imports_shared_resolvers(self) -> None:
        # Resolution is delegated to the shared marketplace_paths resolvers —
        # the hardened machine-global home-root creator and the public
        # main-checkout resolver — never re-implemented here.
        assert hasattr(build_queue, 'ensure_home_root')
        assert hasattr(build_queue, 'main_checkout_root')

    def test_no_inline_git_common_dir_in_source(self) -> None:
        src = SCRIPT_PATH.read_text(encoding='utf-8')
        assert '--git-common-dir' not in src


# =============================================================================
# Machine-global resolution — the host-wide home-root tier (cwd-independent)
# =============================================================================


class TestMachineGlobalResolution:
    def test_queue_resolves_under_home_root_ignoring_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The queue lives under the machine-global home root, NOT PLAN_BASE_DIR.
        # Pinning cwd into a worktree does not redirect it — home_root() is
        # host-wide and cwd-independent.
        home = tmp_path / 'home'
        home.mkdir()
        monkeypatch.setenv('PLAN_MARSHALL_HOME', str(home))

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        resolved = build_queue._resolve_queue_path()
        assert resolved == home / 'build-queue.json'
        assert worktree / '.plan' / 'local' / 'build-queue.json' != resolved

    def test_acquire_writes_to_home_root_from_worktree_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        main_repo = tmp_path / 'main'
        base = main_repo / '.plan' / 'local'
        (base / 'plans').mkdir(parents=True)
        home = tmp_path / 'home'
        home.mkdir()
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))
        monkeypatch.setenv('PLAN_MARSHALL_HOME', str(home))
        monkeypatch.setattr(build_queue, 'main_checkout_root', lambda: main_repo)

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert result['admission'] == 'admitted'
        # The queue landed under the machine-global home root, not the worktree.
        assert (home / 'build-queue.json').is_file()
        assert not (worktree / '.plan' / 'local' / 'build-queue.json').exists()
