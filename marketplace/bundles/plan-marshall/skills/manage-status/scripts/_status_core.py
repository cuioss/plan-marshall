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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from _locks_core import rmw_json
from constants import DIR_ARCHIVED, DIR_PLANS, FILE_STATUS
from file_ops import (
    base_path,
    get_executor_path,
    get_plan_dir,
    get_store_dir,
    now_utc_iso,
    output_toon,
    read_json,
    write_json,
)
from input_validation import require_valid_plan_id  # noqa: F401 - re-exported
from plan_logging import log_entry

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

    Specified once in ``manage-terminal-title/standards/terminal-title-architecture.md``
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
# PreToolUse:Bash / PostToolUse:Bash render assist that brackets a build window,
# ``merge-lock`` is manage-locks/merge_lock.py, and ``cli`` is an explicit
# ``manage-status title-token set`` invocation from the orchestration layer.
TITLE_TOKEN_OWNER_BUILD_HOOK = 'build-hook'
TITLE_TOKEN_OWNER_MERGE_LOCK = 'merge-lock'
TITLE_TOKEN_OWNER_CLI = 'cli'
TITLE_TOKEN_OWNERS = frozenset(
    {TITLE_TOKEN_OWNER_BUILD_HOOK, TITLE_TOKEN_OWNER_MERGE_LOCK, TITLE_TOKEN_OWNER_CLI}
)

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


def write_status(plan_id: str, status: dict[Any, Any]) -> None:
    """Write status.json for a plan."""
    status['updated'] = now_utc_iso()
    write_json(get_status_path(plan_id), status)


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
# Orchestrator store (kind=orchestrator)
# =============================================================================
#
# The orchestrator store holds epic-level status.json documents under
# ``.plan/local/orchestrator/{slug}/`` (main-anchored via ``get_store_dir``,
# deliverable D0). The ``kind=orchestrator`` schema is deliberately lean —
# a three-value ``phase`` field instead of the plan phase-transition
# machinery:
#
#   {kind, title, phase (init|orchestrating|closed), workstreams[],
#    plans[]{id,slug,workstream,status,plan_marshall_plan_id,pr,landing},
#    resume_anchor, metadata, created, updated}
#
# See ``standards/status-lifecycle.md`` for the schema contract.

ORCHESTRATOR_STORE = 'orchestrator'
ORCHESTRATOR_PHASES = ('init', 'orchestrating', 'closed')
ORCHESTRATOR_LIST_FIELDS = frozenset({'workstreams', 'plans'})
ORCHESTRATOR_UPDATABLE_FIELDS = frozenset({'phase', 'resume_anchor'}) | ORCHESTRATOR_LIST_FIELDS


def get_store_status_path(store: str, entry_id: str, allow_archived: bool = False) -> Path:
    """Get the status.json path for an entry of a named store.

    ``allow_archived`` threads into :func:`file_ops.get_store_dir`'s
    read-fallback: for ``store='orchestrator'``, when ``True`` and the active
    tree is absent, the archived home is resolved (when it exists). READ verbs
    opt in; WRITE verbs keep the default ``False`` so an archived epic is never
    mutated at the active path.
    """
    return get_store_dir(store, entry_id, allow_archived=allow_archived) / FILE_STATUS


def read_store_status(store: str, entry_id: str, allow_archived: bool = False) -> dict[Any, Any]:
    """Read status.json for a store entry (empty dict when absent or malformed).

    ``read_json`` already degrades a missing/unreadable/unparseable file to the
    default ``{}``, but a status.json whose top-level JSON is valid-but-non-dict
    (an array, a bare string, ``null``) would otherwise flow straight into
    ``cast(dict, ...)`` and crash every downstream ``.get``/subscript caller.
    Fall back to ``{}`` on any non-dict parse so callers always receive a dict.

    ``allow_archived`` threads into :func:`get_store_status_path` so READ verbs
    resolve an archived epic transparently when its active tree is absent.
    """
    data = read_json(get_store_status_path(store, entry_id, allow_archived=allow_archived))
    if not isinstance(data, dict):
        return {}
    return cast(dict[Any, Any], data)


def write_store_status(store: str, entry_id: str, status: dict[Any, Any]) -> None:
    """Write status.json for a store entry, stamping ``updated``."""
    status['updated'] = now_utc_iso()
    write_json(get_store_status_path(store, entry_id), status)


def _require_orchestrator_status(
    args: argparse.Namespace, allow_archived: bool = False
) -> dict[Any, Any] | None:
    """Validate the slug and read the orchestrator status, TOON error when missing.

    ``allow_archived`` threads into :func:`read_store_status`: READ verbs pass
    ``True`` so an archived-only epic resolves from ``archived-orchestrators/``;
    WRITE verbs keep the default ``False`` so an archived-only epic is absent at
    the strict active path and refuses with the existing ``file_not_found``
    contract (no resurrection at the active path).
    """
    require_valid_plan_id(args)
    status = read_store_status(ORCHESTRATOR_STORE, args.plan_id, allow_archived=allow_archived)
    if not status:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'store': ORCHESTRATOR_STORE,
                'error': 'file_not_found',
                'message': 'status.json not found in orchestrator store',
            }
        )
        return None
    return status


def cmd_orchestrator_create(args: argparse.Namespace) -> dict[str, Any] | None:
    """Create a ``kind=orchestrator`` status.json under the orchestrator store."""
    require_valid_plan_id(args)
    status_path = get_store_status_path(ORCHESTRATOR_STORE, args.plan_id)
    if status_path.exists() and not args.force:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'store': ORCHESTRATOR_STORE,
            'error': 'already_exists',
            'message': 'status.json already exists (use --force to overwrite)',
        }
    now = now_utc_iso()
    status: dict[str, Any] = {
        'kind': 'orchestrator',
        'title': args.title,
        'phase': ORCHESTRATOR_PHASES[0],
        'workstreams': [],
        'plans': [],
        'resume_anchor': '',
        'metadata': {},
        'created': now,
        'updated': now,
    }
    write_json(status_path, status)
    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'store': ORCHESTRATOR_STORE,
        'kind': 'orchestrator',
        'phase': status['phase'],
        'file': str(status_path),
    }


def cmd_orchestrator_read(args: argparse.Namespace) -> dict[str, Any] | None:
    """Read a ``kind=orchestrator`` status.json."""
    status = _require_orchestrator_status(args, allow_archived=True)
    if status is None:
        return None
    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'store': ORCHESTRATOR_STORE,
        'plan': status,
    }


def cmd_orchestrator_update_field(args: argparse.Namespace) -> dict[str, Any] | None:
    """Update one top-level field of a ``kind=orchestrator`` status.json.

    ``phase`` is validated against :data:`ORCHESTRATOR_PHASES`;
    list fields (``workstreams``, ``plans``) take a JSON-array ``--value``;
    ``resume_anchor`` stores the value verbatim.
    """
    status = _require_orchestrator_status(args)
    if status is None:
        return None
    field = args.field
    if field not in ORCHESTRATOR_UPDATABLE_FIELDS:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'store': ORCHESTRATOR_STORE,
            'error': 'invalid_field',
            'message': f'--field must be one of {sorted(ORCHESTRATOR_UPDATABLE_FIELDS)}, got: {field}',
        }
    value: Any = args.value
    if field == 'phase' and value not in ORCHESTRATOR_PHASES:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'store': ORCHESTRATOR_STORE,
            'error': 'invalid_value',
            'message': f'--value for phase must be one of {list(ORCHESTRATOR_PHASES)}, got: {value}',
        }
    if field in ORCHESTRATOR_LIST_FIELDS:
        try:
            value = json.loads(value)
        except ValueError:
            value = None
        if not isinstance(value, list):
            return {
                'status': 'error',
                'plan_id': args.plan_id,
                'store': ORCHESTRATOR_STORE,
                'error': 'invalid_value',
                'message': f'--value for {field} must be a JSON array',
            }
    # Serialize the read-modify-write behind the shared O_EXCL-guarded
    # rmw_json critical section (the same coordination core merge_lock uses):
    # the mutation runs against the FRESH in-lock state, so a concurrent
    # orchestrator session mutating a DIFFERENT field cannot be clobbered by a
    # last-writer-wins over a stale read. The orchestrator status.json is
    # main-anchored via get_store_dir('orchestrator', ...) (ADR-002), matching
    # rmw_json's main-anchored contract.
    outcome: dict[str, Any] = {}

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        outcome['previous'] = state.get(field)
        state[field] = value
        state['updated'] = now_utc_iso()
        return state

    rmw_json(get_store_status_path(ORCHESTRATOR_STORE, args.plan_id), _mutate)
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
    # The --get read-path resolves an archived epic transparently; the --set
    # write-path stays strict so an archived-only epic refuses with
    # file_not_found (no resurrection at the active path).
    status = _require_orchestrator_status(args, allow_archived=bool(args.get))
    if status is None:
        return None
    if args.set:
        if args.value is None:
            return {
                'status': 'error',
                'plan_id': args.plan_id,
                'store': ORCHESTRATOR_STORE,
                'error': 'wrong_parameters',
                'message': '--set requires --value; refusing to store a null metadata value',
            }
        # Serialize the metadata read-modify-write behind the shared
        # O_EXCL-guarded rmw_json critical section (the coordination core
        # merge_lock reuses). The mutation runs against the FRESH in-lock
        # state and touches only status['metadata'][field], so a concurrent
        # orchestrator session setting a different metadata field (or a
        # different top-level field) is not lost to a last-writer-wins over a
        # stale read. Main-anchored via get_store_dir (ADR-002).
        field = args.field
        value = args.value
        outcome: dict[str, Any] = {}

        def _mutate(state: dict[str, Any]) -> dict[str, Any]:
            metadata = state.get('metadata')
            if not isinstance(metadata, dict):
                metadata = {}
                state['metadata'] = metadata
            outcome['previous'] = metadata.get(field)
            metadata[field] = value
            state['updated'] = now_utc_iso()
            return state

        rmw_json(get_store_status_path(ORCHESTRATOR_STORE, args.plan_id), _mutate)
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
        metadata = status.get('metadata', {})
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


def _parse_drive_reply(
    completed: 'subprocess.CompletedProcess[str] | None',
) -> dict[Any, Any] | None:
    """Parse a drive-seam delegate's TOON stdout into a dict, else None.

    The shared parse half of the observable-non-delivery pattern: both
    :func:`_repaint_non_delivery_reason` and
    :func:`_teardown_non_delivery_reason` read their delegate's reply through
    this one helper, so the parse discipline (the shared ``toon_parser``, never
    a hand-rolled scan) is stated once.

    Returns ``None`` whenever the reply is unusable: no completed process, empty
    stdout, an unavailable parser, a parse failure, or a non-dict payload.
    """
    if completed is None or not completed.stdout:
        return None
    try:
        from toon_parser import parse_toon
    except ImportError as exc:
        logger.debug('drive-seam reply unparsed (toon_parser unavailable): %s', exc)
        return None
    try:
        reply = parse_toon(completed.stdout)
    except Exception as exc:  # noqa: BLE001 — drive seam is best-effort
        logger.debug('drive-seam reply unparsed: %s', exc)
        return None
    return reply if isinstance(reply, dict) else None


def _teardown_non_delivery_reason(completed: 'subprocess.CompletedProcess[str] | None') -> str | None:
    """Return the reportable failure reason from a teardown reply, else None.

    Releasing the binding is the whole of the teardown, so ``unbound`` is the one
    outcome there is to report: an ACTIVE delegate that failed to drop the slot
    left a stale binding behind, which is worth surfacing.

    An inactive delegate (``active: false`` — a project that never wired up
    terminal titles, reported as ``reason: feature_inactive``) is the ordinary
    nothing-to-do case and returns ``None``.
    """
    reply = _parse_drive_reply(completed)
    if reply is None or reply.get('active') is not True:
        return None
    if reply.get('unbound') is False:
        return 'binding_release_failed'
    return None


def _drive_teardown(plan_id: str) -> None:
    """Best-effort ``session teardown`` — release the caller session's binding.

    Runs through the SAME best-effort executor channel :func:`_drive_bind` /
    :func:`_drive_repaint` use, and the delegate is itself activation-gated — a
    project that never wired up terminal titles is left untouched.

    ``plan_id`` names the plan for the audit trail only — the teardown operates
    on the CALLER SESSION's own binding, not on a plan-scoped slot, so it takes
    no plan argument.

    NOT fired by ``cmd_archive``: the archive path deliberately releases no
    binding, because the terminal state it just persisted is delivered by the
    next render event, which resolves the plan only through that binding.

    A failed release is OBSERVABLE rather than DEBUG-swallowed: when the
    activated delegate reports a failed binding release, one persisted
    ``log_entry`` (the manage-logging work log) names the plan and the reason, so
    the stale binding reaches the plan record instead of only subprocess stderr.
    An inactive delegate and every other failure path keep their DEBUG level.

    Fully exception-swallowing, mirroring :func:`_surface_drive`: a delegation
    failure never changes the calling command's status or exit code.
    """
    try:
        logger.debug('drive-seam teardown fired for %s', plan_id)
        completed = _run_executor(_PLATFORM_RUNTIME_NOTATION, 'session', 'teardown')
        reason = _teardown_non_delivery_reason(completed)
        if reason is not None:
            # Persist the non-delivery to the plan work log via manage-logging
            # (log_entry) instead of a stderr-only logger.warning, so a dead
            # title channel is OBSERVABLE in the plan record. log_entry is itself
            # best-effort (it swallows every I/O error internally), and this call
            # sits inside the surrounding best-effort try/except, so a logging
            # failure never changes the archive command's status or exit code.
            log_entry('work', plan_id, 'WARNING', f'session teardown incomplete for {plan_id}: {reason}')
    except Exception as exc:  # noqa: BLE001 — drive seam is best-effort
        logger.debug('drive-seam teardown for %s failed: %s', plan_id, exc)


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
    except Exception as exc:  # noqa: BLE001 — drive seam is best-effort
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


def require_status(args: argparse.Namespace) -> dict[Any, Any] | None:
    """Validate plan_id and read status, returning None with TOON error if missing."""
    require_valid_plan_id(args)
    status = read_status(args.plan_id)
    if not status:
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'file_not_found', 'message': 'status.json not found'}
        )
        return None
    return status
