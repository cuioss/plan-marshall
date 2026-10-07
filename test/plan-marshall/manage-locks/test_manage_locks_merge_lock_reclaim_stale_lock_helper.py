#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer fronted by a FIFO admission queue.

Its sections, in order:

* Fixtures
* _reclaim_stale_lock — atomic eviction of the OBSERVED stale file (deterministic
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _manage_locks_merge_lock_fixtures import (
    _make_live_plan,
    _stub_title_tokens,
    _TokenRecorder,
    isolated_base,
    merge_lock,
)

# =============================================================================
# Fixtures
# =============================================================================


# =============================================================================
# _reclaim_stale_lock — atomic eviction of the OBSERVED stale file (deterministic
# in-process unit; pins the atomicity contract the concurrency tests exercise only
# stochastically)
# =============================================================================


class TestReclaimStaleLockHelper:
    """The reclaim eviction arbitrates on the SPECIFIC observed stale file, not the
    bare path: it renames the file aside to a per-reclaimer unique sidecar,
    re-confirms the renamed-away content is exactly the dead holder it decided to
    evict, and only then O_EXCL-recreates. The former blind ``os.unlink(path)``
    would evict whatever lived at the path — including a live holder a concurrent
    reclaimer had just installed — and let two acquirers both win. These
    deterministic units pin both branches: confirmed-dead reclaim, and the
    abort/restore branch when the path's holder changed to a live holder between
    observation and reclaim."""

    def test_reclaim_succeeds_for_observed_dead_holder(self, isolated_base: dict) -> None:
        """A lock file recording a dead holder (no live plan dir) is atomically
        reclaimed: the helper returns True, the dead file is gone, and the lock
        file now records the new holder."""
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # 'dead-holder' has no plan dir under <base>/plans → dead.
        lock_path.write_text('dead-holder\n', encoding='utf-8')

        won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')

        assert won is True
        # The lock now records the reclaiming holder.
        assert lock_path.read_text(encoding='utf-8').strip() == 'plan-b'
        # No reclaim sidecar left behind.
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_reclaim_aborts_and_restores_when_holder_became_live(self, isolated_base: dict) -> None:
        """The abort/restore branch: the file at the path changed to a LIVE holder
        between the liveness observation and the reclaim. The helper renames it
        aside, finds the renamed-away content is NOT the observed dead holder (it
        is a live holder), restores the file intact (no-clobber link), and returns
        False — the live holder's lock survives unchanged and this reclaimer loses."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # The file at the path is now a LIVE holder (its plan dir exists), even
        # though the reclaimer OBSERVED a dead holder ('dead-holder') a beat earlier.
        _make_live_plan(base, 'live-winner')
        lock_path.write_text('live-winner\n', encoding='utf-8')

        won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')

        assert won is False
        # The live holder's lock file is restored intact — never evicted.
        assert lock_path.is_file()
        assert lock_path.read_text(encoding='utf-8').strip() == 'live-winner'
        # The sidecar was replaced back, not left dangling.
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_reclaim_aborts_and_restores_when_holder_changed_to_other_dead(self, isolated_base: dict) -> None:
        """The observed-file arbitration also loses when the path's content changed
        to a DIFFERENT holder (even another dead one) before the rename — the
        renamed-away content must equal the SPECIFIC observed holder. A mismatch
        restores the file and returns False rather than stealing a slot the
        reclaimer never observed."""
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # The file is a different (also dead) holder than the one observed.
        lock_path.write_text('other-dead\n', encoding='utf-8')

        won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')

        assert won is False
        # The file is restored intact (the different holder), not reclaimed.
        assert lock_path.read_text(encoding='utf-8').strip() == 'other-dead'
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_reclaim_never_clobbers_a_lock_recreated_in_the_restore_window(self, isolated_base: dict) -> None:
        """The abort/restore branch when a writer that bypasses the arbitration
        guard recreated the path
        between this reclaimer's rename and its restore: the restore must NOT
        overwrite the newer lock. Driven with the real filesystem — the claimant's
        lock is created at the moment the helper reads the sidecar, which is
        exactly the window — so the no-clobber property is exercised rather than
        simulated by a raising stub. The newer lock survives, the stale sidecar is
        dropped, and the reclaimer loses cleanly with ``False``."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # The file at the path is a LIVE holder (its plan dir exists) — different
        # from the observed dead holder, so the helper enters the restore branch.
        _make_live_plan(base, 'live-winner')
        lock_path.write_text('live-winner\n', encoding='utf-8')

        real_read_holder = merge_lock._read_holder

        def _read_then_race(path: Path) -> str:
            holder: str = real_read_holder(path)
            # A writer that bypasses the arbitration guard O_EXCL-creates the
            # freed path in the window. The exclusive create is the real
            # claimant primitive: it would FAIL if the path were still occupied.
            assert merge_lock._try_atomic_create(lock_path, 'concurrent-claimant') is True
            return holder

        mp = pytest.MonkeyPatch()
        mp.setattr(merge_lock, '_read_holder', _read_then_race)
        try:
            won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')
        finally:
            mp.undo()

        assert won is False
        # The concurrent claimant's lock is intact — never overwritten by the restore.
        assert lock_path.read_text(encoding='utf-8').strip() == 'concurrent-claimant'
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_arbitration_guard_is_held_while_the_lock_is_aside(self, isolated_base: dict) -> None:
        """While the lock file is renamed aside the path is free, so a cooperating
        claimant's create must be shut out for that whole window. The acquire leg
        creates under the same guard this asserts is held, so it cannot win a lock
        whose previous holder is about to be restored as live."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        _make_live_plan(base, 'live-winner')
        lock_path.write_text('live-winner\n', encoding='utf-8')
        guard_path = lock_path.with_name(f'{lock_path.name}.arbitration.lock')
        observed: list[tuple[bool, bool]] = []
        real_read_holder = merge_lock._read_holder

        def _read_and_observe(path: Path) -> str:
            # (guard held, lock path free) at the moment the sidecar is inspected.
            observed.append((guard_path.exists(), not lock_path.exists()))
            holder: str = real_read_holder(path)
            return holder

        mp = pytest.MonkeyPatch()
        mp.setattr(merge_lock, '_read_holder', _read_and_observe)
        try:
            won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')
        finally:
            mp.undo()

        assert won is False
        assert observed == [(True, True)], observed
        # The guard is released and the live holder is back in place.
        assert not guard_path.exists()
        assert lock_path.read_text(encoding='utf-8').strip() == 'live-winner'

    def test_restore_keeps_the_live_lock_when_hard_links_are_rejected(self, isolated_base: dict) -> None:
        """A link failure other than ``FileExistsError`` leaves the path free, so
        discarding the sidecar would strip a live holder of its lock. The restore
        falls back to a rename and the live holder's lock survives."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        _make_live_plan(base, 'live-winner')
        lock_path.write_text('live-winner\n', encoding='utf-8')

        def _no_hard_links(_src: str, _dst: str) -> None:
            raise PermissionError('hard links not supported')

        mp = pytest.MonkeyPatch()
        mp.setattr(merge_lock.os, 'link', _no_hard_links)
        try:
            won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')
        finally:
            mp.undo()

        assert won is False
        assert lock_path.read_text(encoding='utf-8').strip() == 'live-winner'
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_restore_leaves_the_sidecar_when_no_restore_path_works(self, isolated_base: dict) -> None:
        """When neither the link nor the rename can restore the file, the sidecar
        is left on disk — a stranded sidecar is recoverable, a deleted live lock
        is not — and the reclaimer still loses."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        _make_live_plan(base, 'live-winner')
        lock_path.write_text('live-winner\n', encoding='utf-8')

        def _fails(_src: str, _dst: str) -> None:
            raise PermissionError('not permitted')

        mp = pytest.MonkeyPatch()
        mp.setattr(merge_lock.os, 'link', _fails)
        mp.setattr(merge_lock.os, 'replace', _fails)
        try:
            won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')
        finally:
            mp.undo()

        assert won is False
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert len(siblings) == 1, siblings
        assert siblings[0].read_text(encoding='utf-8').strip() == 'live-winner'

    def test_reclaim_returns_false_when_path_already_gone(self, isolated_base: dict) -> None:
        """When a racing reclaimer already swapped/removed the file, the rename
        fails (the path is gone) and the helper loses cleanly with False — no
        sidecar, no recreate, fall through to lose."""
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # No file at the path — simulates a racing reclaimer having claimed it.
        assert not lock_path.exists()

        won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')

        assert won is False
        assert not lock_path.exists()
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_reclaim_uses_unique_sidecar_per_reclaimer(self, isolated_base: dict) -> None:
        """The sidecar target is a per-reclaimer unique name (``{lock}.reclaim.{pid}.{uuid}``)
        — a path only this reclaimer names, so two concurrent reclaimers never
        collide on the rename target. Exercised by confirming the rename target
        carries the pid and a uuid hex suffix during a successful reclaim (the
        sidecar is consumed by the time the helper returns, so assert via a wrapped
        ``os.rename`` seam)."""
        import os as _os

        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text('dead-holder\n', encoding='utf-8')

        rename_targets: list[str] = []
        real_rename = _os.rename

        def _recording_rename(src: str, dst: str) -> None:
            rename_targets.append(dst)
            real_rename(src, dst)

        mp = pytest.MonkeyPatch()
        mp.setattr(merge_lock.os, 'rename', _recording_rename)
        try:
            won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')
        finally:
            mp.undo()

        assert won is True
        # The (single) rename targeted a unique sidecar carrying pid + a hex uuid.
        assert len(rename_targets) == 1, rename_targets
        target_name = Path(rename_targets[0]).name
        assert target_name.startswith(f'{lock_path.name}.reclaim.{_os.getpid()}.')
        # The uuid suffix is 32 hex chars.
        suffix = target_name.rsplit('.', 1)[-1]
        assert len(suffix) == 32 and all(c in '0123456789abcdef' for c in suffix)
