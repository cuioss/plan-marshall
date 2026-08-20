#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `phase-boundary` subcommand of manage_metrics."""


from _manage_metrics_fixtures import (
    ns_boundary_status,
    ns_end_phase,
    ns_phase_boundary,
    ns_start_phase,
)
from _manage_metrics_phase_boundary_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _UNSEEDED_PLAN_IDS,
    _field,
    _phase_block,
    _register_unseeded,
    _seed_guarded_plan_dirs,
    _seed_status_created,
    cmd_boundary_status,
    cmd_end_phase,
    cmd_phase_boundary,
    cmd_start_phase,
    manage_metrics,
)

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


def test_boundary_status_missing_when_prev_started_but_not_ended(plan_context):
    """prev has start_time but no end_time → 'missing' on prev.end_time.

    The prior session opened the prev phase and self-transitioned away without
    the paired phase-boundary closing it — the canonical half-stamped state.
    """
    # 1-init opened, but never closed (no phase-boundary), and 2-refine opened.
    cmd_start_phase(ns_start_phase('bs-missing-prev', '1-init'))
    cmd_start_phase(ns_start_phase('bs-missing-prev', '2-refine'))

    result = cmd_boundary_status(
        ns_boundary_status('bs-missing-prev', prev_phase='1-init', next_phase='2-refine')
    )

    assert result['status'] == 'success'
    assert result['classification'] == 'missing'
    assert result['prev_phase'] == '1-init'
    assert result['next_phase'] == '2-refine'
    assert result['missing_fields'] == '1-init.end_time'


def test_boundary_status_missing_reports_both_offending_fields(plan_context):
    """prev unclosed AND next unopened → both fields listed in missing_fields."""
    # 1-init opened, never closed; 2-refine never opened.
    cmd_start_phase(ns_start_phase('bs-missing-both', '1-init'))

    result = cmd_boundary_status(
        ns_boundary_status('bs-missing-both', prev_phase='1-init', next_phase='2-refine')
    )

    assert result['status'] == 'success'
    assert result['classification'] == 'missing'
    fields = result['missing_fields'].split(',')
    assert '1-init.end_time' in fields
    assert '2-refine.start_time' in fields


# -----------------------------------------------------------------------------
# stamped: complete boundary left unchanged
# -----------------------------------------------------------------------------


def test_boundary_status_stamped_when_boundary_complete(plan_context):
    """prev has start+end AND next has start → classification 'stamped'."""
    # 1-init opened+closed (phase-boundary writes 1-init.end_time + 2-refine.start_time).
    cmd_start_phase(ns_start_phase('bs-stamped', '1-init'))
    cmd_phase_boundary(ns_phase_boundary('bs-stamped', prev_phase='1-init', next_phase='2-refine'))

    result = cmd_boundary_status(
        ns_boundary_status('bs-stamped', prev_phase='1-init', next_phase='2-refine')
    )

    assert result['status'] == 'success'
    assert result['classification'] == 'stamped'
    assert result['prev_phase'] == '1-init'
    assert result['next_phase'] == '2-refine'
    # No missing_fields on a stamped verdict.
    assert 'missing_fields' not in result


def test_boundary_status_stamped_when_prev_omitted_and_next_has_start(plan_context):
    """--prev-phase omitted + next has start_time → classification 'stamped'."""
    cmd_start_phase(ns_start_phase('bs-stamped-noprev', '3-outline'))

    result = cmd_boundary_status(ns_boundary_status('bs-stamped-noprev', next_phase='3-outline'))

    assert result['status'] == 'success'
    assert result['classification'] == 'stamped'
    assert result['prev_phase'] == '-'
    assert result['next_phase'] == '3-outline'


def test_boundary_status_leaves_metrics_unchanged(plan_context):
    """boundary-status performs ZERO mutation of metrics.toon (read-only)."""
    cmd_start_phase(ns_start_phase('bs-readonly', '1-init'))
    cmd_phase_boundary(ns_phase_boundary('bs-readonly', prev_phase='1-init', next_phase='2-refine'))

    metrics_file = plan_context.plan_dir_for('bs-readonly') / 'work' / 'metrics.toon'
    before = metrics_file.read_text()

    # Run the detector across several boundary shapes — none may mutate the file.
    cmd_boundary_status(ns_boundary_status('bs-readonly', prev_phase='1-init', next_phase='2-refine'))
    cmd_boundary_status(ns_boundary_status('bs-readonly', next_phase='3-outline'))
    cmd_boundary_status(ns_boundary_status('bs-readonly', prev_phase='2-refine', next_phase='3-outline'))

    after = metrics_file.read_text()
    assert before == after


# -----------------------------------------------------------------------------
# not_applicable: prev phase never started — nothing to reconcile
# -----------------------------------------------------------------------------


def test_boundary_status_not_applicable_when_prev_phase_never_started(plan_context):
    """--prev-phase supplied but it has no metrics row → 'not_applicable'.

    Covers the request's 'neither start nor end recorded' path for the prev
    side: the prev phase never ran, so there is no boundary to reconcile.
    """
    # Only 2-refine started; 1-init has no row at all.
    cmd_start_phase(ns_start_phase('bs-na', '2-refine'))

    result = cmd_boundary_status(
        ns_boundary_status('bs-na', prev_phase='1-init', next_phase='2-refine')
    )

    assert result['status'] == 'success'
    assert result['classification'] == 'not_applicable'
    assert result['prev_phase'] == '1-init'
    assert result['next_phase'] == '2-refine'
    # not_applicable carries a reason, never missing_fields.
    assert 'missing_fields' not in result


def test_boundary_status_prev_omitted_never_yields_not_applicable(plan_context):
    """When --prev-phase is omitted, not_applicable never applies — only the
    'next has no start' condition is evaluated, yielding 'missing'."""
    # Empty metrics: 3-outline has no start_time, no prev supplied.
    result = cmd_boundary_status(ns_boundary_status('bs-noprev-na', next_phase='3-outline'))

    assert result['status'] == 'success'
    assert result['classification'] == 'missing'
    assert result['missing_fields'] == '3-outline.start_time'


# -----------------------------------------------------------------------------
# invalid input rejection
# -----------------------------------------------------------------------------


def test_boundary_status_invalid_next_phase_rejected(plan_context):
    """Invalid next-phase name returns invalid_phase error (no mutation)."""
    result = cmd_boundary_status(ns_boundary_status('bs-bad-next', next_phase='nope'))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'
    assert 'next_phase' in result['message']


def test_boundary_status_invalid_prev_phase_rejected(plan_context):
    """Invalid prev-phase name returns invalid_phase error (no mutation)."""
    result = cmd_boundary_status(
        ns_boundary_status('bs-bad-prev', prev_phase='nope', next_phase='2-refine')
    )
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'
    assert 'prev_phase' in result['message']


def test_boundary_status_plan_not_found_when_unseeded(plan_context):
    """Guard fires: an unseeded plan returns plan_not_found before classification."""
    plan_id = _register_unseeded('bs-unseeded')
    result = cmd_boundary_status(ns_boundary_status(plan_id, next_phase='2-refine'))
    assert result['status'] == 'error'
    assert result['error'] == 'plan_not_found'
