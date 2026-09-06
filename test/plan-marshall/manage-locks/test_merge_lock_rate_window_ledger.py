#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for the ``merge_lock.py`` rate window's PER-PR attempt ledger.

The recursion cap is scoped to ``(bot_kind, pr_number)`` while the store is keyed by
``bot_kind`` ALONE. A single stored counter therefore names only whichever PR most
recently claimed the window, and the cap is bypassable through the gap: PR 101 spends
its budget, PR 202 claims once and replaces the record, and PR 101's next claim starts
from zero. The ``attempts_by_pr`` ledger is what makes a displaced PR's count survive
the ownership change.

Its sections, in order:

* Cap survival across a window takeover
* Migration from the pre-ledger record shape
"""


from __future__ import annotations

import json
from pathlib import Path

import pytest
from _merge_lock_rate_window_fixtures import (
    _check,
    _claim,
    _make_live_plan,
    _read_store,
    _release,
    isolated_base,
)

# =============================================================================
# Fixtures and helpers
# =============================================================================


def _write_pre_ledger_record(
    queue_path: Path, *, pr_number: object, attempts: int, holder: str = ''
) -> None:
    """Persist a rate-window record in the shape written BEFORE the ledger existed.

    Hand-built rather than produced by the code under test, and that is the point: a
    record the current writer emits always carries a ledger, so the migration path
    would never be exercised by a store this suite created for itself.
    """
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        json.dumps(
            {
                'waiting': [],
                'rate_windows': {
                    'coderabbit': {
                        'holder': holder,
                        'pr_number': pr_number,
                        'expires_at': 0.0,
                        'attempts': attempts,
                    }
                },
            }
        ),
        encoding='utf-8',
    )


#: The budget the pre-ledger fixtures below are written as already having spent, and
#: the cap they are read back under. A LOCAL pair, deliberately not the shipped
#: default: what these tests assert is that a legacy count is carried across the
#: upgrade at all, and pinning them to the shipped number would make them a second,
#: drifting statement of a value ``TestRateWindowCli`` already owns.
_LEGACY_SPENT = 2


def _spend_the_cap(base: Path, plan_id: str, pr_number: int) -> int:
    """Claim until ``pr_number``'s budget is gone; return the cap that was spent."""
    _make_live_plan(base, plan_id)
    cap: int = _claim(plan_id, pr_number=pr_number)['attempt_cap']
    for _ in range(cap - 1):
        _claim(plan_id, pr_number=pr_number)
    assert _claim(plan_id, pr_number=pr_number)['status'] == 'refused'
    return cap


# =============================================================================
# Cap survival across a window takeover
# =============================================================================


class TestCapSurvivesAWindowTakeover:
    def test_an_exhausted_pr_stays_refused_after_another_pr_claims_the_window(
        self, isolated_base: dict
    ) -> None:
        """The regression this ledger exists for.

        With one counter per ``bot_kind``, the second PR's claim OVERWRITES the first
        PR's spent count, and the first PR's next claim is admitted against a budget
        it had already spent — a whole second recovery run driven at a bot that is
        refusing, which is precisely what the cap exists to stop. The sequence below
        is the real one: the recovery releases the window between attempts, so a
        concurrent plan on another PR can legitimately claim it in between.
        """
        cap = _spend_the_cap(isolated_base['base'], 'plan-a', 101)
        _release('plan-a')
        _make_live_plan(isolated_base['base'], 'plan-b')

        # A DIFFERENT PR takes the window over and writes its own count over the record.
        assert _claim('plan-b', pr_number=202)['attempts'] == 1
        _release('plan-b')

        refused = _claim('plan-a', pr_number=101)

        assert refused['status'] == 'refused', refused
        assert refused['reason'] == 'recovery_cap_exhausted'
        assert refused['attempts'] == cap

    def test_check_still_reports_the_displaced_prs_spent_budget(
        self, isolated_base: dict
    ) -> None:
        """``check`` agrees with the ``claim`` above — the read-before-act invariant.

        A consumer polls ``check`` before deciding to recover. Were the takeover to
        lose the count, ``check`` would report a full budget and the consumer would
        arm a recovery the cap forbids, without ever reaching the refusal.
        """
        cap = _spend_the_cap(isolated_base['base'], 'plan-a', 101)
        _release('plan-a')
        _claim('plan-b', pr_number=202)
        _release('plan-b')

        displaced = _check('plan-a', pr_number=101)

        assert displaced['attempts_for_pr'] == cap, displaced
        assert displaced['attempts_remaining'] == 0

    def test_a_pr_that_never_claimed_still_gets_a_full_budget(
        self, isolated_base: dict
    ) -> None:
        """Matched positive control: the ledger PRESERVES counts, it does not invent them.

        A fix that merely stopped resetting — carrying the previous PR's count forward
        as the new PR's own — would pass every assertion above while refusing a PR that
        has spent nothing. The cap has to stay per-PR in both directions.
        """
        _spend_the_cap(isolated_base['base'], 'plan-a', 101)
        _release('plan-a')
        _claim('plan-b', pr_number=202)
        _release('plan-b')

        fresh = _claim('plan-a', pr_number=303)

        assert fresh['status'] == 'success', fresh
        assert fresh['attempts'] == 1
        assert fresh['attempts_remaining'] == fresh['attempt_cap'] - 1

    def test_every_claimed_prs_count_is_persisted_beside_the_record(
        self, isolated_base: dict
    ) -> None:
        """The survival above is a STORED fact, not an in-memory one.

        Every verb reads the store fresh, so a count that survived only within one
        process would be gone by the next CLI invocation — which is how the recovery
        sequence actually runs.
        """
        cap = _spend_the_cap(isolated_base['base'], 'plan-a', 101)
        _release('plan-a')
        _claim('plan-b', pr_number=202)

        record = _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']

        assert record['attempts_by_pr'] == {'101': cap, '202': 1}, record
        # ...and the top-level field still names the CURRENT holder's PR, which is
        # what `check` / `claim` / `release` publish as `attempts`.
        assert record['pr_number'] == 202
        assert record['attempts'] == 1

    def test_a_release_retains_the_whole_ledger(self, isolated_base: dict) -> None:
        """Release drops the holder; it must drop no count, for any PR."""
        cap = _spend_the_cap(isolated_base['base'], 'plan-a', 101)
        _release('plan-a')
        _claim('plan-b', pr_number=202)

        _release('plan-b')

        record = _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']
        assert record['holder'] == ''
        assert record['attempts_by_pr'] == {'101': cap, '202': 1}, record


# =============================================================================
# Migration from the pre-ledger record shape
# =============================================================================


class TestPreLedgerRecordMigration:
    def test_a_pre_ledger_record_keeps_its_attempts_for_its_own_pr(
        self, isolated_base: dict
    ) -> None:
        """An upgrade must not hand an already-exhausted PR a fresh budget.

        The count in a pre-ledger record belongs to that record's own ``pr_number``,
        so it is seeded into the ledger under that key rather than discarded.
        """
        _write_pre_ledger_record(
            isolated_base['queue_path'], pr_number=101, attempts=_LEGACY_SPENT
        )

        observed = _check('plan-a', pr_number=101, attempt_cap=_LEGACY_SPENT)

        assert observed['attempts_for_pr'] == _LEGACY_SPENT, observed
        assert observed['attempts_remaining'] == 0
        assert _claim('plan-a', pr_number=101, attempt_cap=_LEGACY_SPENT)['status'] == 'refused'

    def test_a_pre_ledger_record_grants_a_different_pr_a_fresh_budget(
        self, isolated_base: dict
    ) -> None:
        """Matched negative control: the seeding is scoped to the record's own PR.

        Seeding the legacy count under every PR would refuse a PR that never claimed.
        """
        _write_pre_ledger_record(
            isolated_base['queue_path'], pr_number=101, attempts=_LEGACY_SPENT
        )

        fresh = _claim('plan-a', pr_number=202, attempt_cap=_LEGACY_SPENT)

        assert fresh['status'] == 'success', fresh
        assert fresh['attempts'] == 1

    def test_the_seeded_count_then_survives_a_takeover_like_any_other(
        self, isolated_base: dict
    ) -> None:
        """Migration and the takeover fix have to hold TOGETHER.

        Seeding alone is not enough: a seeded count that the next PR's claim then
        overwrote would reopen the same bypass one claim later.
        """
        _write_pre_ledger_record(
            isolated_base['queue_path'], pr_number=101, attempts=_LEGACY_SPENT
        )
        _claim('plan-a', pr_number=202, attempt_cap=_LEGACY_SPENT)
        _release('plan-a')

        refused = _claim('plan-a', pr_number=101, attempt_cap=_LEGACY_SPENT)

        assert refused['status'] == 'refused', refused
        assert refused['reason'] == 'recovery_cap_exhausted'

    def test_an_unattributable_count_blocks_nobody_and_is_still_published(
        self, isolated_base: dict
    ) -> None:
        """A record with no readable ``pr_number`` has no PR to charge its count to.

        There is nothing to seed, so the count constrains no caller — but it is still
        surfaced as the raw stored ``attempts`` rather than silently zeroed, because a
        reader inspecting a degraded store needs to see what is actually in it.
        """
        _write_pre_ledger_record(
            isolated_base['queue_path'], pr_number='not-an-int', attempts=_LEGACY_SPENT
        )

        observed = _check('plan-a', pr_number=101, attempt_cap=_LEGACY_SPENT)

        assert observed['attempts'] == _LEGACY_SPENT, observed
        assert observed['attempts_for_pr'] == 0
        assert (
            _claim('plan-a', pr_number=101, attempt_cap=_LEGACY_SPENT)['status'] == 'success'
        )

    @pytest.mark.parametrize(
        'junk',
        ['not-a-mapping', 42, ['101'], {'not-a-number': 3}, {'101': 'not-an-int'}],
    )
    def test_a_malformed_ledger_degrades_to_no_entry_rather_than_crashing(
        self, isolated_base: dict, junk: object
    ) -> None:
        """Same hand-edited-store tolerance the sibling record fields already carry.

        ``attempts`` is zero in every case so no migration seeding fires, which is what
        makes all five junk shapes assert the SAME outcome: the ledger read produced
        nothing, and the claim proceeds on an empty budget rather than raising into the
        merge path that shares this file.
        """
        isolated_base['queue_path'].write_text(
            json.dumps(
                {
                    'rate_windows': {
                        'coderabbit': {
                            'holder': '',
                            'pr_number': 101,
                            'expires_at': 0.0,
                            'attempts': 0,
                            'attempts_by_pr': junk,
                        }
                    }
                }
            ),
            encoding='utf-8',
        )

        result = _claim('plan-a', pr_number=101)

        assert result['status'] == 'success', result
        assert result['attempts'] == 1
