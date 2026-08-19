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

import json

# The shared core owns the [LOCK]-log resolver and the best-effort emission
# swallow. ``merge_lock`` does ``from _locks_core import log_lock_event``, so the
# function closes over the _locks_core module that ``merge_lock`` imported — that
# SAME module instance is recovered from the function's ``__module__`` (NOT a
# fresh ``load_script_module`` copy, which would be a different instance whose
# patches ``merge_lock`` never sees).
from argparse import Namespace
from pathlib import Path

import pytest
from _manage_locks_merge_lock_fixtures import (
    _REAL_PUSH_TITLE_TOKEN,
    _make_live_plan,
    _TokenRecorder,
    _waiting_plan_ids,
    merge_lock,
)

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
# Live-worktree reclaim guard — orphaned shell auto-reclaims, genuine
# mid-recovery worktree stays protected (strengthened holder_has_live_worktree)
# =============================================================================


class TestLiveWorktreeReclaimGuard:
    """Acceptance regression for the strengthened ``holder_has_live_worktree``
    predicate that gates the merge-lock auto-reclaim. A stale holder whose worktree
    is an orphaned EMPTY SHELL (no git plumbing, no live plan dir) is now
    auto-reclaimed on the next ``acquire`` — closing both observed incidents (a
    vanished/never-persisted plan; a post-migration stranded holder) that
    previously wedged the merge lock behind a dead holder until a manual
    ``release-under-holder-id``. A GENUINELY-live holder and a genuine mid-recovery
    worktree (real git-worktree marker present, plan dir moved out) stay protected
    from false reclaim — the latter still surfaces ``stale_holder_live_worktree``
    for operator confirmation."""

    def _hold_dead_lock_then_dequeue(self, holder: str) -> None:
        """Stage a lock held by a plan-dir-dead ``holder`` and dequeue it so the
        next acquirer is the FIFO front. The caller stages the holder's worktree
        shape (orphaned shell vs genuine marker) before the reclaiming acquire."""
        merge_lock.run_acquire(Namespace(plan_id=holder, timeout=5.0))
        merge_lock._dequeue_fifo(holder)

    def test_vanished_plan_orphaned_shell_is_auto_reclaimed(self, isolated_base: dict) -> None:
        # Incident class (a): a plan that never persisted its dir leaves a bare,
        # empty worktree shell (no .git marker, no live plan dir) while holding the
        # merge lock. Under the strengthened predicate the shell no longer
        # masquerades as mid-recovery, so the front acquirer auto-reclaims — no
        # manual release-under-holder-id required.
        base = isolated_base['base']
        self._hold_dead_lock_then_dequeue('vanished')
        # Orphaned empty shell on disk — worktree dir exists but carries neither a
        # git-worktree marker nor a live plan dir.
        (base / 'worktrees' / 'vanished').mkdir(parents=True, exist_ok=True)

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['status'] == 'success', result
        assert result['action'] == 'acquired'
        assert result['reclaimed'] is True
        assert result['holder'] == 'plan-b'
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-b'

    def test_post_migration_stranded_shell_is_auto_reclaimed(self, isolated_base: dict) -> None:
        # Incident class (b): a post-migration / stranded holder — its plan dir is
        # gone but an incomplete finalize teardown left a worktree shell with stray
        # leftover content (still no git plumbing, no live plan dir). It must also
        # be auto-reclaimed rather than blocking the merge forever.
        base = isolated_base['base']
        self._hold_dead_lock_then_dequeue('stranded')
        shell = base / 'worktrees' / 'stranded'
        (shell / 'leftover' / 'residue').mkdir(parents=True, exist_ok=True)

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['status'] == 'success', result
        assert result['action'] == 'acquired'
        assert result['reclaimed'] is True
        assert result['holder'] == 'plan-b'

    def test_genuinely_live_holder_is_not_reclaimed(self, isolated_base: dict) -> None:
        # A genuinely-live holder (its plan dir exists) is NEVER reclaimed — the
        # acquirer serializes (blocks) with no false reclaim. This negative guards
        # against the strengthened predicate over-reclaiming a live holder.
        merge_lock.run_acquire(Namespace(plan_id='live-holder', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'live-holder')

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))
        assert result['status'] == 'blocked'
        assert result['admission'] == 'blocked'
        assert result['blocking_plan_id'] == 'live-holder'
        assert result.get('reclaimed') is not True
        # A live holder is an ordinary block, NOT the refuse-auto-reclaim sub-case.
        assert 'stale_holder_live_worktree' not in result
        # The live holder's lock survives unchanged.
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'live-holder'

    def test_genuine_mid_recovery_worktree_is_still_refused(self, isolated_base: dict) -> None:
        # A genuine mid-recovery holder: plan-dir-dead everywhere, but its worktree
        # carries a real git-worktree marker (a `.git` gitdir link) — an interrupted
        # finalize move-back moved the plan dir out but left the git plumbing. The
        # guard REFUSES to auto-reclaim it and surfaces `stale_holder_live_worktree`
        # so the branch-cleanup escalation asks the operator to confirm, retaining
        # the mid-recovery protection.
        base = isolated_base['base']
        self._hold_dead_lock_then_dequeue('mid-rec')
        worktree = base / 'worktrees' / 'mid-rec'
        worktree.mkdir(parents=True, exist_ok=True)
        (worktree / '.git').write_text(
            'gitdir: /main/.git/worktrees/mid-rec\n', encoding='utf-8'
        )

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['status'] == 'blocked', result
        assert result['admission'] == 'blocked'
        assert result['stale_holder_live_worktree'] is True
        assert result['blocking_plan_id'] == 'mid-rec'
        assert result.get('reclaimed') is not True
        # The mid-recovery holder's lock is NOT force-released.
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'mid-rec'

    def test_non_front_blocked_acquire_surfaces_lock_waiting(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """A non-front FIFO block surfaces `lock-waiting` (⏳) too — even when the
        lock is FREE, a plan behind the front is waiting for its turn."""
        base = isolated_base['base']
        for name in ('front', 'behind'):
            _make_live_plan(base, name)
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [
                {'plan_id': 'front', 'ts': 1.0},
                {'plan_id': 'behind', 'ts': 2.0},
            ]}),
            encoding='utf-8',
        )
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_acquire(Namespace(plan_id='behind', timeout=5.0))
        assert result['status'] == 'blocked'
        assert _stub_title_tokens.set_states == ['lock-waiting']
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_WAITING]

    def test_blocked_release_surfaces_lock_cleared(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """Symmetric partner of `test_blocked_acquire_surfaces_lock_waiting`: a
        plan that was blocked against a live foreign holder (⏳ pushed) and then
        calls `release` has its token CLEARED. The lock stays held by the foreign
        holder (release is scoped to the caller), but the blocked waiter's own
        stale `lock-waiting` token is cleared via the foreign-holder noop branch."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        # Drop plan-a's own acquire surface so the assertions below see only the
        # blocked waiter's tokens (mirrors `test_blocked_acquire_surfaces_lock_waiting`).
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()
        # plan-b blocks behind the live holder, surfacing `lock-waiting` (⏳).
        blocked = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.6))
        assert blocked['status'] == 'blocked'
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_WAITING]
        _stub_title_tokens.cleared.clear()

        # The blocked waiter gives up and releases — its stale token is cleared and
        # the foreign holder's lock is left intact.
        result = merge_lock.run_release(Namespace(plan_id='plan-b'))
        assert result['action'] == 'noop'
        assert _stub_title_tokens.cleared == ['plan-b']
        assert isolated_base['lock_path'].is_file()

    def test_non_front_blocked_release_surfaces_lock_cleared(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """Symmetric partner of `test_non_front_blocked_acquire_surfaces_lock_waiting`:
        a non-front FIFO waiter (⏳ pushed, lock FREE) that then calls `release` has
        its token CLEARED via the already-free noop branch, and is dequeued so the
        front can advance."""
        base = isolated_base['base']
        for name in ('front', 'behind'):
            _make_live_plan(base, name)
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [
                {'plan_id': 'front', 'ts': 1.0},
                {'plan_id': 'behind', 'ts': 2.0},
            ]}),
            encoding='utf-8',
        )
        # `behind` blocks as a non-front waiter, surfacing `lock-waiting` (⏳).
        blocked = merge_lock.run_acquire(Namespace(plan_id='behind', timeout=5.0))
        assert blocked['status'] == 'blocked'
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_WAITING]
        _stub_title_tokens.cleared.clear()

        # `behind` gives up and releases — the lock was never held by anyone, so the
        # already-free noop branch clears its stale token and dequeues it.
        result = merge_lock.run_release(Namespace(plan_id='behind'))
        assert result['action'] == 'noop'
        assert _stub_title_tokens.cleared == ['behind']
        assert 'behind' not in _waiting_plan_ids(isolated_base['queue_path'])

    def test_release_clears_token_on_released_path(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _stub_title_tokens.cleared.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['action'] == 'released'
        assert _stub_title_tokens.cleared == ['plan-a']
        # The released path also fires a plain, icon-less repaint through the
        # canonical seam (icon=None) so the 🔒 glyph disappears LIVE instead of
        # lingering until the next render event.
        assert _stub_title_tokens.pushed_icons == [None], (
            'release must repaint (icon-less push) after clearing the token'
        )

    def test_release_clears_token_on_already_free_noop(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['action'] == 'noop'
        # The already-free noop still clears this caller's stale token.
        assert _stub_title_tokens.cleared == ['plan-a']

    def test_release_clears_token_on_foreign_holder_noop(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _stub_title_tokens.cleared.clear()

        result = merge_lock.run_release(Namespace(plan_id='plan-b'))
        assert result['action'] == 'noop'
        # The foreign-holder noop clears the CALLER's (plan-b's) stale token, and
        # leaves plan-a's lock intact.
        assert _stub_title_tokens.cleared == ['plan-b']
        assert isolated_base['lock_path'].is_file()

    def test_token_write_failure_never_breaks_acquire(self, isolated_base: dict) -> None:
        """The best-effort wrappers swallow any underlying executor failure — a
        token write that raises NEVER affects the lock acquire outcome. This
        exercises the REAL _set_title_token / _push_title_token wrappers by making
        the underlying _run_executor raise."""

        def _raising_run_executor(*_a: object, **_k: object) -> dict:
            raise OSError('tty gone')

        # Patch the low-level executor seam (NOT the higher-level token seams), so
        # the real best-effort try/except wrappers run and swallow the error.
        import pytest as _pytest

        mp = _pytest.MonkeyPatch()
        mp.setattr(merge_lock, '_run_executor', _raising_run_executor)
        try:
            result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        finally:
            mp.undo()

        # The lock was acquired despite the token channel raising.
        assert result['status'] == 'success'
        assert result['action'] == 'acquired'
        assert isolated_base['lock_path'].is_file()

    def test_token_clear_failure_never_breaks_release(self, isolated_base: dict) -> None:
        """Symmetric to ``test_token_write_failure_never_breaks_acquire`` on the
        RELEASE side: the best-effort ``_clear_title_token`` wrapper swallows any
        underlying executor failure, so a token-clear that raises NEVER aborts the
        lock release. Exercises the REAL ``_clear_title_token`` wrapper by making
        the low-level ``_run_executor`` seam raise, and asserts the lock file is
        still removed (the release succeeded despite the token channel raising)."""

        def _raising_run_executor(*_a: object, **_k: object) -> dict:
            raise OSError('tty gone')

        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert isolated_base['lock_path'].is_file()

        # Patch the low-level executor seam (NOT the higher-level token seams), so
        # the real best-effort try/except wrapper runs and swallows the error.
        import pytest as _pytest

        mp = _pytest.MonkeyPatch()
        mp.setattr(merge_lock, '_run_executor', _raising_run_executor)
        try:
            result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        finally:
            mp.undo()

        # The lock was released despite the token-clear channel raising.
        assert result['status'] == 'success'
        assert result['action'] == 'released'
        assert not isolated_base['lock_path'].exists()

    def test_lock_owned_token_set_only_after_atomic_create_succeeds(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The O_EXCL-window-not-widened invariant: the ``lock-owned`` token writes
        run STRICTLY AFTER the atomic ``_try_atomic_create`` has already succeeded,
        never interleaved inside the check-then-act. Record the ordered sequence of
        (atomic-create, token-set) events through wrapped seams and assert the
        atomic create's success is observed BEFORE the first ``lock-owned`` set —
        proving the token surface cannot reopen the closed TOCTOU window."""
        events: list[str] = []

        real_atomic_create = merge_lock._try_atomic_create

        def _recording_atomic_create(lock_path: Path, holder: str) -> bool:
            ok: bool = real_atomic_create(lock_path, holder)
            events.append(f'atomic_create:{"ok" if ok else "eexist"}')
            return ok

        monkeypatch.setattr(merge_lock, '_try_atomic_create', _recording_atomic_create)
        monkeypatch.setattr(
            merge_lock, '_set_title_token', lambda _p, state: events.append(f'set:{state}')
        )
        monkeypatch.setattr(merge_lock, '_push_title_token', lambda _p, icon: events.append('push'))

        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['status'] == 'success'

        # The successful atomic create MUST be recorded before the first lock-owned
        # set — the token write is strictly after the window closed, never inside it.
        assert 'atomic_create:ok' in events
        assert 'set:lock-owned' in events
        assert events.index('atomic_create:ok') < events.index('set:lock-owned'), events
        # No token of any kind precedes the successful atomic create.
        first_token_idx = next(
            (i for i, e in enumerate(events) if e.startswith(('set:', 'push'))), len(events)
        )
        assert events.index('atomic_create:ok') < first_token_idx, events

    def test_release_repaint_via_surface_lock_cleared_default(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """The default (set_title_token=True) _surface_lock_cleared both clears the
        token AND fires the icon-less repaint — the consolidation of the clear path
        onto the shared repaint seam."""
        _stub_title_tokens.pushed_icons.clear()
        merge_lock._surface_lock_cleared('plan-a')
        assert _stub_title_tokens.cleared == ['plan-a']
        assert _stub_title_tokens.pushed_icons == [None]

    def test_surface_lock_cleared_suppressed_fires_neither_clear_nor_repaint(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """set_title_token=False suppresses the ENTIRE surface — no clear AND no
        repaint fire (the early return precedes both writes)."""
        _stub_title_tokens.pushed_icons.clear()
        merge_lock._surface_lock_cleared('plan-a', set_title_token=False)
        assert _stub_title_tokens.cleared == []
        assert _stub_title_tokens.pushed_icons == []

    def test_push_title_token_omits_icon_for_plain_repaint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The canonical push seam omits --icon for a plain repaint (icon=None) and
        includes --icon <glyph> when a glyph is supplied. Exercises the REAL
        _push_title_token wrapper (captured before the autouse stub) with a
        recording _run_executor."""
        calls: list[tuple] = []
        monkeypatch.setattr(merge_lock, '_run_executor', lambda notation, *args: calls.append((notation, args)))

        _REAL_PUSH_TITLE_TOKEN('plan-a')  # plain repaint — no icon
        _REAL_PUSH_TITLE_TOKEN('plan-b', merge_lock._ICON_LOCK_OWNED)  # glyph push

        assert calls[0][1] == ('session', 'push-title-token', '--plan-id', 'plan-a'), (
            'plain repaint must call session push-title-token with NO --icon'
        )
        assert '--icon' not in calls[0][1]
        assert calls[1][1] == (
            'session', 'push-title-token', '--plan-id', 'plan-b', '--icon', merge_lock._ICON_LOCK_OWNED
        ), 'a glyph push must include --icon <glyph>'

    def test_lock_owned_state_maps_to_lock_icon(self) -> None:
        """Guard the glyph contract: the lock-owned/lock-waiting icon constants
        match the canonical manage-terminal-title glyph vocabulary (🔒 / ⏳), and
        the bare STATE NAMES are passed to manage-status (no hard-coded glyph in
        the lock branching)."""
        assert merge_lock._ICON_LOCK_OWNED == '\U0001f512'
        assert merge_lock._ICON_LOCK_WAITING == '⏳'
        assert merge_lock._STATE_LOCK_OWNED == 'lock-owned'
        assert merge_lock._STATE_LOCK_WAITING == 'lock-waiting'
