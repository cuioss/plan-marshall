#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for _findings_core.py - the storage engine for findings and Q-Gate findings."""


from _findings_store_fixtures import (
    add_finding,
    get_finding,
    mark_finding_responded,
    query_findings,
    resolve_finding,
    resolve_findings_by_type,
)


def test_resolve_findings_by_type_accepts_rejected(plan_context):
    """Bulk resolve accepts `rejected` as a valid target resolution."""
    add_finding('store-bulk-rejected', 'lint-issue', 'Lint 1', 'Detail')
    add_finding('store-bulk-rejected', 'lint-issue', 'Lint 2', 'Detail')

    result = resolve_findings_by_type('store-bulk-rejected', ('lint-issue',), 'rejected')

    assert result['status'] == 'success'
    assert result['resolved_count'] == 2

    rejected = query_findings('store-bulk-rejected', finding_type='lint-issue', resolution='rejected')
    assert rejected['filtered_count'] == 2
    pending = query_findings('store-bulk-rejected', finding_type='lint-issue', resolution='pending')
    assert pending['filtered_count'] == 0


# =============================================================================
# Test: resolve_findings_by_type (bulk resolve)
# =============================================================================


def test_resolve_findings_by_type_bulk_count(plan_context):
    """Bulk-resolving all pending findings of a type returns the correct count."""
    add_finding('store-bulk-count', 'bug', 'Bug 1', 'Detail')
    add_finding('store-bulk-count', 'bug', 'Bug 2', 'Detail')
    add_finding('store-bulk-count', 'bug', 'Bug 3', 'Detail')

    result = resolve_findings_by_type('store-bulk-count', ('bug',), 'fixed')
    assert result['status'] == 'success'
    assert result['resolved_count'] == 3
    assert len(result['hash_ids']) == 3

    pending = query_findings('store-bulk-count', finding_type='bug', resolution='pending')
    assert pending['filtered_count'] == 0
    resolved = query_findings('store-bulk-count', finding_type='bug', resolution='fixed')
    assert resolved['filtered_count'] == 3


def test_resolve_findings_by_type_leaves_other_types(plan_context):
    """Findings not matching the type predicate are left unresolved."""
    add_finding('store-bulk-other', 'bug', 'Bug 1', 'Detail')
    add_finding('store-bulk-other', 'bug', 'Bug 2', 'Detail')
    add_finding('store-bulk-other', 'improvement', 'Improve 1', 'Detail')

    result = resolve_findings_by_type('store-bulk-other', ('bug',), 'fixed')
    assert result['status'] == 'success'
    assert result['resolved_count'] == 2

    pending_improve = query_findings(
        'store-bulk-other', finding_type='improvement', resolution='pending'
    )
    assert pending_improve['filtered_count'] == 1


def test_resolve_findings_by_type_skips_already_resolved(plan_context):
    """An already-resolved finding is not double-counted on a subsequent bulk resolve."""
    r1 = add_finding('store-bulk-dup', 'bug', 'Bug 1', 'Detail')
    add_finding('store-bulk-dup', 'bug', 'Bug 2', 'Detail')

    resolve_finding('store-bulk-dup', r1['hash_id'], 'fixed')

    result = resolve_findings_by_type('store-bulk-dup', ('bug',), 'fixed')
    assert result['status'] == 'success'
    assert result['resolved_count'] == 1
    assert r1['hash_id'] not in result['hash_ids']


def test_resolve_findings_by_type_empty_when_no_match(plan_context):
    """Bulk resolve returns a zero count when no findings match the type predicate."""
    add_finding('store-bulk-empty', 'improvement', 'Improve 1', 'Detail')

    result = resolve_findings_by_type('store-bulk-empty', ('bug',), 'fixed')
    assert result['status'] == 'success'
    assert result['resolved_count'] == 0
    assert result['hash_ids'] == []


def test_resolve_findings_by_type_multiple_types(plan_context):
    """Bulk resolve spans multiple finding types in a single call."""
    add_finding('store-bulk-multi', 'bug', 'Bug 1', 'Detail')
    add_finding('store-bulk-multi', 'improvement', 'Improve 1', 'Detail')
    add_finding('store-bulk-multi', 'tip', 'Tip 1', 'Detail')

    result = resolve_findings_by_type('store-bulk-multi', ('bug', 'improvement'), 'fixed')
    assert result['status'] == 'success'
    assert result['resolved_count'] == 2

    pending_tip = query_findings('store-bulk-multi', finding_type='tip', resolution='pending')
    assert pending_tip['filtered_count'] == 1


def test_resolve_findings_by_type_invalid_resolution(plan_context):
    """An invalid target resolution returns the canonical error shape without mutating state."""
    add_finding('store-bulk-badres', 'bug', 'Bug 1', 'Detail')

    result = resolve_findings_by_type('store-bulk-badres', ('bug',), 'not-a-resolution')
    assert result['status'] == 'error'
    assert 'Invalid resolution' in result['message']

    pending = query_findings('store-bulk-badres', finding_type='bug', resolution='pending')
    assert pending['filtered_count'] == 1, 'invalid resolution must leave the finding unmutated'


def test_resolve_findings_by_type_custom_from_resolution(plan_context):
    """Bulk resolve can re-resolve findings matching a non-default from_resolution."""
    r1 = add_finding('store-bulk-from', 'bug', 'Bug 1', 'Detail')
    add_finding('store-bulk-from', 'bug', 'Bug 2', 'Detail')

    resolve_finding('store-bulk-from', r1['hash_id'], 'accepted')

    result = resolve_findings_by_type(
        'store-bulk-from', ('bug',), 'fixed', from_resolution='accepted'
    )
    assert result['status'] == 'success'
    assert result['resolved_count'] == 1
    assert result['hash_ids'] == [r1['hash_id']]


def test_resolve_findings_by_type_without_detail_preserves_existing_resolution_detail(plan_context):
    """A bulk resolve with ``detail=None`` must not erase a recorded detail.

    Regression guard. The bulk path built its update dict as
    ``{'resolution': ..., 'resolution_detail': detail}`` unconditionally, so
    omitting ``detail`` wrote a literal ``None`` over whatever the earlier
    single-finding resolve had recorded — silently destroying the audit trail
    that explained WHY the finding had been resolved. ``resolve_finding`` has
    always guarded the field behind ``if detail:``; the bulk counterpart now
    matches it.

    The data loss is invisible at the call site: ``resolved_count`` is
    identical either way, so nothing in the return value reveals that a
    populated field was overwritten with nothing.
    """
    r1 = add_finding('store-bulk-keepdetail', 'bug', 'Bug 1', 'Detail')
    resolve_finding(
        'store-bulk-keepdetail', r1['hash_id'], 'accepted', detail='Accepted: known trade-off'
    )

    # Bulk-resolve WITHOUT a detail argument.
    result = resolve_findings_by_type(
        'store-bulk-keepdetail', ('bug',), 'fixed', from_resolution='accepted'
    )
    assert result['status'] == 'success'
    assert result['resolved_count'] == 1

    resolved = query_findings('store-bulk-keepdetail', finding_type='bug', resolution='fixed')
    assert resolved['filtered_count'] == 1
    record = resolved['findings'][0]
    # The resolution advanced ...
    assert record['resolution'] == 'fixed'
    # ... but the pre-existing detail survived it.
    assert record['resolution_detail'] == 'Accepted: known trade-off'


def test_resolve_findings_by_type_with_detail_still_overwrites(plan_context):
    """Positive control: an explicitly supplied detail is still written.

    Pairs with the preservation guard above. Without this case, an
    implementation that dropped ``resolution_detail`` from the update dict
    altogether would satisfy the preservation test while silently discarding
    every detail a caller DID pass.
    """
    r1 = add_finding('store-bulk-setdetail', 'bug', 'Bug 1', 'Detail')
    resolve_finding('store-bulk-setdetail', r1['hash_id'], 'accepted', detail='Original reason')

    result = resolve_findings_by_type(
        'store-bulk-setdetail', ('bug',), 'fixed', detail='Superseded by bulk fix',
        from_resolution='accepted',
    )
    assert result['status'] == 'success'
    assert result['resolved_count'] == 1

    resolved = query_findings('store-bulk-setdetail', finding_type='bug', resolution='fixed')
    record = resolved['findings'][0]
    assert record['resolution_detail'] == 'Superseded by bulk fix'


def test_resolve_findings_by_type_clears_responded_marker_on_change(plan_context):
    """The bulk resolve path clears the marker on a disposition change, like resolve_finding.

    Guards the two entry points against drifting apart: a bulk re-decide of an
    already-transmitted finding must invalidate its marker, or a changed
    disposition would be silently suppressed through the bulk door.
    """
    r = add_finding('store-responded-bulk', 'pr-comment', 'C', 'detail')
    hash_id = r['hash_id']
    resolve_finding('store-responded-bulk', hash_id, 'accepted', detail='Accepted: original.')
    mark_finding_responded('store-responded-bulk', hash_id)
    assert get_finding('store-responded-bulk', hash_id)['responded'] is True

    result = resolve_findings_by_type(
        'store-responded-bulk', ('pr-comment',), 'rejected', from_resolution='accepted'
    )
    assert result['resolved_count'] == 1
    reread = get_finding('store-responded-bulk', hash_id)
    assert reread['resolution'] == 'rejected'
    assert reread['responded'] is False
    assert reread['responded_at'] is None
