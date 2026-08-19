#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py transition + archive + delete + orphans + loop-back."""


import json
from argparse import Namespace
from pathlib import Path

from _manage_status_transition_fixtures import (
    SCRIPT_PATH,
    _lifecycle,
    _seed_execute_phase_plan,
    _seed_finalize_phase_plan,
    cmd_archive,
    cmd_transition,
)

from conftest import run_script


def test_cli_transition_not_found_exits_zero(plan_context):
    """Regression: transition with missing status.json exits 0 with TOON error output."""
    result = run_script(SCRIPT_PATH, 'transition', '--plan-id', 'nonexistent', '--completed', '1-init')
    assert result.success, f'Should exit 0, got: {result.stderr}'
    assert 'status: error' in result.stdout
    assert 'file_not_found' in result.stdout


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
