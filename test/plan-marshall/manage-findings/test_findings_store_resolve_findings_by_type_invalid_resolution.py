#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for _findings_core.py - the storage engine for findings and Q-Gate findings."""


from _findings_store_fixtures import (
    add_finding,
    add_qgate_finding,
    get_finding,
    mark_finding_responded,
    promote_finding,
    query_findings,
    resolve_finding,
    resolve_findings_by_type,
)


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


# =============================================================================
# Test: responded-marker lifecycle (the RESPOND idempotency key)
#
# The provider RESPOND verbs stamp a `responded` marker after transmitting a
# reply, and skip a finding that already carries it. Re-resolving a finding to a
# DIFFERENT disposition must clear the marker so the corrected decision goes out
# again; an unchanged re-resolve must preserve it so the already-sent reply is
# not re-sent. That clearing is what makes the idempotency a per-(finding,
# disposition) key rather than a permanent suppression, and it must hold at BOTH
# resolve entry points.
# =============================================================================


def test_resolve_finding_clears_responded_marker_on_changed_disposition(plan_context):
    """A resolution or reply-body change clears a stale transmission marker."""
    r = add_finding('store-responded-change', 'pr-comment', 'C', 'detail')
    hash_id = r['hash_id']
    resolve_finding('store-responded-change', hash_id, 'accepted', detail='Accepted: original.')
    mark_finding_responded('store-responded-change', hash_id)
    assert get_finding('store-responded-change', hash_id)['responded'] is True

    # A changed resolution AND body — the marker must be cleared.
    resolve_finding('store-responded-change', hash_id, 'rejected', detail='Rejected: reconsidered.')
    reread = get_finding('store-responded-change', hash_id)
    assert reread['responded'] is False
    assert reread['responded_at'] is None


def test_resolve_finding_keeps_responded_marker_on_unchanged_reresolve(plan_context):
    """An idempotent re-resolve (same disposition) must NOT clear the marker.

    Otherwise the already-sent reply would be needlessly re-transmitted — the very
    defect the marker exists to prevent.
    """
    r = add_finding('store-responded-noop', 'pr-comment', 'C', 'detail')
    hash_id = r['hash_id']
    resolve_finding('store-responded-noop', hash_id, 'accepted', detail='Accepted: same.')
    mark_finding_responded('store-responded-noop', hash_id)

    # Same resolution, same detail — nothing changed, the marker holds.
    resolve_finding('store-responded-noop', hash_id, 'accepted', detail='Accepted: same.')
    assert get_finding('store-responded-noop', hash_id)['responded'] is True

    # Same resolution, detail omitted (None) — also a no-op for the marker.
    resolve_finding('store-responded-noop', hash_id, 'accepted')
    assert get_finding('store-responded-noop', hash_id)['responded'] is True


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


# =============================================================================
# Test: promote_finding
# =============================================================================


def test_promote_finding_success(plan_context):
    """Test promoting a finding."""
    r = add_finding('store-promote', 'bug', 'Bug', 'Detail')
    hash_id = r['hash_id']

    result = promote_finding('store-promote', hash_id, 'manage-lessons')
    assert result['status'] == 'success'
    assert result['promoted_to'] == 'manage-lessons'

    query = query_findings('store-promote', promoted=True)
    assert query['filtered_count'] == 1


# =============================================================================
# Test: Q-Gate findings
# =============================================================================


def test_add_qgate_finding_basic(plan_context):
    """Test adding a Q-Gate finding."""
    result = add_qgate_finding(
        'store-qgate-add',
        '5-execute',
        'qgate',
        'build-error',
        'Build failure',
        'Compilation failed',
    )
    assert result['status'] == 'success'
    assert 'hash_id' in result
    assert result['phase'] == '5-execute'


def test_add_qgate_finding_invalid_phase(plan_context):
    """Test adding Q-Gate finding with invalid phase."""
    result = add_qgate_finding(
        'store-qgate-badphase',
        '1-init',
        'qgate',
        'build-error',
        'Title',
        'Detail',
    )
    assert result['status'] == 'error'
    assert 'Invalid Q-Gate phase' in result['message']


def test_add_qgate_finding_invalid_source(plan_context):
    """Test adding Q-Gate finding with invalid source."""
    result = add_qgate_finding(
        'store-qgate-badsrc',
        '5-execute',
        'invalid-source',
        'build-error',
        'Title',
        'Detail',
    )
    assert result['status'] == 'error'
    assert 'Invalid Q-Gate source' in result['message']


def test_qgate_dedup_pending(plan_context):
    """Test Q-Gate deduplication for pending findings with same title AND content.

    Dedup keys on the (title, content-discriminator) pair — a bare title
    collision alone is no longer enough. A genuine re-detection of the same
    defect carries the SAME title AND the SAME content (detail/file/rule), so
    the discriminator matches and the second add collapses onto the first.
    """
    r1 = add_qgate_finding(
        'store-qgate-dedup',
        '5-execute',
        'qgate',
        'build-error',
        'Same title',
        'Same detail',
    )
    assert r1['status'] == 'success'

    r2 = add_qgate_finding(
        'store-qgate-dedup',
        '5-execute',
        'qgate',
        'build-error',
        'Same title',
        'Same detail',
    )
    assert r2['status'] == 'deduplicated'
    assert r2['hash_id'] == r1['hash_id']
