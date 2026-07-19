#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-locks ``_locks_core.py`` shared coordination primitives.

``_locks_core`` is the single TOCTOU-safe coordination surface that both the
merge mutex and the build-queue limiter build on. It is imported as a module
(never an executor entry point) and exposes two public pieces plus the private
helpers they compose:

  * :func:`holder_is_dead` — the plan-liveness predicate. A recorded holder is
    dead when its plan dir lives in NEITHER the main checkout NOR the holder's
    worktree.
  * :func:`rmw_json` — a serialized, main-anchored read-modify-write for JSON
    state files, guarded by an ``O_EXCL`` guard-file mutex and committed via an
    atomic temp-file replace.

Isolation: under the autouse ``_plan_base_dir_sandbox`` fixture, ``PLAN_BASE_DIR``
is redirected into a per-test tmp dir; ``resolve_main_anchored_path`` (which
``holder_is_dead`` and the call sites of ``rmw_json`` anchor on) honours that
override, so ``holder_is_dead`` resolves liveness against the sandbox tree rather
than the real main checkout. Tests that exercise ``holder_is_dead`` therefore use
the ``plan_context`` fixture (whose ``PLAN_BASE_DIR`` redirect wins over the
autouse default) and build plan/worktree dirs under ``plan_context.fixture_dir``.
The guard / RMW tests operate on free-standing JSON files under ``tmp_path`` and
need no plan-tree scaffolding.
"""

from __future__ import annotations

import json
import os
import threading
import time

import pytest

from conftest import load_script_module

_mod = load_script_module('plan-marshall', 'manage-locks', '_locks_core.py', '_locks_core_under_test')

holder_is_dead = _mod.holder_is_dead
holder_has_live_worktree = _mod.holder_has_live_worktree
rmw_json = _mod.rmw_json
_read_json_or_empty = _mod._read_json_or_empty
_acquire_guard = _mod._acquire_guard
_atomic_write_json = _mod._atomic_write_json
log_lock_event = _mod.log_lock_event
_resolve_lock_log_path = _mod._resolve_lock_log_path


# =============================================================================
# holder_is_dead — empty / malformed holder
# =============================================================================


def test_holder_is_dead_empty_string_is_dead(plan_context):
    # An empty holder is treated as dead so a corrupt lock file is reclaimable.
    assert holder_is_dead('') is True


def test_holder_is_dead_whitespace_only_is_dead(plan_context):
    # Whitespace is stripped to empty → dead.
    assert holder_is_dead('   ') is True


@pytest.mark.parametrize(
    'malicious_holder',
    [
        '../evil',
        '../../evil',
        'a/../evil',
        'sub/evil',
        'sub\\evil',
        '..',
        'foo\x00bar',
    ],
)
def test_holder_is_dead_rejects_traversal_holder(plan_context, malicious_holder):
    # holder is a plan-id joined DIRECTLY onto the anchored .plan/local base to
    # build the main-checkout (main_plan) and worktree (worktree_plan) plan-dir
    # paths. A holder bearing a path separator, a `..` parent segment, or an
    # embedded NUL must be classified dead (True) BEFORE the path is constructed
    # — otherwise a crafted holder could escape the base, resolve to an unrelated
    # existing dir, report a truly-dead holder "alive", and permanently block
    # lock reclamation (a DoS). Inverse polarity to the sibling
    # holder_has_live_worktree guard (which returns False for the same corpus).
    assert holder_is_dead(malicious_holder) is True


def test_holder_is_dead_traversal_does_not_escape_base(plan_context):
    # Concrete escape scenario: `../evil` would resolve `plans/../evil` to a
    # sibling dir of the plans root (i.e. base/evil). Stage that sibling so,
    # absent the guard, main_plan.exists() would be True and the predicate would
    # report the holder "alive" (False). The guard must reject the traversal and
    # return True (dead) rather than resolving the escaped path.
    base = plan_context.fixture_dir
    (base / 'evil').mkdir(parents=True, exist_ok=True)  # plans/../evil target

    assert holder_is_dead('../evil') is True


# =============================================================================
# holder_is_dead — liveness via main checkout
# =============================================================================


def test_holder_is_dead_false_when_main_plan_dir_exists(plan_context):
    # A holder whose plan dir lives on main (phases 1-4 / post-finalize) is alive.
    plan_context.plan_dir_for('lc-alive-main')

    assert holder_is_dead('lc-alive-main') is False


# =============================================================================
# holder_is_dead — liveness via the holder's worktree
# =============================================================================


def test_holder_is_dead_false_when_worktree_plan_dir_exists(plan_context):
    # While executing, the plan dir is MOVED into the worktree and does NOT
    # exist on main. Checking only main would wrongly declare the holder dead;
    # the worktree-resident path must keep it alive.
    base = plan_context.fixture_dir
    worktree_plan = base / 'worktrees' / 'lc-alive-wt' / '.plan' / 'local' / 'plans' / 'lc-alive-wt'
    worktree_plan.mkdir(parents=True, exist_ok=True)

    assert holder_is_dead('lc-alive-wt') is False


def test_holder_is_dead_true_when_neither_path_exists(plan_context):
    # No main plan dir and no worktree plan dir → the holder is dead.
    assert holder_is_dead('lc-no-such-holder') is True


# =============================================================================
# holder_is_dead — project-qualified liveness (project_root=, machine-global lock)
# =============================================================================
#
# When a lock file is shared across repos (the machine-global lock anchor), a
# recorded holder may live in a DIFFERENT project's checkout. The acquirer must
# judge that holder's liveness against ITS project (project_root=<A>), not the
# acquirer's own checkout — otherwise a foreign LIVE holder is wrongly reclaimed.


def test_holder_is_dead_foreign_live_holder_not_reclaimed_with_project_root(tmp_path, monkeypatch):
    # A holder whose live plan dir exists under project A's checkout must NOT be
    # declared dead when checked with project_root=<A> from a session whose own
    # checkout is project B (where the holder is absent). Caller-anchored
    # (project_root=None) resolution against B still reports it dead.
    holder = 'foreign-live-holder'
    project_a = tmp_path / 'project-a'
    (project_a / '.plan' / 'local' / 'plans' / holder).mkdir(parents=True)

    # The session's own checkout is B — anchor project_root=None resolution there.
    b_base = tmp_path / 'project-b' / '.plan' / 'local'
    b_base.mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(b_base))

    # Caller-anchored (default) sees B, where the holder is absent → dead.
    assert holder_is_dead(holder) is True
    # Project-qualified against A sees A's live plan dir → NOT dead.
    assert holder_is_dead(holder, project_root=project_a) is False


def test_holder_is_dead_project_root_consults_worktree_plan_dir(tmp_path, monkeypatch):
    # The project-qualified base consults BOTH liveness paths. Here the holder's
    # plan dir lives in its WORKTREE under project A (moved-in mid-execute), not
    # A's main checkout — project_root=<A> must still judge it alive.
    holder = 'foreign-wt-holder'
    project_a = tmp_path / 'project-a'
    wt_plan = project_a / '.plan' / 'local' / 'worktrees' / holder / '.plan' / 'local' / 'plans' / holder
    wt_plan.mkdir(parents=True)

    b_base = tmp_path / 'project-b' / '.plan' / 'local'
    b_base.mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(b_base))

    assert holder_is_dead(holder, project_root=project_a) is False
    assert holder_is_dead(holder) is True  # caller-anchored at B → dead


def test_holder_is_dead_project_root_dead_when_absent_in_that_project(tmp_path, monkeypatch):
    # project_root does not blanket a holder alive — a holder absent from project
    # A's checkout is still dead when judged against A.
    b_base = tmp_path / 'project-b' / '.plan' / 'local'
    b_base.mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(b_base))
    project_a = tmp_path / 'project-a'
    project_a.mkdir(parents=True)

    assert holder_is_dead('absent-holder', project_root=project_a) is True


# =============================================================================
# holder_has_live_worktree — genuine live/mid-recovery worktree marker (D3, strengthened)
# =============================================================================
#
# A STRONGER presence signal than holder_is_dead: it does NOT trust the bare
# existence of the worktree DIRECTORY. It returns True ONLY for a genuine
# live/mid-recovery worktree carrying a concrete marker under worktrees/{holder} —
# EITHER a git-worktree gitdir link (a `.git` file or dir at the worktree root) OR
# a live plan dir (worktrees/{holder}/.plan/local/plans/{holder}) — and False for
# an orphaned empty shell carrying neither. The merge_lock acquire path gates the
# automatic stale-reclaim on this being False, so an orphaned shell now permits
# auto-reclaim while a genuine mid-recovery holder stays protected.


def test_holder_has_live_worktree_false_when_worktree_dir_is_bare_shell(plan_context):
    # A bare, empty worktree directory carrying NO git-worktree marker and NO live
    # plan dir is an orphaned shell — under the strengthened contract it must NOT
    # count as live (previously a bare dir.exists() wrongly reported True and
    # permanently blocked the merge-lock auto-reclaim).
    base = plan_context.fixture_dir
    (base / 'worktrees' / 'lc-bare-shell').mkdir(parents=True, exist_ok=True)

    assert holder_has_live_worktree('lc-bare-shell') is False


def test_holder_has_live_worktree_false_when_orphaned_empty_shell(plan_context):
    # An orphaned empty shell (the worktree root plus a stray leftover sub-dir, but
    # neither a `.git` marker nor a live plan dir) → False. This is the exact class
    # both observed incidents (a never-persisted plan; a post-migration stranded
    # holder) left on disk.
    base = plan_context.fixture_dir
    shell = base / 'worktrees' / 'lc-orphan-shell'
    (shell / 'some' / 'leftover').mkdir(parents=True, exist_ok=True)

    assert holder_has_live_worktree('lc-orphan-shell') is False


def test_holder_has_live_worktree_true_when_git_worktree_marker_present(plan_context):
    # A `.git` marker file at the worktree root is the git-worktree gitdir link —
    # its presence means the worktree's git plumbing is still wired up, so the
    # holder is a genuine (possibly mid-recovery) worktree → True.
    base = plan_context.fixture_dir
    worktree = base / 'worktrees' / 'lc-git-marker'
    worktree.mkdir(parents=True, exist_ok=True)
    (worktree / '.git').write_text(
        'gitdir: /main/.git/worktrees/lc-git-marker\n', encoding='utf-8'
    )

    assert holder_has_live_worktree('lc-git-marker') is True


def test_holder_has_live_worktree_true_when_git_marker_is_directory(plan_context):
    # The `.git` marker may also be a directory (a non-linked worktree layout);
    # either shape counts as live git plumbing → True.
    base = plan_context.fixture_dir
    worktree = base / 'worktrees' / 'lc-git-marker-dir'
    (worktree / '.git').mkdir(parents=True, exist_ok=True)

    assert holder_has_live_worktree('lc-git-marker-dir') is True


def test_holder_has_live_worktree_true_when_live_plan_dir_present(plan_context):
    # A live plan dir moved into the worktree
    # (worktrees/{holder}/.plan/local/plans/{holder}) — present while the plan is
    # executing or mid-finalize — is the second live-worktree marker → True, even
    # with no `.git` marker staged.
    base = plan_context.fixture_dir
    live_plan = (
        base / 'worktrees' / 'lc-live-plan' / '.plan' / 'local' / 'plans' / 'lc-live-plan'
    )
    live_plan.mkdir(parents=True, exist_ok=True)

    assert holder_has_live_worktree('lc-live-plan') is True


def test_holder_has_live_worktree_false_when_worktree_dir_absent(plan_context):
    # No worktree directory on disk → False.
    assert holder_has_live_worktree('lc-no-worktree-dir') is False


def test_holder_has_live_worktree_empty_string_is_false(plan_context):
    # An empty holder has no worktree → False (distinct from holder_is_dead('')
    # which is True — the two predicates answer different questions).
    assert holder_has_live_worktree('') is False


def test_holder_has_live_worktree_whitespace_only_is_false(plan_context):
    # Whitespace is stripped to empty → no worktree → False.
    assert holder_has_live_worktree('   ') is False


def test_mid_recovery_holder_is_dead_by_plan_dir_but_has_live_worktree(plan_context):
    # The guard scenario: an interrupted finalize move-back leaves the worktree on
    # disk WITH its git plumbing intact (a `.git` marker) but the plan dir has been
    # moved out of BOTH main and the worktree's .plan. holder_is_dead is True
    # (plan-dir absent everywhere) while holder_has_live_worktree is True (the
    # genuine git-worktree marker is still present), so the acquire guard refuses to
    # auto-reclaim it.
    base = plan_context.fixture_dir
    worktree = base / 'worktrees' / 'lc-mid-recovery'
    worktree.mkdir(parents=True, exist_ok=True)
    (worktree / '.git').write_text(
        'gitdir: /main/.git/worktrees/lc-mid-recovery\n', encoding='utf-8'
    )

    assert holder_is_dead('lc-mid-recovery') is True
    assert holder_has_live_worktree('lc-mid-recovery') is True


@pytest.mark.parametrize(
    'malicious_holder',
    [
        '../evil',
        '../../evil',
        'a/../evil',
        'sub/evil',
        'sub\\evil',
        '..',
        'foo\x00bar',
    ],
)
def test_holder_has_live_worktree_rejects_traversal_holder(plan_context, malicious_holder):
    # holder is a plan-id joined DIRECTLY onto the worktrees root to build a
    # filesystem path. A holder bearing a path separator, a `..` parent segment,
    # or an embedded NUL must be rejected as having no live worktree BEFORE the
    # path is constructed — otherwise a crafted holder could escape the worktrees
    # root, resolve to an unrelated existing dir, and permanently block lock
    # reclamation (a DoS).
    assert holder_has_live_worktree(malicious_holder) is False


def test_holder_has_live_worktree_traversal_does_not_escape_worktrees_root(plan_context):
    # Concrete escape scenario: `../evil` would resolve `worktrees/../evil` to a
    # sibling dir of the worktrees root. Stage that sibling so, absent the guard,
    # the predicate would report the holder "alive". The guard must reject the
    # traversal and return False rather than resolving the escaped path.
    base = plan_context.fixture_dir
    (base / 'evil').mkdir(parents=True, exist_ok=True)  # worktrees/../evil target

    assert holder_has_live_worktree('../evil') is False


# =============================================================================
# _read_json_or_empty — missing / corrupt / non-dict / valid
# =============================================================================


def test_read_json_missing_file_returns_empty(tmp_path):
    missing = tmp_path / 'state.json'

    assert _read_json_or_empty(missing) == {}


def test_read_json_corrupt_content_returns_empty(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text('{not valid json', encoding='utf-8')

    assert _read_json_or_empty(path) == {}


def test_read_json_non_dict_list_returns_empty(tmp_path):
    # A valid-JSON but non-dict top-level shape is also treated as empty so a
    # malformed file cannot corrupt a dict-expecting consumer.
    path = tmp_path / 'state.json'
    path.write_text('[1, 2, 3]', encoding='utf-8')

    assert _read_json_or_empty(path) == {}


def test_read_json_scalar_returns_empty(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text('42', encoding='utf-8')

    assert _read_json_or_empty(path) == {}


def test_read_json_valid_dict_is_returned(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'slots': {'a': 1}}), encoding='utf-8')

    assert _read_json_or_empty(path) == {'slots': {'a': 1}}


# =============================================================================
# _atomic_write_json — round-trip / overwrite / no temp residue
# =============================================================================


def test_atomic_write_round_trips(tmp_path):
    path = tmp_path / 'state.json'

    _atomic_write_json(path, {'held_by': 'plan-x'})

    assert json.loads(path.read_text(encoding='utf-8')) == {'held_by': 'plan-x'}


def test_atomic_write_overwrites_existing(tmp_path):
    path = tmp_path / 'state.json'
    _atomic_write_json(path, {'v': 1})

    _atomic_write_json(path, {'v': 2})

    assert json.loads(path.read_text(encoding='utf-8')) == {'v': 2}


def test_atomic_write_creates_parent_dirs(tmp_path):
    path = tmp_path / 'nested' / 'dir' / 'state.json'

    _atomic_write_json(path, {'ok': True})

    assert json.loads(path.read_text(encoding='utf-8')) == {'ok': True}


def test_atomic_write_leaves_no_temp_file(tmp_path):
    path = tmp_path / 'state.json'

    _atomic_write_json(path, {'v': 1})

    # The temp file (``{name}.{pid}.tmp``) is consumed by os.replace — only the
    # committed file should remain in the directory.
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != 'state.json']
    assert leftovers == []


def test_atomic_write_large_payload_round_trips_without_truncation(tmp_path):
    # POSIX permits os.write to return a partial count, so a single os.write
    # call does not guarantee the whole buffer reaches the file for a large
    # payload. The write-loop must keep writing until every byte is flushed —
    # a large state dict (well past any single-write boundary) must round-trip
    # intact, never truncated to a parse error or a short read.
    path = tmp_path / 'state.json'
    large_state = {'slots': {f'plan-{i:05d}': {'pid': i, 'note': 'x' * 64} for i in range(5000)}}

    _atomic_write_json(path, large_state)

    assert json.loads(path.read_text(encoding='utf-8')) == large_state


# =============================================================================
# _acquire_guard — free / stale-reclamation / timeout
# =============================================================================


def test_acquire_guard_on_free_returns_fd(tmp_path):
    guard = tmp_path / 'state.json.lock'

    fd = _acquire_guard(guard)
    try:
        assert isinstance(fd, int)
        assert guard.exists()
    finally:
        os.close(fd)
        guard.unlink()


def test_acquire_guard_creates_parent_dir(tmp_path):
    guard = tmp_path / 'nested' / 'state.json.lock'

    fd = _acquire_guard(guard)
    try:
        assert guard.exists()
    finally:
        os.close(fd)
        guard.unlink()


def test_acquire_guard_reclaims_stale_guard(tmp_path, monkeypatch):
    # A guard older than the stale threshold is reclaimed (a crashed mutator
    # left it behind). Shrink the threshold so a freshly-created guard counts as
    # stale, then assert acquisition still succeeds.
    monkeypatch.setattr(_mod, '_GUARD_STALE_SECONDS', -1.0)
    guard = tmp_path / 'state.json.lock'
    guard.write_text('', encoding='utf-8')  # pre-existing (stale) guard

    fd = _acquire_guard(guard)
    try:
        assert guard.exists()
    finally:
        os.close(fd)
        guard.unlink()


def test_acquire_guard_times_out_when_held(tmp_path, monkeypatch):
    # A guard that is held and NOT stale cannot be acquired within the budget →
    # TimeoutError. Keep the stale threshold high so the held guard is never
    # reclaimed, and shrink the timeout/backoff so the spin resolves fast.
    monkeypatch.setattr(_mod, '_GUARD_STALE_SECONDS', 10_000.0)
    monkeypatch.setattr(_mod, '_GUARD_TIMEOUT_SECONDS', 0.05)
    monkeypatch.setattr(_mod, '_GUARD_BACKOFF_SECONDS', 0.005)
    guard = tmp_path / 'state.json.lock'

    held_fd = _acquire_guard(guard)
    try:
        raised = False
        try:
            _acquire_guard(guard)
        except TimeoutError:
            raised = True
        assert raised, 'expected TimeoutError when the guard is held and not stale'
    finally:
        os.close(held_fd)
        guard.unlink()


# =============================================================================
# rmw_json — missing pre-state / existing pre-state / mutate semantics
# =============================================================================


def test_rmw_json_missing_file_mutates_over_empty(tmp_path):
    path = tmp_path / 'state.json'

    result = rmw_json(path, lambda state: {**state, 'count': 1})

    assert result == {'count': 1}
    assert json.loads(path.read_text(encoding='utf-8')) == {'count': 1}


def test_rmw_json_receives_existing_state(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'count': 1}), encoding='utf-8')

    seen: dict = {}

    def _mutate(state):
        seen.update(state)
        return {**state, 'count': state['count'] + 1}

    result = rmw_json(path, _mutate)

    assert seen == {'count': 1}  # mutate saw the freshly-read pre-state
    assert result == {'count': 2}
    assert json.loads(path.read_text(encoding='utf-8')) == {'count': 2}


def test_rmw_json_corrupt_pre_state_treated_as_empty(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text('{corrupt', encoding='utf-8')

    result = rmw_json(path, lambda state: {**state, 'rebuilt': True})

    assert result == {'rebuilt': True}


def test_rmw_json_removes_guard_after_commit(tmp_path):
    path = tmp_path / 'state.json'
    guard = path.with_name(f'{path.name}{_mod._GUARD_SUFFIX}')

    rmw_json(path, lambda state: {**state, 'v': 1})

    # The guard is always removed in a ``finally`` so a later mutator is not
    # blocked by a leftover guard file.
    assert not guard.exists()


def test_rmw_json_removes_guard_when_mutate_raises(tmp_path):
    # Even when the mutate callback raises, the guard MUST be removed so a
    # crashed mutator does not wedge the file forever.
    path = tmp_path / 'state.json'
    guard = path.with_name(f'{path.name}{_mod._GUARD_SUFFIX}')

    def _boom(_state):
        raise ValueError('mutate failed')

    raised = False
    try:
        rmw_json(path, _boom)
    except ValueError:
        raised = True

    assert raised
    assert not guard.exists()


def test_rmw_json_returns_committed_state(tmp_path):
    path = tmp_path / 'state.json'

    returned = rmw_json(path, lambda state: {'final': 'state'})

    assert returned == {'final': 'state'}


# =============================================================================
# rmw_json — serialization under concurrency (TOCTOU correctness)
# =============================================================================


@pytest.mark.xdist_group(name="manage_locks_contention")
def test_rmw_json_serializes_concurrent_increments(tmp_path):
    # Two threads each run N increment mutations against the same file. If the
    # read-modify-write were not serialized by the guard, lost updates would
    # leave the final count below 2*N. The guard must make every increment
    # observe the prior committed state, so the final count equals 2*N exactly.
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'count': 0}), encoding='utf-8')
    per_thread = 25

    def _worker():
        for _ in range(per_thread):
            rmw_json(path, lambda state: {'count': state.get('count', 0) + 1})

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final = json.loads(path.read_text(encoding='utf-8'))
    assert final['count'] == 2 * per_thread


def test_rmw_json_second_caller_sees_first_committed_state(tmp_path, monkeypatch):
    # A second mutator that contends on the guard must read the FIRST mutator's
    # committed state, never the stale pre-state. Simulate the race
    # single-threaded by having the first mutate commit, then the second mutate
    # asserts it observed the first's write.
    path = tmp_path / 'state.json'

    rmw_json(path, lambda state: {'owner': 'first'})

    observed: dict = {}

    def _second(state):
        observed.update(state)
        return {**state, 'owner': 'second'}

    result = rmw_json(path, _second)

    assert observed == {'owner': 'first'}  # second saw first's committed state
    assert result == {'owner': 'second'}


def test_rmw_json_blocks_until_guard_released(tmp_path, monkeypatch):
    # When the guard is already held by another holder, a fresh rmw_json call
    # must spin (not error) until the guard is released, then proceed. Hold the
    # guard from a background thread, release it shortly after, and assert the
    # rmw_json call completes successfully once the guard frees.
    monkeypatch.setattr(_mod, '_GUARD_STALE_SECONDS', 10_000.0)
    monkeypatch.setattr(_mod, '_GUARD_TIMEOUT_SECONDS', 5.0)
    monkeypatch.setattr(_mod, '_GUARD_BACKOFF_SECONDS', 0.005)

    path = tmp_path / 'state.json'
    guard = path.with_name(f'{path.name}{_mod._GUARD_SUFFIX}')

    held_fd = _acquire_guard(guard)
    release_done = threading.Event()

    def _release_after_delay():
        time.sleep(0.05)
        os.close(held_fd)
        guard.unlink()
        release_done.set()

    releaser = threading.Thread(target=_release_after_delay)
    releaser.start()

    # This call must block on the held guard, then succeed once it is released.
    result = rmw_json(path, lambda state: {**state, 'after': 'release'})
    releaser.join()

    assert release_done.is_set()
    assert result == {'after': 'release'}
    assert not guard.exists()


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


def test_resolve_lock_log_path_is_main_anchored(tmp_path, monkeypatch):
    # The lock-event log lives under the MAIN-anchored .plan/logs dir, derived
    # from <PLAN_BASE_DIR>.parent / logs / lock-{date}.log — NOT a worktree path.
    base, log_path = _lock_log_base(tmp_path, monkeypatch)

    assert log_path.parent == base.parent / 'logs'
    assert log_path.name.startswith('lock-')
    assert log_path.name.endswith('.log')


def test_resolve_lock_log_path_ignores_worktree_cwd(tmp_path, monkeypatch):
    # Pinning cwd into a worktree fixture does NOT redirect the lock-event log to
    # a worktree-relative path — it stays the single main-anchored timeline.
    base, _ = _lock_log_base(tmp_path, monkeypatch)
    worktree = tmp_path / 'worktrees' / 'some-plan'
    (worktree / '.plan' / 'local').mkdir(parents=True)
    monkeypatch.chdir(worktree)

    log_path = _resolve_lock_log_path()

    assert log_path.parent == base.parent / 'logs'
    assert (worktree / '.plan' / 'logs') != log_path.parent


def test_log_lock_event_appends_lock_tagged_line(tmp_path, monkeypatch):
    _, log_path = _lock_log_base(tmp_path, monkeypatch)

    log_lock_event('merge', 'acquired', lock_id='plan-a')

    content = log_path.read_text(encoding='utf-8')
    # The bracketed [LOCK] tag + (family:event) + lock_id are on the header line,
    # carrying the standard [ts] [LEVEL] [hash] prefix.
    assert '[LOCK] (merge:acquired) plan-a' in content
    assert '[INFO]' in content


def test_log_lock_event_records_each_lifecycle_event(tmp_path, monkeypatch):
    # acquire / blocked / release / stale-reclaim for both primitives all land
    # in the SINGLE main-anchored timeline.
    _, log_path = _lock_log_base(tmp_path, monkeypatch)

    log_lock_event('merge', 'acquired', lock_id='m-1')
    log_lock_event('merge', 'blocked', lock_id='m-2', holder='m-1', waiter='m-2')
    log_lock_event('merge', 'released', lock_id='m-1')
    log_lock_event('merge', 'reclaimed', lock_id='m-3', reclaimed_from='m-dead')
    log_lock_event('build', 'acquired', lock_id='b-1:uuid', active_count=1, waiting_count=0)
    log_lock_event('build', 'blocked', lock_id='b-2:uuid', waiter='b-2', active_count=1, waiting_count=1)
    log_lock_event('build', 'released', lock_id='b-1:uuid', active_count=0, waiting_count=0)
    log_lock_event('build', 'reaped-stale', lock_id='b-3:uuid')

    content = log_path.read_text(encoding='utf-8')
    assert '[LOCK] (merge:acquired) m-1' in content
    assert '[LOCK] (merge:blocked) m-2' in content
    assert '[LOCK] (merge:released) m-1' in content
    assert '[LOCK] (merge:reclaimed) m-3' in content
    assert '[LOCK] (build:acquired) b-1:uuid' in content
    assert '[LOCK] (build:blocked) b-2:uuid' in content
    assert '[LOCK] (build:released) b-1:uuid' in content
    assert '[LOCK] (build:reaped-stale) b-3:uuid' in content


def test_log_lock_event_includes_correlation_fields(tmp_path, monkeypatch):
    _, log_path = _lock_log_base(tmp_path, monkeypatch)

    log_lock_event('merge', 'blocked', lock_id='m-2', holder='m-1', waiter='m-2')

    content = log_path.read_text(encoding='utf-8')
    # Correlation fields are appended as indented lines under the header.
    assert 'holder: m-1' in content
    assert 'waiter: m-2' in content


def test_log_lock_event_reaped_stale_is_warning_level(tmp_path, monkeypatch):
    # The reaped-stale event is logged at WARNING; every other event is INFO.
    _, log_path = _lock_log_base(tmp_path, monkeypatch)

    log_lock_event('build', 'reaped-stale', lock_id='b-stale:uuid')

    content = log_path.read_text(encoding='utf-8')
    assert '[WARNING]' in content
    assert '[LOCK] (build:reaped-stale) b-stale:uuid' in content


def test_log_lock_event_other_events_are_info_level(tmp_path, monkeypatch):
    # Every non-reaped-stale event is INFO — never WARNING.
    _, log_path = _lock_log_base(tmp_path, monkeypatch)

    log_lock_event('merge', 'acquired', lock_id='m-info')

    content = log_path.read_text(encoding='utf-8')
    assert '[INFO]' in content
    assert '[WARNING]' not in content


def test_log_lock_event_appends_not_overwrites(tmp_path, monkeypatch):
    # A second emission appends to the SAME log file; the first line survives.
    _, log_path = _lock_log_base(tmp_path, monkeypatch)

    log_lock_event('merge', 'acquired', lock_id='first')
    log_lock_event('merge', 'released', lock_id='first')

    content = log_path.read_text(encoding='utf-8')
    assert '[LOCK] (merge:acquired) first' in content
    assert '[LOCK] (merge:released) first' in content


def test_log_lock_event_swallows_resolution_failure(tmp_path, monkeypatch):
    # A failure ANYWHERE in the emission body (here: the path resolver raising)
    # is swallowed — log_lock_event is best-effort and MUST NOT raise into the
    # lock action it observes.
    _lock_log_base(tmp_path, monkeypatch)

    def _boom() -> object:
        raise RuntimeError('resolution failed')

    monkeypatch.setattr(_mod, '_resolve_lock_log_path', _boom)

    # No exception propagates.
    log_lock_event('merge', 'acquired', lock_id='plan-a')


def test_log_lock_event_swallows_unwritable_dir(tmp_path, monkeypatch):
    # An open() that raises (unwritable dir / encoding error) is swallowed too —
    # the emission is OUTSIDE the lock's atomic window, so a write failure can
    # never affect lock correctness.
    _lock_log_base(tmp_path, monkeypatch)

    def _raising_open(*_a: object, **_k: object) -> object:
        raise OSError('disk full')

    monkeypatch.setattr('builtins.open', _raising_open)

    # No exception propagates despite the write failing.
    log_lock_event('merge', 'released', lock_id='plan-a')
