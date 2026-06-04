#!/usr/bin/env python3
# ruff: noqa: I001, E402, F811
"""Tests for phase_handshake pending-findings invariants and blocking-type roundtrip.

Split from test_phase_handshake.py: covers the two pluggable invariants
(``pending_findings_by_type``, ``pending_findings_blocking_count``), the
intra-finalize re-capture boundary guards, the qgate aggregator, and the
D4 round-trip parametrized contract over every blocking type.
"""

from __future__ import annotations

import pytest

from _handshake_fixtures import (
    _ns,
    cmds,
    inv,
    store,
    # Fixtures (imported so pytest can resolve them):
    stub_metadata,  # noqa: F401
)


@pytest.fixture
def only_pending_findings_invariants(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace INVARIANTS with just the two real pending-finding entries."""
    stubbed = [
        (
            'pending_findings_by_type',
            lambda _pid, _md: True,
            inv._capture_pending_findings_by_type,
        ),
        (
            'pending_findings_blocking_count',
            lambda _pid, _md: True,
            inv._capture_pending_findings_blocking_count,
        ),
    ]
    monkeypatch.setattr(inv, 'INVARIANTS', stubbed)
    monkeypatch.setattr(cmds, 'INVARIANTS', stubbed)


@pytest.fixture
def stub_query_counts(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """Stub ``_query_pending_count_for_type`` with a per-type pending counter."""
    state: dict[str, int] = {}

    def _query(_plan_id: str, finding_type: str) -> int:
        return state.get(finding_type, 0)

    monkeypatch.setattr(inv, '_query_pending_count_for_type', _query)
    return state


@pytest.fixture
def stub_blocking_types(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str] | None]:
    """Stub ``_read_blocking_finding_types`` with a per-phase mapping."""
    state: dict[str, list[str] | None] = {}

    def _read(_plan_id: str, phase: str) -> list[str] | None:
        return state.get(phase)

    monkeypatch.setattr(inv, '_read_blocking_finding_types', _read)
    return state


# --- (a) per-type capture matches manage-findings query output -----------


def test_capture_pending_findings_by_type_compact_summary(
    plan_context, only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """The per-type row mirrors the per-type query and stays sorted/stable."""
    stub_query_counts['bug'] = 2
    stub_query_counts['lint-issue'] = 1
    stub_query_counts['insight'] = 5
    stub_blocking_types['5-execute'] = None

    result = cmds.cmd_capture(_ns(plan_id='pf-by-type', phase='5-execute'))

    assert result['status'] == 'success'
    summary = result['invariants']['pending_findings_by_type']
    assert 'bug=2' in summary
    assert 'lint-issue=1' in summary
    assert 'insight=5' in summary
    assert 'tip=0' in summary
    assert 'best-practice=0' in summary
    assert result['invariants']['pending_findings_blocking_count'] in (0, '0')


def test_capture_pending_findings_by_type_persists_to_handshakes_toon(
    plan_context, only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """The per-type row round-trips through handshakes.toon under the schema."""
    stub_query_counts['triage'] = 4
    stub_blocking_types['5-execute'] = None

    cmds.cmd_capture(_ns(plan_id='pf-persist', phase='5-execute'))

    row = store.get_row('pf-persist', '5-execute')
    assert row is not None
    assert 'pending_findings_by_type' in row
    assert 'triage=4' in row['pending_findings_by_type']
    assert 'pending_findings_blocking_count' in row


def test_handshake_fields_includes_pending_finding_columns() -> None:
    """The TOON column schema must include both pending-finding columns."""
    assert 'pending_findings_by_type' in store.HANDSHAKE_FIELDS
    assert 'pending_findings_blocking_count' in store.HANDSHAKE_FIELDS


# --- (b) verify-strict blocks transition at guarded boundary -------------


def test_capture_at_finalize_boundary_blocks_when_blocking_type_pending(
    plan_context, only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """5-execute → 6-finalize: capture --phase 6-finalize must refuse."""
    stub_query_counts['bug'] = 1
    stub_query_counts['lint-issue'] = 0
    stub_blocking_types['6-finalize'] = ['bug', 'lint-issue']

    result = cmds.cmd_capture(_ns(plan_id='pf-block-finalize', phase='6-finalize'))

    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['blocking_count'] == 1
    assert result['blocking_types'] == ['bug', 'lint-issue']
    assert result['per_type'] == {'bug': 1, 'lint-issue': 0}
    assert store.get_row('pf-block-finalize', '6-finalize') is None


def test_capture_blocks_automated_review_to_branch_cleanup_boundary(
    plan_context, only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """automated-review → branch-cleanup boundary is guarded via re-capture."""
    stub_query_counts['sonar-issue'] = 2
    stub_blocking_types['6-finalize'] = ['sonar-issue']

    result = cmds.cmd_capture(_ns(plan_id='pf-block-autoreview', phase='6-finalize'))

    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['blocking_count'] == 2
    assert result['per_type'] == {'sonar-issue': 2}
    assert store.get_row('pf-block-autoreview', '6-finalize') is None


def test_capture_blocks_sonar_roundtrip_next_boundary(
    plan_context, only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """sonar-roundtrip → next boundary is guarded via re-capture."""
    stub_query_counts['pr-comment'] = 3
    stub_blocking_types['6-finalize'] = ['pr-comment']

    result = cmds.cmd_capture(_ns(plan_id='pf-block-sonar', phase='6-finalize'))

    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['blocking_count'] == 3
    assert result['per_type'] == {'pr-comment': 3}
    assert store.get_row('pf-block-sonar', '6-finalize') is None


def test_verify_at_finalize_boundary_reports_drift_for_strict_mode(
    plan_context, only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """cmd_verify translates BlockingFindingsPresent into drift on the
    blocking-count column — the CLI ``--strict`` flag turns drift into exit 1."""
    stub_blocking_types['6-finalize'] = ['bug']

    cap = cmds.cmd_capture(_ns(plan_id='pf-verify-strict', phase='6-finalize'))
    assert cap['status'] == 'success'

    stub_query_counts['bug'] = 1
    result = cmds.cmd_verify(_ns(plan_id='pf-verify-strict', phase='6-finalize'))

    assert result['status'] == 'drift'
    diff_names = {d['invariant'] for d in result['diffs']}
    assert 'pending_findings_blocking_count' in diff_names


# --- (c) verify-strict allows transition with only non-blocking types ---


def test_capture_at_finalize_succeeds_when_only_long_lived_findings_pending(
    plan_context, only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """Only the four long-lived non-blocking types pending → boundary clears."""
    stub_query_counts['insight'] = 7
    stub_query_counts['tip'] = 4
    stub_query_counts['best-practice'] = 2
    stub_query_counts['improvement'] = 9
    stub_blocking_types['6-finalize'] = ['bug', 'lint-issue', 'sonar-issue']

    result = cmds.cmd_capture(_ns(plan_id='pf-long-lived', phase='6-finalize'))

    assert result['status'] == 'success'
    assert result['invariants']['pending_findings_blocking_count'] in (0, '0')
    summary = result['invariants']['pending_findings_by_type']
    assert 'insight=7' in summary
    assert 'tip=4' in summary
    assert 'best-practice=2' in summary
    assert 'improvement=9' in summary
    row = store.get_row('pf-long-lived', '6-finalize')
    assert row is not None
    assert row['pending_findings_blocking_count'] in (0, '0')

    verify = cmds.cmd_verify(_ns(plan_id='pf-long-lived', phase='6-finalize'))
    assert verify['status'] == 'ok'


def test_blocking_count_zero_when_no_partition_configured(
    plan_context, only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """Phases without a blocking_finding_types config slot capture as 0."""
    stub_query_counts['bug'] = 5
    stub_blocking_types['3-outline'] = None

    result = cmds.cmd_capture(_ns(plan_id='pf-no-partition', phase='3-outline'))

    assert result['status'] == 'success'
    assert result['invariants']['pending_findings_blocking_count'] in (0, '0')
    summary = result['invariants']['pending_findings_by_type']
    assert 'bug=5' in summary


def test_blocking_count_passive_at_non_guarded_boundary(
    plan_context, only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """Non-guarded phases capture the blocking total without raising."""
    stub_query_counts['bug'] = 2
    stub_blocking_types['5-execute'] = ['bug']

    result = cmds.cmd_capture(_ns(plan_id='pf-passive', phase='5-execute'))

    assert result['status'] == 'success'
    assert result['invariants']['pending_findings_blocking_count'] in (2, '2')


# --- (d) accepted / taken_into_account resolutions count as resolved -----


def test_query_pending_count_excludes_accepted_and_taken_into_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_query_pending_count_for_type`` filters by ``--resolution pending``."""
    captured: list[list[str]] = []

    def _fake_run(args: list[str]) -> str:
        captured.append(args)
        return 'filtered_count: 0\n'

    monkeypatch.setattr(inv, '_run_script', _fake_run)

    inv._query_pending_count_for_type('any-plan', 'bug')

    assert len(captured) == 1
    args = captured[0]
    resolution_idx = args.index('--resolution')
    assert args[resolution_idx + 1] == 'pending'
    type_idx = args.index('--type')
    assert args[type_idx + 1] == 'bug'


def test_capture_blocking_count_excludes_resolved_findings(
    plan_context, only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """End-to-end: a 6-finalize capture clears even when blocking-type
    findings exist in resolved buckets."""
    stub_query_counts['bug'] = 0
    stub_query_counts['lint-issue'] = 0
    stub_query_counts['sonar-issue'] = 0
    stub_blocking_types['6-finalize'] = ['bug', 'lint-issue', 'sonar-issue']

    result = cmds.cmd_capture(_ns(plan_id='pf-accepted', phase='6-finalize'))

    assert result['status'] == 'success'
    assert result['invariants']['pending_findings_blocking_count'] in (0, '0')
    row = store.get_row('pf-accepted', '6-finalize')
    assert row is not None


# --- (e) qgate aggregation across all phase files ------------------------


def test_qgate_aggregated_helper_loops_every_qgate_phase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_query_pending_qgate_count_aggregated`` issues one query per phase."""
    captured: list[list[str]] = []
    per_phase_counts = {
        '2-refine': 0,
        '3-outline': 1,
        '4-plan': 0,
        '5-execute': 2,
        '6-finalize': 0,
    }

    def _fake_run(args: list[str]) -> str:
        captured.append(args)
        phase_idx = args.index('--phase')
        phase = args[phase_idx + 1]
        return f'filtered_count: {per_phase_counts.get(phase, 0)}\n'

    monkeypatch.setattr(inv, '_run_script', _fake_run)

    total = inv._query_pending_qgate_count_aggregated('any-plan')

    assert total == 3
    assert len(captured) == len(inv.QGATE_PHASES)
    for args in captured:
        assert args[1] == 'qgate'
        assert args[2] == 'list'
        resolution_idx = args.index('--resolution')
        assert args[resolution_idx + 1] == 'pending'

    queried_phases = {args[args.index('--phase') + 1] for args in captured}
    assert queried_phases == set(inv.QGATE_PHASES)


def test_qgate_aggregated_helper_returns_none_on_partial_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Any per-phase query failure poisons the aggregate to ``None``."""
    def _fake_run(args: list[str]) -> str | None:
        phase = args[args.index('--phase') + 1]
        if phase == '4-plan':
            return None
        return 'filtered_count: 0\n'

    monkeypatch.setattr(inv, '_run_script', _fake_run)

    total = inv._query_pending_qgate_count_aggregated('any-plan')

    assert total is None


def test_capture_blocks_at_finalize_when_qgate_pending_via_aggregator(
    plan_context,
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """qgate is in the default blocking partition for 6-finalize."""
    monkeypatch.setattr(
        inv,
        '_query_pending_qgate_count_aggregated',
        lambda _plan_id: 1,
    )
    stub_blocking_types['6-finalize'] = ['qgate']

    result = cmds.cmd_capture(_ns(plan_id='pf-block-qgate', phase='6-finalize'))

    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['blocking_count'] == 1
    assert result['blocking_types'] == ['qgate']
    assert result['per_type'] == {'qgate': 1}
    assert store.get_row('pf-block-qgate', '6-finalize') is None


def test_capture_succeeds_at_finalize_when_qgate_finding_accepted(
    plan_context,
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """qgate findings resolved via ``accepted`` / ``taken_into_account``
    drop out of the pending count; the boundary clears."""
    monkeypatch.setattr(
        inv,
        '_query_pending_qgate_count_aggregated',
        lambda _plan_id: 0,
    )
    stub_blocking_types['6-finalize'] = ['qgate']

    result = cmds.cmd_capture(_ns(plan_id='pf-qgate-accepted', phase='6-finalize'))

    assert result['status'] == 'success'
    assert result['invariants']['pending_findings_blocking_count'] in (0, '0')
    row = store.get_row('pf-qgate-accepted', '6-finalize')
    assert row is not None
    assert row['pending_findings_blocking_count'] in (0, '0')


def test_capture_routes_only_qgate_via_aggregator(
    plan_context,
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The qgate-aggregator route MUST NOT leak into other blocking types."""
    aggregator_calls: list[str] = []
    type_query_types: list[str] = []

    def _fake_aggregator(plan_id: str) -> int:
        aggregator_calls.append(plan_id)
        return 0

    def _fake_type_query(_plan_id: str, finding_type: str) -> int:
        type_query_types.append(finding_type)
        return 0

    monkeypatch.setattr(inv, '_query_pending_qgate_count_aggregated', _fake_aggregator)
    monkeypatch.setattr(inv, '_query_pending_count_for_type', _fake_type_query)

    stub_blocking_types['6-finalize'] = ['build-error', 'qgate', 'lint-issue']

    result = cmds.cmd_capture(_ns(plan_id='pf-qgate-route', phase='6-finalize'))

    assert result['status'] == 'success'
    assert aggregator_calls == ['pf-qgate-route']
    assert 'qgate' not in type_query_types
    assert 'build-error' in type_query_types
    assert 'lint-issue' in type_query_types


# --- (f) intra-finalize boundary re-capture (production scenarios) -------


def test_pending_pr_comment_blocks_automated_review_to_branch_cleanup(
    plan_context,
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
) -> None:
    """automated-review → branch-cleanup intra-finalize re-capture."""
    stub_query_counts['pr-comment'] = 2
    stub_blocking_types['6-finalize'] = ['pr-comment']

    result = cmds.cmd_capture(_ns(plan_id='pf-intra-autoreview', phase='6-finalize'))

    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['blocking_count'] == 2
    assert 'pr-comment' in result['blocking_types']
    assert result['per_type'] == {'pr-comment': 2}
    assert store.get_row('pf-intra-autoreview', '6-finalize') is None


def test_pending_sonar_issue_blocks_sonar_roundtrip_to_next(
    plan_context,
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
) -> None:
    """sonar-roundtrip → next intra-finalize re-capture."""
    stub_query_counts['sonar-issue'] = 1
    stub_blocking_types['6-finalize'] = ['sonar-issue']

    result = cmds.cmd_capture(_ns(plan_id='pf-intra-sonar', phase='6-finalize'))

    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['blocking_count'] == 1
    assert 'sonar-issue' in result['blocking_types']
    assert result['per_type'] == {'sonar-issue': 1}
    assert store.get_row('pf-intra-sonar', '6-finalize') is None


def test_intra_finalize_recapture_clears_after_resolution(
    plan_context,
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
) -> None:
    """The intra-finalize re-capture loop-back contract: clears after fix."""
    stub_query_counts['pr-comment'] = 1
    stub_blocking_types['6-finalize'] = ['pr-comment']

    first = cmds.cmd_capture(_ns(plan_id='pf-intra-loop', phase='6-finalize'))
    assert first['status'] == 'error'
    assert first['error'] == 'blocking_findings_present'

    stub_query_counts['pr-comment'] = 0

    second = cmds.cmd_capture(_ns(plan_id='pf-intra-loop', phase='6-finalize'))
    assert second['status'] == 'success'
    assert second['invariants']['pending_findings_blocking_count'] in (0, '0')
    row = store.get_row('pf-intra-loop', '6-finalize')
    assert row is not None


# =============================================================================
# D4: Round-trip tests for every blocking type in the dict[str, Callable] mapping
# =============================================================================


import determine_mode as _determine_mode_for_roundtrip  # type: ignore[import-not-found]  # noqa: E402


@pytest.mark.parametrize(
    'finding_type',
    sorted(_determine_mode_for_roundtrip._FINALIZE_BLOCKING_TYPES.keys()),
)
def test_blocking_type_roundtrip_queried_matches_produced(
    finding_type: str,
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Round-trip: producing N findings of this type → query reports exactly N."""
    produced_count = 3
    if finding_type == 'qgate':
        monkeypatch.setattr(
            inv, '_query_pending_qgate_count_aggregated', lambda _plan_id: produced_count
        )
    else:
        stub_query_counts[finding_type] = produced_count

    stub_blocking_types['5-execute'] = [finding_type]

    queried_count = inv._capture_pending_findings_blocking_count(
        'plan-roundtrip', {}, '5-execute'
    )

    assert queried_count == produced_count, (
        f'Round-trip failed for blocking type {finding_type!r}: '
        f'queried={queried_count}, produced={produced_count}.'
    )


def test_blocking_type_silent_zero_tripwire_all_types_have_dispatch(
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No type in the mapping silently returns zero when traffic exists."""
    mapping_keys = sorted(_determine_mode_for_roundtrip._FINALIZE_BLOCKING_TYPES.keys())

    monkeypatch.setattr(
        inv, '_query_pending_qgate_count_aggregated', lambda _plan_id: 1
    )
    for finding_type in mapping_keys:
        if finding_type == 'qgate':
            continue
        stub_query_counts[finding_type] = 1

    stub_blocking_types['5-execute'] = list(mapping_keys)

    queried_total = inv._capture_pending_findings_blocking_count(
        'plan-tripwire', {}, '5-execute'
    )

    expected_total = len(mapping_keys)
    assert queried_total == expected_total


# =============================================================================
# findings-check: read-only single-invariant verb (cmd_findings_check)
# =============================================================================


@pytest.fixture
def explode_phase_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``_capture_phase_steps_complete`` raise unconditionally.

    The regression assertion for ``findings-check`` is that it does NOT route
    through ``capture_all`` — so this exploding stub must NEVER fire through the
    verb. If a future refactor wires ``cmd_findings_check`` to ``capture_all``,
    the ``PhaseStepsIncomplete`` raised here would surface and break the test.
    """
    def _explode(_pid: str, _md: dict, phase: str):
        raise inv.PhaseStepsIncomplete(phase, missing=['step-a'], not_done=[])

    monkeypatch.setattr(inv, '_capture_phase_steps_complete', _explode)


def test_findings_check_succeeds_when_no_blocking_findings(
    plan_context, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """(a) Clean count → ``status: success`` with the blocking_count echoed."""
    stub_query_counts['bug'] = 0
    stub_blocking_types['6-finalize'] = ['bug']

    result = cmds.cmd_findings_check(_ns(plan_id='fc-clean', phase='6-finalize'))

    assert result['status'] == 'success'
    assert result['plan_id'] == 'fc-clean'
    assert result['phase'] == '6-finalize'
    assert result['blocking_count'] == 0
    # Read-only: no handshake row is ever written by findings-check.
    assert store.get_row('fc-clean', '6-finalize') is None


def test_findings_check_blocks_when_blocking_finding_pending(
    plan_context, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """(c) Pending blocking finding → the composite-capture error envelope."""
    stub_query_counts['pr-comment'] = 2
    stub_blocking_types['6-finalize'] = ['pr-comment']

    result = cmds.cmd_findings_check(_ns(plan_id='fc-block', phase='6-finalize'))

    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['plan_id'] == 'fc-block'
    assert result['phase'] == '6-finalize'
    assert result['blocking_count'] == 2
    assert result['blocking_types'] == ['pr-comment']
    assert result['per_type'] == {'pr-comment': 2}
    assert 'message' in result
    # Read-only: the blocking verdict writes no handshake row.
    assert store.get_row('fc-block', '6-finalize') is None


def test_findings_check_does_not_run_phase_steps_complete(
    plan_context, stub_metadata, stub_query_counts, stub_blocking_types, explode_phase_steps
) -> None:
    """(b) Regression: findings-check evaluates ONLY the blocking-findings
    invariant — never ``phase_steps_complete`` — so a mid-pipeline checkpoint
    where the required steps are incomplete still produces
    ``blocking_findings_present`` (NOT ``phase_steps_incomplete``)."""
    stub_query_counts['sonar-issue'] = 1
    stub_blocking_types['6-finalize'] = ['sonar-issue']

    result = cmds.cmd_findings_check(_ns(plan_id='fc-no-steps', phase='6-finalize'))

    # The exploding phase_steps stub did NOT fire — the verb skipped capture_all.
    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['error'] != 'phase_steps_incomplete'
    assert result['blocking_count'] == 1


def test_findings_check_clean_count_ignores_incomplete_phase_steps(
    plan_context, stub_metadata, stub_query_counts, stub_blocking_types, explode_phase_steps
) -> None:
    """Clean blocking count clears even when phase steps are incomplete — the
    core fix: the gate no longer short-circuits on ``phase_steps_incomplete``."""
    stub_query_counts['bug'] = 0
    stub_blocking_types['6-finalize'] = ['bug']

    result = cmds.cmd_findings_check(_ns(plan_id='fc-clean-no-steps', phase='6-finalize'))

    assert result['status'] == 'success'
    assert result['blocking_count'] == 0


def test_findings_check_error_envelope_matches_composite_capture(
    plan_context, only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """(c) The blocking-findings error payload field set is identical between
    ``findings-check`` and the composite ``capture`` so the two intra-finalize
    callers branch on an interchangeable envelope."""
    stub_query_counts['pr-comment'] = 3
    stub_blocking_types['6-finalize'] = ['pr-comment']

    capture_result = cmds.cmd_capture(_ns(plan_id='fc-parity-cap', phase='6-finalize'))
    check_result = cmds.cmd_findings_check(_ns(plan_id='fc-parity-chk', phase='6-finalize'))

    # Same field set (plan_id differs by construction; keys must match).
    assert set(capture_result.keys()) == set(check_result.keys())
    for key in ('status', 'error', 'blocking_count', 'blocking_types', 'per_type'):
        assert capture_result[key] == check_result[key]


def test_findings_check_refuses_on_unresolved_worktree(
    plan_context, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """The worktree-resolution assertion fires before the findings query, so an
    unresolved worktree surfaces ``worktree_unresolved`` (consistent with
    ``capture`` / ``verify``)."""
    stub_metadata['use_worktree'] = True
    stub_metadata['worktree_path'] = ''
    stub_blocking_types['6-finalize'] = ['bug']

    result = cmds.cmd_findings_check(_ns(plan_id='fc-wt', phase='6-finalize'))

    assert result['status'] == 'error'
    assert result['error'] == 'worktree_unresolved'
    assert result['plan_id'] == 'fc-wt'
    assert result['phase'] == '6-finalize'


def test_findings_check_fails_closed_on_unevaluable_query(
    plan_context, stub_metadata, stub_blocking_types, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partial query failure (per-type query returns ``None``) makes the gate
    fail CLOSED with ``query_failed`` rather than failing open as
    ``status: success``. The intra-finalize boundary must not advance to
    branch-cleanup without proof that no blocking findings remain — returning
    success on an unevaluable invariant would be a fail-open gate."""
    monkeypatch.setattr(inv, '_query_pending_count_for_type', lambda _p, _t: None)
    stub_blocking_types['6-finalize'] = ['bug']

    result = cmds.cmd_findings_check(_ns(plan_id='fc-query-fail', phase='6-finalize'))

    assert result['status'] == 'error'
    assert result['error'] == 'query_failed'
    assert result['plan_id'] == 'fc-query-fail'
    assert result['phase'] == '6-finalize'
    assert 'message' in result
    # Read-only: no handshake row is written even on the query-failure path.
    assert store.get_row('fc-query-fail', '6-finalize') is None
