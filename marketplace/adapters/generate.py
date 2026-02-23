#!/usr/bin/env python3
"""CLI entry point for generating marketplace adapter output.

Usage:
    python3 marketplace/adapters/generate.py --target opencode --output .opencode/
    python3 marketplace/adapters/generate.py --target opencode --output .opencode/ --bundles pm-dev-java,pm-workflow
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on path for imports
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from marketplace.adapters.opencode_adapter import OpenCodeAdapter  # noqa: E402

ADAPTERS = {
    'opencode': OpenCodeAdapter,
}

DEFAULT_MARKETPLACE_DIR = Path(__file__).resolve().parent.parent / 'bundles'


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate marketplace adapter output for target AI assistants.')
    parser.add_argument('--target', required=True, choices=list(ADAPTERS.keys()), help='Target assistant format.')
    parser.add_argument('--output', required=True, type=Path, help='Output directory.')
    parser.add_argument(
        '--bundles', type=str, default=None, help='Comma-separated list of bundles to export (default: all).'
    )
    parser.add_argument(
        '--marketplace-dir', type=Path, default=DEFAULT_MARKETPLACE_DIR, help='Path to marketplace/bundles/ directory.'
    )

    args = parser.parse_args()

    adapter_cls = ADAPTERS[args.target]
    adapter = adapter_cls()

    bundle_list = [b.strip() for b in args.bundles.split(',')] if args.bundles else None

    output_dir = args.output.resolve()
    marketplace_dir = args.marketplace_dir.resolve()

    if not marketplace_dir.exists():
        print(f'Error: Marketplace directory not found: {marketplace_dir}', file=sys.stderr)
        return 1

    print(f'Generating {adapter.name()} output...')
    print(f'  Source: {marketplace_dir}')
    print(f'  Output: {output_dir}')
    if bundle_list:
        print(f'  Bundles: {", ".join(bundle_list)}')

    generated = adapter.generate(marketplace_dir, output_dir, bundles=bundle_list)

    print(f'Generated {len(generated)} files.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
