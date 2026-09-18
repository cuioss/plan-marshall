#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Per-level pin and multi-target effort ladder materialization step for steward.

Reads the machine-local effort ladder (.plan/local/effort-ladder.json) or legacy
pin map and materializes per-level model pins or two-axis coordinates for targets.
The authoritative map read/write contract lives in
``marshall-steward/standards/pin-provisioning.md`` and
``doc/developer/effort-ladders.adoc``.

Behavior:
    - Reads the machine-local effort ladder at ``.plan/local/effort-ladder.json``
      (resolved main-anchored via ``resolve_main_anchored_path``) or legacy
      ``effort-pins.json``.
    - Supports multi-target Option A structure under ``targets.<target_name>``
      (e.g. ``antigravity``, ``claude``, ``opencode``) as well as legacy
      ``pins.<level>`` entries.
    - Materializes per-level pins for the requested target or open-model-set harness.
    - Preserves ``inherit`` when a level is unpinned or configured with null.
    - Enforces the never-escalate guard (never promotes a level above its
      resolved rung per ADR-021).
    - Seeds built-in defaults via ``ensure-defaults`` for ``antigravity`` (Option 1),
      ``claude`` (canonical), and ``opencode`` (inherit).
    - Emits a TOON contract. A malformed map fails closed with an error
      TOON and no partial output.
    - Guarded: ``--harness claude`` (when not using target-specific materialize)
      returns untouched without pins.

Subcommands:
    validate         Validate the ladder or map file schema. Read-only.
    materialize      Materialize per-level pins from the ladder or map file.
    ensure-defaults  Ensure default ladders are seeded into the ladder file.

Usage:
    python3 effort_pins.py validate [--map-path /path/to/effort-ladder.json] [--target antigravity]
    python3 effort_pins.py materialize [--map-path /path/to/effort-ladder.json] [--target antigravity]
    python3 effort_pins.py materialize --harness open
    python3 effort_pins.py materialize --harness claude
    python3 effort_pins.py ensure-defaults [--map-path /path/to/effort-ladder.json] [--target all]
"""

from __future__ import annotations

import argparse
import json
import os
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

ANTIGRAVITY_DEFAULT_LADDER: dict[str, dict[str, str | None]] = {
    'level-1': {'model': 'flash', 'effort': 'low'},
    'level-2': {'model': 'flash', 'effort': 'low'},
    'level-3': {'model': 'flash', 'effort': 'medium'},
    'level-4': {'model': 'flash', 'effort': 'medium'},
    'level-5': {'model': 'flash', 'effort': 'high'},
    'level-6': {'model': 'pro', 'effort': 'low'},
    'level-7': {'model': 'pro', 'effort': 'high'},
}

CLAUDE_DEFAULT_LADDER: dict[str, dict[str, str | None]] = {
    'level-1': {'model': 'haiku', 'effort': None},
    'level-2': {'model': 'sonnet', 'effort': 'medium'},
    'level-3': {'model': 'sonnet', 'effort': 'high'},
    'level-4': {'model': 'opus', 'effort': 'medium'},
    'level-5': {'model': 'opus', 'effort': 'high'},
    'level-6': {'model': 'opus', 'effort': 'xhigh'},
    'level-7': {'model': 'fable', 'effort': 'max'},
}

OPENCODE_DEFAULT_LADDER: dict[str, dict[str, str | None]] = {
    'level-1': {'model': None, 'effort': None},
    'level-2': {'model': None, 'effort': None},
    'level-3': {'model': None, 'effort': None},
    'level-4': {'model': None, 'effort': None},
    'level-5': {'model': None, 'effort': None},
    'level-6': {'model': None, 'effort': None},
    'level-7': {'model': None, 'effort': None},
}

DEFAULT_TARGET_LADDERS: dict[str, dict[str, dict[str, str | None]]] = {
    'antigravity': ANTIGRAVITY_DEFAULT_LADDER,
    'claude': CLAUDE_DEFAULT_LADDER,
    'opencode': OPENCODE_DEFAULT_LADDER,
}


def resolve_default_ladder_path() -> str:
    """Resolve the default machine-local effort ladder path.

    Checks:
    1. $PLAN_BASE_DIR/effort-ladder.json if PLAN_BASE_DIR is set.
    2. Main-anchored .plan/local/effort-ladder.json via marketplace_paths.
    3. CWD ancestor walk searching for .plan/local/effort-ladder.json.
    4. Fallback to .plan/local/effort-ladder.json relative to cwd.
    """
    if 'PLAN_BASE_DIR' in os.environ:
        return str(Path(os.environ['PLAN_BASE_DIR']) / 'effort-ladder.json')
    try:
        from marketplace_paths import resolve_main_anchored_path

        return str(resolve_main_anchored_path('effort-ladder.json'))
    except Exception:
        pass
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        local_dir = candidate / '.plan' / 'local'
        if local_dir.is_dir():
            return str(local_dir / 'effort-ladder.json')
    return str(Path('.plan/local/effort-ladder.json').resolve())


DEFAULT_LADDER_PATH: str = resolve_default_ladder_path()
DEFAULT_MAP_PATH: str = DEFAULT_LADDER_PATH


def _entry_error(level: str, reason: str) -> str:
    return f'pins.{level}: {reason}'


def validate_map_data(data: Any, target: str | None = None) -> tuple[bool, list[str]]:
    """Validate decoded map JSON. Returns (ok, errors)."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return False, ['map root must be a JSON object']

    if 'targets' in data:
        targets = data.get('targets')
        if not isinstance(targets, dict):
            return False, ["'targets' must be an object keyed by target name"]
        targets_to_check = [target] if target and target != 'all' else list(targets.keys())
        for t in targets_to_check:
            if t not in targets:
                errors.append(f"targets.{t}: target not found in 'targets'")
                continue
            ladder = targets[t]
            if not isinstance(ladder, dict):
                errors.append(f'targets.{t}: ladder must be an object keyed by level')
                continue
            for level, entry in ladder.items():
                if level not in LEVEL_RANK:
                    errors.append(f'targets.{t}.{level}: unknown level (expected one of {",".join(LEVELS)})')
                    continue
                if not isinstance(entry, dict):
                    errors.append(f'targets.{t}.{level}: entry must be an object')
                    continue
                model = entry.get('model')
                if model is not None and not isinstance(model, str):
                    errors.append(f"targets.{t}.{level}: 'model' must be a string or null")
                effort = entry.get('effort')
                if effort is not None and not isinstance(effort, str):
                    errors.append(f"targets.{t}.{level}: 'effort' must be a string or null")
                rank = entry.get('capability_rank')
                if rank is not None and (not isinstance(rank, int) or isinstance(rank, bool)):
                    errors.append(f"targets.{t}.{level}: 'capability_rank' must be an integer when present")
                kind = entry.get('kind')
                if kind is not None and kind not in ALLOWED_KINDS:
                    continue
                if kind == 'local':
                    if not isinstance(model, str) or not model:
                        errors.append(f"targets.{t}.{level}: missing required field 'model' (non-empty string)")
                if kind == 'provider':
                    ref = entry.get('route') or model
                    if not isinstance(ref, str) or not ref:
                        errors.append(
                            f"targets.{t}.{level}: missing required field 'route' (or 'model') as non-empty string"
                        )
        return (len(errors) == 0), errors

    if 'pins' in data:
        pins = data.get('pins')
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
                continue
            if kind == 'local':
                model = entry.get('model')
                if not isinstance(model, str) or not model:
                    errors.append(_entry_error(level, "missing required field 'model' (non-empty string)"))
            if kind == 'provider':
                ref = entry.get('route') or entry.get('model')
                if not isinstance(ref, str) or not ref:
                    errors.append(
                        _entry_error(level, "missing required field 'route' (or 'model') as non-empty string")
                    )
            rank = entry.get('capability_rank')
            if rank is not None and (not isinstance(rank, int) or isinstance(rank, bool)):
                errors.append(_entry_error(level, "'capability_rank' must be an integer when present"))
        return (len(errors) == 0), errors

    return False, ["map root must contain either 'targets' or 'pins'"]


def load_map_file(map_path: str) -> tuple[dict[str, Any] | None, str]:
    """Load and decode the map/ladder file. Returns (data, error_detail)."""
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


def load_ladder_file(ladder_path: str | Path) -> tuple[dict[str, Any] | None, str]:
    """Alias for load_map_file for ladder-first callers."""
    return load_map_file(str(ladder_path))


def save_ladder_file(ladder_path: str | Path, data: dict[str, Any]) -> None:
    """Write ladder JSON data with parent directory creation."""
    p = Path(ladder_path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def load_ladder(
    target: str,
    ladder_path: str | Path | None = None,
) -> tuple[dict[str, dict[str, str | None]] | None, list[str]]:
    """Load the ladder for `target` from the machine-local effort ladder JSON file.

    Returns (ladder_dict, warnings).
    If file is absent or target unconfigured, ladder_dict is None and warnings
    names the fallback to inherit.
    """
    path = str(ladder_path) if ladder_path else resolve_default_ladder_path()
    data, err = load_map_file(path)
    if data is None:
        return None, [f'ladder file not found: {path} (warning: falling back to inherit)']

    if 'targets' in data and isinstance(data['targets'], dict):
        targets = data['targets']
        if target in targets:
            ladder = targets[target]
            if isinstance(ladder, dict):
                return ladder, []
        return None, [f"target '{target}' not configured in {path} (warning: falling back to inherit)"]

    if 'pins' in data and isinstance(data['pins'], dict):
        pins = data['pins']
        legacy_ladder: dict[str, dict[str, str | None]] = {}
        for lvl in LEVELS:
            entry = pins.get(lvl)
            if isinstance(entry, dict):
                model = entry.get('model') or entry.get('route')
                legacy_ladder[lvl] = {'model': model, 'effort': None}
            else:
                legacy_ladder[lvl] = {'model': None, 'effort': None}
        return legacy_ladder, []

    return None, [f'ladder file {path} has invalid format (missing targets or pins)']


def save_ladder(
    target: str,
    ladder: dict[str, dict[str, str | None]],
    ladder_path: str | Path | None = None,
) -> None:
    """Save the ladder for `target` into the machine-local effort ladder JSON file."""
    path = str(ladder_path) if ladder_path else resolve_default_ladder_path()
    data, _ = load_map_file(path)
    if data is None or not isinstance(data, dict):
        data = {'targets': {}}
    elif 'targets' not in data or not isinstance(data['targets'], dict):
        data['targets'] = {}
    data['targets'][target] = ladder
    save_ladder_file(path, data)


def ensure_default_ladder(
    target: str | None = None,
    ladder_path: str | Path | None = None,
) -> tuple[bool, str]:
    """Ensure default ladder exists in the machine-local ladder file.

    Seeds default ladder for target (or all targets if target is None or 'all').
    Preserves existing entries without clobbering.
    Returns (modified, detail_message).
    """
    path = str(ladder_path) if ladder_path else resolve_default_ladder_path()
    data, _ = load_map_file(path)
    if data is None or not isinstance(data, dict):
        data = {'targets': {}}
    elif 'targets' not in data or not isinstance(data['targets'], dict):
        data['targets'] = {}

    targets_dict = data['targets']
    targets_to_seed = (
        [target] if target and target != 'all' else ['antigravity', 'claude', 'opencode']
    )
    modified = False
    seeded: list[str] = []

    for t in targets_to_seed:
        if t in DEFAULT_TARGET_LADDERS and t not in targets_dict:
            targets_dict[t] = dict(DEFAULT_TARGET_LADDERS[t])
            modified = True
            seeded.append(t)

    if modified:
        save_ladder_file(path, data)
        return True, f"Seeded default ladder for {', '.join(seeded)} in {path}"
    return False, f'Default ladder already present in {path}'


def materialize_levels(
    map_data: dict[str, Any],
    target: str | None = None,
) -> tuple[dict[str, str], int]:
    """Materialize per-level pins. Returns (pins, guard_hits).

    ``pins`` maps every level to either its provisioned model reference or
    ``inherit``. Narrow by construction: an entry only ever serves its own
    level. Never-escalate: an entry whose ``capability_rank`` exceeds the
    level rank falls back to ``inherit`` and counts a guard hit.
    """
    pins: dict[str, str] = {}
    guard_hits = 0

    if 'targets' in map_data and isinstance(map_data['targets'], dict):
        targets = map_data['targets']
        ladder: dict[str, Any] = {}
        if target and target in targets:
            ladder = targets[target]
        elif not target:
            for cand in ('opencode', 'open', 'antigravity'):
                if cand in targets:
                    ladder = targets[cand]
                    break
            if not ladder and targets:
                ladder = next(iter(targets.values()))
        if not isinstance(ladder, dict):
            ladder = {}
        for level in LEVELS:
            entry = ladder.get(level)
            if not isinstance(entry, dict):
                pins[level] = 'inherit'
                continue
            rank = entry.get('capability_rank')
            if isinstance(rank, int) and not isinstance(rank, bool):
                if rank > LEVEL_RANK[level]:
                    guard_hits += 1
                    pins[level] = 'inherit'
                    continue
            kind = entry.get('kind')
            if kind == 'provider':
                route = entry.get('route') or entry.get('model')
                pins[level] = str(route) if route else 'inherit'
            elif kind == 'local':
                model = entry.get('model')
                pins[level] = str(model) if model else 'inherit'
            else:
                model = entry.get('model')
                if model and model != 'inherit':
                    pins[level] = str(model)
                else:
                    pins[level] = 'inherit'
        return pins, guard_hits

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
    target = getattr(args, 'target', None)
    data, load_error = load_map_file(map_path)
    if data is None:
        return {
            'status': 'error',
            'error': 'map_unreadable',
            'detail': load_error,
            'map_path': map_path,
        }
    ok, errors = validate_map_data(data, target=target)
    if not ok:
        return {
            'status': 'error',
            'error': 'map_schema_invalid',
            'detail': '; '.join(errors),
            'map_path': map_path,
        }
    if 'targets' in data and isinstance(data['targets'], dict):
        count = sum(len(ladder) for ladder in data['targets'].values() if isinstance(ladder, dict))
    else:
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
    target = getattr(args, 'target', None)
    if harness == 'claude' and not target:
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
    ok, errors = validate_map_data(data, target=target)
    if not ok:
        return {
            'status': 'error',
            'error': 'map_schema_invalid',
            'detail': '; '.join(errors),
            'map_path': map_path,
        }
    pins, guard_hits = materialize_levels(data, target=target)
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


def cmd_ensure_defaults(args: argparse.Namespace) -> dict[str, Any]:
    map_path = str(args.map_path)
    target = getattr(args, 'target', None)
    modified, detail = ensure_default_ladder(target=target, ladder_path=map_path)
    return {
        'status': 'success',
        'modified': modified,
        'detail': detail,
        'map_path': map_path,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='effort_pins',
        description=(
            'Materialize per-level model pins from the machine-local effort-to-model map or effort ladder.'
        ),
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate the ladder/map file schema. Read-only.',
        allow_abbrev=False,
    )
    validate_parser.add_argument(
        '--map-path',
        '--ladder-path',
        dest='map_path',
        type=str,
        default=DEFAULT_MAP_PATH,
        help='Path to the machine-local pin map or effort ladder JSON file.',
    )
    validate_parser.add_argument(
        '--target',
        type=str,
        default=None,
        help='Optional target to validate specifically (e.g. antigravity, claude, opencode).',
    )

    materialize_parser = subparsers.add_parser(
        'materialize',
        help='Materialize per-level pins from the ladder/map file. Read-only emitter.',
        allow_abbrev=False,
    )
    materialize_parser.add_argument(
        '--map-path',
        '--ladder-path',
        dest='map_path',
        type=str,
        default=DEFAULT_MAP_PATH,
        help='Path to the machine-local pin map or effort ladder JSON file.',
    )
    materialize_parser.add_argument(
        '--harness',
        type=str,
        choices=('open', 'claude'),
        default='open',
        help=(
            "Harness CLASS, not a runtime.target name: 'open' covers every "
            "open-model-set harness (opencode and any future one); 'claude' is "
            'the fixed alias-palette class and returns untouched (guarded).'
        ),
    )
    materialize_parser.add_argument(
        '--target',
        type=str,
        default=None,
        help='Optional target name to materialize from targets.<target> (e.g. antigravity, claude, opencode).',
    )

    ensure_defaults_parser = subparsers.add_parser(
        'ensure-defaults',
        help='Ensure default ladders are seeded into the ladder file.',
        allow_abbrev=False,
    )
    ensure_defaults_parser.add_argument(
        '--map-path',
        '--ladder-path',
        dest='map_path',
        type=str,
        default=DEFAULT_MAP_PATH,
        help='Path to the machine-local effort ladder JSON file.',
    )
    ensure_defaults_parser.add_argument(
        '--target',
        type=str,
        default='all',
        help='Target to seed (antigravity, claude, opencode, or all).',
    )

    args = parser.parse_args(argv)

    if args.command == 'validate':
        result = cmd_validate(args)
    elif args.command == 'materialize':
        result = cmd_materialize(args)
    elif args.command == 'ensure-defaults':
        result = cmd_ensure_defaults(args)
    else:  # pragma: no cover - argparse enforces a valid subcommand
        parser.print_help()
        return 2

    from toon_parser import serialize_toon

    print(serialize_toon(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
