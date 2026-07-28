#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``merge_lock.py`` ``rate-window`` verbs — the cross-plan claim on
ONE review bot's rate window, co-tenanting the merge-lock store.

Contract under test (manage-locks/SKILL.md § "The rate window shares the STORE,
never the MUTEX" + § Canonical invocations → ``merge_lock — rate-window {claim,
check,release}``):

* **TOCTOU-safe claim** — the claim mutation runs inside the shared
  :func:`_locks_core.rmw_json` critical section, so N concurrent claimers on the
  same ``bot_kind`` produce exactly ONE holder; the rest are ``blocked``.
* **Idempotent for the self-holder** — a re-claim by the current holder renews the
  same record in place rather than contending or creating a second claim.
* **Holder-liveness reclamation** — a claim whose recorded holder no longer
  corresponds to a live plan is reclaimable (reusing the shared
  :func:`_locks_core.holder_is_dead` predicate); a LIVE holder's unexpired window
  is not.
* **Expiry reclamation** — an elapsed window is reclaimable even when its holder
  is live: the window, not the plan, is what the claim guards.
* **Recursion cap** — a plan may generate at most ``attempt_cap`` recovery events
  per bot per PR; the attempt past the cap is REFUSED with an explicit
  ``recovery_cap_exhausted`` verdict and mutates nothing. The counter is scoped to
  ``(bot_kind, pr_number)`` and SURVIVES a release, so releasing and re-claiming
  cannot reset the cap.
* **Non-mutating check** — ``check`` never writes the store; it reports the
  window's own observable state (``expired`` / ``seconds_remaining``), which is
  what the recovery sequence polls between paced sleeps and what gates the
  trigger-comment fallback.
* **Store co-tenancy, NOT mutex coupling** — a rate-window claim leaves the
  ``waiting`` FIFO list and ``merge.lock`` untouched, and a merge acquire/release
  round-trip leaves ``rate_windows`` intact (the sibling-key-preservation
  invariant; its merge-side half lives in
  ``test_manage_locks_merge_lock.py``).
* **Degraded-state tolerance** — a corrupt or absent ``rate_windows`` value
  degrades to an empty mapping and is rebuilt rather than crashing.

Isolation: every test runs against an isolated ``PLAN_BASE_DIR`` staged under
``tmp_path`` so the suite never contends for the real
``.plan/local/merge-queue.json`` under ``-n auto``.
"""

from __future__ import annotations

import json
import time
from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from conftest import load_script_module

merge_lock = load_script_module(
    'plan-marshall', 'manage-locks', 'merge_lock.py', 'merge_lock_rate_window_under_test'
)


# =============================================================================
# Fixtures and helpers
# =============================================================================


@pytest.fixture
def isolated_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated PLAN_BASE_DIR under tmp_path.

    Mirrors ``test_manage_locks_merge_lock.py``'s fixture: the rate-window state
    lives in the SAME main-anchored store the FIFO admission queue uses, so both
    resolve to ``<base>/merge-queue.json``.
    """
    base = tmp_path / 'main' / '.plan' / 'local'
    (base / 'plans').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return {
        'base': base,
        'lock_path': base / 'merge.lock',
        'queue_path': base / 'merge-queue.json',
    }


def _make_live_plan(base: Path, plan_id: str) -> None:
    """Create a holder plan directory so the holder counts as LIVE."""
    (base / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)


def _read_store(queue_path: Path) -> dict:
    """Read the persisted merge-queue store as a dict ('{}' when absent)."""
    if not queue_path.exists():
        return {}
    data: dict = json.loads(queue_path.read_text(encoding='utf-8'))
    return data


def _claim(
    plan_id: str, bot_kind: str = 'coderabbit', pr_number: int = 42, window_seconds: float = 3600.0
) -> dict:
    result: dict = merge_lock.run_rate_window(
        Namespace(
            action='claim',
            plan_id=plan_id,
            bot_kind=bot_kind,
            pr_number=pr_number,
            window_seconds=window_seconds,
        )
    )
    return result


def _check(plan_id: str, bot_kind: str = 'coderabbit') -> dict:
    result: dict = merge_lock.run_rate_window(
        Namespace(action='check', plan_id=plan_id, bot_kind=bot_kind)
    )
    return result


def _release(plan_id: str, bot_kind: str = 'coderabbit') -> dict:
    result: dict = merge_lock.run_rate_window(
        Namespace(action='release', plan_id=plan_id, bot_kind=bot_kind)
    )
    return result


# =============================================================================
# Claim
# =============================================================================


class TestRateWindowClaim:
    def test_claim_records_holder_expiry_and_attempt(self, isolated_base: dict) -> None:
        result = _claim('plan-a')

        assert result['status'] == 'success', result
        assert result['action'] == 'claimed'
        assert result['bot_kind'] == 'coderabbit'
        assert result['pr_number'] == 42
        assert result['attempts'] == 1
        assert result['attempts_remaining'] == result['attempt_cap'] - 1
        assert result['seconds_remaining'] > 0

        record = _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']
        assert record['holder'] == 'plan-a'
        assert record['pr_number'] == 42
        assert record['attempts'] == 1

    def test_self_holder_reclaim_renews_in_place(self, isolated_base: dict) -> None:
        """Idempotent for the self-holder: no contention, no second record."""
        _make_live_plan(isolated_base['base'], 'plan-a')
        _claim('plan-a')

        second = _claim('plan-a')

        assert second['status'] == 'success', second
        assert second['action'] == 'renewed'
        assert second['reclaimed_from'] is None
        windows = _read_store(isolated_base['queue_path'])['rate_windows']
        assert list(windows) == ['coderabbit']
        assert windows['coderabbit']['holder'] == 'plan-a'

    def test_foreign_live_holder_with_open_window_blocks(self, isolated_base: dict) -> None:
        _make_live_plan(isolated_base['base'], 'plan-a')
        _claim('plan-a')

        blocked = _claim('plan-b')

        assert blocked['status'] == 'blocked', blocked
        assert blocked['reason'] == 'window_held_by_other_plan'
        assert blocked['holder'] == 'plan-a'
        assert blocked['seconds_remaining'] > 0
        # No mutation: plan-a still holds it.
        assert _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']['holder'] == 'plan-a'

    def test_dead_holder_is_reclaimed(self, isolated_base: dict) -> None:
        """holder_is_dead reclamation — plan-a never had a plan dir, so it is dead."""
        _claim('plan-a')

        reclaimed = _claim('plan-b')

        assert reclaimed['status'] == 'success', reclaimed
        assert reclaimed['action'] == 'reclaimed'
        assert reclaimed['reclaimed_from'] == 'plan-a'
        assert _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']['holder'] == 'plan-b'

    def test_expired_window_is_reclaimable_even_from_a_live_holder(self, isolated_base: dict) -> None:
        """The WINDOW, not the plan, is what the claim guards."""
        _make_live_plan(isolated_base['base'], 'plan-a')
        _claim('plan-a', window_seconds=-1.0)

        reclaimed = _claim('plan-b')

        assert reclaimed['status'] == 'success', reclaimed
        assert reclaimed['action'] == 'reclaimed'
        assert reclaimed['reclaimed_from'] == 'plan-a'

    def test_concurrent_claims_produce_exactly_one_holder(self, isolated_base: dict) -> None:
        """TOCTOU: the rmw_json critical section admits exactly one claimer."""
        plan_ids = [f'plan-{n}' for n in 'abcdef']
        for plan_id in plan_ids:
            _make_live_plan(isolated_base['base'], plan_id)

        with ThreadPoolExecutor(max_workers=len(plan_ids)) as pool:
            results = list(pool.map(_claim, plan_ids))

        successes = [r for r in results if r['status'] == 'success']
        blocked = [r for r in results if r['status'] == 'blocked']
        assert len(successes) == 1, results
        assert len(blocked) == len(plan_ids) - 1, results
        stored_holder = _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']['holder']
        assert stored_holder == successes[0]['holder']


# =============================================================================
# Recursion cap
# =============================================================================


class TestRecursionCap:
    def test_attempt_past_the_cap_is_refused_with_an_explicit_verdict(self, isolated_base: dict) -> None:
        _make_live_plan(isolated_base['base'], 'plan-a')
        cap = _claim('plan-a')['attempt_cap']

        for _ in range(cap - 1):
            assert _claim('plan-a')['status'] == 'success'

        refused = _claim('plan-a')

        assert refused['status'] == 'refused', refused
        assert refused['reason'] == 'recovery_cap_exhausted'
        assert refused['attempts'] == cap
        assert refused['attempt_cap'] == cap

    def test_refusal_mutates_nothing(self, isolated_base: dict) -> None:
        _make_live_plan(isolated_base['base'], 'plan-a')
        cap = _claim('plan-a')['attempt_cap']
        for _ in range(cap - 1):
            _claim('plan-a')
        before = _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']

        _claim('plan-a')

        assert _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit'] == before

    def test_cap_survives_release_and_reclaim(self, isolated_base: dict) -> None:
        """Releasing between attempts must NOT reset the cap — the recovery
        sequence releases the window after every generated event, so a
        release-resets-counter would make the cap vacuous."""
        _make_live_plan(isolated_base['base'], 'plan-a')
        cap = _claim('plan-a')['attempt_cap']
        _release('plan-a')
        for _ in range(cap - 1):
            assert _claim('plan-a')['status'] == 'success'
            _release('plan-a')

        refused = _claim('plan-a')

        assert refused['status'] == 'refused', refused
        assert refused['reason'] == 'recovery_cap_exhausted'

    def test_cap_is_scoped_per_pr(self, isolated_base: dict) -> None:
        _make_live_plan(isolated_base['base'], 'plan-a')
        cap = _claim('plan-a', pr_number=42)['attempt_cap']
        for _ in range(cap - 1):
            _claim('plan-a', pr_number=42)
        assert _claim('plan-a', pr_number=42)['status'] == 'refused'

        other_pr = _claim('plan-a', pr_number=43)

        assert other_pr['status'] == 'success', other_pr
        assert other_pr['attempts'] == 1


# =============================================================================
# Check (non-mutating) — the observable the recovery sequence polls
# =============================================================================


class TestRateWindowCheck:
    def test_check_on_unclaimed_bot_reports_free(self, isolated_base: dict) -> None:
        result = _check('plan-a')

        assert result['status'] == 'free', result
        assert result['holder'] is None
        assert result['attempts'] == 0
        assert not isolated_base['queue_path'].exists()

    def test_check_does_not_mutate_the_store(self, isolated_base: dict) -> None:
        _claim('plan-a')
        before = _read_store(isolated_base['queue_path'])

        _check('plan-b')

        assert _read_store(isolated_base['queue_path']) == before

    def test_open_window_reports_not_expired_so_the_trigger_stays_gated(self, isolated_base: dict) -> None:
        """The trigger-comment fallback is reachable only after the window elapses.
        While the claim is unexpired, the observable the recovery sequence polls
        says so — a premature trigger has no branch to enter."""
        _claim('plan-a')

        result = _check('plan-a')

        assert result['status'] == 'held', result
        assert result['expired'] is False
        assert result['seconds_remaining'] > 0

    def test_elapsed_window_reports_expired(self, isolated_base: dict) -> None:
        _claim('plan-a', window_seconds=-1.0)

        result = _check('plan-a')

        assert result['status'] == 'free', result
        assert result['expired'] is True
        assert result['seconds_remaining'] == 0.0


# =============================================================================
# Release
# =============================================================================


class TestRateWindowRelease:
    def test_release_clears_the_holder_but_retains_the_attempt_count(self, isolated_base: dict) -> None:
        _claim('plan-a')

        result = _release('plan-a')

        assert result['status'] == 'success', result
        assert result['action'] == 'released'
        assert result['attempts'] == 1
        record = _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']
        assert record['holder'] == ''
        assert record['attempts'] == 1

    def test_release_of_an_unclaimed_window_is_a_noop(self, isolated_base: dict) -> None:
        result = _release('plan-a')

        assert result['status'] == 'success', result
        assert result['action'] == 'noop'
        assert result['holder'] is None

    def test_release_never_drops_a_foreign_holder(self, isolated_base: dict) -> None:
        _make_live_plan(isolated_base['base'], 'plan-a')
        _claim('plan-a')

        result = _release('plan-b')

        assert result['action'] == 'noop', result
        assert result['holder'] == 'plan-a'
        assert _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']['holder'] == 'plan-a'


# =============================================================================
# Store co-tenancy — shares the STORE, never the MUTEX
# =============================================================================


class TestStoreIsolationFromTheMergeMutex:
    def test_claim_leaves_the_waiting_fifo_and_merge_lock_untouched(self, isolated_base: dict) -> None:
        """The converse of the sibling-key-preservation regression: a rate-window
        claim must not create, read, reclaim, or release ``merge.lock``, and must
        not mutate the ``waiting`` FIFO list."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        waiting_before = _read_store(isolated_base['queue_path'])['waiting']
        lock_before = isolated_base['lock_path'].read_text(encoding='utf-8')

        _claim('plan-b')
        _release('plan-b')

        store = _read_store(isolated_base['queue_path'])
        assert store['waiting'] == waiting_before
        assert isolated_base['lock_path'].read_text(encoding='utf-8') == lock_before
        # ...and the claim's own key landed alongside, not instead of, `waiting`.
        assert 'rate_windows' in store

    def test_claim_does_not_block_on_a_foreign_merge_lock_holder(self, isolated_base: dict) -> None:
        """A bot cooldown can never stall behind the merge serializer, and vice
        versa: plan-b claims a window while plan-a holds the merge mutex."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        result = _claim('plan-b')

        assert result['status'] == 'success', result
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-a'


# =============================================================================
# Degraded-state tolerance
# =============================================================================


class TestDegradedState:
    @pytest.mark.parametrize('junk', ['not-a-mapping', 42, ['a', 'b']])
    def test_corrupt_rate_windows_value_is_rebuilt(self, isolated_base: dict, junk: object) -> None:
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [], 'rate_windows': junk}), encoding='utf-8'
        )

        result = _claim('plan-a')

        assert result['status'] == 'success', result
        assert result['attempts'] == 1

    def test_malformed_record_fields_degrade_to_defaults(self, isolated_base: dict) -> None:
        isolated_base['queue_path'].write_text(
            json.dumps(
                {
                    'rate_windows': {
                        'coderabbit': {
                            'holder': 'plan-a',
                            'pr_number': 'not-an-int',
                            'expires_at': 'not-a-number',
                            'attempts': 'not-an-int',
                        }
                    }
                }
            ),
            encoding='utf-8',
        )

        result = _check('plan-b')

        assert result['status'] == 'free', result
        assert result['pr_number'] is None
        assert result['attempts'] == 0

    def test_corrupt_store_does_not_crash_the_merge_path(self, isolated_base: dict) -> None:
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': 'junk', 'rate_windows': 'junk'}), encoding='utf-8'
        )

        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        assert result['status'] == 'success', result
        assert result['admission'] == 'admitted'


# =============================================================================
# Window expiry is wall-clock derived
# =============================================================================


def test_expires_at_is_derived_from_the_supplied_window_length(isolated_base: dict) -> None:
    before = time.time()

    result = _claim('plan-a', window_seconds=900.0)

    assert result['expires_at'] >= before + 900.0
    assert result['seconds_remaining'] <= 900.0
