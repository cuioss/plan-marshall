#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``manage-locks/build_queue.py`` — the bounded-``k``-slot build-queue
concurrency limiter with a FIFO waiting queue.

Contract under test (solution_outline.md D5 + lock-reconciliation-analysis.md §5
massive-parallel-concurrency invariants (i) + (iii) + (iv); ADR-002):

* **Admit under capacity** — ``acquire`` with ``len(active) < max_slots`` appends
  ``{id, ts}`` to ``active`` and returns ``admission: admitted``.
* **Block at capacity** — ``acquire`` with ``active`` full appends to the FIFO
  ``waiting`` queue and returns ``admission: blocked``. The script never loops —
  ``blocked`` is a structured signal, not an error.
* **Release frees + FIFO-promotes** — ``release --id ID`` removes the id from
  ``active`` and promotes the FRONT waiting entry (the first list element —
  serialized append order, NOT the smallest admit-``ts``) into
  the freed slot, recording it as ``promoted``; it appends an id+timestamp
  ``run_log`` entry. Release of an absent id is an idempotent no-op success.
* **FIFO ordering is list position, not admit-``ts``** — every promote path (the
  reaper promote, the idempotent re-poll promote-eligibility check, and the
  release promote) selects the front by list position. ``ts`` is sampled outside
  the serialized ``rmw_json`` section and is informational only, so under
  concurrent enqueue it can disagree with append order; an inverted-``ts``
  fixture pins that a ``min(ts)`` selector cannot creep back in.
* **Id collision-resistance** — the admission id is ``{plan_id}:{uuid4}`` so two
  acquires by the SAME plan never collide.
* **Default + configured ``max_slots``** — absent config defaults to 5; a
  ``build_queue.max_slots`` override in marshal.json is honored.
* **Corrupt/missing file as empty** — a missing or malformed ``build-queue.json``
  is treated as empty state, not a crash.
* **Machine-global resolution** — ``build-queue.json`` resolves under the
  machine-global home root (:func:`marketplace_paths.home_root`,
  ``~/.plan-marshall/build-queue.json`` by default, overridable via
  ``PLAN_MARSHALL_HOME``) regardless of caller cwd — the host-wide tier shared
  across every checkout, NOT the per-repo main-anchored exception corpus.
* **Foreign-holder pruning** — each entry is stamped at acquire with
  ``project_root = str(main_checkout_root())`` so a foreign project's live holder
  is judged against its OWN checkout and never reclaimed by a session in a
  different repo.
* **Shared-core delegation** — liveness is the imported
  :func:`_locks_core.holder_is_dead`; the resolvers are the imported
  :func:`marketplace_paths.home_root` / ``main_checkout_root``; none is
  re-implemented.

Real-parallel obligations (§5 (i) + (iii) + (iv)): the no-over-admit boundary (i),
the no-double-promote/lost-entry FIFO property (iii), and dead-holder reclaim
without evicting a live holder (iv) are asserted under REAL spawned-subprocess
contention — N processes racing the SAME machine-global ``build-queue.json`` via
the CLI entry point — not sequential calls. A sequential test can never exercise
the kernel-serialized read-modify-write race window these invariants guard.

Isolation: every test runs against an isolated home root and ``PLAN_BASE_DIR``
staged under ``tmp_path`` so the suite never contends for the real
``~/.plan-marshall/build-queue.json`` under ``-n auto``. The queue resolves to
``<PLAN_MARSHALL_HOME>/build-queue.json``; holder plan dirs resolve to
``<PLAN_BASE_DIR>/plans/{holder}``; marshal.json resolves to
``<PLAN_BASE_DIR>/marshal.json``. The ``main`` fixture dir is a real git repo so
subprocess ``main_checkout_root()`` resolves to it, and the in-process fixture
pins ``build_queue.main_checkout_root`` to that same root so stamped
``project_root`` liveness resolves under ``<PLAN_BASE_DIR>``.
"""


from __future__ import annotations

# The shared core owns the [LOCK]-log resolver and the best-effort emission
# swallow. ``build_queue`` does ``from _locks_core import log_lock_event``, so the
# function closes over the _locks_core module that ``build_queue`` imported — that
# SAME module instance is recovered from the function's ``__module__`` (NOT a
# fresh ``load_script_module`` copy, which would be a different instance whose
# patches ``build_queue`` never sees).
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
)


@pytest.fixture
def isolated_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated machine-global home + PLAN_BASE_DIR under tmp_path.

    Layout::

        tmp_path/main/                              (a real git repo → project_root)
        tmp_path/main/.plan/local/                  (PLAN_BASE_DIR — holder liveness)
        tmp_path/main/.plan/local/plans/            (holder plan dirs resolve here)
        tmp_path/main/.plan/local/marshal.json      (max_slots config resolves here)
        tmp_path/home/                              (PLAN_MARSHALL_HOME — home root)
        tmp_path/home/build-queue.json              (queue resolves here)

    ``main`` is a real git repo so a spawned subprocess's ``main_checkout_root()``
    resolves to it (run subprocesses with ``cwd=main_repo`` +
    ``env_overrides``); in-process, ``build_queue.main_checkout_root`` is pinned
    to ``main`` so the stamped ``project_root`` liveness resolves under
    ``main/.plan/local`` (== ``PLAN_BASE_DIR``).
    """
    main_repo = tmp_path / 'main'
    main_repo.mkdir()
    _init_git_repo(main_repo)
    base = main_repo / '.plan' / 'local'
    (base / 'plans').mkdir(parents=True)
    home = tmp_path / 'home'
    home.mkdir()

    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(home))
    # In-process: pin the project_root stamp at main_repo so the machine-global
    # prune judges liveness under main_repo/.plan/local (== base). Subprocess
    # tests instead pass cwd=main_repo so the real git resolver lands there.
    monkeypatch.setattr(build_queue, 'main_checkout_root', lambda: main_repo)

    return {
        'base': base,
        'main_repo': main_repo,
        'home': home,
        'queue_path': home / 'build-queue.json',
        'env_overrides': {'PLAN_BASE_DIR': str(base), 'PLAN_MARSHALL_HOME': str(home)},
    }


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
