"""Command handlers for phase_handshake (capture, verify, list, clear)."""

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
    PhaseStepsIncomplete,
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


def _resolve_worktree_assertion(metadata: dict[str, Any]) -> dict[str, Any] | None:
    """Worktree-resolution phase-entry assertion.

    Asserts that when ``metadata.use_worktree`` is true, the
    ``metadata.worktree_path`` field is non-empty AND filesystem-resolvable
    (the directory exists AND ``git -C {path} rev-parse --show-toplevel``
    returns the same canonical path).

    Returns ``None`` when the assertion passes (use_worktree is false or
    the worktree resolves cleanly). Returns a structured TOON-shaped error
    dict when the assertion fails — callers (``cmd_capture`` / ``cmd_verify``)
    surface it verbatim and refuse to enter the phase.

    Failure cases:
        - ``use_worktree==true`` and ``worktree_path`` is missing/empty
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
                'plan-marshall:manage-status:manage_status',
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
    worktree_error = _resolve_worktree_assertion(metadata)
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


def _diffs(captured_row: dict[str, Any], observed: dict[str, Any]) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    for name, _a, _c in INVARIANTS:
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
    worktree_error = _resolve_worktree_assertion(metadata)
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
