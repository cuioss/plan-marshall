#!/usr/bin/env python3
"""Tests for manage-findings.py script.

Tier 2 (direct import) tests with 2-3 subprocess tests for CLI plumbing.
"""

import importlib.util
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-findings', 'manage-findings.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

# Tier 2 direct imports - load hyphenated module via importlib
_MANAGE_FINDINGS_SCRIPT = str(
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-findings'
    / 'scripts'
    / 'manage-findings.py'
)
_spec = importlib.util.spec_from_file_location('manage_findings', _MANAGE_FINDINGS_SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_add = _mod.cmd_add
cmd_get = _mod.cmd_get
cmd_promote = _mod.cmd_promote
cmd_query = _mod.cmd_query
cmd_resolve = _mod.cmd_resolve
cmd_qgate_add = _mod.cmd_qgate_add
cmd_qgate_clear = _mod.cmd_qgate_clear
cmd_qgate_query = _mod.cmd_qgate_query
cmd_qgate_resolve = _mod.cmd_qgate_resolve

# Core query function (direct, bypassing the CLI namespace) for unified-read tests
query_findings_unified = _mod.query_findings_unified


# =============================================================================
# Namespace Builders
# =============================================================================


def _add_ns(
    plan_id='test-plan',
    type='bug',
    title='Test finding',
    detail='Test detail',
    file_path=None,
    line=None,
    component=None,
    module=None,
    rule=None,
    severity=None,
):
    return Namespace(
        plan_id=plan_id,
        type=type,
        title=title,
        detail=detail,
        file_path=file_path,
        line=line,
        component=component,
        module=module,
        rule=rule,
        severity=severity,
    )


def _query_ns(plan_id='test-plan', type=None, resolution=None, promoted=None, file_pattern=None, include_qgate=False):
    return Namespace(
        plan_id=plan_id,
        type=type,
        resolution=resolution,
        promoted=promoted,
        file_pattern=file_pattern,
        include_qgate=include_qgate,
    )


def _get_ns(plan_id='test-plan', hash_id=''):
    return Namespace(plan_id=plan_id, hash_id=hash_id)


def _resolve_ns(plan_id='test-plan', hash_id='', resolution='fixed', detail=None):
    return Namespace(plan_id=plan_id, hash_id=hash_id, resolution=resolution, detail=detail)


def _promote_ns(plan_id='test-plan', hash_id='', promoted_to='architecture'):
    return Namespace(plan_id=plan_id, hash_id=hash_id, promoted_to=promoted_to)


def _qgate_add_ns(
    plan_id='test-plan',
    phase='3-outline',
    source='qgate',
    type='triage',
    title='Test qgate finding',
    detail='Test detail',
    file_path=None,
    component=None,
    severity=None,
    iteration=None,
):
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        source=source,
        type=type,
        title=title,
        detail=detail,
        file_path=file_path,
        component=component,
        severity=severity,
        iteration=iteration,
    )


def _qgate_query_ns(plan_id='test-plan', phase='3-outline', resolution=None, source=None, iteration=None):
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        resolution=resolution,
        source=source,
        iteration=iteration,
    )


def _qgate_resolve_ns(plan_id='test-plan', phase='3-outline', hash_id='', resolution='taken_into_account', detail=None):
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        hash_id=hash_id,
        resolution=resolution,
        detail=detail,
    )


def _qgate_clear_ns(plan_id='test-plan', phase='3-outline'):
    return Namespace(plan_id=plan_id, phase=phase)


# =============================================================================
# Test: Finding Add Command
# =============================================================================


def test_finding_add_basic(plan_context):
    """Test adding a basic finding."""
    result = cmd_add(
        _add_ns(
            type='bug',
            title='Test failure in CacheTest',
            detail='AssertionError: expected 5 but got 3',
        )
    )
    assert result['status'] == 'success'
    assert 'hash_id' in result
    assert result['type'] == 'bug'


def test_finding_add_with_file_info(plan_context):
    """Test adding finding with file location."""
    result = cmd_add(
        _add_ns(
            type='sonar-issue',
            title='S1192: String literals duplicated',
            detail='String "application/json" appears 5 times',
            file_path='src/main/java/Api.java',
            line=42,
            rule='java:S1192',
            severity='warning',
        )
    )
    assert result['status'] == 'success'


def test_finding_add_all_types(plan_context):
    """Test that all finding types are accepted."""
    finding_types = [
        'bug',
        'improvement',
        'anti-pattern',
        'triage',
        'tip',
        'insight',
        'best-practice',
        'build-error',
        'test-failure',
        'lint-issue',
        'sonar-issue',
        'pr-comment',
    ]
    for ftype in finding_types:
        result = cmd_add(_add_ns(type=ftype, title=f'Test {ftype}', detail=f'Testing {ftype} type'))
        assert result['status'] == 'success', f'Failed for type {ftype}'


# =============================================================================
# Test: Finding Query Command
# =============================================================================


def test_finding_query_empty(plan_context):
    """Test querying with no findings."""
    result = cmd_query(_query_ns())
    assert result['total_count'] == 0


def test_finding_query_by_type(plan_context):
    """Test filtering findings by type."""
    cmd_add(_add_ns(type='bug', title='Bug 1', detail='d'))
    cmd_add(_add_ns(type='tip', title='Tip 1', detail='d'))
    cmd_add(_add_ns(type='bug', title='Bug 2', detail='d'))

    result = cmd_query(_query_ns(type='bug'))
    assert result['filtered_count'] == 2


def test_finding_query_by_resolution(plan_context):
    """Test filtering findings by resolution."""
    add_result = cmd_add(_add_ns(type='bug', title='Bug to fix', detail='d'))
    hash_id = str(add_result['hash_id'])

    cmd_resolve(_resolve_ns(hash_id=hash_id, resolution='fixed', detail='Fixed in commit abc'))

    result = cmd_query(_query_ns(resolution='fixed'))
    assert result['filtered_count'] == 1


# =============================================================================
# Test: Finding Resolve Command
# =============================================================================


def test_finding_resolve(plan_context):
    """Test resolving a finding."""
    add_result = cmd_add(
        _add_ns(
            type='build-error',
            title='Compilation error',
            detail='Missing import',
        )
    )
    hash_id = str(add_result['hash_id'])

    result = cmd_resolve(
        _resolve_ns(
            hash_id=hash_id,
            resolution='fixed',
            detail='Added missing import statement',
        )
    )
    assert result['status'] == 'success'
    assert result['resolution'] == 'fixed'


def test_finding_resolve_all_statuses(plan_context):
    """Test all resolution statuses."""
    resolutions = ['pending', 'fixed', 'suppressed', 'accepted']
    for res in resolutions:
        add_result = cmd_add(_add_ns(type='bug', title=f'Bug for {res}', detail='d'))
        hash_id = str(add_result['hash_id'])

        result = cmd_resolve(_resolve_ns(hash_id=hash_id, resolution=res))
        assert result['status'] == 'success', f'Failed for resolution {res}'


# =============================================================================
# Test: Finding Promote Command
# =============================================================================


def test_finding_promote(plan_context):
    """Test promoting a finding."""
    add_result = cmd_add(
        _add_ns(
            plan_id='finding-promote',
            type='tip',
            title='Use constructor injection',
            detail='Prefer constructor injection over field injection for testability',
        )
    )
    hash_id = str(add_result['hash_id'])

    result = cmd_promote(
        _promote_ns(
            plan_id='finding-promote',
            hash_id=hash_id,
            promoted_to='architecture',
        )
    )
    assert result['status'] == 'success'
    assert result['promoted_to'] == 'architecture'


def test_finding_promote_to_lessons(plan_context):
    """Test promoting to lessons learned."""
    add_result = cmd_add(
        _add_ns(
            type='bug',
            title='Null pointer from missing null check',
            detail='Always check for null before calling methods on optional fields',
        )
    )
    hash_id = str(add_result['hash_id'])

    result = cmd_promote(
        _promote_ns(
            hash_id=hash_id,
            promoted_to='lessons-2025-01-22-001',
        )
    )
    assert 'lessons-' in result['promoted_to']


def test_finding_query_promoted(plan_context):
    """Test filtering by promoted status."""
    # Add and promote one
    add_result = cmd_add(_add_ns(type='tip', title='Promoted tip', detail='d'))
    hash_id = str(add_result['hash_id'])
    cmd_promote(_promote_ns(hash_id=hash_id, promoted_to='architecture'))

    # Add one not promoted
    cmd_add(_add_ns(type='tip', title='Not promoted', detail='d'))

    # Query promoted
    result = cmd_query(_query_ns(promoted='true'))
    assert result['filtered_count'] == 1

    # Query not promoted
    result = cmd_query(_query_ns(promoted='false'))
    assert result['filtered_count'] == 1


# =============================================================================
# Test: Q-Gate Add Command
# =============================================================================


def test_qgate_add_basic(plan_context):
    """Test adding a basic Q-Gate finding."""
    result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-add-basic',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='False positive: helper.py',
            detail='File is consumer-only, not a producer',
        )
    )
    assert result['status'] == 'success'
    assert 'hash_id' in result
    assert result['phase'] == '3-outline'


def test_qgate_add_with_options(plan_context):
    """Test adding Q-Gate finding with all options."""
    result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-add-opts',
            phase='3-outline',
            source='user_review',
            type='triage',
            title='User: Add module X',
            detail='User requested adding module X to scope',
            file_path='src/module-x/main.py',
            component='deliverable-3',
            severity='warning',
            iteration=2,
        )
    )
    assert result['status'] == 'success'


def test_qgate_add_invalid_phase(plan_context):
    """Test that invalid phase is rejected (CLI plumbing - subprocess).

    The canonical ``parse_args_with_toon_errors`` contract emits
    ``status: error / error: invalid_phase`` TOON on stdout with exit
    code 0 (so callers can read the structured error without parsing
    stderr). The legacy assertion checked ``not result.success``; the
    new contract requires inspecting the parsed TOON instead.
    """
    result = run_script(
        SCRIPT_PATH,
        'qgate',
        'add',
        '--plan-id',
        'qgate-inv-phase',
        '--phase',
        'invalid-phase',
        '--source',
        'qgate',
        '--type',
        'triage',
        '--title',
        'Test',
        '--detail',
        'Test detail',
    )
    # New contract: argparse-boundary validation emits TOON on stdout
    # with exit code 0. Older invalid-source/invalid-type values still
    # fall through to the command handler which exits non-zero.
    assert result.returncode == 0
    data = result.toon()
    assert data.get('status') == 'error'
    assert data.get('error') == 'invalid_phase'


def test_qgate_add_invalid_source(plan_context):
    """Test that invalid source is rejected (CLI plumbing - subprocess)."""
    result = run_script(
        SCRIPT_PATH,
        'qgate',
        'add',
        '--plan-id',
        'qgate-inv-source',
        '--phase',
        '3-outline',
        '--source',
        'invalid',
        '--type',
        'triage',
        '--title',
        'Test',
        '--detail',
        'Test detail',
    )
    assert not result.success


# =============================================================================
# Test: Q-Gate Query Command
# =============================================================================


def test_qgate_query_empty(plan_context):
    """Test querying with no Q-Gate findings."""
    result = cmd_qgate_query(_qgate_query_ns(plan_id='qgate-query-empty', phase='3-outline'))
    assert result['status'] == 'success'
    assert result['total_count'] == 0
    assert result['phase'] == '3-outline'


def test_qgate_query_by_resolution(plan_context):
    """Test filtering Q-Gate findings by resolution."""
    # Add two findings
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-query-res',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Finding 1',
            detail='d1',
        )
    )
    add_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-query-res',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Finding 2',
            detail='d2',
        )
    )
    hash_id = str(add_result['hash_id'])

    # Resolve one
    cmd_qgate_resolve(
        _qgate_resolve_ns(
            plan_id='qgate-query-res',
            hash_id=hash_id,
            resolution='taken_into_account',
            phase='3-outline',
            detail='Addressed by revising deliverable 3',
        )
    )

    # Query pending
    result = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-query-res',
            phase='3-outline',
            resolution='pending',
        )
    )
    assert result['filtered_count'] == 1

    # Query taken_into_account
    result = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-query-res',
            phase='3-outline',
            resolution='taken_into_account',
        )
    )
    assert result['filtered_count'] == 1


def test_qgate_query_by_source(plan_context):
    """Test filtering Q-Gate findings by source."""
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-query-src',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Auto finding',
            detail='d',
        )
    )
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-query-src',
            phase='3-outline',
            source='user_review',
            type='triage',
            title='User finding',
            detail='d',
        )
    )

    result = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-query-src',
            phase='3-outline',
            source='user_review',
        )
    )
    assert result['total_count'] == 2
    assert result['filtered_count'] == 1


def test_qgate_per_phase_isolation(plan_context):
    """Test that Q-Gate findings are isolated per phase."""
    # Add to phase 3
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
    # Add to phase 4
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

    # Query phase 3 only
    result = cmd_qgate_query(_qgate_query_ns(plan_id='qgate-phase-iso', phase='3-outline'))
    assert result['total_count'] == 1
    assert result['phase'] == '3-outline'

    # Query phase 4 only
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
    resolutions = ['pending', 'fixed', 'suppressed', 'accepted', 'taken_into_account']
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

    # Verify empty
    query_result = cmd_qgate_query(_qgate_query_ns(plan_id='qgate-clear', phase='3-outline'))
    assert query_result['total_count'] == 0


def test_qgate_clear_empty(plan_context):
    """Test clearing when no Q-Gate findings exist."""
    result = cmd_qgate_clear(_qgate_clear_ns(plan_id='qgate-clear-empty', phase='3-outline'))
    assert result['status'] == 'success'
    assert result['cleared'] == 0


def test_qgate_user_review_source(plan_context):
    """Test that user_review findings work end-to-end."""
    # Add user review finding
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

    # Query user_review findings
    query_result = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-user-review',
            phase='3-outline',
            source='user_review',
        )
    )
    assert query_result['filtered_count'] == 1

    # Resolve as taken_into_account
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

    # Verify resolved
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
    """Test that adding same title twice returns deduplicated, only 1 record."""
    result1 = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-dedup-pend',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Missing assessment for helper.py',
            detail='d1',
        )
    )
    assert result1['status'] == 'success'
    original_hash = str(result1['hash_id'])

    # Add same title again
    result2 = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-dedup-pend',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Missing assessment for helper.py',
            detail='d2',
        )
    )
    assert result2['status'] == 'deduplicated'
    assert str(result2['hash_id']) == original_hash

    # Verify only 1 record exists
    query_result = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-dedup-pend',
            phase='3-outline',
        )
    )
    assert query_result['total_count'] == 1


def test_qgate_add_reopen_resolved(plan_context):
    """Test that re-adding a resolved finding reopens it."""
    # Add finding
    add_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-dedup-reopen',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Missing coverage for utils.py',
            detail='d1',
        )
    )
    assert add_result['status'] == 'success'
    hash_id = str(add_result['hash_id'])

    # Resolve it
    cmd_qgate_resolve(
        _qgate_resolve_ns(
            plan_id='qgate-dedup-reopen',
            hash_id=hash_id,
            resolution='taken_into_account',
            phase='3-outline',
            detail='Addressed',
        )
    )

    # Re-add same title
    reopen_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-dedup-reopen',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Missing coverage for utils.py',
            detail='d2',
        )
    )
    assert reopen_result['status'] == 'reopened'
    assert str(reopen_result['hash_id']) == hash_id

    # Verify it's pending again
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
# Test: Finding Resolve with taken_into_account (extended)
# =============================================================================


def test_finding_resolve_taken_into_account(plan_context):
    """Test that taken_into_account resolution works for regular findings too."""
    add_result = cmd_add(_add_ns(type='triage', title='Reviewed finding', detail='d'))
    hash_id = str(add_result['hash_id'])

    result = cmd_resolve(
        _resolve_ns(
            hash_id=hash_id,
            resolution='taken_into_account',
            detail='Addressed in revision',
        )
    )
    assert result['resolution'] == 'taken_into_account'


# =============================================================================
# Test: Unified per-plan + Q-Gate read surface (--include-qgate)
# =============================================================================


def test_unified_query_merges_plan_and_qgate(plan_context):
    """(a) --include-qgate returns both per-plan findings and pending Q-Gate findings."""
    pid = 'unified-merge'
    cmd_add(_add_ns(plan_id=pid, type='bug', title='Plan bug', detail='d'))
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid,
            phase='5-execute',
            source='qgate',
            type='triage',
            title='Q-Gate finding',
            detail='d',
        )
    )

    # Default (no --include-qgate) sees only the plan finding.
    plain = cmd_query(_query_ns(plan_id=pid))
    assert plain['filtered_count'] == 1
    assert 'qgate_included' not in plain

    # Unified read merges the pending q-gate finding alongside the plan finding.
    unified = cmd_query(_query_ns(plan_id=pid, include_qgate=True))
    assert unified['status'] == 'success'
    assert unified['qgate_included'] is True
    assert unified['plan_count'] == 1
    assert unified['qgate_count'] == 1
    assert unified['filtered_count'] == 2
    titles = {f['title'] for f in unified['findings']}
    assert titles == {'Plan bug', 'Q-Gate finding'}


def test_unified_query_spans_all_phases(plan_context):
    """(b) Per-plan unified query returns q-gate findings across every phase."""
    pid = 'unified-all-phases'
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='3-outline', source='qgate', type='triage', title='Phase 3 fd', detail='d'
        )
    )
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='4-plan', source='qgate', type='triage', title='Phase 4 fd', detail='d'
        )
    )
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='Phase 5 fd', detail='d'
        )
    )

    unified = cmd_query(_query_ns(plan_id=pid, include_qgate=True))
    assert unified['plan_count'] == 0
    assert unified['qgate_count'] == 3
    assert unified['filtered_count'] == 3
    titles = {f['title'] for f in unified['findings']}
    assert titles == {'Phase 3 fd', 'Phase 4 fd', 'Phase 5 fd'}


def test_unified_query_excludes_resolved_qgate(plan_context):
    """(b) Only PENDING q-gate findings are merged; resolved ones are dropped."""
    pid = 'unified-only-pending'
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='Stays pending', detail='d'
        )
    )
    resolved = cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='Gets resolved', detail='d'
        )
    )
    cmd_qgate_resolve(
        _qgate_resolve_ns(
            plan_id=pid,
            hash_id=str(resolved['hash_id']),
            resolution='taken_into_account',
            phase='5-execute',
        )
    )

    unified = cmd_query(_query_ns(plan_id=pid, include_qgate=True))
    assert unified['qgate_count'] == 1
    titles = {f['title'] for f in unified['findings']}
    assert titles == {'Stays pending'}


def test_unified_query_type_filter_applies_to_both_slices(plan_context):
    """(c) The --type narrow filters both plan and q-gate slices."""
    pid = 'unified-type-filter'
    cmd_add(_add_ns(plan_id=pid, type='bug', title='Plan bug', detail='d'))
    cmd_add(_add_ns(plan_id=pid, type='tip', title='Plan tip', detail='d'))
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='QG triage', detail='d'
        )
    )

    unified = cmd_query(_query_ns(plan_id=pid, type='bug', include_qgate=True))
    assert unified['plan_count'] == 1
    assert unified['qgate_count'] == 0
    assert unified['filtered_count'] == 1
    assert unified['findings'][0]['title'] == 'Plan bug'
    # total_count spans the FULL universe of both slices symmetrically: the
    # entire plan store (2 findings: bug + tip) plus every pending q-gate record
    # (1: QG triage), before the --type narrowing. filtered_count (1) is the
    # post-narrowing union. total_count must NOT mix the plan store's unfiltered
    # total with the q-gate slice's filtered count.
    assert unified['total_count'] == 3


def test_unified_query_resolution_filter_scopes_plan_slice(plan_context):
    """(c) The --resolution narrow scopes the plan slice without dropping pending q-gate."""
    pid = 'unified-res-filter'
    fixed = cmd_add(_add_ns(plan_id=pid, type='bug', title='Fixed bug', detail='d'))
    cmd_resolve(_resolve_ns(plan_id=pid, hash_id=str(fixed['hash_id']), resolution='fixed'))
    cmd_add(_add_ns(plan_id=pid, type='bug', title='Open bug', detail='d'))
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='QG pending', detail='d'
        )
    )

    unified = cmd_query(_query_ns(plan_id=pid, resolution='fixed', include_qgate=True))
    # Plan slice narrowed to the single fixed finding; pending q-gate still merged.
    assert unified['plan_count'] == 1
    assert unified['qgate_count'] == 1
    titles = {f['title'] for f in unified['findings']}
    assert titles == {'Fixed bug', 'QG pending'}


def test_unified_query_empty(plan_context):
    """(d) Unified read on an empty plan returns zero counts but the unified shape."""
    unified = cmd_query(_query_ns(plan_id='unified-empty', include_qgate=True))
    assert unified['status'] == 'success'
    assert unified['qgate_included'] is True
    assert unified['plan_count'] == 0
    assert unified['qgate_count'] == 0
    assert unified['filtered_count'] == 0
    assert unified['findings'] == []


def test_backward_compat_list_without_include_qgate(plan_context):
    """(d) Existing list call shape (no --include-qgate) keeps its original shape."""
    pid = 'compat-list'
    cmd_add(_add_ns(plan_id=pid, type='bug', title='Plan bug', detail='d'))
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='QG finding', detail='d'
        )
    )

    plain = cmd_query(_query_ns(plan_id=pid))
    assert plain['status'] == 'success'
    # No q-gate provenance keys; q-gate finding is NOT merged.
    assert 'qgate_included' not in plain
    assert 'plan_count' not in plain
    assert plain['filtered_count'] == 1
    assert plain['findings'][0]['title'] == 'Plan bug'


def test_backward_compat_qgate_list_unaffected(plan_context):
    """(d) The narrowed qgate list call shape is unchanged by the unified surface."""
    pid = 'compat-qgate-list'
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='3-outline', source='qgate', type='triage', title='QG fd', detail='d'
        )
    )

    result = cmd_qgate_query(_qgate_query_ns(plan_id=pid, phase='3-outline'))
    assert result['status'] == 'success'
    assert result['phase'] == '3-outline'
    assert result['total_count'] == 1
    assert result['filtered_count'] == 1
    # Per-phase qgate list does NOT carry the unified provenance markers.
    assert 'qgate_included' not in result


def test_unified_query_core_direct(plan_context):
    """Direct core call (bypassing CLI namespace) merges plan + pending q-gate."""
    pid = 'unified-core-direct'
    cmd_add(_add_ns(plan_id=pid, type='bug', title='Core plan bug', detail='d'))
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='Core QG', detail='d'
        )
    )

    unified = query_findings_unified(pid)
    assert unified['qgate_included'] is True
    assert unified['plan_count'] == 1
    assert unified['qgate_count'] == 1
    titles = {f['title'] for f in unified['findings']}
    assert titles == {'Core plan bug', 'Core QG'}


def test_cli_unified_list_include_qgate_roundtrip(plan_context):
    """CLI plumbing: list --include-qgate merges plan + q-gate via subprocess."""
    pid = 'cli-unified-rt'
    add_result = run_script(
        SCRIPT_PATH, 'add', '--plan-id', pid, '--type', 'bug', '--title', 'CLI plan bug', '--detail', 'd'
    )
    assert add_result.success, f'Script failed: {add_result.stderr}'
    qgate_result = run_script(
        SCRIPT_PATH,
        'qgate',
        'add',
        '--plan-id',
        pid,
        '--phase',
        '5-execute',
        '--source',
        'qgate',
        '--type',
        'triage',
        '--title',
        'CLI QG',
        '--detail',
        'd',
    )
    assert qgate_result.success, f'Script failed: {qgate_result.stderr}'

    # Default list: only the plan finding.
    plain = run_script(SCRIPT_PATH, 'list', '--plan-id', pid)
    assert plain.success
    plain_data = parse_toon(plain.stdout)
    assert plain_data['filtered_count'] == 1

    # Unified list: plan + pending q-gate finding.
    unified = run_script(SCRIPT_PATH, 'list', '--plan-id', pid, '--include-qgate')
    assert unified.success, f'Script failed: {unified.stderr}'
    unified_data = parse_toon(unified.stdout)
    assert unified_data['qgate_included'] is True
    assert unified_data['filtered_count'] == 2


# =============================================================================
# CLI Plumbing Tests (subprocess)
# =============================================================================


def test_cli_add_and_query_roundtrip(plan_context):
    """CLI plumbing: add a finding and query it back via subprocess."""
    result = run_script(
        SCRIPT_PATH,
        'add',
        '--plan-id',
        'test-plan',
        '--type',
        'bug',
        '--title',
        'CLI roundtrip test',
        '--detail',
        'Testing CLI plumbing',
    )
    assert result.success, f'Script failed: {result.stderr}'
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'

    query_result = run_script(SCRIPT_PATH, 'list', '--plan-id', 'test-plan')
    assert query_result.success
    query_data = parse_toon(query_result.stdout)
    assert query_data['total_count'] == 1


def test_cli_qgate_add_and_clear_roundtrip(plan_context):
    """CLI plumbing: add Q-Gate finding and clear via subprocess."""
    add_result = run_script(
        SCRIPT_PATH,
        'qgate',
        'add',
        '--plan-id',
        'cli-qgate-rt',
        '--phase',
        '3-outline',
        '--source',
        'qgate',
        '--type',
        'triage',
        '--title',
        'CLI qgate test',
        '--detail',
        'Testing CLI plumbing',
    )
    assert add_result.success, f'Script failed: {add_result.stderr}'

    clear_result = run_script(SCRIPT_PATH, 'qgate', 'clear', '--plan-id', 'cli-qgate-rt', '--phase', '3-outline')
    assert clear_result.success
    clear_data = parse_toon(clear_result.stdout)
    assert clear_data['cleared'] == 1
