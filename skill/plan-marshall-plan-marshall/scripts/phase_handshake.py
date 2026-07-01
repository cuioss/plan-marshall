#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Phase handshake: capture and verify cross-phase invariants.

Usage:
    phase_handshake.py capture        --plan-id X --phase P [--override --reason R]
    phase_handshake.py verify         --plan-id X --phase P [--strict]
    phase_handshake.py findings-check --plan-id X --phase P
    phase_handshake.py list           --plan-id X
    phase_handshake.py clear          --plan-id X --phase P

All subcommands emit TOON to stdout. `verify` with ``--strict`` exits 1 on
``status: drift`` so callers can gate progress at the CLI level.

``findings-check`` is a read-only single-invariant gate: it evaluates ONLY the
``pending_findings_blocking_count`` invariant (never ``phase_steps_complete``)
and writes NO handshake row. It exists for the intra-finalize boundaries where
the composite ``capture`` would short-circuit on ``phase_steps_incomplete``
because downstream finalize steps have not run yet. Its exit code follows the
``capture`` convention — a ``status: error`` payload still exits 0; the verdict
is carried entirely in the TOON ``status`` field.

Retained-vs-relaxed worktree-state drift map (Option 5' / ADR-002), keyed on
the boundary phase the handshake verifies (the phase transitioned OUT of):

    boundary           worktree-state drift checks
    -----------------  --------------------------------------------------
    1-init  → 2-refine  RETAINED (planning runs on main; leaks possible)
    2-refine → 3-outline RETAINED
    3-outline → 4-plan   RETAINED
    4-plan  → 5-execute  RETAINED
    5-execute → 6-finalize RELAXED  (cwd-pinned move model; checks moot)

The "worktree-state drift checks" relaxed at phase-5+ are the layer-D
leak-into-main guard (``main_dirty_files`` / ``_check_main_dirty_drift``) and
the sideways worktree invariants (``worktree_sha`` / ``worktree_dirty``).
Under the move-based, cwd-pinned hermetic worktree model
the worktree is materialized at phase-5 start and the plan dir is MOVED into
it; from then the orchestrator's cwd IS the worktree and the single
cwd-unchanged invariant (asserted by ``file_ops.guard_worktree_cwd``) keeps it
pinned there. Plan work lands in the worktree by construction, so a leak-into-
main guard and a sideways worktree-SHA comparison have nothing to catch at the
``5-execute → 6-finalize`` boundary. The relaxation is realized via the
per-phase blocking scope in ``_invariants.INVARIANT_BLOCKING_SCOPE`` and the
mirrored boundary-phase gate in ``_handshake_commands._check_main_dirty_drift``
— the discriminator is the boundary phase already known to the handshake, NOT
a runtime resolver branch, so the handshake never references a removed check at
a boundary that still needs it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _handshake_commands import (  # type: ignore[import-not-found]
    cmd_capture,
    cmd_clear,
    cmd_findings_check,
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

    findings_check = subparsers.add_parser(
        'findings-check',
        help='Read-only check of the blocking-findings invariant only (no row write)',
        allow_abbrev=False,
    )
    add_plan_id_arg(findings_check)
    add_phase_arg(findings_check)

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
    elif args.command == 'findings-check':
        result = cmd_findings_check(args)
    elif args.command == 'list':
        result = cmd_list(args)
    elif args.command == 'clear':
        result = cmd_clear(args)
    else:
        parser.print_help()
        return 2

    output_toon(result)

    if args.command == 'verify' and getattr(args, 'strict', False):
        if result.get('status') == 'drift':
            return 1
        # worktree_unresolved (metadata→disk) and
        # main_checkout_dirtied_during_plan (layer-D filesystem leak into
        # the main checkout during a worktree-routed plan) are both
        # phase-boundary refusals. Under --strict they MUST surface as a
        # non-zero exit so calling tooling that swallows TOON output still
        # sees the failure (mirrors the drift contract). Both share the same
        # severity: the operator must repair the disagreement (or revert the
        # leaked main-checkout changes) before any phase advance is allowed.
        if result.get('error') in (
            'worktree_unresolved',
            'main_checkout_dirtied_during_plan',
        ):
            return 1
    if result.get('status') == 'error':
        return 0
    return 0


if __name__ == '__main__':
    main()
