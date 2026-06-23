#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Summarize phase-handshake invariant values captured in a plan's handshakes.

Reads ``<plan_dir>/handshakes.toon`` (the canonical storage owned by
``plan-marshall:plan-marshall:phase_handshake``). Does NOT re-run capture —
values are whatever phase transitions already persisted.

The invariant registry lives in
``plan-marshall:plan-marshall:_invariants.py``; this script references the
same names but does not import the registry because archived plans may have
been captured by a different revision of the registry and any schema drift
should manifest as ``invariants_missing`` entries, not import failures.

``phase_steps_complete`` is **conditional**: it is only included in
``expected_invariants`` when the phase has a
``skills/phase-{phase}/standards/required-steps.md`` file in the bundle tree.
Phases that do not opt in to required-step tracking are not penalised.

Output is a deterministic TOON fragment consumed by the orchestrator and
interpreted by ``references/invariant-check-summary.md``.

Usage:
    python3 summarize-invariants.py run --plan-id EXAMPLE-PLAN --mode live
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
from marketplace_paths import find_marketplace_path  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]

# Invariants that apply to every plan. Additional invariants
# (``worktree_sha``, ``worktree_dirty``) are only recorded when the plan
# actually runs in a worktree; their absence should not be flagged.
# ``phase_steps_complete`` is omitted here — it is appended conditionally by
# ``expected_invariants`` when the phase opts in via ``required-steps.md``.
_CORE_INVARIANTS = (
    'main_sha',
    'main_dirty',
    'task_state_hash',
    'qgate_open_count',
    'config_hash',
    'unfinished_tasks_count',
)

_WORKTREE_INVARIANTS = ('worktree_sha', 'worktree_dirty')

# Columns in handshakes.toon that are row-level metadata, not invariant values.
_NON_INVARIANT_COLUMNS = frozenset(
    {
        'phase',
        'captured_at',
        'override',
        'override_reason',
    }
)

HANDSHAKE_FILE = 'handshakes.toon'


def _phase_at_or_after_execute(phase: str | None) -> bool:
    """Return ``True`` when ``phase`` is at or after ``5-execute``.

    Parses the leading integer of the ``N-name`` phase string (e.g.
    ``5-execute`` -> ``5``) and returns ``int(prefix) >= 5``. Under the
    ADR-002 deferred-materialization model the worktree is not created until
    phase-5-execute, so worktree invariants cannot be expected from the plan's
    metadata before then.

    Returns ``False`` for ``phase is None`` or any unparseable prefix: when the
    phase ordinal cannot be proven to be at or after 5, the worktree cannot be
    proven materialized, so worktree invariants are NOT expected.
    """
    if phase is None:
        return False
    prefix = phase.split('-', 1)[0]
    try:
        return int(prefix) >= 5
    except ValueError:
        return False


def _phase_steps_complete_applies(phase: str) -> bool:
    """Return ``True`` when the phase opts in to required-step tracking.

    Resolution rule mirrors ``_invariants._resolve_required_steps_path``:
    the file ``marketplace/bundles/plan-marshall/skills/phase-{phase}/
    standards/required-steps.md`` must exist relative to the bundle root.
    Returns ``False`` when the marketplace root cannot be located or the
    file is absent, so phases that have not opted in are not penalised.

    Resolved independently — does not import ``_invariants.py`` to keep
    the no-import-from-registry contract documented in the module docstring.
    """
    bundles = find_marketplace_path()
    if bundles is None:
        return False
    candidate = (
        bundles / 'plan-marshall' / 'skills' / f'phase-{phase}' / 'standards' / 'required-steps.md'
    )
    return candidate.is_file()


def resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    if mode == 'live':
        if not plan_id:
            raise ValueError('--plan-id is required for live mode')
        return base_path('plans', plan_id)
    if mode == 'archived':
        if not archived_plan_path:
            raise ValueError('--archived-plan-path is required for archived mode')
        return Path(archived_plan_path)
    raise ValueError(f'Unknown mode: {mode!r}')


def load_status_metadata(plan_dir: Path) -> dict[str, Any]:
    """Used solely to detect ``worktree_path`` so worktree-only invariants are
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


def expected_invariants(
    metadata: dict[str, Any],
    phase: str | None = None,
    phase_values: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    """Return the tuple of invariants expected for this plan and phase.

    Worktree-only invariants are included when the worktree can be proven
    materialized for this phase. Two signals decide this — the captured row's
    values come first, the plan's current metadata is the phase-gated fallback:

    1. If ``phase_values`` carries a non-empty ``worktree_sha`` OR
       ``worktree_dirty`` value, the row itself proves the worktree was
       materialized when the phase captured. Include
       ``_WORKTREE_INVARIANTS`` (unconditional — independent of ``phase``).
    2. Otherwise, if the phase is at or after ``5-execute`` AND the plan's
       current metadata reports ``use_worktree`` (a non-empty
       ``worktree_path`` once phase-5 materializes the worktree), the plan is
       worktree-routed and an empty captured value represents a real capture
       gap. Include ``_WORKTREE_INVARIANTS``. Under the ADR-002 deferred-
       materialization model the worktree is not created until phase-5-execute,
       so phases 1-4 never capture worktree values; Signal 2 is gated off there
       (and for the un-phased default where ``phase is None``) to avoid a
       guaranteed false-positive "missing worktree invariant" finding.

    ``phase_steps_complete`` is appended only when ``phase`` is provided
    and ``_phase_steps_complete_applies(phase)`` returns ``True`` — i.e.
    the phase has opted in via a ``standards/required-steps.md`` file.
    When ``phase`` is ``None`` (the no-handshakes fallback path), the
    invariant is omitted.
    """
    base: tuple[str, ...] = _CORE_INVARIANTS

    include_worktree = False
    if isinstance(phase_values, dict):
        # Signal 1: the captured row carries a worktree value.
        for key in _WORKTREE_INVARIANTS:
            value = phase_values.get(key)
            if value not in (None, ''):
                include_worktree = True
                break
    if (
        not include_worktree
        and _phase_at_or_after_execute(phase)
        and (metadata.get('worktree_path') or metadata.get('use_worktree'))
    ):
        # Signal 2: the plan is worktree-routed AND the phase is at or after
        # 5-execute, so the worktree is materialized → an empty captured value
        # is a real capture gap. Phases 1-4 (and the un-phased default) never
        # capture worktree values under ADR-002 deferred materialization, so
        # the signal is gated off there to avoid a false-positive finding.
        include_worktree = True

    if include_worktree:
        base = base + _WORKTREE_INVARIANTS
    if phase is not None and _phase_steps_complete_applies(phase):
        base = base + ('phase_steps_complete',)
    return base


def detect_drift(phase_map: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    """Detect invariant value drift across phases.

    Emits a drift entry whenever a named invariant's value changes between
    consecutive phases in declaration order. ``main_dirty`` /
    ``worktree_dirty`` / ``qgate_open_count`` / ``unfinished_tasks_count`` are
    excluded — they naturally vary as work progresses.
    """
    excluded = {'main_dirty', 'worktree_dirty', 'qgate_open_count', 'unfinished_tasks_count'}
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
                drift.append(
                    {
                        'invariant': invariant,
                        'from_phase': prev_phase,
                        'to_phase': phase,
                        'detail': f'{prev_value!s} -> {value!s}',
                    }
                )
            prev_phase = phase
            prev_value = value
    return drift


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    metadata = load_status_metadata(plan_dir)
    rows = load_handshake_rows(plan_dir)
    # Un-phased default used only for the no-handshakes-found path where there
    # is no phase to pass; per-phase expected sets are computed inside the loop.
    default_expected = expected_invariants(metadata)

    phases_out: list[dict[str, Any]] = []
    findings: list[dict[str, str]] = []

    if rows is None or not rows:
        findings.append(
            {
                'severity': 'warning',
                'invariant': 'phase_handshake',
                'message': 'No handshakes.toon found',
            }
        )
        phase_map: dict[str, dict[str, Any]] = {}
    else:
        phase_map = project_rows_to_phase_map(rows)

    for phase, values in phase_map.items():
        expected = expected_invariants(metadata, phase, values)
        present = sorted(k for k, v in values.items() if v not in (None, ''))
        missing = sorted(set(expected) - set(present))
        phases_out.append(
            {
                'phase': phase,
                'invariants_present': present,
                'invariants_missing': missing,
            }
        )
        for invariant in missing:
            # Worktree-only invariants missing on non-worktree plans are
            # filtered out by ``expected``; anything that survives is a real
            # gap.
            findings.append(
                {
                    'severity': 'error',
                    'invariant': invariant,
                    'message': f'Phase {phase} missing invariant {invariant}',
                }
            )

    drift = detect_drift(phase_map)
    for entry in drift:
        findings.append(
            {
                'severity': 'warning',
                'invariant': entry['invariant'],
                'message': f'{entry["invariant"]} drift {entry["from_phase"]} -> {entry["to_phase"]}: {entry["detail"]}',
            }
        )

    return {
        'status': 'success',
        'aspect': 'invariant_summary',
        'plan_id': args.plan_id or plan_dir.name,
        'phases': phases_out,
        'drift': drift,
        'findings': findings,
        'expected_invariants': list(default_expected),
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
