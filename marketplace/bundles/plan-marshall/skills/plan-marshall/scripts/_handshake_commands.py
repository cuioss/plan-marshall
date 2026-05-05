"""Command handlers for phase_handshake (capture, verify, list, clear)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
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
