#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Storage-layout tests for the per-type findings JSONL split.

These tests pin the contract for the per-type storage layer:

* findings live under ``findings/{type}.jsonl`` (one file per finding type),
* Q-Gate findings live under ``findings/qgate-{phase}.jsonl``,
* assessments live under ``findings/assessments.jsonl``,
* per-type files are created lazily on first write,
* ``query_findings`` merges across every per-type file with a stable
  ``hash_id`` space,
* type / resolution / promoted / file-pattern filters keep working post-split,
* ``get_finding`` / ``resolve_finding`` / ``promote_finding`` locate the
  owning per-type file by ``hash_id`` (not by type),
* ``add_finding`` / ``add_qgate_finding`` / ``add_assessment`` route writes to
  their respective files within the same ``findings/`` directory.

Implementation tests (CLI plumbing, validation error paths, qgate dedup/reopen
semantics) live in ``test_findings_store.py`` and ``test_manage_findings.py``;
this module is intentionally storage-layout focused.
"""


from _findings_storage_fixtures import (
    add_assessment,
    add_finding,
    add_qgate_finding,
    get_assessments_path,
    get_findings_dir,
    get_findings_path,
    get_qgate_path,
    query_findings,
)

# =============================================================================
# Lazy creation: per-type file appears only after first matching write
# =============================================================================


def test_findings_dir_absent_until_first_write(plan_context):
    """`findings/` directory does not exist until something is written."""
    findings_dir = get_findings_dir('storage-dir-lazy')

    assert not findings_dir.exists()


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
