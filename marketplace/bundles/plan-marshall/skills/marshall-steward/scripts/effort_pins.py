#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Per-level pin materialization step for the steward menu.

Reads the machine-local effort-to-model pin map and materializes per-level
model pins for open-model-set harnesses. The authoritative map read/write
contract lives in ``marshall-steward/standards/pin-provisioning.md`` — see
that standard instead of re-deriving the path heuristic, entry-kind
vocabulary, or guard table here.

Behavior:
    - Reads the machine-local pin map at the PLAN-01 resolved path
      (entry kinds ``local`` and ``provider``).
    - Materializes per-level pins for the active harness — open-model-set
      harnesses only.
    - Preserves ``inherit`` when a level is unpinned.
    - Enforces the never-escalate guard (never promotes a level above its
      resolved rung per ADR-021).
    - Emits a TOON contract. A malformed map fails closed with an error
      TOON and no partial output.
    - The Claude target fixed alias-palette flow is never touched (guarded:
      ``--harness claude`` returns untouched without pins).

Subcommands:
    validate      Validate the map file schema. Read-only.
    materialize   Materialize per-level pins from the map file. Read-only
                  emitter — the caller applies pins through the existing
                  ``manage-config effort`` surface; this script writes
                  nothing itself.

Usage:
    python3 effort_pins.py validate --map-path /path/to/effort-pins.json
    python3 effort_pins.py materialize --map-path /path/to/effort-pins.json --harness open
    python3 effort_pins.py materialize --map-path /path/to/effort-pins.json --harness claude

Output (TOON format):
    validate subcommand:
        status	success
        valid	true
        entries	2
        map_path	/path/to/effort-pins.json

        status	error
        error	map_schema_invalid
        detail	<pins.level-2: missing required field 'model'>
        map_path	/path/to/effort-pins.json

    materialize subcommand (open harness):
        status	success
        harness	open
        materialized_count	2
        inherit_count	5
        guard_hits	0
        pins	level-1=inherit,level-2=local-model-a,level-3=inherit,level-4=provider-route-z,level-5=inherit,level-6=inherit,level-7=inherit
        map_path	/path/to/effort-pins.json

    materialize subcommand (claude harness, guarded):
        status	success
        harness	claude
        untouched	true
        detail	Claude target fixed alias-palette flow is untouched; pin materialization applies to open-model-set harnesses only
        map_path	/path/to/effort-pins.json

    materialize subcommand (malformed map, fail-closed):
        status	error
        error	map_schema_invalid
        detail	<reason>
        map_path	/path/to/effort-pins.json

Exit 0 on success, 2 on argparse rejection. Schema failures return
``status: error`` with exit 0 — the TOON payload carries the verdict,
not the process exit code.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

LEVELS: tuple[str, ...] = (
    'level-1',
    'level-2',
    'level-3',
    'level-4',
    'level-5',
    'level-6',
    'level-7',
)

LEVEL_RANK: dict[str, int] = {level: index for index, level in enumerate(LEVELS)}

ALLOWED_KINDS: tuple[str, ...] = ('local', 'provider')

DEFAULT_MAP_PATH: str = str(Path.home() / '.config' / 'plan-marshall' / 'effort-pins.json')


def _entry_error(level: str, reason: str) -> str:
    return f'pins.{level}: {reason}'


def validate_map_data(data: Any) -> tuple[bool, list[str]]:
    """Validate decoded map JSON. Returns (ok, errors)."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return False, ['map root must be a JSON object']
    pins = data.get('pins', {})
    if not isinstance(pins, dict):
        return False, ["'pins' must be an object keyed by level"]
    for level, entry in pins.items():
        if level not in LEVEL_RANK:
            errors.append(f'pins.{level}: unknown level (expected one of {",".join(LEVELS)})')
            continue
        if not isinstance(entry, dict):
            errors.append(_entry_error(level, 'entry must be an object'))
            continue
        kind = entry.get('kind')
        if kind not in ALLOWED_KINDS:
            # Per pin-provisioning.md and ADR-021 obligation 1: an entry
            # without a usable kind is unprovisioned, exactly as an absent
            # entry is — the level resolves to inherit at materialize
            # time instead of failing the whole map.
            continue
        if kind == 'local':
            model = entry.get('model')
            if not isinstance(model, str) or not model:
                errors.append(_entry_error(level, "missing required field 'model' (non-empty string)"))
        if kind == 'provider':
            ref = entry.get('route') or entry.get('model')
            if not isinstance(ref, str) or not ref:
                errors.append(_entry_error(level, "missing required field 'route' (or 'model') as non-empty string"))
        rank = entry.get('capability_rank')
        if rank is not None and (not isinstance(rank, int) or isinstance(rank, bool)):
            errors.append(_entry_error(level, "'capability_rank' must be an integer when present"))
    return (len(errors) == 0), errors


def load_map_file(map_path: str) -> tuple[dict[str, Any] | None, str]:
    """Load and decode the map file. Returns (data, error_detail)."""
    try:
        text = Path(map_path).expanduser().read_text(encoding='utf-8')
    except FileNotFoundError:
        return None, f'map file not found: {map_path}'
    except OSError as exc:
        return None, f'map file unreadable: {exc}'
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f'map file is not valid JSON: {exc}'
    return data, ''


def materialize_levels(map_data: dict[str, Any]) -> tuple[dict[str, str], int]:
    """Materialize per-level pins. Returns (pins, guard_hits).

    ``pins`` maps every level to either its provisioned model reference or
    ``inherit``. Narrow by construction: an entry only ever serves its own
    level. Never-escalate: an entry whose ``capability_rank`` exceeds the
    level rank falls back to ``inherit`` and counts a guard hit.
    """
    pins: dict[str, str] = {}
    guard_hits = 0
    entries = map_data.get('pins', {})
    if not isinstance(entries, dict):
        entries = {}
    for level in LEVELS:
        entry = entries.get(level)
        if not isinstance(entry, dict):
            pins[level] = 'inherit'
            continue
        kind = entry.get('kind')
        if kind not in ALLOWED_KINDS:
            pins[level] = 'inherit'
            continue
        rank = entry.get('capability_rank')
        if isinstance(rank, int) and not isinstance(rank, bool):
            if rank > LEVEL_RANK[level]:
                guard_hits += 1
                pins[level] = 'inherit'
                continue
        if kind == 'local':
            model = entry.get('model')
            pins[level] = str(model) if model else 'inherit'
        else:
            route = entry.get('route') or entry.get('model')
            pins[level] = str(route) if route else 'inherit'
    return pins, guard_hits


def _pins_to_string(pins: dict[str, str]) -> str:
    return ','.join(f'{level}={pins[level]}' for level in LEVELS)


def cmd_validate(args: argparse.Namespace) -> dict[str, Any]:
    map_path = str(args.map_path)
    data, load_error = load_map_file(map_path)
    if data is None:
        return {
            'status': 'error',
            'error': 'map_unreadable',
            'detail': load_error,
            'map_path': map_path,
        }
    ok, errors = validate_map_data(data)
    if not ok:
        return {
            'status': 'error',
            'error': 'map_schema_invalid',
            'detail': '; '.join(errors),
            'map_path': map_path,
        }
    pins = data.get('pins', {})
    count = len(pins) if isinstance(pins, dict) else 0
    return {
        'status': 'success',
        'valid': True,
        'entries': count,
        'map_path': map_path,
    }


def cmd_materialize(args: argparse.Namespace) -> dict[str, Any]:
    map_path = str(args.map_path)
    harness = str(args.harness)
    if harness == 'claude':
        return {
            'status': 'success',
            'harness': 'claude',
            'untouched': True,
            'detail': (
                'Claude target fixed alias-palette flow is untouched; '
                'pin materialization applies to open-model-set harnesses only'
            ),
            'map_path': map_path,
        }
    data, load_error = load_map_file(map_path)
    if data is None:
        return {
            'status': 'error',
            'error': 'map_unreadable',
            'detail': load_error,
            'map_path': map_path,
        }
    ok, errors = validate_map_data(data)
    if not ok:
        return {
            'status': 'error',
            'error': 'map_schema_invalid',
            'detail': '; '.join(errors),
            'map_path': map_path,
        }
    pins, guard_hits = materialize_levels(data)
    materialized = sum(1 for level in LEVELS if pins[level] != 'inherit')
    return {
        'status': 'success',
        'harness': harness,
        'materialized_count': materialized,
        'inherit_count': len(LEVELS) - materialized,
        'guard_hits': guard_hits,
        'pins': _pins_to_string(pins),
        'map_path': map_path,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='effort_pins',
        description=(
            'Materialize per-level model pins from the machine-local effort-to-model map for open-model-set harnesses.'
        ),
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate the map file schema. Read-only.',
        allow_abbrev=False,
    )
    validate_parser.add_argument(
        '--map-path',
        type=str,
        default=DEFAULT_MAP_PATH,
        help='Path to the machine-local pin map JSON file.',
    )

    materialize_parser = subparsers.add_parser(
        'materialize',
        help='Materialize per-level pins from the map file. Read-only emitter.',
        allow_abbrev=False,
    )
    materialize_parser.add_argument(
        '--map-path',
        type=str,
        default=DEFAULT_MAP_PATH,
        help='Path to the machine-local pin map JSON file.',
    )
    materialize_parser.add_argument(
        '--harness',
        type=str,
        choices=('open', 'claude'),
        default='open',
        help="Active harness. 'claude' returns untouched (guarded).",
    )

    args = parser.parse_args(argv)

    if args.command == 'validate':
        result = cmd_validate(args)
    elif args.command == 'materialize':
        result = cmd_materialize(args)
    else:  # pragma: no cover - argparse enforces a valid subcommand
        parser.print_help()
        return 2

    from toon_parser import serialize_toon

    print(serialize_toon(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
