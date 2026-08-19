#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for _findings_core.py - the storage engine for findings and Q-Gate findings."""


from _findings_store_fixtures import add_qgate_finding_checked, query_qgate_findings, resolve_qgate_finding

# =============================================================================
# Test: add_qgate_finding_checked — the centralized persist+partition helper
# =============================================================================
#
# add_qgate_finding_checked wraps add_qgate_finding and partitions its status
# into (hash_id, failure_descriptor). It centralizes the QGATE_PERSIST_OK
# membership check that github_pr/gitlab_pr/sonar previously each duplicated.
# These tests drive the REAL primitive (never a stub) through both halves of
# that partition.


def test_add_qgate_finding_checked_success_yields_hash_id_no_failure(plan_context):
    """A fresh `success` persist yields a hash_id and no failure descriptor."""
    hash_id, failure = add_qgate_finding_checked(
        'store-qgate-checked-success',
        '5-execute',
        'qgate',
        'build-error',
        'Checked probe',
        'Detail',
    )

    assert hash_id is not None
    assert failure is None

    stored = query_qgate_findings('store-qgate-checked-success', '5-execute')
    assert stored['filtered_count'] == 1
    assert stored['findings'][0]['hash_id'] == hash_id


def test_add_qgate_finding_checked_deduplicated_yields_hash_id_no_failure(plan_context):
    """A `deduplicated` persist outcome (identical pending record) still yields
    the existing hash_id and no failure descriptor."""
    pid = 'store-qgate-checked-dedup'
    first_hash, first_failure = add_qgate_finding_checked(
        pid, '5-execute', 'qgate', 'build-error', 'Dup probe', 'Detail',
    )
    assert first_failure is None

    second_hash, second_failure = add_qgate_finding_checked(
        pid, '5-execute', 'qgate', 'build-error', 'Dup probe', 'Detail',
    )

    assert second_hash == first_hash
    assert second_failure is None


def test_add_qgate_finding_checked_reopened_yields_hash_id_no_failure(plan_context):
    """A `reopened` persist outcome (same defect re-detected after resolution)
    yields the reopened hash_id and no failure descriptor."""
    pid = 'store-qgate-checked-reopen'
    first_hash, _ = add_qgate_finding_checked(
        pid, '5-execute', 'qgate', 'build-error', 'Reopen probe', 'Detail',
    )
    resolve_qgate_finding(pid, '5-execute', first_hash, 'fixed')

    second_hash, second_failure = add_qgate_finding_checked(
        pid, '5-execute', 'qgate', 'build-error', 'Reopen probe', 'Detail',
    )

    assert second_hash == first_hash
    assert second_failure is None


def test_add_qgate_finding_checked_rejected_yields_failure_descriptor(plan_context):
    """A rejected persist (invalid finding type) yields (None, failure), where
    `failure` carries the finding's own title/detail plus the primitive's
    rejection message — never silently folded into a benign zero."""
    hash_id, failure = add_qgate_finding_checked(
        'store-qgate-checked-rejected',
        '5-execute',
        'qgate',
        'not-a-finding-type',
        'Rejected probe',
        'Detail',
    )

    assert hash_id is None
    assert failure is not None
    assert failure['title'] == 'Rejected probe'
    assert failure['detail'] == 'Detail'
    assert 'Invalid finding type' in failure['message']

    stored = query_qgate_findings('store-qgate-checked-rejected', '5-execute')
    assert stored['filtered_count'] == 0
