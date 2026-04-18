#!/usr/bin/env python3
"""Summarize phase-handshake invariant values captured in a plan's status.

Reads ``status.metadata.phase_handshake`` (or the legacy
``status.metadata.invariants`` key) from the plan's ``status.json``. Does NOT
re-run capture — values are whatever phase transitions already persisted.

The invariant registry lives in
``plan-marshall:plan-marshall:_invariants.py``; this script references the
same names but does not import the registry because archived plans may have
been captured by a different revision of the registry and any schema drift
should manifest as ``invariants_missing`` entries, not import failures.

Output is a deterministic TOON fragment consumed by the orchestrator and
interpreted by ``references/invariant-check-summary.md``.

Usage:
    python3 summarize-invariants.py run --plan-id my-plan --mode live
    python3 summarize-invariants.py run --archived-plan-path /abs --mode archived
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from file_ops import base_path, output_toon, safe_main  # type: ignore[import-not-found]

# Invariants that apply to every plan. Additional invariants
# (``worktree_sha``, ``worktree_dirty``) are only recorded when the plan
# actually runs in a worktree; their absence should not be flagged.
_CORE_INVARIANTS = (
    'main_sha',
    'main_dirty',
    'task_state_hash',
    'qgate_open_count',
    'config_hash',
    'phase_steps_complete',
)

_WORKTREE_INVARIANTS = ('worktree_sha', 'worktree_dirty')


def resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    if mode == 'live':
        if not plan_id:
            raise ValueError('--plan-id is required for live mode')
        return base_path('plans', plan_id)
    if mode == 'archived':
        if not archived_plan_path:
            raise ValueError('--archived-plan-path is required for archived mode')
        return Path(archived_plan_path)
    raise ValueError(f"Unknown mode: {mode!r}")


def load_status(plan_dir: Path) -> dict[str, Any]:
    """Load ``status.json`` (or return an empty dict on error).

    ``status.toon`` is the legacy TOON-serialized variant; status.json is the
    canonical JSON form and is always written by ``manage-status`` post
    PR #171. Callers tolerate either.
    """
    json_path = plan_dir / 'status.json'
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def extract_phase_map(status: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract per-phase invariant rows from ``metadata``.

    Supports two storage shapes:
    - ``metadata.phase_handshake`` — post-handshake layout, a dict keyed by
      phase name whose value is a dict of ``invariant_name -> value``.
    - ``metadata.invariants`` — legacy layout with the same shape.

    Returns ``{}`` when neither key is present.
    """
    metadata = status.get('metadata') or {}
    if not isinstance(metadata, dict):
        return {}
    for key in ('phase_handshake', 'invariants'):
        raw = metadata.get(key)
        if isinstance(raw, dict) and raw:
            return {
                phase: (values if isinstance(values, dict) else {})
                for phase, values in raw.items()
            }
    return {}


def expected_invariants(metadata: dict[str, Any]) -> tuple[str, ...]:
    """Return the tuple of invariants expected for this plan.

    Worktree-only invariants are included whenever the plan has a
    ``worktree_path`` recorded in its metadata.
    """
    if isinstance(metadata, dict) and metadata.get('worktree_path'):
        return _CORE_INVARIANTS + _WORKTREE_INVARIANTS
    return _CORE_INVARIANTS


def detect_drift(phase_map: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    """Detect invariant value drift across phases.

    Emits a drift entry whenever a named invariant's value changes between
    consecutive phases in declaration order. ``main_dirty`` /
    ``worktree_dirty`` are excluded — they naturally vary as work progresses.
    """
    excluded = {'main_dirty', 'worktree_dirty', 'qgate_open_count'}
    # Preserve insertion order — it matches phase_handshake insertion order.
    phases = list(phase_map.keys())
    if len(phases) < 2:
        return []

    drift: list[dict[str, str]] = []
    for invariant in sorted({name for values in phase_map.values() for name in values}):
        if invariant in excluded:
            continue
        prev_value: Any = None
        prev_phase: str | None = None
        for phase in phases:
            value = phase_map[phase].get(invariant)
            if value is None or value == '':
                continue
            if prev_phase is not None and prev_value != value:
                drift.append({
                    'invariant': invariant,
                    'from_phase': prev_phase,
                    'to_phase': phase,
                    'detail': f'{prev_value!s} -> {value!s}',
                })
            prev_phase = phase
            prev_value = value
    return drift


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    status = load_status(plan_dir)
    raw_metadata = status.get('metadata')
    metadata: dict[str, Any] = raw_metadata if isinstance(raw_metadata, dict) else {}
    phase_map = extract_phase_map(status)
    expected = expected_invariants(metadata)

    phases_out: list[dict[str, Any]] = []
    findings: list[dict[str, str]] = []

    if not phase_map:
        findings.append({
            'severity': 'warning',
            'invariant': 'phase_handshake',
            'message': 'No phase_handshake data in status.metadata',
        })

    for phase, values in phase_map.items():
        present = sorted(k for k, v in values.items() if v not in (None, ''))
        missing = sorted(set(expected) - set(present))
        phases_out.append({
            'phase': phase,
            'invariants_present': present,
            'invariants_missing': missing,
        })
        for invariant in missing:
            # Worktree-only invariants missing on non-worktree plans are
            # filtered out by ``expected``; anything that survives is a real
            # gap.
            findings.append({
                'severity': 'error',
                'invariant': invariant,
                'message': f'Phase {phase} missing invariant {invariant}',
            })

    drift = detect_drift(phase_map)
    for entry in drift:
        findings.append({
            'severity': 'warning',
            'invariant': entry['invariant'],
            'message': f'{entry["invariant"]} drift {entry["from_phase"]} -> {entry["to_phase"]}: {entry["detail"]}',
        })

    return {
        'status': 'success',
        'aspect': 'invariant_summary',
        'plan_id': args.plan_id or plan_dir.name,
        'phases': phases_out,
        'drift': drift,
        'findings': findings,
        'expected_invariants': list(expected),
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Summarize captured invariants from a plan',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser('run', help='Summarize invariants', allow_abbrev=False)
    run_parser.add_argument('--plan-id', help='Plan identifier (live mode)')
    run_parser.add_argument(
        '--archived-plan-path',
        help='Absolute path to archived plan directory (archived mode)',
    )
    run_parser.add_argument(
        '--mode',
        choices=['live', 'archived'],
        required=True,
        help='Resolution mode',
    )
    run_parser.set_defaults(func=cmd_run)

    args = parser.parse_args()
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()  # type: ignore[no-untyped-call]
