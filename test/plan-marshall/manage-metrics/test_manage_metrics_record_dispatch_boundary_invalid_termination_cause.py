#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `record-dispatch-boundary` subcommand of manage_metrics.

phase-5-execute loses log coverage on agent-initiated re-dispatch without a
per-dispatch audit trail. That trail is captured by this subcommand.

A leading block pins the boundary MEASURE: the reader returns its row count
beside its token sum, because a sum cannot state its own coverage. The lettered
sections below pin the subcommand's own contract:

  (a) first invocation creates the artifact file with one row,
  (b) subsequent invocations append rows in order with monotonic timestamps,
  (c) every documented --termination-cause value is accepted (parametrized over
      the live DISPATCH_TERMINATION_CAUSES tuple, including budget_yield),
  (d) any other value rejected with non-zero exit before any file write,
  (e) missing required flags cause non-zero exit before any file write,
  (f) the artifact's TOON layout is parseable by the parse_toon helper.
"""


from __future__ import annotations

from _manage_metrics_record_dispatch_boundary_fixtures import (
    DISPATCH_TERMINATION_CAUSES,
    SCRIPT_PATH,
    _boundary_path,
    _data_rows,
    _ns,
    _seed_status_json,
    cmd_record_dispatch_boundary,
)
from toon_parser import parse_toon

from conftest import run_script

# =============================================================================
# (d) Any other --termination-cause value is rejected with non-zero exit
# =============================================================================


def test_invalid_termination_cause_rejected_subprocess_no_file_written(plan_context):
    """An out-of-enum termination_cause value rejects the run before any file write."""
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
    assert not _boundary_path(plan_context.plan_dir_for('disp-bad-cause'), '5-execute').exists()


# =============================================================================
# (e) Missing required flags cause non-zero exit before any file write
# =============================================================================


def test_missing_required_flag_rejected_subprocess_no_file_written(plan_context):
    """Omitting --termination-cause rejects the run before any file write."""
    result = run_script(
        SCRIPT_PATH,
        'record-dispatch-boundary',
        '--plan-id',
        'disp-missing-cause',
        '--phase',
        '5-execute',
    )
    assert result.returncode != 0, 'argparse rejection MUST yield non-zero exit'
    assert not _boundary_path(plan_context.plan_dir_for('disp-missing-cause'), '5-execute').exists()


# =============================================================================
# (f) The artifact's TOON layout is parseable by the parse_toon helper
# =============================================================================


def test_toon_layout_parseable_by_parse_toon(plan_context):
    """The header section parses cleanly via the canonical parse_toon helper."""
    plan_dir = plan_context.plan_dir_for('disp-parse')
    _seed_status_json(plan_dir)
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

    path = _boundary_path(plan_dir)
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


def test_clean_exit_queue_empty_accepted_as_canonical_clean_exit_value(plan_context):
    """`clean_exit_queue_empty` is the canonical clean-exit value post-migration."""
    plan_id = 'disp-clean-exit'
    plan_dir = plan_context.plan_dir_for(plan_id)
    _seed_status_json(plan_dir)
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

    path = _boundary_path(plan_dir, '5-execute')
    content = path.read_text(encoding='utf-8')
    rows = _data_rows(content)
    assert len(rows) == 1
    assert ',clean_exit_queue_empty,10,5,1234' in rows[0]


def test_legacy_unknown_termination_cause_rejected_no_file_written(plan_context):
    """The legacy `unknown` value is rejected by argparse (no implicit fallback)."""
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
    assert not _boundary_path(plan_context.plan_dir_for('disp-legacy-unknown'), '5-execute').exists()


def test_dispatch_termination_causes_does_not_contain_unknown():
    """The live tuple no longer contains the legacy `unknown` fallback value."""
    assert 'unknown' not in DISPATCH_TERMINATION_CAUSES
    assert 'clean_exit_queue_empty' in DISPATCH_TERMINATION_CAUSES


# =============================================================================
# (i) budget_yield — the phase-5 budget-bounded dispatch loop's yield signal
#
#     The phase-5-execute envelope yields to the orchestrator at a TASK
#     boundary when the per-task budget reserve is exhausted; the orchestrator
#     records that yield with termination_cause=budget_yield. This block pins
#     both the enum membership and the recorder's acceptance of the value.
# =============================================================================


def test_dispatch_termination_causes_contains_budget_yield():
    """The live tuple includes the budget_yield phase-5 dispatch-loop signal."""
    assert 'budget_yield' in DISPATCH_TERMINATION_CAUSES


def test_budget_yield_cause_accepted_and_recorded(plan_context):
    """budget_yield records a single data row carrying the cause verbatim."""
    plan_id = 'disp-budget-yield'
    plan_dir = plan_context.plan_dir_for(plan_id)
    _seed_status_json(plan_dir)
    result = cmd_record_dispatch_boundary(
        _ns(
            plan_id,
            phase='5-execute',
            termination_cause='budget_yield',
            total_tokens=119000,
            tool_uses=42,
            duration_ms=300000,
        )
    )
    assert result['status'] == 'success'
    assert result['termination_cause'] == 'budget_yield'

    path = _boundary_path(plan_dir, '5-execute')
    content = path.read_text(encoding='utf-8')
    rows = _data_rows(content)
    assert len(rows) == 1
    assert ',budget_yield,119000,42,300000' in rows[0]


def test_budget_yield_subprocess_accepted_by_argparse(plan_context):
    """End-to-end: argparse accepts budget_yield (it is a member of the choices)."""
    plan_dir = plan_context.plan_dir_for('disp-budget-yield-sub')
    _seed_status_json(plan_dir)
    result = run_script(
        SCRIPT_PATH,
        'record-dispatch-boundary',
        '--plan-id',
        'disp-budget-yield-sub',
        '--phase',
        '5-execute',
        '--termination-cause',
        'budget_yield',
    )
    assert result.returncode == 0, (
        f'budget_yield MUST be accepted by argparse: {result.stderr}'
    )
    assert _boundary_path(plan_dir, '5-execute').exists()


# =============================================================================
# (j) returned_with_findings — the productive-loop-back dispatch-ledger member
#
#     The finalize dispatcher stamps a review-shaped dispatch that returned
#     findings and signalled a loop-back (its mark-step-done recorded
#     outcome: loop_back) as returned_with_findings — NEVER error. Before this
#     member existed, such a return fell through to `error`, conflating the most
#     productive dispatches with fatal failures. This block pins both the enum
#     membership and the recorder's acceptance of the value on the finalize
#     boundary file (its actual routing target).
# =============================================================================


def test_dispatch_termination_causes_contains_returned_with_findings():
    """The live tuple includes the productive-loop-back member.

    RED before the member was added — the taxonomy modelled how a dispatch
    stopped but not the verdict a review-shaped dispatch returns, so a
    findings-bearing loop-back had no member of its own.
    """
    assert 'returned_with_findings' in DISPATCH_TERMINATION_CAUSES


def test_returned_with_findings_recorded_on_the_finalize_boundary(plan_context):
    """A loop-back dispatch is stamped returned_with_findings in the finalize file.

    This is the D1 done-when for the stamping half: a finalize dispatch that
    returned findings lands one boundary row carrying the new member verbatim in
    `work/metrics-dispatch-boundaries-6-finalize.toon`. RED before the member
    existed (argparse `choices` rejected it and the writer errored).
    """
    plan_id = 'disp-returned-with-findings'
    plan_dir = plan_context.plan_dir_for(plan_id)
    _seed_status_json(plan_dir)
    result = cmd_record_dispatch_boundary(
        _ns(
            plan_id,
            phase='6-finalize',
            termination_cause='returned_with_findings',
            total_tokens=73000,
            tool_uses=21,
            duration_ms=210000,
        )
    )
    assert result['status'] == 'success'
    assert result['termination_cause'] == 'returned_with_findings'

    path = _boundary_path(plan_dir, '6-finalize')
    content = path.read_text(encoding='utf-8')
    rows = _data_rows(content)
    assert len(rows) == 1
    assert ',returned_with_findings,73000,21,210000' in rows[0]


def test_returned_with_findings_subprocess_accepted_by_argparse(plan_context):
    """End-to-end: argparse accepts returned_with_findings (a member of choices)."""
    plan_dir = plan_context.plan_dir_for('disp-rwf-sub')
    _seed_status_json(plan_dir)
    result = run_script(
        SCRIPT_PATH,
        'record-dispatch-boundary',
        '--plan-id',
        'disp-rwf-sub',
        '--phase',
        '6-finalize',
        '--termination-cause',
        'returned_with_findings',
    )
    assert result.returncode == 0, (
        f'returned_with_findings MUST be accepted by argparse: {result.stderr}'
    )
    assert _boundary_path(plan_dir, '6-finalize').exists()


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
