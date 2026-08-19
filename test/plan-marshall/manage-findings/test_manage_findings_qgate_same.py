#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-findings.py script."""


from _manage_findings_fixtures import (
    _add_ns,
    _parse_raw_input,
    _qgate_add_ns,
    _qgate_query_ns,
    _qgate_resolve_ns,
    _query_ns,
    _RawInputError,
    _resolve_ns,
    cmd_add,
    cmd_qgate_add,
    cmd_qgate_query,
    cmd_qgate_resolve,
    cmd_query,
    cmd_resolve,
)


def test_qgate_same_title_same_discriminator_merges(plan_context):
    """Same title AND same discriminator across iterations collapses to one record."""
    pid = 'qgate-same-disc-merge'
    r1 = cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid,
            phase='5-execute',
            title='dup-literal',
            detail='S1192 in Api.java',
            file_path='Api.java',
            rule='java:S1192',
            iteration=1,
        )
    )
    r2 = cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid,
            phase='5-execute',
            title='dup-literal',
            detail='S1192 in Api.java',
            file_path='Api.java',
            rule='java:S1192',
            iteration=2,
        )
    )
    assert r1['status'] == 'success'
    assert r2['status'] == 'deduplicated'
    assert str(r2['hash_id']) == str(r1['hash_id'])

    query_result = cmd_qgate_query(_qgate_query_ns(plan_id=pid, phase='5-execute'))
    assert query_result['total_count'] == 1


# =============================================================================
# Test: raw_input quarantine byte cap
# =============================================================================


def test_raw_input_bytecap_truncation(plan_context):
    """raw_input free-text over the byte cap is truncated with a [truncated] marker."""
    pid = 'rawinput-cap'
    big = 'x' * 200
    result = cmd_add(
        _add_ns(
            plan_id=pid,
            type='pr-comment',
            title='big comment',
            detail='d',
            raw_input={'body': big},
            raw_input_max_bytes=50,
        )
    )
    assert result['status'] == 'success'

    query = cmd_query(_query_ns(plan_id=pid, type='pr-comment'))
    record = query['findings'][0]
    assert 'raw_input' in record
    body = record['raw_input']['body']
    assert body.endswith('[truncated]')
    assert body[: -len('[truncated]')] == 'x' * 50


def test_raw_input_under_cap_stored_verbatim(plan_context):
    """A raw_input value within the cap is stored verbatim with no marker."""
    pid = 'rawinput-nocap'
    result = cmd_add(
        _add_ns(
            plan_id=pid,
            type='pr-comment',
            title='small comment',
            detail='d',
            raw_input={'body': 'short body'},
        )
    )
    assert result['status'] == 'success'

    query = cmd_query(_query_ns(plan_id=pid, type='pr-comment'))
    record = query['findings'][0]
    assert record['raw_input']['body'] == 'short body'


# =============================================================================
# Test: raw_input parse-error sentinel collision
# =============================================================================


def test_raw_input_status_error_pair_stored_as_data(plan_context):
    """A legitimate ``--raw-input status=error`` pair is stored as data, not
    mistaken for the parse-error sentinel and silently discarded.
    """
    pid = 'rawinput-status-error'
    result = cmd_add(
        _add_ns(
            plan_id=pid,
            type='pr-comment',
            title='status field carries the literal error',
            detail='d',
            raw_input=['status=error'],
        )
    )
    assert result['status'] == 'success'

    query = cmd_query(_query_ns(plan_id=pid, type='pr-comment'))
    record = query['findings'][0]
    assert record['raw_input']['status'] == 'error'


def test_parse_raw_input_success_dict_is_not_error_marker():
    """A successfully-parsed mapping (incl. a literal ``status=error`` pair) is a
    plain dict, never a ``_RawInputError`` sentinel.
    """
    parsed = _parse_raw_input(['status=error'])
    assert parsed == {'status': 'error'}
    assert not isinstance(parsed, _RawInputError)


def test_parse_raw_input_malformed_pair_returns_error_marker():
    """A malformed pair yields a ``_RawInputError`` carrying the canonical error payload."""
    parsed = _parse_raw_input(['no-equals-sign'])
    assert isinstance(parsed, _RawInputError)
    assert parsed['status'] == 'error'
    assert 'Invalid --raw-input' in parsed['message']


def test_parse_raw_input_empty_field_returns_error_marker():
    """An empty field name yields a ``_RawInputError`` sentinel."""
    parsed = _parse_raw_input(['=value'])
    assert isinstance(parsed, _RawInputError)
    assert parsed['status'] == 'error'


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
# Test: Finding Resolve with taken_into_account (extended)
# =============================================================================


def test_finding_resolve_taken_into_account(plan_context):
    """Test that taken_into_account resolution works for regular findings too."""
    add_result = cmd_add(_add_ns(type='triage', title='Reviewed finding', detail='d'))
    hash_id = str(add_result['hash_id'])

    result = cmd_resolve(
        _resolve_ns(
            hash_id=hash_id,
            resolution='taken_into_account',
            detail='Addressed in revision',
        )
    )
    assert result['resolution'] == 'taken_into_account'


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
