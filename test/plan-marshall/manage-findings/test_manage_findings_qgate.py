#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-findings.py script.

Its sections, in order:

* Q-Gate Add Command
* Q-Gate Deduplication
* Q-Gate Query Command
"""

from argparse import Namespace

from _manage_findings_fixtures import (
    SCRIPT_PATH,
    _add_ns,
    _get_ns,
    _qgate_add_ns,
    _qgate_query_ns,
    _qgate_resolve_ns,
    _query_ns,
    cmd_add,
    cmd_get,
    cmd_qgate_add,
    cmd_qgate_query,
    cmd_qgate_resolve,
    cmd_query,
    cmd_resolve,
    cmd_stamp_fix_commit,
    query_findings_unified,
)

from conftest import get_skill_dir, run_script


def _qgate_add_optin_ns(*args, **kwargs):
    """Same as the shared ``_qgate_add_ns`` builder with the opt-in reopen flag set."""
    ns = _qgate_add_ns(*args, **kwargs)
    ns.reopen = True
    return ns


# Plan ids this module's tests file findings against — seeded by the autouse
# ``_materialize_declared_plan_dirs`` fixture in ``test/conftest.py``.
PLAN_IDS = (
    'qgate-add-basic',
    'qgate-add-opts',
    'qgate-dedup-diff',
    'qgate-dedup-pend',
    'qgate-reopen-fixed',
    'qgate-reopen-kept',
    'qgate-reopen-nonfixed',
    'qgate-inv-phase',
    'qgate-inv-source',
    'qgate-query-empty',
    'qgate-query-res',
    'qgate-query-src',
    'qgate-short-owned',
    'qgate-short-new',
    'qgate-d2-ownership',
    'qgate-d2-builderror',
    'qgate-d1-plan-store',
    'qgate-d1-qgate-store',
)

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


def test_qgate_add_fixed_plus_optin_reopens_with_history(plan_context):
    """Fixed plus the opt-in reopens: the prior resolution is readable from history."""
    add_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-reopen-fixed',
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
            plan_id='qgate-reopen-fixed',
            hash_id=hash_id,
            resolution='fixed',
            phase='3-outline',
            detail='Addressed',
        )
    )

    # Same title AND same detail → same discriminator → genuine re-detection
    # with the opt-in → reopen with the prior disposition retained in history.
    reopen_result = cmd_qgate_add(
        _qgate_add_optin_ns(
            plan_id='qgate-reopen-fixed',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Missing coverage for utils.py',
            detail='utils.parse() has no test',
        )
    )
    assert reopen_result['status'] == 'reopened'
    assert str(reopen_result['hash_id']) == hash_id
    assert reopen_result['resolution'] == 'pending'
    assert reopen_result['previous_resolution'] == 'fixed'

    stored = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-reopen-fixed',
            phase='3-outline',
        )
    )
    assert stored['findings'][0]['history'][0]['resolution'] == 'fixed'

    query_result = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-reopen-fixed',
            phase='3-outline',
            resolution='pending',
        )
    )
    assert query_result['filtered_count'] == 1


def test_qgate_add_fixed_without_optin_kept(plan_context):
    """Fixed without the opt-in is kept: the recorded resolution stands."""
    add_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-reopen-kept',
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
            plan_id='qgate-reopen-kept',
            hash_id=hash_id,
            resolution='fixed',
            phase='3-outline',
            detail='Addressed',
        )
    )

    kept_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-reopen-kept',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Missing coverage for utils.py',
            detail='utils.parse() has no test',
        )
    )
    assert kept_result['status'] == 'kept'
    assert str(kept_result['hash_id']) == hash_id
    assert kept_result['resolution'] == 'fixed'

    query_result = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-reopen-kept',
            phase='3-outline',
            resolution='pending',
        )
    )
    assert query_result['filtered_count'] == 0


def test_qgate_add_nonfixed_with_optin_kept(plan_context):
    """A non-fixed resolution re-detected WITH the opt-in is kept: only fixed reopens."""
    add_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-reopen-nonfixed',
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
            plan_id='qgate-reopen-nonfixed',
            hash_id=hash_id,
            resolution='taken_into_account',
            phase='3-outline',
            detail='Addressed',
        )
    )

    kept_result = cmd_qgate_add(
        _qgate_add_optin_ns(
            plan_id='qgate-reopen-nonfixed',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Missing coverage for utils.py',
            detail='utils.parse() has no test',
        )
    )
    assert kept_result['status'] == 'kept'
    assert str(kept_result['hash_id']) == hash_id
    assert kept_result['resolution'] == 'taken_into_account'


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

    cmd_qgate_resolve(
        _qgate_resolve_ns(
            plan_id='qgate-query-res',
            hash_id=hash_id,
            resolution='taken_into_account',
            phase='3-outline',
            detail='Addressed by revising deliverable 3',
        )
    )

    result = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-query-res',
            phase='3-outline',
            resolution='pending',
        )
    )
    assert result['filtered_count'] == 1

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


# =============================================================================
# Test: Q-Gate short-circuit task reference (resolve fixed with task number)
# =============================================================================


def test_qgate_resolve_fixed_stores_structured_task_reference(plan_context):
    """A repeated identical failure reopens owned: the pending record still names TASK-7."""
    add_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-short-owned',
            phase='5-execute',
            source='qgate',
            type='test-failure',
            title='FAILED test_login',
            detail='AssertionError: expected 200',
            file_path='test/auth.py',
        )
    )
    assert add_result['status'] == 'success'
    hash_id = str(add_result['hash_id'])

    resolve_result = cmd_qgate_resolve(
        Namespace(
            plan_id='qgate-short-owned',
            phase='5-execute',
            hash_id=hash_id,
            resolution='fixed',
            detail='Will be addressed by TASK-7; see follow-up commit on this branch',
            task_number=7,
        )
    )
    assert resolve_result['status'] == 'success'
    assert resolve_result['fix_task_number'] == 7

    # A repeated identical failure WITH the opt-in reopens the owned record back
    # to pending; without it the kept resolution would stand.
    reopen_result = cmd_qgate_add(
        _qgate_add_optin_ns(
            plan_id='qgate-short-owned',
            phase='5-execute',
            source='qgate',
            type='test-failure',
            title='FAILED test_login',
            detail='AssertionError: expected 200',
            file_path='test/auth.py',
        )
    )
    assert reopen_result['status'] == 'reopened'

    # The short-circuit read-back: the pending record still names its owner,
    # so the verdict is all-owned-by-TASK-7 and no second fix task is allocated.
    pending = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-short-owned',
            phase='5-execute',
            resolution='pending',
        )
    )
    assert pending['filtered_count'] == 1
    assert pending['findings'][0]['fix_task_number'] == 7


def test_qgate_short_circuit_new_findings_when_one_differs(plan_context):
    """A pending finding with no identical owned match is new: the dispatch proceeds."""
    owned_add = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-short-new',
            phase='5-execute',
            source='qgate',
            type='test-failure',
            title='FAILED test_login',
            detail='AssertionError: expected 200',
            file_path='test/auth.py',
        )
    )
    cmd_qgate_resolve(
        Namespace(
            plan_id='qgate-short-new',
            phase='5-execute',
            hash_id=str(owned_add['hash_id']),
            resolution='fixed',
            detail='Will be addressed by TASK-7; see follow-up commit on this branch',
            task_number=7,
        )
    )
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-short-new',
            phase='5-execute',
            source='qgate',
            type='test-failure',
            title='FAILED test_logout',
            detail='AssertionError: expected 200',
            file_path='test/auth.py',
        )
    )

    pending = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-short-new',
            phase='5-execute',
            resolution='pending',
        )
    )
    assert pending['filtered_count'] == 1
    # The differing finding carries no structured owner: verdict new-findings.
    assert pending['findings'][0].get('fix_task_number') is None


def test_qgate_resolve_task_number_requires_fixed(plan_context):
    """A task number with any other resolution is refused and writes nothing."""
    add_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-short-new',
            phase='5-execute',
            source='qgate',
            type='test-failure',
            title='FAILED test_checkout',
            detail='Timeout after 30s',
        )
    )

    bad = cmd_qgate_resolve(
        Namespace(
            plan_id='qgate-short-new',
            phase='5-execute',
            hash_id=str(add_result['hash_id']),
            resolution='accepted',
            detail='Accepted with task',
            task_number=7,
        )
    )
    assert bad['status'] == 'error'
    assert bad['error'] == 'fix_task_number_requires_fixed'


# =============================================================================
# Test: D2 fix-task ownership surviving refile plus red-build routing
# =============================================================================


def test_d2_ownership_survives_qgate_reopen_refile(plan_context):
    """Triage into TASK-N plus unchanged --reopen refile yields all-owned-by-TASK-N."""
    add_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-d2-ownership',
            phase='5-execute',
            source='qgate',
            type='test-failure',
            title='FAILED test_d2_login',
            detail='AssertionError: expected 200',
            file_path='test/d2_auth.py',
        )
    )
    assert add_result['status'] == 'success'
    hash_id = str(add_result['hash_id'])

    resolve_result = cmd_qgate_resolve(
        Namespace(
            plan_id='qgate-d2-ownership',
            phase='5-execute',
            hash_id=hash_id,
            resolution='fixed',
            detail='Will be addressed by TASK-11; see follow-up commit on this branch',
            task_number=11,
        )
    )
    assert resolve_result['status'] == 'success'
    assert resolve_result['fix_task_number'] == 11

    reopen_result = cmd_qgate_add(
        _qgate_add_optin_ns(
            plan_id='qgate-d2-ownership',
            phase='5-execute',
            source='qgate',
            type='test-failure',
            title='FAILED test_d2_login',
            detail='AssertionError: expected 200',
            file_path='test/d2_auth.py',
        )
    )
    assert reopen_result['status'] == 'reopened'

    pending = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-d2-ownership',
            phase='5-execute',
            resolution='pending',
        )
    )
    assert pending['filtered_count'] == 1
    assert pending['findings'][0]['fix_task_number'] == 11


def test_d2_orchestrator_error_build_routes_to_triage(plan_context):
    """Orchestrator-tier error build carrying findings returns new-findings, never no-pending."""
    qgate_empty = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-d2-builderror',
            phase='5-execute',
            resolution='pending',
        )
    )
    assert qgate_empty['filtered_count'] == 0

    stored = cmd_add(
        _add_ns(
            plan_id='qgate-d2-builderror',
            type='build-error',
            title='Build error in d2_module',
            detail='tool: python; command: verify; category: build_failure',
            file_path='src/d2_module.py',
            severity='error',
        )
    )
    assert stored['status'] == 'success'

    plan_pending = cmd_query(
        _query_ns(
            plan_id='qgate-d2-builderror',
            type='build-error,test-failure,lint-issue',
            resolution='pending',
        )
    )
    assert plan_pending['filtered_count'] >= 1

    unified = query_findings_unified(
        plan_id='qgate-d2-builderror',
        include_qgate=True,
    )
    assert unified['filtered_count'] >= 1


# =============================================================================
# Test: D1 store-routed task fix (ownership recorded in the finding's own store)
# =============================================================================

# The commit sha the stamp tests record; any 7-40 hex id works.
_FIX_COMMIT = 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678'

_TRIAGE_MD = get_skill_dir('plan-marshall', 'plan-marshall') / 'workflow' / 'triage.md'


def _fix_shape1_block() -> str:
    """The Shape-1 (task fix) slice of triage.md's FIX action body.

    Sliced from the Shape-1 marker to the Shape-2 marker, so neither an
    inline-fix command nor a command of the FIX preamble above Shape 1 can
    satisfy an assertion about the task-fix shape.
    """
    body = _TRIAGE_MD.read_text(encoding='utf-8')
    start = body.index('**Shape 1')
    end = body.index('**Shape 2', start)
    return body[start:end]


def _resolve_commands_in(block: str) -> dict[str, list[str]]:
    """The manage-findings resolve invocations in ``block``, keyed by target store.

    Each invocation is joined across its backslash continuations first, so an
    assertion about the flags one verb carries cannot be satisfied by a flag on
    another verb's continuation line.
    """
    joined = block.replace('\\\n', ' ')
    commands: dict[str, list[str]] = {'plan': [], 'qgate': []}
    for line in joined.splitlines():
        if 'plan-marshall:manage-findings:manage-findings qgate resolve' in line:
            commands['qgate'].append(line.strip())
        elif 'plan-marshall:manage-findings:manage-findings resolve' in line:
            commands['plan'].append(line.strip())
    return commands


def test_d1_plan_scoped_task_fix_resolves_in_the_plan_store(plan_context):
    """A plan-scoped PR-comment finding triaged into a fix task is owned and stampable.

    At ``b9cd36be1`` FIX Shape 1 routes every finding through the Q-Gate verb,
    which answers ``Q-Gate finding not found`` for a plan-scoped hash — so the
    finding never gains a ``fix_task_number`` and the short-circuit guard cannot
    see an owner. Shape 1 must route by the record's store: a plan-scoped
    finding through the plan-scoped ``resolve --task-number``, a Q-Gate finding
    through ``qgate resolve --phase ... --task-number``.

    The behaviour half drives the plan-scoped route end to end: add a
    PR-comment finding, resolve it fixed under its owning fix task, then find
    it with ``stamp-fix-commit --task-number``.
    """
    commands = _resolve_commands_in(_fix_shape1_block())

    assert len(commands['plan']) == 1, (
        'Shape 1 must route a plan-scoped finding through the plan-scoped '
        '`resolve` verb; before the fix it carries no plan-scoped command at all'
    )
    plan_command = commands['plan'][0]
    assert '--task-number {N}' in plan_command
    assert '--phase' not in plan_command

    assert len(commands['qgate']) == 1, 'Shape 1 must keep routing a Q-Gate finding through `qgate resolve`'
    qgate_command = commands['qgate'][0]
    assert '--phase {qgate_phase}' in qgate_command
    assert '--task-number {N}' in qgate_command

    plan_id = 'qgate-d1-plan-store'
    added = cmd_add(
        _add_ns(
            plan_id=plan_id,
            type='pr-comment',
            title='Reviewer: the bound equals the per-call ceiling',
            detail='The wrapper must hand back below the ceiling, not at it.',
            file_path='marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py',
            author='coderabbitai[bot]',
            kind='review_body',
        )
    )
    assert added['status'] == 'success'
    hash_id = str(added['hash_id'])

    resolved = cmd_resolve(
        Namespace(
            plan_id=plan_id,
            hash_id=hash_id,
            resolution='fixed',
            detail='Will be addressed by TASK-7; see follow-up commit on this branch',
            task_number=7,
        )
    )
    assert resolved['status'] == 'success'
    assert resolved['fix_task_number'] == 7

    stored = cmd_get(_get_ns(plan_id=plan_id, hash_id=hash_id))
    assert stored['resolution'] == 'fixed'
    assert stored['fix_task_number'] == 7

    stamped = cmd_stamp_fix_commit(Namespace(plan_id=plan_id, commit_sha=_FIX_COMMIT, task_number=7, hash_id=None))
    assert stamped['status'] == 'success'
    assert stamped['selector'] == 'fix_task_number'
    assert stamped['stamped_count'] == 1
    assert cmd_get(_get_ns(plan_id=plan_id, hash_id=hash_id))['fix_commit_sha'] == _FIX_COMMIT


def test_d1_qgate_task_fix_resolves_in_the_qgate_store(plan_context):
    """A Q-Gate finding resolved with a fix task keeps its ownership in the Q-Gate store.

    The companion route of the same task fix: a record that lives in the
    Q-Gate store records ``fix_task_number`` through ``qgate resolve``, reads
    back owned, and is identified — not resolved — by the plan-scoped verb.
    """
    plan_id = 'qgate-d1-qgate-store'
    add_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id=plan_id,
            phase='5-execute',
            source='qgate',
            type='test-failure',
            title='FAILED test_the_wait_bound_stays_foreground_safe',
            detail='AssertionError: the bound equals the per-call ceiling',
            file_path='test/plan-marshall/script-shared/test_build_execute_factory.py',
        )
    )
    assert add_result['status'] == 'success'
    hash_id = str(add_result['hash_id'])

    resolve_result = cmd_qgate_resolve(
        Namespace(
            plan_id=plan_id,
            phase='5-execute',
            hash_id=hash_id,
            resolution='fixed',
            detail='Will be addressed by TASK-7; see follow-up commit on this branch',
            task_number=7,
        )
    )
    assert resolve_result['status'] == 'success'
    assert resolve_result['fix_task_number'] == 7

    fixed = cmd_qgate_query(_qgate_query_ns(plan_id=plan_id, phase='5-execute', resolution='fixed'))
    assert fixed['filtered_count'] == 1
    assert fixed['findings'][0]['fix_task_number'] == 7

    # The record lives in the Q-Gate store only: the plan-scoped verb identifies
    # it elsewhere instead of reporting a bare not-found.
    plan_side = cmd_get(_get_ns(plan_id=plan_id, hash_id=hash_id))
    assert plan_side['status'] == 'error'
    assert plan_side['error'] == 'finding_in_other_store'
    assert plan_side['use_verb'] == 'qgate resolve --phase 5-execute'
