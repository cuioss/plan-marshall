#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for ``manage-locks/build_queue.py`` — the bounded-``k``-slot build-queue
concurrency limiter with a FIFO waiting queue.

Scope: the cap-disagreement detection and reporting path. Because the cap is
resolved per process while the queue is shared host-wide, two sessions can admit
against different caps; every entry is therefore stamped at admission with
``admitted_under_max_slots`` and ``acquire`` compares its own resolved cap against
the stamps of the entries already in the queue.

Contract under test:

* **The stamp is written once and carried forward** — a new entry records the cap
  it was ACTUALLY admitted under, on the admitted path and the enqueued path
  alike, and a promotion moves that entry with its ORIGINAL stamp rather than
  re-stamping it under whatever cap the promoting call resolved.
* **Three-valued verdict, with ``disagree`` outranking ``unknown``** —
  ``cap_agreement`` is ``disagree`` when any stamped entry was admitted under a
  different cap, otherwise ``unknown`` when at least one entry carries no usable
  stamp, otherwise ``agree``. A proven disagreement is not softened by a second
  entry that could not be compared.
* **The verdict never travels without its population** —
  ``cap_compared_count`` publishes how many entries were examined (``0`` for an
  empty queue) and ``cap_unstamped_count`` how many of those could not be
  compared, so an ``agree`` can never be read off a comparison that never
  happened. This is the ADR-009 /
  ``manage-locks/standards/scope-limited-negative-is-unknown.md`` obligation: a
  scope-limited negative is ``unknown``, not a clean negative.
* **An unusable stamp is unstamped, never agreement** — an absent stamp, a
  ``bool``, and a non-positive ``int`` all count toward
  ``cap_unstamped_count``. A ``bool`` is the load-bearing case: ``True`` is an
  ``int`` subclass equal to ``1``, so an unguarded comparison against a cap of 1
  would report a false ``agree``.
* **Reported, never reconciled** — the disagreement changes NOTHING about the
  admission. The admitting caller applies its own cap, the existing stamps are
  left byte-identical, and neither value is picked as authoritative.
* **Reported on three surfaces** — the ``acquire`` result, exactly one
  ``cap_disagreement`` entry on the ``warnings[]`` channel the build wrapper
  already surfaces, and exactly one WARN ``[LOCK]`` ``cap-disagreement`` event
  per acquire (not one per disagreeing holder).
"""

from __future__ import annotations

import time
from argparse import Namespace
from pathlib import Path
from typing import Any

from _build_queue_fixtures import (
    _make_live_plan,
    _read_lock_log,
    _read_queue,
    _set_max_slots,
    _write_queue,
    build_queue,
    isolated_base,
)

_STAMP = build_queue.STAMP_ADMITTED_UNDER_MAX_SLOTS

_LOCK_EVENT_MARKER = '[LOCK] (build:cap-disagreement)'


def _entry(
    entry_id: str,
    plan_id: str,
    project_root: Path,
    *,
    stamp: Any = None,
    omit_stamp: bool = False,
) -> dict[str, Any]:
    """Build one queue entry, fresh enough that the time-based reaper leaves it.

    ``active_since`` is ``now`` so the entry is never over-age (the reap
    threshold is ``2 × 600 s`` by default) — this module is about the cap
    comparison, and an entry the reaper removed first would be compared against
    nothing.

    ``omit_stamp`` writes NO ``admitted_under_max_slots`` key at all (the
    pre-existing-entry case, written before the stamp shipped), which is distinct
    from ``stamp`` holding an unusable value.
    """
    entry: dict[str, Any] = {
        'id': entry_id,
        'plan_id': plan_id,
        'ts': 0.0,
        'active_since': time.time(),
        'project_root': str(project_root),
    }
    if not omit_stamp:
        entry[_STAMP] = stamp
    return entry


def _warnings_with_code(result: dict[str, Any], code: str) -> list[dict[str, str]]:
    """Return the result's warnings carrying ``code``."""
    return [w for w in result['warnings'] if w['code'] == code]


class TestCapDisagreementVerdict:
    def test_a_stamped_entry_admitted_under_a_different_cap_reports_disagree(self, isolated_base: dict) -> None:
        """An entry stamped 8 and a caller resolving 5 reports `disagree` with one
        row naming the holder, exactly one warning, and exactly one WARN [LOCK]
        event — while the admission itself behaves exactly as it would without
        the check."""
        base = isolated_base['base']
        main_repo = isolated_base['main_repo']
        _set_max_slots(isolated_base['home'], 5)
        _make_live_plan(base, 'plan-foreign')
        _make_live_plan(base, 'plan-new')
        foreign_id = 'plan-foreign:foreign-uuid'
        _write_queue(
            isolated_base['queue_path'],
            {
                'active': [_entry(foreign_id, 'plan-foreign', main_repo, stamp=8)],
                'waiting': [],
                'run_log': [],
            },
        )

        result = build_queue.run_acquire(Namespace(plan_id='plan-new'))

        # The verdict, with the population it was computed over.
        assert result['cap_agreement'] == build_queue.CAP_AGREEMENT_DISAGREE
        assert result['cap_compared_count'] == 1
        assert result['cap_unstamped_count'] == 0

        # One row, naming the holder well enough to find the other side of it.
        assert result['cap_disagreement'] == [
            {
                'id': foreign_id,
                'plan_id': 'plan-foreign',
                'project_root': str(main_repo),
                _STAMP: 8,
            }
        ]

        # Exactly one warning, and it is the cap-disagreement one.
        assert len(result['warnings']) == 1
        warning = result['warnings'][0]
        assert warning['code'] == build_queue.WARNING_CAP_DISAGREEMENT
        # Both caps and the holder's project are named — a warning that stated
        # only "the caps disagree" would leave the operator nothing to act on.
        assert 'max_slots=5' in warning['message']
        assert 'max_slots=8' in warning['message']
        assert str(main_repo) in warning['message']
        assert 'never reconciled' in warning['message']

        # Exactly ONE [LOCK] event, at WARNING, for the whole acquire.
        content = _read_lock_log()
        assert content.count(_LOCK_EVENT_MARKER) == 1
        assert 'WARNING' in content
        assert 'caller_max_slots: 5' in content
        assert 'disagreeing_count: 1' in content

        # Admission is untouched: the caller's own cap applies (5), so a queue
        # holding 1 entry admits rather than blocks.
        assert result['admission'] == 'admitted'
        assert result['max_slots'] == 5
        assert result['active_count'] == 2
        assert result['waiting_count'] == 0

    def test_the_disagreeing_entrys_stamp_is_left_exactly_as_admitted(self, isolated_base: dict) -> None:
        """Detection never reconciles: the existing entry's stamp is not rewritten
        to the admitting caller's cap, and no value is picked as authoritative."""
        base = isolated_base['base']
        main_repo = isolated_base['main_repo']
        _set_max_slots(isolated_base['home'], 5)
        _make_live_plan(base, 'plan-foreign')
        _make_live_plan(base, 'plan-new')
        foreign_id = 'plan-foreign:foreign-uuid'
        _write_queue(
            isolated_base['queue_path'],
            {
                'active': [_entry(foreign_id, 'plan-foreign', main_repo, stamp=8)],
                'waiting': [],
                'run_log': [],
            },
        )

        build_queue.run_acquire(Namespace(plan_id='plan-new'))

        state = _read_queue(isolated_base['queue_path'])
        foreign = next(e for e in state['active'] if e['id'] == foreign_id)
        assert foreign[_STAMP] == 8  # NOT rewritten to the caller's 5
        new_entry = next(e for e in state['active'] if e['id'] != foreign_id)
        assert new_entry[_STAMP] == 5  # the caller stamped its OWN cap

    def test_equal_stamps_report_agree(self, isolated_base: dict) -> None:
        """Every stamped entry matching the caller's cap reports `agree`, with the
        compared population published alongside."""
        base = isolated_base['base']
        main_repo = isolated_base['main_repo']
        _set_max_slots(isolated_base['home'], 5)
        _make_live_plan(base, 'plan-peer')
        _make_live_plan(base, 'plan-new')
        _write_queue(
            isolated_base['queue_path'],
            {
                'active': [_entry('plan-peer:peer-uuid', 'plan-peer', main_repo, stamp=5)],
                'waiting': [],
                'run_log': [],
            },
        )

        result = build_queue.run_acquire(Namespace(plan_id='plan-new'))

        assert result['cap_agreement'] == build_queue.CAP_AGREEMENT_AGREE
        assert result['cap_compared_count'] == 1
        assert result['cap_unstamped_count'] == 0
        assert result['cap_disagreement'] == []
        assert _warnings_with_code(result, build_queue.WARNING_CAP_DISAGREEMENT) == []
        assert _LOCK_EVENT_MARKER not in _read_lock_log()

    def test_an_entry_with_no_stamp_reports_unknown_and_publishes_the_unstamped_count(
        self, isolated_base: dict
    ) -> None:
        """A pre-existing entry carrying no stamp, and nothing else in the queue,
        reports `unknown` with cap_unstamped_count 1 — never `agree`, because
        nothing was actually compared."""
        base = isolated_base['base']
        main_repo = isolated_base['main_repo']
        _set_max_slots(isolated_base['home'], 5)
        _make_live_plan(base, 'plan-legacy')
        _make_live_plan(base, 'plan-new')
        _write_queue(
            isolated_base['queue_path'],
            {
                'active': [_entry('plan-legacy:legacy-uuid', 'plan-legacy', main_repo, omit_stamp=True)],
                'waiting': [],
                'run_log': [],
            },
        )

        result = build_queue.run_acquire(Namespace(plan_id='plan-new'))

        assert result['cap_agreement'] == build_queue.CAP_AGREEMENT_UNKNOWN
        assert result['cap_compared_count'] == 1
        assert result['cap_unstamped_count'] == 1
        assert result['cap_disagreement'] == []
        # `unknown` is not a disagreement, so it raises neither surface.
        assert _warnings_with_code(result, build_queue.WARNING_CAP_DISAGREEMENT) == []
        assert _LOCK_EVENT_MARKER not in _read_lock_log()

    def test_an_unusable_stamp_counts_as_unstamped_never_as_agreement(self, isolated_base: dict) -> None:
        """A `bool` stamp and a non-positive stamp are both unusable and count
        toward `unknown`.

        The `bool` is the load-bearing case: `True` is an `int` subclass equal to
        `1`, so against a caller cap of 1 an unguarded comparison would report a
        false `agree` — the clean-negative direction, which is the dangerous one.
        """
        base = isolated_base['base']
        main_repo = isolated_base['main_repo']
        _set_max_slots(isolated_base['home'], 1)
        for name in ('plan-bool', 'plan-zero', 'plan-new'):
            _make_live_plan(base, name)
        _write_queue(
            isolated_base['queue_path'],
            {
                'active': [_entry('plan-bool:bool-uuid', 'plan-bool', main_repo, stamp=True)],
                'waiting': [_entry('plan-zero:zero-uuid', 'plan-zero', main_repo, stamp=0)],
                'run_log': [],
            },
        )

        result = build_queue.run_acquire(Namespace(plan_id='plan-new'))

        assert result['cap_agreement'] == build_queue.CAP_AGREEMENT_UNKNOWN
        assert result['cap_compared_count'] == 2
        assert result['cap_unstamped_count'] == 2
        assert result['cap_disagreement'] == []

    def test_disagree_outranks_unknown(self, isolated_base: dict) -> None:
        """One disagreeing stamped entry plus one unstamped entry reports
        `disagree` — a proven disagreement is not softened by a second entry that
        could not be compared — while still publishing the unstamped count."""
        base = isolated_base['base']
        main_repo = isolated_base['main_repo']
        _set_max_slots(isolated_base['home'], 5)
        for name in ('plan-foreign', 'plan-legacy', 'plan-new'):
            _make_live_plan(base, name)
        _write_queue(
            isolated_base['queue_path'],
            {
                'active': [
                    _entry('plan-foreign:foreign-uuid', 'plan-foreign', main_repo, stamp=8),
                    _entry('plan-legacy:legacy-uuid', 'plan-legacy', main_repo, omit_stamp=True),
                ],
                'waiting': [],
                'run_log': [],
            },
        )

        result = build_queue.run_acquire(Namespace(plan_id='plan-new'))

        assert result['cap_agreement'] == build_queue.CAP_AGREEMENT_DISAGREE
        assert result['cap_compared_count'] == 2
        assert result['cap_unstamped_count'] == 1
        assert [row['id'] for row in result['cap_disagreement']] == ['plan-foreign:foreign-uuid']

    def test_an_empty_queue_reports_agree_with_a_published_population_of_zero(self, isolated_base: dict) -> None:
        """An empty queue reports `agree` with cap_compared_count 0.

        The population is what makes this verdict readable: a bare `agree` over
        an empty queue is indistinguishable from `agree` over a fully-compared
        one, and publishing the count is what keeps an empty comparison visible
        rather than passing as a clean bill of health.
        """
        _set_max_slots(isolated_base['home'], 5)
        _make_live_plan(isolated_base['base'], 'plan-new')

        result = build_queue.run_acquire(Namespace(plan_id='plan-new'))

        assert result['cap_agreement'] == build_queue.CAP_AGREEMENT_AGREE
        assert result['cap_compared_count'] == 0
        assert result['cap_unstamped_count'] == 0
        assert result['cap_disagreement'] == []
        assert result['warnings'] == []


class TestAdmissionStamp:
    def test_an_admitted_entry_is_stamped_with_the_cap_it_was_admitted_under(self, isolated_base: dict) -> None:
        """A first-acquire admit records the caller's resolved cap on the entry."""
        _set_max_slots(isolated_base['home'], 3)
        _make_live_plan(isolated_base['base'], 'plan-a')

        acq = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert acq['admission'] == 'admitted'

        state = _read_queue(isolated_base['queue_path'])
        assert state['active'][0][_STAMP] == 3

    def test_an_enqueued_entry_is_stamped_too(self, isolated_base: dict) -> None:
        """A blocked (enqueued) entry carries the stamp from the moment it is
        queued — not only once it becomes active — so a waiting entry is never an
        uncomparable hole in the population."""
        base = isolated_base['base']
        _set_max_slots(isolated_base['home'], 1)
        for name in ('plan-held', 'plan-w1'):
            _make_live_plan(base, name)

        build_queue.run_acquire(Namespace(plan_id='plan-held'))
        blocked = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        assert blocked['admission'] == 'blocked'

        state = _read_queue(isolated_base['queue_path'])
        assert state['waiting'][0][_STAMP] == 1

    def test_a_promoted_entry_keeps_its_original_stamp(self, isolated_base: dict) -> None:
        """A promotion carries the entry's ORIGINAL stamp forward.

        The waiter is enqueued under a cap of 1, the machine-global cap then moves
        to 9, and the release that promotes it resolves 9 — yet the promoted entry
        must still report the 1 it was actually admitted under. Re-stamping on
        promotion would erase the very disagreement the stamp exists to expose.
        """
        base = isolated_base['base']
        _set_max_slots(isolated_base['home'], 1)
        for name in ('plan-held', 'plan-w1'):
            _make_live_plan(base, name)

        held = build_queue.run_acquire(Namespace(plan_id='plan-held'))
        w1 = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        assert w1['admission'] == 'blocked'

        _set_max_slots(isolated_base['home'], 9)
        build_queue.run_release(Namespace(plan_id='plan-held', id=held['id']))

        state = _read_queue(isolated_base['queue_path'])
        promoted = next(e for e in state['active'] if e['id'] == w1['id'])
        assert promoted[_STAMP] == 1  # the cap it was admitted under, not 9
