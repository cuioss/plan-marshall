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

import importlib.util
import json
from argparse import Namespace

import pytest

from conftest import get_script_path

# The entrypoint filename is kebab-case (manage-metrics.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
_spec = importlib.util.spec_from_file_location(
    'manage_metrics', get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')
)
assert _spec is not None and _spec.loader is not None
manage_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manage_metrics)
cmd_phase_boundary = manage_metrics.cmd_phase_boundary
cmd_start_phase = manage_metrics.cmd_start_phase
cmd_end_phase = manage_metrics.cmd_end_phase
cmd_boundary_status = manage_metrics.cmd_boundary_status


# =============================================================================
# require_plan_exists guard fixtures
# =============================================================================
#
# TASK-1 added a require_plan_exists guard to every plan-scoped writer in
# manage-metrics.py (start-phase, end-phase, generate, phase-boundary,
# accumulate-agent-usage, enrich). The guard returns ``error: plan_not_found``
# unless the plan directory carries a ``status.json`` sentinel. The
# ``plan_context`` fixture creates plan dirs without that sentinel, so every
# positive test below would otherwise trip the guard.
#
# The autouse fixture below patches ``manage_metrics.require_plan_exists`` so
# that, during these tests, it auto-materialises the ``status.json`` sentinel for
# any plan whose dir exists but is not explicitly registered as "unseeded". This
# is the real guard chokepoint — it fires regardless of whether a test resolves
# its plan dir before or after calling the writer. Guard-negative tests register
# their plan_id via ``_register_unseeded`` so the patched guard lets the genuine
# ``plan_not_found`` branch run.

_UNSEEDED_PLAN_IDS: set[str] = set()


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


def _register_unseeded(plan_id: str) -> str:
    """Mark ``plan_id`` so the autouse guard-seeder leaves it un-sentinelled.

    Returns the plan_id for inline use. Negative guard tests call this so the
    patched ``require_plan_exists`` runs its genuine ``plan_not_found`` branch.
    """
    _UNSEEDED_PLAN_IDS.add(plan_id)
    return plan_id


def _ns_start_phase(plan_id, phase):
    return Namespace(plan_id=plan_id, phase=phase, command='start-phase', func=cmd_start_phase)


def _ns_boundary(
    plan_id,
    prev_phase,
    next_phase,
    total_tokens=None,
    duration_ms=None,
    tool_uses=None,
    retrospective_tokens=None,
):
    return Namespace(
        plan_id=plan_id,
        prev_phase=prev_phase,
        next_phase=next_phase,
        total_tokens=total_tokens,
        duration_ms=duration_ms,
        tool_uses=tool_uses,
        retrospective_tokens=retrospective_tokens,
        command='phase-boundary',
        func=cmd_phase_boundary,
    )


def _ns_end_phase(
    plan_id,
    phase,
    total_tokens=None,
    duration_ms=None,
    tool_uses=None,
    retrospective_tokens=None,
):
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        total_tokens=total_tokens,
        duration_ms=duration_ms,
        tool_uses=tool_uses,
        retrospective_tokens=retrospective_tokens,
        command='end-phase',
        func=cmd_end_phase,
    )


def _ns_boundary_status(plan_id, next_phase, prev_phase=None):
    return Namespace(
        plan_id=plan_id,
        prev_phase=prev_phase,
        next_phase=next_phase,
        command='boundary-status',
        func=cmd_boundary_status,
    )


def _phase_block(content: str, phase: str) -> str:
    """Return the metrics.toon text block for a single [phase] section."""
    start = content.index(f'[{phase}]')
    rest = content[start + len(f'[{phase}]'):]
    nxt = rest.find('\n[')
    return rest if nxt == -1 else rest[:nxt]


def _field(block: str, key: str) -> str | None:
    for line in block.splitlines():
        s = line.strip()
        if s.startswith(f'{key}:'):
            return s.split(':', 1)[1].strip()
    return None


# =============================================================================
# Successful boundary semantics
# =============================================================================


def test_phase_boundary_records_end_and_start_atomically(plan_context, monkeypatch):
    """phase-boundary writes end_time on prev and start_time on next in one call."""
    # Freeze the clock so cmd_start_phase and cmd_phase_boundary observe the
    # SAME instant. now_utc_iso() truncates to whole seconds, so without this the
    # two real reads can straddle a 1-second boundary (start=…:11, end=…:12),
    # making the wall span 1000 ms instead of ~0 and the clamp below assert 1000.
    # Capturing the real value once preserves its exact ISO format while making
    # the wall span deterministically zero.
    frozen_now = manage_metrics.now_utc_iso()
    monkeypatch.setattr(manage_metrics, 'now_utc_iso', lambda: frozen_now)

    cmd_start_phase(_ns_start_phase('boundary-basic', '1-init'))

    result = cmd_phase_boundary(
        _ns_boundary(
            'boundary-basic',
            prev_phase='1-init',
            next_phase='2-refine',
            total_tokens=12000,
            duration_ms=180000,
            tool_uses=8,
        )
    )

    assert result['status'] == 'success'
    assert result['prev_phase'] == '1-init'
    assert result['next_phase'] == '2-refine'
    assert 'end_time' in result
    assert 'start_time' in result
    assert result['prev_total_tokens'] == 12000

    metrics_file = plan_context.plan_dir_for('boundary-basic') / 'work' / 'metrics.toon'
    content = metrics_file.read_text()

    # Previous phase closed with token data
    assert '[1-init]' in content
    assert 'end_time:' in content
    assert 'total_tokens: 12000' in content
    assert 'tool_uses: 8' in content
    # start→boundary fire back-to-back, so the wall span is ~0 and the forwarded
    # worked window (180000 ms) is clamped to the wall span by _clamp_worked_to_wall.
    assert 'agent_duration_ms: 0' in content

    # Next phase opened
    assert '[2-refine]' in content
    # Both blocks present, with start_time on the next phase
    next_idx = content.index('[2-refine]')
    # Make sure the next-phase block has a start_time line
    assert 'start_time:' in content[next_idx:]


def test_phase_boundary_generates_metrics_md(plan_context):
    """phase-boundary regenerates metrics.md as a side effect."""
    cmd_start_phase(_ns_start_phase('boundary-generate', '1-init'))
    result = cmd_phase_boundary(
        _ns_boundary(
            'boundary-generate',
            prev_phase='1-init',
            next_phase='2-refine',
            total_tokens=5000,
        )
    )
    assert result['status'] == 'success'
    assert result.get('metrics_file') == 'metrics.md'
    # The generated report must exist
    metrics_md = plan_context.plan_dir_for('boundary-generate') / 'metrics.md'
    assert metrics_md.exists()
    report = metrics_md.read_text()
    assert '1-init' in report
    # phases_recorded is at least 2 (prev + next)
    assert int(result.get('phases_recorded', 0)) >= 2


def test_phase_boundary_optional_token_args_omitted(plan_context):
    """phase-boundary works with no token/duration/tool-uses flags (main-context phase)."""
    cmd_start_phase(_ns_start_phase('boundary-no-tokens', '2-refine'))
    result = cmd_phase_boundary(_ns_boundary('boundary-no-tokens', prev_phase='2-refine', next_phase='3-outline'))
    assert result['status'] == 'success'
    # No prev_total_tokens since not provided
    assert 'prev_total_tokens' not in result

    content = (plan_context.plan_dir_for('boundary-no-tokens') / 'work' / 'metrics.toon').read_text()
    # No token fields should have been written for the closing phase
    prev_idx = content.index('[2-refine]')
    next_idx = content.index('[3-outline]') if '[3-outline]' in content else len(content)
    prev_block = content[prev_idx:next_idx]
    assert 'total_tokens' not in prev_block
    assert 'tool_uses' not in prev_block
    # But end_time MUST be present
    assert 'end_time:' in prev_block


def test_phase_boundary_without_prev_start_records_end_only(plan_context):
    """phase-boundary tolerates a previous phase with no recorded start (no duration)."""
    # No start-phase called for 1-init
    result = cmd_phase_boundary(_ns_boundary('boundary-no-start', prev_phase='1-init', next_phase='2-refine'))
    assert result['status'] == 'success'
    # No prev_duration_seconds in the result since start_time was missing
    assert 'prev_duration_seconds' not in result


# =============================================================================
# Invalid input rejection
# =============================================================================


def test_phase_boundary_invalid_prev_phase_rejected(plan_context):
    """Invalid prev-phase name returns invalid_phase error."""
    result = cmd_phase_boundary(_ns_boundary('boundary-bad-prev', prev_phase='nope', next_phase='2-refine'))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'
    assert 'prev_phase' in result['message']


def test_phase_boundary_invalid_next_phase_rejected(plan_context):
    """Invalid next-phase name returns invalid_phase error."""
    result = cmd_phase_boundary(_ns_boundary('boundary-bad-next', prev_phase='1-init', next_phase='nope'))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'
    assert 'next_phase' in result['message']


def test_phase_boundary_equivalent_to_three_call_sequence(plan_context, monkeypatch):
    """The fused call persists the same key fields the three-call sequence would.

    We don't assert byte-equivalence (timestamps differ between calls), but the
    set of recorded keys per phase MUST match: prev gets end_time + token data;
    next gets start_time. Both must be present after the fused call.
    """
    # Freeze the clock so cmd_start_phase and cmd_phase_boundary observe the same
    # instant — otherwise the two whole-second reads can straddle a 1-second
    # boundary, making the wall span 1000 ms and the clamp assert 1000 instead of
    # 0 (same flake as test_phase_boundary_records_end_and_start_atomically).
    frozen_now = manage_metrics.now_utc_iso()
    monkeypatch.setattr(manage_metrics, 'now_utc_iso', lambda: frozen_now)

    cmd_start_phase(_ns_start_phase('boundary-equiv', '4-plan'))
    result = cmd_phase_boundary(
        _ns_boundary(
            'boundary-equiv',
            prev_phase='4-plan',
            next_phase='5-execute',
            total_tokens=42000,
            duration_ms=600000,
            tool_uses=15,
        )
    )
    assert result['status'] == 'success'
    content = (plan_context.plan_dir_for('boundary-equiv') / 'work' / 'metrics.toon').read_text()

    # Same fields end-phase would have written
    assert 'total_tokens: 42000' in content
    assert 'tool_uses: 15' in content
    # start→boundary fire back-to-back, so the wall span is ~0 and the forwarded
    # worked window (600000 ms) is clamped to the wall span by _clamp_worked_to_wall.
    assert 'agent_duration_ms: 0' in content
    # Same field start-phase would have written for next
    assert '[5-execute]' in content


# =============================================================================
# 1-init start_time backfill (D4)
# =============================================================================


def _seed_status_created(plan_dir, created_ts: str) -> None:
    """Write a minimal status.json with the given `created` timestamp."""
    status_path = plan_dir / 'status.json'
    status_path.write_text(
        json.dumps({'plan_id': plan_dir.name, 'created': created_ts}),
        encoding='utf-8',
    )


def test_phase_boundary_backfills_1init_start_time_from_status_created(plan_context):
    """1-init lacks start_time → cmd_phase_boundary backfills from status.json.created."""
    # status.json with a known `created` timestamp, well before end_now.
    created_ts = '2026-03-27T09:00:00+00:00'
    plan_dir = plan_context.plan_dir_for('boundary-backfill-01')
    _seed_status_created(plan_dir, created_ts)

    # No cmd_start_phase call → metrics.toon has no 1-init.start_time.
    result = cmd_phase_boundary(
        _ns_boundary('boundary-backfill-01', prev_phase='1-init', next_phase='2-refine')
    )
    assert result['status'] == 'success'

    content = (plan_dir / 'work' / 'metrics.toon').read_text()
    # Backfilled start_time matches status.json.created.
    assert f'start_time: {created_ts}' in content
    # Duration computation kicked in (real wall-clock between created_ts and end_time).
    assert 'duration_seconds:' in content
    # Surfaced via prev_duration_seconds on the result (positive number).
    assert 'prev_duration_seconds' in result
    assert result['prev_duration_seconds'] > 0


def test_phase_boundary_preserves_existing_1init_start_time(plan_context):
    """1-init.start_time already present → cmd_phase_boundary does NOT overwrite it."""
    cmd_start_phase(_ns_start_phase('boundary-backfill-02', '1-init'))
    # Override status.json.created with a value that would differ if backfill ran.
    plan_dir = plan_context.plan_dir_for('boundary-backfill-02')
    _seed_status_created(plan_dir, '1999-01-01T00:00:00+00:00')

    # Capture the start_time written by cmd_start_phase.
    content_pre = (plan_dir / 'work' / 'metrics.toon').read_text()
    # Extract start_time from the 1-init block.
    init_idx = content_pre.index('[1-init]')
    block = content_pre[init_idx:]
    start_line = next(line for line in block.splitlines() if line.strip().startswith('start_time:'))
    original_start = start_line.split('start_time:', 1)[1].strip()
    assert original_start != '1999-01-01T00:00:00+00:00'

    cmd_phase_boundary(_ns_boundary('boundary-backfill-02', prev_phase='1-init', next_phase='2-refine'))

    content_post = (plan_dir / 'work' / 'metrics.toon').read_text()
    # status.json.created stays UNUSED — the original start_time wins.
    assert '1999-01-01T00:00:00+00:00' not in content_post
    assert f'start_time: {original_start}' in content_post


def test_phase_boundary_no_backfill_for_non_1init_prev_phase(plan_context):
    """prev_phase != '1-init' → no status.json read, no backfill, regression guard preserved."""
    # status.json present and would be readable, but the phase is not 1-init.
    plan_dir = plan_context.plan_dir_for('boundary-backfill-03')
    _seed_status_created(plan_dir, '2026-03-27T09:00:00+00:00')

    # Transition 2-refine → 3-outline without a prior start-phase.
    cmd_phase_boundary(_ns_boundary('boundary-backfill-03', prev_phase='2-refine', next_phase='3-outline'))

    content = (plan_dir / 'work' / 'metrics.toon').read_text()
    # The status.json.created timestamp must not have leaked into the 2-refine row.
    refine_idx = content.index('[2-refine]')
    next_idx = content.index('[3-outline]') if '[3-outline]' in content else len(content)
    prev_block = content[refine_idx:next_idx]
    assert 'start_time' not in prev_block


def test_phase_boundary_status_json_missing_no_exception(plan_context):
    """status.json missing → call succeeds, 1-init.start_time remains absent, no exception raised."""
    # Do NOT seed status.json. No prior cmd_start_phase either.
    result = cmd_phase_boundary(
        _ns_boundary('boundary-backfill-04', prev_phase='1-init', next_phase='2-refine')
    )
    assert result['status'] == 'success'
    # Backfill skipped silently → no start_time, no duration_seconds.
    content = (plan_context.plan_dir_for('boundary-backfill-04') / 'work' / 'metrics.toon').read_text()
    init_idx = content.index('[1-init]')
    refine_idx = content.index('[2-refine]') if '[2-refine]' in content else len(content)
    prev_block = content[init_idx:refine_idx]
    assert 'start_time' not in prev_block
    assert 'duration_seconds' not in prev_block


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
    start_res = cmd_start_phase(_ns_start_phase('boundary-real-seed', '1-init'))
    seeded_start = start_res['start_time']

    # Step 2: status.json present with a far-past `created` that would
    # produce a years-long duration if the backfill path were taken.
    old_created_ts = '1999-01-01T00:00:00+00:00'
    plan_dir = plan_context.plan_dir_for('boundary-real-seed')
    _seed_status_created(plan_dir, old_created_ts)

    # Step 3: fused phase-boundary call.
    result = cmd_phase_boundary(
        _ns_boundary('boundary-real-seed', prev_phase='1-init', next_phase='2-refine')
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
        _ns_boundary('boundary-backfill-05', prev_phase='1-init', next_phase='2-refine')
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
    created→end wall span is clamped so worked <= wall (the worked>wall row from
    lesson 2026-05-29-17-001 can no longer be persisted)."""
    # status.json.created at "now" makes the backfilled wall span near-zero;
    # the forwarded worked window is deliberately huge.
    created_ts = manage_metrics.now_utc_iso()
    plan_dir = plan_context.plan_dir_for('clamp-1init')
    _seed_status_created(plan_dir, created_ts)

    # No prior start-phase; backfill from status.json.created.
    result = cmd_phase_boundary(
        _ns_boundary(
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
    cmd_start_phase(_ns_start_phase('clamp-end', '3-outline'))

    result = cmd_end_phase(
        _ns_end_phase('clamp-end', phase='3-outline', duration_ms=888_888_888)
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
        _ns_boundary(
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
    cmd_start_phase(_ns_start_phase('retro-attr', '6-finalize'))

    result = cmd_end_phase(
        _ns_end_phase(
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
    cmd_start_phase(_ns_start_phase('retro-absent', '6-finalize'))

    # total_tokens only, no retrospective attribution.
    result = cmd_end_phase(
        _ns_end_phase('retro-absent', phase='6-finalize', total_tokens=10000)
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
    cmd_start_phase(_ns_start_phase('bs-missing-next', '1-init'))
    cmd_phase_boundary(_ns_boundary('bs-missing-next', prev_phase='1-init', next_phase='2-refine'))

    # On resume, the orchestrator is about to enter 3-outline, which has no start.
    result = cmd_boundary_status(_ns_boundary_status('bs-missing-next', next_phase='3-outline'))

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
    cmd_start_phase(_ns_start_phase('bs-missing-prev', '1-init'))
    cmd_start_phase(_ns_start_phase('bs-missing-prev', '2-refine'))

    result = cmd_boundary_status(
        _ns_boundary_status('bs-missing-prev', prev_phase='1-init', next_phase='2-refine')
    )

    assert result['status'] == 'success'
    assert result['classification'] == 'missing'
    assert result['prev_phase'] == '1-init'
    assert result['next_phase'] == '2-refine'
    assert result['missing_fields'] == '1-init.end_time'


def test_boundary_status_missing_reports_both_offending_fields(plan_context):
    """prev unclosed AND next unopened → both fields listed in missing_fields."""
    # 1-init opened, never closed; 2-refine never opened.
    cmd_start_phase(_ns_start_phase('bs-missing-both', '1-init'))

    result = cmd_boundary_status(
        _ns_boundary_status('bs-missing-both', prev_phase='1-init', next_phase='2-refine')
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
    cmd_start_phase(_ns_start_phase('bs-stamped', '1-init'))
    cmd_phase_boundary(_ns_boundary('bs-stamped', prev_phase='1-init', next_phase='2-refine'))

    result = cmd_boundary_status(
        _ns_boundary_status('bs-stamped', prev_phase='1-init', next_phase='2-refine')
    )

    assert result['status'] == 'success'
    assert result['classification'] == 'stamped'
    assert result['prev_phase'] == '1-init'
    assert result['next_phase'] == '2-refine'
    # No missing_fields on a stamped verdict.
    assert 'missing_fields' not in result


def test_boundary_status_stamped_when_prev_omitted_and_next_has_start(plan_context):
    """--prev-phase omitted + next has start_time → classification 'stamped'."""
    cmd_start_phase(_ns_start_phase('bs-stamped-noprev', '3-outline'))

    result = cmd_boundary_status(_ns_boundary_status('bs-stamped-noprev', next_phase='3-outline'))

    assert result['status'] == 'success'
    assert result['classification'] == 'stamped'
    assert result['prev_phase'] == '-'
    assert result['next_phase'] == '3-outline'


def test_boundary_status_leaves_metrics_unchanged(plan_context):
    """boundary-status performs ZERO mutation of metrics.toon (read-only)."""
    cmd_start_phase(_ns_start_phase('bs-readonly', '1-init'))
    cmd_phase_boundary(_ns_boundary('bs-readonly', prev_phase='1-init', next_phase='2-refine'))

    metrics_file = plan_context.plan_dir_for('bs-readonly') / 'work' / 'metrics.toon'
    before = metrics_file.read_text()

    # Run the detector across several boundary shapes — none may mutate the file.
    cmd_boundary_status(_ns_boundary_status('bs-readonly', prev_phase='1-init', next_phase='2-refine'))
    cmd_boundary_status(_ns_boundary_status('bs-readonly', next_phase='3-outline'))
    cmd_boundary_status(_ns_boundary_status('bs-readonly', prev_phase='2-refine', next_phase='3-outline'))

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
    cmd_start_phase(_ns_start_phase('bs-na', '2-refine'))

    result = cmd_boundary_status(
        _ns_boundary_status('bs-na', prev_phase='1-init', next_phase='2-refine')
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
    result = cmd_boundary_status(_ns_boundary_status('bs-noprev-na', next_phase='3-outline'))

    assert result['status'] == 'success'
    assert result['classification'] == 'missing'
    assert result['missing_fields'] == '3-outline.start_time'


# -----------------------------------------------------------------------------
# invalid input rejection
# -----------------------------------------------------------------------------


def test_boundary_status_invalid_next_phase_rejected(plan_context):
    """Invalid next-phase name returns invalid_phase error (no mutation)."""
    result = cmd_boundary_status(_ns_boundary_status('bs-bad-next', next_phase='nope'))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'
    assert 'next_phase' in result['message']


def test_boundary_status_invalid_prev_phase_rejected(plan_context):
    """Invalid prev-phase name returns invalid_phase error (no mutation)."""
    result = cmd_boundary_status(
        _ns_boundary_status('bs-bad-prev', prev_phase='nope', next_phase='2-refine')
    )
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'
    assert 'prev_phase' in result['message']


def test_boundary_status_plan_not_found_when_unseeded(plan_context):
    """Guard fires: an unseeded plan returns plan_not_found before classification."""
    plan_id = _register_unseeded('bs-unseeded')
    result = cmd_boundary_status(_ns_boundary_status(plan_id, next_phase='2-refine'))
    assert result['status'] == 'error'
    assert result['error'] == 'plan_not_found'
