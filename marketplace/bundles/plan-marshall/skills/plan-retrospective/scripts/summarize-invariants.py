#!/usr/bin/env python3
"""Summarize phase-handshake invariant values captured in a plan's handshakes.

Reads ``<plan_dir>/handshakes.toon`` (the canonical storage owned by
``plan-marshall:plan-marshall:phase_handshake``). Does NOT re-run capture —
values are whatever phase transitions already persisted.

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
from input_validation import (  # type: ignore[import-not-found]
    add_plan_id_arg,
    parse_args_with_toon_errors,
)
from toon_parser import parse_toon  # type: ignore[import-not-found]

# Invariants that apply to every plan. Additional invariants
# (``worktree_sha``, ``worktree_dirty``) are only recorded when the plan
# actually runs in a worktree; their absence should not be flagged.
_CORE_INVARIANTS = (
    'main_sha',
    'main_dirty',
    'task_state_hash',
    'qgate_open_count',
    'config_hash',
    'pending_tasks_count',
    'phase_steps_complete',
)

_WORKTREE_INVARIANTS = ('worktree_sha', 'worktree_dirty')

# Columns in handshakes.toon that are row-level metadata, not invariant values.
_NON_INVARIANT_COLUMNS = frozenset({
    'phase',
    'captured_at',
    'worktree_applicable',
    'override',
    'override_reason',
})

HANDSHAKE_FILE = 'handshakes.toon'


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


def load_status_metadata(plan_dir: Path) -> dict[str, Any]:
    """Load ``metadata`` from ``status.json`` (or return an empty dict on error).

    Used solely to detect ``worktree_path`` so worktree-only invariants are
    expected for worktree plans.
    """
    json_path = plan_dir / 'status.json'
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                metadata = data.get('metadata')
                if isinstance(metadata, dict):
                    return metadata
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def load_handshake_rows(plan_dir: Path) -> list[dict[str, Any]] | None:
    """Read and parse ``<plan_dir>/handshakes.toon``.

    Returns ``None`` when the file is absent — callers translate that into the
    canonical ``No handshakes.toon found`` warning. Returns an empty list when
    the file exists but contains zero rows (e.g. capture ran but every row was
    cleared); callers also surface that as the missing-data warning since the
    retrospective has no per-phase data to summarize either way.
    """
    path = plan_dir / HANDSHAKE_FILE
    if not path.exists():
        return None
    try:
        parsed = parse_toon(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    rows = parsed.get('handshakes') or []
    if not isinstance(rows, list):
        return []
    return [r for r in rows if isinstance(r, dict)]


def project_rows_to_phase_map(
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Project handshake rows into the legacy ``phase → {name: value}`` shape.

    Strips row-level metadata columns (``captured_at``, ``override`` etc.) and
    drops empty-string values so ``invariants_present`` only lists invariants
    that actually captured a value (matching the previous behaviour where
    ``invariants_missing`` flagged unset invariants).
    """
    phase_map: dict[str, dict[str, Any]] = {}
    for row in rows:
        phase = row.get('phase')
        if not isinstance(phase, str) or not phase:
            continue
        values: dict[str, Any] = {}
        for key, value in row.items():
            if key in _NON_INVARIANT_COLUMNS:
                continue
            if value is None or value == '':
                continue
            values[key] = value
        phase_map[phase] = values
    return phase_map


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
    ``worktree_dirty`` / ``qgate_open_count`` / ``pending_tasks_count`` are
    excluded — they naturally vary as work progresses.
    """
    excluded = {'main_dirty', 'worktree_dirty', 'qgate_open_count', 'pending_tasks_count'}
    # Preserve insertion order — it matches handshakes.toon row order.
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
    metadata = load_status_metadata(plan_dir)
    rows = load_handshake_rows(plan_dir)
    expected = expected_invariants(metadata)

    phases_out: list[dict[str, Any]] = []
    findings: list[dict[str, str]] = []

    if rows is None or not rows:
        findings.append({
            'severity': 'warning',
            'invariant': 'phase_handshake',
            'message': 'No handshakes.toon found',
        })
        phase_map: dict[str, dict[str, Any]] = {}
    else:
        phase_map = project_rows_to_phase_map(rows)

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
    add_plan_id_arg(run_parser, required=False)
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

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()  # type: ignore[no-untyped-call]
