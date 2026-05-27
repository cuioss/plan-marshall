#!/usr/bin/env python3
# ruff: noqa: I001, E402, F811
"""Tests for phase_handshake cmd_capture / cmd_verify / cmd_list / cmd_clear.

Split from test_phase_handshake.py: covers the base capture / verify
command handlers, drift detection for each stubbed invariant, the
references_valid hash invariant, and the phase-aware blocking classifier.
"""

from __future__ import annotations

import pytest

from _handshake_fixtures import (
    SCRIPTS_DIR,
    _ns,
    cmds,
    inv,
    store,
    # Fixtures (imported so pytest can resolve them):
    stub_metadata,  # noqa: F401
    stubbed_invariants,  # noqa: F401
)


# =============================================================================
# cmd_capture / cmd_verify
# =============================================================================


def test_capture_first_time_success(plan_context, stubbed_invariants, stub_metadata) -> None:
    result = cmds.cmd_capture(_ns(plan_id='cap-a', phase='5-execute'))
    assert result['status'] == 'success'
    assert result['phase'] == '5-execute'
    assert result['worktree_applicable'] is False
    assert 'main_sha' in result['invariants']
    assert 'worktree_sha' not in result['invariants']


def test_capture_worktree_applicable(plan_context, stubbed_invariants, stub_metadata) -> None:
    stub_metadata['worktree_path'] = '/tmp/fake-worktree'
    stubbed_invariants['worktree_sha'] = 'wt-sha'
    stubbed_invariants['worktree_dirty'] = 0
    result = cmds.cmd_capture(_ns(plan_id='cap-b', phase='5-execute'))
    assert result['worktree_applicable'] is True
    assert result['invariants']['worktree_sha'] == 'wt-sha'


@pytest.mark.xfail(
    strict=False,
    reason=(
        'Root-cause notation fix (underscore manage_status -> hyphen manage-status '
        'in _handshake_commands.py:_load_status_metadata) is owned by plan '
        'renaming-a-marketplace-script-file-silently-chang. Until that plan lands, '
        '_load_status_metadata invokes an unresolvable executor notation. This '
        'contract test flips to a real pass once the sibling fix merges; the xfail '
        'marker is removed in a follow-up.'
    ),
)
def test_load_status_metadata_uses_resolvable_manage_status_notation() -> None:
    """End-to-end contract: _load_status_metadata must invoke a resolvable notation."""
    handshake_src = (SCRIPTS_DIR / '_handshake_commands.py').read_text(encoding='utf-8')
    canonical_notation = 'plan-marshall:manage-status:manage-status'
    underscore_notation = 'plan-marshall:manage-status:manage_status'

    assert canonical_notation in handshake_src, (
        '_handshake_commands.py must invoke manage-status via the canonical '
        f'hyphenated notation {canonical_notation!r} that the executor maps.'
    )
    assert underscore_notation not in handshake_src, (
        '_handshake_commands.py must not invoke the underscore notation '
        f'{underscore_notation!r} — it is absent from the executor SCRIPTS '
        'mapping and resolves to a non-zero exit, which _load_status_metadata '
        'swallows into an empty metadata dict.'
    )


def test_capture_override_requires_reason(plan_context, stubbed_invariants, stub_metadata) -> None:
    result = cmds.cmd_capture(_ns(plan_id='cap-c', phase='5-execute', override=True))
    assert result['status'] == 'error'
    assert result['error'] == 'missing_reason'


def test_capture_override_with_reason_stores_flag(plan_context, stubbed_invariants, stub_metadata) -> None:
    result = cmds.cmd_capture(_ns(plan_id='cap-d', phase='5-execute', override=True, reason='manual commit'))
    assert result['status'] == 'success'
    assert result['override'] is True
    row = store.get_row('cap-d', '5-execute')
    assert row is not None
    assert row['override'] is True
    assert row['override_reason'] == 'manual commit'


def test_verify_ok_no_drift(plan_context, stubbed_invariants, stub_metadata) -> None:
    cmds.cmd_capture(_ns(plan_id='ver-a', phase='5-execute'))
    result = cmds.cmd_verify(_ns(plan_id='ver-a', phase='5-execute'))
    assert result['status'] == 'ok'


def test_verify_drift_main_dirty(plan_context, stubbed_invariants, stub_metadata) -> None:
    cmds.cmd_capture(_ns(plan_id='ver-b', phase='5-execute'))
    stubbed_invariants['main_dirty'] = 5
    result = cmds.cmd_verify(_ns(plan_id='ver-b', phase='5-execute'))
    assert result['status'] == 'drift'
    diff_names = {d['invariant'] for d in result['diffs']}
    assert 'main_dirty' in diff_names


def test_verify_drift_main_sha(plan_context, stubbed_invariants, stub_metadata) -> None:
    cmds.cmd_capture(_ns(plan_id='ver-c', phase='5-execute'))
    stubbed_invariants['main_sha'] = 'def456'
    result = cmds.cmd_verify(_ns(plan_id='ver-c', phase='5-execute'))
    assert result['status'] == 'drift'
    diff_names = {d['invariant'] for d in result['diffs']}
    assert 'main_sha' in diff_names


def test_verify_drift_task_state_hash(plan_context, stubbed_invariants, stub_metadata) -> None:
    cmds.cmd_capture(_ns(plan_id='ver-d', phase='5-execute'))
    stubbed_invariants['task_state_hash'] = 'different-hash'
    result = cmds.cmd_verify(_ns(plan_id='ver-d', phase='5-execute'))
    assert result['status'] == 'drift'
    diff_names = {d['invariant'] for d in result['diffs']}
    assert 'task_state_hash' in diff_names


def test_verify_drift_qgate_count(plan_context, stubbed_invariants, stub_metadata) -> None:
    cmds.cmd_capture(_ns(plan_id='ver-e', phase='5-execute'))
    stubbed_invariants['qgate_open_count'] = 3
    result = cmds.cmd_verify(_ns(plan_id='ver-e', phase='5-execute'))
    assert result['status'] == 'drift'
    diff_names = {d['invariant'] for d in result['diffs']}
    assert 'qgate_open_count' in diff_names


def test_verify_drift_config_hash(plan_context, stubbed_invariants, stub_metadata) -> None:
    cmds.cmd_capture(_ns(plan_id='ver-f', phase='5-execute'))
    stubbed_invariants['config_hash'] = 'rotated'
    result = cmds.cmd_verify(_ns(plan_id='ver-f', phase='5-execute'))
    assert result['status'] == 'drift'
    diff_names = {d['invariant'] for d in result['diffs']}
    assert 'config_hash' in diff_names


def test_capture_persists_unfinished_tasks_count_to_handshakes_toon(
    plan_context, stubbed_invariants, stub_metadata
) -> None:
    """``unfinished_tasks_count`` must round-trip through handshakes.toon."""
    stubbed_invariants['unfinished_tasks_count'] = 4
    result = cmds.cmd_capture(_ns(plan_id='cap-pending-persist', phase='5-execute'))
    assert result['status'] == 'success'
    assert result['invariants'].get('unfinished_tasks_count') in (4, '4')
    row = store.get_row('cap-pending-persist', '5-execute')
    assert row is not None
    assert 'unfinished_tasks_count' in row, (
        f'unfinished_tasks_count must be a HANDSHAKE_FIELDS column, got {list(row)}'
    )
    assert row['unfinished_tasks_count'] in (4, '4'), row


def test_verify_drift_unfinished_tasks_count(plan_context, stubbed_invariants, stub_metadata) -> None:
    """A change in unfinished_tasks_count between capture and verify is drift."""
    stubbed_invariants['unfinished_tasks_count'] = 3
    cmds.cmd_capture(_ns(plan_id='ver-pending', phase='5-execute'))
    stubbed_invariants['unfinished_tasks_count'] = 0
    result = cmds.cmd_verify(_ns(plan_id='ver-pending', phase='5-execute'))
    assert result['status'] == 'drift'
    diff_names = {d['invariant'] for d in result['diffs']}
    assert 'unfinished_tasks_count' in diff_names


def test_handshake_fields_includes_unfinished_tasks_count() -> None:
    """The TOON column schema must include ``unfinished_tasks_count``."""
    assert 'unfinished_tasks_count' in store.HANDSHAKE_FIELDS


def test_verify_skipped_no_capture(plan_context, stubbed_invariants, stub_metadata) -> None:
    result = cmds.cmd_verify(_ns(plan_id='ver-g', phase='5-execute'))
    assert result['status'] == 'skipped'


def test_list_returns_all_captures(plan_context, stubbed_invariants, stub_metadata) -> None:
    cmds.cmd_capture(_ns(plan_id='list-a', phase='5-execute'))
    cmds.cmd_capture(_ns(plan_id='list-a', phase='6-finalize'))
    result = cmds.cmd_list(_ns(plan_id='list-a'))
    assert result['count'] == 2
    phases = {r['phase'] for r in result['handshakes']}
    assert phases == {'5-execute', '6-finalize'}


def test_clear_removes_one_phase(plan_context, stubbed_invariants, stub_metadata) -> None:
    cmds.cmd_capture(_ns(plan_id='clr-a', phase='5-execute'))
    cmds.cmd_capture(_ns(plan_id='clr-a', phase='6-finalize'))
    result = cmds.cmd_clear(_ns(plan_id='clr-a', phase='5-execute'))
    assert result['removed'] is True
    remaining = cmds.cmd_list(_ns(plan_id='clr-a'))
    assert remaining['count'] == 1
    assert remaining['handshakes'][0]['phase'] == '6-finalize'


def test_clear_missing_phase_reports_not_removed(plan_context, stubbed_invariants, stub_metadata) -> None:
    result = cmds.cmd_clear(_ns(plan_id='clr-b', phase='5-execute'))
    assert result['status'] == 'success'
    assert result['removed'] is False


# =============================================================================
# references_valid invariant
# =============================================================================


def _make_refs_toon_success(fields: dict) -> str:
    """Build a TOON string that ``manage-references read`` would emit on success."""
    lines = ['status: success', 'plan_id: test-plan']
    lines.append('references:')
    for k, v in fields.items():
        if isinstance(v, list):
            lines.append(f'  {k}: {len(v)} items')
        else:
            lines.append(f'  {k}: {v}')
    return '\n'.join(lines) + '\n'


def _make_refs_toon_error() -> str:
    return 'status: error\nerror: file_not_found\nmessage: references.json not found\n'


def test_references_valid_hash_stable_for_valid_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Capture of a present, valid references.json produces the same hash twice."""
    valid_toon = _make_refs_toon_success({
        'branch': 'feature/my-plan',
        'base_branch': 'main',
        'modified_files': [],
    })
    monkeypatch.setattr(inv, '_run_script', lambda _args: valid_toon)

    hash_a = inv._capture_references_valid('any', {}, '2-refine')
    hash_b = inv._capture_references_valid('any', {}, '2-refine')

    assert hash_a is not None
    assert isinstance(hash_a, str)
    assert len(hash_a) == 16
    assert hash_a == hash_b, (
        'Hash is not stable: two captures of the same valid references.json '
        f'produced different values: {hash_a!r} vs {hash_b!r}.'
    )


def test_references_valid_hash_differs_for_missing_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing references.json produces a hash that differs from the valid baseline."""
    valid_toon = _make_refs_toon_success({
        'branch': 'feature/my-plan',
        'base_branch': 'main',
        'modified_files': [],
    })
    error_toon = _make_refs_toon_error()

    monkeypatch.setattr(inv, '_run_script', lambda _args: valid_toon)
    hash_valid = inv._capture_references_valid('any', {}, '2-refine')

    monkeypatch.setattr(inv, '_run_script', lambda _args: error_toon)
    hash_missing = inv._capture_references_valid('any', {}, '2-refine')

    assert hash_valid is not None
    assert hash_missing is not None
    assert hash_valid != hash_missing


def test_references_valid_hash_differs_for_non_dict_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """An error response from manage-references read produces a hash differing from the valid baseline."""
    valid_toon = _make_refs_toon_success({
        'branch': 'feature/my-plan',
        'base_branch': 'main',
        'modified_files': [],
    })
    error_toon = _make_refs_toon_error()

    monkeypatch.setattr(inv, '_run_script', lambda _args: valid_toon)
    hash_valid = inv._capture_references_valid('any', {}, '2-refine')

    monkeypatch.setattr(inv, '_run_script', lambda _args: error_toon)
    hash_error = inv._capture_references_valid('any', {}, '2-refine')

    assert hash_valid is not None
    assert hash_error is not None
    assert hash_valid != hash_error


def test_references_valid_hash_differs_for_missing_required_field(monkeypatch: pytest.MonkeyPatch) -> None:
    """Removing a required field from references.json produces a different hash."""
    full_toon = _make_refs_toon_success({
        'branch': 'feature/my-plan',
        'base_branch': 'main',
        'modified_files': [],
    })
    partial_toon = _make_refs_toon_success({
        'branch': 'feature/my-plan',
        'base_branch': 'main',
    })

    monkeypatch.setattr(inv, '_run_script', lambda _args: full_toon)
    hash_full = inv._capture_references_valid('any', {}, '2-refine')

    monkeypatch.setattr(inv, '_run_script', lambda _args: partial_toon)
    hash_partial = inv._capture_references_valid('any', {}, '2-refine')

    assert hash_full is not None
    assert hash_partial is not None
    assert hash_full != hash_partial


def test_handshake_fields_includes_references_valid() -> None:
    """The TOON column schema must include ``references_valid``."""
    assert 'references_valid' in store.HANDSHAKE_FIELDS


# =============================================================================
# Blocking-classification axis (INVARIANT_BLOCKING_SCOPE)
# =============================================================================


def test_classifier_main_sha_blocking_at_5_execute() -> None:
    """main_sha drift IS blocking at verify --phase 5-execute."""
    assert inv.is_invariant_blocking_at_phase('main_sha', '5-execute') is True


def test_classifier_main_sha_informational_at_planning_phases() -> None:
    """main_sha drift is informational-only at every planning-phase boundary."""
    for planning_phase in ('1-init', '2-refine', '3-outline', '4-plan'):
        assert inv.is_invariant_blocking_at_phase('main_sha', planning_phase) is False, (
            f'main_sha must be informational at {planning_phase}, got blocking'
        )


def test_classifier_main_dirty_and_files_classified_same_as_main_sha() -> None:
    """main_dirty and main_dirty_files share the same blocking scope as main_sha."""
    for invariant in ('main_dirty', 'main_dirty_files'):
        assert inv.is_invariant_blocking_at_phase(invariant, '5-execute') is True
        for planning_phase in ('1-init', '2-refine', '3-outline', '4-plan'):
            assert inv.is_invariant_blocking_at_phase(invariant, planning_phase) is False


def test_classifier_task_state_hash_blocking_everywhere() -> None:
    """task_state_hash drift IS blocking at every boundary (planning + execute)."""
    for phase in ('1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-finalize'):
        assert inv.is_invariant_blocking_at_phase('task_state_hash', phase) is True, (
            f'task_state_hash must remain blocking at {phase}'
        )


def test_classifier_other_invariants_blocking_everywhere() -> None:
    """All non-main_* invariants remain blocking at every boundary."""
    always_blocking = (
        'worktree_sha',
        'worktree_dirty',
        'worktree_orphan',
        'references_valid',
        'task_state_hash',
        'qgate_open_count',
        'config_hash',
        'unfinished_tasks_count',
        'phase_steps_complete',
        'task_graph_valid',
        'pending_findings_by_type',
        'pending_findings_blocking_count',
    )
    for invariant in always_blocking:
        for phase in ('1-init', '3-outline', '4-plan', '5-execute', '6-finalize'):
            assert inv.is_invariant_blocking_at_phase(invariant, phase) is True, (
                f'{invariant} must remain blocking at {phase}'
            )


def test_classifier_unmapped_invariant_defaults_to_blocking() -> None:
    """Unknown invariant names fail safe to blocking_at_every_boundary."""
    assert inv.is_invariant_blocking_at_phase('newly_added_unmapped_invariant', '3-outline') is True


def test_verify_drift_main_sha_at_planning_phase_returns_ok_with_informational(
    plan_context, stubbed_invariants, stub_metadata
) -> None:
    """At a planning-phase boundary, main_sha drift returns status: ok and is
    surfaced in informational_diffs[], not the blocking diffs[] payload."""
    cmds.cmd_capture(_ns(plan_id='ver-cls-sha-planning', phase='3-outline'))
    stubbed_invariants['main_sha'] = 'def456'
    result = cmds.cmd_verify(_ns(plan_id='ver-cls-sha-planning', phase='3-outline'))

    assert result['status'] == 'ok', (
        f'main_sha drift at planning-phase 3-outline must NOT block, got {result!r}'
    )
    assert result.get('informational_count', 0) == 1
    informational = result.get('informational_diffs') or []
    info_names = {d['invariant'] for d in informational}
    assert 'main_sha' in info_names


def test_verify_drift_main_sha_at_5_execute_still_blocks(
    plan_context, stubbed_invariants, stub_metadata
) -> None:
    """At the 5-execute → 6-finalize boundary, main_sha drift IS blocking."""
    cmds.cmd_capture(_ns(plan_id='ver-cls-sha-execute', phase='5-execute'))
    stubbed_invariants['main_sha'] = 'def456'
    result = cmds.cmd_verify(_ns(plan_id='ver-cls-sha-execute', phase='5-execute'))

    assert result['status'] == 'drift'
    diff_names = {d['invariant'] for d in result['diffs']}
    assert 'main_sha' in diff_names


def test_verify_drift_main_dirty_at_planning_phase_returns_ok_with_informational(
    plan_context, stubbed_invariants, stub_metadata
) -> None:
    """main_dirty drift at planning-phase boundary is informational, not blocking."""
    cmds.cmd_capture(_ns(plan_id='ver-cls-dirty-planning', phase='2-refine'))
    stubbed_invariants['main_dirty'] = 7
    result = cmds.cmd_verify(_ns(plan_id='ver-cls-dirty-planning', phase='2-refine'))

    assert result['status'] == 'ok'
    informational = result.get('informational_diffs') or []
    info_names = {d['invariant'] for d in informational}
    assert 'main_dirty' in info_names


def test_verify_drift_task_state_hash_at_planning_phase_still_blocks(
    plan_context, stubbed_invariants, stub_metadata
) -> None:
    """task_state_hash drift at planning-phase boundary IS still blocking."""
    cmds.cmd_capture(_ns(plan_id='ver-cls-task-planning', phase='3-outline'))
    stubbed_invariants['task_state_hash'] = 'different-hash'
    result = cmds.cmd_verify(_ns(plan_id='ver-cls-task-planning', phase='3-outline'))

    assert result['status'] == 'drift'
    diff_names = {d['invariant'] for d in result['diffs']}
    assert 'task_state_hash' in diff_names


def test_verify_main_columns_persist_regardless_of_classification(
    plan_context, stubbed_invariants, stub_metadata
) -> None:
    """main_sha / main_dirty captured rows are persisted in handshakes.toon
    even at planning-phase boundaries — classification affects drift-counting,
    not persistence."""
    cmds.cmd_capture(_ns(plan_id='ver-cls-persistence', phase='3-outline'))
    rows = store.load_rows('ver-cls-persistence')
    assert len(rows) == 1
    row = rows[0]
    assert row.get('main_sha')
    assert 'main_dirty' in row
