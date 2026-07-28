#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic stage-plan / gate-decision emitter for the ``upgrade`` verb.

``marshall-steward`` is a hybrid skill: an LLM workflow router plus
deterministic decision-emitter scripts (``determine_mode``) that the router
consumes. This script extends that model with the ``upgrade`` verb's planner.
It emits the fixed four-stage post-change-reconciliation plan and, for each
stage, the top-level-gate disposition and the ordered ``sub_steps`` the router
must drive.

The plan is a **pure function of ``(integrate, project_kind)``**: the script
invokes no machinery, mutates no filesystem, and makes no git/CI calls. Only
``project-kind`` resolution in ``auto`` mode performs a read-only filesystem
presence check (``detect_project_kind``); the pure builder ``build_plan`` takes
an explicit kind and stays directly testable. The LLM reference
(``references/upgrade-flow.md``) consumes this plan and drives each stage's
``sub_steps`` against the existing machinery, honouring the emitted gate
dispositions.

Project kinds:

* ``meta``     — the plan-marshall meta-project itself (BOTH
  ``marketplace/targets/generate.py`` and ``marketplace/bundles/`` exist under
  the root). It regenerates the ``target/claude`` tree AND the executor, and
  verifies with executor preflight AND a content-drift report.
* ``consumer`` — a downstream project that consumes plan-marshall (the
  meta-only marketplace surface is absent). It gates on plugin-cache freshness
  (``cache-freshness-check``), regenerates ONLY the executor, and verifies with
  executor preflight ONLY. The meta-only sub-steps (``regenerate-target-tree``
  in Stage 1, ``content-drift-report`` in Stage 3) are absent from a consumer
  plan and MUST NOT be attempted. The freshness gate is consumer-only: the meta
  project refreshes its own cache through
  ``project:finalize-step-sync-plugin-cache``, a surface consumers do not have.

The four stages are fixed and ordered:

    1. regenerate-targets  (mutating)  — regenerate target tree and/or executor
    2. reconcile-config    (mutating)  — reconcile marshal.json
    3. verify              (read-only) — executor preflight (+ content drift on meta)
    4. land                (mutating)  — run the landing cycle

Per-stage ``sub_steps`` (the meta/consumer matrix):

    Stage 1 regenerate-targets  meta:     [regenerate-target-tree, regenerate-executor,
                                           cache-retention-sweep]
                                consumer: [cache-freshness-check, regenerate-executor,
                                           cache-retention-sweep]
    Stage 2 reconcile-config    both:     [reconcile-marshal-json, migrate-bot-lists]
    Stage 3 verify              meta:     [executor-preflight, content-drift-report]
                                consumer: [executor-preflight]
    Stage 4 land                both:     [run-landing-cycle]

Gate model:

* ``top_level_gate`` is ``suppressed`` for every stage when ``--integrate true``
  and ``prompt`` otherwise. ``integrate=true`` suppresses ONLY the four
  top-level stage gates.
* ``nested_gates`` are ``integrate``-invariant — they still prompt under
  ``integrate=true``: ``cache-retention-prune`` on ``regenerate-targets``
  (the destructive apply of the retention sweep);
  ``build-map-reseed`` on ``reconcile-config``; ``land-leave`` +
  ``branch-reuse`` on ``land``; none elsewhere.

Subcommands:
    plan               Emit the stage plan. ``--integrate {true|false}`` (default
                       ``false``) and ``--project-kind {auto|meta|consumer}``
                       (default ``auto``).
    migrate-bot-lists  One-shot legacy auto-map of the retired ``enabled_bots``
                       knob onto ``required_bots`` / ``optional_bots``. Driven as
                       the ``migrate-bot-lists`` sub_step of Stage 2
                       (``reconcile-config``).

Usage:
    python3 upgrade.py plan
    python3 upgrade.py plan --integrate true
    python3 upgrade.py plan --project-kind consumer
    python3 upgrade.py migrate-bot-lists

Output (TOON):
    status: success
    integrate: false
    project_kind: meta
    stages[4]{order,key,name,mutating,top_level_gate,nested_gates,sub_steps}:
    1,regenerate-targets,Regenerate targets,true,prompt,"[]","[\"regenerate-target-tree\", \"regenerate-executor\"]"
    ...

Exit 0 on success, 2 on argparse rejection.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# The fixed four-stage plan. Each spec is ``integrate``-invariant except for
# ``top_level_gate``, which build_plan() fills from the ``integrate`` flag.
# ``nested_gates`` are declared here and never vary with ``integrate``.
#
# ``sub_steps`` is either a plain list (kind-invariant — stages 2 and 4) or a
# ``{project_kind: [...]}`` dict (kind-dependent — stages 1 and 3, where the
# meta-only sub-steps are dropped for a consumer). build_plan() resolves the
# per-kind list via :func:`_resolve_sub_steps`.
_STAGE_SPECS: list[dict] = [
    {
        'order': 1,
        'key': 'regenerate-targets',
        'name': 'Regenerate targets',
        'mutating': True,
        'nested_gates': ['cache-retention-prune'],
        'sub_steps': {
            'meta': ['regenerate-target-tree', 'regenerate-executor', 'cache-retention-sweep'],
            'consumer': ['cache-freshness-check', 'regenerate-executor', 'cache-retention-sweep'],
        },
    },
    {
        'order': 2,
        'key': 'reconcile-config',
        'name': 'Reconcile config',
        'mutating': True,
        'nested_gates': ['build-map-reseed'],
        'sub_steps': ['reconcile-marshal-json', 'migrate-bot-lists'],
    },
    {
        'order': 3,
        'key': 'verify',
        'name': 'Verify',
        'mutating': False,
        'nested_gates': [],
        'sub_steps': {
            'meta': ['executor-preflight', 'content-drift-report'],
            'consumer': ['executor-preflight'],
        },
    },
    {
        'order': 4,
        'key': 'land',
        'name': 'Land',
        'mutating': True,
        'nested_gates': ['land-leave', 'branch-reuse'],
        'sub_steps': ['run-landing-cycle'],
    },
]

_PROJECT_KINDS = ('meta', 'consumer')


def detect_project_kind(root: Path) -> str:
    """Classify ``root`` as ``meta`` or ``consumer`` by filesystem presence.

    A pure read-only presence check — no mutation, no git/CI. A directory is
    ``meta`` (the plan-marshall meta-project itself) only when BOTH the target
    generator (``marketplace/targets/generate.py``) and the bundle source tree
    (``marketplace/bundles/``) exist under ``root``; every other tree is a
    ``consumer`` of plan-marshall.

    Args:
        root: The project root to classify.

    Returns:
        ``'meta'`` or ``'consumer'``.
    """
    generate_py = root / 'marketplace' / 'targets' / 'generate.py'
    bundles_dir = root / 'marketplace' / 'bundles'
    if generate_py.is_file() and bundles_dir.is_dir():
        return 'meta'
    return 'consumer'


def _resolve_sub_steps(spec_sub_steps: list | dict, project_kind: str) -> list[str]:
    """Resolve a stage spec's ``sub_steps`` for ``project_kind``.

    A plain-list spec is kind-invariant and returned as a copy; a
    ``{project_kind: [...]}`` dict spec selects the per-kind list.
    """
    if isinstance(spec_sub_steps, dict):
        return list(spec_sub_steps[project_kind])
    return list(spec_sub_steps)


def build_plan(integrate: bool, project_kind: str) -> dict:
    """Build the deterministic stage plan for ``(integrate, project_kind)``.

    Pure function: constructs the plan dict from :data:`_STAGE_SPECS` with each
    stage's ``top_level_gate`` set to ``suppressed`` when ``integrate`` is True
    and ``prompt`` otherwise, and each stage's ``sub_steps`` resolved for
    ``project_kind`` (meta-only sub-steps dropped on a consumer).
    ``nested_gates`` are copied verbatim (they never vary with ``integrate`` or
    ``project_kind``).

    Args:
        integrate: When True, all four top-level stage gates are suppressed.
        project_kind: ``'meta'`` or ``'consumer'`` — selects each stage's
            per-kind ``sub_steps``.

    Returns:
        The plan dict — ``status``, the echoed ``integrate`` flag, the echoed
        ``project_kind``, and the ``stages`` list. Each stage dict's key order
        matches the documented
        ``{order,key,name,mutating,top_level_gate,nested_gates,sub_steps}``
        column order.

    Raises:
        ValueError: When ``project_kind`` is neither ``meta`` nor ``consumer``.
    """
    if project_kind not in _PROJECT_KINDS:
        raise ValueError(f'project_kind must be one of {_PROJECT_KINDS}, got {project_kind!r}')
    top_level_gate = 'suppressed' if integrate else 'prompt'
    stages = [
        {
            'order': spec['order'],
            'key': spec['key'],
            'name': spec['name'],
            'mutating': spec['mutating'],
            'top_level_gate': top_level_gate,
            'nested_gates': list(spec['nested_gates']),
            'sub_steps': _resolve_sub_steps(spec['sub_steps'], project_kind),
        }
        for spec in _STAGE_SPECS
    ]
    return {'status': 'success', 'integrate': integrate, 'project_kind': project_kind, 'stages': stages}


# ---------------------------------------------------------------------------
# migrate-bot-lists — one-shot legacy auto-map of the retired enabled_bots knob
# ---------------------------------------------------------------------------
#
# The retired ``enabled_bots`` knob is replaced by the two-list participation
# model (``required_bots`` / ``optional_bots``). This migration is deliberately
# hosted on the EXISTING upgrade entry point rather than as a new script, and is
# driven as the ``migrate-bot-lists`` sub_step of Stage 2 (reconcile-config).
#
# It is exhaustive over four input states and SELF-DISARMING — once the legacy
# key is gone, states (3) and (4) are indistinguishable and both are a no-op
# success, so re-running the upgrade verb is always safe.

_AUTOMATIC_REVIEW_STEP_ID = 'plan-marshall:automatic-review'
_LEGACY_BOT_LIST_KEY = 'enabled_bots'
_REQUIRED_BOTS_KEY = 'required_bots'
_OPTIONAL_BOTS_KEY = 'optional_bots'
_PROVENANCE_KEY = 'bot_lists_provenance'


def migrate_bot_lists(params: dict) -> dict:
    """Auto-map a retired ``enabled_bots`` value onto the two-list model.

    Pure function over ONE step's param object. It mutates ``params`` in place
    and returns a report describing which of the four input states applied.

    The four states are exhaustive:

    1. **legacy present, neither new key present** — seed ``required_bots`` from
       the legacy value VERBATIM, leave ``optional_bots`` empty, remove
       ``enabled_bots``, and record provenance ``migrated``. Seeding required (not
       optional) preserves the legacy semantics: every bot on the old list was
       awaited, and awaiting is exactly what ``required`` means.
    2. **legacy present, either new key already present** — the operator has
       already answered, so THEIR ANSWER WINS: the new keys are left untouched and
       only the stale legacy key is removed. Both values are reported so the
       operator can see what was discarded. Provenance is NOT downgraded to
       ``migrated`` — an answered value stays ``answered``.
    3. **legacy absent, neither new key present** — nothing to migrate; a no-op
       success that leaves the never-asked posture intact.
    4. **already migrated** — indistinguishable from (3) once the legacy key is
       gone. This is what makes the migration self-disarming and re-runnable.

    Args:
        params: The ``plan-marshall:automatic-review`` step's param object.

    Returns:
        A report dict: ``state`` (one of ``migrated`` / ``operator_answer_kept`` /
        ``noop``), plus ``required_bots`` / ``optional_bots`` (the resulting
        values) and, when a legacy value was discarded, ``discarded_legacy``.
    """
    legacy = params.get(_LEGACY_BOT_LIST_KEY)
    has_legacy = legacy is not None
    has_new = _REQUIRED_BOTS_KEY in params or _OPTIONAL_BOTS_KEY in params

    if not has_legacy:
        # States (3) and (4) — nothing to migrate, and deliberately
        # indistinguishable from each other.
        return {
            'state': 'noop',
            'required_bots': params.get(_REQUIRED_BOTS_KEY, ''),
            'optional_bots': params.get(_OPTIONAL_BOTS_KEY, ''),
        }

    if has_new:
        # State (2) — the operator already answered; their answer wins. Remove
        # only the stale legacy key.
        del params[_LEGACY_BOT_LIST_KEY]
        return {
            'state': 'operator_answer_kept',
            'required_bots': params.get(_REQUIRED_BOTS_KEY, ''),
            'optional_bots': params.get(_OPTIONAL_BOTS_KEY, ''),
            'discarded_legacy': legacy,
        }

    # State (1) — seed required from the legacy list verbatim.
    params[_REQUIRED_BOTS_KEY] = legacy
    params[_OPTIONAL_BOTS_KEY] = ''
    params[_PROVENANCE_KEY] = 'migrated'
    del params[_LEGACY_BOT_LIST_KEY]
    return {
        'state': 'migrated',
        'required_bots': legacy,
        'optional_bots': '',
    }


def cmd_migrate_bot_lists(_args: argparse.Namespace) -> dict:
    """Handle the ``migrate-bot-lists`` subcommand against the live marshal.json.

    Loads marshal.json, applies :func:`migrate_bot_lists` to the
    ``plan-marshall:automatic-review`` step's param object, and writes the config
    back only when the migration actually changed something. A project with no
    such step configured is a no-op success — the verb never fails merely because
    the automatic-review step is absent.
    """
    from _config_core import load_config, save_config

    config = load_config()
    steps = (config.get('plan', {}).get('phase-6-finalize', {}) or {}).get('steps') or {}
    params = steps.get(_AUTOMATIC_REVIEW_STEP_ID)
    if not isinstance(params, dict):
        return {
            'status': 'success',
            'operation': 'migrate-bot-lists',
            'state': 'noop',
            'detail': f'no {_AUTOMATIC_REVIEW_STEP_ID} step configured',
        }

    report = migrate_bot_lists(params)
    if report['state'] != 'noop':
        save_config(config)
    return {'status': 'success', 'operation': 'migrate-bot-lists', **report}


def cmd_plan(args: argparse.Namespace) -> dict:
    """Handle the ``plan`` subcommand.

    Resolves ``--project-kind auto`` via :func:`detect_project_kind` against the
    current working directory (keeping :func:`build_plan` pure and directly
    testable), then delegates to the pure builder.
    """
    integrate = args.integrate == 'true'
    project_kind = args.project_kind
    if project_kind == 'auto':
        project_kind = detect_project_kind(Path.cwd())
    return build_plan(integrate, project_kind)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='upgrade',
        description="Emit the marshall-steward 'upgrade' verb stage plan and per-stage gate dispositions.",
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    plan_parser = subparsers.add_parser(
        'plan',
        help='Emit the fixed four-stage upgrade plan with per-stage gate dispositions and sub_steps.',
        allow_abbrev=False,
    )
    plan_parser.add_argument(
        '--integrate',
        choices=['true', 'false'],
        default='false',
        help='When true, suppress the four top-level stage gates (nested gates still prompt). Default: false.',
    )
    plan_parser.add_argument(
        '--project-kind',
        choices=['auto', 'meta', 'consumer'],
        default='auto',
        help=(
            'Project kind driving each stage\'s sub_steps. "meta" regenerates the target tree + executor '
            'and verifies with preflight + content-drift; "consumer" regenerates the executor only and '
            'verifies with preflight only. "auto" (default) detects the kind from the cwd via a read-only '
            'marketplace/targets/generate.py + marketplace/bundles/ presence check.'
        ),
    )

    subparsers.add_parser(
        'migrate-bot-lists',
        help=(
            'One-shot legacy auto-map of the retired enabled_bots knob onto '
            'required_bots / optional_bots. Idempotent and self-disarming.'
        ),
        allow_abbrev=False,
    )

    args = parser.parse_args(argv)

    if args.command == 'plan':
        result = cmd_plan(args)
    elif args.command == 'migrate-bot-lists':
        result = cmd_migrate_bot_lists(args)
    else:  # pragma: no cover - argparse enforces a valid subcommand
        parser.print_help()
        return 2

    from toon_parser import serialize_toon

    print(serialize_toon(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
