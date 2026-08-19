#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer fronted by a FIFO admission queue.

Contract under test (lock-reconciliation-analysis.md §4 behavioural-equivalence
criteria + §5 massive-parallel-concurrency invariants (ii) + (iv); the FIFO
merge-queue admission layer + its canonical contract in manage-locks/SKILL.md;
ADR-002):

* **Atomic acquire** — ``acquire`` creates the lock file via ``O_EXCL`` and
  records the holder ``plan_id`` in the file contents.
* **FIFO admission (fairness)** — ``acquire`` first FIFO-enqueues ``--plan-id``
  into ``merge-queue.json``; ONLY the FIFO-front plan (the oldest entry by
  admit-``ts``) is admission-eligible. A non-front plan returns
  ``admission: blocked`` WITHOUT attempting the ``O_EXCL`` create — it never
  contends the kernel race — even when the lock file is FREE.
* **Idempotent re-poll position preservation** — a plan already in the queue
  KEEPS its FIFO position on re-poll; it is never re-appended to the back, so a
  plan polling repeatedly never loses priority to a later-arriving plan.
* **Release advances the front** — ``release`` dequeues ``--plan-id`` from
  ``merge-queue.json`` so the next FIFO entry becomes the front and is admitted
  on its next re-poll.
* **No double-grant** — exactly one of N concurrent ``acquire`` calls holds the
  lock; the rest return ``status: blocked``. Two plans never both hold the lock.
* **``blocked`` still escalates** — a blocked admission returns ``status: blocked``
  + ``blocking_plan_id`` (when a foreign live holder holds the lock) +
  ``waiting_count``, so the Pre-Merge Gate's poll/backoff loop and last-resort
  orchestrator escalation fire. ``blocked`` is NOT a hard error (no ``error_code``).
* **Stale reclamation** — a lock whose recorded holder has no live plan dir (on
  main OR in its worktree) is reclaimable (``reclaimed: true``) by the FIFO-front
  plan; a lock whose holder IS live is NOT reclaimable.
* **Idempotent release** — ``release`` removes the lock so the next acquire
  succeeds; release is idempotent (already-free / foreign-holder → no-op success,
  the foreign holder's lock left intact) and ALWAYS dequeues the FIFO entry.
* **``check`` holder read** — ``check`` returns ``{free}`` when no lock file
  exists and ``{held, holder_plan_id}`` when one does, without creating or
  mutating the lock, and never touching the FIFO queue.
* **Holder liveness via the shared core** — liveness is the imported
  :func:`_locks_core.holder_is_dead`, NOT a re-implemented copy; both main and
  worktree paths are consulted.
* **Main-anchored resolution (the single exception)** — both the lock AND the
  FIFO queue resolve to the MAIN checkout regardless of caller cwd, even when cwd
  is pinned to a worktree fixture.

Real-parallel obligations (§5 (ii) + (iv)): the no-double-grant invariant (ii) and
the dead-holder-reclaim-without-evicting-a-live-holder invariant (iv) are BOTH
asserted under REAL spawned-subprocess contention — N processes racing the SAME
main-anchored ``merge.lock`` + ``merge-queue.json`` via the CLI entry point — not
sequential calls. A sequential test can never exercise the kernel ``O_EXCL`` race
window (ii), the FIFO enqueue read-modify-write race, nor the interleave between
the stale-holder unlink and the atomic re-create (iv).

Isolation (test-isolation lessons): every test runs against an isolated
``PLAN_BASE_DIR`` staged under ``tmp_path`` so the suite never contends for the
real ``.plan/merge.lock`` / ``.plan/merge-queue.json`` under ``-n auto``. Under
``PLAN_BASE_DIR`` the lock resolves to ``<PLAN_BASE_DIR>/merge.lock``, the queue
to ``<PLAN_BASE_DIR>/merge-queue.json``, and holder plan dirs to
``<PLAN_BASE_DIR>/plans/{holder}``.

Filename note: this file is named ``test_manage_locks_merge_lock.py`` rather than
``test_merge_lock.py`` because pytest's default ``prepend`` import mode requires
unique test-module basenames across the suite.
"""


from __future__ import annotations

# The shared core owns the [LOCK]-log resolver and the best-effort emission
# swallow. ``merge_lock`` does ``from _locks_core import log_lock_event``, so the
# function closes over the _locks_core module that ``merge_lock`` imported — that
# SAME module instance is recovered from the function's ``__module__`` (NOT a
# fresh ``load_script_module`` copy, which would be a different instance whose
# patches ``merge_lock`` never sees).
from pathlib import Path

import pytest
from _manage_locks_merge_lock_fixtures import _make_live_plan, _TokenRecorder, merge_lock

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def isolated_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated PLAN_BASE_DIR under tmp_path.

    Layout::

        tmp_path/main/.plan/local/                  (PLAN_BASE_DIR — main stand-in)
        tmp_path/main/.plan/local/plans/            (holder plan dirs resolve here)
        tmp_path/main/.plan/local/merge.lock        (the O_EXCL lock resolves here)
        tmp_path/main/.plan/local/merge-queue.json  (the FIFO queue resolves here)

    Sets PLAN_BASE_DIR to the main stand-in so the lock resolves to
    ``<base>/merge.lock``, the FIFO queue to ``<base>/merge-queue.json``, and
    ``holder_is_dead(holder)`` resolves the holder plan dir to
    ``<base>/plans/{holder}``.
    """
    base = tmp_path / 'main' / '.plan' / 'local'
    (base / 'plans').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return {
        'base': base,
        'lock_path': base / 'merge.lock',
        'queue_path': base / 'merge-queue.json',
    }


@pytest.fixture(autouse=True)
def _stub_title_tokens(monkeypatch: pytest.MonkeyPatch) -> _TokenRecorder:
    """Autouse: stub the three best-effort title-token seams for EVERY test so the
    direct ``run_acquire`` / ``run_release`` unit tests never spawn the real
    executor subprocess (the token surface is best-effort and out-of-scope for the
    lock-correctness assertions). Tests that care about the token surface request
    this fixture by name and assert on the recorder.

    The CLI-subprocess concurrency tests run in a SEPARATE spawned process where
    this monkeypatch does not apply — there the real best-effort wrappers run and
    swallow any executor failure, exactly as in production.
    """
    recorder = _TokenRecorder()
    recorder.install(monkeypatch)
    return recorder


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

    def test_reclaim_aborts_and_restores_when_holder_became_live(
        self, isolated_base: dict
    ) -> None:
        """The abort/restore branch: the file at the path changed to a LIVE holder
        between the liveness observation and the reclaim. The helper renames it
        aside, finds the renamed-away content is NOT the observed dead holder (it
        is a live holder), restores the file intact via ``os.replace``, and returns
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

    def test_reclaim_aborts_and_restores_when_holder_changed_to_other_dead(
        self, isolated_base: dict
    ) -> None:
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

    def test_reclaim_drops_sidecar_and_loses_when_restore_replace_raises(
        self, isolated_base: dict
    ) -> None:
        """The abort/restore branch when ``os.replace`` ITSELF raises: the helper
        observed a dead holder, renamed the file aside, then found the renamed-away
        content was NOT the observed dead holder — so it tries to restore the file
        via ``os.replace``, but that restore raises (a concurrent reclaimer already
        recreated the path). The helper must drop the now-stale sidecar via
        ``os.unlink`` and still lose cleanly with ``False`` — never granting this
        reclaimer the lock. This pins the best-effort-restore sub-branch the other
        abort tests (where ``os.replace`` succeeds) leave unexercised."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # The file at the path is a LIVE holder (its plan dir exists) — different
        # from the observed dead holder, so the helper enters the restore branch.
        _make_live_plan(base, 'live-winner')
        lock_path.write_text('live-winner\n', encoding='utf-8')

        # Make the restore os.replace raise, simulating a concurrent reclaimer
        # having recreated the path before this loser could restore it.
        unlinked: list[str] = []
        real_unlink = merge_lock.os.unlink

        def _raising_replace(_src: str, _dst: str) -> None:
            raise OSError('restore target busy')

        def _recording_unlink(target: str) -> None:
            unlinked.append(target)
            real_unlink(target)

        mp = pytest.MonkeyPatch()
        mp.setattr(merge_lock.os, 'replace', _raising_replace)
        mp.setattr(merge_lock.os, 'unlink', _recording_unlink)
        try:
            won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')
        finally:
            mp.undo()

        # The reclaimer lost cleanly despite the restore failing.
        assert won is False
        # The now-stale sidecar was dropped via os.unlink (best-effort cleanup),
        # so no reclaim sidecar lingers on disk.
        assert len(unlinked) == 1, unlinked
        assert Path(unlinked[0]).name.startswith(f'{lock_path.name}.reclaim.')
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

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
