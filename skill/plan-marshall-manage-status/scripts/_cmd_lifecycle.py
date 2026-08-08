#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Lifecycle command handlers for manage-status: create, transition, archive, delete-plan.
"""

import argparse
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, NamedTuple

from _handshake_commands import cmd_capture, cmd_verify
from _invariants import _BLOCKING_BOUNDARIES
from _lessons_query import RESTORE_ACTIONS
from _short_description import derive_short_description
from _status_core import (
    _surface_drive,
    get_archive_dir,
    get_status_path,
    log_entry,
    normalize_metadata,
    now_utc_iso,
    require_status,
    require_valid_plan_id,
    write_status,
)
from constants import (
    PHASE_STATUS_DONE,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_PENDING,
)
from file_ops import get_plan_dir

# Result-status values that indicate the strict-verify gate refuses to advance.
# Mirrors the ``--strict`` exit-1 conditions in ``phase_handshake.py`` main()
# so the inline guard in ``cmd_transition`` and the CLI exit-code wrapper in
# ``manage_status.py`` main() treat the same situations as boundary refusals.
# Single source of truth — both consumers import this name; do not duplicate
# the literal set.
VERIFY_REFUSAL_ERRORS = frozenset({
    'worktree_unresolved',
    'worktree_metadata_drift',
    'main_checkout_dirtied_during_plan',
    'worktree_dirty_at_boundary',
})


def _clean_tree_refusal(plan_id: str, status: dict[str, Any]) -> dict[str, Any] | None:
    """Clean-tree post-condition for guarded boundaries (5-execute → 6-finalize).

    When the plan runs in an isolated worktree (``metadata.use_worktree``
    truthy), the working tree at ``metadata.worktree_path`` MUST be clean
    before the transition into a blocking boundary is allowed: every
    per-deliverable commit belongs to the phase-5-execute envelope's Step 10a
    chain-tail, so uncommitted edits at the boundary mean a commit obligation
    was skipped. Returns the structured refusal dict when the tree is dirty
    (or when ``git status`` itself fails — the gate fails closed), and
    ``None`` when the transition may proceed.
    """
    metadata = normalize_metadata(status)
    if not metadata.get('use_worktree'):
        return None
    worktree_path = metadata.get('worktree_path')
    if not worktree_path:
        # Resolvability is asserted by the strict-verify guard that runs
        # before this gate (``worktree_unresolved``); an empty path here
        # means the verify guard already owns the refusal path.
        return None

    proc = subprocess.run(
        ['git', '-C', worktree_path, 'status', '--porcelain'],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        # Fail closed: an unreadable tree cannot be proven clean.
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'worktree_dirty_at_boundary',
            'dirty_files': [],
            'message': (
                f'git status failed in worktree {worktree_path} '
                f'(exit {proc.returncode}): {proc.stderr.strip()} — '
                'cannot prove the tree is clean; refusing to transition.'
            ),
        }

    if not proc.stdout.strip():
        return None

    # Split the RAW stdout — a global .strip() would eat the leading space
    # of the first line's "XY " porcelain status prefix (e.g. " M src.py")
    # and shift the fixed 3-char slice into the path.
    dirty_files = [line[3:] for line in proc.stdout.splitlines() if len(line) > 3]
    return {
        'status': 'error',
        'plan_id': plan_id,
        'error': 'worktree_dirty_at_boundary',
        'dirty_files': dirty_files,
        'message': (
            f'Worktree {worktree_path} has {len(dirty_files)} uncommitted '
            'change(s) at a guarded phase boundary. Every per-deliverable '
            'commit is owned by phase-5-execute Step 10a — run the boundary '
            'settlement commit, then retry the transition.'
        ),
    }


def _loop_back_auto_override(
    args: argparse.Namespace,
    status: dict[str, Any],
    verify_result: dict[str, Any],
) -> dict[str, Any] | None:
    """Auto-resolve the structurally-guaranteed loop-back handshake drift.

    A sanctioned loop-back (``cmd_set_phase`` backward move) persists
    ``metadata.loop_back_reentry``; the re-entered phases then legitimately
    change the invariants the earlier capture recorded, so ``cmd_verify``
    reports ``status: drift`` by construction at the next guarded boundary.
    When BOTH hold — the blocking verify result is invariant drift AND the
    marker is present — re-capture the handshake with ``override=True`` and a
    recorded reason, clear the marker (persisted immediately so the override
    fires exactly once per scheduled loop-back), emit a decision-log WARNING
    with the drift diff summary, and let the transition proceed by returning
    ``None``.

    Every other blocking result returns the refusal unchanged: drift WITHOUT
    the marker keeps today's blocking behavior, and the worktree-resolution /
    dirty-boundary / main-dirtied refusals (``VERIFY_REFUSAL_ERRORS``) are
    NEVER bypassed by the marker — only invariant drift is auto-resolved.
    A failed re-capture also blocks (fail closed) by returning its error
    payload.
    """
    metadata = normalize_metadata(status)
    marker = metadata.get('loop_back_reentry')
    if verify_result.get('status') != 'drift' or not marker:
        return verify_result

    from_phase = marker.get('from_phase', 'unknown') if isinstance(marker, dict) else 'unknown'
    recapture = cmd_capture(
        argparse.Namespace(
            plan_id=args.plan_id,
            phase=args.completed,
            override=True,
            reason=f'loop-back re-entry auto-override (scheduled by {from_phase} loop_back)',
            strict=False,
        )
    )
    if recapture.get('status') != 'success':
        # Fail closed: an un-recapturable baseline cannot be auto-resolved.
        return recapture

    metadata.pop('loop_back_reentry', None)
    write_status(args.plan_id, status)

    diff_summary = '; '.join(
        f'{d.get("invariant")}: {d.get("captured")} -> {d.get("observed")}'
        for d in verify_result.get('diffs', [])
    )
    log_entry(
        'decision',
        args.plan_id,
        'WARNING',
        f'(plan-marshall:manage-status) Loop-back re-entry auto-override at '
        f'{args.completed}: drift ({verify_result.get("drift_count", 0)} invariant(s)) '
        f'auto-resolved via override re-capture scheduled by {from_phase} loop_back — '
        f'{diff_summary}',
    )
    return None


def verify_blocks_transition(verify_result: dict[str, Any]) -> bool:
    """Return True when a cmd_verify result MUST block the transition.

    Consumed by both ``cmd_transition`` (refuse to mutate state) and
    ``manage_status.py`` main() (exit 1) so the in-process refusal and the
    CLI exit-code contract stay in lockstep.
    """
    if verify_result.get('status') == 'drift':
        return True
    return verify_result.get('error') in VERIFY_REFUSAL_ERRORS


def cmd_create(args: argparse.Namespace) -> dict[str, Any]:
    """Create status.json for a new plan.

    When the plan runs in an isolated worktree, the caller passes
    ``--use-worktree`` so the use-worktree intent is recorded in
    ``status.metadata`` at creation time. Only ``use_worktree`` is
    persisted at create — the feature branch (``feature/{plan_id}``)
    and the resolved ``worktree_path`` are derived and back-filled at
    phase-5-execute Step 2.5, when the worktree directory is created on
    disk via ``git worktree add``.

    When ``--use-worktree`` is omitted (or set to ``false``), no
    worktree metadata is written and the plan is treated as running
    against the main checkout.
    """
    require_valid_plan_id(args)

    path = get_status_path(args.plan_id)
    if path.exists() and not args.force:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'file_exists',
            'message': 'status.json already exists. Use --force to overwrite.',
        }

    # Parse phases from comma-separated argument
    phases = [p.strip() for p in args.phases.split(',') if p.strip()]
    if not phases:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_phases',
            'message': 'At least one phase is required',
        }

    # Worktree intent — at create the only durable fact is whether the plan
    # runs in an isolated worktree. The feature branch (always
    # ``feature/{plan_id}``) and the resolved ``worktree_path`` are derived at
    # phase-5-execute Step 2.5 and back-filled there, so nothing about the
    # branch is read or validated here: ``feature/`` is unconditionally in the
    # closed working-prefix set, making a create-time prefix check vacuous.
    use_worktree = bool(getattr(args, 'use_worktree', False))

    now = now_utc_iso()

    status: dict[str, Any] = {
        'title': args.title,
        'short_description': derive_short_description(args.title),
        'current_phase': phases[0],
        'phases': [{'name': p, 'status': PHASE_STATUS_PENDING} for p in phases],
        'created': now,
        'updated': now,
    }
    # Mark first phase as in_progress
    status['phases'][0]['status'] = PHASE_STATUS_IN_PROGRESS

    if use_worktree:
        # Only the use-worktree intent is durable at create. The branch and
        # the resolved worktree_path are derived and persisted at
        # phase-5-execute Step 2.5 when `git worktree add` runs.
        status['metadata'] = {'use_worktree': True}
    else:
        # Explicit false-state seeding: even when no worktree is
        # allocated, downstream consumers benefit from a definite
        # ``use_worktree: false`` marker rather than having to treat
        # absence-of-metadata as "main-checkout". Keeps the contract
        # symmetric.
        status['metadata'] = {'use_worktree': False}

    write_status(args.plan_id, status)
    # Persisted-title-state-write drive seam (best-effort, fire-and-forget):
    # the first-phase seed is a current_phase write, so bind + repaint fire here
    # too — a delegation failure never changes this command's outcome.
    _surface_drive(args.plan_id)

    result: dict[str, Any] = {
        'status': 'success',
        'plan_id': args.plan_id,
        'file': 'status.json',
        'created': True,
        'plan': {'title': args.title, 'current_phase': phases[0]},
        'use_worktree': use_worktree,
    }
    return result


def cmd_transition(args: argparse.Namespace) -> dict[str, Any] | None:
    """Transition to next phase."""
    status = require_status(args)
    if status is None:
        return None

    phases = status.get('phases', [])
    phase_names = [p['name'] for p in phases]

    if args.completed not in phase_names:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_phase',
            'message': f'Invalid phase: {args.completed}',
        }

    completed_idx = phase_names.index(args.completed)

    # Determine next phase early so the guard below can inspect it before any
    # state mutation. The standalone ``cmd_transition`` later computes the same
    # value after marking the completed phase done, but the inline guard MUST
    # see ``next_phase`` first to decide whether the strict-verify gate fires.
    if completed_idx + 1 < len(phase_names):
        next_phase: str | None = phase_names[completed_idx + 1]
    else:
        next_phase = None

    # Inline strict-verify guard for guarded boundaries — folds the
    # ``phase_handshake verify --phase {completed} --strict`` step that
    # workflow docs used to issue separately into the transition itself.
    # When ``next_phase`` is in ``_BLOCKING_BOUNDARIES`` (currently
    # ``{'6-finalize'}``), re-run the verify code path against the captured
    # baseline for the completed phase. On drift (or any of the three
    # worktree-/main-checkout boundary refusals listed in
    # ``VERIFY_REFUSAL_ERRORS``) return the verify result unchanged and
    # SKIP ``write_status`` so ``current_phase`` stays on the completed
    # phase. Non-guarded transitions are unaffected — they keep today's
    # behaviour with no verify invoked.
    if next_phase in _BLOCKING_BOUNDARIES:
        verify_args = argparse.Namespace(
            plan_id=args.plan_id,
            phase=args.completed,
            strict=True,
        )
        verify_result = cmd_verify(verify_args)
        if verify_blocks_transition(verify_result):
            refusal = _loop_back_auto_override(args, status, verify_result)
            if refusal is not None:
                return refusal
        else:
            # Consume-on-next-guarded-verification: the loop_back_reentry
            # marker is consumed at the very next guarded boundary check
            # REGARDLESS of whether that check found drift. A clean verify
            # with the marker still present must clear it here — otherwise a
            # later, genuinely unscheduled drift would find the stale marker
            # and incorrectly auto-override it.
            metadata = status.get('metadata')
            if isinstance(metadata, dict) and metadata.get('loop_back_reentry'):
                marker = metadata.pop('loop_back_reentry')
                write_status(args.plan_id, status)
                from_phase = (
                    marker.get('from_phase', 'unknown')
                    if isinstance(marker, dict)
                    else 'unknown'
                )
                log_entry(
                    'decision',
                    args.plan_id,
                    'INFO',
                    f'(plan-marshall:manage-status) Loop-back re-entry marker '
                    f'consumed on clean guarded verification at {args.completed} '
                    f'(scheduled by {from_phase} loop_back) — no drift to '
                    'auto-resolve; marker cleared without recapture',
                )

        # Clean-tree post-condition: after the strict-verify guard passes,
        # the worktree itself must be clean — uncommitted edits at the
        # boundary mean a phase-5 Step 10a commit obligation was skipped.
        # On refusal, skip write_status so current_phase stays on the
        # completed phase (same contract as the verify refusal above).
        clean_tree_refusal = _clean_tree_refusal(args.plan_id, status)
        if clean_tree_refusal is not None:
            return clean_tree_refusal

    # Mark completed phase as done
    phases[completed_idx]['status'] = PHASE_STATUS_DONE

    # Apply the next-phase mutation. ``next_phase`` was resolved earlier so
    # the inline strict-verify guard could decide whether to fire — here we
    # only need to perform the state changes that follow from it.
    if next_phase is not None:
        phases[completed_idx + 1]['status'] = PHASE_STATUS_IN_PROGRESS
        status['current_phase'] = next_phase
    else:
        # Last phase completed — set the post-finalize sentinel so dormant
        # consumers (phase-6-finalize SKILL.md "current_phase: complete"
        # check, planning.md cleanup --filter complete) start matching.
        # Mirrors cmd_archive's atomic-archive behavior so the two verbs
        # produce the same end-state.
        status['current_phase'] = 'complete'

    # No title-token sweep here: staleness is a READ-side property resolved by
    # the aged-token predicate (_status_core.title_token_is_stale), not a
    # transition-side one. A transition-side sweep only fires when a phase
    # happens to change, so a stranded token could outlive it indefinitely.
    write_status(args.plan_id, status)
    # Persisted-title-state-write drive seam (best-effort, fire-and-forget):
    # a phase advance is a current_phase write, so bind + repaint fire here so
    # the title reflects the new phase immediately instead of freezing.
    _surface_drive(args.plan_id)

    result: dict[str, Any] = {'status': 'success', 'plan_id': args.plan_id, 'completed_phase': args.completed}
    if next_phase:
        result['next_phase'] = next_phase
    else:
        result['message'] = 'All phases completed'

    return result


def cmd_archive(args: argparse.Namespace) -> dict[str, Any] | None:
    """Archive a completed plan.

    Atomically closes the active phase before moving the plan directory:
    marks the active phase ``done``, and when every phase is done sets
    ``current_phase = 'complete'``. Mirrors cmd_transition so an archived
    status.json reflects a fully-closed plan instead of being frozen at the
    last phase's in_progress state.
    """
    require_valid_plan_id(args)

    plan_dir = get_plan_dir(args.plan_id)
    if not plan_dir.exists():
        return {'status': 'error', 'plan_id': args.plan_id, 'error': 'not_found', 'message': 'Plan directory not found'}

    date_prefix = now_utc_iso()[:10]  # YYYY-MM-DD
    archive_name = f'{date_prefix}-{args.plan_id}'
    archive_dir = get_archive_dir()
    archive_path = archive_dir / archive_name

    if args.dry_run:
        return {'status': 'success', 'plan_id': args.plan_id, 'dry_run': True, 'would_archive_to': str(archive_path)}

    # Atomic phase close: load status, mark the active phase done, set the
    # post-finalize sentinel when all phases are complete, then write back
    # to the live plan directory BEFORE the shutil.move. This guarantees the
    # archived status.json reflects the closed state — historically this
    # was attempted via a follow-up `transition --completed 6-finalize`
    # call, but that always failed because shutil.move had already
    # invalidated the live path.
    status = require_status(args)
    if status is None:
        # Plan dir exists but status.json is missing/unreadable. Fail
        # loudly via require_status's error contract instead of moving the
        # broken plan into the archive — silent archives mask data loss.
        return None
    phases = status.get('phases', [])
    active_idx = next(
        (i for i, p in enumerate(phases) if p.get('status') != PHASE_STATUS_DONE),
        None,
    )
    if active_idx is not None:
        phases[active_idx]['status'] = PHASE_STATUS_DONE
    if all(p.get('status') == PHASE_STATUS_DONE for p in phases):
        status['current_phase'] = 'complete'
    # Drop any in-flight terminal-title token (any TITLE_TOKEN_STATES value —
    # lock-waiting/lock-owned/build-busy) before archiving. An archived plan
    # holds no live coordination state worth arbitrating over, so this pop is
    # owner-agnostic: a single pop covers every record regardless of its owner.
    # ``preserve_title_token=False`` on the write below is what makes the pop
    # stick — the default write path deliberately carries the live record over,
    # and archive is the one writer that intends to discard it.
    status.pop('title_token', None)
    # Persist optional --reason into status.metadata.archived_reason before
    # write_status so the archived status.json carries the structured reason.
    # Absent --reason leaves the field unset (no schema migration). Mirrors the
    # additive-metadata contract used elsewhere in this module.
    reason = getattr(args, 'reason', None)
    if reason is not None:
        metadata = status.setdefault('metadata', {})
        metadata['archived_reason'] = reason
    write_status(args.plan_id, status, preserve_title_token=False)

    # This write makes the plan terminal and drops its token, so its RENDERED
    # projection changes — which obliges a paired delivery exactly as every other
    # current_phase write does. Fired here, BEFORE the move, while the live plan
    # path still resolves. The seam binds and settles the state; the repaint is
    # deferred to the next hook event, which reads the archived status.json
    # through this very binding.
    _surface_drive(args.plan_id)

    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(plan_dir), str(archive_path))

    # NO binding release here, deliberately. The terminal title this archive just
    # persisted is painted by the NEXT hook event, which can only resolve the plan
    # while the session binding survives — releasing it here would destroy the
    # delivery route for the state we just wrote. SessionStart:clear is the sole
    # release point, and `session doctor` exempts this slot from GC until the
    # terminal state has actually been delivered.

    return {'status': 'success', 'plan_id': args.plan_id, 'archived_to': str(archive_path)}


#: The closed vocabulary :attr:`LessonCarryBack.action` reports.
#:
#: - ``restored`` — the plan directory was scanned, DID carry ``lesson-*.md``
#:   files, and EVERY one of them landed in the corpus.
#: - ``restore_incomplete`` — the plan directory was scanned and carried lesson
#:   files, but at least one did NOT land. ``restored_ids`` / ``skipped`` say
#:   which; ``restored_ids`` is legitimately empty when none landed. This is
#:   the state that fires the ``cmd_delete_plan`` veto.
#: - ``no_lesson_file`` — the plan directory was scanned and carried none. The
#:   benign zero.
#: - ``plan_dir_unresolved`` — the carry-back could not look: the plan directory
#:   is gone, or the main-anchored lessons store could not be resolved AND the
#:   directory carried lesson files that consequently could not land. A
#:   store-unresolved scan over a directory carrying NO lesson file is
#:   ``no_lesson_file``, not this value: that directory WAS scanned and holds
#:   nothing to restore, so the benign zero is the honest action and
#:   ``store_resolution: unresolved`` is what records that the corpus was never
#:   reached. Consumers therefore read BOTH fields — ``action`` says what the
#:   scan found, ``store_resolution`` says whether the corpus was reachable —
#:   and neither alone answers both questions.
#: - ``not_attempted`` — the carry-back was opted out of via
#:   ``--no-restore-lessons``, so nothing was scanned and no store was
#:   resolved. Any lesson the directory carries is discarded with it.
#:
#: The four values this set SHARES with ``_lessons_query.RESTORE_ACTIONS``
#: carry identical meanings there, so the two lesson-restore surfaces answer
#: the "which kind of zero is this?" question the same way. That relationship
#: is ENCODED as a union rather than restated as literals, so the shared four
#: cannot drift apart silently. The sets are NOT equal, and deliberately so:
#: ``not_attempted`` is producible only here, because only ``delete-plan`` has
#: an opt-out flag. A superset derivation is precisely not the equality claim
#: this docstring once made — claiming equality while the two disagreed on what
#: ``restored`` means was itself a contract drift, and a consumer trusting the
#: claim would carry the wrong meaning across surfaces.
CARRY_BACK_ACTIONS = RESTORE_ACTIONS | frozenset({'not_attempted'})


class LessonCarryBack(NamedTuple):
    """Outcome of the ``delete-plan`` lesson carry-back.

    Replaces the previous ``(bool, list[str])`` tuple outright: that shape could
    not express EITHER of the two ways the carry-back fails silently — a plan
    directory it never looked at, and a lesson it looked at but did not land.
    Both mattered here more than anywhere else on the lesson path, because the
    caller deletes the directory holding the only copy immediately afterwards.

    Attributes:
        action: One of :data:`CARRY_BACK_ACTIONS`.
        store_resolution: How the lessons store resolved, over
            ``_lessons_io.STORE_RESOLUTIONS``. ``unresolved`` on the
            ``not_attempted`` path too — that path resolves no store, and
            reporting a resolution it never performed is the same fail-open in
            miniature.
        lessons_dir: The corpus path lessons were moved into, or ``''`` when the
            store did not resolve or was never consulted.
        restored_ids: Lesson ids that successfully landed in the corpus.
        skipped: One ``{lesson_id, reason}`` row per carried lesson that did NOT
            land. A non-empty list means the plan directory still holds the only
            copy of those lessons.
        detail: Human-readable provenance naming the substrate or the failure.
    """

    action: str
    store_resolution: str
    lessons_dir: str
    restored_ids: list[str]
    skipped: list[dict[str, str]]
    detail: str


def _restore_lesson_from_plan_dir(plan_id: str, plan_dir: Path) -> LessonCarryBack:
    """Scan ``plan_dir`` for lesson-{id}.md files and move each back to the corpus.

    The destination resolves through the main-anchored lessons-store handle
    (``_lessons_io.resolve_lesson_store``), NOT through the cwd-keyed
    ``base_path()``: this helper runs from ``delete-plan``, which a
    worktree-pinned caller invokes routinely, and a cwd-keyed resolution would
    restore the lesson into the worktree's own empty corpus — a store that is
    discarded when the worktree goes away.

    Every carried lesson that does not land is REPORTED in
    :attr:`LessonCarryBack.skipped` rather than silently ``continue``-skipped.
    The silent skip was the sharpest edge on the whole lesson path: the caller
    deletes the plan directory right after this returns, so a dropped collision
    destroyed the only copy of a lesson with no signal anywhere.

    Args:
        plan_id: The plan being deleted (used for the work-log entry).
        plan_dir: The plan directory to scan.

    Returns:
        A :class:`LessonCarryBack` describing what was scanned, what landed, and
        what did not.
    """
    from _lessons_io import resolve_lesson_store

    if not plan_dir.exists():
        return LessonCarryBack(
            'plan_dir_unresolved',
            'unresolved',
            '',
            [],
            [],
            f'Plan directory {plan_dir} does not exist, so it was never scanned '
            f'for lesson files.',
        )

    matches = sorted(plan_dir.glob('lesson-*.md'))

    store = resolve_lesson_store()
    if store.path is None:
        # Could not look at the corpus. When the plan directory carries lessons,
        # every one of them is un-landed and the caller MUST NOT delete the
        # directory holding them.
        return LessonCarryBack(
            'plan_dir_unresolved' if matches else 'no_lesson_file',
            store.resolution,
            '',
            [],
            [
                {'lesson_id': m.stem[len('lesson-'):], 'reason': 'store_unresolved'}
                for m in matches
            ],
            store.detail,
        )

    if not matches:
        return LessonCarryBack(
            'no_lesson_file', store.resolution, str(store.path), [], [], store.detail
        )

    lessons_dir = store.path.resolve()
    lessons_dir.mkdir(parents=True, exist_ok=True)

    restored_ids: list[str] = []
    skipped: list[dict[str, str]] = []
    for match in matches:
        # The id comes from the MATCHED name, never from a resolved one. A
        # symlinked ``lesson-*.md`` resolves OUT of the plan directory, so an id
        # read off the resolved path describes the link's target rather than the
        # file the plan actually carries — and the traversal guard below would
        # then be inspecting the wrong name entirely.
        lesson_id = match.stem[len('lesson-'):]
        if any(sep in lesson_id for sep in ('/', '\\', '..')):
            skipped.append({'lesson_id': lesson_id, 'reason': 'path_traversal'})
            continue

        # Only a regular, non-symlinked file may be carried back. For a symlink
        # (or a directory, FIFO, device node) the move would relocate whatever
        # the entry points AT — an arbitrary file outside the plan directory,
        # removed from its own location — on the code path whose caller deletes
        # that directory immediately afterwards. Reporting the rejection as a
        # skip is what routes it into the veto instead of dropping it silently.
        if match.is_symlink() or not match.is_file():
            skipped.append({'lesson_id': lesson_id, 'reason': 'unsafe_source'})
            continue

        destination = (lessons_dir / f'{lesson_id}.md').resolve()
        if destination.parent != lessons_dir:
            skipped.append({'lesson_id': lesson_id, 'reason': 'path_traversal'})
            continue

        # Claim the destination with a no-replace create: ``O_EXCL`` makes the
        # collision test and the claim ONE operation. A separate ``exists()``
        # probe followed by a replacing move is a TOCTOU pair — a destination
        # created between the two is silently overwritten and the incumbent
        # lesson is lost, which is exactly the irrecoverable loss this
        # carry-back exists to prevent. A lost race is the ordinary
        # ``destination_exists`` skip, so it fires the veto like any other.
        try:
            claim_fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            skipped.append({'lesson_id': lesson_id, 'reason': 'destination_exists'})
            continue

        # Write THROUGH the claim fd. Closing it and handing the PATH back to a
        # copy helper would discard the guarantee the claim just bought: the
        # reopen is a SECOND name lookup, and between the close and it a
        # concurrent process can unlink the claimed entry and leave a symlink
        # under that name — which a ``'wb'`` reopen follows, truncating whatever
        # it points at. The claim would then protect only the collision test and
        # never the write it exists to make safe. A descriptor names the claimed
        # inode itself, so nothing swapped in under the name afterwards can be
        # written to. ``os.fdopen`` takes ownership of the fd, and entering it
        # FIRST means the ``with`` closes it exactly once even when opening the
        # source raises.
        #
        # Copy-then-unlink rather than move: the source stays in place until the
        # claim is filled, so no failure between the claim and the copy can
        # leave the lesson existing nowhere.
        try:
            with os.fdopen(claim_fd, 'wb') as claimed, match.open('rb') as carried:
                shutil.copyfileobj(carried, claimed)
        except OSError:
            # The empty claim must not outlive a failed copy — left behind, it
            # turns every later carry-back of this id into a
            # ``destination_exists`` skip against a corpus entry holding none
            # of the lesson.
            destination.unlink(missing_ok=True)
            raise
        match.unlink()
        log_entry(
            'work',
            plan_id,
            'INFO',
            f'[RESTORE] (plan-marshall:manage-status:delete-plan) Restored lesson file '
            f'lesson-{lesson_id}.md to {destination} before plan-dir deletion',
        )
        restored_ids.append(lesson_id)

    # ``restored`` asserts that every carried lesson landed. When any did not,
    # the honest value is ``restore_incomplete`` — reporting ``restored`` over a
    # possibly-empty ``restored_ids`` claims the one thing the value promises.
    return LessonCarryBack(
        'restore_incomplete' if skipped else 'restored',
        store.resolution,
        str(lessons_dir),
        restored_ids,
        skipped,
        store.detail,
    )


def cmd_delete_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Delete an entire plan directory.

    The lesson carry-back runs FIRST and can VETO the deletion. When any lesson
    the plan carries did not land in the main-anchored corpus — a destination
    collision, a traversal-shaped id, or a store that would not resolve — the
    plan directory holds the only copy, so the delete is refused with
    ``error: lesson_carry_back_incomplete`` and the directory is left intact.
    Deleting anyway is unrecoverable, and the refusal is what makes the
    previously-silent per-file skip impossible to lose a lesson through.

    ``--no-restore-lessons`` opts out of the carry-back entirely; the veto is
    part of the carry-back, so opting out also opts out of the veto. That path
    reports ``lesson_carry_back_action: not_attempted`` with
    ``lesson_store_resolution: unresolved`` — it scanned nothing and resolved
    nothing, so it may claim neither the benign scanned-and-empty outcome nor a
    resolution it never performed. The distinction is the whole audit value of
    the payload: this is the one branch that can destroy a carried lesson.
    """
    require_valid_plan_id(args)

    plan_dir = get_plan_dir(args.plan_id)

    if not plan_dir.exists():
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'plan_not_found',
            'message': f'Plan directory does not exist: {plan_dir}',
        }

    # Auto-restore moved lesson files (default behaviour; opt-out via
    # ``--no-restore-lessons``). Plans derived from multiple lessons can
    # carry more than one ``lesson-*.md`` file; restore them all.
    #
    # The opt-out sentinel must NOT borrow the benign scanned-and-empty answer:
    # this path scans nothing and never calls ``resolve_lesson_store``, so
    # claiming ``no_lesson_file`` (defined as "SCANNED and carried none") and
    # ``main_anchored`` (a resolution that never happened) reports the verified
    # zero for the one branch that can silently discard a carried lesson. An
    # auditor reading the payload could not tell "deleted a plan that verifiably
    # carried no lesson" from "deleted a plan whose lessons went unexamined".
    carry_back = LessonCarryBack(
        'not_attempted',
        'unresolved',
        '',
        [],
        [],
        'carry-back not attempted (--no-restore-lessons): the plan directory was '
        'never scanned and no lessons store was resolved, so any lesson it '
        'carries is discarded with it',
    )
    if not getattr(args, 'no_restore_lessons', False):
        carry_back = _restore_lesson_from_plan_dir(args.plan_id, plan_dir)

    # Carry-back veto: refuse to delete the directory holding the only copy of a
    # lesson that did not land. Membership is tested against the skipped list's
    # LENGTH, never its truthiness, so the guard reads the same whether the list
    # is empty or absent.
    if len(carry_back.skipped) > 0:
        skipped_ids = [row['lesson_id'] for row in carry_back.skipped]
        log_entry(
            'work',
            args.plan_id,
            'ERROR',
            f'[BLOCKED] (plan-marshall:manage-status:delete-plan) Refusing to delete '
            f'{plan_dir}: {len(skipped_ids)} carried lesson(s) did not land in the '
            f'corpus — {", ".join(skipped_ids)}',
        )
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'lesson_carry_back_incomplete',
            'action': 'refused',
            'path': str(plan_dir),
            'lesson_carry_back_action': carry_back.action,
            'lesson_store_resolution': carry_back.store_resolution,
            'lessons_dir': carry_back.lessons_dir,
            'lesson_restored': len(carry_back.restored_ids) > 0,
            'restored_lesson_ids': carry_back.restored_ids,
            'skipped_lessons': carry_back.skipped,
            'message': (
                f'{len(skipped_ids)} carried lesson(s) could not be restored '
                f'({", ".join(skipped_ids)}); the plan directory holds the only copy, '
                f'so it was NOT deleted. Resolve the conflict, or pass '
                f'--no-restore-lessons to delete anyway and discard them. '
                f'Store: {carry_back.detail}'
            ),
        }

    # Count files before deletion for audit trail
    files_removed = sum(1 for _ in plan_dir.rglob('*') if _.is_file())

    try:
        shutil.rmtree(plan_dir)
        log_entry('work', args.plan_id, 'INFO', f'[MANAGE-STATUS] Deleted plan ({files_removed} files)')
        result: dict[str, Any] = {
            'status': 'success',
            'plan_id': args.plan_id,
            'action': 'deleted',
            'path': str(plan_dir),
            'files_removed': files_removed,
            'lesson_carry_back_action': carry_back.action,
            'lesson_store_resolution': carry_back.store_resolution,
            'lessons_dir': carry_back.lessons_dir,
            'lesson_restored': len(carry_back.restored_ids) > 0,
            'restored_lesson_ids': carry_back.restored_ids,
            'skipped_lessons': carry_back.skipped,
        }
        return result
    except PermissionError as e:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'permission_denied',
            'message': f'Permission denied: {e}',
        }
    except Exception as e:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'delete_failed',
            'message': f'Failed to delete plan directory: {e}',
        }
