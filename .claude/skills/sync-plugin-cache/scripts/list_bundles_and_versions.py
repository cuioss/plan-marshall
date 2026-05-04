#!/usr/bin/env python3
"""Enumerate marketplace bundles and emit TOON bundle:version pairs.

Reads `marketplace/bundles/*/.claude-plugin/plugin.json` relative to the
current working directory and prints a TOON table consumable by Step 3 of
`.claude/skills/sync-plugin-cache/SKILL.md` (parallel rsync calls).

A missing or malformed manifest yields `version: unknown`, matching the
fallback semantics of the original shell snippet this script replaces.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _read_version(manifest: Path) -> str:
    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return 'unknown'
    version = data.get('version')
    return version if isinstance(version, str) and version else 'unknown'


def main() -> int:
    bundles_root = Path('marketplace/bundles')
    pairs: list[tuple[str, str]] = []
    if bundles_root.is_dir():
        for bundle_dir in sorted(p for p in bundles_root.iterdir() if p.is_dir()):
            manifest = bundle_dir / '.claude-plugin' / 'plugin.json'
            pairs.append((bundle_dir.name, _read_version(manifest)))

    lines = ['status: success', f'bundles[{len(pairs)}]{{name,version}}:']
    lines.extend(f'{name},{version}' for name, version in pairs)
    sys.stdout.write('\n'.join(lines) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
