#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-findings.py script."""


from _manage_findings_fixtures import (
    _add_ns,
    _parse_raw_input,
    _qgate_add_ns,
    _qgate_clear_ns,
    _qgate_query_ns,
    _qgate_resolve_ns,
    _query_ns,
    _RawInputError,
    cmd_add,
    cmd_qgate_add,
    cmd_qgate_clear,
    cmd_qgate_query,
    cmd_qgate_resolve,
    cmd_query,
)

# =============================================================================
# Test: Q-Gate Query Command
# =============================================================================

def test_qgate_per_phase_isolation(plan_context):
    """Test that Q-Gate findings are isolated per phase."""
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-phase-iso',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Phase 3 finding',
            detail='d',
        )
    )
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-phase-iso',
            phase='4-plan',
            source='qgate',
            type='triage',
            title='Phase 4 finding',
            detail='d',
        )
    )

    result = cmd_qgate_query(_qgate_query_ns(plan_id='qgate-phase-iso', phase='3-outline'))
    assert result['total_count'] == 1
    assert result['phase'] == '3-outline'

    result = cmd_qgate_query(_qgate_query_ns(plan_id='qgate-phase-iso', phase='4-plan'))
    assert result['total_count'] == 1
    assert result['phase'] == '4-plan'


# =============================================================================
# Test: Q-Gate Resolve Command
# =============================================================================


def test_qgate_resolve_taken_into_account(plan_context):
    """Test resolving a Q-Gate finding with taken_into_account."""
    add_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-resolve-tia',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Missing coverage',
            detail='File X not covered',
        )
    )
    hash_id = str(add_result['hash_id'])

    result = cmd_qgate_resolve(
        _qgate_resolve_ns(
            plan_id='qgate-resolve-tia',
            hash_id=hash_id,
            resolution='taken_into_account',
            phase='3-outline',
            detail='Added file X to deliverable 2',
        )
    )
    assert result['status'] == 'success'
    assert result['resolution'] == 'taken_into_account'


def test_qgate_resolve_all_statuses(plan_context):
    """Test all resolution statuses for Q-Gate findings."""
    resolutions = ['pending', 'fixed', 'suppressed', 'accepted', 'taken_into_account', 'rejected']
    for res in resolutions:
        add_result = cmd_qgate_add(
            _qgate_add_ns(
                plan_id='qgate-resolve-all-st',
                phase='5-execute',
                source='qgate',
                type='triage',
                title=f'Finding for {res}',
                detail='d',
            )
        )
        assert add_result['status'] == 'success', f'Add failed for {res}'
        hash_id = str(add_result['hash_id'])

        result = cmd_qgate_resolve(
            _qgate_resolve_ns(
                plan_id='qgate-resolve-all-st',
                hash_id=hash_id,
                resolution=res,
                phase='5-execute',
            )
        )
        assert result['status'] == 'success', f'Failed for resolution {res}'


# =============================================================================
# Test: Q-Gate Clear Command
# =============================================================================


def test_qgate_clear(plan_context):
    """Test clearing Q-Gate findings for a phase."""
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-clear',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Finding 1',
            detail='d',
        )
    )
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-clear',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Finding 2',
            detail='d',
        )
    )

    result = cmd_qgate_clear(_qgate_clear_ns(plan_id='qgate-clear', phase='3-outline'))
    assert result['status'] == 'success'
    assert result['cleared'] == 2

    query_result = cmd_qgate_query(_qgate_query_ns(plan_id='qgate-clear', phase='3-outline'))
    assert query_result['total_count'] == 0


def test_qgate_clear_empty(plan_context):
    """Test clearing when no Q-Gate findings exist."""
    result = cmd_qgate_clear(_qgate_clear_ns(plan_id='qgate-clear-empty', phase='3-outline'))
    assert result['status'] == 'success'
    assert result['cleared'] == 0


def test_qgate_user_review_source(plan_context):
    """Test that user_review findings work end-to-end."""
    add_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-user-review',
            phase='3-outline',
            source='user_review',
            type='triage',
            title='User: scope too narrow',
            detail='Please include module Y in the deliverables',
        )
    )
    assert add_result['status'] == 'success'
    hash_id = str(add_result['hash_id'])

    query_result = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-user-review',
            phase='3-outline',
            source='user_review',
        )
    )
    assert query_result['filtered_count'] == 1

    resolve_result = cmd_qgate_resolve(
        _qgate_resolve_ns(
            plan_id='qgate-user-review',
            hash_id=hash_id,
            resolution='taken_into_account',
            phase='3-outline',
            detail='Added module Y to deliverable scope',
        )
    )
    assert resolve_result['status'] == 'success'

    verify_result = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-user-review',
            phase='3-outline',
            resolution='pending',
        )
    )
    assert verify_result['filtered_count'] == 0


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
