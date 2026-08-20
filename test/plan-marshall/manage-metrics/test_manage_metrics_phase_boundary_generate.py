#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `phase-boundary` subcommand of manage_metrics."""


import pytest
from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_generate,
    ns_phase_boundary,
    ns_start_phase,
)
from _manage_metrics_phase_boundary_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _field,
    _freeze_clock,
    _phase_block,
    _read_block,
    cmd_end_phase,
    cmd_generate,
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


# =============================================================================
# Boundary monotonicity detector (D3): a finalize loop-back re-enters an earlier
# phase, so a later phase's start_time precedes an earlier phase's end_time.
# =============================================================================


def test_generate_flags_loopback_non_monotonic_boundary(plan_context):
    """A loop-back row where 6-finalize.start_time precedes 5-execute.end_time is flagged,
    its idle residual guarded (non-negative, non-corrupt), and a warning surfaced.
    """
    # Seed a non-monotonic boundary directly: 5-execute closes at 15:00 while the
    # subsequent 6-finalize re-entry starts at 14:00 (a finalize loop-back). The
    # 6-finalize wall span would otherwise derive a corrupt residual.
    manage_metrics.write_metrics(
        'monotonic-loopback',
        {
            'phases': {
                '5-execute': {
                    'start_time': '2026-05-08T13:00:00+00:00',
                    'end_time': '2026-05-08T15:00:00+00:00',
                    'agent_duration_ms': 60000,
                },
                '6-finalize': {
                    # start precedes 5-execute.end_time (15:00) — non-monotonic.
                    'start_time': '2026-05-08T14:00:00+00:00',
                    'end_time': '2026-05-08T14:30:00+00:00',
                    'agent_duration_ms': 30000,
                },
            },
        },
    )

    result = cmd_generate(ns_generate('monotonic-loopback'))
    assert result['status'] == 'success'
    # 6-finalize is the offending phase (its start precedes 5-execute's end).
    assert result['boundary_monotonicity'] == ['6-finalize']

    content = (plan_context.plan_dir_for('monotonic-loopback') / 'work' / 'metrics.toon').read_text()
    # Top-level warning key persisted.
    assert 'boundary_monotonicity: 6-finalize' in content
    # Per-phase annotation stamped on the offending row.
    fin_block = _phase_block(content, '6-finalize')
    assert _field(fin_block, 'boundary_non_monotonic') == 'true'
    # Idle residual guarded to zero (never a corrupt/negative figure).
    assert _field(fin_block, 'idle_duration_ms') == '0'
    # The recorded boundary fields are NOT rewritten (read-only detector).
    assert _field(fin_block, 'start_time') == '2026-05-08T14:00:00+00:00'
    assert _field(fin_block, 'end_time') == '2026-05-08T14:30:00+00:00'

    # Warning marker rendered under the Phase Breakdown heading.
    md = (plan_context.plan_dir_for('monotonic-loopback') / 'metrics.md').read_text()
    assert 'Boundary monotonicity warning' in md


def test_generate_monotonic_boundaries_have_no_warning(plan_context):
    """A well-ordered sequence produces no boundary_monotonicity warning and the idle
    residual for each phase is derived normally (not guarded).
    """
    manage_metrics.write_metrics(
        'monotonic-clean',
        {
            'phases': {
                '5-execute': {
                    'start_time': '2026-05-08T13:00:00+00:00',
                    'end_time': '2026-05-08T14:00:00+00:00',
                    'agent_duration_ms': 60000,
                },
                '6-finalize': {
                    'start_time': '2026-05-08T14:00:00+00:00',
                    'end_time': '2026-05-08T14:30:00+00:00',
                    'agent_duration_ms': 60000,
                },
            },
        },
    )

    result = cmd_generate(ns_generate('monotonic-clean'))
    assert result['status'] == 'success'
    assert result['boundary_monotonicity'] == []

    content = (plan_context.plan_dir_for('monotonic-clean') / 'work' / 'metrics.toon').read_text()
    assert 'boundary_monotonicity:' not in content
    fin_block = _phase_block(content, '6-finalize')
    assert _field(fin_block, 'boundary_non_monotonic') is None
    # 6-finalize wall = 30m (1800000 ms), worked = 60000 ms -> idle = 1740000 ms.
    assert _field(fin_block, 'idle_duration_ms') == '1740000'

    md = (plan_context.plan_dir_for('monotonic-clean') / 'metrics.md').read_text()
    assert 'Boundary monotonicity warning' not in md


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
