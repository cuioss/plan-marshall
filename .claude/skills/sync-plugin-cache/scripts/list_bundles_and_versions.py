#!/usr/bin/env python3
"""Enumerate bundles + versions from ``target/claude/`` and emit a TOON table.

Reads ``{source_root}/<bundle>/.claude-plugin/plugin.json`` from the
configured source root (defaulting to ``{cwd}/target/claude``) and
prints a TOON table consumable by ``sync.py``.

A missing or malformed manifest yields ``version: unknown``.

The ``--source-root PATH`` flag overrides the default. The default
points at the multi-target generator output (``target/claude/``); pass
``--source-root <worktree>/target/claude`` to read from a worktree-local
generator output.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_SOURCE_SUBDIR = Path('target') / 'claude'


def _read_version(manifest: Path) -> str:
    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return 'unknown'
    version = data.get('version')
    return version if isinstance(version, str) and version else 'unknown'


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='List bundles and their versions in TOON format.',
        allow_abbrev=False,
    )
    parser.add_argument(
        '--source-root',
        type=Path,
        default=None,
        metavar='PATH',
        help=(
            'Directory whose immediate subdirectories are bundles. When '
            'omitted, defaults to {cwd}/target/claude/. Pass --source-root '
            '<worktree>/target/claude to read from a worktree-local generator output.'
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    base = args.source_root if args.source_root is not None else Path.cwd() / DEFAULT_SOURCE_SUBDIR

    pairs: list[tuple[str, str]] = []
    if base.is_dir():
        for bundle_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            manifest = bundle_dir / '.claude-plugin' / 'plugin.json'
            pairs.append((bundle_dir.name, _read_version(manifest)))

    lines = ['status: success', f'bundles[{len(pairs)}]{{name,version}}:']
    lines.extend(f'{name},{version}' for name, version in pairs)
    sys.stdout.write('\n'.join(lines) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
