#!/usr/bin/env python3
"""CLI entry point for marketplace target generation.

Usage:
    python3 marketplace/targets/generate.py --target claude
    python3 marketplace/targets/generate.py --target claude --output target/claude
    python3 marketplace/targets/generate.py --target opencode --output target/opencode
    python3 marketplace/targets/generate.py --target all --output target

Exits 0 on success, 2 on any failure (unknown target, missing required
flag, generator-reported error).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path so `import marketplace.targets` resolves.
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from marketplace.targets import TARGET_REGISTRY  # noqa: E402

DEFAULT_MARKETPLACE_DIR = Path(__file__).resolve().parent.parent / 'bundles'

EXIT_OK = 0
EXIT_ERROR = 2


def _build_parser() -> argparse.ArgumentParser:
    target_choices = sorted(TARGET_REGISTRY.keys()) + ['all']
    parser = argparse.ArgumentParser(
        prog='marketplace-targets-generate',
        description='Generate marketplace target output (claude verbatim mirror, opencode emitter).',
        allow_abbrev=False,
    )
    parser.add_argument(
        '--target',
        required=True,
        choices=target_choices,
        help='Target to generate. Use "all" to run every registered target sequentially.',
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help=(
            'Output directory. Required for opencode (and for claude when emitting); '
            'optional for claude when running equality-check only.'
        ),
    )
    parser.add_argument(
        '--bundles',
        type=str,
        default=None,
        help='Comma-separated list of bundles to process. Default: all bundles.',
    )
    parser.add_argument(
        '--marketplace-dir',
        type=Path,
        default=DEFAULT_MARKETPLACE_DIR,
        help='Path to the marketplace/bundles/ directory. Default: marketplace/bundles/.',
    )
    return parser


def _parse_bundles(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    items = [b.strip() for b in raw.split(',') if b.strip()]
    if not items:
        return None
    return items


def _resolve_targets(name: str) -> list[str]:
    if name == 'all':
        return sorted(TARGET_REGISTRY.keys())
    return [name]


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    marketplace_dir = args.marketplace_dir.resolve()
    if not marketplace_dir.exists():
        print(f'error: marketplace directory not found: {marketplace_dir}', file=sys.stderr)
        return EXIT_ERROR

    bundles = _parse_bundles(args.bundles)
    target_names = _resolve_targets(args.target)
    output_dir = args.output.resolve() if args.output is not None else None

    overall_ok = True
    for target_name in target_names:
        target_cls = TARGET_REGISTRY.get(target_name)
        if target_cls is None:
            print(f'error: unknown target {target_name!r}', file=sys.stderr)
            return EXIT_ERROR

        target = target_cls()
        per_target_output = output_dir / target_name if (output_dir is not None and args.target == 'all') else output_dir

        try:
            generated = target.generate(marketplace_dir, per_target_output, bundles=bundles)
        except NotImplementedError as exc:
            print(f'error: target {target_name!r} not yet implemented: {exc}', file=sys.stderr)
            overall_ok = False
            continue
        except Exception as exc:  # noqa: BLE001
            print(f'error: target {target_name!r} failed: {exc}', file=sys.stderr)
            overall_ok = False
            continue

        print(f'{target_name}: produced {len(generated)} entries')

    return EXIT_OK if overall_ok else EXIT_ERROR


if __name__ == '__main__':
    sys.exit(main())
