#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic stage-plan / gate-decision emitter for the ``upgrade`` verb.

``marshall-steward`` is a hybrid skill: an LLM workflow router plus
deterministic decision-emitter scripts (``determine_mode``) that the router
consumes. This script extends that model with the ``upgrade`` verb's planner.
It emits the fixed four-stage post-change-reconciliation plan and, for each
stage, the top-level-gate disposition as a pure function of ``--integrate``.

It is a **pure function**: it invokes no machinery, mutates no filesystem,
and makes no git/CI calls. The LLM reference (``references/upgrade-flow.md``)
consumes this plan and drives each stage's existing machinery, honouring the
emitted gate dispositions.

The four stages are fixed and ordered:

    1. regenerate-targets  (mutating)  — regenerate target/claude + executor
    2. reconcile-config    (mutating)  — reconcile marshal.json
    3. verify              (read-only) — executor preflight + content-drift report
    4. land                (mutating)  — run the landing cycle

Gate model:

* ``top_level_gate`` is ``suppressed`` for every stage when ``--integrate true``
  and ``prompt`` otherwise. ``integrate=true`` suppresses ONLY the four
  top-level stage gates.
* ``nested_gates`` are ``integrate``-invariant — they still prompt under
  ``integrate=true``: ``build-map-reseed`` on ``reconcile-config``;
  ``land-leave`` + ``branch-reuse`` on ``land``; none elsewhere.

Subcommand:
    plan  Emit the stage plan. ``--integrate {true|false}`` (default ``false``).

Usage:
    python3 upgrade.py plan
    python3 upgrade.py plan --integrate true

Output (TOON):
    status: success
    integrate: false
    stages[4]{order,key,name,mutating,top_level_gate,nested_gates}:
    1,regenerate-targets,Regenerate targets,true,prompt,"[]"
    2,reconcile-config,Reconcile config,true,prompt,"[\"build-map-reseed\"]"
    3,verify,Verify,false,prompt,"[]"
    4,land,Land,true,prompt,"[\"land-leave\", \"branch-reuse\"]"

Exit 0 on success, 2 on argparse rejection.
"""

from __future__ import annotations

import argparse
import sys

# The fixed four-stage plan. Each spec is ``integrate``-invariant except for
# ``top_level_gate``, which build_plan() fills from the ``integrate`` flag.
# ``nested_gates`` are declared here and never vary with ``integrate``.
_STAGE_SPECS: list[dict] = [
    {'order': 1, 'key': 'regenerate-targets', 'name': 'Regenerate targets', 'mutating': True, 'nested_gates': []},
    {
        'order': 2,
        'key': 'reconcile-config',
        'name': 'Reconcile config',
        'mutating': True,
        'nested_gates': ['build-map-reseed'],
    },
    {'order': 3, 'key': 'verify', 'name': 'Verify', 'mutating': False, 'nested_gates': []},
    {'order': 4, 'key': 'land', 'name': 'Land', 'mutating': True, 'nested_gates': ['land-leave', 'branch-reuse']},
]


def build_plan(integrate: bool) -> dict:
    """Build the deterministic stage plan for the given ``integrate`` flag.

    Pure function: constructs the plan dict from :data:`_STAGE_SPECS` with each
    stage's ``top_level_gate`` set to ``suppressed`` when ``integrate`` is True
    and ``prompt`` otherwise. ``nested_gates`` are copied verbatim (they never
    vary with ``integrate``).

    Args:
        integrate: When True, all four top-level stage gates are suppressed.

    Returns:
        The plan dict — ``status``, the echoed ``integrate`` flag, and the
        ``stages`` list. Each stage dict's key order matches the documented
        ``{order,key,name,mutating,top_level_gate,nested_gates}`` column order.
    """
    top_level_gate = 'suppressed' if integrate else 'prompt'
    stages = [
        {
            'order': spec['order'],
            'key': spec['key'],
            'name': spec['name'],
            'mutating': spec['mutating'],
            'top_level_gate': top_level_gate,
            'nested_gates': list(spec['nested_gates']),
        }
        for spec in _STAGE_SPECS
    ]
    return {'status': 'success', 'integrate': integrate, 'stages': stages}


def cmd_plan(args: argparse.Namespace) -> dict:
    """Handle the ``plan`` subcommand."""
    integrate = args.integrate == 'true'
    return build_plan(integrate)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='upgrade',
        description="Emit the marshall-steward 'upgrade' verb stage plan and per-stage gate dispositions.",
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    plan_parser = subparsers.add_parser(
        'plan',
        help='Emit the fixed four-stage upgrade plan with per-stage gate dispositions.',
        allow_abbrev=False,
    )
    plan_parser.add_argument(
        '--integrate',
        choices=['true', 'false'],
        default='false',
        help='When true, suppress the four top-level stage gates (nested gates still prompt). Default: false.',
    )

    args = parser.parse_args(argv)

    if args.command == 'plan':
        result = cmd_plan(args)
    else:  # pragma: no cover - argparse enforces a valid subcommand
        parser.print_help()
        return 2

    from toon_parser import serialize_toon

    print(serialize_toon(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
