#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for _findings_core.py - the storage engine for findings and Q-Gate findings."""


from _findings_store_fixtures import (
    _SCRIPTS_DIR,
    QGATE_PERSIST_OK,
    _findings_core,
    _observed_qgate_statuses,
    add_qgate_finding,
    clear_qgate_findings,
    query_findings_unified,
    query_qgate_findings,
    resolve_qgate_finding,
    resolve_qgate_findings_by_evidence,
)


def test_qgate_reopen_resolved(plan_context):
    """Test Q-Gate reopens a resolved finding when the SAME defect is re-detected.

    Reopen fires only on a genuine re-detection — same title AND same content
    discriminator (detail/file/rule) as the resolved record. A same-title but
    different-content finding fails the discriminator match and is filed fresh
    instead of reopening the unrelated resolved record.
    """
    r1 = add_qgate_finding(
        'store-qgate-reopen',
        '5-execute',
        'qgate',
        'build-error',
        'Flaky test',
        'Detail',
    )
    resolve_qgate_finding('store-qgate-reopen', '5-execute', r1['hash_id'], 'fixed')

    r2 = add_qgate_finding(
        'store-qgate-reopen',
        '5-execute',
        'qgate',
        'build-error',
        'Flaky test',
        'Detail',
    )
    assert r2['status'] == 'reopened'
    assert r2['hash_id'] == r1['hash_id']


def test_query_qgate_findings(plan_context):
    """Test querying Q-Gate findings."""
    add_qgate_finding(
        'store-qgate-query',
        '5-execute',
        'qgate',
        'build-error',
        'Error 1',
        'Detail',
    )
    add_qgate_finding(
        'store-qgate-query',
        '5-execute',
        'user_review',
        'pr-comment',
        'Comment 1',
        'Detail',
    )

    result = query_qgate_findings('store-qgate-query', '5-execute')
    assert result['status'] == 'success'
    assert result['total_count'] == 2

    result = query_qgate_findings('store-qgate-query', '5-execute', source='qgate')
    assert result['filtered_count'] == 1


def test_resolve_qgate_finding(plan_context):
    """Test resolving a Q-Gate finding."""
    r = add_qgate_finding(
        'store-qgate-resolve',
        '5-execute',
        'qgate',
        'test-failure',
        'Test failure',
        'Detail',
    )

    result = resolve_qgate_finding(
        'store-qgate-resolve',
        '5-execute',
        r['hash_id'],
        'fixed',
        detail='Fixed it',
    )
    assert result['status'] == 'success'
    assert result['resolution'] == 'fixed'


def test_resolve_qgate_finding_rejected_is_valid(plan_context):
    """`rejected` is accepted as a valid Q-Gate resolution by the validator."""
    r = add_qgate_finding(
        'store-qgate-resolve-rejected',
        '5-execute',
        'qgate',
        'test-failure',
        'Refuted Q-Gate finding',
        'Detail',
    )

    result = resolve_qgate_finding(
        'store-qgate-resolve-rejected',
        '5-execute',
        r['hash_id'],
        'rejected',
        detail='Adversarially refuted at the verify stage',
    )
    assert result['status'] == 'success'
    assert result['resolution'] == 'rejected'


def test_rejected_qgate_finding_is_non_pending_in_unified_read(plan_context):
    """A `rejected` Q-Gate finding is non-blocking: excluded from the unified read.

    The findings-gate invariant in `query_findings_unified` merges ONLY pending
    Q-Gate records. A finding resolved to `rejected` is therefore treated as
    non-pending exactly like `fixed` / `accepted` — it never surfaces through the
    unified gate read and so does not block the gate.
    """
    pid = 'store-qgate-rejected-nonpending'
    pending = add_qgate_finding(
        pid, '5-execute', 'qgate', 'test-failure', 'Stays pending', 'Detail'
    )
    refuted = add_qgate_finding(
        pid, '5-execute', 'qgate', 'test-failure', 'Gets rejected', 'Detail'
    )
    resolve_qgate_finding(pid, '5-execute', refuted['hash_id'], 'rejected')

    unified = query_findings_unified(pid)

    assert unified['qgate_count'] == 1
    titles = {f['title'] for f in unified['findings']}
    assert titles == {'Stays pending'}
    assert pending['hash_id'] in {f['hash_id'] for f in unified['findings']}


# =============================================================================
# Test: resolve_qgate_findings_by_evidence (D3 — self-review loop-back resolution)
#
# A loop-back that lands a fix transitions the corresponding finding; a finding
# with no evidenced fix is left alone. Both directions are asserted — the second
# is the important one: a finding marked `fixed` without a landed change touching
# its file is strictly worse than one left `pending`.
# =============================================================================


def test_resolve_evidenced_transitions_finding_whose_file_changed(plan_context):
    """A pending finding whose file_path IS in the landed-fix set is resolved `fixed`."""
    pid = 'ev-resolve-changed'
    r = add_qgate_finding(
        pid, '6-finalize', 'qgate', 'bug', 'contract_drift at src/a.py:10', 'Detail',
        file_path='src/a.py',
    )

    result = resolve_qgate_findings_by_evidence(
        pid, '6-finalize', ['src/a.py'], evidence_sha='deadbeef'
    )

    assert result['status'] == 'success'
    assert [e['hash_id'] for e in result['resolved']] == [r['hash_id']]
    assert result['left_pending'] == []
    # The store reflects the transition.
    pending = query_qgate_findings(pid, '6-finalize', resolution='pending')
    assert pending['filtered_count'] == 0
    fixed = query_qgate_findings(pid, '6-finalize', resolution='fixed')
    assert fixed['filtered_count'] == 1
    assert 'deadbeef' in fixed['findings'][0]['resolution_detail']
    assert 'src/a.py' in fixed['findings'][0]['resolution_detail']


def test_resolve_evidenced_leaves_finding_whose_file_unchanged(plan_context):
    """THE important direction: a pending finding whose file_path is NOT in the
    landed-fix set is left `pending` — an unevidenced fix never auto-resolves."""
    pid = 'ev-resolve-unchanged'
    r = add_qgate_finding(
        pid, '6-finalize', 'qgate', 'bug', 'contract_drift at src/b.py:20', 'Detail',
        file_path='src/b.py',
    )

    # The landed fix touched a DIFFERENT file.
    result = resolve_qgate_findings_by_evidence(pid, '6-finalize', ['src/other.py'])

    assert result['status'] == 'success'
    assert result['resolved'] == []
    assert [e['hash_id'] for e in result['left_pending']] == [r['hash_id']]
    # The finding is untouched.
    pending = query_qgate_findings(pid, '6-finalize', resolution='pending')
    assert pending['filtered_count'] == 1
    assert pending['findings'][0]['hash_id'] == r['hash_id']


def test_resolve_evidenced_leaves_finding_with_no_file_path(plan_context):
    """A pending finding carrying no file_path cannot be evidenced — left `pending`."""
    pid = 'ev-resolve-no-file'
    add_qgate_finding(pid, '6-finalize', 'qgate', 'bug', 'defect with no file anchor', 'Detail')

    result = resolve_qgate_findings_by_evidence(pid, '6-finalize', ['src/anything.py'])

    assert result['status'] == 'success'
    assert result['resolved'] == []
    assert len(result['left_pending']) == 1
    assert query_qgate_findings(pid, '6-finalize', resolution='pending')['filtered_count'] == 1


def test_resolve_evidenced_mixed_batch_partitions_by_evidence(plan_context):
    """A batch resolves only the file-matched findings; the rest stay pending."""
    pid = 'ev-resolve-mixed'
    fixed_finding = add_qgate_finding(
        pid, '6-finalize', 'qgate', 'bug', 'defect at src/fixed.py:1', 'Detail',
        file_path='src/fixed.py',
    )
    kept_finding = add_qgate_finding(
        pid, '6-finalize', 'qgate', 'bug', 'defect at src/kept.py:1', 'Detail',
        file_path='src/kept.py',
    )

    result = resolve_qgate_findings_by_evidence(pid, '6-finalize', ['src/fixed.py'])

    assert [e['hash_id'] for e in result['resolved']] == [fixed_finding['hash_id']]
    assert [e['hash_id'] for e in result['left_pending']] == [kept_finding['hash_id']]


def test_resolve_evidenced_ignores_already_resolved_findings(plan_context):
    """A finding already resolved is neither re-resolved nor reported as pending."""
    pid = 'ev-resolve-already'
    r = add_qgate_finding(
        pid, '6-finalize', 'qgate', 'bug', 'defect at src/done.py:1', 'Detail',
        file_path='src/done.py',
    )
    resolve_qgate_finding(pid, '6-finalize', r['hash_id'], 'accepted')

    result = resolve_qgate_findings_by_evidence(pid, '6-finalize', ['src/done.py'])

    assert result['resolved'] == []
    assert result['left_pending'] == []
    # The accepted resolution is untouched (not overwritten to fixed).
    accepted = query_qgate_findings(pid, '6-finalize', resolution='accepted')
    assert accepted['filtered_count'] == 1


def test_resolve_evidenced_premature_resolution_is_self_correcting(plan_context):
    """A resolution the fix did not actually earn is corrected by the next round:
    re-detecting the same (title, discriminator) REOPENS the record to pending."""
    pid = 'ev-resolve-reopen'
    add_qgate_finding(
        pid, '6-finalize', 'qgate', 'bug', 'defect at src/c.py:5', 'Detail',
        file_path='src/c.py',
    )
    # The fix touched src/c.py, so evidence resolves it...
    resolve_qgate_findings_by_evidence(pid, '6-finalize', ['src/c.py'])
    assert query_qgate_findings(pid, '6-finalize', resolution='fixed')['filtered_count'] == 1

    # ...but the defect persisted, so the next round re-detects it → reopened.
    reopened = add_qgate_finding(
        pid, '6-finalize', 'qgate', 'bug', 'defect at src/c.py:5', 'Detail',
        file_path='src/c.py',
    )
    assert reopened['status'] == 'reopened'
    assert query_qgate_findings(pid, '6-finalize', resolution='pending')['filtered_count'] == 1


def test_resolve_evidenced_invalid_phase_errors(plan_context):
    """An invalid Q-Gate phase is rejected."""
    result = resolve_qgate_findings_by_evidence('ev-bad-phase', 'not-a-phase', ['x.py'])
    assert result['status'] == 'error'
    assert 'phase' in result['message'].lower()


def test_resolve_evidenced_failed_write_reported_as_pending_not_resolved(plan_context, monkeypatch):
    """A finding whose file matches the evidence but whose persistence WRITE fails
    is reported as still `pending`, never as `resolved` — claiming a resolution the
    store never recorded is the fail-open this evidence gate exists to prevent."""
    pid = 'ev-resolve-write-fail'
    r = add_qgate_finding(
        pid, '6-finalize', 'qgate', 'bug', 'defect at src/z.py:1', 'Detail',
        file_path='src/z.py',
    )
    # Simulate the record vanishing between the read and the update write.
    monkeypatch.setattr(_findings_core, 'update_jsonl', lambda *a, **k: False)

    result = resolve_qgate_findings_by_evidence(pid, '6-finalize', ['src/z.py'])

    assert result['status'] == 'success'
    assert result['resolved'] == [], (
        'A failed write must not be reported as a resolution — the finding is '
        'still pending.'
    )
    assert [e['hash_id'] for e in result['left_pending']] == [r['hash_id']]


def test_clear_qgate_findings(plan_context):
    """Test clearing all Q-Gate findings for a phase."""
    add_qgate_finding(
        'store-qgate-clear',
        '5-execute',
        'qgate',
        'build-error',
        'Error 1',
        'Detail',
    )
    add_qgate_finding(
        'store-qgate-clear',
        '5-execute',
        'qgate',
        'test-failure',
        'Error 2',
        'Detail',
    )

    result = clear_qgate_findings('store-qgate-clear', '5-execute')
    assert result['status'] == 'success'
    assert result['cleared'] == 2

    query = query_qgate_findings('store-qgate-clear', '5-execute')
    assert query['total_count'] == 0


def test_clear_qgate_findings_empty(plan_context):
    """Test clearing Q-Gate findings when none exist."""
    result = clear_qgate_findings('store-qgate-clear-empty', '5-execute')
    assert result['status'] == 'success'
    assert result['cleared'] == 0


def test_script_source_uses_canonical_local_plans_path():
    """The script source references .plan/local/plans, not the legacy form.

    Regression guard for the path-consolidation sweep: the module docstring's
    Storage block and the ``get_findings_dir`` / ``get_findings_path`` /
    ``get_qgate_path`` / ``get_assessments_path`` docstrings must spell the
    findings location as ``.plan/local/plans/`` — the legacy bare
    ``.plan/plans/`` form is incorrect since runtime state moved under
    ``.plan/local``.
    """
    import re

    source = (_SCRIPTS_DIR / '_findings_core.py').read_text(encoding='utf-8')
    assert '.plan/local/plans/' in source
    legacy = re.findall(r'(?<!local/)\.plan/plans/', source)
    assert legacy == [], f'Legacy .plan/plans/ strings remain: {legacy}'


def test_qgate_persist_ok_admits_every_in_store_outcome(plan_context):
    """The three outcomes that leave the record IN the store are all members."""
    observed = _observed_qgate_statuses('store-qgate-partition-ok')

    assert observed['fresh'] in QGATE_PERSIST_OK
    assert observed['dedup'] in QGATE_PERSIST_OK
    assert observed['reopened'] in QGATE_PERSIST_OK


def test_qgate_persist_ok_excludes_the_rejection_outcome(plan_context):
    """A REJECTED persist is outside the set — it must never read as benign."""
    observed = _observed_qgate_statuses('store-qgate-partition-reject')

    assert observed['rejected'] not in QGATE_PERSIST_OK
    assert observed['rejected'] != observed['dedup'], (
        'a rejection must not collapse onto the benign deduplicated outcome'
    )


def test_qgate_persist_ok_partitions_the_outcome_space_exactly(plan_context):
    """The set is exactly the in-store outcomes — no more, no less.

    Derived both ways: every observed in-store outcome is a member, and the set
    carries no member the primitive never produces, so an extra value silently
    added to ``QGATE_PERSIST_OK`` (which would re-admit a rejection) fails here.
    """
    observed = _observed_qgate_statuses('store-qgate-partition-exact')

    in_store = {observed['fresh'], observed['dedup'], observed['reopened']}
    assert set(QGATE_PERSIST_OK) == in_store
