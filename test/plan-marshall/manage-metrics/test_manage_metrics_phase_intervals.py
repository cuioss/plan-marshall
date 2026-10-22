#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the per-interval phase windows ``enrich`` attributes usage to.

A phase that is re-entered occupies more than one interval. The window lookup
must emit one window per interval, in order, so usage dated inside a
6-finalize interval is attributed to 6-finalize rather than to the surrounding
5-execute window.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from _manage_metrics_fixtures import ns_phase_boundary, ns_start_phase
from _manage_metrics_module_fixtures import (
    _seed_guarded_plan_dirs,
    cmd_phase_boundary,
    cmd_start_phase,
    manage_metrics,
)

_BASE = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)


def _at(minutes: int) -> str:
    """Return the ISO stamp *minutes* after the fixed clock."""
    return (_BASE + timedelta(minutes=minutes)).isoformat()


@pytest.fixture()
def clock(monkeypatch):
    """Drive ``now_utc_iso`` from a mutable clock so intervals are deterministic."""
    state = {'now': _at(0)}
    monkeypatch.setattr(manage_metrics, 'now_utc_iso', lambda: state['now'])
    return state


def _drive_re_entry(plan_id: str, clock) -> None:
    """Record a 5→6→5→6 transition sequence, closing each interval as it ends."""
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    transitions = [(5, '5-execute', '6-finalize'), (10, '6-finalize', '5-execute')]
    transitions += [(20, '5-execute', '6-finalize'), (30, '6-finalize', '5-execute')]
    for minutes, prev_phase, next_phase in transitions:
        clock['now'] = _at(minutes)
        cmd_phase_boundary(ns_phase_boundary(plan_id, prev_phase, next_phase))


def test_phase_window_lookup_emits_one_window_per_interval(plan_context, clock):
    """A 5→6→5→6 phase log yields four windows, in the order they were open."""
    plan_id = 'phase-intervals-four-windows'
    _drive_re_entry(plan_id, clock)

    windows = manage_metrics._phase_window_lookup(plan_id)

    assert [phase for phase, _start, _end in windows] == [
        '5-execute',
        '6-finalize',
        '5-execute',
        '6-finalize',
    ]
    assert [(start.isoformat(), end.isoformat()) for _phase, start, end in windows] == [
        (_at(0), _at(5)),
        (_at(5), _at(10)),
        (_at(10), _at(20)),
        (_at(20), _at(30)),
    ]


def test_usage_inside_the_first_finalize_interval_belongs_to_finalize(plan_context, clock):
    """A message dated inside the first 6-finalize interval is not booked to 5-execute.

    With one window per phase NAME, 5-execute's window would run from its first
    start to its last end and swallow the finalize interval in between.
    """
    plan_id = 'phase-intervals-first-finalize'
    _drive_re_entry(plan_id, clock)
    windows = manage_metrics._phase_window_lookup(plan_id)

    moment = datetime.fromisoformat(_at(7))

    owners = [phase for phase, start, end in windows if start <= moment < end]

    assert owners == ['6-finalize']


def test_a_store_without_intervals_falls_back_to_one_window_per_phase(plan_context, clock):
    """A pre-interval store still attributes its usage from the row's own pair."""
    plan_id = 'phase-intervals-legacy-store'
    clock['now'] = _at(0)
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    clock['now'] = _at(30)
    cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))

    data = manage_metrics.read_metrics_raw(plan_id)
    data['phases']['6-finalize']['end_time'] = _at(40)
    data.pop(manage_metrics._PHASE_INTERVALS_FIELD, None)
    manage_metrics.write_metrics(plan_id, data)

    windows = manage_metrics._phase_window_lookup(plan_id)

    # 5-execute never closed, so only 6-finalize contributes a complete window.
    assert windows == [('6-finalize', datetime.fromisoformat(_at(30)), datetime.fromisoformat(_at(40)))]
