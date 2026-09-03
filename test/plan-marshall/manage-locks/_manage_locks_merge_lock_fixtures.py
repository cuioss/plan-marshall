#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``manage locks merge lock`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
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

Filename note: the modules sharing this preamble are named
``test_manage_locks_merge_lock*.py`` rather than ``test_merge_lock_*.py`` because
pytest's default ``prepend`` import mode requires unique test-module basenames
across the suite.
"""


from __future__ import annotations

import json
from pathlib import Path

import pytest
from _manage_locks_fixtures import _make_live_plan  # noqa: F401 — re-exported to the modules beside this preamble

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-locks', 'merge_lock.py')


merge_lock = load_script_module('plan-marshall', 'manage-locks', 'merge_lock.py', 'merge_lock_under_test')


# Capture the REAL _push_title_token before the autouse _TokenRecorder stub
# replaces it, so the canonical-seam CLI-shape test can exercise the
# actual icon-optional push wrapper (it resolves _run_executor as a module
# global, so a monkeypatch on merge_lock._run_executor still takes effect).
_REAL_PUSH_TITLE_TOKEN = merge_lock._push_title_token


# Same rationale for the set/clear wrappers: the owner-scoping tests must
# exercise the REAL wrappers to observe the constructed argv, not the autouse
# _TokenRecorder stubs that replace them for every other test.
_REAL_SET_TITLE_TOKEN = merge_lock._set_title_token


_REAL_CLEAR_TITLE_TOKEN = merge_lock._clear_title_token


# The shared core owns the [LOCK]-log resolver and the best-effort emission
# swallow. ``merge_lock`` does ``from _locks_core import log_lock_event``, so the
# function closes over the _locks_core module that ``merge_lock`` imported — that
# SAME module instance is recovered from the function's ``__module__`` (NOT a
# fresh ``load_script_module`` copy, which would be a different instance whose
# patches ``merge_lock`` never sees).
import sys as _sys  # noqa: E402

_locks_core = _sys.modules[merge_lock.log_lock_event.__module__]


def _read_lock_log() -> str:
    """Read the main-anchored [LOCK] log, '' when no emission landed yet."""
    log_path = _locks_core._resolve_lock_log_path()
    if not log_path.exists():
        return ''
    return str(log_path.read_text(encoding='utf-8'))


def _read_queue(queue_path: Path) -> dict:
    """Read the persisted FIFO merge-queue state as a dict ('{}' when absent)."""
    if not queue_path.exists():
        return {}
    data: dict = json.loads(queue_path.read_text(encoding='utf-8'))
    return data


def _waiting_plan_ids(queue_path: Path) -> list[str]:
    """Return the FIFO ``waiting`` plan_ids in stored (serialized arrival / list) order."""
    return [e['plan_id'] for e in _read_queue(queue_path).get('waiting', [])]


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


class _TokenRecorder:
    """Records the best-effort title-token set/clear/push calls so a test can
    assert WHAT was surfaced without spawning the real executor subprocess.

    Installed over the three module-level seams ``_set_title_token`` /
    ``_clear_title_token`` / ``_push_title_token`` — the same seam-mock approach
    used by ``test_build_queue*.py`` for the D6 wrapper.
    """

    def __init__(self) -> None:
        self.set_states: list[str] = []
        self.cleared: list[str] = []
        self.pushed_icons: list[str] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(merge_lock, '_set_title_token', lambda _p, state: self.set_states.append(state))
        monkeypatch.setattr(merge_lock, '_clear_title_token', lambda p: self.cleared.append(p))
        # icon is optional: a glyph push (acquire) records the icon; a plain
        # icon-less repaint (the clear path) records None.
        monkeypatch.setattr(
            merge_lock, '_push_title_token', lambda _p, icon=None: self.pushed_icons.append(icon)
        )


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
