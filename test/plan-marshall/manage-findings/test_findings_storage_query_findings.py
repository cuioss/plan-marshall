#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Storage-layout tests for the per-type findings JSONL split.

Its sections, in order:

* Query merging: query_findings concatenates every per-type file
* Filter-after-merge: type, resolution, promoted, file_pattern
* Hash-id-only operations: locate the owning per-type file
"""


from _findings_storage_fixtures import (
    add_assessment,
    add_finding,
    add_qgate_finding,
    get_assessments_path,
    get_finding,
    get_findings_path,
    mark_finding_responded,
    promote_finding,
    query_findings,
    resolve_finding,
)

# Plan ids this module's tests file findings against. The autouse
# ``_materialize_declared_plan_dirs`` fixture in ``test/conftest.py`` creates
# ``plans/{plan_id}/`` for each, because every findings surface REFUSES a plan
# directory that is absent under the resolved root — in production the
# lifecycle creates that directory before anything is filed against it.
PLAN_IDS = (
    'storage-assess-route',
    'storage-filter-file',
    'storage-filter-multitype',
    'storage-filter-promoted',
    'storage-filter-resolution',
    'storage-filter-type',
    'storage-get-locate',
    'storage-promote-locate',
    'storage-query-hash',
    'storage-query-isolate',
    'storage-query-merge',
    'storage-reject-locate',
    'storage-resolve-locate',
    'storage-resolve-missing',
    'storage-responded-mark',
    'storage-responded-missing',
)


def test_assessment_writes_to_assessments_file(plan_context):
    """`add_assessment` creates `findings/assessments.jsonl` only."""
    assess_path = get_assessments_path('storage-assess-route')
    bug_path = get_findings_path('storage-assess-route', 'bug')

    add_assessment(
        'storage-assess-route',
        'docs/architecture.md',
        'CERTAIN_INCLUDE',
        85,
    )

    assert assess_path.exists()
    assert assess_path.name == 'assessments.jsonl'
    assert not bug_path.exists()


# =============================================================================
# Query merging: query_findings concatenates every per-type file
# =============================================================================


def test_query_findings_merges_across_per_type_files(plan_context):
    """Query returns the union of every per-type file."""
    add_finding('storage-query-merge', 'bug', 'Bug X', 'Detail')
    add_finding('storage-query-merge', 'improvement', 'Improve X', 'Detail')
    add_finding('storage-query-merge', 'tip', 'Tip X', 'Detail')
    add_finding('storage-query-merge', 'sonar-issue', 'S1234', 'Detail')

    result = query_findings('storage-query-merge')

    assert result['status'] == 'success'
    assert result['total_count'] == 4
    assert result['filtered_count'] == 4
    seen_types = sorted({r['type'] for r in result['findings']})
    assert seen_types == ['bug', 'improvement', 'sonar-issue', 'tip']


def test_query_findings_ignores_qgate_and_assessment_files(plan_context):
    """Q-Gate and assessment records must not leak into `query_findings`."""
    add_finding('storage-query-isolate', 'bug', 'Plan bug', 'Detail')
    add_qgate_finding(
        'storage-query-isolate',
        '5-execute',
        'qgate',
        'build-error',
        'Phase bug',
        'Detail',
    )
    add_assessment('storage-query-isolate', 'x.md', 'CERTAIN_INCLUDE', 80)

    result = query_findings('storage-query-isolate')

    assert result['total_count'] == 1
    assert result['findings'][0]['title'] == 'Plan bug'


def test_query_findings_hash_id_space_is_stable_across_split(plan_context):
    """Every merged record exposes a hash_id; ids are unique across files."""
    r1 = add_finding('storage-query-hash', 'bug', 'Bug 1', 'Detail')
    r2 = add_finding('storage-query-hash', 'improvement', 'Improve 1', 'Detail')
    r3 = add_finding('storage-query-hash', 'tip', 'Tip 1', 'Detail')

    merged = query_findings('storage-query-hash')['findings']
    merged_ids = sorted(r['hash_id'] for r in merged)

    assert merged_ids == sorted([r1['hash_id'], r2['hash_id'], r3['hash_id']])
    assert len(set(merged_ids)) == 3


# =============================================================================
# Filter-after-merge: type, resolution, promoted, file_pattern
# =============================================================================


def test_query_findings_type_filter_after_merge(plan_context):
    """`finding_type` filter narrows merged records to one type."""
    add_finding('storage-filter-type', 'bug', 'Bug 1', 'Detail')
    add_finding('storage-filter-type', 'bug', 'Bug 2', 'Detail')
    add_finding('storage-filter-type', 'improvement', 'Improve 1', 'Detail')

    result = query_findings('storage-filter-type', finding_type='bug')

    assert result['total_count'] == 3
    assert result['filtered_count'] == 2
    assert all(r['type'] == 'bug' for r in result['findings'])


def test_query_findings_comma_separated_type_filter_after_merge(plan_context):
    """Comma-separated type filter spans multiple per-type files."""
    add_finding('storage-filter-multitype', 'bug', 'Bug 1', 'Detail')
    add_finding('storage-filter-multitype', 'improvement', 'Improve 1', 'Detail')
    add_finding('storage-filter-multitype', 'tip', 'Tip 1', 'Detail')

    result = query_findings('storage-filter-multitype', finding_type='bug,improvement')

    assert result['filtered_count'] == 2
    seen = sorted(r['type'] for r in result['findings'])
    assert seen == ['bug', 'improvement']


def test_query_findings_resolution_filter_after_merge(plan_context):
    """Resolution filter applies after the per-type files are merged."""
    r1 = add_finding('storage-filter-resolution', 'bug', 'Bug 1', 'Detail')
    add_finding('storage-filter-resolution', 'improvement', 'Improve 1', 'Detail')
    resolve_finding('storage-filter-resolution', r1['hash_id'], 'fixed')

    pending = query_findings('storage-filter-resolution', resolution='pending')
    fixed = query_findings('storage-filter-resolution', resolution='fixed')

    assert pending['filtered_count'] == 1
    assert pending['findings'][0]['type'] == 'improvement'
    assert fixed['filtered_count'] == 1
    assert fixed['findings'][0]['type'] == 'bug'


def test_query_findings_promoted_filter_after_merge(plan_context):
    """`promoted=True` filter spans every per-type file."""
    r_bug = add_finding('storage-filter-promoted', 'bug', 'Bug 1', 'Detail')
    add_finding('storage-filter-promoted', 'improvement', 'Improve 1', 'Detail')
    promote_finding('storage-filter-promoted', r_bug['hash_id'], 'manage-lessons')

    promoted = query_findings('storage-filter-promoted', promoted=True)
    unpromoted = query_findings('storage-filter-promoted', promoted=False)

    assert promoted['filtered_count'] == 1
    assert promoted['findings'][0]['hash_id'] == r_bug['hash_id']
    assert unpromoted['filtered_count'] == 1
    assert unpromoted['findings'][0]['type'] == 'improvement'


def test_query_findings_file_pattern_filter_after_merge(plan_context):
    """File-pattern filter spans every per-type file."""
    add_finding(
        'storage-filter-file',
        'bug',
        'Bug 1',
        'Detail',
        file_path='src/main/Foo.py',
    )
    add_finding(
        'storage-filter-file',
        'improvement',
        'Improve 1',
        'Detail',
        file_path='src/test/FooTest.py',
    )
    add_finding(
        'storage-filter-file',
        'tip',
        'Tip 1',
        'Detail',
        file_path='src/main/Bar.py',
    )

    result = query_findings('storage-filter-file', file_pattern='src/main/*')

    assert result['filtered_count'] == 2
    seen_paths = sorted(r['file_path'] for r in result['findings'])
    assert seen_paths == ['src/main/Bar.py', 'src/main/Foo.py']


# =============================================================================
# Hash-id-only operations: locate the owning per-type file
# =============================================================================


def test_get_finding_locates_record_in_owning_per_type_file(plan_context):
    """`get_finding` finds a record in a non-default per-type file by hash_id."""
    add_finding('storage-get-locate', 'bug', 'Decoy bug', 'Detail')
    target = add_finding(
        'storage-get-locate',
        'sonar-issue',
        'Sonar finding',
        'Detail',
        file_path='src/x.py',
    )

    result = get_finding('storage-get-locate', target['hash_id'])

    assert result['status'] == 'success'
    assert result['hash_id'] == target['hash_id']
    assert result['type'] == 'sonar-issue'
    assert result['title'] == 'Sonar finding'


def test_resolve_finding_writes_back_to_owning_per_type_file(plan_context):
    """`resolve_finding` updates only the per-type file containing the hash."""
    bug_path = get_findings_path('storage-resolve-locate', 'bug')
    sonar_path = get_findings_path('storage-resolve-locate', 'sonar-issue')

    add_finding('storage-resolve-locate', 'bug', 'Untouched bug', 'Detail')
    target = add_finding('storage-resolve-locate', 'sonar-issue', 'Sonar', 'Detail')

    outcome = resolve_finding('storage-resolve-locate', target['hash_id'], 'fixed', detail='Fix me')

    assert outcome['status'] == 'success'
    assert outcome['resolution'] == 'fixed'

    bug_lines = bug_path.read_text(encoding='utf-8').splitlines()
    sonar_lines = sonar_path.read_text(encoding='utf-8').splitlines()
    assert len(bug_lines) == 1
    assert '"resolution": "pending"' in bug_lines[0]
    assert len(sonar_lines) == 1
    assert '"resolution": "fixed"' in sonar_lines[0]
    assert '"resolution_detail": "Fix me"' in sonar_lines[0]


def test_resolve_finding_rejected_writes_back_to_owning_per_type_file(plan_context):
    """`resolve_finding(..., 'rejected')` is a valid resolution and is persisted.

    The `rejected` resolution (added by the ext-point-verify findings pipeline)
    must round-trip through the per-type storage exactly like the other terminal
    resolutions: the owning per-type file records `"resolution": "rejected"`.
    """
    sonar_path = get_findings_path('storage-reject-locate', 'sonar-issue')

    target = add_finding('storage-reject-locate', 'sonar-issue', 'Rejected sonar', 'Detail')

    outcome = resolve_finding(
        'storage-reject-locate', target['hash_id'], 'rejected', detail='Out of scope'
    )

    assert outcome['status'] == 'success'
    assert outcome['resolution'] == 'rejected'

    sonar_lines = sonar_path.read_text(encoding='utf-8').splitlines()
    assert len(sonar_lines) == 1
    assert '"resolution": "rejected"' in sonar_lines[0]
    assert '"resolution_detail": "Out of scope"' in sonar_lines[0]


def test_resolve_finding_returns_error_when_hash_absent_in_any_file(plan_context):
    """`resolve_finding` reports not-found when the hash is in no per-type file."""
    add_finding('storage-resolve-missing', 'bug', 'Bug', 'Detail')

    outcome = resolve_finding('storage-resolve-missing', 'deadbe', 'fixed')

    assert outcome['status'] == 'error'
    assert 'not found' in outcome['message']


def test_promote_finding_writes_back_to_owning_per_type_file(plan_context):
    """`promote_finding` updates only the per-type file containing the hash."""
    bug_path = get_findings_path('storage-promote-locate', 'bug')
    tip_path = get_findings_path('storage-promote-locate', 'tip')

    add_finding('storage-promote-locate', 'bug', 'Untouched bug', 'Detail')
    target = add_finding('storage-promote-locate', 'tip', 'Promotable tip', 'Detail')

    outcome = promote_finding('storage-promote-locate', target['hash_id'], 'manage-architecture')

    assert outcome['status'] == 'success'
    assert outcome['promoted_to'] == 'manage-architecture'

    bug_lines = bug_path.read_text(encoding='utf-8').splitlines()
    tip_lines = tip_path.read_text(encoding='utf-8').splitlines()
    assert '"promoted": false' in bug_lines[0]
    assert '"promoted": true' in tip_lines[0]
    assert '"promoted_to": "manage-architecture"' in tip_lines[0]


def test_mark_finding_responded_stamps_marker_and_timestamp(plan_context):
    """`mark_finding_responded` writes responded + responded_at to the owning file."""
    target = add_finding('storage-responded-mark', 'sonar-issue', 'Dismissable', 'Detail')

    outcome = mark_finding_responded('storage-responded-mark', target['hash_id'])

    assert outcome['status'] == 'success'
    assert outcome['hash_id'] == target['hash_id']

    stored = get_finding('storage-responded-mark', target['hash_id'])
    assert stored['responded'] is True
    assert stored['responded_at']


def test_mark_finding_responded_returns_error_when_hash_absent(plan_context):
    """`mark_finding_responded` reports not-found when the hash is in no per-type file."""
    add_finding('storage-responded-missing', 'sonar-issue', 'Issue', 'Detail')

    outcome = mark_finding_responded('storage-responded-missing', 'deadbe')

    assert outcome['status'] == 'error'
    assert 'not found' in outcome['message']
