#!/usr/bin/env python3
"""Tests for the `record-dispatch-boundary` subcommand of manage_metrics.

Lesson 2026-05-08-14-001: phase-5-execute lost log coverage on agent-initiated
re-dispatch. Part of the cure is a per-dispatch audit trail captured by this
new subcommand. These six tests pin the contract:

  (a) first invocation creates the artifact file with one row,
  (b) subsequent invocations append rows in order with monotonic timestamps,
  (c) all five --termination-cause values are accepted,
  (d) any other value rejected with non-zero exit before any file write,
  (e) missing required flags cause non-zero exit before any file write,
  (f) the artifact's TOON layout is parseable by the parse_toon helper.
"""

from __future__ import annotations

import time
from argparse import Namespace
from pathlib import Path

import pytest
from manage_metrics import (  # type: ignore[import-not-found]
    DISPATCH_TERMINATION_CAUSES,
    cmd_record_dispatch_boundary,
)
from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import PlanContext, get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage_metrics.py')


def _ns(
    plan_id: str,
    phase: str = '5-execute',
    termination_cause: str = 'voluntary_checkpoint',
    total_tokens: int | None = None,
    tool_uses: int | None = None,
    duration_ms: int | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        termination_cause=termination_cause,
        total_tokens=total_tokens,
        tool_uses=tool_uses,
        duration_ms=duration_ms,
        command='record-dispatch-boundary',
        func=cmd_record_dispatch_boundary,
    )


def _boundary_path(plan_dir: Path, phase: str = '5-execute') -> Path:
    return plan_dir / 'work' / f'metrics-dispatch-boundaries-{phase}.toon'


def _seed_status_json(plan_dir: Path) -> None:
    """Seed status.json so cmd_record_dispatch_boundary's require_plan_exists guard accepts the plan.

    The `PlanContext` helper creates the plan directory but does NOT write
    status.json — the per-plan sentinel that `require_plan_exists` checks for
    (lesson 2026-05-15-X: script-side guard against orphan-plan-dir creation).
    Tests that exercise the happy path of `cmd_record_dispatch_boundary` must
    call this helper after entering the context.
    """
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')


def _data_rows(content: str) -> list[str]:
    """Return only the data rows (skipping the TOON header lines)."""
    rows = []
    for line in content.splitlines():
        if not line:
            continue
        if line.startswith(('plan_id:', 'phase:', 'rows[]')):
            continue
        rows.append(line)
    return rows


# =============================================================================
# (a) First invocation creates the artifact file with one row
# =============================================================================


def test_first_invocation_creates_file_with_one_row():
    """The first record-dispatch-boundary call writes the header and exactly one data row."""
    with PlanContext(plan_id='disp-first') as ctx:
        _seed_status_json(ctx.plan_dir)
        result = cmd_record_dispatch_boundary(
            _ns(
                'disp-first',
                phase='5-execute',
                termination_cause='voluntary_checkpoint',
                total_tokens=12345,
                tool_uses=10,
                duration_ms=60000,
            )
        )

        assert result['status'] == 'success'
        assert result['phase'] == '5-execute'
        assert result['termination_cause'] == 'voluntary_checkpoint'
        assert result['total_tokens'] == 12345
        assert result['tool_uses'] == 10
        assert result['duration_ms'] == 60000
        assert result['rows_recorded'] == 1
        assert result['dispatch_boundary_file'] == 'work/metrics-dispatch-boundaries-5-execute.toon'

        path = _boundary_path(ctx.plan_dir, '5-execute')
        assert path.exists()
        content = path.read_text(encoding='utf-8')

        # Header lines present
        assert 'plan_id: disp-first' in content
        assert 'phase: 5-execute' in content
        assert 'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:' in content

        # Exactly one data row
        rows = _data_rows(content)
        assert len(rows) == 1
        assert ',voluntary_checkpoint,12345,10,60000' in rows[0]


# =============================================================================
# (b) Subsequent invocations append rows in order with monotonic timestamps
# =============================================================================


def test_subsequent_invocations_append_rows_in_order_with_monotonic_timestamps():
    """Successive invocations append rows in chronological order, header preserved."""
    with PlanContext(plan_id='disp-append') as ctx:
        _seed_status_json(ctx.plan_dir)
        cmd_record_dispatch_boundary(
            _ns('disp-append', termination_cause='voluntary_checkpoint', total_tokens=100)
        )
        # Force a measurable timestamp delta so monotonicity is observable even on
        # platforms where the iso-second granularity is coarse.
        time.sleep(1.05)
        cmd_record_dispatch_boundary(
            _ns('disp-append', termination_cause='task_complete_returned_verbatim', total_tokens=200)
        )
        time.sleep(1.05)
        result = cmd_record_dispatch_boundary(
            _ns('disp-append', termination_cause='harness_cancellation', total_tokens=300)
        )

        assert result['rows_recorded'] == 3

        path = _boundary_path(ctx.plan_dir)
        content = path.read_text(encoding='utf-8')
        rows = _data_rows(content)
        assert len(rows) == 3

        # Order preserved by termination_cause column
        assert ',voluntary_checkpoint,100,' in rows[0]
        assert ',task_complete_returned_verbatim,200,' in rows[1]
        assert ',harness_cancellation,300,' in rows[2]

        # Timestamps strictly non-decreasing across appended rows
        timestamps = [row.split(',', 1)[0] for row in rows]
        assert timestamps == sorted(timestamps), (
            f'Timestamps not monotonic across appended rows: {timestamps}'
        )


# =============================================================================
# (c) All five --termination-cause values are accepted
# =============================================================================


@pytest.mark.parametrize('cause', list(DISPATCH_TERMINATION_CAUSES))
def test_all_five_termination_causes_accepted(cause):
    """Each member of the documented termination-cause enum is accepted as-is."""
    # plan_id slugs use kebab-case; map underscores → hyphens for the slug.
    plan_id = f'disp-cause-{cause.replace("_", "-")}'
    with PlanContext(plan_id=plan_id) as ctx:
        _seed_status_json(ctx.plan_dir)
        result = cmd_record_dispatch_boundary(
            _ns(
                plan_id,
                phase='5-execute',
                termination_cause=cause,
                total_tokens=1,
                tool_uses=1,
                duration_ms=1,
            )
        )
        assert result['status'] == 'success'
        assert result['termination_cause'] == cause

        path = _boundary_path(ctx.plan_dir, '5-execute')
        content = path.read_text(encoding='utf-8')
        # Only one data row, and it carries the requested cause verbatim.
        rows = _data_rows(content)
        assert len(rows) == 1
        assert f',{cause},1,1,1' in rows[0]


# =============================================================================
# (d) Any other --termination-cause value is rejected with non-zero exit
# =============================================================================


def test_invalid_termination_cause_rejected_subprocess_no_file_written():
    """An out-of-enum termination_cause value rejects the run before any file write."""
    with PlanContext(plan_id='disp-bad-cause') as ctx:
        result = run_script(
            SCRIPT_PATH,
            'record-dispatch-boundary',
            '--plan-id',
            'disp-bad-cause',
            '--phase',
            '5-execute',
            '--termination-cause',
            'definitely-not-a-real-cause',
        )
        assert result.returncode != 0, 'argparse rejection MUST yield non-zero exit'
        # No artifact created.
        assert not _boundary_path(ctx.plan_dir, '5-execute').exists()


# =============================================================================
# (e) Missing required flags cause non-zero exit before any file write
# =============================================================================


def test_missing_required_flag_rejected_subprocess_no_file_written():
    """Omitting --termination-cause rejects the run before any file write."""
    with PlanContext(plan_id='disp-missing-cause') as ctx:
        result = run_script(
            SCRIPT_PATH,
            'record-dispatch-boundary',
            '--plan-id',
            'disp-missing-cause',
            '--phase',
            '5-execute',
        )
        assert result.returncode != 0, 'argparse rejection MUST yield non-zero exit'
        assert not _boundary_path(ctx.plan_dir, '5-execute').exists()


# =============================================================================
# (f) The artifact's TOON layout is parseable by the parse_toon helper
# =============================================================================


def test_toon_layout_parseable_by_parse_toon():
    """The header section parses cleanly via the canonical parse_toon helper."""
    with PlanContext(plan_id='disp-parse') as ctx:
        _seed_status_json(ctx.plan_dir)
        cmd_record_dispatch_boundary(
            _ns(
                'disp-parse',
                phase='5-execute',
                termination_cause='voluntary_checkpoint',
                total_tokens=42,
                tool_uses=2,
                duration_ms=4242,
            )
        )

        path = _boundary_path(ctx.plan_dir)
        content = path.read_text(encoding='utf-8')
        parsed = parse_toon(content)

        # Header keys parse to their expected scalar values.
        assert parsed['plan_id'] == 'disp-parse'
        assert parsed['phase'] == '5-execute'
        # parse_toon should have ingested the rows[] header without error.
        # The exact representation of tabular bodies is parser-dependent, so
        # we assert the document-level keys plus the presence of the data row
        # in the raw content (already covered above by _data_rows).
        rows = _data_rows(content)
        assert len(rows) == 1
        assert ',voluntary_checkpoint,42,2,4242' in rows[0]


# =============================================================================
# (g) DISPATCH_TERMINATION_CAUSES schema migration — clean_exit_queue_empty
#     replaces the legacy `unknown` fallback. The recorder now accepts
#     `clean_exit_queue_empty` and rejects the literal `unknown`.
# =============================================================================


def test_clean_exit_queue_empty_accepted_as_canonical_clean_exit_value():
    """`clean_exit_queue_empty` is the canonical clean-exit value post-migration."""
    plan_id = 'disp-clean-exit'
    with PlanContext(plan_id=plan_id) as ctx:
        _seed_status_json(ctx.plan_dir)
        result = cmd_record_dispatch_boundary(
            _ns(
                plan_id,
                phase='5-execute',
                termination_cause='clean_exit_queue_empty',
                total_tokens=10,
                tool_uses=5,
                duration_ms=1234,
            )
        )
        assert result['status'] == 'success'
        assert result['termination_cause'] == 'clean_exit_queue_empty'

        path = _boundary_path(ctx.plan_dir, '5-execute')
        content = path.read_text(encoding='utf-8')
        rows = _data_rows(content)
        assert len(rows) == 1
        assert ',clean_exit_queue_empty,10,5,1234' in rows[0]


def test_legacy_unknown_termination_cause_rejected_no_file_written():
    """The legacy `unknown` value is rejected by argparse (no implicit fallback)."""
    with PlanContext(plan_id='disp-legacy-unknown') as ctx:
        result = run_script(
            SCRIPT_PATH,
            'record-dispatch-boundary',
            '--plan-id',
            'disp-legacy-unknown',
            '--phase',
            '5-execute',
            '--termination-cause',
            'unknown',
        )
        assert result.returncode != 0, 'argparse MUST reject the legacy `unknown` value'
        assert not _boundary_path(ctx.plan_dir, '5-execute').exists()


def test_dispatch_termination_causes_does_not_contain_unknown():
    """The live tuple no longer contains the legacy `unknown` fallback value."""
    assert 'unknown' not in DISPATCH_TERMINATION_CAUSES
    assert 'clean_exit_queue_empty' in DISPATCH_TERMINATION_CAUSES


# =============================================================================
# (h) Script-side require_plan_exists guard
#
# cmd_record_dispatch_boundary MUST refuse to write a dispatch-boundary row
# under a plan directory that does not exist (or exists but lacks
# status.json). The guard returns the canonical TOON envelope and MUST NOT
# mkdir the plan tree as a side-effect.
# =============================================================================


def test_record_dispatch_boundary_rejects_unknown_plan_id_no_mkdir(tmp_path, monkeypatch):
    """Unknown plan_id: returns plan_not_found error, no plan dir created."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plans_dir = tmp_path / 'plans'
    # Pre-condition: plans/ tree absent.
    assert not plans_dir.exists()

    result = cmd_record_dispatch_boundary(
        _ns(
            'never-initialized',
            phase='5-execute',
            termination_cause='voluntary_checkpoint',
            total_tokens=1,
            tool_uses=1,
            duration_ms=1,
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'plan_not_found'
    assert result['plan_id'] == 'never-initialized'
    assert 'never-initialized' in result['plan_dir']
    # Side-effect invariant: the guard MUST NOT have mkdir'd the plan tree.
    assert not plans_dir.exists()


def test_record_dispatch_boundary_rejects_plan_dir_missing_status_json_no_mkdir(
    tmp_path, monkeypatch
):
    """Plan dir exists but no status.json: returns plan_not_found error."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    half_dir = tmp_path / 'plans' / 'half-initialized'
    half_dir.mkdir(parents=True)
    assert not (half_dir / 'status.json').exists()

    result = cmd_record_dispatch_boundary(
        _ns(
            'half-initialized',
            phase='5-execute',
            termination_cause='voluntary_checkpoint',
            total_tokens=1,
            tool_uses=1,
            duration_ms=1,
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'plan_not_found'
    assert result['plan_id'] == 'half-initialized'
    # The pre-existing directory remains, status.json is NOT auto-created,
    # and the work/ subtree (where the boundaries file would live) was NOT
    # materialised by the guard rejection.
    assert half_dir.is_dir()
    assert not (half_dir / 'status.json').exists()
    assert not (half_dir / 'work').exists()


def test_record_dispatch_boundary_with_initialized_plan_id_continues_to_work():
    """Happy path: initialized plan_id (status.json present) → success.

    Pins that the require_plan_exists guard does not regress the existing
    cmd_record_dispatch_boundary contract for in-progress plans.
    """
    with PlanContext(plan_id='disp-happy') as ctx:
        _seed_status_json(ctx.plan_dir)
        result = cmd_record_dispatch_boundary(
            _ns(
                'disp-happy',
                phase='5-execute',
                termination_cause='voluntary_checkpoint',
                total_tokens=99,
                tool_uses=3,
                duration_ms=500,
            )
        )

        assert result['status'] == 'success'
        assert result['plan_id'] == 'disp-happy'
        assert result['rows_recorded'] == 1
        # The boundaries file was written to the expected path.
        path = _boundary_path(ctx.plan_dir, '5-execute')
        assert path.exists()
