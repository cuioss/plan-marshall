#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py transition + archive + delete + orphans + loop-back.

Split from test_manage_status.py: covers cmd_transition (incl. inline
strict-verify guard for guarded boundaries, and last-phase symmetry with
cmd_archive), cmd_archive (incl. --reason flag), cmd_delete_plan (incl.
lesson-restoration), cmd_list (incl. worktree moved-in plan discovery),
cmd_list_orphans, and cmd_mark_step_done loop-back target validation.
"""

import json
import shutil
import sys as _sys
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path, load_script_module, run_script

# Script path for CLI plumbing / subprocess tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')


_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_cmd_lifecycle')
_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_status_cmd_query')

cmd_archive = _lifecycle.cmd_archive
cmd_create = _lifecycle.cmd_create
cmd_delete_plan = _lifecycle.cmd_delete_plan
cmd_list = _query.cmd_list
cmd_list_orphans = _query.cmd_list_orphans
cmd_set_phase = _query.cmd_set_phase
cmd_transition = _lifecycle.cmd_transition
cmd_update_phase = _query.cmd_update_phase


# =============================================================================
# Test: Delete Plan
# =============================================================================


def test_delete_plan_success(plan_context):
    """Test deleting an existing plan directory."""
    plan_dir = plan_context.plan_dir_for('delete-test')
    # Create some files in the plan
    (plan_dir / 'request.md').write_text('# Request')
    (plan_dir / 'references.json').write_text('{"branch": "main"}')
    (plan_dir / 'tasks').mkdir()
    (plan_dir / 'tasks' / 'TASK-001.toon').write_text('title: Test')

    result = cmd_delete_plan(Namespace(plan_id='delete-test'))
    assert result['status'] == 'success'
    assert result['action'] == 'deleted'
    assert result['plan_id'] == 'delete-test'
    assert result['files_removed'] == 3  # request.md, references.json, TASK-001.toon
    # Verify directory was deleted
    assert not plan_dir.exists()


def test_delete_plan_not_found(plan_context):
    """Test deleting a plan that doesn't exist."""
    result = cmd_delete_plan(Namespace(plan_id='nonexistent-plan'))
    assert result['status'] == 'error'
    assert result['error'] == 'plan_not_found'


def test_delete_plan_invalid_id(plan_context):
    """Test delete-plan rejects invalid plan IDs (sys.exit(1) from require_valid_plan_id)."""
    with pytest.raises(SystemExit) as exc_info:
        cmd_delete_plan(Namespace(plan_id='Invalid_Plan'))
    assert exc_info.value.code == 0


def test_delete_plan_auto_restores_lesson(plan_context):
    """delete-plan moves a lesson-{id}.md back to lessons-learned/ before deletion."""
    plan_dir = plan_context.plan_dir_for('lesson-2025-01-01-001')
    (plan_dir / 'request.md').write_text('# Request')
    (plan_dir / 'lesson-2025-01-01-001.md').write_text(
        'id=2025-01-01-001\ncomponent=foo\ncategory=bug\ncreated=2025-01-01\n\n# Lesson\n\nBody.\n'
    )

    lessons_dir = plan_context.fixture_dir / 'lessons-learned'
    # Pre-emptively confirm the destination does not exist
    if lessons_dir.exists():
        (lessons_dir / '2025-01-01-001.md').unlink(missing_ok=True)

    result = cmd_delete_plan(Namespace(plan_id='lesson-2025-01-01-001', no_restore_lessons=False))

    assert result['status'] == 'success'
    assert result['action'] == 'deleted'
    assert result['lesson_restored'] is True
    assert result['restored_lesson_ids'] == ['2025-01-01-001']

    # Plan dir was deleted
    assert not plan_dir.exists()
    # Lesson file lives in lessons-learned/ again
    restored = plan_context.fixture_dir / 'lessons-learned' / '2025-01-01-001.md'
    assert restored.exists()
    assert '# Lesson' in restored.read_text()


def test_delete_plan_no_lesson_file_unchanged_behaviour(plan_context):
    """delete-plan on a plan dir without a lesson file reports lesson_restored: False."""
    plan_dir = plan_context.plan_dir_for('delete-no-lesson')
    (plan_dir / 'request.md').write_text('# Request')

    result = cmd_delete_plan(Namespace(plan_id='delete-no-lesson', no_restore_lessons=False))

    assert result['status'] == 'success'
    assert result['action'] == 'deleted'
    assert result['lesson_restored'] is False
    assert 'restored_lesson_ids' not in result
    assert not plan_dir.exists()


def test_delete_plan_no_restore_lessons_flag_skips_restoration(plan_context):
    """--no-restore-lessons preserves the prior unconditional-delete behaviour."""
    plan_dir = plan_context.plan_dir_for('lesson-2025-01-01-002')
    (plan_dir / 'lesson-2025-01-01-002.md').write_text(
        'id=2025-01-01-002\ncomponent=foo\ncategory=bug\ncreated=2025-01-01\n\n# Lesson\n\nBody.\n'
    )

    result = cmd_delete_plan(Namespace(plan_id='lesson-2025-01-01-002', no_restore_lessons=True))

    assert result['status'] == 'success'
    assert result['action'] == 'deleted'
    assert result['lesson_restored'] is False
    # The lesson file was discarded along with the plan dir
    assert not plan_dir.exists()
    assert not (plan_context.fixture_dir / 'lessons-learned' / '2025-01-01-002.md').exists()


def test_delete_plan_restores_all_lesson_files(plan_context):
    """delete-plan restores every lesson-*.md file in the plan dir (multi-lesson plans)."""
    plan_dir = plan_context.plan_dir_for('consolidate-multi')
    (plan_dir / 'request.md').write_text('# Request')
    (plan_dir / 'lesson-2025-02-01-001.md').write_text(
        'id=2025-02-01-001\ncomponent=foo\ncategory=bug\ncreated=2025-02-01\n\n# One\n'
    )
    (plan_dir / 'lesson-2025-02-01-002.md').write_text(
        'id=2025-02-01-002\ncomponent=bar\ncategory=bug\ncreated=2025-02-01\n\n# Two\n'
    )

    result = cmd_delete_plan(Namespace(plan_id='consolidate-multi', no_restore_lessons=False))

    assert result['status'] == 'success'
    assert result['action'] == 'deleted'
    assert result['lesson_restored'] is True
    assert result['restored_lesson_ids'] == ['2025-02-01-001', '2025-02-01-002']

    # Both lesson files exist in lessons-learned/
    lessons_dir = plan_context.fixture_dir / 'lessons-learned'
    assert (lessons_dir / '2025-02-01-001.md').exists()
    assert (lessons_dir / '2025-02-01-002.md').exists()
    assert not plan_dir.exists()


def test_cli_transition_not_found_exits_zero(plan_context):
    """Regression: transition with missing status.json exits 0 with TOON error output."""
    result = run_script(SCRIPT_PATH, 'transition', '--plan-id', 'nonexistent', '--completed', '1-init')
    assert result.success, f'Should exit 0, got: {result.stderr}'
    assert 'status: error' in result.stdout
    assert 'file_not_found' in result.stdout


# =============================================================================
# Regression Tests: cmd_transition(completed='5-execute') no longer seeds
# references.modified_files
# =============================================================================
#
# The worktree-single-source-of-truth plan deleted the modified_files ledger:
# the 5-execute transition used to run ``_collect_modified_files`` and write
# the result to ``references.modified_files``. That producer and its
# write-back are gone — the footprint is now derived on-demand from the live
# worktree diff (manage-references compute-footprint), never persisted. These
# tests pin that the transition is now footprint-free.


def _seed_execute_phase_plan(plan_dir, plan_id: str) -> None:
    """Create a plan with phases 1-4 done, 5-execute in_progress, and a
    references.json carrying base_branch. Returns nothing; mutates the
    fixture directory directly.
    """
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Transition Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    # Advance phases until 5-execute is the current (in_progress) phase.
    for phase in ('1-init', '2-refine', '3-outline', '4-plan'):
        cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))

    refs = {'base_branch': 'main', 'branch': f'feature/{plan_id}'}
    refs_path = plan_dir / 'references.json'
    refs_path.write_text(json.dumps(refs), encoding='utf-8')


def test_collect_modified_files_helper_is_removed():
    """The ``_collect_modified_files`` producer no longer exists.

    The footprint ledger was deleted in favour of the on-demand
    compute-footprint verb; the seeding helper must be gone so no code
    path can re-introduce a persisted modified_files write at transition.
    """
    assert not hasattr(_lifecycle, '_collect_modified_files'), (
        '_collect_modified_files must be deleted — the 5-execute transition '
        'no longer seeds references.modified_files (footprint is derived '
        'on-demand via manage-references compute-footprint).'
    )


def test_transition_5_execute_does_not_write_modified_files(plan_context):
    """The 5-execute transition must NOT add modified_files to references.json."""
    plan_dir = plan_context.plan_dir_for('transition-no-seed')
    _seed_execute_phase_plan(plan_dir, 'transition-no-seed')

    result = cmd_transition(Namespace(plan_id='transition-no-seed', completed='5-execute'))

    assert result['status'] == 'success'
    refs = json.loads((plan_dir / 'references.json').read_text(encoding='utf-8'))
    assert 'modified_files' not in refs, (
        f'5-execute transition seeded modified_files: {refs!r}. The footprint '
        f'ledger was removed — the transition must never touch references.json '
        f'for footprint.'
    )


def test_transition_5_execute_preserves_legacy_modified_files_untouched(plan_context):
    """A references.json that already carries a legacy modified_files key is
    left untouched by the transition — the transition neither reads nor
    rewrites the field.
    """
    plan_dir = plan_context.plan_dir_for('transition-legacy-untouched')
    _seed_execute_phase_plan(plan_dir, 'transition-legacy-untouched')
    # Inject a legacy ledger (as an archived/pre-migration plan might carry).
    refs_path = plan_dir / 'references.json'
    legacy = json.loads(refs_path.read_text(encoding='utf-8'))
    legacy['modified_files'] = ['legacy-a.py', 'legacy-b.py']
    refs_path.write_text(json.dumps(legacy), encoding='utf-8')

    result = cmd_transition(Namespace(plan_id='transition-legacy-untouched', completed='5-execute'))

    assert result['status'] == 'success'
    refs = json.loads(refs_path.read_text(encoding='utf-8'))
    assert refs.get('modified_files') == ['legacy-a.py', 'legacy-b.py'], (
        f'Transition rewrote a legacy modified_files key: {refs!r}. The '
        f'transition must not read or mutate the field at all.'
    )


# =============================================================================
# Regression Tests: cmd_archive atomically completes the active phase, and
# cmd_transition mirrors the same end-state when the LAST phase finishes.
# =============================================================================


def _seed_finalize_phase_plan(plan_id: str) -> None:
    """Create a plan whose phases 1..5 are done and 6-finalize is in_progress.

    Mirrors the end-of-execute state when phase-6-finalize is about to run
    its final step (archive-plan).
    """
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Atomic Archive Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    for phase in ('1-init', '2-refine', '3-outline', '4-plan', '5-execute'):
        cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='6-finalize'))


def test_archive_marks_final_phase_done_and_sets_complete(plan_context):
    """cmd_archive must close the active phase + set current_phase=complete BEFORE the move."""
    plan_id = 'archive-atomic-happy-path'
    _seed_finalize_phase_plan(plan_id)
    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False))

    assert result['status'] == 'success', f'archive failed: {result}'
    assert 'archived_to' in result, f'missing archived_to in {result}'

    archived_status_path = Path(result['archived_to']) / 'status.json'
    assert archived_status_path.exists(), (
        f'archived status.json missing at {archived_status_path} — '
        f'either move failed or archived_to points to wrong path'
    )

    archived_status = json.loads(archived_status_path.read_text(encoding='utf-8'))
    assert archived_status['current_phase'] == 'complete', (
        f"Expected archived current_phase='complete', got "
        f"{archived_status['current_phase']!r}. Atomic-archive fix "
        f'regressed: cmd_archive is not setting the post-finalize sentinel '
        f'before shutil.move runs.'
    )
    assert archived_status['phases'][-1]['status'] == 'done', (
        f"Expected archived phases[-1].status='done', got "
        f"{archived_status['phases'][-1]['status']!r}. Atomic-archive fix "
        f'regressed: cmd_archive is not marking the active phase done '
        f'before shutil.move runs.'
    )


def test_archive_dry_run_leaves_status_unchanged(plan_context):
    """--dry-run must NOT mutate status.json or create the archive directory."""
    plan_id = 'archive-atomic-dry-run'
    _seed_finalize_phase_plan(plan_id)

    live_status_path = plan_context.plan_dir_for(plan_id) / 'status.json'
    before = live_status_path.read_text(encoding='utf-8')

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=True))

    assert result['status'] == 'success'
    assert result.get('dry_run') is True, f'missing dry_run flag: {result}'
    assert 'would_archive_to' in result
    assert 'archived_to' not in result, (
        f'dry-run must NOT report archived_to: {result}'
    )

    assert not Path(result['would_archive_to']).exists(), (
        f"dry-run created the archive dir at {result['would_archive_to']} — "
        f'atomic-archive write block leaked into the dry-run path; the '
        f'`if args.dry_run:` early-return must precede the write block.'
    )

    after = live_status_path.read_text(encoding='utf-8')
    assert before == after, (
        'dry-run mutated the live status.json — atomic-archive write '
        'block leaked into the dry-run path; verify the early-return '
        'on args.dry_run runs before the write_status call.'
    )


# =============================================================================
# Test: cmd_archive --reason flag persistence
# =============================================================================


def test_archive_with_reason_persists_archived_reason_metadata(plan_context):
    """cmd_archive --reason=<value> must persist status.metadata.archived_reason."""
    plan_id = 'archive-reason-persists'
    _seed_finalize_phase_plan(plan_id)
    result = cmd_archive(
        Namespace(plan_id=plan_id, dry_run=False, reason='low_confidence')
    )

    assert result['status'] == 'success', f'archive failed: {result}'
    archived_status_path = Path(result['archived_to']) / 'status.json'
    assert archived_status_path.exists(), (
        f'archived status.json missing at {archived_status_path}'
    )

    archived_status = json.loads(archived_status_path.read_text(encoding='utf-8'))
    assert 'metadata' in archived_status, (
        'archived status.json missing metadata block — cmd_archive failed '
        'to setdefault metadata before writing archived_reason'
    )
    assert archived_status['metadata'].get('archived_reason') == 'low_confidence', (
        f"Expected metadata.archived_reason='low_confidence', got "
        f"{archived_status['metadata'].get('archived_reason')!r}. "
        f'--reason flag did not persist via setdefault before write_status.'
    )


def test_archive_without_reason_omits_archived_reason_field(plan_context):
    """cmd_archive without --reason must NOT introduce an archived_reason field."""
    plan_id = 'archive-reason-omitted'
    _seed_finalize_phase_plan(plan_id)
    result = cmd_archive(
        Namespace(plan_id=plan_id, dry_run=False, reason=None)
    )

    assert result['status'] == 'success', f'archive failed: {result}'
    archived_status_path = Path(result['archived_to']) / 'status.json'
    archived_status = json.loads(archived_status_path.read_text(encoding='utf-8'))

    metadata = archived_status.get('metadata', {})
    assert 'archived_reason' not in metadata, (
        f"Expected archived_reason absent from metadata when --reason "
        f"omitted, got metadata={metadata!r}. Additive-metadata contract "
        f"violated — cmd_archive must guard the write with "
        f"`if reason is not None:`."
    )


def test_archive_reason_attribute_missing_does_not_raise(plan_context):
    """cmd_archive must tolerate Namespace without a ``reason`` attribute."""
    plan_id = 'archive-reason-attr-missing'
    _seed_finalize_phase_plan(plan_id)
    # Intentionally omit ``reason`` from Namespace to simulate legacy callers.
    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False))

    assert result['status'] == 'success', (
        f'archive raised or failed when Namespace lacked reason attr: {result}'
    )
    archived_status_path = Path(result['archived_to']) / 'status.json'
    archived_status = json.loads(archived_status_path.read_text(encoding='utf-8'))
    metadata = archived_status.get('metadata', {})
    assert 'archived_reason' not in metadata, (
        f'Legacy Namespace path leaked an archived_reason key: {metadata!r}'
    )


def test_archive_dry_run_with_reason_does_not_mutate_status(plan_context):
    """--dry-run with --reason must NOT mutate live status.json or archive."""
    plan_id = 'archive-reason-dry-run'
    _seed_finalize_phase_plan(plan_id)

    live_status_path = plan_context.plan_dir_for(plan_id) / 'status.json'
    before = live_status_path.read_text(encoding='utf-8')

    result = cmd_archive(
        Namespace(plan_id=plan_id, dry_run=True, reason='dangling_worktree')
    )

    assert result['status'] == 'success'
    assert result.get('dry_run') is True, f'missing dry_run flag: {result}'
    assert 'archived_to' not in result, (
        f'dry-run must NOT report archived_to even with --reason: {result}'
    )

    after = live_status_path.read_text(encoding='utf-8')
    assert before == after, (
        'dry-run with --reason mutated live status.json — the metadata '
        'write block leaked past the dry-run early-return.'
    )


def test_archive_reason_cli_round_trip_persists_to_archive(plan_context):
    """End-to-end CLI invocation: ``manage-status archive --reason=X`` persists."""
    plan_id = 'archive-reason-cli'
    _seed_finalize_phase_plan(plan_id)

    result = run_script(
        SCRIPT_PATH,
        'archive',
        '--plan-id',
        plan_id,
        '--reason',
        'orphan_directory',
    )
    assert result.returncode == 0, (
        f'CLI archive --reason failed (rc={result.returncode}): '
        f'stdout={result.stdout!r} stderr={result.stderr!r}'
    )

    # Locate the archive by parsing the TOON output for ``archived_to``.
    archived_to_line = next(
        (line for line in result.stdout.splitlines() if 'archived_to' in line),
        None,
    )
    assert archived_to_line is not None, (
        f'CLI output missing archived_to: {result.stdout!r}'
    )
    archived_path = Path(archived_to_line.split(':', 1)[1].strip().strip('"'))
    archived_status = json.loads(
        (archived_path / 'status.json').read_text(encoding='utf-8')
    )
    assert (
        archived_status.get('metadata', {}).get('archived_reason')
        == 'orphan_directory'
    ), (
        f'CLI --reason did not round-trip into archived status.json: '
        f'{archived_status.get("metadata")!r}'
    )


def test_transition_last_phase_sets_complete(plan_context):
    """cmd_transition must mirror cmd_archive when completing the LAST phase."""
    plan_id = 'transition-last-phase-complete'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_transition(Namespace(plan_id=plan_id, completed='6-finalize'))

    assert result['status'] == 'success'
    assert result.get('message') == 'All phases completed', (
        f'expected terminal message, got {result}'
    )
    assert 'next_phase' not in result, (
        f'cmd_transition on the last phase must not return next_phase: {result}'
    )

    live_status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert live_status['current_phase'] == 'complete', (
        f"Expected current_phase='complete' after transition --completed "
        f'6-finalize, got {live_status["current_phase"]!r}. Symmetry '
        f'with cmd_archive regressed: cmd_transition is not setting '
        f'the post-finalize sentinel for the last phase.'
    )
    assert live_status['phases'][-1]['status'] == 'done', (
        f"Expected phases[-1].status='done', got "
        f'{live_status["phases"][-1]["status"]!r}.'
    )


# =============================================================================
# Regression Tests: cmd_list discovers moved-in worktree plans (ADR-002)
# =============================================================================
#
# Per ADR-002 a plan's runtime state (its plan directory) MOVES into the
# plan's own worktree at phase-5 entry and back to main at finalize. A plan
# that is mid-flight in phase-5+ therefore no longer lives under the main
# checkout's plans_dir — a main-only walk is BLIND to it. cmd_list must scan
# get_worktree_root()'s child worktrees for moved-in plans and surface them
# with location='worktree'. These tests pin that discovery so a regression to
# the old main-only walk fails loudly.
#
# Worktree-resident plan layout probed by cmd_list:
#   {base_dir}/worktrees/{wt}/.plan/local/plans/{plan_id}/status.json
# Under the plan_context fixture, base_dir == PLAN_BASE_DIR == tmp_path, so
# the helper materializes that exact path inside the isolated fixture tree.


def _seed_worktree_resident_plan(
    fixture_dir: Path,
    plan_id: str,
    *,
    worktree_name: str | None = None,
    current_phase: str = '5-execute',
) -> Path:
    """Materialize a moved-in worktree plan and return its status.json path.

    Mirrors the ADR-002 phase-5 move-in: the plan directory lives under
    ``{fixture_dir}/worktrees/{worktree_name}/.plan/local/plans/{plan_id}/``
    (NOT under the main ``{fixture_dir}/plans/`` tree). ``worktree_name``
    defaults to ``plan_id`` — the canonical ``worktree-create`` layout where
    the worktree dir is named for the plan it hosts.
    """
    wt = worktree_name or plan_id
    wt_plan_dir = fixture_dir / 'worktrees' / wt / '.plan' / 'local' / 'plans' / plan_id
    wt_plan_dir.mkdir(parents=True, exist_ok=True)
    status_path = wt_plan_dir / 'status.json'
    status_path.write_text(
        json.dumps({'current_phase': current_phase, 'title': f'Worktree {plan_id}'}),
        encoding='utf-8',
    )
    return status_path


def test_list_discovers_moved_in_worktree_plan(plan_context):
    """Regression: cmd_list surfaces a plan whose dir moved into a worktree.

    The plan directory lives ONLY under the worktree tree (the ADR-002
    move-in removed it from the main plans_dir). A main-only walk returns
    total=0; the fixed cmd_list must discover it via the worktree scan and
    tag it location='worktree'.
    """
    # Remove the fixture's default main-checkout plan so the worktree plan is
    # the only discoverable plan — total must be exactly 1.
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)
    _seed_worktree_resident_plan(plan_context.fixture_dir, 'moved-in-plan')

    result = cmd_list(Namespace(filter=None))

    assert result['status'] == 'success'
    assert result['total'] == 1, (
        f'cmd_list is blind to the moved-in worktree plan: expected total=1, '
        f"got {result['total']} plans={result['plans']!r}. A regression to the "
        f'main-only plans_dir walk drops every phase-5+ plan whose directory '
        f'moved into its worktree (ADR-002).'
    )
    entry = result['plans'][0]
    assert entry['id'] == 'moved-in-plan'
    assert entry['location'] == 'worktree', (
        f"Moved-in plan must be tagged location='worktree', got "
        f"{entry['location']!r}."
    )
    assert entry['current_phase'] == '5-execute'


def test_list_merges_main_and_worktree_plans_sorted(plan_context):
    """cmd_list merges main-checkout and worktree plans, sorted by id.

    One legitimate plan on the main checkout (location='current') plus one
    moved-in worktree plan (location='worktree') → both returned, deduped,
    and sorted by id.
    """
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)
    # Main-checkout plan via cmd_create (writes a real status.json under plans_dir).
    cmd_create(
        Namespace(
            plan_id='alpha-on-main',
            title='Main Plan',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    # Worktree-resident plan whose id sorts AFTER the main plan.
    _seed_worktree_resident_plan(plan_context.fixture_dir, 'zeta-in-worktree')

    result = cmd_list(Namespace(filter=None))

    assert result['status'] == 'success'
    assert result['total'] == 2, (
        f'Expected both the main-checkout and worktree plans, got '
        f"total={result['total']} plans={result['plans']!r}."
    )
    ids = [p['id'] for p in result['plans']]
    assert ids == ['alpha-on-main', 'zeta-in-worktree'], (
        f'Merged plans must be sorted by id regardless of source, got {ids}.'
    )
    by_id = {p['id']: p for p in result['plans']}
    assert by_id['alpha-on-main']['location'] == 'current'
    assert by_id['zeta-in-worktree']['location'] == 'worktree'


def test_list_dedupes_plan_present_in_both_main_and_worktree(plan_context):
    """Defensive dedup: a plan present on main AND in a worktree appears once.

    The transient both-present window (before the move-in fully removes the
    main copy) must not double-count. The main-checkout entry wins
    (location='current') because the main scan runs first and records the id.
    """
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)
    cmd_create(
        Namespace(
            plan_id='dual-present',
            title='Dual Present',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    # Same id also seeded in a worktree (transient both-present window).
    _seed_worktree_resident_plan(plan_context.fixture_dir, 'dual-present')

    result = cmd_list(Namespace(filter=None))

    assert result['status'] == 'success'
    assert result['total'] == 1, (
        f"Plan present in both sources must appear exactly once, got "
        f"total={result['total']} plans={result['plans']!r}."
    )
    entry = result['plans'][0]
    assert entry['id'] == 'dual-present'
    assert entry['location'] == 'current', (
        f"The main-checkout entry must win dedup (main scan runs first), got "
        f"location={entry['location']!r}."
    )


def test_list_worktree_plan_honours_phase_filter(plan_context):
    """The --filter phase predicate applies to worktree-resident plans too.

    A worktree plan in phase 5-execute is filtered out by --filter 3-outline
    and surfaced by --filter 5-execute — the worktree scan honours the same
    _passes_phase_filter predicate as the main scan.
    """
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)
    _seed_worktree_resident_plan(
        plan_context.fixture_dir, 'filtered-worktree', current_phase='5-execute'
    )

    excluded = cmd_list(Namespace(filter='3-outline'))
    assert excluded['status'] == 'success'
    assert excluded['total'] == 0, (
        f'Worktree plan in 5-execute must be excluded by --filter 3-outline, '
        f"got {excluded['plans']!r}. The worktree scan must apply the phase "
        f'filter, not just the main scan.'
    )

    included = cmd_list(Namespace(filter='5-execute'))
    assert included['status'] == 'success'
    assert included['total'] == 1
    assert included['plans'][0]['id'] == 'filtered-worktree'


def test_list_cli_surfaces_worktree_plan(plan_context):
    """End-to-end CLI: ``manage-status list`` surfaces the moved-in plan.

    Exercises the full script entry point (argparse → cmd_list → TOON), not
    just the in-process handler, so the subcommand wiring is covered. The
    fixture's PLAN_BASE_DIR is propagated to the subprocess via run_script's
    os.environ.copy(), so the child resolves the same worktree tree.
    """
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)
    _seed_worktree_resident_plan(plan_context.fixture_dir, 'cli-worktree-plan')

    result = run_script(SCRIPT_PATH, 'list')

    assert result.success, (
        f'list subcommand must be resolvable via the script entry point. '
        f'stderr: {result.stderr}'
    )
    assert 'status: success' in result.stdout
    assert 'cli-worktree-plan' in result.stdout, (
        f'CLI list output missing the moved-in worktree plan: {result.stdout!r}'
    )
    assert 'worktree' in result.stdout


# =============================================================================
# Tests: cmd_list_orphans (orphan-dir cleanup pass)
# =============================================================================


def _seed_legitimate_plan(plan_id: str) -> None:
    """cmd_create a plan with a status.json so cmd_list_orphans skips it."""
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title=f'Legitimate {plan_id}',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def test_list_orphans_empty_plans_dir(plan_context):
    """(a) Empty plans_dir returns total: 0 and orphans: []."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-empty'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success'
    assert result['total'] == 0
    assert result['orphans'] == []


def test_list_orphans_skips_dir_with_status_json(plan_context):
    """(b) Directory present with status.json is NOT listed as an orphan."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-skip-valid'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)
    _seed_legitimate_plan('legit-plan')

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success'
    assert result['total'] == 0, (
        f"Legitimate plan with status.json must NOT be reported as orphan, got: {result['orphans']}"
    )
    assert result['orphans'] == []


def test_list_orphans_includes_dir_without_status_json_with_subdirs(plan_context):
    """(c) Directory without status.json but with logs/ or work/ subdirs IS listed."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-with-subdirs'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    orphan_dir = plan_context.fixture_dir / 'plans' / 'orphan-with-subdirs'
    orphan_dir.mkdir(parents=True)
    (orphan_dir / 'logs').mkdir()
    (orphan_dir / 'work').mkdir()

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success'
    assert result['total'] == 1
    assert len(result['orphans']) == 1
    entry = result['orphans'][0]
    assert entry['id'] == 'orphan-with-subdirs'
    assert entry['path'] == str(orphan_dir)
    assert entry['contents'] == ['logs', 'work']


def test_list_orphans_returns_multiple_sorted(plan_context):
    """(d) Multiple orphans are all returned, sorted by id."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-many'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    plans_dir = plan_context.fixture_dir / 'plans'
    for name in ('zeta-orphan', 'alpha-orphan', 'mid-orphan'):
        d = plans_dir / name
        d.mkdir(parents=True)
        (d / 'stray.txt').write_text('x')

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success'
    assert result['total'] == 3
    ids = [o['id'] for o in result['orphans']]
    assert ids == ['alpha-orphan', 'mid-orphan', 'zeta-orphan'], (
        f'orphans must be returned in sorted id order, got {ids}'
    )
    for orphan in result['orphans']:
        assert orphan['contents'] == ['stray.txt']


def test_list_orphans_mixed_eight_orphans_plus_two_legitimate_plans(plan_context):
    """CLI resolvability + filter contract: 8 orphans + 2 legitimate plans → ONLY the 8 orphans returned."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-mixed'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    plans_dir = plan_context.fixture_dir / 'plans'
    orphan_names = [f'orphan-{i:02d}' for i in range(8)]
    for name in orphan_names:
        (plans_dir / name).mkdir(parents=True)

    _seed_legitimate_plan('lesson-alpha')
    _seed_legitimate_plan('lesson-beta')

    result = cmd_list_orphans(Namespace())
    assert result['status'] == 'success'
    assert result['total'] == 8, (
        f"Expected exactly 8 orphans (legitimate lesson-* plans must be filtered out), "
        f"got total={result['total']} ids={[o['id'] for o in result['orphans']]}"
    )
    returned_ids = [o['id'] for o in result['orphans']]
    assert returned_ids == sorted(orphan_names), (
        f'Expected sorted orphan ids {sorted(orphan_names)}, got {returned_ids}'
    )
    assert 'lesson-alpha' not in returned_ids
    assert 'lesson-beta' not in returned_ids

    cli_result = run_script(SCRIPT_PATH, 'list-orphans')
    assert cli_result.success, (
        f'list-orphans subcommand must be resolvable via the script entry point. '
        f'stderr: {cli_result.stderr}'
    )
    assert 'status: success' in cli_result.stdout
    for name in orphan_names:
        assert name in cli_result.stdout, f'orphan {name} missing from CLI output'
    assert 'lesson-alpha' not in cli_result.stdout
    assert 'lesson-beta' not in cli_result.stdout


def test_list_orphans_unreadable_dir_emits_sentinel(plan_context, monkeypatch):
    """(1) OSError on iterdir → contents=['<unreadable>'] sentinel."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-unreadable'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    orphan_dir = plan_context.fixture_dir / 'plans' / 'unreadable-orphan'
    orphan_dir.mkdir(parents=True)

    from pathlib import Path as _Path

    original_iterdir = _Path.iterdir

    def patched_iterdir(self):
        if self == orphan_dir:
            raise PermissionError('simulated unreadable dir')
        return original_iterdir(self)

    monkeypatch.setattr(_Path, 'iterdir', patched_iterdir)

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success'
    assert result['total'] == 1
    entry = result['orphans'][0]
    assert entry['id'] == 'unreadable-orphan'
    assert entry['contents'] == ['<unreadable>'], (
        f'Unreadable orphan must surface ["<unreadable>"] sentinel, got '
        f'{entry["contents"]!r}. An empty list would trigger silent '
        f'deletion under planning.md Step 3b.'
    )


def test_list_orphans_file_at_plans_dir_returns_zero(monkeypatch, tmp_path):
    """(2) Stray FILE at plans_dir path → total=0 cleanly, no exception."""
    stray_file = tmp_path / 'plans'
    stray_file.write_text('this is a file, not a directory\n')

    monkeypatch.setattr(_query, 'get_plans_dir', lambda: stray_file)

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success', (
        f'Stray file at plans_dir must yield clean success, got {result!r}. '
        f'Regression: plans_dir.exists() returned True for the file and '
        f'iterdir() raised NotADirectoryError.'
    )
    assert result['total'] == 0
    assert result['orphans'] == []


def test_list_orphans_empty_status_json_not_flagged(plan_context, monkeypatch):
    """(3) Empty ``{}`` status.json must NOT be reported as orphan."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-empty-status'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    plans_dir = plan_context.fixture_dir / 'plans'
    plan_dir = plans_dir / 'empty-status-plan'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success'
    assert result['total'] == 0, (
        f'Empty {{}} status.json must NOT be flagged as orphan (matches '
        f'require_plan_exists file-presence guard), got '
        f'total={result["total"]} orphans={result["orphans"]!r}. '
        f'Regression: the filter is using parsed-truthy `if status:` '
        f'instead of `(plan_dir / "status.json").is_file()`.'
    )
    assert result['orphans'] == []


# =============================================================================
# Regression Tests: cmd_transition inline strict-verify guard for guarded
# boundaries (folded from the standalone phase_handshake verify --strict step
# that orchestrator workflow docs used to issue separately at 5-execute -> 6-finalize).
# =============================================================================

# Use STANDARD imports for handshake modules so the monkeypatch in the
# fixtures below hits the same module instance that ``_cmd_lifecycle.cmd_verify``
# reads at runtime.
_PLAN_HANDSHAKE_SCRIPTS_DIR = str(
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'plan-marshall'
    / 'scripts'
)
if _PLAN_HANDSHAKE_SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _PLAN_HANDSHAKE_SCRIPTS_DIR)

import _handshake_commands as _cmds  # noqa: E402
import _invariants as _inv  # noqa: E402


@pytest.fixture
def _stubbed_invariants(monkeypatch):
    """Deterministic invariant registry shared across cmd_capture / cmd_verify."""
    state = {
        'main_sha': 'abc123',
        'main_dirty': 0,
        'main_dirty_files': [],
        'worktree_sha': None,
        'worktree_dirty': None,
        'worktree_orphan': None,
        'task_state_hash': 'hash-tasks',
        'qgate_open_count': 0,
        'config_hash': 'hash-cfg',
        'unfinished_tasks_count': 2,
        'phase_steps_complete': None,
        'pending_findings_by_type': '',
        'pending_findings_blocking_count': 0,
    }

    def always(_pid, _md):
        return True

    def make_capture(name):
        def _cap(_pid, _md, _phase):
            return state[name]

        return _cap

    stubbed = [
        ('main_sha', always, make_capture('main_sha')),
        ('main_dirty', always, make_capture('main_dirty')),
        ('main_dirty_files', always, make_capture('main_dirty_files')),
        ('task_state_hash', always, make_capture('task_state_hash')),
        ('qgate_open_count', always, make_capture('qgate_open_count')),
        ('config_hash', always, make_capture('config_hash')),
        ('unfinished_tasks_count', always, make_capture('unfinished_tasks_count')),
        ('pending_findings_by_type', always, make_capture('pending_findings_by_type')),
        ('pending_findings_blocking_count', always, make_capture('pending_findings_blocking_count')),
    ]
    monkeypatch.setattr(_inv, 'INVARIANTS', stubbed)
    monkeypatch.setattr(_cmds, 'INVARIANTS', stubbed)
    return state


@pytest.fixture
def _stub_metadata(monkeypatch):
    """Replace _load_status_metadata so cmd_verify sees a metadata dict free
    of worktree fields (avoids the worktree-resolution assertion).
    """
    md: dict = {}
    monkeypatch.setattr(_cmds, '_load_status_metadata', lambda _pid: md)
    return md


def _seed_plan_with_5_execute_capture(plan_id):
    """Create a plan, advance to 5-execute, capture the handshake row."""
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Transition Guard Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    for phase in ('1-init', '2-refine', '3-outline', '4-plan'):
        cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))
    _cmds.cmd_capture(
        Namespace(plan_id=plan_id, phase='5-execute', override=False, reason=None, strict=False)
    )


def _seed_plan_with_4_plan_capture(plan_id):
    """Create a plan, advance to 4-plan, capture the handshake row."""
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Transition Guard Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    for phase in ('1-init', '2-refine', '3-outline'):
        cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='4-plan'))
    _cmds.cmd_capture(
        Namespace(plan_id=plan_id, phase='4-plan', override=False, reason=None, strict=False)
    )


def test_transition_5_execute_refuses_on_handshake_drift(plan_context, _stubbed_invariants, _stub_metadata):
    """cmd_transition refuses to advance when the captured 5-execute row drifts."""
    plan_id = 'transition-drift-5exec'
    _seed_plan_with_5_execute_capture(plan_id)

    _stubbed_invariants['main_sha'] = 'drifted-sha-xyz'
    plan_dir = plan_context.plan_dir_for(plan_id)
    status_before = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'drift', (
        f'Expected status: drift on guarded-boundary transition with drifted '
        f'capture, got {result!r}. The inline guard in cmd_transition is not '
        f'firing for 5-execute -> 6-finalize.'
    )
    assert result['phase'] == '5-execute'
    diff_names = {d['invariant'] for d in result['diffs']}
    assert 'main_sha' in diff_names

    status_after = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    assert status_after['current_phase'] == status_before['current_phase'] == '5-execute', (
        'cmd_transition wrote status despite drift — the guard is not '
        'short-circuiting before write_status.'
    )
    assert status_after['phases'] == status_before['phases'], (
        'Phase status list mutated despite drift refusal — write_status fired.'
    )


def test_transition_5_execute_drift_toon_byte_equivalent(plan_context, _stubbed_invariants, _stub_metadata):
    """The dict returned by cmd_transition on drift must equal cmd_verify's dict."""
    plan_id = 'transition-drift-equiv'
    _seed_plan_with_5_execute_capture(plan_id)
    _stubbed_invariants['main_sha'] = 'drifted-sha-equiv'

    transition_result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))
    verify_result = _cmds.cmd_verify(
        Namespace(plan_id=plan_id, phase='5-execute', strict=True)
    )

    assert transition_result == verify_result, (
        'cmd_transition drift dict diverges from cmd_verify dict. '
        f'transition={transition_result!r} verify={verify_result!r}. '
        'The inline guard MUST return the verify result unchanged.'
    )


def test_transition_4_plan_skips_handshake_verify_on_drift(plan_context, _stubbed_invariants, _stub_metadata):
    """cmd_transition --completed 4-plan ignores handshake drift."""
    plan_id = 'transition-4plan-skip'
    _seed_plan_with_4_plan_capture(plan_id)

    _stubbed_invariants['main_sha'] = 'drifted-sha-4plan'

    result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))

    assert result is not None
    assert result['status'] == 'success', (
        f'cmd_transition refused a non-guarded transition (4-plan -> '
        f'5-execute) despite drift, got {result!r}. The boundary set '
        f"_BLOCKING_BOUNDARIES MUST gate the verify call — non-guarded "
        f'transitions stay drift-blind.'
    )
    assert result['next_phase'] == '5-execute'

    status_after = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert status_after['current_phase'] == '5-execute', (
        'Non-guarded transition failed to advance current_phase despite '
        'returning success — write_status did not fire.'
    )


# =============================================================================
# Test: Hybrid loopback contract — `--loop-back-target` granularity flag
# =============================================================================

_cmd_mark_step = load_script_module('plan-marshall', 'manage-status', '_cmd_mark_step.py', '_cmd_mark_step')
cmd_mark_step_done = _cmd_mark_step.cmd_mark_step_done


def _mark_step_args(
    plan_id: str,
    phase: str,
    step: str,
    outcome: str,
    *,
    force: bool = False,
    display_detail: str | None = None,
    head_at_completion: str | None = None,
    loop_back_target: str | None = None,
) -> Namespace:
    """Build a Namespace for cmd_mark_step_done that mirrors the argparse layer."""
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        step=step,
        outcome=outcome,
        force=force,
        display_detail=display_detail,
        head_at_completion=head_at_completion,
        loop_back_target=loop_back_target,
    )


def _setup_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Loop-back Target Tests',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


class TestLoopBackTargetValidation:
    """The `--loop-back-target` flag is REQUIRED on every loop_back outcome
    and FORBIDDEN on every other outcome.
    """

    def test_loop_back_without_target_returns_missing_error(self, plan_context) -> None:
        """Case 1: omitting `--loop-back-target` on a loop_back outcome
        returns `error: missing_loop_back_target`."""
        plan_id = 'lbt-missing-target'
        _setup_plan(plan_id)
        result = cmd_mark_step_done(
            _mark_step_args(
                plan_id,
                '6-finalize',
                'automatic-review',
                'loop_back',
                display_detail='loop-back without target',
                loop_back_target=None,
            )
        )
        assert result['status'] == 'error'
        assert result['error'] == 'missing_loop_back_target'
        assert 'required' in result['message'].lower()

    def test_loop_back_with_target_5_execute_persists_field(self, plan_context) -> None:
        """Case 2: `--loop-back-target 5-execute` succeeds and persists."""
        plan_id = 'lbt-target-5-execute'
        _setup_plan(plan_id)
        result = cmd_mark_step_done(
            _mark_step_args(
                plan_id,
                '6-finalize',
                'sonar-roundtrip',
                'loop_back',
                display_detail='loop-back iter 1 (target=5-execute)',
                loop_back_target='5-execute',
            )
        )
        assert result['status'] == 'success'
        assert result['outcome'] == 'loop_back'
        assert result['loop_back_target'] == '5-execute'

        status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
        entry = status['metadata']['phase_steps']['6-finalize']['sonar-roundtrip']
        assert entry['outcome'] == 'loop_back'
        assert entry['loop_back_target'] == '5-execute', (
            'Persisted phase_steps record must carry loop_back_target=5-execute'
        )

    def test_loop_back_with_target_6_finalize_persists_field(self, plan_context) -> None:
        """Case 3: `--loop-back-target 6-finalize` succeeds and persists."""
        plan_id = 'lbt-target-6-finalize'
        _setup_plan(plan_id)
        result = cmd_mark_step_done(
            _mark_step_args(
                plan_id,
                '6-finalize',
                'automatic-review',
                'loop_back',
                display_detail='loop-back iter 1 (target=6-finalize)',
                loop_back_target='6-finalize',
            )
        )
        assert result['status'] == 'success'
        assert result['outcome'] == 'loop_back'
        assert result['loop_back_target'] == '6-finalize'

        status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
        entry = status['metadata']['phase_steps']['6-finalize']['automatic-review']
        assert entry['outcome'] == 'loop_back'
        assert entry['loop_back_target'] == '6-finalize', (
            'Persisted phase_steps record must carry loop_back_target=6-finalize'
        )

    def test_loop_back_with_invalid_target_rejected_by_argparse(self, plan_context) -> None:
        """Case 4: argparse `choices` enforcement rejects invalid value."""
        plan_id = 'lbt-invalid-target'
        _setup_plan(plan_id)
        result = run_script(
            SCRIPT_PATH,
            'mark-step-done',
            '--plan-id',
            plan_id,
            '--phase',
            '6-finalize',
            '--step',
            'automatic-review',
            '--outcome',
            'loop_back',
            '--loop-back-target',
            'invalid-phase',
            '--display-detail',
            'loop-back invalid target',
        )
        assert result.returncode == 2, (
            f'argparse must reject invalid --loop-back-target value '
            f'with exit code 2; got {result.returncode}'
        )
        assert 'invalid choice' in result.stderr.lower() or 'invalid-phase' in result.stderr.lower()

    def test_loop_back_target_forbidden_on_non_loop_back_outcome(self, plan_context) -> None:
        """Guard: supplying `--loop-back-target` alongside a non-loop_back outcome errors."""
        plan_id = 'lbt-forbidden-on-done'
        _setup_plan(plan_id)
        result = cmd_mark_step_done(
            _mark_step_args(
                plan_id,
                '6-finalize',
                'push',
                'done',
                display_detail='step complete',
                loop_back_target='5-execute',
            )
        )
        assert result['status'] == 'error'
        assert result['error'] == 'unexpected_loop_back_target'

    def test_loop_back_target_invalid_at_api_layer(self, plan_context) -> None:
        """API-layer guard: bypassing argparse with invalid loop_back_target value."""
        plan_id = 'lbt-api-invalid-target'
        _setup_plan(plan_id)
        result = cmd_mark_step_done(
            _mark_step_args(
                plan_id,
                '6-finalize',
                'automatic-review',
                'loop_back',
                display_detail='loop-back invalid api target',
                loop_back_target='not-a-real-phase',
            )
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_loop_back_target'


# =============================================================================
# Fixed actionable-vs-knowledge rule at the 5-execute -> 6-finalize boundary
# =============================================================================
#
# Integration-level assertions over the REAL ``_capture_pending_findings_blocking_count``
# (narrowed INVARIANTS registry) driven through ``cmd_capture --phase 6-finalize``:
# a pending KNOWLEDGE-type finding does NOT block the guarded boundary; a pending
# ACTIONABLE-type finding DOES. No marshal.json blocking_finding_types partition
# is involved — the rule is hardcoded in ``_invariants._ACTIONABLE_FINDING_TYPES``.


@pytest.fixture
def _only_blocking_invariant(monkeypatch):
    """Narrow INVARIANTS to just the real pending-findings-blocking entry."""
    stubbed = [
        (
            'pending_findings_blocking_count',
            lambda _pid, _md: True,
            _inv._capture_pending_findings_blocking_count,
        ),
    ]
    monkeypatch.setattr(_inv, 'INVARIANTS', stubbed)
    monkeypatch.setattr(_cmds, 'INVARIANTS', stubbed)


def _stub_finding_queries(monkeypatch, per_type: dict[str, int], qgate: int = 0) -> None:
    """Stub the per-type and qgate-aggregator query helpers."""
    monkeypatch.setattr(
        _inv, '_query_pending_count_for_type', lambda _pid, ft: per_type.get(ft, 0)
    )
    monkeypatch.setattr(
        _inv, '_query_pending_qgate_count_aggregated', lambda _pid: qgate
    )


def test_finalize_boundary_pending_knowledge_finding_does_not_block(
    plan_context, _only_blocking_invariant, _stub_metadata, monkeypatch
):
    """A pending KNOWLEDGE-type finding (``insight``) clears the 6-finalize
    capture under the fixed rule."""
    _stub_finding_queries(monkeypatch, {'insight': 5, 'tip': 3})

    result = _cmds.cmd_capture(
        Namespace(plan_id='fixed-rule-knowledge', phase='6-finalize', override=False, reason=None, strict=False)
    )

    assert result['status'] == 'success'
    assert result['invariants']['pending_findings_blocking_count'] in (0, '0')


def test_finalize_boundary_pending_actionable_finding_blocks(
    plan_context, _only_blocking_invariant, _stub_metadata, monkeypatch
):
    """A pending ACTIONABLE-type finding (``build-error``) refuses the 6-finalize
    capture under the fixed rule."""
    _stub_finding_queries(monkeypatch, {'build-error': 1})

    result = _cmds.cmd_capture(
        Namespace(plan_id='fixed-rule-actionable', phase='6-finalize', override=False, reason=None, strict=False)
    )

    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['blocking_count'] == 1
    assert result['blocking_types'] == list(_inv._ACTIONABLE_FINDING_TYPES)
    assert result['per_type']['build-error'] == 1


# =============================================================================
# Regression Tests: persisted-title-state-write drive seam (Defects 1 & 2)
# =============================================================================
#
# Every current_phase write fires the shared _surface_drive seam AFTER
# write_status — one bind (session->plan, last-driven-wins; Defect 2) plus one
# repaint (icon-optional title push; Defect 1). cmd_transition is the phase-
# advance writer covered here; the seam internals (bind+repaint ordering, the
# no-icon repaint contract, delegation-failure swallowing, and the executor-
# absent no-op guard) are pinned directly on _status_core.

_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_status_core_drive')


def test_cmd_transition_fires_drive_seam_after_write(plan_context, monkeypatch):
    """cmd_transition fires _surface_drive exactly once (with the plan_id) on advance."""
    plan_id = 'drive-seam-transition'
    _seed_execute_phase_plan(plan_context.plan_dir_for(plan_id), plan_id)

    calls = []
    monkeypatch.setattr(_lifecycle, '_surface_drive', lambda pid: calls.append(pid))

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result['status'] == 'success'
    assert calls == [plan_id], (
        f'cmd_transition must fire the drive seam exactly once with the plan_id '
        f'after write_status, got {calls!r}.'
    )


def test_cmd_transition_drift_refusal_does_not_fire_drive_seam(
    plan_context, _stubbed_invariants, _stub_metadata, monkeypatch
):
    """A guarded-boundary drift refusal returns BEFORE write_status — the drive
    seam must NOT fire (no phase advanced, nothing to repaint)."""
    plan_id = 'drive-seam-no-fire-on-drift'
    _seed_plan_with_5_execute_capture(plan_id)
    _stubbed_invariants['main_sha'] = 'drifted-no-fire'

    calls = []
    monkeypatch.setattr(_lifecycle, '_surface_drive', lambda pid: calls.append(pid))

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result['status'] == 'drift'
    assert calls == [], (
        f'The drive seam must not fire when the transition is refused before '
        f'write_status, got {calls!r}.'
    )


def test_surface_drive_fires_bind_then_repaint(monkeypatch):
    """_surface_drive fires exactly one bind then one repaint, both with the plan_id."""
    events = []
    monkeypatch.setattr(_core, '_drive_bind', lambda pid: events.append(('bind', pid)))
    monkeypatch.setattr(_core, '_drive_repaint', lambda pid: events.append(('repaint', pid)))

    _core._surface_drive('seam-plan')

    assert events == [('bind', 'seam-plan'), ('repaint', 'seam-plan')], (
        f'_surface_drive must fire one bind then one repaint, got {events!r}.'
    )


def test_drive_bind_and_repaint_target_correct_verbs(monkeypatch):
    """_drive_bind -> session bind; _drive_repaint -> session push-title-token (NO --icon)."""
    calls = []
    monkeypatch.setattr(_core, '_run_executor', lambda notation, *args: calls.append((notation, args)))

    _core._drive_bind('bind-plan')
    _core._drive_repaint('paint-plan')

    assert calls[0] == (
        'plan-marshall:platform-runtime:platform_runtime',
        ('session', 'bind', '--plan-id', 'bind-plan'),
    )
    assert calls[1] == (
        'plan-marshall:platform-runtime:platform_runtime',
        ('session', 'push-title-token', '--plan-id', 'paint-plan'),
    ), 'repaint must push with NO --icon (plain repaint, default active icon)'
    assert '--icon' not in calls[1][1], 'the repaint seam must never pass --icon (Defect 1 plain repaint)'


def test_surface_drive_swallows_delegation_failure(monkeypatch):
    """A raising primitive is fully swallowed — _surface_drive never propagates."""
    def _boom(_pid):
        raise RuntimeError('delegation blew up')

    monkeypatch.setattr(_core, '_drive_bind', _boom)

    # Must NOT raise — the seam is best-effort and self-guarding.
    _core._surface_drive('seam-plan')


def test_run_executor_skips_when_executor_absent(monkeypatch, tmp_path):
    """_run_executor is a no-op (no subprocess) when the executor is not on disk."""
    missing = tmp_path / 'execute-script.py'  # deliberately not created
    monkeypatch.setattr(_core, 'get_executor_path', lambda: missing)
    spawned = []
    monkeypatch.setattr(_core.subprocess, 'run', lambda *a, **k: spawned.append(a))

    _core._run_executor('plan-marshall:platform-runtime:platform_runtime', 'session', 'bind', '--plan-id', 'x')

    assert spawned == [], 'an absent executor must skip the subprocess spawn entirely'


def test_run_executor_spawns_when_executor_present(monkeypatch, tmp_path):
    """_run_executor spawns the executor subprocess when the script exists on disk."""
    present = tmp_path / 'execute-script.py'
    present.write_text('# stub executor\n', encoding='utf-8')
    monkeypatch.setattr(_core, 'get_executor_path', lambda: present)
    captured = []
    monkeypatch.setattr(_core.subprocess, 'run', lambda cmd, **k: captured.append(cmd))

    _core._run_executor(
        'plan-marshall:platform-runtime:platform_runtime', 'session', 'push-title-token', '--plan-id', 'x'
    )

    assert len(captured) == 1, f'exactly one spawn expected, got {captured!r}'
    cmd = captured[0]
    assert str(present) in cmd
    assert cmd[-4:] == ['session', 'push-title-token', '--plan-id', 'x']


def test_run_executor_swallows_subprocess_oserror(monkeypatch, tmp_path):
    """A subprocess OSError is swallowed — _run_executor never propagates."""
    present = tmp_path / 'execute-script.py'
    present.write_text('# stub executor\n', encoding='utf-8')
    monkeypatch.setattr(_core, 'get_executor_path', lambda: present)

    def _explode(*_a, **_k):
        raise OSError('simulated spawn failure')

    monkeypatch.setattr(_core.subprocess, 'run', _explode)

    # Must NOT raise.
    _core._run_executor('plan-marshall:platform-runtime:platform_runtime', 'session', 'bind', '--plan-id', 'x')
