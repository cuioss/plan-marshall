#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Query command handlers for manage-status: read, progress, metadata, get-context, list, census.
"""

import argparse
from pathlib import Path
from typing import Any, NamedTuple

from _locks_core import rmw_json
from _status_core import (
    TITLE_TOKEN_OWNER_CLI,
    TITLE_TOKEN_OWNERS,
    TITLE_TOKEN_STATES,
    _surface_drive,
    _try_read_status_json,
    get_plans_dir,
    get_status_path,
    in_progress_phases,
    log_entry,
    normalize_metadata,
    read_title_token,
    require_status,
    title_token_is_stale,
    write_status,
)
from constants import (
    DIR_ARCHIVED,
    DIR_PLANS,
    FILE_STATUS,
    PHASE_STATUS_DONE,
    PHASE_STATUS_IN_PROGRESS,
)
from file_ops import (
    WORKTREE_STATE_DISABLED,
    WORKTREE_STATE_MATERIALIZED,
    WORKTREE_STATE_PENDING,
    derive_worktree_state,
    get_base_dir,
    get_worktree_root,
    now_utc_iso,
)
from marketplace_paths import PLAN_DIR_NAME, base_dir_override_active, resolve_main_anchored_path

# Metadata fields that are semantically boolean. The ``metadata --set`` CLI
# receives every value as a raw string; for these keys the raw string is
# coerced to a JSON boolean before storage so downstream consumers
# (e.g. phase_handshake worktree drift checks) see ``true``/``false`` rather
# than the string ``"true"``/``"false"``. Non-allowlisted fields keep
# verbatim string storage.
BOOLEAN_METADATA_FIELDS = frozenset({'use_worktree'})


def _coerce_metadata_value(field: str, raw_value: Any) -> Any:
    """Coerce a raw ``--set`` value string for typed metadata fields.

    Boolean-typed fields (see ``BOOLEAN_METADATA_FIELDS``) map the
    case-insensitive strings ``"true"``/``"false"`` to JSON booleans. Any
    other value for a boolean field, and every value for a non-boolean
    field, is returned verbatim.
    """
    if field in BOOLEAN_METADATA_FIELDS and isinstance(raw_value, str):
        lowered = raw_value.strip().lower()
        if lowered == 'true':
            return True
        if lowered == 'false':
            return False
    return raw_value


def cmd_read(args: argparse.Namespace) -> dict[str, Any] | None:
    """Read plan status."""
    status = require_status(args)
    if status is None:
        return None

    return {'status': 'success', 'plan_id': args.plan_id, 'plan': status}


def cmd_set_phase(args: argparse.Namespace) -> dict[str, Any] | None:
    """Set current phase."""
    status = require_status(args)
    if status is None:
        return None

    phase_names = [p['name'] for p in status.get('phases', [])]
    if args.phase not in phase_names:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_phase',
            'message': f'Invalid phase: {args.phase}',
            'valid_phases': phase_names,
        }

    previous = status.get('current_phase')
    status['current_phase'] = args.phase

    # Loop-back detection: a backward move (target phase precedes the current
    # phase in the plan's phase list) structurally guarantees handshake drift
    # at the next guarded boundary — the re-entered phase will re-capture its
    # invariants against a tree that has legitimately moved on. Persist a
    # scheduling marker alongside the phase write so cmd_transition's inline
    # guard can auto-resolve exactly that expected-by-construction drift
    # (see _cmd_lifecycle.cmd_transition). Forward moves never write it.
    is_loop_back = previous in phase_names and phase_names.index(previous) > phase_names.index(args.phase)
    if is_loop_back:
        metadata = normalize_metadata(status)
        metadata['loop_back_reentry'] = {
            'from_phase': previous,
            'to_phase': args.phase,
            'at': now_utc_iso(),
        }

    # Update phase statuses
    for phase in status['phases']:
        if phase['name'] == args.phase:
            phase['status'] = PHASE_STATUS_IN_PROGRESS

    # No title-token sweep here: staleness is a READ-side property resolved by
    # the aged-token predicate (_status_core.title_token_is_stale), so a
    # stranded token self-heals on the next read rather than waiting for a
    # phase to happen to change.
    write_status(args.plan_id, status)
    # Persisted-title-state-write drive seam (best-effort, fire-and-forget):
    # cmd_set_phase is a current_phase write, so bind + repaint fire here so the
    # title reflects the new phase immediately. A delegation failure never
    # changes this command's status or exit code.
    _surface_drive(args.plan_id)
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-STATUS] Phase: {previous} -> {args.phase}')
    if is_loop_back:
        log_entry(
            'decision',
            args.plan_id,
            'INFO',
            f'(plan-marshall:manage-status) Loop-back set-phase {previous} -> {args.phase}: '
            'persisted metadata.loop_back_reentry — the next guarded-boundary handshake '
            'drift is scheduled for auto-override re-capture',
        )

    return {'status': 'success', 'plan_id': args.plan_id, 'current_phase': args.phase, 'previous_phase': previous}


def cmd_update_phase(args: argparse.Namespace) -> dict[str, Any] | None:
    """Update a specific phase status."""
    status = require_status(args)
    if status is None:
        return None

    found = False
    for phase in status.get('phases', []):
        if phase['name'] == args.phase:
            phase['status'] = args.status
            found = True
            break

    if not found:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'phase_not_found',
            'message': f"Phase '{args.phase}' not found",
        }

    write_status(args.plan_id, status)

    return {'status': 'success', 'plan_id': args.plan_id, 'phase': args.phase, 'phase_status': args.status}


def cmd_progress(args: argparse.Namespace) -> dict[str, Any] | None:
    """Calculate plan progress."""
    status = require_status(args)
    if status is None:
        return None

    phases = status.get('phases', [])
    total = len(phases)
    completed = sum(1 for p in phases if p.get('status') == PHASE_STATUS_DONE)
    percent = int((completed / total) * 100) if total > 0 else 0

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'progress': {
            'total_phases': total,
            'completed_phases': completed,
            'current_phase': status.get('current_phase'),
            'percent': percent,
        },
    }


def _cmd_metadata_append(args: argparse.Namespace) -> dict[str, Any]:
    """Append ``--value`` to a LIST-valued metadata field, atomically.

    Exists because some plan identities are inherently multi-valued and a scalar
    field modelling one of them gets CLOBBERED rather than extended: the second
    writer has nowhere to put its value except on top of the first. The session
    identity is the motivating case — a plan can legitimately span several
    sessions (any resume), so every later writer overwrote the identity of the
    session that came before it.

    The read-modify-write runs inside ``rmw_json``'s O_EXCL critical section, the
    same guard ``cmd_title_token`` and ``write_status`` commit through. A plain
    ``require_status`` → mutate → ``write_status`` would carry a check-then-act
    window between the snapshot read and the commit, and losing an append in that
    window is precisely the defect this verb exists to prevent — see
    ``ref-code-quality/standards/code-organization.md`` § TOCTOU /
    Check-Then-Act Hazards.

    Semantics:

    - field absent      → the field becomes ``[value]``
    - field is a list   → ``value`` is appended, unless already present (append
      is idempotent, so a re-run of the same capture does not grow the list)
    - field is NOT a list → ``metadata_field_not_a_list`` error, and the document
      is left BYTE-IDENTICAL (``rmw_json`` commits unconditionally, so the
      mutator returns the state it was handed, untouched — including
      ``updated``). The value is not coerced into a list: silently rewriting a
      caller's scalar into a container is a type change made on a guess, and a
      field genuinely migrating to a list should be renamed so its plurality is
      visible to every reader.
    """
    outcome: dict[str, Any] = {}

    def _apply(current: dict[str, Any]) -> dict[str, Any]:
        metadata = normalize_metadata(current)
        existing = metadata.get(args.field)
        if existing is not None and not isinstance(existing, list):
            outcome['error'] = type(existing).__name__
            return current
        values: list[Any] = list(existing) if isinstance(existing, list) else []
        already = args.value in values
        if not already:
            values.append(args.value)
        metadata[args.field] = values
        current['metadata'] = metadata
        current['updated'] = now_utc_iso()
        outcome['values'] = values
        outcome['already_present'] = already
        return current

    rmw_json(get_status_path(args.plan_id), _apply)

    if 'error' in outcome:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'field': args.field,
            'error': 'metadata_field_not_a_list',
            'message': (
                f"Metadata field '{args.field}' holds a {outcome['error']}, not a list — "
                f'--append cannot extend it. Nothing was written.'
            ),
        }

    if not outcome['already_present']:
        log_entry(
            'work',
            args.plan_id,
            'INFO',
            f'[MANAGE-STATUS] Metadata append: {args.field}+={args.value}',
        )

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'field': args.field,
        'value': outcome['values'],
        'appended': not outcome['already_present'],
    }


def cmd_metadata(args: argparse.Namespace) -> dict[str, Any] | None:
    """Get, set, or append to a metadata field in status.json."""
    if args.set and getattr(args, 'append', False):
        if args.value is None:
            return {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'missing_value',
                'message': '--value is required for --set --append',
            }
        # Guard the plan's existence on the same seam every other branch uses,
        # BEFORE opening the critical section.
        if require_status(args) is None:
            return None
        return _cmd_metadata_append(args)

    status = require_status(args)
    if status is None:
        return None

    if getattr(args, 'append', False):
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'append_without_set',
            'message': '--append is a modifier for --set; pass --set --append --field F --value V',
        }

    if args.set:
        # Set metadata
        if 'metadata' not in status:
            status['metadata'] = {}

        previous_value = status['metadata'].get(args.field)
        coerced_value = _coerce_metadata_value(args.field, args.value)
        status['metadata'][args.field] = coerced_value

        write_status(args.plan_id, status)
        log_entry('work', args.plan_id, 'INFO', f'[MANAGE-STATUS] Metadata: {args.field}={coerced_value}')

        result: dict[str, Any] = {
            'status': 'success',
            'plan_id': args.plan_id,
            'field': args.field,
            'value': coerced_value,
        }
        if previous_value is not None:
            result['previous_value'] = previous_value
        return result

    elif args.get:
        # Get metadata
        metadata = status.get('metadata', {})
        value = metadata.get(args.field)

        if value is None:
            return {
                'status': 'not_found',
                'plan_id': args.plan_id,
                'field': args.field,
                'message': f"Metadata field '{args.field}' not found",
                'available_fields': list(metadata.keys()),
            }

        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'field': args.field,
            'value': value,
        }

    else:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'missing_operation',
            'message': 'Either --get or --set is required',
        }


def cmd_title_token(args: argparse.Namespace) -> dict[str, Any] | None:
    """Set or clear the structured ``title_token`` record in status.json.

    The title token is a ``{owner, state, set_at}`` record written into
    ``status.title_token``. manage-status performs NO rendering — the
    composition (glyph vocabulary + ``{icon} {body}`` assembly) lives in
    ``manage-terminal-title``. This verb only persists the record so the
    per-target renderer can read it.

    - ``set`` writes the record with the caller's ``--owner`` and a fresh
      ``set_at``. ``--state`` is validated against ``TITLE_TOKEN_STATES``.
      A set from ANY owner replaces the record wholesale (last-writer wins),
      so the record always names its current owner.
    - ``clear`` is OWNER-SCOPED: it removes the field only when the caller
      owns the live record, or when the live record is stale. A foreign clear
      is a reported no-op, so a lock glyph cannot be clobbered by an unrelated
      build bracket. Clearing an already-absent token is idempotent.

    Both verbs mutate ``status.json`` inside a single ``rmw_json`` critical
    section. Four independent writers (the build-hook render assist,
    merge_lock's two lock surfaces, and merge_lock's clear) mutate this one
    field from separate executor subprocesses, so a plain read-modify-write
    carries a check-then-act window in which a concurrent set is silently
    dropped. The O_EXCL guard-file mutex closes it — see
    ``ref-code-quality/standards/code-organization.md`` § TOCTOU /
    Check-Then-Act Hazards.

    Those four are the writers that TARGET this field, but they are not the
    only processes that can destroy a record written here: every full-document
    ``status.json`` writer (phase writes, transitions, create) commits a whole
    document assembled from an earlier snapshot read, so one committing after a
    set here would restore the snapshot's stale ``title_token``. That second
    window is closed at the shared write seam rather than in this verb —
    ``_status_core.write_status`` commits inside the SAME ``rmw_json`` guard
    (same path, therefore the same guard file) and carries over the record read
    inside the guard. Both windows are therefore closed for all writers, not
    only for the four that name this field.

    The record shape, owner vocabulary, arbitration rule, and staleness
    threshold are specified once in
    ``platform-runtime/standards/terminal-title-architecture.md``
    § Channel Delivery Contract ruling (c).
    """
    status = require_status(args)
    if status is None:
        return None

    owner = getattr(args, 'owner', None) or TITLE_TOKEN_OWNER_CLI
    if owner not in TITLE_TOKEN_OWNERS:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_title_token_owner',
            'message': f'Invalid title-token owner: {owner}',
            'valid_owners': sorted(TITLE_TOKEN_OWNERS),
        }

    if args.token_verb == 'set':
        state = args.state
        if state not in TITLE_TOKEN_STATES:
            return {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_title_token_state',
                'message': f'Invalid title-token state: {state}',
                'valid_states': sorted(TITLE_TOKEN_STATES),
            }
        record: dict[str, Any] = {'owner': owner, 'state': state, 'set_at': now_utc_iso()}

        # Whether this set CHANGES the stored value, decided inside the critical
        # section against the freshly-read record (the same discipline the clear
        # branch below applies). ``set_at`` is deliberately excluded from the
        # comparison: it is refreshed on every call by construction, so including
        # it would make every set "changed" and suppress nothing.
        set_outcome: dict[str, Any] = {'changed': True}

        def _apply_set(current: dict[str, Any]) -> dict[str, Any]:
            # Read through ``read_title_token`` — the staleness-aware accessor —
            # not the raw field. A record past TITLE_TOKEN_STALE_AFTER_SECONDS
            # "reads as absent" to every reader, so re-asserting it IS a change
            # (absent → present) and must log. Comparing the raw field would
            # stay silent about a token the renderers had already stopped
            # honouring.
            previous = read_title_token(current)
            set_outcome['changed'] = not (
                isinstance(previous, dict) and previous.get('owner') == owner and previous.get('state') == state
            )
            current['title_token'] = record
            current['updated'] = now_utc_iso()
            return current

        rmw_json(get_status_path(args.plan_id), _apply_set)
        # Log only a value CHANGE. The PreToolUse:Bash render hook (Claude
        # target — see ``platform-runtime/standards/terminal-title-architecture.md``
        # § Channel Delivery Contract ruling (c)) re-asserts the
        # same (owner, state) pair on every build command, so an unconditional
        # emission turned one bracket into a run of identical work-log lines
        # carrying no new information. The write itself is never suppressed —
        # ``set_at`` still refreshes, so the aged-token staleness predicate keeps
        # seeing a live token across a long build.
        if set_outcome['changed']:
            log_entry('work', args.plan_id, 'INFO', f'[MANAGE-STATUS] Title token: {state} (owner={owner})')
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'title_token': record,
            'changed': set_outcome['changed'],
        }

    # clear — owner-scoped. The arbitration decision is taken INSIDE the
    # critical section against the freshly-read record, never against the
    # copy read before the guard was acquired.
    outcome: dict[str, Any] = {'cleared': False, 'previous': None, 'reason': None}

    def _apply_clear(current: dict[str, Any]) -> dict[str, Any]:
        previous = current.get('title_token')
        outcome['previous'] = previous
        if previous is None:
            outcome['reason'] = 'absent'
            return current
        stale = title_token_is_stale(previous)
        record_owner = previous.get('owner') if isinstance(previous, dict) else None
        if not stale and record_owner != owner:
            outcome['reason'] = 'foreign_owner'
            return current
        current.pop('title_token', None)
        current['updated'] = now_utc_iso()
        outcome['cleared'] = True
        outcome['reason'] = 'stale' if stale else 'owned'
        return current

    rmw_json(get_status_path(args.plan_id), _apply_clear)
    if outcome['cleared']:
        log_entry(
            'work',
            args.plan_id,
            'INFO',
            f'[MANAGE-STATUS] Title token cleared by {owner} (was: {outcome["previous"]})',
        )
    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'title_token': None if outcome['cleared'] else outcome['previous'],
        'cleared': outcome['cleared'],
        'reason': outcome['reason'],
    }


def cmd_get_context(args: argparse.Namespace) -> dict[str, Any] | None:
    """Get combined status context (phase, progress, metadata)."""
    status = require_status(args)
    if status is None:
        return None

    phases = status.get('phases', [])
    total = len(phases)
    completed = sum(1 for p in phases if p.get('status') == PHASE_STATUS_DONE)

    # Build context
    context: dict[str, Any] = {
        'status': 'success',
        'plan_id': args.plan_id,
        'title': status.get('title', ''),
        'current_phase': status.get('current_phase', 'unknown'),
        'total_phases': total,
        'completed_phases': completed,
    }

    # Include metadata fields at top level for convenience
    metadata = status.get('metadata', {})
    for key, value in metadata.items():
        context[key] = value

    return context


def cmd_get_worktree_path(args: argparse.Namespace) -> dict[str, Any] | None:
    """Return the persisted worktree path for a plan as a tri-state response.

    Reads ``status.metadata.use_worktree`` and ``status.metadata.worktree_path``
    and returns the path so that callers (build wrappers, git_workflow,
    phase-entry assertions) can resolve the active worktree from a
    plan-id alone — no ``--project-dir``, no filesystem layout
    re-derivation.

    Output contract (tri-state, discriminated by ``worktree_state``):

    - ``use_worktree == false`` (or metadata absent) →
      ``worktree_state: disabled``, ``worktree_path: ''``. The plan runs
      against the main checkout.
    - ``use_worktree == true`` and ``worktree_path`` is empty/missing →
      ``worktree_state: pending``, ``worktree_path: ''``,
      ``not_yet_materialized: true``. The plan opted into a worktree but
      it has not been materialized yet (pre-materialization). Callers
      MUST fall back to the main checkout cwd.
    - ``use_worktree == true`` and ``worktree_path`` is set →
      ``worktree_state: materialized``, ``worktree_path: <abs>``. The
      worktree is materialized and the path is authoritative.
    """
    status = require_status(args)
    if status is None:
        return None

    metadata = status.get('metadata') or {}
    # The state machine is derived by the ONE function that owns it, so the
    # published discriminator and any consumer that reads status metadata
    # directly (rather than shelling out here) cannot drift apart.
    worktree_state, worktree_path = derive_worktree_state(metadata)

    if worktree_state == WORKTREE_STATE_DISABLED:
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'use_worktree': False,
            'worktree_state': WORKTREE_STATE_DISABLED,
            'worktree_path': '',
        }

    if worktree_state == WORKTREE_STATE_PENDING:
        pending: dict[str, Any] = {
            'status': 'success',
            'plan_id': args.plan_id,
            'use_worktree': True,
            'worktree_state': WORKTREE_STATE_PENDING,
            'worktree_path': '',
            'not_yet_materialized': True,
        }
        worktree_branch = metadata.get('worktree_branch')
        if worktree_branch:
            pending['worktree_branch'] = worktree_branch
        return pending

    result: dict[str, Any] = {
        'status': 'success',
        'plan_id': args.plan_id,
        'use_worktree': True,
        'worktree_state': WORKTREE_STATE_MATERIALIZED,
        'worktree_path': worktree_path,
    }
    worktree_branch = metadata.get('worktree_branch')
    if worktree_branch:
        result['worktree_branch'] = worktree_branch
    return result


def _passes_phase_filter(current_phase: str, filter_arg: str | None) -> bool:
    """Return whether ``current_phase`` survives the ``--filter`` phase filter.

    ``filter_arg`` is the raw comma-separated ``args.filter`` value (or
    ``None`` when no filter was supplied, in which case every plan passes).
    Shared by the main-checkout enumeration and the worktree scan so both
    paths honour the same filter semantics.
    """
    if not filter_arg:
        return True
    filter_phases = [p.strip() for p in filter_arg.split(',')]
    return current_phase in filter_phases


def _resolution_scope() -> str:
    """Classify ``cmd_list``'s enumeration scope: ``main`` vs ``worktree_local``.

    ``cmd_list`` resolves ``get_plans_dir()`` / ``get_worktree_root()``
    cwd-relatively under the uniform resolver (ADR-002). The resolved scope is NOT
    the same in every checkout, and a consumer that reads the enumeration as an
    authoritative census MUST know which:

      * ``main`` — the current base IS the main-anchored ``.plan/local``. The scan
        observes main's plans AND every sibling worktree
        (``get_worktree_root()`` == ``<main>/.plan/local/worktrees``), so an absent
        plan is authoritative absence.
      * ``worktree_local`` — the current base is a pinned worktree's own
        ``.plan/local``. ``get_plans_dir()`` / ``get_worktree_root()`` anchor THERE,
        so the scan observes only this worktree's own moved-in plan and is
        structurally BLIND to sibling worktrees. An absent plan under this scope is
        ``unknown`` (not-observed-from-this-scope), NOT authoritative absence — the
        sibling-worktree shape. A destructive/authority-bearing consumer MUST
        NOT treat a ``worktree_local`` empty as proof of absence; route the decision
        through a main-anchored verdict (e.g. ``merge_lock check`` staleness). See
        ``manage-locks/standards/cwd-keyed-store-resolution-audit.md``.
      * ``unknown`` — the base (or the main-anchored base) could not be resolved
        (outside a git repo, no override). Fail-closed: neither authoritative.

    The verdict is surfaced on the ``cmd_list`` output as a first-class ``scope``
    field so consumers cannot silently mistake a cwd-scoped census for a global one.
    """
    try:
        main_base = resolve_main_anchored_path('')
        current_base = get_base_dir()
    except (RuntimeError, OSError):
        return 'unknown'
    try:
        return 'main' if current_base.resolve() == main_base.resolve() else 'worktree_local'
    except OSError:
        return 'main' if str(current_base) == str(main_base) else 'worktree_local'


def cmd_list(args: argparse.Namespace) -> dict[str, Any]:
    """Discover all plans across the main checkout AND its worktrees.

    Enumerates two sources and merges them deduped by plan id:

    - **Main checkout** (``get_plans_dir()``): plans whose directory lives on
      the current checkout. Each is tagged ``location: 'current'``.
    - **Worktrees** (``get_worktree_root()`` children): a phase-5+ plan whose
      directory was MOVED into its worktree at execute entry (ADR-002) is no
      longer present under ``get_plans_dir()``, so a plain main-only walk is
      blind to it. The worktree scan probes each worktree's
      ``{wt}/.plan/local/plans`` for plan dirs with a readable ``status.json``
      and surfaces them tagged ``location: 'worktree'``. The probed layout is
      the exact ``get_worktree_root() / {id} / .plan/local/plans/{id}`` path
      that ``worktree-create`` materializes and ``cmd_locate_plan_checkout``
      probes — single-sourced via ``PLAN_DIR_NAME`` / ``DIR_PLANS``.

    Each entry carries ``{id, current_phase, status, location}``. The merged
    list is deduped by id (a moved-in plan appears exactly once — main never
    holds it post-move; dedup is defensive against the transient both-present
    window) and sorted by id for stable ordering regardless of checkout. The
    worktree scan is guarded against the outside-git-repo ``RuntimeError`` from
    ``get_worktree_root()`` — on that error the main-only result is returned.

    The output also carries a ``scope`` field (``main`` / ``worktree_local`` /
    ``unknown``, from :func:`_resolution_scope`) naming the enumeration's
    authoritativeness: a ``worktree_local`` census is cwd-scoped and BLIND to
    sibling worktrees, so a consumer MUST NOT read an absent plan under it as
    authoritative absence (the sibling-worktree shape). See
    ``manage-locks/standards/cwd-keyed-store-resolution-audit.md``.
    """
    plans: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    # Source 1: main-checkout plans. Tolerate a missing plans dir so a fresh
    # main checkout with no plans/ dir but an active worktree still reaches the
    # worktree scan below.
    plans_dir = get_plans_dir()
    if plans_dir.is_dir():
        for plan_dir in sorted(plans_dir.iterdir()):
            if not plan_dir.is_dir():
                continue

            status = _try_read_status_json(plan_dir)
            if not isinstance(status, dict) or not status:
                continue

            try:
                current_phase = status.get('current_phase', 'unknown')
                if not _passes_phase_filter(current_phase, args.filter):
                    continue
                plans.append(
                    {
                        'id': plan_dir.name,
                        'current_phase': current_phase,
                        'status': PHASE_STATUS_IN_PROGRESS,
                        'location': 'current',
                    }
                )
                seen_ids.add(plan_dir.name)
            except (KeyError, TypeError):
                # Skip plans with corrupted status
                continue

    # Source 2: worktree-resident plans. Outside a git repo get_worktree_root()
    # raises RuntimeError — skip the scan entirely and return the main-only
    # result rather than crashing.
    try:
        worktree_root = get_worktree_root()
    except RuntimeError:
        worktree_root = None

    if worktree_root is not None and worktree_root.is_dir():
        for worktree_dir in sorted(worktree_root.iterdir()):
            if not worktree_dir.is_dir():
                continue

            wt_plans_dir = worktree_dir / PLAN_DIR_NAME / 'local' / DIR_PLANS
            if not wt_plans_dir.is_dir():
                continue

            try:
                plan_dirs = sorted(wt_plans_dir.iterdir())
            except OSError:
                continue

            for plan_dir in plan_dirs:
                if not plan_dir.is_dir() or plan_dir.name in seen_ids:
                    continue

                status = _try_read_status_json(plan_dir)
                if not isinstance(status, dict) or not status:
                    continue

                try:
                    current_phase = status.get('current_phase', 'unknown')
                    if not _passes_phase_filter(current_phase, args.filter):
                        continue
                    plans.append(
                        {
                            'id': plan_dir.name,
                            'current_phase': current_phase,
                            'status': PHASE_STATUS_IN_PROGRESS,
                            'location': 'worktree',
                        }
                    )
                    seen_ids.add(plan_dir.name)
                except (KeyError, TypeError):
                    continue

    plans.sort(key=lambda p: p['id'])

    # Surface the resolution scope as a first-class field: a `worktree_local` census
    # is structurally blind to sibling worktrees, so an absent plan under it is
    # `unknown`, NOT authoritative absence (the sibling-worktree shape). See _resolution_scope.
    return {
        'status': 'success',
        'total': len(plans),
        'scope': _resolution_scope(),
        'plans': plans,
    }


def cmd_list_orphans(args: argparse.Namespace) -> dict[str, Any]:  # args unused: the uniform cmd_* handler signature
    """Discover orphan plan directories (directories without a readable status.json).

    Inverse of ``cmd_list``: walks ``plans_dir.iterdir()`` and collects directory
    entries that do NOT have a readable ``status.json`` file. Plans with a
    readable status.json are skipped. The ``archived-plans`` directory (if
    present as a sibling) is excluded — orphan scanning operates only on the
    active plans directory returned by ``get_plans_dir()``.

    Output contract:
        status: success
        total: N
        orphans: [{id, path, contents}]

    Each orphan entry includes:
        - ``id``: directory name
        - ``path``: absolute filesystem path
        - ``contents``: sorted list of top-level entry names inside the orphan
          directory (files and subdirectories). Empty list when the directory
          has no entries.
    """
    plans_dir = get_plans_dir()
    # Use is_dir() rather than exists() so a stray file at the plans_dir path
    # returns total=0 cleanly instead of raising NotADirectoryError from iterdir().
    if not plans_dir.is_dir():
        return {'status': 'success', 'total': 0, 'orphans': []}

    orphans: list[dict[str, Any]] = []
    for plan_dir in sorted(plans_dir.iterdir()):
        if not plan_dir.is_dir():
            continue

        # Skip plans whose status.json FILE is present — matches the
        # require_plan_exists guard in tools-file-ops/file_ops.py. An empty
        # ``{}`` status.json is a valid plan file and must NOT be flagged as
        # orphan; only directories with no status.json file at all are orphans.
        if (plan_dir / 'status.json').is_file():
            continue

        # Collect top-level contents for caller-side decision making. On
        # OSError (e.g., permission denied) emit a single '<unreadable>'
        # sentinel rather than an empty list — an empty list would trigger
        # silent deletion under planning.md Step 3b. The sentinel forces a
        # user prompt instead.
        try:
            contents = sorted(entry.name for entry in plan_dir.iterdir())
        except OSError:
            contents = ['<unreadable>']

        orphans.append({'id': plan_dir.name, 'path': str(plan_dir), 'contents': contents})

    return {'status': 'success', 'total': len(orphans), 'orphans': orphans}


# =============================================================================
# Plan census (cmd_census)
# =============================================================================
# The census answers "how many plans does each store hold, and is any of them
# still recording an open phase?" from the MAIN checkout, whatever the caller's
# cwd. It is deliberately NOT built on the cwd-relative ``get_plans_dir()`` /
# ``get_archive_dir()`` / ``get_worktree_root()`` family that ``cmd_list`` uses:
# those resolve wherever the working directory is, so a phase-5+ caller pinned
# into a worktree counts that worktree's own moved-in plan and reads a zero for
# everything else. (``cleanup-status``'s ``archived_plans_total`` is the live
# instance of that defect: it binds its base directory at module import, so from
# a worktree it publishes ``0`` against a non-zero main-anchored truth.) Every
# cohort below resolves through ``resolve_main_anchored_path`` — ADR-002's single
# sanctioned main-anchored exception — so the answer does not move with cwd.

#: Cohort identifiers — one per plan store, counted SEPARATELY and never summed.
#: A live plan, a plan moved into its worktree, and an archived plan are three
#: different populations; a blended total answers no caller's question and hides
#: which store a number came from.
CENSUS_COHORT_LIVE = 'live'
CENSUS_COHORT_WORKTREE = 'worktree'
CENSUS_COHORT_ARCHIVED = 'archived'

#: Per-cohort coverage tri-state. The distinction this verb exists to publish:
#:
#: - ``complete``   — the cohort was enumerated in full. Every member was read.
#: - ``partial``    — the cohort was enumerated, but at least one entry went
#:                    unread: a member whose ``status.json`` would not parse, or
#:                    an entry whose membership could not be established at all.
#:                    ``population`` is what was found and ``unreadable_count``
#:                    is non-zero, so the shortfall is visible instead of being
#:                    absorbed into the count.
#: - ``unevaluated`` — the cohort was NOT enumerated at all. It publishes NO
#:                    count keys whatsoever (see :func:`_census_row`), because a
#:                    zero from a cohort that was never looked at is
#:                    indistinguishable from a verified empty one.
CENSUS_COVERAGE_COMPLETE = 'complete'
CENSUS_COVERAGE_PARTIAL = 'partial'
CENSUS_COVERAGE_UNEVALUATED = 'unevaluated'

#: Which anchor the cohort paths were resolved against. ``override`` names the
#: ``PLAN_BASE_DIR`` / ``set_base_dir()`` branch of
#: :func:`marketplace_paths.resolve_main_anchored_path` (the branch every
#: fixture-driven caller takes), ``main`` the production git-common-dir branch.
#: Reported so a reader can tell a census of a real checkout from a census of a
#: redirected store rather than having to infer it from ``anchor_path``.
CENSUS_ANCHOR_MAIN = 'main'
CENSUS_ANCHOR_OVERRIDE = 'override'

#: Trailing segment of the main-anchored worktree container. ``constants.py``
#: deliberately exports no name for it ("the worktree root is intentionally NOT
#: a constant here"), and ``file_ops`` spells the same literal inline where it
#: composes ``<plan-root>/.plan/local/worktrees``; this is that segment, joined
#: onto the main-anchored base rather than onto a cwd-resolved one.
CENSUS_WORKTREES_DIRNAME = 'worktrees'

#: Outcome of one attempt to list a directory of plan directories.
_SCAN_SCANNED = 'scanned'
_SCAN_ABSENT = 'absent'
_SCAN_UNLISTABLE = 'unlistable'


class _ContainerScan(NamedTuple):
    """What one directory-of-plan-directories yielded.

    ``state`` is the discriminator and MUST be read first: on ``absent`` and
    ``unlistable`` every count and list is structurally meaningless (nothing was
    counted) and is left empty only because a NamedTuple has no absent field.
    The caller converts them into the published row, which is where the
    never-a-bare-zero rule is enforced.

    The two shortfalls are carried SEPARATELY rather than summed here, because
    they are different facts: an unreadable ``status.json`` belongs to a
    directory already established to be a plan, while an unexaminable entry is
    one whose membership could not be established at all. The caller sums them
    into the published ``unreadable_count`` and names each in the ``reason``.

    Attributes:
        state: ``scanned`` | ``absent`` | ``unlistable``.
        population: Plan directories found (entries carrying a ``status.json``).
        unreadable: How many of those could not be parsed into a status dict.
        records: One ``{cohort, id, open_phases}`` row per plan holding an open
            phase.
        unreadable_ids: Directory names behind ``unreadable``, for the reason.
        unexaminable_ids: Names of entries that could not be examined at all, so
            their membership is unknown. NOT counted in ``population`` — nothing
            established they are plans — but never dropped either.
    """

    state: str
    population: int
    unreadable: int
    records: list[dict[str, Any]]
    unreadable_ids: list[str]
    unexaminable_ids: list[str]


def _open_phase_names(status: dict[Any, Any]) -> list[str]:
    """Return the NAMES of every phase recorded as ``in_progress``.

    A thin naming projection over :func:`_status_core.in_progress_phases`, which owns
    the predicate. The census and ``cmd_archive``'s closure loop therefore ask the same
    question through the same function: the set of phases the archive closes and the set
    this verb reports as open cannot drift into two different answers, which they would
    the moment either side re-spelled ``status == in_progress`` locally.

    The predicate is the ``phases[]`` status and nothing else — deliberately NOT
    ``metadata.loop_back_reentry``. That marker records that a loop-back was SCHEDULED,
    which is neither necessary nor sufficient for a phase being left open: a plan can
    carry the marker with every phase closed, and a plan with no marker can still hold
    an ``in_progress`` phase, which is exactly the population this census exists to
    find.
    """
    return [str(phase.get('name', '')) for phase in in_progress_phases(status)]


def _scan_plan_container(container: Path, cohort: str) -> _ContainerScan:
    """Enumerate one directory whose children are plan directories.

    Absence and un-listability are returned as SEPARATE states, which is why the
    listing is attempted directly instead of being guarded by an ``exists()``
    probe: a cohort directory that is simply not there is a verified empty
    population, while one that exists but cannot be read is a cohort nothing is
    known about. An ``exists()``-then-``iterdir()`` pair would also be a
    check-then-act window, and collapsing the two outcomes is precisely the
    false-zero this verb refuses to publish.

    Population membership is "directory carrying a ``status.json`` file". A
    directory WITHOUT one is not a plan and is skipped — that is the orphan
    population, owned by :func:`cmd_list_orphans`. A ``status.json`` that is
    present but will not parse into a dict counts toward ``unreadable`` rather
    than being dropped, so it lands in the cohort's ``partial`` verdict.

    An entry the membership probe itself cannot complete is the third outcome,
    and it is CREDITED rather than skipped: it lands in ``unexaminable_ids``, so
    the cohort reports ``partial`` over what it did read instead of publishing
    ``complete`` over an enumeration it knows fell short.
    """
    try:
        entries = sorted(container.iterdir())
    except FileNotFoundError:
        return _ContainerScan(_SCAN_ABSENT, 0, 0, [], [], [])
    except OSError:
        # Present but unreadable (a file where a directory was expected, a
        # permission denial, an unreadable mount). Nothing was enumerated.
        return _ContainerScan(_SCAN_UNLISTABLE, 0, 0, [], [], [])

    population = 0
    unreadable = 0
    records: list[dict[str, Any]] = []
    unreadable_ids: list[str] = []
    unexaminable_ids: list[str] = []

    for entry in entries:
        try:
            if not entry.is_dir() or not (entry / FILE_STATUS).is_file():
                continue
        except OSError:
            # The probe could not be completed (``is_dir`` already absorbs the
            # benign races — ENOENT, ENOTDIR, a symlink loop — and returns
            # False, so reaching here means a genuine denial such as EACCES).
            # Whether this entry is a plan is therefore UNKNOWN, not "no": it is
            # credited as a shortfall rather than dropped, and deliberately NOT
            # added to ``population``, which only ever counts established
            # members. Continuing silently here is what would let the cohort
            # claim ``complete`` over an entry it never managed to look at.
            unexaminable_ids.append(entry.name)
            continue
        population += 1
        status = _try_read_status_json(entry)
        if not isinstance(status, dict):
            # ``_try_read_status_json`` returns None for BOTH an absent and an
            # unparseable status.json; the ``is_file`` guard above has already
            # established presence, so reaching here means unparseable.
            unreadable += 1
            unreadable_ids.append(entry.name)
            continue
        open_phases = _open_phase_names(status)
        if open_phases:
            records.append({'cohort': cohort, 'id': entry.name, 'open_phases': open_phases})

    return _ContainerScan(_SCAN_SCANNED, population, unreadable, records, unreadable_ids, unexaminable_ids)


#: Reason fragment naming entries whose membership could not be established. The
#: names are listed rather than counted in the prose: the count is already
#: published as part of ``unreadable_count``, and the names are what a reader
#: needs to go and look.
_UNEXAMINABLE_REASON = 'directory entries that could not be examined, so their membership is unknown'


def _scan_shortfall_reason(scan: _ContainerScan) -> str:
    """Name every shortfall one container scan hit, as one ``;``-joined reason.

    Both shortfalls feed the single published ``unreadable_count`` — each is a
    part of the cohort that went unread — but they are named separately, because
    an unparseable ``status.json`` and an entry nobody could examine send a
    reader to different places. Returns ``''`` when the scan hit neither, which
    is exactly the ``complete`` case where there is no shortfall to name.
    """
    parts: list[str] = []
    if scan.unreadable:
        parts.append(
            f'{scan.unreadable} of {scan.population} plan(s) carry an unreadable '
            f'status.json: {", ".join(scan.unreadable_ids)}'
        )
    if scan.unexaminable_ids:
        parts.append(f'{_UNEXAMINABLE_REASON}: {", ".join(scan.unexaminable_ids)}')
    return '; '.join(parts)


def _census_row(
    cohort: str,
    coverage: str,
    *,
    population: int | None = None,
    open_phase_count: int | None = None,
    unreadable_count: int | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Assemble one cohort row, OMITTING every count the cohort cannot justify.

    Key absence is the contract, not a formatting detail. An ``unevaluated``
    cohort passes ``None`` for all three counts and the row carries none of
    them, so a consumer that branches on ``population`` finds no key rather than
    a ``0`` it would read as "this store is empty". The rule covers
    ``unreadable_count`` for the same reason it covers the other two: on a
    cohort that was never enumerated, "zero unreadable members" is a claim about
    members nobody looked at. ``reason`` is present on ``unevaluated`` and
    ``partial`` and omitted on ``complete``, where there is no shortfall to name.
    """
    row: dict[str, Any] = {'cohort': cohort, 'coverage': coverage}
    if population is not None:
        row['population'] = population
    if open_phase_count is not None:
        row['open_phase_count'] = open_phase_count
    if unreadable_count is not None:
        row['unreadable_count'] = unreadable_count
    if reason is not None:
        row['reason'] = reason
    return row


def _census_single_container(cohort: str, container: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build the cohort row for a store held in ONE directory (live, archived).

    ``complete`` is reserved for a scan with NO shortfall of either kind: the
    published ``unreadable_count`` sums the unparseable members and the entries
    whose membership could not be established, and any non-zero sum degrades the
    cohort to ``partial``. A cohort that reported ``complete`` while knowing it
    had skipped an entry would be asserting a count over a population it had
    failed to enumerate in full.
    """
    scan = _scan_plan_container(container, cohort)

    if scan.state == _SCAN_ABSENT:
        # A resolved anchor with no cohort directory is a verified empty store,
        # not an unevaluated one: the anchor was reachable and the directory
        # demonstrably holds nothing.
        return _census_row(cohort, CENSUS_COVERAGE_COMPLETE, population=0, open_phase_count=0, unreadable_count=0), []

    if scan.state == _SCAN_UNLISTABLE:
        return (
            _census_row(
                cohort,
                CENSUS_COVERAGE_UNEVALUATED,
                reason=f'cohort directory {container} exists but could not be listed, so no member was enumerated',
            ),
            [],
        )

    shortfall = scan.unreadable + len(scan.unexaminable_ids)
    if shortfall:
        return (
            _census_row(
                cohort,
                CENSUS_COVERAGE_PARTIAL,
                population=scan.population,
                open_phase_count=len(scan.records),
                unreadable_count=shortfall,
                reason=_scan_shortfall_reason(scan),
            ),
            scan.records,
        )

    return (
        _census_row(
            cohort,
            CENSUS_COVERAGE_COMPLETE,
            population=scan.population,
            open_phase_count=len(scan.records),
            unreadable_count=0,
        ),
        scan.records,
    )


def _census_worktree_cohort(worktrees_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build the cohort row for the two-level worktree-resident plan store.

    A phase-5+ plan directory is MOVED into its worktree (ADR-002), so this
    cohort's members live one level deeper than the other two: each worktree
    carries its own ``{wt}/.plan/local/plans``. A worktree with no such
    directory is skipped rather than counted — it holds no moved-in plan, which
    is an ordinary state and not a coverage gap.

    A worktree whose plan store exists but cannot be listed is different: it may
    hold any number of plans, none of which were seen. Such a store counts as
    ONE unreadable unit (its real member count is unknowable) and the cohort
    degrades to ``partial`` with the worktree named in the reason, so the
    shortfall is reported with its true shape instead of being counted as a
    single unreadable plan.

    A worktree entry the probe cannot examine at all is the same class of
    shortfall one step earlier — whether it is even a directory is unknown, so
    whether it holds a plan store is unknown too. It counts as one unreadable
    unit and is named, rather than skipped: a silent skip is what would let this
    cohort publish ``complete`` over a worktree nobody looked inside.
    """
    try:
        worktrees = sorted(worktrees_root.iterdir())
    except FileNotFoundError:
        return (
            _census_row(
                CENSUS_COHORT_WORKTREE,
                CENSUS_COVERAGE_COMPLETE,
                population=0,
                open_phase_count=0,
                unreadable_count=0,
            ),
            [],
        )
    except OSError:
        return (
            _census_row(
                CENSUS_COHORT_WORKTREE,
                CENSUS_COVERAGE_UNEVALUATED,
                reason=(
                    f'worktree container {worktrees_root} exists but could not be listed, '
                    'so no worktree plan store was enumerated'
                ),
            ),
            [],
        )

    population = 0
    unreadable = 0
    records: list[dict[str, Any]] = []
    unreadable_ids: list[str] = []
    unlistable_stores: list[str] = []
    unexaminable: list[str] = []

    for worktree_dir in worktrees:
        try:
            if not worktree_dir.is_dir():
                continue
        except OSError:
            # The entry could not be examined, so it may hold a plan store of any
            # size, none of it seen. Credited as one unreadable unit and named,
            # never silently skipped.
            unreadable += 1
            unexaminable.append(worktree_dir.name)
            continue
        scan = _scan_plan_container(worktree_dir / PLAN_DIR_NAME / 'local' / DIR_PLANS, CENSUS_COHORT_WORKTREE)
        if scan.state == _SCAN_ABSENT:
            continue
        if scan.state == _SCAN_UNLISTABLE:
            unreadable += 1
            unlistable_stores.append(worktree_dir.name)
            continue
        population += scan.population
        unreadable += scan.unreadable + len(scan.unexaminable_ids)
        records.extend(scan.records)
        unreadable_ids.extend(scan.unreadable_ids)
        # Qualified by the holding worktree: a bare entry name would be ambiguous
        # across worktrees, and this cohort's members live one level deeper.
        unexaminable.extend(f'{worktree_dir.name}/{name}' for name in scan.unexaminable_ids)

    if unreadable:
        reason_parts: list[str] = []
        if unreadable_ids:
            reason_parts.append(f'unreadable status.json in plan(s): {", ".join(unreadable_ids)}')
        if unlistable_stores:
            reason_parts.append(
                f'plan store could not be listed in worktree(s) (member count unknowable): '
                f'{", ".join(unlistable_stores)}'
            )
        if unexaminable:
            reason_parts.append(f'{_UNEXAMINABLE_REASON}: {", ".join(unexaminable)}')
        return (
            _census_row(
                CENSUS_COHORT_WORKTREE,
                CENSUS_COVERAGE_PARTIAL,
                population=population,
                open_phase_count=len(records),
                unreadable_count=unreadable,
                reason='; '.join(reason_parts),
            ),
            records,
        )

    return (
        _census_row(
            CENSUS_COHORT_WORKTREE,
            CENSUS_COVERAGE_COMPLETE,
            population=population,
            open_phase_count=len(records),
            unreadable_count=0,
        ),
        records,
    )


def cmd_census(args: argparse.Namespace) -> dict[str, Any]:  # args unused: the uniform cmd_* handler signature
    """Count every plan store separately from the main checkout, naming what it could not read.

    Store-wide and read-only: this verb declares no ``--plan-id`` because it
    asks about populations rather than about one plan, and it writes nothing.

    Returns ``status: success`` with ``anchor`` / ``anchor_path``, one
    ``cohorts[]`` row per store (live, worktree-resident, archived) and one
    ``open_phase_records[]`` row per plan still recording an ``in_progress``
    phase. Each cohort row publishes its own ``coverage`` and only the counts
    that coverage justifies — an ``unevaluated`` cohort carries no count keys at
    all, so "nothing is known about this store" can never be misread as "this
    store is empty".

    When the main anchor itself cannot be resolved the verb FAILS CLOSED with
    ``error: anchor_unresolved`` and NO cohort rows: without an anchor there is
    no store to count, and emitting three zeroed cohorts would report a
    thoroughly-surveyed empty machine.
    """
    try:
        anchor_base = resolve_main_anchored_path('')
    except (RuntimeError, OSError) as exc:
        return {
            'status': 'error',
            'error': 'anchor_unresolved',
            'message': (
                f'Could not resolve the main-anchored plan root, so no cohort was counted: {exc}. '
                'Run from inside the repository, or set PLAN_BASE_DIR to the store to survey.'
            ),
        }

    anchor = CENSUS_ANCHOR_OVERRIDE if base_dir_override_active() else CENSUS_ANCHOR_MAIN

    live_row, live_records = _census_single_container(CENSUS_COHORT_LIVE, anchor_base / DIR_PLANS)
    worktree_row, worktree_records = _census_worktree_cohort(anchor_base / CENSUS_WORKTREES_DIRNAME)
    archived_row, archived_records = _census_single_container(CENSUS_COHORT_ARCHIVED, anchor_base / DIR_ARCHIVED)

    return {
        'status': 'success',
        'anchor': anchor,
        'anchor_path': str(anchor_base),
        'cohorts': [live_row, worktree_row, archived_row],
        'open_phase_records': [*live_records, *worktree_records, *archived_records],
    }
