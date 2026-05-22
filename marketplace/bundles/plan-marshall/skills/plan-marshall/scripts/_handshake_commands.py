"""Command handlers for phase_handshake (capture, verify, list, clear).

This module wires three worktree-related boundary checks on top of the
generic invariant registry in :mod:`_invariants`:

1. :func:`_resolve_worktree_assertion` — phase-entry assertion in the
   ``metadata→disk`` direction. Refuses to enter a phase when
   ``metadata.use_worktree==true`` but ``metadata.worktree_path`` is
   missing or does not resolve to a real git worktree. Surfaces as
   ``error: worktree_unresolved`` (under ``--strict`` exits non-zero).

2. ``_capture_worktree_orphan`` (in :mod:`_invariants`, raises
   :class:`_invariants.WorktreeMetadataDrift`) — capture-time check in
   the **inverse** ``disk→metadata`` direction. Refuses to capture when
   the on-disk worktree directory exists but metadata reports
   ``use_worktree != true``. Surfaces as ``error: worktree_metadata_drift``.

3. ``_capture_main_dirty_files`` (in :mod:`_invariants`) plus
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

All three checks share a common contract: under ``--strict`` they refuse
to advance the boundary so prompt-discipline failures and writer-chain
drift cannot run silently. See
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
    WorktreeMetadataDrift,
    _main_dirty_drift_diff,
    capture_all,
)
from file_ops import get_base_dir  # type: ignore[import-not-found]
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


# Phases whose entry boundary precedes worktree materialization. During
# these phases, ``use_worktree==true`` with an empty ``worktree_path`` is
# the legitimate deferred-pending state (the orchestrator has decided to
# route the plan through a worktree, but ``phase-5-execute`` has not yet
# created the on-disk directory). The tri-state contract treats this as
# pass-through, not as ``worktree_unresolved``.
_PRE_MATERIALIZATION_PHASES: frozenset[str] = frozenset({
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

    Implements a tri-state contract:

    1. ``use_worktree`` is not truthy → assertion passes (return ``None``).
       Plans routed against the main checkout never trip this assertion.
    2. ``use_worktree==true`` AND ``worktree_path`` is non-empty AND
       filesystem-resolvable (directory exists, is a git worktree, and
       ``git rev-parse --show-toplevel`` returns the same canonical
       path) → assertion passes (return ``None``).
    3. ``use_worktree==true`` AND ``worktree_path`` is empty/missing →
       deferred-pending. When ``phase`` is one of the pre-materialization
       phases (``1-init`` / ``2-refine`` / ``3-outline`` / ``4-plan``)
       the assertion passes (return ``None``); the worktree has not been
       materialized yet and the empty path is the legitimate transitional
       state. For phases ``5-execute`` / ``6-finalize`` the assertion
       fails with ``worktree_unresolved`` because the worktree should
       already exist post-materialization. When ``phase`` is ``None``
       (legacy single-arg callers) the strict pre-tri-state behaviour
       is preserved — empty path always fails.

    Failure cases that ignore the tri-state phase gate (always surface
    as ``worktree_unresolved`` regardless of phase):
        - ``worktree_path`` is set but the directory does not exist
        - ``worktree_path`` exists but is not a git worktree
        - ``worktree_path`` exists, is a git worktree, but ``rev-parse
          --show-toplevel`` resolves to a different path (stale link)

    The **inverse direction** (orphan worktree dir on disk while
    metadata reports ``use_worktree != true``) is handled by the
    ``_worktree_orphan`` invariant in ``_invariants.py``. That capture
    raises :class:`_invariants.WorktreeMetadataDrift` which
    ``cmd_capture`` and ``cmd_verify`` translate into a structured
    ``error: worktree_metadata_drift`` payload. Both directions refuse
    to advance under ``--strict`` so the writer-chain drift surfaced by
    lesson ``2026-05-08-14-001`` cannot run silently.

    See ``workflow-integration-git/standards/worktree-handling.md`` for the
    canonical worktree contract this assertion enforces at every phase
    boundary.
    """
    if not _is_truthy_metadata(metadata.get('use_worktree')):
        return None

    raw = metadata.get('worktree_path')
    path_str = str(raw).strip() if raw is not None else ''
    if not path_str:
        # Tri-state: in pre-materialization phases, an empty path while
        # use_worktree==true is the deferred-pending state. The worktree
        # has not been created yet and the assertion lets the boundary
        # advance. Post-materialization phases still fail loud.
        if phase in _PRE_MATERIALIZATION_PHASES:
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
        base = get_base_dir()
    except RuntimeError:
        return {}
    executor = base.parent.parent / '.plan' / 'execute-script.py'
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

    Gate: only fires when ``metadata.use_worktree`` is truthy. Plans that
    run against the main checkout (``use_worktree==false`` or absent)
    legitimately dirty main, so the invariant is not enforced there.

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
    except WorktreeMetadataDrift as exc:
        return {
            'status': 'error',
            'error': 'worktree_metadata_drift',
            'plan_id': plan_id,
            'phase': phase,
            'worktree_dir': exc.worktree_dir,
            'use_worktree': exc.use_worktree,
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


def _diffs(captured_row: dict[str, Any], observed: dict[str, Any]) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
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
            diffs.append(
                {
                    'invariant': name,
                    'captured': str(cap_value),
                    'observed': str(obs_value),
                }
            )
    return diffs


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
    except WorktreeMetadataDrift as exc:
        # Inverse-direction worktree drift: an orphan worktree directory
        # exists on disk while metadata claims no worktree is in use.
        # Surfaced as a hard error (not drift) because there is nothing
        # for the operator to compare against — the metadata is wrong.
        return {
            'status': 'error',
            'error': 'worktree_metadata_drift',
            'plan_id': plan_id,
            'phase': phase,
            'worktree_dir': exc.worktree_dir,
            'use_worktree': exc.use_worktree,
            'message': str(exc),
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

    diffs = _diffs(captured_row, observed)

    if not diffs:
        return {
            'status': 'ok',
            'plan_id': plan_id,
            'phase': phase,
            'override': captured_row.get('override', False),
        }

    result: dict[str, Any] = {
        'status': 'drift',
        'plan_id': plan_id,
        'phase': phase,
        'override': captured_row.get('override', False),
        'drift_count': len(diffs),
        'diffs': diffs,
    }
    return result


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
