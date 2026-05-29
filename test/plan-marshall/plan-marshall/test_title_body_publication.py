#!/usr/bin/env python3
"""Tests for title-body publication hook on manage-status mutation paths.

Pins the publication contract introduced by TASK-001:

* Every mutation entry point (``create``, ``set-phase``, ``transition``,
  ``archive``) writes ``{plan_dir}/title-body.txt`` reflecting
  ``pm:{current_phase}[:{short_description}]``.
* Terminal phases (``complete``, ``archived``) delete the file rather
  than write it — "file absent → no plan-title to render" is the only
  conditional carried by the per-target reader.
* ``read`` cold-bootstraps a missing ``title-body.txt`` for an active
  (non-terminal) plan without requiring a state mutation.
* Plans with no ``short_description`` render ``pm:{phase}`` with no
  trailing segment.
* The hook uses ``atomic_write_file`` so a crash during write does not
  corrupt the previously published artifact (temp-file + rename
  pattern).
"""

from __future__ import annotations

import os
from pathlib import Path

from conftest import get_script_path, run_script

STATUS_SCRIPT = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')

TITLE_BODY_FILENAME = 'title-body.txt'


# =============================================================================
# Helpers
# =============================================================================


def _create_plan(plan_id: str, title: str, phases: str) -> None:
    """Create a plan via manage-status and assert success."""
    result = run_script(
        STATUS_SCRIPT,
        'create',
        '--plan-id',
        plan_id,
        '--title',
        title,
        '--phases',
        phases,
    )
    assert result.success, f'Failed to create plan: {result.stderr}'


def _title_body_path(plan_dir: Path) -> Path:
    """Return the title-body.txt path inside the active fixture plan dir."""
    return plan_dir / TITLE_BODY_FILENAME


def _read_title_body(plan_dir: Path) -> str:
    """Read the title-body artifact stripped of the trailing newline."""
    return _title_body_path(plan_dir).read_text(encoding='utf-8').rstrip('\n')


# =============================================================================
# Test: create publishes title-body
# =============================================================================


def test_create_publishes_title_body_with_short_description(plan_context):
    """cmd_create must publish title-body.txt with pm:{phase}:{short_description}."""
    plan_dir = plan_context.plan_dir_for('tb-create')
    _create_plan('tb-create', 'Add login button to homepage', '1-init,2-refine')
    path = _title_body_path(plan_dir)
    assert path.exists(), 'title-body.txt must be written by cmd_create'
    body = _read_title_body(plan_dir)
    assert body.startswith('pm:1-init:'), f'Unexpected body: {body!r}'
    # short_description is derived from the title; assert the prefix
    # and that it is non-empty (exact derivation is owned by
    # _short_description.py — not under test here).
    suffix = body[len('pm:1-init:') :]
    assert suffix, 'short_description segment must be non-empty when derivable'


def test_create_writes_single_trailing_newline(plan_context):
    """atomic_write_file appends exactly one '\\n' — no double newline."""
    plan_dir = plan_context.plan_dir_for('tb-newline')
    _create_plan('tb-newline', 'Newline test', '1-init,2-refine')
    raw = _title_body_path(plan_dir).read_text(encoding='utf-8')
    assert raw.endswith('\n'), 'Artifact must end with exactly one newline'
    assert not raw.endswith('\n\n'), 'Artifact must not end with double newline'


# =============================================================================
# Test: set-phase publishes title-body
# =============================================================================


def test_set_phase_republishes_title_body(plan_context):
    """cmd_set_phase must rewrite title-body.txt to reflect the new phase."""
    plan_dir = plan_context.plan_dir_for('tb-setphase')
    _create_plan('tb-setphase', 'Phase mutator test', '1-init,2-refine,3-outline')
    # set-phase to 2-refine
    result = run_script(
        STATUS_SCRIPT, 'set-phase', '--plan-id', 'tb-setphase', '--phase', '2-refine'
    )
    assert result.success, f'set-phase failed: {result.stderr}'
    body = _read_title_body(plan_dir)
    assert body.startswith('pm:2-refine'), f'Expected pm:2-refine prefix, got: {body!r}'


# =============================================================================
# Test: transition publishes title-body
# =============================================================================


def test_transition_republishes_title_body(plan_context):
    """cmd_transition must rewrite title-body.txt to the next phase."""
    plan_dir = plan_context.plan_dir_for('tb-transition')
    _create_plan('tb-transition', 'Transition test', '1-init,2-refine,3-outline')
    result = run_script(
        STATUS_SCRIPT, 'transition', '--plan-id', 'tb-transition', '--completed', '1-init'
    )
    assert result.success, f'transition failed: {result.stderr}'
    body = _read_title_body(plan_dir)
    assert body.startswith('pm:2-refine'), f'Expected pm:2-refine prefix, got: {body!r}'


def test_transition_last_phase_deletes_title_body(plan_context):
    """Completing the last phase sets current_phase=='complete' (terminal)
    and the hook must delete title-body.txt rather than write it."""
    plan_dir = plan_context.plan_dir_for('tb-last')
    _create_plan('tb-last', 'Last phase test', '1-init,2-finalize')
    # Advance through both phases
    r1 = run_script(
        STATUS_SCRIPT, 'transition', '--plan-id', 'tb-last', '--completed', '1-init'
    )
    assert r1.success
    # File should exist after the first transition (phase is 2-finalize, non-terminal)
    assert _title_body_path(plan_dir).exists()

    r2 = run_script(
        STATUS_SCRIPT, 'transition', '--plan-id', 'tb-last', '--completed', '2-finalize'
    )
    assert r2.success, f'final transition failed: {r2.stderr}'
    # current_phase is now 'complete' — terminal — file must be gone
    assert not _title_body_path(plan_dir).exists(), (
        'title-body.txt must be deleted when current_phase becomes terminal (complete)'
    )


# =============================================================================
# Test: archive publishes the Completed body (write-before-archive)
# =============================================================================


def _archived_plan_dir(plan_context, plan_id: str) -> Path:
    """Locate the moved plan directory inside archived-plans/ for a plan_id.

    The archive name is ``{YYYY-MM-DD}-{plan_id}``; match on the exact
    ``-{plan_id}`` suffix so a prefix collision between similarly named plans
    cannot resolve the wrong directory.
    """
    archive_root = plan_context.fixture_dir / 'archived-plans'
    assert archive_root.exists(), 'archive directory missing'
    archived_dirs = list(archive_root.iterdir())
    assert archived_dirs, 'archived plan directory missing'
    target = next((d for d in archived_dirs if d.name.endswith(f'-{plan_id}')), None)
    assert target is not None, f'archived plan not found: {[d.name for d in archived_dirs]}'
    return target


def test_archive_publishes_completed_title_body_before_move(plan_context):
    """cmd_archive closes the last open phase and, when every phase is done,
    sets current_phase='complete' (terminal). It then writes the special
    non-deletable ``pm:Completed:{short_description}`` body to the live
    title-body.txt BEFORE shutil.move, so the Completed body travels into the
    archive tree with the moved directory (write-before-archive). This is the
    one terminal transition that PUBLISHES a body rather than deleting it."""
    plan_dir = plan_context.plan_dir_for('tb-archive')
    _create_plan('tb-archive', 'Archive test', '1-init,2-finalize')
    # Drive the plan all the way to "every phase done" so cmd_archive
    # promotes current_phase to 'complete'.
    r0 = run_script(
        STATUS_SCRIPT, 'transition', '--plan-id', 'tb-archive', '--completed', '1-init'
    )
    assert r0.success
    # File present before archive (current_phase=='2-finalize', non-terminal)
    assert _title_body_path(plan_dir).exists()

    result = run_script(STATUS_SCRIPT, 'archive', '--plan-id', 'tb-archive')
    assert result.success, f'archive failed: {result.stderr}'

    # The plan dir was moved into archived-plans/, so the original path is
    # gone. The Completed body must have been published BEFORE the move and
    # therefore lands inside the archived plan directory.
    target = _archived_plan_dir(plan_context, 'tb-archive')
    archived_body_path = target / TITLE_BODY_FILENAME
    assert archived_body_path.exists(), (
        'title-body.txt must be published (write-before-archive) and travel '
        'into the archive tree with the moved directory'
    )
    body = archived_body_path.read_text(encoding='utf-8').rstrip('\n')
    assert body.startswith('pm:Completed:'), (
        f'Archived body must be the Completed terminal body, got: {body!r}'
    )
    suffix = body[len('pm:Completed:') :]
    assert suffix, 'Completed body must carry a non-empty short_description segment'


def test_archive_completed_body_carries_short_description(plan_context):
    """The published Completed body uses ``short_description`` as its name
    token — the same token the active ``pm:{phase}:{short}`` format uses. The
    derived short_description must survive verbatim into the archived body."""
    import json

    plan_dir = plan_context.plan_dir_for('tb-archive-short')
    _create_plan('tb-archive-short', 'Consolidate terminal docs', '1-init,2-finalize')
    # Read the derived short_description from the live status before archive.
    status_path = plan_dir / 'status.json'
    short_desc = json.loads(status_path.read_text(encoding='utf-8'))['short_description']
    assert short_desc, 'fixture precondition: short_description must be derivable'

    r0 = run_script(
        STATUS_SCRIPT, 'transition', '--plan-id', 'tb-archive-short', '--completed', '1-init'
    )
    assert r0.success

    result = run_script(STATUS_SCRIPT, 'archive', '--plan-id', 'tb-archive-short')
    assert result.success, f'archive failed: {result.stderr}'

    target = _archived_plan_dir(plan_context, 'tb-archive-short')
    body = (target / TITLE_BODY_FILENAME).read_text(encoding='utf-8').rstrip('\n')
    assert body == f'pm:Completed:{short_desc}', (
        f'Archived Completed body must be pm:Completed:{short_desc!r}, got: {body!r}'
    )


def test_archive_completed_body_single_trailing_newline(plan_context):
    """The Completed body is published via atomic_write_file, which appends
    exactly one terminating newline — no double newline, matching the
    active-phase publication contract."""
    plan_context.plan_dir_for('tb-archive-nl')
    _create_plan('tb-archive-nl', 'Newline archive test', '1-init,2-finalize')
    r0 = run_script(
        STATUS_SCRIPT, 'transition', '--plan-id', 'tb-archive-nl', '--completed', '1-init'
    )
    assert r0.success

    result = run_script(STATUS_SCRIPT, 'archive', '--plan-id', 'tb-archive-nl')
    assert result.success, f'archive failed: {result.stderr}'

    target = _archived_plan_dir(plan_context, 'tb-archive-nl')
    raw = (target / TITLE_BODY_FILENAME).read_text(encoding='utf-8')
    assert raw.endswith('\n'), 'Completed body must end with exactly one newline'
    assert not raw.endswith('\n\n'), 'Completed body must not end with a double newline'


# =============================================================================
# Test: read cold-bootstrap
# =============================================================================


def test_read_cold_bootstraps_missing_title_body(plan_context):
    """cmd_read republishes title-body.txt when it is absent for an
    active (non-terminal) plan. Covers fresh tabs/processes that opened
    after the writer's last successful publish — the next read self-heals."""
    plan_dir = plan_context.plan_dir_for('tb-cold')
    _create_plan('tb-cold', 'Cold-bootstrap test', '1-init,2-refine')
    path = _title_body_path(plan_dir)
    # Simulate the missing-file state
    path.unlink()
    assert not path.exists()

    result = run_script(STATUS_SCRIPT, 'read', '--plan-id', 'tb-cold')
    assert result.success, f'read failed: {result.stderr}'

    assert path.exists(), 'cmd_read must republish title-body.txt when absent'
    body = _read_title_body(plan_dir)
    assert body.startswith('pm:1-init'), f'Unexpected body after cold-bootstrap: {body!r}'


def test_read_does_not_republish_when_file_present(plan_context):
    """cmd_read MUST NOT rewrite an existing title-body.txt — only
    cold-bootstraps when absent. Guards against unnecessary rewrites
    on every read (which would defeat the writer-side publication
    model and churn mtimes pointlessly)."""
    plan_dir = plan_context.plan_dir_for('tb-noop')
    _create_plan('tb-noop', 'Read no-op test', '1-init,2-refine')
    path = _title_body_path(plan_dir)
    # Overwrite the file with a sentinel and capture mtime — if
    # cmd_read republishes unconditionally, our sentinel goes away.
    sentinel = 'sentinel-do-not-overwrite\n'
    path.write_text(sentinel, encoding='utf-8')

    result = run_script(STATUS_SCRIPT, 'read', '--plan-id', 'tb-noop')
    assert result.success, f'read failed: {result.stderr}'

    assert path.read_text(encoding='utf-8') == sentinel, (
        'cmd_read must not rewrite an existing title-body.txt'
    )


# =============================================================================
# Test: short_description absent
# =============================================================================


def test_render_without_short_description_produces_no_trailing_segment(plan_context):
    """When status['short_description'] is absent or empty, the
    artifact renders as ``pm:{phase}`` with NO trailing colon segment."""
    plan_dir = plan_context.plan_dir_for('tb-noshort')
    _create_plan('tb-noshort', 'Short desc test', '1-init,2-refine')
    # Drop short_description from status.json directly to exercise
    # the "no short_description" branch. cmd_create always derives
    # one, so we have to remove it post-hoc and re-trigger a
    # mutation hook (set-phase) so the artifact is recomputed
    # against the mutated status.
    import json

    status_path = plan_dir / 'status.json'
    data = json.loads(status_path.read_text(encoding='utf-8'))
    data.pop('short_description', None)
    status_path.write_text(json.dumps(data), encoding='utf-8')

    # Trigger a mutation that republishes from the mutated status
    result = run_script(
        STATUS_SCRIPT, 'set-phase', '--plan-id', 'tb-noshort', '--phase', '2-refine'
    )
    assert result.success, f'set-phase failed: {result.stderr}'

    body = _read_title_body(plan_dir)
    assert body == 'pm:2-refine', (
        f"Expected 'pm:2-refine' with no trailing segment, got: {body!r}"
    )


# =============================================================================
# Test: atomic-write resilience
# =============================================================================


def test_partial_write_does_not_corrupt_existing_file(plan_context):
    """The hook uses atomic_write_file (temp-file + rename). A crash or
    permission failure DURING the write must leave the existing
    title-body.txt untouched — no partial/empty artifact.

    Simulated by making the plan_dir non-writable AFTER the first
    successful publish, then triggering another mutation. The second
    publish swallows OSError silently (consistent with the legacy
    terminal-title hook), and the previously-written file remains
    bit-identical.
    """
    plan_dir = plan_context.plan_dir_for('tb-atomic')
    _create_plan('tb-atomic', 'Atomic write test', '1-init,2-refine,3-outline')
    path = _title_body_path(plan_dir)
    assert path.exists()
    before = path.read_bytes()

    # Lock the plan_dir read-only so atomic_write_file can neither
    # create a temp file nor rename. The hook swallows OSError.
    original_mode = plan_dir.stat().st_mode
    os.chmod(plan_dir, 0o500)  # r-x------
    try:
        result = run_script(
            STATUS_SCRIPT, 'set-phase', '--plan-id', 'tb-atomic', '--phase', '2-refine'
        )
        # The mutation itself may surface an error (status.json
        # write also goes through the locked directory). What
        # matters for THIS contract is that the existing
        # title-body.txt is NOT clobbered, truncated, or replaced
        # with a partial write.
        del result  # exit code is not the assertion target here
    finally:
        os.chmod(plan_dir, original_mode)

    # Existing artifact must be bit-identical to its pre-attempt state.
    after = path.read_bytes()
    assert after == before, (
        'Partial / failed write must not corrupt the previously published title-body.txt'
    )
    # And must still contain a non-empty body line.
    body = after.decode('utf-8').rstrip('\n')
    assert body.startswith('pm:1-init'), (
        f'Existing artifact lost its body after failed mutation attempt: {body!r}'
    )
