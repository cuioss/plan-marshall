#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-findings.py script."""


from _manage_findings_fixtures import (
    _qgate_add_ns,
    _qgate_clear_ns,
    _qgate_query_ns,
    _qgate_resolve_ns,
    cmd_qgate_add,
    cmd_qgate_clear,
    cmd_qgate_query,
    cmd_qgate_resolve,
)

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
# Test: Q-Gate Deduplication
# =============================================================================


def test_qgate_add_dedup_pending(plan_context):
    """Same title AND same content discriminator dedups to a single pending record."""
    result1 = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-dedup-pend',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Missing assessment for helper.py',
            detail='helper.py is consumer-only',
        )
    )
    assert result1['status'] == 'success'
    original_hash = str(result1['hash_id'])

    # Same title AND same detail/file_path/rule → same discriminator → dedup.
    result2 = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-dedup-pend',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Missing assessment for helper.py',
            detail='helper.py is consumer-only',
        )
    )
    assert result2['status'] == 'deduplicated'
    assert str(result2['hash_id']) == original_hash

    query_result = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-dedup-pend',
            phase='3-outline',
        )
    )
    assert query_result['total_count'] == 1


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
