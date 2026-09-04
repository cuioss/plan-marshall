#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `phase-boundary` subcommand of manage_metrics."""


from _manage_metrics_fixtures import (
    ns_accumulate,
    ns_end_phase,
    ns_start_phase,
)
from _manage_metrics_phase_boundary_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _field,
    _freeze_clock,
    _read_block,
    _seed_guarded_plan_dirs,
    cmd_accumulate_agent_usage,
    cmd_end_phase,
    cmd_start_phase,
    manage_metrics,
)

# -----------------------------------------------------------------------------
# Rule A — an accumulator-sourced re-close ASSIGNS, never doubles
# -----------------------------------------------------------------------------


def test_accumulator_sourced_reclose_assigns_without_doubling(plan_context, monkeypatch):
    """A re-close resolving from the accumulator assigns the cumulative total.

    The accumulator is already cumulative (``accumulate-agent-usage`` only ever
    sums and no verb resets it), so a blanket ``+=`` at the write site would
    double-count it on every re-close. Two flag-less closes against the same
    accumulator must leave the row equal to the accumulator, not twice it.
    """
    plan_id = 'accum-source-assign'
    cmd_accumulate_agent_usage(ns_accumulate(plan_id, '5-execute', total_tokens=5000, tool_uses=3))

    _freeze_clock(monkeypatch, '2026-05-08T13:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T13:01:40+00:00')
    first = cmd_end_phase(ns_end_phase(plan_id, phase='5-execute'))
    assert first['accumulator_used'] is True
    assert _field(_read_block(plan_context, plan_id, '5-execute'), 'total_tokens') == '5000'

    _freeze_clock(monkeypatch, '2026-05-08T14:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T14:03:20+00:00')
    second = cmd_end_phase(ns_end_phase(plan_id, phase='5-execute'))

    block = _read_block(plan_context, plan_id, '5-execute')
    # ASSIGNED, not added — 10000 would be the double-count defect.
    assert _field(block, 'total_tokens') == '5000'
    assert _field(block, 'tool_uses') == '3'
    assert second['close_count'] == 2
    # Rule B is NOT provenance-keyed: the wall span accumulates regardless of
    # where the token values came from.
    assert _field(block, 'duration_seconds') == '300.0'


def test_mixed_flag_then_accumulator_close_assigns_cumulative_total(plan_context, monkeypatch):
    """A flag close followed by an accumulator close lands on the cumulative total.

    The accumulator spans the WHOLE phase, so once it becomes the resolution
    source it is authoritative for the row — the earlier flag delta is subsumed
    by it rather than added to it.
    """
    plan_id = 'accum-mixed-sequence'

    _freeze_clock(monkeypatch, '2026-05-08T13:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T13:01:40+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='5-execute', total_tokens=1000, tool_uses=5))
    assert _field(_read_block(plan_context, plan_id, '5-execute'), 'total_tokens') == '1000'

    # The accumulator now holds the phase's cumulative figure.
    cmd_accumulate_agent_usage(ns_accumulate(plan_id, '5-execute', total_tokens=8000, tool_uses=9))

    _freeze_clock(monkeypatch, '2026-05-08T14:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T14:03:20+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='5-execute'))

    block = _read_block(plan_context, plan_id, '5-execute')
    # Assigned from the accumulator — neither 1000 (replaced away) nor 9000 (added).
    assert _field(block, 'total_tokens') == '8000'
    assert _field(block, 'tool_uses') == '9'
    assert _field(block, 'close_count') == '2'


# -----------------------------------------------------------------------------
# close_count
# -----------------------------------------------------------------------------


def test_close_count_increments_on_every_close(plan_context, monkeypatch):
    """close_count counts closes, starting at 1 and rising on each re-close."""
    plan_id = 'accum-close-count'

    _freeze_clock(monkeypatch, '2026-05-08T13:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '4-plan'))

    for index, stamp in enumerate(
        ('2026-05-08T13:01:00+00:00', '2026-05-08T13:02:00+00:00', '2026-05-08T13:03:00+00:00'),
        start=1,
    ):
        _freeze_clock(monkeypatch, stamp)
        result = cmd_end_phase(ns_end_phase(plan_id, phase='4-plan'))
        assert result['close_count'] == index

    assert _field(_read_block(plan_context, plan_id, '4-plan'), 'close_count') == '3'


def test_single_close_records_close_count_of_one(plan_context, monkeypatch):
    """A phase closed exactly once carries close_count 1 (never absent, never 0)."""
    plan_id = 'accum-close-count-single'
    _freeze_clock(monkeypatch, '2026-05-08T13:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '4-plan'))
    _freeze_clock(monkeypatch, '2026-05-08T13:01:00+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='4-plan'))

    assert _field(_read_block(plan_context, plan_id, '4-plan'), 'close_count') == '1'


# -----------------------------------------------------------------------------
# Rule B anchor — max(start_time, prior_end_time)
# -----------------------------------------------------------------------------


def test_bare_second_close_adds_only_span_since_prior_end(plan_context, monkeypatch):
    """A second close with NO intervening start-phase anchors on the prior end_time.

    Entry 1 spans 13:00:00 → 13:01:40 (100 s). The second close fires at 13:05:00
    with ``start_time`` still at 13:00:00, so anchoring on ``start_time`` would add
    the full 300 s and double-count the first entry's 100 s. Anchoring on the
    prior ``end_time`` adds only the genuinely-new 200 s.
    """
    plan_id = 'accum-anchor-prior-end'

    _freeze_clock(monkeypatch, '2026-05-08T13:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T13:01:40+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='5-execute'))
    assert _field(_read_block(plan_context, plan_id, '5-execute'), 'duration_seconds') == '100.0'

    # No start-phase in between — the stale start_time must lose to prior end_time.
    _freeze_clock(monkeypatch, '2026-05-08T13:05:00+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='5-execute'))

    block = _read_block(plan_context, plan_id, '5-execute')
    assert _field(block, 'duration_seconds') == '300.0'
    # 400.0 is the start_time-anchored answer, which double-counts entry 1.
    assert _field(block, 'duration_seconds') != '400.0'
    assert _field(block, 'start_time') == '2026-05-08T13:00:00+00:00'


def test_loopback_reentry_anchors_on_restamped_start_time(plan_context, monkeypatch):
    """A loop-back re-entry re-stamps start_time, which then wins the anchor.

    Entry 1 closes at 13:01:40; the re-entry starts at 14:00:00 — later than that
    prior end_time — so the second span runs from the NEW start (200 s), not from
    the prior end (3560 s, which would bill the idle gap between the two entries).
    """
    plan_id = 'accum-anchor-new-start'

    _freeze_clock(monkeypatch, '2026-05-08T13:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T13:01:40+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='5-execute'))

    _freeze_clock(monkeypatch, '2026-05-08T14:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T14:03:20+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='5-execute'))

    block = _read_block(plan_context, plan_id, '5-execute')
    assert _field(block, 'duration_seconds') == '300.0'
    # 3660.0 (100 s + 3560 s) is the prior-end-anchored answer, which would bill
    # the gap spent in another phase to this row.
    assert _field(block, 'duration_seconds') != '3660.0'


def test_first_close_duration_is_plain_end_minus_start(plan_context, monkeypatch):
    """Negative control: a FIRST close is byte-identical to end_time - start_time."""
    plan_id = 'accum-first-close-span'
    _freeze_clock(monkeypatch, '2026-05-08T13:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '3-outline'))
    _freeze_clock(monkeypatch, '2026-05-08T13:02:30+00:00')
    cmd_end_phase(ns_end_phase(plan_id, phase='3-outline'))

    assert _field(_read_block(plan_context, plan_id, '3-outline'), 'duration_seconds') == '150.0'


def test_unparseable_prior_end_time_leaves_duration_untouched(plan_context, monkeypatch):
    """A malformed prior end_time leaves duration_seconds untouched, never partial."""
    plan_id = 'accum-bad-prior-end'
    manage_metrics.write_metrics(
        plan_id,
        {
            'phases': {
                '5-execute': {
                    'start_time': '2026-05-08T13:00:00+00:00',
                    'end_time': 'not-a-timestamp',
                    'duration_seconds': 100.0,
                },
            },
        },
    )

    _freeze_clock(monkeypatch, '2026-05-08T13:05:00+00:00')
    result = cmd_end_phase(ns_end_phase(plan_id, phase='5-execute'))

    assert result['status'] == 'success'
    # Untouched — not a partial value derived from a half-parsed anchor.
    assert _field(_read_block(plan_context, plan_id, '5-execute'), 'duration_seconds') == '100.0'


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
