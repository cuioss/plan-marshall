"""Command handlers for phase_handshake (capture, verify, list, clear).

This module wires two worktree-related boundary checks on top of the
generic invariant registry in :mod:`_invariants`:

1. :func:`_resolve_worktree_assertion` — phase-entry assertion in the
   ``metadata→disk`` direction. Refuses to enter a phase when
   ``metadata.use_worktree==true`` but ``metadata.worktree_path`` is
   missing or does not resolve to a real git worktree. Surfaces as
   ``error: worktree_unresolved`` (under ``--strict`` exits non-zero).

2. ``_capture_main_dirty_files`` (in :mod:`_invariants`) plus
   :func:`_check_main_dirty_drift` (verify-time, in this module) — layer-D
   enforcement that detects free-form filesystem leaks into the main
   checkout during a worktree-routed plan. The capture records the
   sorted, ``.plan/``-filtered dirty-path set; the verify check raises
   :class:`_invariants.MainCheckoutDirtiedDuringPlan` when the live set
   is a *proper superset* of the captured baseline AND ``use_worktree==true``.
   Surfaces as ``error: main_checkout_dirtied_during_plan`` (under
   ``--strict`` exits non-zero). The proper-superset rule means
   pre-existing dirty paths (baseline-equal) do not trip the invariant —
   only newly-dirty paths between boundaries count as a leak.

Both checks share a common contract: under ``--strict`` they refuse
to advance the boundary so prompt-discipline failures cannot run
silently. See
``workflow-integration-git/standards/worktree-handling.md`` for the
operator-facing recovery loops and the worktree-routing contract this
module enforces.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from _handshake_store import (  # type: ignore[import-not-found]
    HANDSHAKE_FIELDS,
    get_row,
    load_rows,
    remove_row,
    upsert_row,
)
from _invariants import (  # type: ignore[import-not-found]
    INVARIANTS,
    BlockingFindingsPresent,
    MainCheckoutDirtiedDuringPlan,
    PhaseStepsIncomplete,
    _capture_pending_findings_blocking_count,
    _main_dirty_drift_diff,
    capture_all,
    is_invariant_blocking_at_phase,
)
from file_ops import get_executor_path  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]


def _now_iso() -> str:
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def _is_truthy_metadata(value: Any) -> bool:
    """Decide whether a metadata field expressing a boolean is true.

    ``status.json`` metadata serializes booleans through TOON, which yields
    Python ``bool`` after ``parse_toon``. Tolerates the string forms
    ``'true'`` / ``'True'`` / ``'1'`` for robustness against future TOON
    schema changes — never returns true for empty / missing values.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {'true', '1', 'yes'}
    if isinstance(value, int):
        return value != 0
    return False


# Planning-phase boundaries that run on the main checkout. The on-disk
# worktree directory and feature branch are materialized at phase-5-execute
# Step 2.5; phases 1-init through 4-plan run on main. This set gates the
# layer-D leak-into-main guard (:func:`_check_main_dirty_drift`), which only
# fires for the planning-phase boundaries where a free-form filesystem write
# can still land in the main checkout.
_PLANNING_PHASES_ON_MAIN: frozenset[str] = frozenset({
    '1-init',
    '2-refine',
    '3-outline',
    '4-plan',
})


def _resolve_worktree_assertion(
    metadata: dict[str, Any],
    phase: str | None = None,
) -> dict[str, Any] | None:
    """Worktree-resolution phase-entry assertion (metadata→disk direction).

    1. ``use_worktree`` is not truthy → assertion passes (return ``None``).
       Plans routed against the main checkout never trip this assertion.
    2. ``use_worktree==true`` AND ``worktree_path`` is non-empty AND
       filesystem-resolvable (directory exists, is a git worktree, and
       ``git rev-parse --show-toplevel`` returns the same canonical
       path) → assertion passes (return ``None``).
    3. ``use_worktree==true`` AND ``worktree_path`` is empty/missing →
       phase-dependent. The worktree (and therefore ``worktree_path``) is
       materialized at phase-5-execute Step 2.5; phases 1-4 persist only the
       ``use_worktree`` intent (``_cmd_lifecycle`` writes ``{'use_worktree':
       True}`` at create with no path). An empty path while
       ``use_worktree==true`` is therefore the *legitimate* pre-materialization
       state for the on-main planning phases (``_PLANNING_PHASES_ON_MAIN``) and
       the assertion passes there. From phase-5 onward — and whenever ``phase``
       is unknown — the path MUST be present, so an empty path still surfaces
       ``worktree_unresolved`` (fail-closed default).

    Other failure cases (always surface as ``worktree_unresolved`` at every
    phase, because a *set-but-broken* path is never a transitional state):
        - ``worktree_path`` is set but the directory does not exist
        - ``worktree_path`` exists but is not a git worktree
        - ``worktree_path`` exists, is a git worktree, but ``rev-parse
          --show-toplevel`` resolves to a different path (stale link)

    See ``workflow-integration-git/standards/worktree-handling.md`` for the
    canonical worktree contract this assertion enforces at every phase
    boundary.
    """
    if not _is_truthy_metadata(metadata.get('use_worktree')):
        return None

    raw = metadata.get('worktree_path')
    path_str = str(raw).strip() if raw is not None else ''
    if not path_str:
        # Phases 1-4 run on the main checkout and persist only the
        # use_worktree intent; the path is materialized at phase-5 Step 2.5.
        # An empty path there is the expected pre-materialization state, not a
        # defect. From phase-5 onward (or when phase is unknown) fail closed.
        if phase in _PLANNING_PHASES_ON_MAIN:
            return None
        return {
            'status': 'error',
            'error': 'worktree_unresolved',
            'reason': 'worktree_path_missing',
            'message': (
                'metadata.use_worktree==true but metadata.worktree_path is missing or empty; '
                'phase entry refuses to advance until status metadata is repaired.'
            ),
        }

    candidate = Path(path_str)
    if not candidate.exists() or not candidate.is_dir():
        return {
            'status': 'error',
            'error': 'worktree_unresolved',
            'reason': 'worktree_path_not_found',
            'worktree_path': path_str,
            'message': (
                f'metadata.worktree_path={path_str!r} does not exist on disk; '
                'phase entry refuses to advance.'
            ),
        }

    try:
        result = subprocess.run(
            ['git', '-C', path_str, 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {
            'status': 'error',
            'error': 'worktree_unresolved',
            'reason': 'git_invocation_failed',
            'worktree_path': path_str,
            'message': (
                f'metadata.worktree_path={path_str!r} could not be probed via '
                f'git rev-parse --show-toplevel: {exc}.'
            ),
        }

    if result.returncode != 0:
        stderr = (result.stderr or '').strip()
        return {
            'status': 'error',
            'error': 'worktree_unresolved',
            'reason': 'not_a_git_worktree',
            'worktree_path': path_str,
            'message': (
                f'metadata.worktree_path={path_str!r} is not a git worktree '
                f'(git rev-parse --show-toplevel exit={result.returncode}, stderr={stderr!r}).'
            ),
        }

    resolved = (result.stdout or '').strip()
    try:
        same = resolved and Path(resolved).resolve() == candidate.resolve()
    except OSError:
        same = False
    if not same:
        return {
            'status': 'error',
            'error': 'worktree_unresolved',
            'reason': 'worktree_path_stale',
            'worktree_path': path_str,
            'resolved_toplevel': resolved,
            'message': (
                f'metadata.worktree_path={path_str!r} resolves to a different toplevel '
                f'({resolved!r}); the persisted path is stale.'
            ),
        }

    return None


def _load_status_metadata(plan_id: str) -> dict[str, Any]:
    """Return ``status.json`` metadata for ``plan_id`` via ``manage-status``."""
    try:
        executor = get_executor_path()
    except RuntimeError:
        return {}
    if not executor.exists():
        return {}
    try:
        result = subprocess.run(
            [
                'python3',
                str(executor),
                'plan-marshall:manage-status:manage-status',
                'read',
                '--plan-id',
                plan_id,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return {}
    if result.returncode != 0:
        return {}
    try:
        parsed = parse_toon(result.stdout)
    except Exception:
        return {}
    plan = parsed.get('plan') or {}
    metadata = plan.get('metadata') if isinstance(plan, dict) else {}
    return metadata if isinstance(metadata, dict) else {}


def _coerce_path_list(raw: Any) -> list[str]:
    """Coerce a captured-row ``main_dirty_files`` value into a list of paths.

    The stored row may carry the field as:

    - A Python list (the natural shape after :func:`toon_parser.parse_toon`
      decodes a TOON list) — returned verbatim with each element stringified.
    - The empty string ``''`` (the ``HANDSHAKE_FIELDS`` default when capture
      returned ``None``) — returned as ``[]`` to mean "no baseline".
    - A comma-separated string (legacy or hand-edited rows) — split and
      stripped so callers don't need to guess at the storage format.

    Returns ``[]`` for ``None`` / unrecognized shapes so the caller's
    proper-superset check sees an empty baseline (every observed path
    becomes "newly dirty"). That matches the conservative interpretation:
    if we cannot prove the baseline, treat any current dirty path as
    suspect rather than silently passing the boundary.
    """
    if raw is None or raw == '':
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item)]
    if isinstance(raw, str):
        return [item.strip() for item in raw.split(',') if item.strip()]
    return []


def _check_main_dirty_drift(
    plan_id: str,
    phase: str,
    captured_row: dict[str, Any],
    observed: dict[str, Any],
    metadata: dict[str, Any],
) -> None:
    """Layer-D enforcement: raise on proper-superset main-checkout drift.

    Gate 1 (boundary phase): only fires at the planning-phase boundaries
    ``1-init`` / ``2-refine`` / ``3-outline`` / ``4-plan`` (which run on the
    main checkout). Under the move-based, cwd-pinned hermetic worktree model
    (ADR-002 / Option 5'), phase-5 materializes the worktree and MOVES the
    plan dir in; from that point the orchestrator's cwd IS the worktree and
    the single cwd-unchanged invariant keeps it pinned there, so plan work
    lands in the worktree by construction and the leak-into-main guard is
    structurally moot at the ``5-execute → 6-finalize`` boundary. Mirrors the
    ``main_dirty_files`` blocking-scope relaxation in
    ``_invariants.INVARIANT_BLOCKING_SCOPE`` — the discriminator is the
    boundary phase, not a runtime resolver branch.

    Gate 2 (worktree routing): only fires when ``metadata.use_worktree`` is
    truthy. Plans that run against the main checkout (``use_worktree==false``
    or absent) legitimately dirty main, so the invariant is not enforced
    there.

    Compares ``captured_row['main_dirty_files']`` (the previous-boundary
    baseline) against ``observed.get('main_dirty_files')`` (the live
    capture) using set-difference proper-superset semantics. When the
    observed set contains every baseline path AND at least one additional
    path, raises :class:`_invariants.MainCheckoutDirtiedDuringPlan` with
    the ``newly_dirty`` payload listing only the leaked paths so
    ``cmd_verify`` can surface a structured TOON error and the operator
    sees exactly what to revert.

    Returns ``None`` (no drift) when:
        - ``use_worktree`` is not truthy (gate)
        - The observed set is a (non-strict) subset of the baseline
        - The baseline and observed sets are identical

    Note: the inverse direction (baseline contained paths the observed
    set no longer has) is *not* a layer-D leak; a previously-dirty main
    file that got cleaned between captures is benign. Only newly-dirty
    paths count.
    """
    # Gate 1 — boundary phase: relaxed for phase-5+ (move model makes the
    # leak-into-main surface structurally closed); retained for phases 1-4.
    if phase not in _PLANNING_PHASES_ON_MAIN:
        return
    # Gate 2 — worktree routing: main-checkout plans dirty main freely.
    if not _is_truthy_metadata(metadata.get('use_worktree')):
        return
    baseline = _coerce_path_list(captured_row.get('main_dirty_files'))
    live = _coerce_path_list(observed.get('main_dirty_files'))
    newly_dirty = _main_dirty_drift_diff(baseline, live)
    if not newly_dirty:
        return
    raise MainCheckoutDirtiedDuringPlan(
        plan_id=plan_id,
        phase=phase,
        baseline=baseline,
        observed=live,
        newly_dirty=newly_dirty,
    )


def _row_for_capture(
    plan_id: str,
    phase: str,
    captured: dict[str, Any],
    metadata: dict[str, Any],
    *,
    override: bool,
    override_reason: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        'phase': phase,
        'captured_at': _now_iso(),
        'worktree_applicable': bool(metadata.get('worktree_path')),
        'override': override,
        'override_reason': override_reason,
    }
    for name, _applies, _capture in INVARIANTS:
        row[name] = captured.get(name, '')
    return row


def cmd_capture(args: Any) -> dict[str, Any]:
    if args.override and not args.reason:
        return {
            'status': 'error',
            'error': 'missing_reason',
            'message': '--override requires --reason',
        }

    plan_id = args.plan_id
    phase = args.phase
    metadata = _load_status_metadata(plan_id)
    worktree_error = _resolve_worktree_assertion(metadata, phase)
    if worktree_error is not None:
        payload = dict(worktree_error)
        payload['plan_id'] = plan_id
        payload['phase'] = phase
        return payload
    try:
        captured = capture_all(plan_id, metadata, phase)
    except PhaseStepsIncomplete as exc:
        return {
            'status': 'error',
            'error': 'phase_steps_incomplete',
            'plan_id': plan_id,
            'phase': phase,
            'missing': exc.missing,
            'not_done': exc.not_done,
            'legacy_format': exc.legacy_format,
            'message': str(exc),
        }
    except BlockingFindingsPresent as exc:
        return {
            'status': 'error',
            'error': 'blocking_findings_present',
            'plan_id': plan_id,
            'phase': phase,
            'blocking_count': exc.blocking_count,
            'blocking_types': exc.blocking_types,
            'per_type': exc.per_type,
            'message': str(exc),
        }
    row = _row_for_capture(
        plan_id,
        phase,
        captured,
        metadata,
        override=bool(args.override),
        override_reason=args.reason or '',
    )
    upsert_row(plan_id, row)

    invariants_out = {name: row[name] for name, _a, _c in INVARIANTS if row[name] != ''}
    return {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'override': row['override'],
        'worktree_applicable': row['worktree_applicable'],
        'invariants': invariants_out,
    }


def _diffs(
    captured_row: dict[str, Any],
    observed: dict[str, Any],
    phase: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(blocking_diffs, informational_diffs)`` for ``phase``.

    Each invariant's drift is bucketed by its blocking classification (see
    ``_invariants.INVARIANT_BLOCKING_SCOPE``). Blocking diffs contribute to
    ``drift_count`` and are surfaced in the ``diffs[]`` payload; informational
    diffs are returned separately so ``cmd_verify`` can record them in
    ``handshakes.toon`` without raising ``status: drift``.

    ``phase`` is the phase being entered (the target side of the transition
    the handshake is verifying).
    """
    blocking_diffs: list[dict[str, Any]] = []
    informational_diffs: list[dict[str, Any]] = []
    for name, _a, _c in INVARIANTS:
        # ``main_dirty_files`` is owned by the dedicated layer-D drift
        # check :func:`_check_main_dirty_drift` (proper-superset semantics).
        # Skipping it here prevents the generic stringified-list comparison
        # from emitting a low-signal "drift" diff alongside (or instead of)
        # the structured ``main_checkout_dirtied_during_plan`` error. The
        # accompanying scalar ``main_dirty`` column still participates in
        # the generic comparison so operators retain the count signal.
        if name == 'main_dirty_files':
            continue
        cap_value = captured_row.get(name, '')
        if cap_value == '':
            # Not captured (invariant was not applicable or missing) — skip.
            continue
        obs_value = observed.get(name)
        if obs_value is None:
            obs_value = ''
        if str(cap_value) != str(obs_value):
            diff_entry = {
                'invariant': name,
                'captured': str(cap_value),
                'observed': str(obs_value),
            }
            if is_invariant_blocking_at_phase(name, phase):
                blocking_diffs.append(diff_entry)
            else:
                informational_diffs.append(diff_entry)
    return blocking_diffs, informational_diffs


def cmd_verify(args: Any) -> dict[str, Any]:
    plan_id = args.plan_id
    phase = args.phase
    captured_row = get_row(plan_id, phase)
    if captured_row is None:
        return {
            'status': 'skipped',
            'plan_id': plan_id,
            'phase': phase,
            'message': 'No capture exists for phase',
        }

    metadata = _load_status_metadata(plan_id)
    worktree_error = _resolve_worktree_assertion(metadata, phase)
    if worktree_error is not None:
        payload = dict(worktree_error)
        payload['plan_id'] = plan_id
        payload['phase'] = phase
        return payload
    try:
        observed = capture_all(plan_id, metadata, phase)
    except PhaseStepsIncomplete as exc:
        # Treat observed incompleteness as drift on the phase_steps_complete
        # column so callers see a structured difference rather than an error.
        observed = {}
        diffs = [
            {
                'invariant': 'phase_steps_complete',
                'captured': str(captured_row.get('phase_steps_complete', '')),
                'observed': (
                    f'incomplete(missing={exc.missing},not_done={exc.not_done},legacy_format={exc.legacy_format})'
                ),
            }
        ]
        return {
            'status': 'drift',
            'plan_id': plan_id,
            'phase': phase,
            'override': captured_row.get('override', False),
            'drift_count': len(diffs),
            'diffs': diffs,
        }
    except BlockingFindingsPresent as exc:
        # Treat observed blocking findings as drift on the
        # ``pending_findings_blocking_count`` column so callers see a
        # structured difference rather than a hard error. ``--strict``
        # turns this into a non-zero exit.
        diffs = [
            {
                'invariant': 'pending_findings_blocking_count',
                'captured': str(captured_row.get('pending_findings_blocking_count', '')),
                'observed': (
                    f'blocking(count={exc.blocking_count},'
                    f'blocking_types={exc.blocking_types},'
                    f'per_type={exc.per_type})'
                ),
            }
        ]
        return {
            'status': 'drift',
            'plan_id': plan_id,
            'phase': phase,
            'override': captured_row.get('override', False),
            'drift_count': len(diffs),
            'diffs': diffs,
        }

    # Layer-D enforcement (filesystem-state-based): proper-superset drift
    # of main_dirty_files between the captured baseline and the live set
    # raises MainCheckoutDirtiedDuringPlan on worktree-routed plans. Run
    # BEFORE the generic _diffs comparison so the structured error
    # payload (with the newly_dirty path list) takes precedence over the
    # plain "drift on main_dirty_files column" form _diffs would emit.
    try:
        _check_main_dirty_drift(plan_id, phase, captured_row, observed, metadata)
    except MainCheckoutDirtiedDuringPlan as exc:
        return {
            'status': 'error',
            'error': 'main_checkout_dirtied_during_plan',
            'plan_id': plan_id,
            'phase': phase,
            'baseline': exc.baseline,
            'observed': exc.observed,
            'newly_dirty': exc.newly_dirty,
            'message': str(exc),
        }

    diffs, informational_diffs = _diffs(captured_row, observed, phase)

    if not diffs:
        result_ok: dict[str, Any] = {
            'status': 'ok',
            'plan_id': plan_id,
            'phase': phase,
            'override': captured_row.get('override', False),
        }
        # Surface informational-only drift (e.g. main_sha changed between
        # planning-phase boundaries) so retrospective analysis sees it even
        # when status is ``ok``. ``drift_count`` deliberately stays absent
        # in the ``ok`` envelope so callers that branch on it (the strict
        # exit path, the orchestrator's drift-recovery branch) continue to
        # treat informational drift as "not a drift".
        if informational_diffs:
            result_ok['informational_count'] = len(informational_diffs)
            result_ok['informational_diffs'] = informational_diffs
        return result_ok

    result: dict[str, Any] = {
        'status': 'drift',
        'plan_id': plan_id,
        'phase': phase,
        'override': captured_row.get('override', False),
        'drift_count': len(diffs),
        'diffs': diffs,
    }
    if informational_diffs:
        result['informational_count'] = len(informational_diffs)
        result['informational_diffs'] = informational_diffs
    return result


def cmd_findings_check(args: Any) -> dict[str, Any]:
    """Read-only single-invariant gate: evaluate ONLY the blocking-findings invariant.

    Mirrors the non-writing ``verify`` precedent — a distinct handler that
    reuses an existing capture function in isolation. It runs the
    worktree-resolution assertion (consistent with ``capture``/``verify``),
    then invokes :func:`_invariants._capture_pending_findings_blocking_count`
    directly — NOT ``capture_all`` — so ``phase_steps_complete`` is never
    evaluated and the gate cannot short-circuit on ``phase_steps_incomplete``
    at a mid-pipeline checkpoint where the downstream finalize steps have not
    run yet.

    Writes NO handshake row. On a clean count returns
    ``{status: success, plan_id, phase, blocking_count: N}``. On a pending
    blocking finding the underlying invariant raises
    :class:`BlockingFindingsPresent`, which this handler translates into the
    SAME ``{status: error, error: blocking_findings_present, ...}`` payload
    shape ``cmd_capture`` returns, so the two intra-finalize callers branch on
    an identical envelope.

    **Fails closed on an unevaluable invariant.**
    :func:`_capture_pending_findings_blocking_count` returns ``None`` when a
    per-type query could not run (executor unreachable / partial query
    failure). For a gate verb that is NOT a benign "not applicable" — returning
    ``status: success`` would let the intra-finalize boundary advance to
    ``branch-cleanup`` without proof that no blocking findings remain. This
    handler therefore translates ``None`` into a distinct
    ``{status: error, error: query_failed, ...}`` envelope so the caller halts
    rather than failing open. (The composite ``capture`` records ``None`` as an
    empty column for retrospective analysis; the read-only gate verb cannot
    afford that latitude because its sole output is the go/no-go verdict.)
    """
    plan_id = args.plan_id
    phase = args.phase
    metadata = _load_status_metadata(plan_id)
    worktree_error = _resolve_worktree_assertion(metadata, phase)
    if worktree_error is not None:
        payload = dict(worktree_error)
        payload['plan_id'] = plan_id
        payload['phase'] = phase
        return payload
    try:
        blocking_count = _capture_pending_findings_blocking_count(plan_id, metadata, phase)
    except BlockingFindingsPresent as exc:
        return {
            'status': 'error',
            'error': 'blocking_findings_present',
            'plan_id': plan_id,
            'phase': phase,
            'blocking_count': exc.blocking_count,
            'blocking_types': exc.blocking_types,
            'per_type': exc.per_type,
            'message': str(exc),
        }
    if blocking_count is None:
        # Fail closed: a partial query failure means the blocking-findings
        # invariant could not be evaluated. Returning success here would let the
        # intra-finalize gate advance without proof that no blocking findings
        # remain. Surface a distinct query_failed error so the caller halts.
        return {
            'status': 'error',
            'error': 'query_failed',
            'plan_id': plan_id,
            'phase': phase,
            'message': (
                'pending_findings_blocking_count could not be evaluated for '
                f"phase '{phase}' (executor unreachable / partial query failure)"
            ),
        }
    return {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'blocking_count': blocking_count,
    }


def cmd_list(args: Any) -> dict[str, Any]:
    plan_id = args.plan_id
    rows = load_rows(plan_id)
    # Project to stored field order for stable output.
    projected = [{f: row.get(f, '') for f in HANDSHAKE_FIELDS} for row in rows]
    return {
        'status': 'success',
        'plan_id': plan_id,
        'count': len(projected),
        'handshakes': projected,
    }


def cmd_clear(args: Any) -> dict[str, Any]:
    plan_id = args.plan_id
    phase = args.phase
    removed = remove_row(plan_id, phase)
    return {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'removed': removed,
    }
