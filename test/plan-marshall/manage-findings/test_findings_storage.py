#!/usr/bin/env python3
"""Storage-layout tests for the per-type findings JSONL split.

These tests pin the contract for the post-split storage layer described in
deliverable 1 of plan ``lesson-2026-05-05-11-001``:

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

import importlib.util
import sys
from pathlib import Path

from conftest import PlanContext

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-findings'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_findings_core = _load_module('_findings_core', '_findings_core.py')

add_assessment = _findings_core.add_assessment
add_finding = _findings_core.add_finding
add_qgate_finding = _findings_core.add_qgate_finding
get_assessments_path = _findings_core.get_assessments_path
get_finding = _findings_core.get_finding
get_findings_dir = _findings_core.get_findings_dir
get_findings_path = _findings_core.get_findings_path
get_qgate_path = _findings_core.get_qgate_path
promote_finding = _findings_core.promote_finding
query_findings = _findings_core.query_findings
query_qgate_findings = _findings_core.query_qgate_findings
resolve_finding = _findings_core.resolve_finding


# =============================================================================
# Lazy creation: per-type file appears only after first matching write
# =============================================================================


def test_findings_dir_absent_until_first_write():
    """`findings/` directory does not exist until something is written."""
    with PlanContext(plan_id='storage-dir-lazy'):
        findings_dir = get_findings_dir('storage-dir-lazy')

        assert not findings_dir.exists()


def test_per_type_file_created_lazily_on_first_add():
    """Adding a `bug` finding creates `findings/bug.jsonl` only."""
    with PlanContext(plan_id='storage-lazy-bug'):
        bug_path = get_findings_path('storage-lazy-bug', 'bug')
        improvement_path = get_findings_path('storage-lazy-bug', 'improvement')
        sonar_path = get_findings_path('storage-lazy-bug', 'sonar-issue')

        add_finding('storage-lazy-bug', 'bug', 'First bug', 'Detail')

        assert bug_path.exists()
        assert not improvement_path.exists()
        assert not sonar_path.exists()


def test_distinct_types_create_distinct_files():
    """Three different finding types create three sibling JSONL files."""
    with PlanContext(plan_id='storage-distinct-files'):
        findings_dir = get_findings_dir('storage-distinct-files')

        add_finding('storage-distinct-files', 'bug', 'Bug A', 'Detail')
        add_finding('storage-distinct-files', 'improvement', 'Improve A', 'Detail')
        add_finding('storage-distinct-files', 'sonar-issue', 'S1192', 'Detail')

        children = sorted(p.name for p in findings_dir.iterdir() if p.is_file())
        assert children == ['bug.jsonl', 'improvement.jsonl', 'sonar-issue.jsonl']


def test_repeated_same_type_appends_to_same_file():
    """Two `bug` findings live in the same `findings/bug.jsonl`."""
    with PlanContext(plan_id='storage-append-bug'):
        bug_path = get_findings_path('storage-append-bug', 'bug')

        add_finding('storage-append-bug', 'bug', 'Bug 1', 'Detail')
        add_finding('storage-append-bug', 'bug', 'Bug 2', 'Detail')

        lines = bug_path.read_text(encoding='utf-8').splitlines()
        assert len(lines) == 2


# =============================================================================
# Routing: each storage flavour goes to its own file under findings/
# =============================================================================


def test_qgate_writes_to_qgate_phase_file():
    """`add_qgate_finding('5-execute', ...)` creates `findings/qgate-5-execute.jsonl` only."""
    with PlanContext(plan_id='storage-qgate-route'):
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


def test_assessment_writes_to_assessments_file():
    """`add_assessment` creates `findings/assessments.jsonl` only."""
    with PlanContext(plan_id='storage-assess-route'):
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


def test_findings_qgate_assessments_coexist_in_same_dir():
    """All three storage flavours share one `findings/` directory without colliding."""
    with PlanContext(plan_id='storage-coexist'):
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


def test_query_findings_merges_across_per_type_files():
    """Query returns the union of every per-type file."""
    with PlanContext(plan_id='storage-query-merge'):
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


def test_query_findings_ignores_qgate_and_assessment_files():
    """Q-Gate and assessment records must not leak into `query_findings`."""
    with PlanContext(plan_id='storage-query-isolate'):
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


def test_query_findings_hash_id_space_is_stable_across_split():
    """Every merged record exposes a hash_id; ids are unique across files."""
    with PlanContext(plan_id='storage-query-hash'):
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


def test_query_findings_type_filter_after_merge():
    """`finding_type` filter narrows merged records to one type."""
    with PlanContext(plan_id='storage-filter-type'):
        add_finding('storage-filter-type', 'bug', 'Bug 1', 'Detail')
        add_finding('storage-filter-type', 'bug', 'Bug 2', 'Detail')
        add_finding('storage-filter-type', 'improvement', 'Improve 1', 'Detail')

        result = query_findings('storage-filter-type', finding_type='bug')

        assert result['total_count'] == 3
        assert result['filtered_count'] == 2
        assert all(r['type'] == 'bug' for r in result['findings'])


def test_query_findings_comma_separated_type_filter_after_merge():
    """Comma-separated type filter spans multiple per-type files."""
    with PlanContext(plan_id='storage-filter-multitype'):
        add_finding('storage-filter-multitype', 'bug', 'Bug 1', 'Detail')
        add_finding('storage-filter-multitype', 'improvement', 'Improve 1', 'Detail')
        add_finding('storage-filter-multitype', 'tip', 'Tip 1', 'Detail')

        result = query_findings('storage-filter-multitype', finding_type='bug,improvement')

        assert result['filtered_count'] == 2
        seen = sorted(r['type'] for r in result['findings'])
        assert seen == ['bug', 'improvement']


def test_query_findings_resolution_filter_after_merge():
    """Resolution filter applies after the per-type files are merged."""
    with PlanContext(plan_id='storage-filter-resolution'):
        r1 = add_finding('storage-filter-resolution', 'bug', 'Bug 1', 'Detail')
        add_finding('storage-filter-resolution', 'improvement', 'Improve 1', 'Detail')
        resolve_finding('storage-filter-resolution', r1['hash_id'], 'fixed')

        pending = query_findings('storage-filter-resolution', resolution='pending')
        fixed = query_findings('storage-filter-resolution', resolution='fixed')

        assert pending['filtered_count'] == 1
        assert pending['findings'][0]['type'] == 'improvement'
        assert fixed['filtered_count'] == 1
        assert fixed['findings'][0]['type'] == 'bug'


def test_query_findings_promoted_filter_after_merge():
    """`promoted=True` filter spans every per-type file."""
    with PlanContext(plan_id='storage-filter-promoted'):
        r_bug = add_finding('storage-filter-promoted', 'bug', 'Bug 1', 'Detail')
        add_finding('storage-filter-promoted', 'improvement', 'Improve 1', 'Detail')
        promote_finding('storage-filter-promoted', r_bug['hash_id'], 'manage-lessons')

        promoted = query_findings('storage-filter-promoted', promoted=True)
        unpromoted = query_findings('storage-filter-promoted', promoted=False)

        assert promoted['filtered_count'] == 1
        assert promoted['findings'][0]['hash_id'] == r_bug['hash_id']
        assert unpromoted['filtered_count'] == 1
        assert unpromoted['findings'][0]['type'] == 'improvement'


def test_query_findings_file_pattern_filter_after_merge():
    """File-pattern filter spans every per-type file."""
    with PlanContext(plan_id='storage-filter-file'):
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


def test_get_finding_locates_record_in_owning_per_type_file():
    """`get_finding` finds a record in a non-default per-type file by hash_id."""
    with PlanContext(plan_id='storage-get-locate'):
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


def test_resolve_finding_writes_back_to_owning_per_type_file():
    """`resolve_finding` updates only the per-type file containing the hash."""
    with PlanContext(plan_id='storage-resolve-locate'):
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


def test_promote_finding_writes_back_to_owning_per_type_file():
    """`promote_finding` updates only the per-type file containing the hash."""
    with PlanContext(plan_id='storage-promote-locate'):
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


def test_resolve_finding_returns_error_when_hash_absent_in_any_file():
    """`resolve_finding` reports not-found when the hash is in no per-type file."""
    with PlanContext(plan_id='storage-resolve-missing'):
        add_finding('storage-resolve-missing', 'bug', 'Bug', 'Detail')

        outcome = resolve_finding('storage-resolve-missing', 'deadbe', 'fixed')

        assert outcome['status'] == 'error'
        assert 'not found' in outcome['message']


# =============================================================================
# Q-Gate identical-results contract across the split
# =============================================================================


def test_qgate_query_returns_identical_records_to_what_was_added():
    """`qgate add` then `qgate query` round-trip yields the same records."""
    with PlanContext(plan_id='storage-qgate-roundtrip'):
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


def test_qgate_phases_use_distinct_files():
    """Different Q-Gate phases write to distinct sibling files."""
    with PlanContext(plan_id='storage-qgate-phases'):
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
