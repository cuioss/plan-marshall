#!/usr/bin/env python3
"""Phase handshake: capture and verify cross-phase invariants.

Usage:
    phase_handshake.py capture --plan-id X --phase P [--override --reason R]
    phase_handshake.py verify  --plan-id X --phase P [--strict]
    phase_handshake.py list    --plan-id X
    phase_handshake.py clear   --plan-id X --phase P

All subcommands emit TOON to stdout. `verify` with ``--strict`` exits 1 on
``status: drift`` so callers can gate progress at the CLI level.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _handshake_commands import (  # type: ignore[import-not-found]
    cmd_capture,
    cmd_clear,
    cmd_list,
    cmd_verify,
)
from file_ops import output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import (  # type: ignore[import-not-found]
    add_phase_arg,
    add_plan_id_arg,
    parse_args_with_toon_errors,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Phase handshake capture/verify', allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True)

    capture = subparsers.add_parser('capture', help='Capture invariants for a phase', allow_abbrev=False)
    add_plan_id_arg(capture)
    add_phase_arg(capture)
    capture.add_argument('--override', action='store_true', help='Mark as override capture')
    capture.add_argument('--reason', help='Reason required when --override is set')

    verify = subparsers.add_parser('verify', help='Verify invariants against a capture', allow_abbrev=False)
    add_plan_id_arg(verify)
    add_phase_arg(verify)
    verify.add_argument('--strict', action='store_true', help='Exit 1 on drift')

    listcmd = subparsers.add_parser('list', help='List all captured phases for a plan', allow_abbrev=False)
    add_plan_id_arg(listcmd)

    clear = subparsers.add_parser('clear', help='Remove a captured phase row', allow_abbrev=False)
    add_plan_id_arg(clear)
    add_phase_arg(clear)

    return parser


@safe_main
def main() -> int:
    parser = _build_parser()
    args = parse_args_with_toon_errors(parser)

    if args.command == 'capture':
        result = cmd_capture(args)
    elif args.command == 'verify':
        result = cmd_verify(args)
    elif args.command == 'list':
        result = cmd_list(args)
    elif args.command == 'clear':
        result = cmd_clear(args)
    else:
        parser.print_help()
        return 2

    output_toon(result)

    if args.command == 'verify' and getattr(args, 'strict', False) and result.get('status') == 'drift':
        return 1
    if result.get('status') == 'error':
        return 0
    return 0


if __name__ == '__main__':
    main()
