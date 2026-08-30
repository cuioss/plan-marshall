#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Storage-layout tests for the per-type findings JSONL split."""


from _findings_storage_fixtures import (
    add_assessment,
    add_finding,
    add_qgate_finding,
    get_findings_dir,
    get_findings_path,
    get_qgate_path,
    query_qgate_findings,
)

# Plan ids this module's tests file findings against — seeded by the autouse
# ``_materialize_declared_plan_dirs`` fixture in ``test/conftest.py``.
PLAN_IDS = (
    'storage-append-bug',
    'storage-coexist',
    'storage-distinct-files',
    'storage-lazy-bug',
    'storage-qgate-phases',
    'storage-qgate-roundtrip',
    'storage-qgate-route',
)

# =============================================================================
# Lazy creation: per-type file appears only after first matching write
# =============================================================================


def test_findings_dir_absent_until_first_write(plan_context):
    """`findings/` directory does not exist until something is written."""
    findings_dir = get_findings_dir('storage-dir-lazy')

    assert not findings_dir.exists()


# =============================================================================
# Routing: each storage flavour goes to its own file under findings/
# =============================================================================

def test_findings_qgate_assessments_coexist_in_same_dir(plan_context):
    """All three storage flavours share one `findings/` directory without colliding."""
    findings_dir = get_findings_dir('storage-coexist')

    add_finding('storage-coexist', 'bug', 'Plan bug', 'Detail')
    add_qgate_finding(
        'storage-coexist',
        '5-execute',
        'qgate',
        'build-error',
        'Phase bug',
        'Detail',
    )
    add_assessment('storage-coexist', 'a.md', 'CERTAIN_INCLUDE', 90)

    children = sorted(p.name for p in findings_dir.iterdir() if p.is_file())
    assert children == ['assessments.jsonl', 'bug.jsonl', 'qgate-5-execute.jsonl']


# =============================================================================
# Lazy creation: per-type file appears only after first matching write
# =============================================================================

def test_per_type_file_created_lazily_on_first_add(plan_context):
    """Adding a `bug` finding creates `findings/bug.jsonl` only."""
    bug_path = get_findings_path('storage-lazy-bug', 'bug')
    improvement_path = get_findings_path('storage-lazy-bug', 'improvement')
    sonar_path = get_findings_path('storage-lazy-bug', 'sonar-issue')

    add_finding('storage-lazy-bug', 'bug', 'First bug', 'Detail')

    assert bug_path.exists()
    assert not improvement_path.exists()
    assert not sonar_path.exists()


def test_distinct_types_create_distinct_files(plan_context):
    """Three different finding types create three sibling JSONL files."""
    findings_dir = get_findings_dir('storage-distinct-files')

    add_finding('storage-distinct-files', 'bug', 'Bug A', 'Detail')
    add_finding('storage-distinct-files', 'improvement', 'Improve A', 'Detail')
    add_finding('storage-distinct-files', 'sonar-issue', 'S1192', 'Detail')

    children = sorted(p.name for p in findings_dir.iterdir() if p.is_file())
    assert children == ['bug.jsonl', 'improvement.jsonl', 'sonar-issue.jsonl']


def test_repeated_same_type_appends_to_same_file(plan_context):
    """Two `bug` findings live in the same `findings/bug.jsonl`."""
    bug_path = get_findings_path('storage-append-bug', 'bug')

    add_finding('storage-append-bug', 'bug', 'Bug 1', 'Detail')
    add_finding('storage-append-bug', 'bug', 'Bug 2', 'Detail')

    lines = bug_path.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 2


# =============================================================================
# Routing: each storage flavour goes to its own file under findings/
# =============================================================================


def test_qgate_writes_to_qgate_phase_file(plan_context):
    """`add_qgate_finding('5-execute', ...)` creates `findings/qgate-5-execute.jsonl` only."""
    qgate_path = get_qgate_path('storage-qgate-route', '5-execute')
    bug_path = get_findings_path('storage-qgate-route', 'bug')

    add_qgate_finding(
        'storage-qgate-route',
        '5-execute',
        'qgate',
        'build-error',
        'Build broke',
        'Detail',
    )

    assert qgate_path.exists()
    assert qgate_path.name == 'qgate-5-execute.jsonl'
    assert not bug_path.exists()


# =============================================================================
# Q-Gate identical-results contract across the split
# =============================================================================


def test_qgate_query_returns_identical_records_to_what_was_added(plan_context):
    """`qgate add` then `qgate query` round-trip yields the same records."""
    r1 = add_qgate_finding(
        'storage-qgate-roundtrip',
        '5-execute',
        'qgate',
        'build-error',
        'Build error A',
        'Detail A',
    )
    r2 = add_qgate_finding(
        'storage-qgate-roundtrip',
        '5-execute',
        'user_review',
        'pr-comment',
        'PR comment B',
        'Detail B',
    )

    result = query_qgate_findings('storage-qgate-roundtrip', '5-execute')

    assert result['status'] == 'success'
    assert result['total_count'] == 2
    returned_ids = sorted(r['hash_id'] for r in result['findings'])
    assert returned_ids == sorted([r1['hash_id'], r2['hash_id']])


def test_qgate_phases_use_distinct_files(plan_context):
    """Different Q-Gate phases write to distinct sibling files."""
    execute_path = get_qgate_path('storage-qgate-phases', '5-execute')
    finalize_path = get_qgate_path('storage-qgate-phases', '6-finalize')

    add_qgate_finding(
        'storage-qgate-phases',
        '5-execute',
        'qgate',
        'build-error',
        'Exec issue',
        'Detail',
    )
    add_qgate_finding(
        'storage-qgate-phases',
        '6-finalize',
        'qgate',
        'pr-comment',
        'Finalize issue',
        'Detail',
    )

    assert execute_path.exists()
    assert finalize_path.exists()
    assert execute_path != finalize_path
    assert execute_path.parent == finalize_path.parent
