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
    ns_boundary_status,
    ns_generate,
    ns_phase_boundary,
    ns_start_phase,
)
from _manage_metrics_phase_boundary_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _field,
    _phase_block,
    _register_unseeded,
    cmd_boundary_status,
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
