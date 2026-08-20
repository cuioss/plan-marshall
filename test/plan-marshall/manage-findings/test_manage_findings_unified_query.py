#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-findings.py script."""


from _manage_findings_fixtures import (
    _add_ns,
    _qgate_add_ns,
    _qgate_query_ns,
    _qgate_resolve_ns,
    _query_ns,
    _resolve_ns,
    cmd_add,
    cmd_qgate_add,
    cmd_qgate_query,
    cmd_qgate_resolve,
    cmd_query,
    cmd_resolve,
    query_findings_unified,
)

# =============================================================================
# Test: resolution_detail relational integrity
# =============================================================================


def test_resolution_detail_keyed_to_parent_hash_id(plan_context):
    """resolution_detail is written keyed to the same hash_id as its parent record."""
    pid = 'res-detail-integrity'
    add_result = cmd_add(_add_ns(plan_id=pid, type='bug', title='keyed', detail='d'))
    hash_id = str(add_result['hash_id'])

    cmd_resolve(_resolve_ns(plan_id=pid, hash_id=hash_id, resolution='fixed', detail='fixed in abc'))

    query = cmd_query(_query_ns(plan_id=pid, type='bug'))
    record = query['findings'][0]
    assert record['hash_id'] == hash_id
    assert record['resolution'] == 'fixed'
    assert record['resolution_detail'] == 'fixed in abc'


def test_resolve_missing_parent_returns_error_and_writes_no_orphan(plan_context):
    """Resolving a non-existent hash_id fails and never writes an orphan detail."""
    pid = 'res-detail-orphan'
    cmd_add(_add_ns(plan_id=pid, type='bug', title='present', detail='d'))

    result = cmd_resolve(_resolve_ns(plan_id=pid, hash_id='deadbeef', resolution='fixed', detail='orphan detail'))
    assert result['status'] == 'error'

    query = cmd_query(_query_ns(plan_id=pid))
    assert all(f.get('resolution_detail') != 'orphan detail' for f in query['findings'])


# =============================================================================
# Test: Unified per-plan + Q-Gate read surface (--include-qgate)
# =============================================================================


def test_unified_query_merges_plan_and_qgate(plan_context):
    """(a) --include-qgate returns both per-plan findings and pending Q-Gate findings."""
    pid = 'unified-merge'
    cmd_add(_add_ns(plan_id=pid, type='bug', title='Plan bug', detail='d'))
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid,
            phase='5-execute',
            source='qgate',
            type='triage',
            title='Q-Gate finding',
            detail='d',
        )
    )

    plain = cmd_query(_query_ns(plan_id=pid))
    assert plain['filtered_count'] == 1
    assert 'qgate_included' not in plain

    unified = cmd_query(_query_ns(plan_id=pid, include_qgate=True))
    assert unified['status'] == 'success'
    assert unified['qgate_included'] is True
    assert unified['plan_count'] == 1
    assert unified['qgate_count'] == 1
    assert unified['filtered_count'] == 2
    titles = {f['title'] for f in unified['findings']}
    assert titles == {'Plan bug', 'Q-Gate finding'}


def test_unified_query_spans_all_phases(plan_context):
    """(b) Per-plan unified query returns q-gate findings across every phase."""
    pid = 'unified-all-phases'
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='3-outline', source='qgate', type='triage', title='Phase 3 fd', detail='d'
        )
    )
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='4-plan', source='qgate', type='triage', title='Phase 4 fd', detail='d'
        )
    )
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='Phase 5 fd', detail='d'
        )
    )

    unified = cmd_query(_query_ns(plan_id=pid, include_qgate=True))
    assert unified['plan_count'] == 0
    assert unified['qgate_count'] == 3
    assert unified['filtered_count'] == 3
    titles = {f['title'] for f in unified['findings']}
    assert titles == {'Phase 3 fd', 'Phase 4 fd', 'Phase 5 fd'}


def test_unified_query_excludes_resolved_qgate(plan_context):
    """(b) Only PENDING q-gate findings are merged; resolved ones are dropped."""
    pid = 'unified-only-pending'
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='Stays pending', detail='d'
        )
    )
    resolved = cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='Gets resolved', detail='d'
        )
    )
    cmd_qgate_resolve(
        _qgate_resolve_ns(
            plan_id=pid,
            hash_id=str(resolved['hash_id']),
            resolution='taken_into_account',
            phase='5-execute',
        )
    )

    unified = cmd_query(_query_ns(plan_id=pid, include_qgate=True))
    assert unified['qgate_count'] == 1
    titles = {f['title'] for f in unified['findings']}
    assert titles == {'Stays pending'}


def test_unified_query_excludes_rejected_qgate(plan_context):
    """A `rejected` q-gate finding is non-pending: dropped from the unified gate read.

    The ext-point-verify findings pipeline adds `rejected` as a terminal,
    non-blocking resolution. Through the CLI command layer, a q-gate finding
    resolved to `rejected` must be excluded from `list --include-qgate` exactly
    like a `taken_into_account` finding.
    """
    pid = 'unified-rejected-nonpending'
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='Stays pending', detail='d'
        )
    )
    rejected = cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='Gets rejected', detail='d'
        )
    )
    cmd_qgate_resolve(
        _qgate_resolve_ns(
            plan_id=pid,
            hash_id=str(rejected['hash_id']),
            resolution='rejected',
            phase='5-execute',
        )
    )

    unified = cmd_query(_query_ns(plan_id=pid, include_qgate=True))
    assert unified['qgate_count'] == 1
    titles = {f['title'] for f in unified['findings']}
    assert titles == {'Stays pending'}


def test_unified_query_type_filter_applies_to_both_slices(plan_context):
    """(c) The --type narrow filters both plan and q-gate slices."""
    pid = 'unified-type-filter'
    cmd_add(_add_ns(plan_id=pid, type='bug', title='Plan bug', detail='d'))
    cmd_add(_add_ns(plan_id=pid, type='tip', title='Plan tip', detail='d'))
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='QG triage', detail='d'
        )
    )

    unified = cmd_query(_query_ns(plan_id=pid, type='bug', include_qgate=True))
    assert unified['plan_count'] == 1
    assert unified['qgate_count'] == 0
    assert unified['filtered_count'] == 1
    assert unified['findings'][0]['title'] == 'Plan bug'
    # total_count spans the FULL universe of both slices symmetrically: the
    # entire plan store (2 findings: bug + tip) plus every pending q-gate record
    # (1: QG triage), before the --type narrowing. filtered_count (1) is the
    # post-narrowing union. total_count must NOT mix the plan store's unfiltered
    # total with the q-gate slice's filtered count.
    assert unified['total_count'] == 3


def test_unified_query_resolution_filter_scopes_plan_slice(plan_context):
    """(c) The --resolution narrow scopes the plan slice without dropping pending q-gate."""
    pid = 'unified-res-filter'
    fixed = cmd_add(_add_ns(plan_id=pid, type='bug', title='Fixed bug', detail='d'))
    cmd_resolve(_resolve_ns(plan_id=pid, hash_id=str(fixed['hash_id']), resolution='fixed'))
    cmd_add(_add_ns(plan_id=pid, type='bug', title='Open bug', detail='d'))
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='QG pending', detail='d'
        )
    )

    unified = cmd_query(_query_ns(plan_id=pid, resolution='fixed', include_qgate=True))
    # Plan slice narrowed to the single fixed finding; pending q-gate still merged.
    assert unified['plan_count'] == 1
    assert unified['qgate_count'] == 1
    titles = {f['title'] for f in unified['findings']}
    assert titles == {'Fixed bug', 'QG pending'}


def test_unified_query_empty(plan_context):
    """(d) Unified read on an empty plan returns zero counts but the unified shape."""
    unified = cmd_query(_query_ns(plan_id='unified-empty', include_qgate=True))
    assert unified['status'] == 'success'
    assert unified['qgate_included'] is True
    assert unified['plan_count'] == 0
    assert unified['qgate_count'] == 0
    assert unified['filtered_count'] == 0
    assert unified['findings'] == []


def test_unified_query_core_direct(plan_context):
    """Direct core call (bypassing CLI namespace) merges plan + pending q-gate."""
    pid = 'unified-core-direct'
    cmd_add(_add_ns(plan_id=pid, type='bug', title='Core plan bug', detail='d'))
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='Core QG', detail='d'
        )
    )

    unified = query_findings_unified(pid)
    assert unified['qgate_included'] is True
    assert unified['plan_count'] == 1
    assert unified['qgate_count'] == 1
    titles = {f['title'] for f in unified['findings']}
    assert titles == {'Core plan bug', 'Core QG'}


def test_backward_compat_list_without_include_qgate(plan_context):
    """(d) Existing list call shape (no --include-qgate) keeps its original shape."""
    pid = 'compat-list'
    cmd_add(_add_ns(plan_id=pid, type='bug', title='Plan bug', detail='d'))
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='QG finding', detail='d'
        )
    )

    plain = cmd_query(_query_ns(plan_id=pid))
    assert plain['status'] == 'success'
    # No q-gate provenance keys; q-gate finding is NOT merged.
    assert 'qgate_included' not in plain
    assert 'plan_count' not in plain
    assert plain['filtered_count'] == 1
    assert plain['findings'][0]['title'] == 'Plan bug'


def test_backward_compat_qgate_list_unaffected(plan_context):
    """(d) The narrowed qgate list call shape is unchanged by the unified surface."""
    pid = 'compat-qgate-list'
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='3-outline', source='qgate', type='triage', title='QG fd', detail='d'
        )
    )

    result = cmd_qgate_query(_qgate_query_ns(plan_id=pid, phase='3-outline'))
    assert result['status'] == 'success'
    assert result['phase'] == '3-outline'
    assert result['total_count'] == 1
    assert result['filtered_count'] == 1
    # Per-phase qgate list does NOT carry the unified provenance markers.
    assert 'qgate_included' not in result
