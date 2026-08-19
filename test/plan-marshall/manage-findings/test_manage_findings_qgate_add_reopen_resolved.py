#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-findings.py script.

Tier 2 (direct import) tests with 2-3 subprocess tests for CLI plumbing.
"""


# Import toon_parser - conftest sets up PYTHONPATH
from _manage_findings_fixtures import (
    _add_ns,
    _qgate_add_ns,
    _qgate_query_ns,
    _qgate_resolve_ns,
    _query_ns,
    cmd_add,
    cmd_qgate_add,
    cmd_qgate_query,
    cmd_qgate_resolve,
    cmd_query,
)


def test_qgate_add_reopen_resolved(plan_context):
    """Re-adding a resolved finding with the SAME content discriminator reopens it."""
    add_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-dedup-reopen',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Missing coverage for utils.py',
            detail='utils.parse() has no test',
        )
    )
    assert add_result['status'] == 'success'
    hash_id = str(add_result['hash_id'])

    cmd_qgate_resolve(
        _qgate_resolve_ns(
            plan_id='qgate-dedup-reopen',
            hash_id=hash_id,
            resolution='taken_into_account',
            phase='3-outline',
            detail='Addressed',
        )
    )

    # Same title AND same detail → same discriminator → genuine re-detection → reopen.
    reopen_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-dedup-reopen',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Missing coverage for utils.py',
            detail='utils.parse() has no test',
        )
    )
    assert reopen_result['status'] == 'reopened'
    assert str(reopen_result['hash_id']) == hash_id

    query_result = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-dedup-reopen',
            phase='3-outline',
            resolution='pending',
        )
    )
    assert query_result['filtered_count'] == 1


def test_qgate_add_different_titles_not_deduped(plan_context):
    """Test that different titles create separate findings."""
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-dedup-diff',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Finding A',
            detail='d1',
        )
    )
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-dedup-diff',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Finding B',
            detail='d2',
        )
    )

    query_result = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-dedup-diff',
            phase='3-outline',
        )
    )
    assert query_result['total_count'] == 2


# =============================================================================
# Test: Content-discriminator dedup
# =============================================================================


def test_qgate_same_class_different_subject_not_reopened(plan_context):
    """A same-title finding with a DIFFERENT content discriminator never reopens a
    resolved sibling.
    """
    pid = 'qgate-diff-subject-noreopen'
    first = cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid,
            phase='5-execute',
            title='missing-null-check',
            detail='Foo.java:10 lacks a guard',
            file_path='Foo.java',
        )
    )
    assert first['status'] == 'success'
    resolved_hash = str(first['hash_id'])
    cmd_qgate_resolve(
        _qgate_resolve_ns(
            plan_id=pid,
            hash_id=resolved_hash,
            resolution='taken_into_account',
            phase='5-execute',
            detail='Guarded',
        )
    )

    # Same bare defect_class title, DIFFERENT subject (file/detail) → new finding, NOT reopen.
    second = cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid,
            phase='5-execute',
            title='missing-null-check',
            detail='Bar.java:22 lacks a guard',
            file_path='Bar.java',
        )
    )
    assert second['status'] == 'success'
    assert str(second['hash_id']) != resolved_hash

    # The originally-resolved finding stays resolved; only the new subject is pending.
    pending = cmd_qgate_query(_qgate_query_ns(plan_id=pid, phase='5-execute', resolution='pending'))
    assert pending['filtered_count'] == 1
    assert pending['findings'][0]['file_path'] == 'Bar.java'
    resolved = cmd_qgate_query(_qgate_query_ns(plan_id=pid, phase='5-execute', resolution='taken_into_account'))
    assert resolved['filtered_count'] == 1


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
