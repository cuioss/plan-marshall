#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `phase-boundary` subcommand of manage_metrics."""


import pytest
from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_start_phase,
)
from _manage_metrics_phase_boundary_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _field,
    _freeze_clock,
    _read_block,
    cmd_end_phase,
    cmd_start_phase,
    manage_metrics,
)


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    """Auto-seed ``status.json`` at the require_plan_exists chokepoint.

    The patched guard resolves the plan dir via the real ``get_plan_dir`` and, for
    any plan_id NOT registered as unseeded, writes the ``status.json`` sentinel
    before delegating to the genuine ``require_plan_exists``. This keeps every
    positive test's happy path intact without per-test seeding, while the
    negative tests (which call ``_register_unseeded``) still exercise the real
    ``plan_not_found`` failure.
    """
    _UNSEEDED_PLAN_IDS.clear()
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        if plan_id not in _UNSEEDED_PLAN_IDS:
            plan_dir = real_get_plan_dir(plan_id)
            plan_dir.mkdir(parents=True, exist_ok=True)
            sentinel = plan_dir / 'status.json'
            if not sentinel.is_file():
                sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context


# -----------------------------------------------------------------------------
# Rule C — accumulate first, THEN clamp the sum
# -----------------------------------------------------------------------------


def test_reclose_clamps_summed_worked_to_accumulated_wall(plan_context, monkeypatch):
    """The SUMMED worked value is clamped to the accumulated wall span.

    Fixture chosen so the two candidate orderings disagree, making this test
    discriminate rather than pass under either:

      - entry 1: wall 100 s, worked delta 40 000 ms → stored 40 000 (unclamped)
      - entry 2: wall +100 s (accumulated 200 s = 200 000 ms), worked delta 500 000 ms

      add-then-clamp (correct):   min(40 000 + 500 000, 200 000) = 200 000
      clamp-delta-then-add (bad): min(500 000, 200 000) + 40 000 = 240 000

    240 000 ms exceeds the 200 000 ms accumulated wall and would break the
    documented ``Worked <= Reported (wall)`` invariant.
    """
    plan_id = 'accum-clamp-ordering'

    _freeze_clock(monkeypatch, '2026-05-08T13:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T13:01:40+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='5-execute', duration_ms=40_000))
    assert _field(_read_block(plan_context, plan_id, '5-execute'), 'agent_duration_ms') == '40000'

    _freeze_clock(monkeypatch, '2026-05-08T14:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T14:01:40+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='5-execute', duration_ms=500_000))

    block = _read_block(plan_context, plan_id, '5-execute')
    assert _field(block, 'duration_seconds') == '200.0'
    assert _field(block, 'agent_duration_ms') == '200000'
    assert _field(block, 'agent_duration_ms') != '240000'
    # The invariant the ordering exists to protect.
    assert float(_field(block, 'agent_duration_seconds')) <= float(_field(block, 'duration_seconds'))


def test_reclose_does_not_inflate_worked_below_accumulated_wall(plan_context, monkeypatch):
    """Negative control: a summed worked value under the accumulated wall is untouched."""
    plan_id = 'accum-clamp-below'

    _freeze_clock(monkeypatch, '2026-05-08T13:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T13:01:40+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='5-execute', duration_ms=40_000))

    _freeze_clock(monkeypatch, '2026-05-08T14:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T14:01:40+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='5-execute', duration_ms=60_000))

    block = _read_block(plan_context, plan_id, '5-execute')
    # 40 000 + 60 000 = 100 000, comfortably under the 200 000 ms accumulated wall.
    assert _field(block, 'agent_duration_ms') == '100000'
    assert _field(block, 'agent_duration_seconds') == '100.0'


def test_worked_stays_within_wall_after_reclose(plan_context, monkeypatch):
    """Worked <= Reported (wall) holds on a re-entered row for a huge worked window."""
    plan_id = 'accum-invariant-reclose'

    _freeze_clock(monkeypatch, '2026-05-08T13:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T13:01:40+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='5-execute', duration_ms=999_999_999))

    _freeze_clock(monkeypatch, '2026-05-08T14:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T14:03:20+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='5-execute', duration_ms=999_999_999))

    block = _read_block(plan_context, plan_id, '5-execute')
    wall_s = float(_field(block, 'duration_seconds'))
    worked_s = float(_field(block, 'agent_duration_seconds'))
    assert wall_s == 300.0
    assert worked_s <= wall_s
    assert int(_field(block, 'agent_duration_ms')) == 300_000


# -----------------------------------------------------------------------------
# Documented timestamp-vs-duration divergence
# -----------------------------------------------------------------------------


def test_reentered_row_duration_diverges_from_timestamp_span(plan_context, monkeypatch):
    """On a re-entered row duration_seconds != end_time - start_time, by design.

    ``start_time`` stays re-entry-scoped (the latest entry's start) while
    ``duration_seconds`` is the cumulative active span, so the two are no longer
    interchangeable definitions. The divergence here is 100 s — an entire entry's
    span, far beyond any rounding artifact.
    """
    plan_id = 'accum-divergence'

    _freeze_clock(monkeypatch, '2026-05-08T13:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T13:01:40+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='5-execute'))

    _freeze_clock(monkeypatch, '2026-05-08T14:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T14:03:20+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='5-execute'))

    block = _read_block(plan_context, plan_id, '5-execute')
    # start_time is the LATEST entry's start, not the first entry's.
    assert _field(block, 'start_time') == '2026-05-08T14:00:00+00:00'
    assert _field(block, 'end_time') == '2026-05-08T14:03:20+00:00'

    timestamp_span_s = 200.0  # 14:00:00 → 14:03:20
    accumulated_s = float(_field(block, 'duration_seconds'))
    assert accumulated_s == 300.0
    assert accumulated_s != timestamp_span_s
    # The excess is exactly entry 1's active span — total ACTIVE time, excluding
    # the gap spent in another phase.
    assert accumulated_s - timestamp_span_s == 100.0
