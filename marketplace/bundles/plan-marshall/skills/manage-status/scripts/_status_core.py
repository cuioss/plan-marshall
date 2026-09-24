#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Core functions for manage-status: TypedDicts, path resolution, read/write, and shared constants.
"""

import argparse
import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple, NotRequired, TypedDict, cast

from _locks_core import rmw_json
from _orchestrator_ledger import (
    LEDGER_ABSENT,
    LEDGER_LEGACY,
    LEDGER_OK,
    LEDGER_UNREADABLE,
    assemble_view,
    create_ledger,
    legacy_layout_error,
    set_metadata_field,
    write_anchor,
    write_header_field,
)
from _orchestrator_ledger import header_path as ledger_header_path
from _orchestrator_ledger import read_anchor as read_ledger_anchor
from _orchestrator_ledger import read_header as read_ledger_header
from constants import (
    DIR_ARCHIVED,
    DIR_PLANS,
    FILE_STATUS,
    PHASE_STATUS_DONE,
    PHASE_STATUS_IN_PROGRESS,
    VALID_PHASE_STATUSES,
)
from file_ops import (
    base_path,
    get_base_dir,
    get_executor_path,
    get_plan_dir,
    get_store_dir,
    get_worktree_root,
    now_utc_iso,
    output_toon,
    read_json,
)
from input_validation import require_valid_plan_id
from marketplace_paths import PLAN_DIR_NAME, resolve_main_anchored_path
from plan_logging import log_entry  # noqa: F401 - re-exported

logger = logging.getLogger(__name__)

# =============================================================================
# TypedDict Definitions
# =============================================================================


class PhaseData(TypedDict):
    """Type definition for phase data."""

    name: str
    status: str  # pending | in_progress | done


class TitleTokenRecord(TypedDict):
    """The structured ``status.title_token`` record.

    Specified once in ``platform-runtime/standards/terminal-title-architecture.md``
    § Channel Delivery Contract ruling (c); this TypedDict is its Python shape.
    """

    owner: str
    state: str
    set_at: str


class StatusData(TypedDict):
    """Type definition for status data structure."""

    title: str
    current_phase: str
    phases: list[PhaseData]
    metadata: NotRequired[dict[str, Any]]
    title_token: NotRequired[TitleTokenRecord]
    created: str
    updated: str


# Valid title-token states — the two lock-coordination states (lock-waiting /
# lock-owned) plus the orchestration-busy state (build-busy). The token is a
# field-only record written into status.json by the ``title-token set`` verb;
# manage-status performs NO rendering. The composition (glyph vocabulary +
# ``{icon} {body}`` assembly) lives in ``manage-terminal-title`` — manage-status
# only persists the state record so the per-target renderer can read it.
# build-busy is written/cleared by the build-hook render assist (not the lock
# machinery) to surface a 🔨 build symbol for the duration of a long-running
# orchestration Bash call; manage-terminal-title renders it as a token-keyed
# icon-slot override, not a glyph.
TITLE_TOKEN_BUILD_BUSY = 'build-busy'
TITLE_TOKEN_STATES = frozenset({'lock-waiting', 'lock-owned', TITLE_TOKEN_BUILD_BUSY})

# Owner vocabulary — the writer that set the token. ``build-hook`` is the
# PreToolUse:Bash / PostToolUse:Bash render assist that brackets a build window
# (Claude target; the hook-event bracket is specified in
# ``platform-runtime/standards/terminal-title-architecture.md`` § Channel
# Delivery Contract ruling (c)),
# ``merge-lock`` is manage-locks/merge_lock.py, and ``cli`` is an explicit
# ``manage-status title-token set`` invocation from the orchestration layer.
TITLE_TOKEN_OWNER_BUILD_HOOK = 'build-hook'
TITLE_TOKEN_OWNER_MERGE_LOCK = 'merge-lock'
TITLE_TOKEN_OWNER_CLI = 'cli'
TITLE_TOKEN_OWNERS = frozenset({TITLE_TOKEN_OWNER_BUILD_HOOK, TITLE_TOKEN_OWNER_MERGE_LOCK, TITLE_TOKEN_OWNER_CLI})

# Aged-token staleness threshold, in seconds. Derived, not arbitrary: it
# comfortably exceeds the longest architecture-resolved build ceiling in this
# project (~1926 s for an unscoped whole-tree verify), so a live bracket can
# never age out mid-call, while any process death that strands a token
# self-heals within the hour without operator action.
TITLE_TOKEN_STALE_AFTER_SECONDS = 3600


# =============================================================================
# Core Functions
# =============================================================================


def get_status_path(plan_id: str) -> Path:
    """Get the status.json file path."""
    return get_plan_dir(plan_id) / FILE_STATUS


def read_status(plan_id: str) -> dict[Any, Any]:
    """Read status.json for a plan."""
    return cast(dict[Any, Any], read_json(get_status_path(plan_id)))


def write_status(plan_id: str, status: dict[Any, Any], *, preserve_title_token: bool = True) -> None:
    """Write status.json for a plan inside the serialized ``rmw_json`` critical section.

    Every caller commits a WHOLE document assembled from a snapshot read taken
    before its own mutation. ``title_token`` is the one field four independent
    writers (the build-hook render assist, merge_lock's two lock surfaces, and
    merge_lock's clear) mutate from separate executor subprocesses, so a plain
    full-document overwrite carries a last-writer-wins window: a ``title-token
    set`` committing between a caller's snapshot read and its write is silently
    clobbered by the stale snapshot value. Committing here closes that window on
    both counts — the O_EXCL guard serializes against ``cmd_title_token``'s own
    critical section (same guard file, because both resolve the path through
    ``get_status_path``), and the ``title_token`` carried into the committed
    document is the one read INSIDE the guard rather than the caller's snapshot.

    Guarding at this single seam rather than at individual phase-write call
    sites is deliberate: every full-document writer in this skill shares the
    hazard, so a per-call-site guard would be one call site short by
    construction the moment a new writer is added.

    Args:
        plan_id: Plan whose ``status.json`` is written.
        status: The whole document to commit. Mutated in place with the
            refreshed ``updated`` stamp and the live ``title_token`` so the
            caller's in-memory view matches what was committed.
        preserve_title_token: When False the caller's own ``title_token`` value
            — including its absence — wins over the live record. ``cmd_archive``
            is the sole intended user: its unconditional full clear is a
            deliberate design decision (an archived plan holds no live
            coordination state worth arbitrating over), not an instance of the
            race above.
    """

    def _apply(current: dict[str, Any]) -> dict[str, Any]:
        if preserve_title_token:
            live = current.get('title_token')
            if live is None:
                status.pop('title_token', None)
            else:
                status['title_token'] = live
        status['updated'] = now_utc_iso()
        return cast(dict[str, Any], status)

    rmw_json(get_status_path(plan_id), _apply)


def normalize_metadata(status: dict[Any, Any]) -> dict[Any, Any]:
    """Return ``status['metadata']`` as a dict, normalizing an explicit JSON
    ``null`` (or any other non-dict value) to an empty dict in place.

    ``dict.get(key, default)`` / ``dict.setdefault`` only apply their default
    when the key is ABSENT — an explicit JSON ``null`` for ``status['metadata']``
    flows through unchanged and crashes a downstream ``.get()``/item-assignment
    on ``None``. Callers that need a guaranteed-dict metadata view use this
    helper instead of duplicating the isinstance guard; the correction is
    written back onto ``status`` so later reads/writes in the same call see it.
    """
    metadata = status.get('metadata')
    if not isinstance(metadata, dict):
        metadata = {}
        status['metadata'] = metadata
    return metadata


# =============================================================================
# Phase closure (the archive post-condition)
# =============================================================================

#: Phase statuses a closing write MUST NOT touch, derived by set DIFFERENCE from the
#: declared vocabulary rather than spelled as the literal ``{'pending'}``. Today the
#: difference is exactly ``{pending}``, but deriving it means a status added to
#: ``VALID_PHASE_STATUSES`` later is untouched by default — it has to be named
#: explicitly here to become closable, rather than silently joining the set a closure
#: writes ``done`` onto. ``VALID_PHASE_STATUSES`` is a TUPLE, so the difference is taken
#: over a ``frozenset`` of it.
UNTOUCHED_PHASE_STATUSES = frozenset(VALID_PHASE_STATUSES) - {PHASE_STATUS_IN_PROGRESS, PHASE_STATUS_DONE}


@dataclass(frozen=True)
class OpenPhaseScan:
    """What one look at a status document's ``phases`` established — and what it did not.

    Two facts, carried together and never collapsed into one another:

    - :attr:`phases` — every phase record the scan POSITIVELY established as
      ``in_progress``. These are the LIVE dicts out of ``status['phases']``, not
      copies, so ``cmd_archive`` closes a phase by mutating one in place.
    - :attr:`unexaminable` — one human-readable note per part of the structure the
      scan could NOT classify. Empty is the ordinary case; non-empty means
      :attr:`phases` is what was found rather than what is there.

    An empty :attr:`phases` therefore no longer answers two different questions with
    the same value. ``examinable=True`` with no phases is *"looked, nothing open"*;
    ``examinable=False`` with no phases is *"could not look"*. Collapsing those into a
    bare ``[]`` is exactly how an unexaminable record came to be archived as
    ``complete`` and published as a clean ``open_phase_count: 0``.

    ⛔ :meth:`__bool__` RAISES rather than answering. Both consumers previously wrote
    ``if not in_progress_phases(status)``, and there is no truthiness rule this type
    could adopt that answers that expression correctly for BOTH states — a falsy
    unexaminable result reinstates the original defect at the first such guard, and a
    truthy one silently inverts the completion gate. Raising turns the stale idiom
    into a loud ``TypeError`` at the call site instead of a false claim in a permanent
    record. Read :attr:`examinable` and :attr:`phases`; never the object itself.
    """

    phases: tuple[dict[str, Any], ...]
    unexaminable: tuple[str, ...] = ()

    @property
    def examinable(self) -> bool:
        """Whether the ``phases`` structure was read IN FULL.

        DERIVED from :attr:`unexaminable` rather than stored beside it, so the flag
        and the notes behind it cannot drift into disagreeing about the same scan.
        """
        return not self.unexaminable

    def __bool__(self) -> bool:
        raise TypeError(
            'OpenPhaseScan has no truth value. Read .examinable to learn whether the '
            'phases structure could be read in full, and .phases for the open phases '
            'that were established: `if not scan:` cannot tell "nothing is open" from '
            '"the phases could not be examined", which is the conflation this type exists '
            'to remove.'
        )


def in_progress_phases(status: dict[Any, Any]) -> OpenPhaseScan:
    """Report EVERY phase recorded as ``in_progress``, and whatever could not be read.

    ``in_progress`` is the only CLOSABLE status: it names a phase that really did
    start, so recording it as ``done`` at archive time closes a genuine record. A
    ``pending`` phase never ran, so writing ``done`` onto it would fabricate a fresh
    false record — which is why the statuses this function does not report are held in
    :data:`UNTOUCHED_PHASE_STATUSES`.

    The single predicate for "which phases are still open", consumed by
    ``_cmd_lifecycle.cmd_archive`` (which mutates the reported records in place) and by
    the ``census`` verb's open-phase reporting. Naming it once is what keeps the
    archive's closure set and the census's reported population from drifting into two
    different answers to the same question.

    Malformed input is REPORTED, never absorbed. Four shapes cannot be classified and
    each lands in :attr:`OpenPhaseScan.unexaminable`:

    - ``phases`` absent, or present but not a list;
    - a row that is not a mapping, so it carries no readable status;
    - a row whose ``name`` is missing, empty, or not a string — the row cannot be
      identified, so neither the archive (which closes phases BY name) nor the census
      (which reports the names) can act on it, and the projection would otherwise
      synthesise ``''`` as though it were a phase name;
    - a row whose ``status`` is outside the declared :data:`VALID_PHASE_STATUSES`
      vocabulary — it may or may not name a running phase, and guessing either way is
      a claim the data does not support.

    The name check applies to EVERY row, not only the ``in_progress`` ones, exactly as
    the vocabulary check already does: ``examinable`` states that the structure was read
    in full, and a row nobody can identify is a part of it that was not.

    The scan still returns whatever it DID establish alongside those notes, so a caller
    holding a structurally odd record can still act on the phases that are readable.
    What it may no longer do is mistake the shortfall for a clean empty set — see
    :class:`OpenPhaseScan`.
    """
    phases = status.get('phases')
    if not isinstance(phases, list):
        return OpenPhaseScan((), (f'phases is {type(phases).__name__}, not a list',))

    open_phases: list[dict[str, Any]] = []
    unexaminable: list[str] = []
    for index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            unexaminable.append(f'phases[{index}] is {type(phase).__name__}, not a phase record')
            continue
        # Checked BEFORE the status, so an unidentifiable row is reported as such rather
        # than being classified open on the strength of a status attached to no name.
        # One note per row: the first failure ends the row's classification.
        name = phase.get('name')
        if not isinstance(name, str) or not name:
            unexaminable.append(f'phases[{index}] carries name {name!r}, not a non-empty string')
            continue
        phase_status = phase.get('status')
        if phase_status not in VALID_PHASE_STATUSES:
            unexaminable.append(f'phases[{index}] carries status {phase_status!r}, outside the declared vocabulary')
            continue
        if phase_status == PHASE_STATUS_IN_PROGRESS:
            open_phases.append(phase)
    return OpenPhaseScan(tuple(open_phases), tuple(unexaminable))


# =============================================================================
# Orchestrator store (kind=orchestrator)
# =============================================================================
#
# The orchestrator store holds each epic's ledger under
# ``.plan/orchestrator/{slug}/`` — resolved via ``get_store_dir``, which
# composes onto the git-tracked config tier, so an epic ledger is versioned
# with the repository. The ledger is split into per-concern files — the header
# ``status.json``, ``resume_anchor.md``, and one ``queue/{PLAN-ID}.json`` per
# plan row — and ``_orchestrator_ledger`` is the single owner of that layout:
# every verb below reads and writes through it and composes no ledger path of
# its own. The header is deliberately lean — a three-value ``phase`` field
# instead of the plan phase-transition machinery, and no ``updated`` stamp:
#
#   status.json       {kind, title, phase (init|orchestrating|closed),
#                      workstreams[], metadata, created}
#   resume_anchor.md  the anchor text
#   queue/{ID}.json   {id, slug, workstream, status, plan_marshall_plan_id,
#                      pr, landing, seq}
#
# A ``status.json`` that still carries ``plans`` or ``resume_anchor`` is the
# monolithic layout; every verb refuses it with ``legacy_layout`` and writes
# nothing. See ``standards/status-lifecycle.md`` for the schema contract.

ORCHESTRATOR_STORE = 'orchestrator'
ORCHESTRATOR_PHASES = ('init', 'orchestrating', 'closed')
ORCHESTRATOR_LIST_FIELDS = frozenset({'workstreams'})
ORCHESTRATOR_UPDATABLE_FIELDS = frozenset({'phase', 'resume_anchor'}) | ORCHESTRATOR_LIST_FIELDS


def get_orchestrator_root(entry_id: str, allow_archived: bool = False) -> Path:
    """Resolve an epic's ledger root under the orchestrator store.

    ``allow_archived`` threads into :func:`file_ops.get_store_dir`'s
    read-fallback: when ``True`` and the active tree is absent, the archived
    home is resolved (when it exists). READ verbs opt in; WRITE verbs keep the
    default ``False`` so an archived epic is never mutated at the active path.
    """
    return cast(Path, get_store_dir(ORCHESTRATOR_STORE, entry_id, allow_archived=allow_archived))


def _orchestrator_error(plan_id: str, error: str, message: str, **extra: Any) -> dict[str, Any]:
    """Build the orchestrator-store TOON error envelope."""
    result: dict[str, Any] = {
        'status': 'error',
        'plan_id': plan_id,
        'store': ORCHESTRATOR_STORE,
        'error': error,
        'message': message,
    }
    result.update(extra)
    return result


def _probe_orchestrator_header(
    args: argparse.Namespace, allow_archived: bool = False
) -> tuple[Path, dict[str, Any] | None]:
    """Validate the slug and probe the epic header, returning ``(root, refusal)``.

    ``refusal`` is ``None`` when the header reads as a per-concern header, and
    otherwise the error envelope the verb returns unchanged:

    * ``file_not_found`` — no header at the root. With ``allow_archived=False``
      (every WRITE verb) an archived-only epic lands here too, so it is refused
      rather than resurrected at the active path.
    * ``legacy_layout`` — the header still carries the queue or the anchor; the
      envelope names ``orchestrator migrate-layout``.
    * ``header_unreadable`` — something occupies the header path but does not
      read as a JSON object. Reported as its own state, never as an absent one.
    """
    require_valid_plan_id(args)
    root = get_orchestrator_root(args.plan_id, allow_archived=allow_archived)
    state, _header, detail = read_ledger_header(root)
    if state == LEDGER_ABSENT:
        return root, _orchestrator_error(args.plan_id, 'file_not_found', 'status.json not found in orchestrator store')
    if state == LEDGER_LEGACY:
        return root, _orchestrator_error(args.plan_id, **legacy_layout_error(args.plan_id))
    if state == LEDGER_UNREADABLE:
        return root, _orchestrator_error(args.plan_id, 'header_unreadable', detail)
    return root, None


def cmd_orchestrator_create(args: argparse.Namespace) -> dict[str, Any] | None:
    """Create a ``kind=orchestrator`` ledger: the header and an empty anchor.

    ``--force`` rewrites the header and the anchor. The queue is never touched by
    ``create``: a new ledger has no ``queue/`` directory, which every reader takes
    as a measured empty queue.

    A header still in the monolithic layout is refused with ``legacy_layout`` —
    ``--force`` included — and nothing is written: overwriting it would drop the
    ``plans[]`` queue and the ``resume_anchor`` it carries, which only
    ``orchestrator migrate-layout`` converts without loss.
    """
    require_valid_plan_id(args)
    root = get_orchestrator_root(args.plan_id)
    state, _header, _detail = read_ledger_header(root)
    if state == LEDGER_LEGACY:
        return _orchestrator_error(args.plan_id, **legacy_layout_error(args.plan_id))
    if ledger_header_path(root).exists() and not args.force:
        return _orchestrator_error(
            args.plan_id, 'already_exists', 'status.json already exists (use --force to overwrite)'
        )
    header = create_ledger(root, args.title, now_utc_iso())
    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'store': ORCHESTRATOR_STORE,
        'kind': 'orchestrator',
        'phase': header['phase'],
        'file': str(ledger_header_path(root)),
    }


def cmd_orchestrator_read(args: argparse.Namespace) -> dict[str, Any] | None:
    """Read an epic ledger as one assembled document.

    ``plan`` carries the assembled view — the header fields, ``plans`` ordered by
    ``(seq, id)``, and ``resume_anchor``. A row file that could not be read is
    listed under ``unreadable_rows`` (its file and the reason) and is absent from
    ``plans``: nothing is known about it, and naming it keeps that absence from
    reading as "no such row".
    """
    root, refusal = _probe_orchestrator_header(args, allow_archived=True)
    if refusal is not None:
        return refusal
    view = assemble_view(root)
    if view.state != LEDGER_OK:
        return _orchestrator_error(args.plan_id, 'ledger_unreadable', view.detail)
    result: dict[str, Any] = {
        'status': 'success',
        'plan_id': args.plan_id,
        'store': ORCHESTRATOR_STORE,
        'plan': view.document,
    }
    if view.unreadable_rows:
        result['unreadable_rows'] = [dict(row) for row in view.unreadable_rows]
    return result


def cmd_orchestrator_update_field(args: argparse.Namespace) -> dict[str, Any] | None:
    """Update one field of an epic ledger.

    ``phase`` is validated against :data:`ORCHESTRATOR_PHASES`; ``workstreams``
    takes a JSON-array ``--value``; both are header fields. ``resume_anchor``
    stores the value verbatim in the anchor file. The queue is NOT a field: a
    whole-queue rewrite cannot exist over per-row files, so the plan queue is
    written only through ``orchestrator queue`` and ``plans`` is refused here
    with ``invalid_field``.
    """
    field = args.field
    if field not in ORCHESTRATOR_UPDATABLE_FIELDS:
        require_valid_plan_id(args)
        return _orchestrator_error(
            args.plan_id,
            'invalid_field',
            f'--field must be one of {sorted(ORCHESTRATOR_UPDATABLE_FIELDS)}, got: {field}. '
            'Nothing was written. The plan queue is written only through `orchestrator queue`.',
        )
    root, refusal = _probe_orchestrator_header(args)
    if refusal is not None:
        return refusal
    value: Any = args.value
    if field == 'phase' and value not in ORCHESTRATOR_PHASES:
        return _orchestrator_error(
            args.plan_id,
            'invalid_value',
            f'--value for phase must be one of {list(ORCHESTRATOR_PHASES)}, got: {value}',
        )
    if field in ORCHESTRATOR_LIST_FIELDS:
        try:
            value = json.loads(value)
        except ValueError:
            value = None
        if not isinstance(value, list):
            return _orchestrator_error(args.plan_id, 'invalid_value', f'--value for {field} must be a JSON array')
    outcome: dict[str, Any]
    if field == 'resume_anchor':
        previous_anchor, _ = read_ledger_anchor(root)
        write_anchor(root, value)
        outcome = {'previous': previous_anchor or None}
    else:
        # The header write runs inside the header's own O_EXCL-guarded
        # read-modify-write, so a concurrent session setting a DIFFERENT header
        # field is not clobbered by a last-writer-wins over a stale read.
        outcome = write_header_field(root, field, value)
        if outcome.get('legacy'):
            return _orchestrator_error(args.plan_id, **legacy_layout_error(args.plan_id))
    result: dict[str, Any] = {
        'status': 'success',
        'plan_id': args.plan_id,
        'store': ORCHESTRATOR_STORE,
        'field': field,
        'value': value,
    }
    if outcome.get('previous') is not None:
        result['previous_value'] = outcome['previous']
    return result


def cmd_orchestrator_metadata(args: argparse.Namespace) -> dict[str, Any] | None:
    """Get or set a metadata field of a ``kind=orchestrator`` status.json."""
    # Reject the mutually-exclusive combination BEFORE resolving the store or
    # computing allow_archived. Otherwise `allow_archived=bool(args.get)` is
    # True for a combined --get --set call, so the archived read-fallback
    # resolves the store and control falls into the --set write branch, which
    # rmw_json's against the STRICT active-path status.json — silently
    # resurrecting/mutating the active orchestrator tree for an archived-only
    # epic instead of refusing the malformed request.
    if args.get and args.set:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'store': ORCHESTRATOR_STORE,
            'error': 'wrong_parameters',
            'message': '--get and --set are mutually exclusive; supply exactly one',
        }
    # ``--append`` is attached to the SHARED ``metadata`` subparser, so it is
    # accepted here by the argparse surface and implemented only by the plans
    # store. Refuse it explicitly rather than ignoring it: an ignored --append
    # falls through to the --set branch below and OVERWRITES, reporting
    # ``status: success`` while destroying the value the caller meant to extend
    # — the precise defect the flag was added to eliminate, reproduced on the
    # store that never implemented it. The orchestrator store's list field
    # (``workstreams``) is served by ``update-field`` (JSON-array ``--value``);
    # see manage-status SKILL.md § Canonical invocations.
    if getattr(args, 'append', False):
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'store': ORCHESTRATOR_STORE,
            'error': 'append_unsupported_for_store',
            'message': (
                '--append is implemented for the plans store only. The orchestrator '
                "store's list fields are set through `update-field` with a JSON-array "
                '--value. Nothing was written.'
            ),
        }
    # The --get read-path resolves an archived epic transparently; the --set
    # write-path stays strict so an archived-only epic refuses with
    # file_not_found (no resurrection at the active path).
    root, refusal = _probe_orchestrator_header(args, allow_archived=bool(args.get))
    if refusal is not None:
        return refusal
    if args.set:
        if args.value is None:
            return _orchestrator_error(
                args.plan_id, 'wrong_parameters', '--set requires --value; refusing to store a null metadata value'
            )
        # The metadata write runs inside the header's O_EXCL-guarded
        # read-modify-write and touches only header['metadata'][field], so a
        # concurrent session setting a different metadata entry (or a different
        # header field) is not lost to a last-writer-wins over a stale read.
        field = args.field
        value = args.value
        outcome = set_metadata_field(root, field, value)
        if outcome.get('legacy'):
            return _orchestrator_error(args.plan_id, **legacy_layout_error(args.plan_id))
        result: dict[str, Any] = {
            'status': 'success',
            'plan_id': args.plan_id,
            'store': ORCHESTRATOR_STORE,
            'field': field,
            'value': value,
        }
        if outcome.get('previous') is not None:
            result['previous_value'] = outcome['previous']
        return result
    if args.get:
        _state, header, _detail = read_ledger_header(root)
        metadata = header.get('metadata', {})
        if not isinstance(metadata, dict):
            metadata = {}
        value = metadata.get(args.field)
        if value is None:
            return {
                'status': 'not_found',
                'plan_id': args.plan_id,
                'store': ORCHESTRATOR_STORE,
                'field': args.field,
                'message': f"Metadata field '{args.field}' not found",
                'available_fields': list(metadata.keys()),
            }
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'store': ORCHESTRATOR_STORE,
            'field': args.field,
            'value': value,
        }
    return {
        'status': 'error',
        'plan_id': args.plan_id,
        'store': ORCHESTRATOR_STORE,
        'error': 'missing_operation',
        'message': 'Either --get or --set is required',
    }


# =============================================================================
# Persisted-title-state-write drive seam (best-effort, executor channel)
# =============================================================================
#
# manage-status is the STATE layer: it writes status.json and composes/emits
# NOTHING itself. On every persisted ``current_phase`` write the state layer
# fires two best-effort, fire-and-forget delegations to ``platform-runtime`` —
# a bind (session→plan, last-driven-wins) and a state settle (icon-optional
# ``push-title-token``) — exactly mirroring how ``manage-locks/merge_lock.py``
# delegates its title-token surface. Both are invoked through the executor as a
# subprocess (the established merge_lock channel, not a fragile file-path import
# across the multi-module platform-runtime layout) and fully swallow every
# failure, so a delegation error NEVER alters the status-write outcome or exit
# code. The single shared ``_surface_drive`` helper is the ONE home every phase
# writer (``cmd_create`` / ``cmd_transition`` / ``cmd_set_phase`` /
# ``cmd_archive``) shares.
#
# Neither delegation DELIVERS a title. The hook render channel is event-driven,
# so a writer discharges its delivery obligation by settling the state the NEXT
# render event reads — which is also why ``cmd_archive`` must keep the session
# binding alive rather than releasing it: that binding is the pending render's
# only route back to the archived plan.

_PLATFORM_RUNTIME_NOTATION = 'plan-marshall:platform-runtime:platform_runtime'


def _run_executor(notation: str, *cli_args: str) -> 'subprocess.CompletedProcess[str] | None':
    """Best-effort: invoke ``{notation}`` through the executor as a subprocess.

    Fire-and-forget — any failure (executor missing, non-zero exit, OSError) is
    swallowed at DEBUG. The drive seam is a display affordance and MUST NOT
    change the status-write outcome. Mirrors ``merge_lock._run_executor``'s
    best-effort contract (the established D6 executor channel).

    The executor is resolved and existence-checked BEFORE the spawn: when the
    plan root is unresolvable or no ``execute-script.py`` is on disk (an
    isolated test fixture, a pre-bootstrap window), there is nothing to delegate
    to, so the call returns without launching a subprocess. Skipping the spawn
    keeps the seam a true no-op wherever the executor is absent instead of
    launching a Python process that would only fail to find the script.

    Returns the :class:`subprocess.CompletedProcess` when the delegate actually
    ran, or ``None`` when the spawn was skipped or failed. The completed process
    lets a caller inspect the delegate's own TOON reply (see
    :func:`_drive_repaint`); callers that need nothing from the reply simply
    ignore the return value.
    """
    try:
        executor = get_executor_path()
    except RuntimeError as exc:
        logger.debug('drive-seam %s skipped (no plan root): %s', notation, exc)
        return None
    if not executor.is_file():
        logger.debug('drive-seam %s skipped (executor absent at %s)', notation, executor)
        return None
    cmd = [sys.executable, str(executor), notation, *cli_args]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        logger.debug('drive-seam %s failed: %s', notation, exc)
        return None


def _drive_bind(plan_id: str) -> None:
    """Best-effort ``session bind --plan-id {id}`` (last-driven-wins; Defect 2)."""
    _run_executor(_PLATFORM_RUNTIME_NOTATION, 'session', 'bind', '--plan-id', plan_id)


def _drive_repaint(plan_id: str) -> None:
    """Best-effort ``session push-title-token --plan-id {id}`` (no icon).

    The delegate runs with no ``--icon``, settling the freshly composed title
    state with its default active icon so the NEXT render event paints the new
    phase instead of the last-rendered one.

    The seam reports no delivery outcome, because it performs no delivery: the
    hook render channel is event-driven, so the repaint this call enables happens
    at the next render event, not here. There is consequently no non-delivery to
    surface — a reply the delegate can only answer with ``no_title_state`` (the
    ordinary "nothing to settle" case) stays at DEBUG. Never alters the command's
    status or exit code.
    """
    _run_executor(_PLATFORM_RUNTIME_NOTATION, 'session', 'push-title-token', '--plan-id', plan_id)


def _surface_drive(plan_id: str) -> None:
    """Best-effort: fire one bind + one repaint after a persisted phase-state write.

    Called immediately AFTER ``write_status`` by the three ``current_phase``
    writers (``cmd_create`` seed / ``cmd_transition`` advance / ``cmd_set_phase``).
    The single shared home so both call sites share it rather than a per-caller
    convention. Fully exception-swallowing: a subprocess/delegation failure never
    changes the command's status or exit code.
    """
    try:
        _drive_bind(plan_id)
        _drive_repaint(plan_id)
    except Exception as exc:  # drive seam is best-effort
        logger.debug('drive-seam surface for %s failed: %s', plan_id, exc)


def _parse_set_at(set_at: Any) -> datetime | None:
    """Parse a ``set_at`` field into an aware UTC datetime, or ``None``.

    Tolerates every malformed shape (absent, non-string, unparseable) by
    returning ``None`` — an unreadable timestamp is treated as "age unknown"
    by :func:`title_token_is_stale`, never as an exception.
    """
    if not isinstance(set_at, str) or not set_at:
        return None
    try:
        parsed = datetime.fromisoformat(set_at.replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def title_token_is_stale(record: Any, *, now: datetime | None = None) -> bool:
    """Age-based staleness predicate for a ``title_token`` record.

    A record is stale when it is structurally unusable (not a mapping, or
    carrying a ``state`` outside :data:`TITLE_TOKEN_STATES`), when its
    ``set_at`` cannot be parsed, or when its ``set_at`` is older than
    :data:`TITLE_TOKEN_STALE_AFTER_SECONDS`. A stale token may be cleared or
    replaced by ANY writer, which is what lets a stranded token self-heal
    without operator action.

    The predicate is applied on every READ of the token rather than swept at a
    phase boundary: a phase-boundary sweep only fires when a phase happens to
    change, so a stranded token could outlive it indefinitely.
    """
    if not isinstance(record, dict):
        return True
    if record.get('state') not in TITLE_TOKEN_STATES:
        return True
    parsed = _parse_set_at(record.get('set_at'))
    if parsed is None:
        return True
    reference = now if now is not None else datetime.now(UTC)
    return (reference - parsed).total_seconds() > TITLE_TOKEN_STALE_AFTER_SECONDS


def read_title_token(status: dict[Any, Any], *, now: datetime | None = None) -> dict[str, Any] | None:
    """Return the live ``title_token`` record from ``status``, or ``None``.

    The single read-side accessor: it applies :func:`title_token_is_stale` so
    every consumer sees a stale token as absent. It does NOT mutate ``status``
    — staleness is a read-side property, so no writer has to sweep.
    """
    record = status.get('title_token')
    if title_token_is_stale(record, now=now):
        return None
    return cast(dict[str, Any], record)


# Phase routing maps phase names to skills (for route command).
# Note: This is a fallback mapping. The authoritative source is
# manage-config's skill_domains.system.workflow_skills in marshal.json.
# When marshal.json is initialized, resolve-workflow-skill should be
# preferred over this static mapping.
PHASE_ROUTING = {
    '1-init': ('plan-init', 'Initialize plan structure'),
    '2-refine': ('request-refine', 'Clarify request until confident'),
    '3-outline': ('solution-outline', 'Create solution outline with deliverables'),
    '4-plan': ('task-plan', 'Create tasks from deliverables'),
    '5-execute': ('plan-execute', 'Execute implementation tasks'),
    '6-finalize': ('plan-finalize', 'Finalize with commit/PR'),
}


def get_plans_dir() -> Path:
    """Get the plans directory."""
    return cast(Path, base_path(DIR_PLANS))


def get_archive_dir() -> Path:
    """Get the archived plans directory."""
    return cast(Path, base_path(DIR_ARCHIVED))


def _try_read_status_json(plan_dir: Path) -> dict[Any, Any] | None:
    """Try to read status.json from a plan directory."""
    status_file = plan_dir / FILE_STATUS
    if status_file.exists():
        try:
            return cast(dict[Any, Any], json.loads(status_file.read_text(encoding='utf-8')))
        except (ValueError, OSError):
            return None
    return None


# =============================================================================
# Plan-status resolution (the read-verb sibling-worktree fallback)
# =============================================================================
#
# Under ADR-002 a phase-5+ plan's directory MOVES into its own worktree, so it is
# absent from every OTHER checkout by design. A gate that answers that absence
# with a bare ``file_not_found`` is structurally incapable of returning presence
# for such a plan, so its refusal is evidence of nothing — and reading it as "the
# plan is dead" has already destroyed live coordination state.
#
# The fallback below is a copy of the shipped resolution shape in
# ``manage-findings/_findings_store_state.py``: consult ``git-workflow
# locate-plan-checkout`` (never a raw plans-directory walk) and adopt the plan
# the holding checkout carries. A second spelling of that contract is how the two
# surfaces drift apart later.

#: Where a plan's ``status.json`` was read from. The vocabulary is
#: ``locate-plan-checkout``'s own ``location`` field, quoted rather than
#: re-invented so the consulting surface and the consulted verb name the same
#: three states.
PLAN_LOCATION_CURRENT = 'current'
PLAN_LOCATION_WORKTREE = 'worktree'
PLAN_LOCATION_NOT_FOUND = 'not_found'
PLAN_LOCATIONS = frozenset({PLAN_LOCATION_CURRENT, PLAN_LOCATION_WORKTREE, PLAN_LOCATION_NOT_FOUND})

#: The closed vocabulary a refusal publishes as ``plan_visibility``.
#:
#: - ``absent_anywhere`` — the widened resolution ran, the locator RENDERED a
#:   verdict, and the enumeration scope was ``main`` (so it observes main's plans
#:   AND every sibling worktree). Only this conjunction substantiates absence.
#: - ``not_visible_from_this_scope`` — everything else: a strict gate that never
#:   consulted the locator, a locator that could not answer, or a scope that is
#:   structurally blind to sibling worktrees. The plan was not found HERE, which
#:   is not evidence that it does not exist.
PLAN_ABSENT_ANYWHERE = 'absent_anywhere'
PLAN_NOT_VISIBLE_FROM_SCOPE = 'not_visible_from_this_scope'
PLAN_VISIBILITY_STATES = frozenset({PLAN_ABSENT_ANYWHERE, PLAN_NOT_VISIBLE_FROM_SCOPE})

#: The closed vocabulary :func:`_resolution_scope` reports, shared verbatim with
#: ``cmd_list``'s first-class ``scope`` field so the enumeration verb and the
#: single-plan read answer "how wide was the look" the same way.
RESOLUTION_SCOPE_MAIN = 'main'
RESOLUTION_SCOPE_WORKTREE_LOCAL = 'worktree_local'
RESOLUTION_SCOPE_UNKNOWN = 'unknown'
RESOLUTION_SCOPES = frozenset({RESOLUTION_SCOPE_MAIN, RESOLUTION_SCOPE_WORKTREE_LOCAL, RESOLUTION_SCOPE_UNKNOWN})

#: Wall-clock budget for the ``locate-plan-checkout`` consult (seconds). Matches
#: the sibling budget in ``_findings_store_state``, which consults the same verb.
_LOCATE_TIMEOUT_SECONDS = 20


class _CheckoutLookup(NamedTuple):
    """What one ``locate-plan-checkout`` consult established.

    ``answered`` is the discriminator and MUST be read first. It is ``True`` only
    when the locator rendered a verdict — including the verdict "no checkout holds
    this plan". Every degraded outcome (no resolvable executor, a non-zero exit, an
    unparsable payload, a ``location`` outside :data:`PLAN_LOCATIONS`) is ``False``:
    nothing was established, so the caller must not upgrade the miss into a claim
    about every checkout.

    ``worktree_path`` is non-``None`` only for a ``worktree`` verdict.
    """

    answered: bool
    worktree_path: Path | None


#: The locator could not be consulted, or could not be understood. Nothing known.
_LOOKUP_UNANSWERED = _CheckoutLookup(False, None)
#: The locator answered, and no checkout other than this one holds the plan.
_LOOKUP_NO_HOLDER = _CheckoutLookup(True, None)


def _locate_plan_checkout(plan_id: str) -> _CheckoutLookup:
    """Ask ``git-workflow locate-plan-checkout`` which checkout holds ``plan_id``.

    Routes through the EXISTING verb rather than re-deriving a locator here: it
    already layers the canonical ``manage-status`` channel over the structural
    ``get_worktree_root() / {plan_id}`` probe, which is precisely the
    moved-in-from-main case this fallback exists to resolve. A raw
    plans-directory walk is the re-implementation that caused the incident behind
    this deliverable and is never the answer.

    One cheap gate runs before the subprocess: every locatable worktree is
    materialized at ``get_worktree_root() / {plan_id}`` — the layout
    ``worktree-create`` writes and the exact path the verb's own structural probe
    reads — so an absent slot means the verb has nothing to find and its answer is
    known in advance. The gate is therefore an ANSWER (``_LOOKUP_NO_HOLDER``),
    never a degraded consult, because it cannot be narrower than the verb it gates.

    ⛔ The consult spawns ``git-workflow``, which spawns ``manage-status
    worktree-path``. That verb resolves through the STRICT gate and never opts
    into this fallback, which is what keeps the consult one level deep. Any verb
    reachable from the locator's own call path MUST stay strict.
    """
    try:
        slot = get_worktree_root() / plan_id
        if not slot.is_dir():
            return _LOOKUP_NO_HOLDER
    except (RuntimeError, OSError):
        # Outside a git repo, or the slot probe itself could not complete: no
        # worktree root was examined, so nothing is known.
        return _LOOKUP_UNANSWERED
    return _run_locator(plan_id)


def _run_locator(plan_id: str) -> _CheckoutLookup:
    """Spawn the ``locate-plan-checkout`` consult and read its verdict.

    Held apart from :func:`_locate_plan_checkout` so the process hop is one named
    seam: the gate, the foreign-store join and the payload read are all exercisable
    against a real worktree without a subprocess standing between the test and the
    behaviour it is checking.
    """
    try:
        executor = get_executor_path()
    except RuntimeError:
        return _LOOKUP_UNANSWERED
    if not executor.is_file():
        return _LOOKUP_UNANSWERED

    try:
        completed = subprocess.run(  # fixed argv, no shell, no caller-supplied executable
            [
                sys.executable,
                str(executor),
                'plan-marshall:workflow-integration-git:git-workflow',
                'locate-plan-checkout',
                '--plan-id',
                plan_id,
            ],
            capture_output=True,
            text=True,
            timeout=_LOCATE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return _LOOKUP_UNANSWERED
    if completed.returncode != 0:
        return _LOOKUP_UNANSWERED

    try:
        from toon_parser import parse_toon  # deferred: keeps import cost off the happy path

        parsed = parse_toon(completed.stdout)
    except Exception:  # a malformed consult establishes nothing
        return _LOOKUP_UNANSWERED

    if not isinstance(parsed, dict):
        return _LOOKUP_UNANSWERED
    location = parsed.get('location')
    if location not in PLAN_LOCATIONS:
        return _LOOKUP_UNANSWERED
    if location != PLAN_LOCATION_WORKTREE:
        # ``not_found`` is a verdict; so is ``current``, which at this point means
        # the locator's cwd walk-up saw a plan dir this gate's resolver did not
        # (an active PLAN_BASE_DIR override). Neither names a foreign holder.
        return _LOOKUP_NO_HOLDER
    worktree_path = parsed.get('worktree_path')
    if not worktree_path:
        return _LOOKUP_UNANSWERED
    return _CheckoutLookup(True, Path(str(worktree_path)))


def _resolution_scope() -> str:
    """Classify how wide a cwd-relative plan enumeration reaches: ``main`` vs ``worktree_local``.

    ``cmd_list`` and this module's plan read both resolve ``get_plans_dir()`` /
    ``get_worktree_root()`` cwd-relatively under the uniform resolver (ADR-002). The
    resolved scope is NOT the same in every checkout, and a consumer that reads an
    absence as authoritative MUST know which:

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
    field, and on a plan read's refusal as the basis of its ``plan_visibility``
    discriminator, so neither surface can silently mistake a cwd-scoped look for a
    global one. Held HERE rather than beside ``cmd_list`` because both consumers
    must ask one predicate; two copies would drift into two answers.
    """
    try:
        main_base = resolve_main_anchored_path('')
        current_base = get_base_dir()
    except (RuntimeError, OSError):
        return RESOLUTION_SCOPE_UNKNOWN
    try:
        return (
            RESOLUTION_SCOPE_MAIN if current_base.resolve() == main_base.resolve() else RESOLUTION_SCOPE_WORKTREE_LOCAL
        )
    except OSError:
        return RESOLUTION_SCOPE_MAIN if str(current_base) == str(main_base) else RESOLUTION_SCOPE_WORKTREE_LOCAL


class PlanStatusResolution(NamedTuple):
    """A plan's status document together with the checkout that answered for it.

    ``status`` is ``None`` exactly when no checkout in reach held the plan; the
    other fields then say how far the look reached rather than asserting absence.

    ``scope`` is resolved ONLY on the miss path and is ``None`` after a local hit.
    That is deliberate: resolving it costs a main-anchor resolution (a ``git
    rev-parse`` in production), and a read answered by the local tree never had to
    ask how wide the alternative scan would have been. A ``None`` scope therefore
    means "the question did not arise", never "the scan was global".

    Attributes:
        status: The plan's ``status.json`` document, or ``None``.
        location: One of :data:`PLAN_LOCATIONS`.
        checkout_path: The holding checkout, present only for
            ``location == 'worktree'``.
        scope: One of :data:`RESOLUTION_SCOPES` on a miss; ``None`` on a hit.
        visibility: One of :data:`PLAN_VISIBILITY_STATES` on a miss; ``None`` on a
            hit.
    """

    status: dict[Any, Any] | None
    location: str
    checkout_path: str | None
    scope: str | None
    visibility: str | None


def resolve_plan_status(plan_id: str, any_checkout: bool = False) -> PlanStatusResolution:
    """Read a plan's status, optionally from the sibling worktree that holds it.

    Args:
        plan_id: Plan identifier whose ``status.json`` is being read.
        any_checkout: When ``True`` and the plan is absent from the locally
            resolved tree, adopt the document of the checkout that actually holds
            it (resolved through ``locate-plan-checkout``).

            ⛔ READ-ONLY by construction at the call sites. ``require_status``
            gates WRITE verbs too (``set-phase``, ``metadata --set``,
            ``transition``), and every one of them commits through
            ``write_status`` → ``get_status_path``, which resolves the path
            LOCALLY. A write verb that read a sibling plan through this fallback
            would then write the document into the wrong tree — strictly worse
            than the absence being fixed. Only read verbs opt in.

    Returns:
        A :class:`PlanStatusResolution`. A miss is returned as ``status=None``
        with a ``visibility`` that says what the look established, never as a bare
        absence.
    """
    status = read_status(plan_id)
    if status:
        return PlanStatusResolution(status, PLAN_LOCATION_CURRENT, None, None, None)

    lookup = _locate_plan_checkout(plan_id) if any_checkout else _LOOKUP_UNANSWERED
    if lookup.worktree_path is not None:
        foreign = read_json(lookup.worktree_path / PLAN_DIR_NAME / 'local' / DIR_PLANS / plan_id / FILE_STATUS)
        if isinstance(foreign, dict) and foreign:
            return PlanStatusResolution(
                foreign,
                PLAN_LOCATION_WORKTREE,
                str(lookup.worktree_path),
                None,
                None,
            )

    # Absence is claimed only on the conjunction that substantiates it: the
    # locator rendered a verdict AND the enumeration scope observes every sibling
    # worktree. A strict gate (which never consulted) and a degraded consult both
    # fall to the weaker, honest claim.
    scope = _resolution_scope()
    visibility = (
        PLAN_ABSENT_ANYWHERE if lookup.answered and scope == RESOLUTION_SCOPE_MAIN else PLAN_NOT_VISIBLE_FROM_SCOPE
    )
    return PlanStatusResolution(None, PLAN_LOCATION_NOT_FOUND, None, scope, visibility)


def plan_resolution_fields(resolution: PlanStatusResolution) -> dict[str, Any]:
    """Return the payload fragment a read verb merges in, naming which checkout answered.

    Published on EVERY read, not only the sibling-worktree one: a caller that can
    see ``resolved_from`` on the local case too can tell the two apart, whereas a
    field that appears only on the foreign case is indistinguishable from a caller
    that forgot to look for it.
    """
    fields: dict[str, Any] = {'resolved_from': resolution.location}
    if resolution.checkout_path is not None:
        fields['resolved_checkout'] = resolution.checkout_path
    return fields


def plan_unresolved_error(plan_id: str, resolution: PlanStatusResolution) -> dict[str, Any]:
    """Build the refusal payload for a plan no reachable checkout held.

    ``error: file_not_found`` is preserved verbatim — it is the code every
    existing consumer branches on, and this deliverable widens the refusal rather
    than renaming it. What is added is the discriminator: ``scope`` names how wide
    the look was and ``plan_visibility`` says whether that look substantiates
    absence.
    """
    if resolution.visibility == PLAN_ABSENT_ANYWHERE:
        message = (
            f'status.json not found: no checkout holds plan {plan_id!r}. The look ran from the '
            f'main-anchored scope, which observes main and every sibling worktree, so this '
            f'absence is authoritative.'
        )
    else:
        message = (
            f'status.json not found: plan {plan_id!r} is not visible from this scope '
            f'(scope={resolution.scope}). The look was anchored at this checkout and did not '
            f'establish that the plan is absent elsewhere — read this as "not visible from here", '
            f'never as "does not exist".'
        )
    return {
        'status': 'error',
        'plan_id': plan_id,
        'error': 'file_not_found',
        'message': message,
        'scope': resolution.scope,
        'plan_visibility': resolution.visibility,
    }


def require_status_resolved(args: argparse.Namespace, any_checkout: bool = False) -> PlanStatusResolution | None:
    """Validate plan_id and resolve the plan's status, TOON refusal when unresolvable.

    The provenance-bearing gate: read verbs call it with ``any_checkout=True`` so
    they can publish which checkout answered (:func:`plan_resolution_fields`).
    :func:`require_status` is the thin dict-returning projection over it that every
    other verb keeps using.
    """
    require_valid_plan_id(args)
    resolution = resolve_plan_status(args.plan_id, any_checkout=any_checkout)
    if resolution.status is None:
        output_toon(plan_unresolved_error(args.plan_id, resolution))
        return None
    return resolution


def require_status(args: argparse.Namespace, any_checkout: bool = False) -> dict[Any, Any] | None:
    """Validate plan_id and read status, returning None with TOON error if missing.

    ``any_checkout`` opts into the sibling-worktree fallback and defaults to
    ``False`` — the same read-widening opt-in shape ``read_store_status`` /
    ``_require_orchestrator_status`` already use for ``allow_archived``. It MUST
    stay default-off: this is the shared gate for WRITE verbs, which commit
    through a LOCALLY resolved path (see :func:`resolve_plan_status`).
    """
    resolution = require_status_resolved(args, any_checkout=any_checkout)
    return None if resolution is None else resolution.status
