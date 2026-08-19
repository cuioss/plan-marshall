#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `phase-boundary` subcommand of manage_metrics."""


import pytest
from _manage_metrics_fixtures import (
    ns_boundary_status,
    ns_end_phase,
    ns_phase_boundary,
    ns_start_phase,
)
from _manage_metrics_phase_boundary_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _field,
    _phase_block,
    _seed_status_created,
    cmd_boundary_status,
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


def test_phase_boundary_uses_real_1init_start_time_when_present(plan_context):
    """When phase-1-init seeds 1-init.start_time, phase-boundary uses the real value.

    Regression guard for the bootstrap accounting bug fixed by
    fix-1-init-phase-boundary-bootstrap-bug. Phase-1-init (Step 3a) now self-
    records 1-init.start_time via `manage-metrics start-phase --phase 1-init`
    immediately after the plan directory is created. The downstream fused
    `phase-boundary --prev-phase 1-init` call MUST observe this seeded
    timestamp and compute `duration_seconds = end_time - seeded_start_time`
    against it — NOT fall back to the `_read_status_created` backfill, even
    when status.json.created is present.

    This test asserts that path by:
      1. Seeding 1-init.start_time via cmd_start_phase (mirrors phase-1-init Step 3a).
      2. Writing a status.json with a deliberately old `created` timestamp that
         would yield a wildly different (years-long) duration if backfill ran.
      3. Calling cmd_phase_boundary.
      4. Confirming the start_time on the 1-init row equals the seeded value,
         the status.json.created sentinel does NOT appear, and the resulting
         prev_duration_seconds is on the order of seconds (real wall clock
         between seed and end) — not years.
    """
    # Step 1: phase-1-init self-records 1-init.start_time.
    start_res = cmd_start_phase(ns_start_phase('boundary-real-seed', '1-init'))
    seeded_start = start_res['start_time']

    # Step 2: status.json present with a far-past `created` that would
    # produce a years-long duration if the backfill path were taken.
    old_created_ts = '1999-01-01T00:00:00+00:00'
    plan_dir = plan_context.plan_dir_for('boundary-real-seed')
    _seed_status_created(plan_dir, old_created_ts)

    # Step 3: fused phase-boundary call.
    result = cmd_phase_boundary(
        ns_phase_boundary('boundary-real-seed', prev_phase='1-init', next_phase='2-refine')
    )
    assert result['status'] == 'success'

    # Step 4: verify the seeded value was used, not the backfill.
    content_post = (plan_dir / 'work' / 'metrics.toon').read_text()
    assert old_created_ts not in content_post, (
        'status.json.created leaked into metrics — backfill ran despite seeded start_time'
    )
    assert f'start_time: {seeded_start}' in content_post

    # Duration was computed against the seeded start_time → small (seconds),
    # not years. Anything under one day (86400s) proves the real seed was used.
    assert 'prev_duration_seconds' in result
    assert result['prev_duration_seconds'] >= 0
    assert result['prev_duration_seconds'] < 86400, (
        f'prev_duration_seconds={result["prev_duration_seconds"]} suggests backfill '
        f'from status.json.created (1999) was used instead of the seeded start_time'
    )


def test_phase_boundary_status_json_malformed_no_exception(plan_context):
    """status.json malformed → call succeeds, no backfill, no exception."""
    plan_dir = plan_context.plan_dir_for('boundary-backfill-05')
    status_path = plan_dir / 'status.json'
    status_path.write_text('{this is not valid json', encoding='utf-8')

    result = cmd_phase_boundary(
        ns_phase_boundary('boundary-backfill-05', prev_phase='1-init', next_phase='2-refine')
    )
    assert result['status'] == 'success'
    content = (plan_dir / 'work' / 'metrics.toon').read_text()
    init_idx = content.index('[1-init]')
    refine_idx = content.index('[2-refine]') if '[2-refine]' in content else len(content)
    prev_block = content[init_idx:refine_idx]
    assert 'start_time' not in prev_block


# =============================================================================
# D5/D6 — worked <= wall clamp invariant
# =============================================================================


def test_phase_boundary_clamps_worked_to_wall_for_1init_bootstrap(plan_context):
    """1-init bootstrap ordering: a forwarded worked window longer than the
    created→end wall span is clamped so worked <= wall (a worked>wall row can
    never be persisted)."""
    # status.json.created at "now" makes the backfilled wall span near-zero;
    # the forwarded worked window is deliberately huge.
    created_ts = manage_metrics.now_utc_iso()
    plan_dir = plan_context.plan_dir_for('clamp-1init')
    _seed_status_created(plan_dir, created_ts)

    # No prior start-phase; backfill from status.json.created.
    result = cmd_phase_boundary(
        ns_phase_boundary(
            'clamp-1init',
            prev_phase='1-init',
            next_phase='2-refine',
            duration_ms=999_999_999,
        )
    )

    assert result['status'] == 'success'
    content = (plan_dir / 'work' / 'metrics.toon').read_text()
    block = _phase_block(content, '1-init')
    wall_s = float(_field(block, 'duration_seconds'))
    worked_s = float(_field(block, 'agent_duration_seconds'))
    worked_ms = int(_field(block, 'agent_duration_ms'))
    assert worked_s <= wall_s
    assert worked_ms <= round(wall_s * 1000)
    assert worked_ms < 999_999_999


def test_end_phase_clamps_worked_to_wall(plan_context):
    """cmd_end_phase write site: the symmetric clamp bounds worked to wall."""
    # Start then immediately end (wall span ~0); forward a huge worked window.
    cmd_start_phase(ns_start_phase('clamp-end', '3-outline'))

    result = cmd_end_phase(
        ns_end_phase('clamp-end', phase='3-outline', duration_ms=888_888_888)
    )

    assert result['status'] == 'success'
    content = (plan_context.plan_dir_for('clamp-end') / 'work' / 'metrics.toon').read_text()
    block = _phase_block(content, '3-outline')
    wall_s = float(_field(block, 'duration_seconds'))
    worked_s = float(_field(block, 'agent_duration_seconds'))
    assert worked_s <= wall_s
    assert int(_field(block, 'agent_duration_ms')) < 888_888_888


def test_clamp_does_not_inflate_when_worked_below_wall(plan_context):
    """Negative control: a worked window SMALLER than wall is left unchanged."""
    # A created timestamp far in the past makes the wall span comfortably
    # exceed the small forwarded worked window.
    created_ts = '2026-01-01T00:00:00+00:00'
    plan_dir = plan_context.plan_dir_for('clamp-below')
    _seed_status_created(plan_dir, created_ts)

    # Small worked window (2 s) vs a multi-month wall span.
    cmd_phase_boundary(
        ns_phase_boundary(
            'clamp-below',
            prev_phase='1-init',
            next_phase='2-refine',
            duration_ms=2000,
        )
    )

    # The clamp only bounds, never inflates: worked stays 2 s.
    content = (plan_dir / 'work' / 'metrics.toon').read_text()
    block = _phase_block(content, '1-init')
    assert int(_field(block, 'agent_duration_ms')) == 2000
    assert float(_field(block, 'agent_duration_seconds')) == 2.0


# =============================================================================
# D8 — retrospective_tokens attribution write
# =============================================================================


def test_retrospective_tokens_recorded_on_finalize_when_forwarded(plan_context):
    """--retrospective-tokens forwarded → recorded as a [6-finalize] sub-field."""
    cmd_start_phase(ns_start_phase('retro-attr', '6-finalize'))

    result = cmd_end_phase(
        ns_end_phase(
            'retro-attr',
            phase='6-finalize',
            total_tokens=10000,
            retrospective_tokens=4000,
        )
    )

    assert result['status'] == 'success'
    assert result['retrospective_tokens'] == 4000
    content = (plan_context.plan_dir_for('retro-attr') / 'work' / 'metrics.toon').read_text()
    block = _phase_block(content, '6-finalize')
    assert _field(block, 'retrospective_tokens') == '4000'


def test_retrospective_tokens_absent_when_not_forwarded(plan_context):
    """No --retrospective-tokens → the field is absent (no schema migration)."""
    cmd_start_phase(ns_start_phase('retro-absent', '6-finalize'))

    # total_tokens only, no retrospective attribution.
    result = cmd_end_phase(
        ns_end_phase('retro-absent', phase='6-finalize', total_tokens=10000)
    )

    # default-absent: the field never appears.
    assert result['status'] == 'success'
    assert 'retrospective_tokens' not in result
    content = (plan_context.plan_dir_for('retro-absent') / 'work' / 'metrics.toon').read_text()
    block = _phase_block(content, '6-finalize')
    assert _field(block, 'retrospective_tokens') is None


# =============================================================================
# boundary-status — resume-time half-stamped boundary detection (read-only)
# =============================================================================
#
# `boundary-status` is the detection half of cross-session boundary
# reconciliation. It reads work/metrics.toon and classifies the boundary into
# --next-phase as one of: stamped / missing / not_applicable. It MUST perform
# ZERO mutation of metrics.toon — the orchestrator reacts to a `missing` verdict
# by issuing an explicit `phase-boundary` call.


# -----------------------------------------------------------------------------
# missing: half-stamped boundary (the case the verb exists to detect)
# -----------------------------------------------------------------------------


def test_boundary_status_missing_when_next_phase_has_no_start(plan_context):
    """next phase has no start_time → classification 'missing' on next.start_time.

    The prior session self-transitioned the status but skipped the paired
    phase-boundary, so the resuming phase has no start_time yet. With no
    --prev-phase, only the "current phase has no start" condition is evaluated.
    """
    # 1-init started + closed, but 2-refine never opened.
    cmd_start_phase(ns_start_phase('bs-missing-next', '1-init'))
    cmd_phase_boundary(ns_phase_boundary('bs-missing-next', prev_phase='1-init', next_phase='2-refine'))

    # On resume, the orchestrator is about to enter 3-outline, which has no start.
    result = cmd_boundary_status(ns_boundary_status('bs-missing-next', next_phase='3-outline'))

    assert result['status'] == 'success'
    assert result['classification'] == 'missing'
    assert result['next_phase'] == '3-outline'
    assert result['prev_phase'] == '-'
    assert result['missing_fields'] == '3-outline.start_time'
