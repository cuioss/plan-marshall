#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
4. Any other shape resolves to no bundle and is appended to ``unresolved[]``.
   Reaching this rule means the path already matched a ``build_map`` glob at
   rule 1 — the project itself declared it build-relevant — so it is a
   diagnosable-unresolvable, not something outside the derivation's remit. A
   consumer project whose sources live under any other layout produces a
   footprint made entirely of such paths, so dropping them returned an empty
   ``bundles`` list *and* an empty ``unresolved`` list, and the gate's
   per-bundle loop iterated zero times and reported green. The disposition
   mirrors ``_test_scope_divergence._module_for_path``, which returns None for
   the same input class so its caller records the path in ``unresolved_paths``.

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
      --files-file "<path to a one-path-per-line footprint list>" \
      --globs "<comma-separated build_map globs>" \
      --marketplace-root "<repo/worktree root containing marketplace/bundles/>"

**Why ``--files-file`` exists.** The footprint reaches this seam as a list, and a
list crossing a process boundary as a hand-composed command-line string is not
transcribed faithfully at scale: the documented caller pastes the paths one by
one, and a 434-path list is long enough that plausible-looking path names get
substituted for real ones. A wrong list is not detectable from the outside — it
derives a *narrower* bundle set, the gate runs fewer bundles, and the run reads
as green. ``--files-file`` removes the human from the hand-off: the producer
writes the exact list to disk and this verb reads those bytes. ``--files`` remains
for the small inputs where composing the string is not a risk, and the two are
mutually exclusive so a caller can never half-use the safe path.

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
        order and holds every glob-matching path that resolved to no bundle:
        a ``test/<b>/…`` path whose ``<b>`` is not a real bundle directory,
        and — by rule 4 — a path of any other shape. Every entry matched a
        ``build_map`` glob, so each is a diagnosable signal, never an error
        and never a silent drop.
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
        else:
            # Rule 4. The path matched a build_map glob but is neither a
            # marketplace/bundles/<b>/… path nor a resolvable test/<b>/… one,
            # so it resolves to no bundle and is REPORTED rather than dropped.
            unresolved.append(path)

    return sorted(bundles), unresolved


def _split_csv(value: str) -> list[str]:
    """Split a comma-separated CLI argument into a trimmed, non-empty list."""
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def read_files_file(path: Path) -> list[str]:
    """Read a one-path-per-line footprint list written by its producer.

    The file is the transport, so the reader is deliberately permissive about
    what it accepts — blank lines and ``#`` comments are skipped, and each
    remaining line is stripped — and deliberately strict about one thing: a
    file that cannot be read or decoded is an error, never an empty list. An
    empty list would derive no bundles, the per-bundle loop would iterate zero
    times, and the gate would report green over a population it never saw.

    Args:
        path: File holding one repo-relative footprint path per line.

    Returns:
        The parsed paths in file order, duplicates preserved (the seam
        de-duplicates the derived *bundle* set, and a repeated path must not be
        silently collapsed on the way in).

    Raises:
        OSError: The file does not exist or cannot be read.
        UnicodeError: The file is not valid UTF-8.
    """
    lines = path.read_text(encoding='utf-8').splitlines()
    return [stripped for line in lines if (stripped := line.strip()) and not stripped.startswith('#')]


def _resolve_files(args: argparse.Namespace) -> list[str]:
    """Resolve the footprint from whichever of the two input forms was given.

    Exactly one of ``--files`` / ``--files-file`` is required; the parser's
    mutually-exclusive group enforces that, so this only has to dispatch.
    """
    if args.files_file is not None:
        return read_files_file(Path(args.files_file).expanduser())
    return _split_csv(args.files)


def cmd_derive(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`derive_gate_bundles` — emits TOON, returns 0."""
    marketplace_root = Path(args.marketplace_root).expanduser()
    bundles_root = marketplace_root / _BUNDLES_SUBPATH
    try:
        files = _resolve_files(args)
    except (OSError, UnicodeError) as exc:
        # An unreadable or undecodable footprint file is reported, never
        # degraded to an empty list. The caller is a gate: a bare traceback
        # would leave the failure legible only to a reader of stderr, while a
        # typed envelope lets it be branched on and named in the step's own
        # record. ``UnicodeError`` is in the tuple because a truncated or
        # non-UTF-8 file raises ``UnicodeDecodeError`` — a ``ValueError``
        # subclass, not an ``OSError`` — and it is the same failure from the
        # gate's point of view: the list could not be read.
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'files_file_unreadable',
                    'files_file': str(args.files_file),
                    'message': f'Failed to read the footprint file: {exc}',
                }
            )
        )
        return 0
    bundles, unresolved = derive_gate_bundles(
        files,
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
    files_group = derive_parser.add_mutually_exclusive_group(required=True)
    files_group.add_argument(
        '--files',
        help=(
            'Comma-separated live-footprint paths (repo-relative). Small '
            'inputs only: a long list composed by hand is not transcribed '
            'faithfully, and a wrong list derives a narrower bundle set that '
            'reads as a green gate. Use --files-file for anything sizeable.'
        ),
    )
    files_group.add_argument(
        '--files-file',
        dest='files_file',
        help=(
            'Path to a file holding one repo-relative footprint path per '
            'line (blank lines and # comments ignored). The faithful hand-off: '
            'the producer writes the exact list, this verb reads those bytes.'
        ),
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


__all__ = ['derive_gate_bundles', 'read_files_file']
