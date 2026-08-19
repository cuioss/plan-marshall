#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `phase-boundary` subcommand of manage_metrics.

Covers:
  - end-of-prev + start-of-next persisted in a single call
  - optional token/duration/tool-uses forwarded to end-phase
  - metrics.md regenerated as a side-effect
  - invalid phase names rejected for either side
  - boundary works even when the previous phase had no start_time
"""


import pytest
from _manage_metrics_fixtures import (
    ns_accumulate,
    ns_end_phase,
    ns_phase_boundary,
    ns_start_phase,
)
from _manage_metrics_phase_boundary_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _field,
    _freeze_clock,
    _read_block,
    cmd_accumulate_agent_usage,
    cmd_end_phase,
    cmd_phase_boundary,
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
# Rule A + Rule B — two explicit-flag closes accumulate every field
# -----------------------------------------------------------------------------


def test_two_flag_closes_accumulate_all_five_fields(plan_context, monkeypatch):
    """Two explicit-flag closes of one phase sum all five accumulated fields.

    Entry 1 spans 100 s and forwards a 40 s worked window; the loop-back entry 2
    spans 200 s and forwards 60 s. Every field must hold the SUM across both
    closes, not entry 2 alone — the defect this write path fixes.
    """
    plan_id = 'accum-two-flag-closes'

    # --- Entry 1: 13:00:00 → 13:01:40 (100 s wall) ---
    _freeze_clock(monkeypatch, '2026-05-08T13:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T13:01:40+00:00')
    first = cmd_end_phase(
        ns_end_phase(
            plan_id,
            phase='5-execute',
            total_tokens=1000,
            tool_uses=5,
            duration_ms=40_000,
            retrospective_tokens=100,
        )
    )
    assert first['status'] == 'success'
    assert first['close_count'] == 1
    assert first['total_tokens'] == 1000

    # --- Entry 2 (the loop-back): re-stamped start 14:00:00 → 14:03:20 (200 s) ---
    _freeze_clock(monkeypatch, '2026-05-08T14:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T14:03:20+00:00')
    second = cmd_end_phase(
        ns_end_phase(
            plan_id,
            phase='5-execute',
            total_tokens=2000,
            tool_uses=7,
            duration_ms=60_000,
            retrospective_tokens=200,
        )
    )
    assert second['status'] == 'success'
    assert second['close_count'] == 2

    block = _read_block(plan_context, plan_id, '5-execute')
    # Rule A — each flag-sourced delta added onto the row.
    assert _field(block, 'total_tokens') == '3000'
    assert _field(block, 'tool_uses') == '12'
    assert _field(block, 'retrospective_tokens') == '300'
    # Rule C — worked accumulated (40 s + 60 s), comfortably under the 300 s wall.
    assert _field(block, 'agent_duration_ms') == '100000'
    assert _field(block, 'agent_duration_seconds') == '100.0'
    # Rule B — active spans summed: 100 s + 200 s. The re-entry re-stamped
    # start_time, so entry 2 anchors on that new start (14:00:00) and contributes
    # 200 s; anchoring on the prior end_time instead would have added 3560 s.
    assert _field(block, 'duration_seconds') == '300.0'
    # The result echoes the PERSISTED row value, not the per-close delta.
    assert second['total_tokens'] == 3000
    assert second['duration_seconds'] == 300.0


def test_flag_close_accumulates_on_phase_boundary_writer_too(plan_context, monkeypatch):
    """The fused phase-boundary writer accumulates identically to end-phase."""
    plan_id = 'accum-boundary-writer'

    _freeze_clock(monkeypatch, '2026-05-08T13:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T13:01:40+00:00')
    first = cmd_phase_boundary(
        ns_phase_boundary(
            plan_id,
            prev_phase='5-execute',
            next_phase='6-finalize',
            total_tokens=1000,
            tool_uses=5,
            duration_ms=40_000,
        )
    )
    assert first['prev_close_count'] == 1

    # Loop-back: 6-finalize → 5-execute, then close 5-execute a second time.
    _freeze_clock(monkeypatch, '2026-05-08T14:00:00+00:00')
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    _freeze_clock(monkeypatch, '2026-05-08T14:03:20+00:00')
    second = cmd_phase_boundary(
        ns_phase_boundary(
            plan_id,
            prev_phase='5-execute',
            next_phase='6-finalize',
            total_tokens=2000,
            tool_uses=7,
            duration_ms=60_000,
        )
    )

    assert second['prev_close_count'] == 2
    assert second['prev_total_tokens'] == 3000
    block = _read_block(plan_context, plan_id, '5-execute')
    assert _field(block, 'total_tokens') == '3000'
    assert _field(block, 'tool_uses') == '12'
    assert _field(block, 'agent_duration_ms') == '100000'
    assert _field(block, 'duration_seconds') == '300.0'


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
