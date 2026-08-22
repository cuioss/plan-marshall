#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Bundle-set deriver for the ``pre-push-quality-gate`` finalize step.

Pure, deterministic seam backing the "Derive unique bundle set" section of
``phase-6-finalize/standards/pre-push-quality-gate.md``. Given the live
footprint ``files[]``, the ``build_map`` globs, and the marketplace root, it
returns the sorted, de-duplicated bundle set the gate must run ``quality-gate``
against, plus an ``unresolved[]`` list of footprint paths that matched a
``build_map`` glob but resolved to no real bundle.

Derivation rules (applied per footprint path, in order):

1. Skip the path when it matches none of the ``build_map`` globs
   (``fnmatch.fnmatch``). The manifest composer already gated activation on
   glob membership; the seam re-applies the filter for defense-in-depth.
2. ``marketplace/bundles/<b>/…`` → take ``<b>`` (path segment 2).
3. ``test/<b>/…`` → take ``<b>`` (path segment 1) **only when
   ``marketplace/bundles/<b>/`` is a real directory**. When it is not, the path
   is **not** a bundle: it is appended to ``unresolved[]`` — never silently
   dropped, never a hard failure. This is what keeps a ``test/marketplace/**``
   path (e.g. ``test/marketplace/targets/test_frontmatter.py``) from deriving a
   phantom ``marketplace`` bundle.
4. Any other shape contributes no bundle (dropped silently — it is neither a
   bundle nor a diagnosable-unresolvable, just out of the derivation's remit).

An entry that resolves to no bundle is **never** an error. The ADR-009
fail-closed contract continues to apply to genuine ``quality-gate`` failures,
which this seam does not touch — it only decides which bundles the gate runs
against.

Return shape (CLI emits this as TOON; programmatic callers consume the tuple
from :func:`derive_gate_bundles` directly)::

    status: success
    bundles[N]: [<sorted unique bundle names>]
    unresolved[M]: [<footprint paths that matched a glob but resolved to no bundle>]

The script is registered through ``generate_executor.py`` and consumed via the
executor proxy::

    python3 .plan/execute-script.py \
      plan-marshall:phase-6-finalize:derive_gate_bundles derive \
      --files "<comma-separated footprint paths>" \
      --globs "<comma-separated build_map globs>" \
      --marketplace-root "<repo/worktree root containing marketplace/bundles/>"

The executor injects ``PYTHONPATH`` for ``toon_parser`` and
``marketplace_paths``, so no in-script ``sys.path`` manipulation is required.
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

from toon_parser import serialize_toon

#: The directory under the marketplace root that holds each bundle by name.
#: A ``test/<b>/…`` footprint path derives bundle ``<b>`` only when
#: ``<marketplace_root>/marketplace/bundles/<b>/`` is a real directory.
_BUNDLES_SUBPATH: str = 'marketplace/bundles'

#: Path prefix identifying a source path already rooted at a bundle directory.
_BUNDLES_PREFIX: str = 'marketplace/bundles/'

#: Path prefix identifying a test path whose second segment names the bundle.
_TEST_PREFIX: str = 'test/'


def derive_gate_bundles(
    files: list[str],
    globs: list[str],
    bundles_root: Path,
) -> tuple[list[str], list[str]]:
    """Derive the sorted unique bundle set and the unresolved-path list.

    Args:
        files: Live footprint paths (repo-relative, forward-slash separated).
        globs: ``build_map`` globs; a path contributes only when it matches at
            least one glob via :func:`fnmatch.fnmatch`.
        bundles_root: Absolute path to the ``marketplace/bundles`` directory.
            A ``test/<b>/…`` path derives bundle ``<b>`` only when
            ``bundles_root / <b>`` is a real directory on disk.

    Returns:
        A ``(bundles, unresolved)`` tuple. ``bundles`` is the sorted,
        de-duplicated bundle-name list. ``unresolved`` preserves footprint
        order and holds each ``test/<b>/…`` path whose ``<b>`` is not a real
        bundle directory — a diagnosable signal, never an error.
    """
    bundles: set[str] = set()
    unresolved: list[str] = []

    for raw in files:
        path = raw.strip()
        if not path:
            continue
        if not any(fnmatch.fnmatch(path, glob) for glob in globs):
            continue

        segments = path.split('/')
        if path.startswith(_BUNDLES_PREFIX) and len(segments) >= 3 and segments[2]:
            bundles.add(segments[2])
        elif path.startswith(_TEST_PREFIX) and len(segments) >= 2 and segments[1]:
            candidate = segments[1]
            if (bundles_root / candidate).is_dir():
                bundles.add(candidate)
            else:
                unresolved.append(path)
        # Any other shape contributes no bundle (silent drop by rule 4).

    return sorted(bundles), unresolved


def _split_csv(value: str) -> list[str]:
    """Split a comma-separated CLI argument into a trimmed, non-empty list."""
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def cmd_derive(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`derive_gate_bundles` — emits TOON, returns 0."""
    marketplace_root = Path(args.marketplace_root).expanduser()
    bundles_root = marketplace_root / _BUNDLES_SUBPATH
    bundles, unresolved = derive_gate_bundles(
        _split_csv(args.files),
        _split_csv(args.globs),
        bundles_root,
    )
    payload = {
        'status': 'success',
        'bundles': bundles,
        'unresolved': unresolved,
    }
    print(serialize_toon(payload))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with a single ``derive`` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            'Derive the sorted unique bundle set (plus an unresolved-path '
            'list) that the pre-push-quality-gate finalize step runs '
            'quality-gate against, given the live footprint, the build_map '
            'globs, and the marketplace root.'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command_name', required=True)

    derive_parser = sub.add_parser(
        'derive',
        help='Derive the bundle set from a footprint and the build_map globs',
        allow_abbrev=False,
    )
    derive_parser.add_argument(
        '--files',
        required=True,
        help='Comma-separated live-footprint paths (repo-relative).',
    )
    derive_parser.add_argument(
        '--globs',
        required=True,
        help='Comma-separated build_map globs (fnmatch syntax).',
    )
    derive_parser.add_argument(
        '--marketplace-root',
        default='.',
        dest='marketplace_root',
        help=(
            'Repository/worktree root that contains marketplace/bundles/. '
            'Defaults to the current working directory, which phase-5+ pins '
            'to the active worktree.'
        ),
    )
    derive_parser.set_defaults(func=cmd_derive)

    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())


__all__ = ['derive_gate_bundles']
