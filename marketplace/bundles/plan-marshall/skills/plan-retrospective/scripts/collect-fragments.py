#!/usr/bin/env python3
"""Assemble per-aspect TOON fragments into a bundle consumed by compile-report.

This is a stateful helper for ``plan-retrospective``: the orchestrator captures
each aspect's output as a TOON fragment file, then registers it via ``add`` so
that ``compile-report run --fragments-file`` can consume a single bundle.

Subcommands:
    init      Create an empty TOON bundle at the mode-appropriate path.
    add       Merge a fragment file into the bundle under the aspect key.
    finalize  Report the bundle path and its registered aspects.

Bundle location:
    live      ``<plan_dir>/work/retro-fragments.toon`` (inside the plan dir).
    archived  ``<OS tmpdir>/plan-retrospective/retro-fragments-<plan_id>.toon``
              (kept outside the archived plan dir so audits never mutate the
              archive).

All subcommands emit TOON output via ``serialize_toon`` and follow the
execute-script executor contract (@safe_main, ``--help`` on every subparser,
kebab-case flags).
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Any

from file_ops import (  # type: ignore[import-not-found]
    atomic_write_file,
    base_path,
    output_toon,
    safe_main,
)
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]

_ARCHIVED_TMP_SUBDIR = 'plan-retrospective'
_META_KEY = '_meta'


def resolve_bundle_path(mode: str, plan_id: str, archived_plan_path: str | None = None) -> Path:
    """Return the bundle path for the given mode.

    Args:
        mode: Either ``'live'`` or ``'archived'``.
        plan_id: Plan identifier. Required for both modes (archived mode uses
            it to disambiguate bundles for concurrent retrospectives).
        archived_plan_path: Accepted for API symmetry with ``compile-report``
            but intentionally ignored — archived bundles live in the OS tmp
            dir so archived plan directories stay read-only during audits.

    Returns:
        Absolute path to the bundle file.

    Raises:
        ValueError: On unknown ``mode`` or missing ``plan_id``.
    """
    if not plan_id:
        raise ValueError('--plan-id is required')
    if mode == 'live':
        return base_path('plans', plan_id) / 'work' / 'retro-fragments.toon'
    if mode == 'archived':
        # ``archived_plan_path`` is accepted for call-site symmetry with
        # compile-report, but not used: archived bundles stay in the OS tmp
        # dir so audits never touch the archived plan directory. Referencing
        # the arg keeps linters happy and documents the intent.
        _ = archived_plan_path
        tmp_root = Path(tempfile.gettempdir()) / _ARCHIVED_TMP_SUBDIR
        return tmp_root / f'retro-fragments-{plan_id}.toon'
    raise ValueError(f'Unknown mode: {mode!r}')


def _read_bundle(bundle_path: Path) -> dict[str, Any]:
    """Read and validate the bundle file.

    Args:
        bundle_path: Path to the bundle file.

    Returns:
        Parsed bundle dict. Empty dict when file is empty.

    Raises:
        ValueError: When the bundle file is missing or not a top-level dict.
    """
    if not bundle_path.exists():
        raise ValueError(f'Bundle file does not exist: {bundle_path}')
    content = bundle_path.read_text(encoding='utf-8')
    if not content.strip():
        return {}
    try:
        parsed = parse_toon(content)
    except Exception as exc:
        raise ValueError(f'Failed to parse bundle TOON at {bundle_path}: {exc}') from exc
    if not isinstance(parsed, dict):
        raise ValueError(f'Bundle TOON must be a top-level dict, got {type(parsed).__name__}')
    return parsed


def _read_fragment(fragment_path: Path) -> Any:
    """Read and parse a fragment TOON file.

    Args:
        fragment_path: Path to the fragment file.

    Returns:
        Parsed fragment value (typically a dict).

    Raises:
        ValueError: When the fragment is missing or fails to parse.
    """
    if not fragment_path.exists():
        raise ValueError(f'Fragment file does not exist: {fragment_path}')
    content = fragment_path.read_text(encoding='utf-8')
    if not content.strip():
        raise ValueError(f'Fragment file is empty: {fragment_path}')
    try:
        return parse_toon(content)
    except Exception as exc:
        raise ValueError(f'Failed to parse fragment TOON at {fragment_path}: {exc}') from exc


def _write_bundle(bundle_path: Path, bundle: dict[str, Any]) -> None:
    """Serialize ``bundle`` to TOON and write it atomically.

    After ``init`` the bundle is seeded with a ``_meta`` entry recording the
    resolution mode (e.g. ``_meta: mode: live``), so it is never literally
    empty on disk. An empty dict would still serialize to an empty string,
    but that code path is retained only for defensive symmetry — production
    callers always pass at least the ``_meta`` seed. The bundle is a
    transient internal artifact consumed only by ``compile-report run``
    (which reads and parses it via ``parse_toon``); no shell consumer runs
    ``test -s`` against it.
    """
    content = serialize_toon(bundle) if bundle else ''
    atomic_write_file(bundle_path, content)


def _read_mode_from_bundle(bundle: dict[str, Any], bundle_path: Path) -> str:
    """Return the persisted resolution mode from the bundle's ``_meta`` block.

    Args:
        bundle: Parsed bundle dict (as returned by ``_read_bundle``).
        bundle_path: Source path for the bundle, included in error messages
            so callers can trace which artifact is malformed.

    Returns:
        The mode string (``'live'`` or ``'archived'``).

    Raises:
        ValueError: When ``_meta.mode`` is missing — indicates the bundle
            was created by an incompatible ``init`` (pre-persisted-mode or
            hand-crafted) and cannot be used by ``add``/``finalize``.
    """
    meta = bundle.get(_META_KEY)
    if not isinstance(meta, dict) or 'mode' not in meta:
        raise ValueError(
            f'Bundle missing _meta.mode — was it created by a compatible '
            f'init? bundle_path={bundle_path}'
        )
    return str(meta['mode'])


def cmd_init(args: argparse.Namespace) -> dict[str, Any]:
    """Create (or overwrite) a bundle file seeded with the resolution mode."""
    bundle_path = resolve_bundle_path(args.mode, args.plan_id, args.archived_plan_path)
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    _write_bundle(bundle_path, {_META_KEY: {'mode': args.mode}})
    return {
        'status': 'success',
        'operation': 'init',
        'plan_id': args.plan_id,
        'mode': args.mode,
        'bundle_path': str(bundle_path),
    }


def _locate_bundle(args: argparse.Namespace) -> Path:
    """Probe live then archived candidate paths; return the first that exists.

    Returns the ``live`` path when neither exists so ``_read_bundle`` raises
    a consistent "Bundle file does not exist" error.
    """
    live_path = resolve_bundle_path('live', args.plan_id, args.archived_plan_path)
    if live_path.exists():
        return live_path
    archived_path = resolve_bundle_path('archived', args.plan_id, args.archived_plan_path)
    if archived_path.exists():
        return archived_path
    return live_path


def cmd_add(args: argparse.Namespace) -> dict[str, Any]:
    """Merge a fragment file into the bundle under the given aspect key."""
    aspect = args.aspect
    if not aspect:
        raise ValueError('--aspect is required')
    if aspect.startswith('_'):
        raise ValueError(
            'Reserved aspect key: keys starting with "_" are internal metadata'
        )

    bundle_path = _locate_bundle(args)
    bundle = _read_bundle(bundle_path)
    mode = _read_mode_from_bundle(bundle, bundle_path)

    # Sanity guard: the path we found the bundle at must match the path the
    # persisted mode resolves to. A mismatch means the bundle was moved or
    # hand-crafted with a contradictory _meta.mode.
    expected_path = resolve_bundle_path(mode, args.plan_id, args.archived_plan_path)
    if bundle_path.resolve() != expected_path.resolve():
        raise ValueError(
            f'Bundle path mismatch: found at {bundle_path} but _meta.mode='
            f'{mode!r} resolves to {expected_path}'
        )

    already_present = aspect in bundle
    if already_present and not args.overwrite:
        return {
            'status': 'error',
            'operation': 'add',
            'plan_id': args.plan_id,
            'aspect': aspect,
            'bundle_path': str(bundle_path),
            'error': f'Aspect already registered: {aspect!r}. Pass --overwrite to replace.',
        }

    fragment = _read_fragment(Path(args.fragment_file))
    bundle[aspect] = fragment
    _write_bundle(bundle_path, bundle)

    return {
        'status': 'success',
        'operation': 'add',
        'plan_id': args.plan_id,
        'aspect': aspect,
        'bundle_path': str(bundle_path),
        'aspects': sorted(k for k in bundle.keys() if not k.startswith('_')),
        'overwrote': already_present,
    }


def cmd_finalize(args: argparse.Namespace) -> dict[str, Any]:
    """Return the bundle path and aspect list for hand-off to compile-report."""
    bundle_path = _locate_bundle(args)
    bundle = _read_bundle(bundle_path)
    mode = _read_mode_from_bundle(bundle, bundle_path)
    aspects = sorted(k for k in bundle.keys() if not k.startswith('_'))
    return {
        'status': 'success',
        'operation': 'finalize',
        'plan_id': args.plan_id,
        'mode': mode,
        'bundle_path': str(bundle_path),
        'aspects': aspects,
        'aspect_count': len(aspects),
    }


def _add_init_args(parser: argparse.ArgumentParser) -> None:
    """Attach flags for ``init``: ``--plan-id``, ``--mode``, ``--archived-plan-path``.

    ``--mode`` is required here because ``init`` persists it into the
    bundle's ``_meta`` block; ``add`` and ``finalize`` later read it back
    from the bundle rather than taking it as an argument.
    """
    parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    parser.add_argument(
        '--mode',
        choices=['live', 'archived'],
        required=True,
        help='Resolution mode (live | archived) — persisted into the bundle',
    )
    parser.add_argument(
        '--archived-plan-path',
        dest='archived_plan_path',
        default=None,
        help='Accepted for symmetry with compile-report; archived bundles live in OS tmp',
    )


def _add_add_finalize_args(parser: argparse.ArgumentParser) -> None:
    """Attach flags for ``add`` and ``finalize``: ``--plan-id``, ``--archived-plan-path``.

    Mode is deliberately omitted — both subcommands read it from the
    bundle's persisted ``_meta.mode`` entry (written by ``init``).
    """
    parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    parser.add_argument(
        '--archived-plan-path',
        dest='archived_plan_path',
        default=None,
        help='Accepted for symmetry with compile-report; archived bundles live in OS tmp',
    )


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Assemble per-aspect TOON fragments into a bundle for compile-report',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # init
    init_parser = subparsers.add_parser(
        'init',
        help='Create an empty fragment bundle at the mode-appropriate path',
        allow_abbrev=False,
    )
    _add_init_args(init_parser)
    init_parser.set_defaults(func=cmd_init)

    # add
    add_parser = subparsers.add_parser(
        'add',
        help='Merge a fragment file into the bundle under an aspect key',
        allow_abbrev=False,
    )
    _add_add_finalize_args(add_parser)
    add_parser.add_argument('--aspect', required=True, help='Aspect key to register')
    add_parser.add_argument(
        '--fragment-file',
        required=True,
        dest='fragment_file',
        help='Path to a TOON fragment file',
    )
    add_parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Replace an existing aspect entry instead of erroring',
    )
    add_parser.set_defaults(func=cmd_add)

    # finalize
    finalize_parser = subparsers.add_parser(
        'finalize',
        help='Return the bundle path and aspect list',
        allow_abbrev=False,
    )
    _add_add_finalize_args(finalize_parser)
    finalize_parser.set_defaults(func=cmd_finalize)

    args = parser.parse_args()
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()  # type: ignore[no-untyped-call]
