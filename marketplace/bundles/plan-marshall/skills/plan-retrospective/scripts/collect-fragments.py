#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Assemble per-aspect TOON fragments into a bundle consumed by compile-report.

This is a stateful helper for ``plan-retrospective``: the orchestrator captures
each aspect's output as a TOON fragment file, then registers it via ``add`` so
that ``compile-report run --fragments-file`` can consume a single bundle.

Subcommands:
    init      Create an empty TOON bundle at the mode-appropriate path.
    add       Merge a fragment file into the bundle under the aspect key.
    register  Merge MANY fragment files in one batch — one aspect-key
              registration pass, one bundle write — reporting registered
              aspect keys with counts.
    finalize  Report the bundle path and its registered aspects.

Bundle location (the bundle root is keyed on ``--plan-id`` and the mode alone):
    live      ``<plan_dir>/work/retro-fragments.toon`` where ``plan_dir`` is
              ``base_path('plans', plan_id)`` (honours ``PLAN_BASE_DIR``).
    archived  ``<tmp>/plan-retrospective/plan-<plan_id>/work/retro-fragments.toon``
              — a synthetic per-plan dir under the OS tmpdir, ALWAYS. The
              archived plan directory is the audit's read-only INPUT (read by
              ``compile-report`` and the aspect scripts through their own
              ``--archived-plan-path``); it is never this script's OUTPUT, so
              neither the bundle nor the ``{fragment_dir}`` fragments land in
              it, and ``add`` / ``register`` / ``finalize`` locate the bundle
              ``init`` created from ``--plan-id`` alone.

Path resolution rules:
    ``add --fragment-file`` and every ``register --item ASPECT=PATH`` resolve
    through the one resolver, ``_resolve_fragment_path``. The documented
    caller form is ``{fragment_dir}/fragment-<aspect>.toon``, where
    ``{fragment_dir}`` is the directory of the ``bundle_path`` that ``init``
    returns — an absolute path, used verbatim. A relative path that already
    resolves from the cwd to a location inside the bundle root is used as
    that location rather than re-anchored (which would double the bundle
    root); any other relative path is anchored to the bundle root.

Missing fragment:
    A fragment path that resolves to no regular file — absent, or a directory
    or other non-file entry — returns ``status: error`` with
    ``error: fragment_missing``, the ``aspect``, the resolved ``fragment_path``
    and its ``path_state`` (``absent`` | ``not_a_file``) — exit code 0, bundle
    untouched. ``register`` aborts the whole batch on the first missing
    fragment, before any fragment is merged.

Missing bundle:
    ``finalize`` against a bundle path that names no regular file returns
    ``status: error`` with ``error: bundle_missing``, the ``bundle_path`` it
    looked at and its ``path_state`` — exit code 0, so the caller can carry the
    refusal forward instead of stopping on a crash.

All subcommands emit TOON output via ``serialize_toon`` and follow the
execute-script executor contract (@safe_main, ``--help`` on every subparser,
kebab-case flags).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from _retro_bundle_root import resolve_bundle_root, resolve_fragment_dir
from file_ops import (
    atomic_write_file,
    output_toon,
    safe_main,
)
from input_validation import (
    add_plan_id_arg,
    parse_args_with_toon_errors,
)
from retro_sections import valid_aspect_keys
from toon_parser import parse_toon, serialize_toon

_META_KEY = '_meta'
_BUNDLE_FILENAME = 'retro-fragments.toon'


def resolve_bundle_path(mode: str, plan_id: str) -> Path:
    """Return the bundle path for the given mode.

    Both modes resolve to ``<bundle_root>/work/retro-fragments.toon``. The
    bundle root comes from the shared :func:`_retro_bundle_root.resolve_bundle_root`
    — the single source of truth the fragment readers use too — so ``init``,
    ``add``, ``register`` and ``finalize`` agree on it by construction.

    Args:
        mode: Either ``'live'`` or ``'archived'``.
        plan_id: Plan identifier. Required for both modes.

    Returns:
        Absolute path to the bundle file.

    Raises:
        ValueError: On unknown ``mode`` or missing ``plan_id``.
    """
    return resolve_fragment_dir(mode, plan_id) / _BUNDLE_FILENAME


def _resolve_fragment_path(raw_path: str, bundle_root: Path) -> Path:
    """Resolve one fragment path — the only fragment-path resolver ``add`` and ``register`` use.

    The documented caller form is ``{fragment_dir}/fragment-<aspect>.toon``,
    where ``{fragment_dir}`` is the directory of the ``bundle_path`` that
    ``init`` returns; it is absolute and is returned verbatim.

    A relative path is resolved in two steps. When it already resolves from
    the cwd to a location inside ``bundle_root`` (the ``.plan/local/plans/<id>/...``
    form a caller in the repository root spells out), that location is used
    as-is: anchoring it to ``bundle_root`` again would double the directory.
    Any other relative path is anchored to ``bundle_root``.

    Args:
        raw_path: The caller-supplied fragment path.
        bundle_root: The resolved bundle root of the bundle's persisted mode.

    Returns:
        The path the fragment is read from. Existence is not checked here.
    """
    raw = Path(raw_path)
    if raw.is_absolute():
        return raw
    from_cwd = raw.resolve()
    if from_cwd.is_relative_to(bundle_root):
        return from_cwd
    return bundle_root / raw


def _path_state(path: Path) -> str:
    """Classify a path that is required to name a regular file but does not.

    ``absent`` when nothing is at the path; ``not_a_file`` when something is —
    a directory or another non-regular entry — so ``read_text`` would raise.
    """
    return 'not_a_file' if path.exists() else 'absent'


def _describe_path_state(path_state: str) -> str:
    """Render a ``_path_state`` value as the clause a refusal message carries."""
    return 'is not a regular file' if path_state == 'not_a_file' else 'does not exist'


def _fragment_missing(operation: str, plan_id: str, aspect: str, fragment_path: Path) -> dict[str, Any]:
    """Return the structured refusal for a fragment path that names no regular file.

    A missing fragment is a caller-visible outcome, not a crash: the aspect
    that produced no file is named so the caller can record it and move on to
    the next aspect, and the resolved path is named so a wrong-path capture is
    diagnosable from the result alone. A directory at the path is refused the
    same way — reading it would raise instead of returning this result.
    """
    path_state = _path_state(fragment_path)
    return {
        'status': 'error',
        'operation': operation,
        'plan_id': plan_id,
        'error': 'fragment_missing',
        'aspect': aspect,
        'fragment_path': str(fragment_path),
        'path_state': path_state,
        'message': (
            f'Fragment file for aspect {aspect!r} {_describe_path_state(path_state)}: {fragment_path}. '
            'The bundle was not modified.'
        ),
    }


def _bundle_missing(operation: str, plan_id: str, bundle_path: Path) -> dict[str, Any]:
    """Return the structured refusal for a bundle path that names no regular file.

    The bundle path is named so the caller can carry the refusal forward as the
    retrospective's error rather than stopping on an uncaught exception.
    """
    path_state = _path_state(bundle_path)
    return {
        'status': 'error',
        'operation': operation,
        'plan_id': plan_id,
        'error': 'bundle_missing',
        'bundle_path': str(bundle_path),
        'path_state': path_state,
        'message': f'Fragments bundle {_describe_path_state(path_state)}: {bundle_path}. Run init first.',
    }


def _read_bundle(bundle_path: Path) -> dict[str, Any]:
    """Read and validate the bundle file.

    Args:
        bundle_path: Path to the bundle file.

    Returns:
        Parsed bundle dict. Empty dict when file is empty.

    Raises:
        ValueError: When the bundle path names no regular file or the bundle is
            not a top-level dict.
    """
    if not bundle_path.is_file():
        raise ValueError(f'Bundle file {_describe_path_state(_path_state(bundle_path))}: {bundle_path}')
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
        ValueError: When the fragment path names no regular file or the
            fragment fails to parse.
    """
    if not fragment_path.is_file():
        raise ValueError(f'Fragment file {_describe_path_state(_path_state(fragment_path))}: {fragment_path}')
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
        raise ValueError(f'Bundle missing _meta.mode — was it created by a compatible init? bundle_path={bundle_path}')
    return str(meta['mode'])


def cmd_init(args: argparse.Namespace) -> dict[str, Any]:
    """Create (or overwrite) a bundle file seeded with the resolution mode."""
    bundle_path = resolve_bundle_path(args.mode, args.plan_id)
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
    """Probe live then archived candidate paths; return the first regular file.

    Returns the ``live`` path when neither names a regular file, so every
    caller reports the absent bundle against one consistent path.
    """
    live_path = resolve_bundle_path('live', args.plan_id)
    if live_path.is_file():
        return live_path
    archived_path = resolve_bundle_path('archived', args.plan_id)
    if archived_path.is_file():
        return archived_path
    return live_path


def _domain_aspect_keys() -> set[str]:
    """Return the set of domain-contributed retrospective aspect names.

    Domain bundles register additional aspects via
    ``provides_retrospective_aspects()`` (e.g. ``wrapper-tangle`` from
    ``pm-plugin-development``). Those keys are registered through the same
    ``collect-fragments add --aspect <key>`` path but are NOT in the static
    :data:`retro_sections.SECTION_SPEC`. The validation guard must accept them,
    so they are discovered at add-time via the same extension-discovery library
    that ``extension-api list-retrospective-aspects`` exposes — both this script
    and ``extension_discovery`` live on the executor PYTHONPATH, so the import is
    a direct in-process call rather than a subprocess shell-out.
    """
    from extension_discovery import (
        discover_all_extensions,
        get_retrospective_aspects_from_extensions,
    )

    extensions = discover_all_extensions()
    aspects = get_retrospective_aspects_from_extensions(extensions)
    try:
        return {a['aspect'] for a in aspects if a.get('aspect')}
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(
            'Domain-contributed retrospective aspects are malformed: expected a '
            "list of dicts each carrying an 'aspect' key, but encountered a "
            f'partially corrupt structure (None, non-dict entry, or wrong value '
            f'type) while building the aspect-key set: {exc}'
        ) from exc


def _registerable_aspect_keys() -> set[str]:
    """Return the closed set of aspect keys ``cmd_add`` accepts.

    The union of (a) the static section registry keys
    (:func:`retro_sections.valid_aspect_keys`) and (b) the domain-contributed
    aspect names (:func:`_domain_aspect_keys`). An ``--aspect`` outside this set
    is a producer/consumer drift — a typo'd or renamed key that the consumer's
    section map will never look up — and is rejected loudly by ``cmd_add``.
    """
    return valid_aspect_keys() | _domain_aspect_keys()


def cmd_add(args: argparse.Namespace) -> dict[str, Any]:
    """Merge a fragment file into the bundle under the given aspect key."""
    aspect = args.aspect
    if not aspect:
        raise ValueError('--aspect is required')
    if aspect.startswith('_'):
        raise ValueError('Reserved aspect key: keys starting with "_" are internal metadata')

    # Validate --aspect against the canonical registry (static section keys ∪
    # domain-contributed aspects) BEFORE touching the bundle. An unregistered
    # key would otherwise write silently into the bundle and then be dropped by
    # compile-report's static section loop — a silent-data-loss class. Reject it
    # loudly here, naming the offending key and the valid set, and do NOT mutate
    # the bundle.
    registerable = _registerable_aspect_keys()
    if aspect not in registerable:
        return {
            'status': 'error',
            'operation': 'add',
            'plan_id': args.plan_id,
            'aspect': aspect,
            'error': (
                f'Unregistered aspect key: {aspect!r}. It is not in the canonical section '
                f'registry nor any domain-contributed aspect set, so compile-report would '
                f'silently drop its section. Valid aspect keys: {sorted(registerable)}'
            ),
            'valid_aspects': sorted(registerable),
        }

    bundle_path = _locate_bundle(args)
    bundle = _read_bundle(bundle_path)
    mode = _read_mode_from_bundle(bundle, bundle_path)

    # Sanity guard: the path we found the bundle at must match the path the
    # persisted mode resolves to. A mismatch means the bundle was moved or
    # hand-crafted with a contradictory _meta.mode.
    expected_path = resolve_bundle_path(mode, args.plan_id)
    if bundle_path.resolve() != expected_path.resolve():
        raise ValueError(
            f'Bundle path mismatch: found at {bundle_path} but _meta.mode={mode!r} resolves to {expected_path}'
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

    bundle_root = resolve_bundle_root(mode, args.plan_id)
    fragment_path = _resolve_fragment_path(args.fragment_file, bundle_root)
    if not fragment_path.is_file():
        return _fragment_missing('add', args.plan_id, aspect, fragment_path)
    fragment = _read_fragment(fragment_path)
    bundle[aspect] = fragment

    # Record the aspect in the authoritative inventory. The --aspect argument
    # is the single source of truth for which keys are genuine aspects, so the
    # reported list is immune to phantom sibling keys that a malformed fragment
    # body might leak into the bundle. Dedup-aware so an --overwrite re-add
    # never duplicates the entry.
    meta = bundle[_META_KEY]
    registered = meta.get('aspects', [])
    if not isinstance(registered, list):
        raise ValueError(
            f'Corrupt bundle {bundle_path}: {_META_KEY}.aspects must be a list, got {type(registered).__name__}'
        )
    if aspect not in registered:
        registered.append(aspect)
    meta['aspects'] = registered
    _write_bundle(bundle_path, bundle)

    return {
        'status': 'success',
        'operation': 'add',
        'plan_id': args.plan_id,
        'aspect': aspect,
        'bundle_path': str(bundle_path),
        'aspects': sorted(bundle[_META_KEY].get('aspects', [])),
        'overwrote': already_present,
    }


def cmd_finalize(args: argparse.Namespace) -> dict[str, Any]:
    """Return the bundle path and aspect list for hand-off to compile-report.

    An absent bundle is refused as ``error: bundle_missing`` naming the path it
    looked at, so the caller reaches its error record instead of a crash.
    """
    bundle_path = _locate_bundle(args)
    if not bundle_path.is_file():
        return _bundle_missing('finalize', args.plan_id, bundle_path)
    bundle = _read_bundle(bundle_path)
    mode = _read_mode_from_bundle(bundle, bundle_path)
    raw_aspects = bundle.get(_META_KEY, {}).get('aspects', [])
    if not isinstance(raw_aspects, list):
        raise ValueError(
            f'Corrupt bundle {bundle_path}: {_META_KEY}.aspects must be a list, got {type(raw_aspects).__name__}'
        )
    aspects = sorted(raw_aspects)
    return {
        'status': 'success',
        'operation': 'finalize',
        'plan_id': args.plan_id,
        'mode': mode,
        'bundle_path': str(bundle_path),
        'aspects': aspects,
        'aspect_count': len(aspects),
    }


def _parse_batch_item(raw: str) -> tuple[str, str]:
    """Split one ``--item ASPECT=PATH`` value on its FIRST ``=``.

    Paths routinely contain ``=`` (query strings, TOON corners); only the
    FIRST one separates the key. A value with no ``=`` — or an empty aspect —
    is a caller error, reported before the bundle is touched.
    """
    aspect, separator, path = raw.partition('=')
    aspect = aspect.strip()
    path = path.strip()
    if not separator or not aspect or not path:
        raise ValueError(f'Malformed --item {raw!r}: expected ASPECT=PATH with a non-empty aspect and path.')
    return aspect, path


def _fragment_entry_count(fragment: Any) -> int:
    """Top-level entry count of a parsed fragment, for the conservation report.

    A dict or list contributes its length; any other shape contributes one —
    the fragment exists and was registered, and the count is what lets a
    reader verify that compile-report dropped nothing silently.
    """
    if isinstance(fragment, (dict, list)):
        return len(fragment)
    return 1


def cmd_register(args: argparse.Namespace) -> dict[str, Any]:
    """Merge MANY fragment files in one batch — one registration pass, one write.

    The batch counterpart to repeated ``add`` calls: the aspect-key registry is
    resolved ONCE, every key is validated BEFORE the bundle is touched
    (all-or-nothing — one bad key leaves the bundle byte-identical), every
    fragment is read, and the bundle is written exactly once. The result
    publishes the registered aspect keys WITH their fragment entry counts, so
    compile-report's section loop is checkable for conservation: a registered
    key with entries that never renders is a loud drop, not a silent one.
    """
    raw_items: list[str] = list(getattr(args, 'item', None) or [])
    if not raw_items:
        raise ValueError('register requires at least one --item ASPECT=PATH.')

    # Parse every item first: a malformed item fails before anything is read.
    parsed: list[tuple[str, str]] = [_parse_batch_item(raw) for raw in raw_items]

    # In-batch duplicates are a caller error even under --overwrite (which
    # governs bundle entries, not the batch itself): last-wins would silently
    # discard one of the two fragment files.
    seen: set[str] = set()
    for aspect, _ in parsed:
        if aspect in seen:
            raise ValueError(f'Duplicate aspect in one register batch: {aspect!r}.')
        seen.add(aspect)

    # ONE aspect-key registration pass for the whole batch (the same closed
    # set `cmd_add` validates against, resolved once, not once per fragment).
    registerable = _registerable_aspect_keys()
    unregistered = sorted({aspect for aspect, _ in parsed} - registerable)
    if unregistered:
        return {
            'status': 'error',
            'operation': 'register',
            'plan_id': args.plan_id,
            'aspects': [aspect for aspect, _ in parsed],
            'error': (
                f'Unregistered aspect key(s): {unregistered}. None are in the canonical '
                f'section registry nor any domain-contributed aspect set, so compile-report '
                f'would silently drop those sections. Valid aspect keys: {sorted(registerable)}'
            ),
            'valid_aspects': sorted(registerable),
        }

    bundle_path = _locate_bundle(args)
    bundle = _read_bundle(bundle_path)
    mode = _read_mode_from_bundle(bundle, bundle_path)

    # Sanity guard: the path we found the bundle at must match the path the
    # persisted mode resolves to (same contract as `cmd_add`).
    expected_path = resolve_bundle_path(mode, args.plan_id)
    if bundle_path.resolve() != expected_path.resolve():
        raise ValueError(
            f'Bundle path mismatch: found at {bundle_path} but _meta.mode={mode!r} resolves to {expected_path}'
        )

    # Already-present check for the WHOLE batch before any fragment is read:
    # without --overwrite one collision aborts the batch with the bundle
    # untouched, so a partial batch never lands.
    already_present = {aspect for aspect, _ in parsed if aspect in bundle}
    if already_present and not args.overwrite:
        return {
            'status': 'error',
            'operation': 'register',
            'plan_id': args.plan_id,
            'bundle_path': str(bundle_path),
            'error': (
                f'Aspect(s) already registered: {sorted(already_present)}. '
                f'Pass --overwrite to replace, or drop them from the batch.'
            ),
        }

    # Resolve every fragment path and refuse the batch on the first missing
    # file, then read every fragment (fail fast — the bundle is still
    # untouched), merge all, update the inventory once, and write once.
    bundle_root = resolve_bundle_root(mode, args.plan_id)
    resolved: list[tuple[str, Path]] = [
        (aspect, _resolve_fragment_path(raw_path, bundle_root)) for aspect, raw_path in parsed
    ]
    for aspect, fragment_path in resolved:
        if not fragment_path.is_file():
            return _fragment_missing('register', args.plan_id, aspect, fragment_path)
    fragments: list[tuple[str, Any]] = [(aspect, _read_fragment(fragment_path)) for aspect, fragment_path in resolved]

    meta = bundle[_META_KEY]
    registered_meta = meta.get('aspects', [])
    if not isinstance(registered_meta, list):
        raise ValueError(
            f'Corrupt bundle {bundle_path}: {_META_KEY}.aspects must be a list, got {type(registered_meta).__name__}'
        )
    rows: list[dict[str, Any]] = []
    for aspect, fragment in fragments:
        overwrote = aspect in bundle
        bundle[aspect] = fragment
        if aspect not in registered_meta:
            registered_meta.append(aspect)
        rows.append({'aspect': aspect, 'entries': _fragment_entry_count(fragment), 'overwrote': overwrote})
    meta['aspects'] = registered_meta
    _write_bundle(bundle_path, bundle)

    return {
        'status': 'success',
        'operation': 'register',
        'plan_id': args.plan_id,
        'bundle_path': str(bundle_path),
        'aspects': sorted(registered_meta),
        'aspect_count': len(registered_meta),
        'registered': sorted(rows, key=lambda row: row['aspect']),
    }


def _add_init_args(parser: argparse.ArgumentParser) -> None:
    """Attach flags for ``init``: ``--plan-id`` and ``--mode``.

    ``--mode`` is required here because ``init`` persists it into the
    bundle's ``_meta`` block; ``add``, ``register`` and ``finalize`` later
    read it back from the bundle rather than taking it as an argument.
    """
    add_plan_id_arg(parser)
    parser.add_argument(
        '--mode',
        choices=['live', 'archived'],
        required=True,
        help='Resolution mode (live | archived) — persisted into the bundle; archived bundles live under the OS tmpdir',
    )


def _add_add_finalize_args(parser: argparse.ArgumentParser) -> None:
    """Attach flags for ``add``, ``register`` and ``finalize``: ``--plan-id``.

    Mode is deliberately omitted — every one of them reads it from the
    bundle's persisted ``_meta.mode`` entry (written by ``init``), and the
    bundle is located from ``--plan-id`` alone.
    """
    add_plan_id_arg(parser)


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
        help='Path to a TOON fragment file — {fragment_dir}/fragment-<aspect>.toon, where {fragment_dir} is the directory of the bundle_path init returns',
    )
    add_parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Replace an existing aspect entry instead of erroring',
    )
    add_parser.set_defaults(func=cmd_add)

    # register
    register_parser = subparsers.add_parser(
        'register',
        help='Merge many fragment files in one batch under their aspect keys',
        allow_abbrev=False,
    )
    _add_add_finalize_args(register_parser)
    register_parser.add_argument(
        '--item',
        dest='item',
        action='append',
        required=True,
        help='One ASPECT=PATH pair per fragment (repeatable; at least one required)',
    )
    register_parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Replace already-registered aspect entries instead of erroring',
    )
    register_parser.set_defaults(func=cmd_register)

    # finalize
    finalize_parser = subparsers.add_parser(
        'finalize',
        help='Return the bundle path and aspect list',
        allow_abbrev=False,
    )
    _add_add_finalize_args(finalize_parser)
    finalize_parser.set_defaults(func=cmd_finalize)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
