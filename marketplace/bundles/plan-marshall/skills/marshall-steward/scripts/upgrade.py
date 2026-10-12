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
  the root). It regenerates the target tree AND the executor, and
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
    2. reconcile-config    (mutating)  — reconcile marshal.json and migrate architecture descriptors
    3. verify              (read-only) — executor preflight (+ content drift on meta)
    4. land                (mutating)  — run the landing cycle

Per-stage ``sub_steps`` (the meta/consumer matrix):

    Stage 1 regenerate-targets  meta:     [regenerate-target-tree, regenerate-executor,
                                           cache-retention-sweep]
                                consumer: [cache-freshness-check, regenerate-executor,
                                           cache-retention-sweep]
    Stage 2 reconcile-config    both:     [migrate-review-steps, reconcile-marshal-json, review-held-defaults,
                                           migrate-bot-lists, validate-bot-lists,
                                           migrate-architecture-descriptors]
    Stage 3 verify              meta:     [executor-preflight, content-drift-report]
                                consumer: [executor-preflight]
    Stage 4 land                both:     [run-landing-cycle]

``migrate-architecture-descriptors`` has no subcommand here: the router drives
it through the existing ``manage-architecture`` verbs (``discover --force
--apply migration`` then ``descriptor-regression-check --pre-ref HEAD``), and
the migration it writes lands through Stage 4 with no commit of its own.

``review-held-defaults`` likewise has no subcommand: it is an agent-executed
sub-step, not a script verb. The agent running the upgrade holds the
``reconcile-marshal-json`` (``sync-defaults``) report returned by the
immediately-preceding call in the SAME run, reads its ``held_for_ask`` /
``re_added`` buckets, and asks the operator once per newly-discovered
not-yet-selected step (never auto-adding). A prior ``remove-step`` survives
the upgrade because ``sync-defaults`` is atomic-once-present on both step
maps — the sub-step only surfaces what was held, using the same ``re-add``
vs ``new default`` wording the sync report uses. A re-run recomputes the
buckets from the live maps (there is no durable declined record, so a
declined id is held again); the safety property is unaffected because
recomputation still never auto-adds.

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
    migrate-review-steps
                       Replace the retired structural self-review finalize step
                       by ``default:functional-review`` and ``default:code-review``,
                       carrying its setting to both. Driven as the FIRST
                       sub_step of Stage 2 (``reconcile-config``), before the
                       defaults merge.
    migrate-bot-lists  One-shot legacy auto-map of the retired ``enabled_bots``
                       knob onto ``required_bots`` / ``optional_bots``. Driven as
                       the ``migrate-bot-lists`` sub_step of Stage 2
                       (``reconcile-config``).
    validate-bot-lists Report any configured ``required_bots`` / ``optional_bots``
                       token that matches no registered reviewer, alongside the
                       live kind set it was checked against and the size of the
                       population actually checked. REPORTS ONLY — it never
                       rewrites ``marshal.json``. Driven as the
                       ``validate-bot-lists`` sub_step of Stage 2
                       (``reconcile-config``).

Usage:
    python3 upgrade.py plan
    python3 upgrade.py plan --integrate true
    python3 upgrade.py plan --project-kind consumer
    python3 upgrade.py migrate-review-steps
    python3 upgrade.py migrate-bot-lists
    python3 upgrade.py validate-bot-lists

Output (TOON):
    status: success
    integrate: false
    project_kind: meta
    stages[4]{order,key,name,mutating,top_level_gate,nested_gates,sub_steps}:
    1,regenerate-targets,Regenerate targets,true,prompt,"[]","[\"regenerate-target-tree\", \"regenerate-executor\"]"
    ...

Exit 0 on success, 2 on argparse rejection.

``main`` is wrapped in ``file_ops.safe_main``, so stdout carries parseable TOON
on EVERY path — including an unexpected exception, which is rendered as
``status: error`` / ``error: internal_error`` at exit 1 rather than a traceback
on stderr and an empty stdout. A caller parsing this script's output therefore
never has to distinguish "no output" from "output it could not read". A refused
save (another writer committed to marshal.json in between) is not a crash: it is
reported as ``error_type: concurrent_modification`` at exit 0.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# Cross-skill imports resolve through the PYTHONPATH the executor injects. This
# script is Stage 2 (reconcile-config) of the upgrade flow, which runs AFTER
# Stage 1 has regenerated the executor, so there is no pre-executor window to
# bootstrap around and the imports are written plainly.
import bot_registry
from file_ops import safe_main
from toon_parser import serialize_toon

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
        'sub_steps': [
            'migrate-review-steps',
            'reconcile-marshal-json',
            'review-held-defaults',
            'migrate-bot-lists',
            'validate-bot-lists',
            'migrate-architecture-descriptors',
        ],
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
# SHIM(A): the retired enabled_bots knob (seeded into required_bots/optional_bots and deleted).
# shim-owner: marshall-steward
# shim-floor: the two-list participation model (required_bots/optional_bots) that replaced the enabled_bots knob
# shim-remove-when: no live marshal.json carries the enabled_bots knob (idempotent)
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

    A project with NO marshal.json at all is likewise a no-op success rather than a
    ``FileNotFoundError`` escaping the verb: this migration runs as a sub-step of
    the steward upgrade flow, and an un-initialized project has no legacy
    ``enabled_bots`` value to migrate. The guard is on a real filesystem boundary
    the caller can genuinely present, not a speculative one.

    A concurrent writer that commits to marshal.json between the load and the
    save is reported as ``error_type: concurrent_modification`` at exit 0 — the
    migration refused to overwrite that writer's change, which is a recoverable
    outcome (re-run the upgrade) rather than a crash. Without this clause the
    refusal reached ``@safe_main`` and surfaced as an ``internal_error`` at exit
    1, telling the operator the steward broke when in fact it declined to
    destroy data.
    """
    from _config_core import (
        ConcurrentConfigModificationError,
        is_initialized,
        load_config,
        save_config,
    )

    if not is_initialized():
        return {
            'status': 'success',
            'operation': 'migrate-bot-lists',
            'state': 'noop',
            'detail': 'no marshal.json — project not initialized, nothing to migrate',
        }

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
        try:
            save_config(config)
        except ConcurrentConfigModificationError as exc:
            return {
                'status': 'error',
                'operation': 'migrate-bot-lists',
                'error': str(exc),
                'error_type': 'concurrent_modification',
            }
    return {'status': 'success', 'operation': 'migrate-bot-lists', **report}


# ---------------------------------------------------------------------------
# validate-bot-lists — report configured reviewer names no registry entry answers to
# ---------------------------------------------------------------------------
#
# The config-read-time counterpart of the participation barrier: it reaches a
# stale or misspelled reviewer token BEFORE any pull request exists, where the
# remedy is a one-line config edit rather than a stalled merge gate.
#
# It REPORTS ONLY, and both halves of that are load-bearing. It drops no token —
# a silent drop is the very collapse this surface exists to remove — and it
# rejects no list, because the fail-closed participation barrier already blocks
# on an unregistered name, so refusing here would turn a one-token typo into an
# unstartable finalize without catching anything the barrier misses.


def _split_bot_list(raw: object) -> list[str]:
    """Split one comma-separated bot-list value into its non-empty tokens.

    Mirrors how the participation step reads the same knobs: comma-separated,
    whitespace-insensitive, with empty segments ignored so a trailing comma or an
    empty value contributes no token rather than an empty one. A non-string value
    yields no tokens — it is a malformed knob, not a reviewer name.
    """
    if not isinstance(raw, str):
        return []
    return [token.strip() for token in raw.split(',') if token.strip()]


def validate_bot_lists(params: dict) -> dict:
    """Report the configured reviewer tokens that match no registered bot kind.

    Pure function over ONE step's param object, modelled on
    :func:`migrate_bot_lists` — except that it MUTATES NOTHING. It splits
    ``required_bots`` and ``optional_bots``, checks each token against
    ``bot_registry.bot_kinds()``, and returns a report.

    The report carries three things, and the third is what makes the other two
    trustworthy (ADR-019 — a surface that measures reports its coverage beside its
    result):

    * ``unknown_tokens`` — the configured names no registered reviewer answers to,
      in first-seen order and de-duplicated, so a name configured in BOTH lists is
      reported once. Never a rejection: the token stays in ``marshal.json``.
    * ``known_bot_kinds`` — the live registry kind set the tokens were checked
      against. It is the REMEDY for an unknown token, not decoration: an operator
      told a name is wrong still has to be told which names are right, and this is
      also the set the corrected token must be chosen from.
    * ``checked_count`` — the size of the population actually validated. Without it
      a clean verdict is ambiguous in exactly the direction that does harm: "no
      unknown tokens among the three configured" and "no tokens configured at all"
      both render as an empty ``unknown_tokens``, and the second is not a clean
      bill of health. A caller reads ``checked_count`` to tell them apart.

    ``bot_registry.bot_kinds()`` is consumed as-is — no accessor is added here, so a
    reviewer added or removed in a standards doc changes this check with no edit to
    this module.

    A registry that resolved no bots at all does not need a third state here. The
    failure would surface as EVERY configured token reading unknown beside an empty
    ``known_bot_kinds`` — loud and self-describing — rather than as the silent clean
    verdict ADR-019's third-state obligation exists to prevent.

    Args:
        params: The ``plan-marshall:automatic-review`` step's param object. Read
            only; this function never writes to it.

    Returns:
        A report dict: ``state`` (``clean`` when every checked token is registered,
        ``unknown_tokens`` when at least one is not), plus ``unknown_tokens``,
        ``known_bot_kinds`` and ``checked_count``.
    """
    known = bot_registry.bot_kinds()
    checked_count = 0
    unknown: list[str] = []
    for key in (_REQUIRED_BOTS_KEY, _OPTIONAL_BOTS_KEY):
        for token in _split_bot_list(params.get(key)):
            checked_count += 1
            if token not in known and token not in unknown:
                unknown.append(token)
    return {
        'state': 'unknown_tokens' if unknown else 'clean',
        'unknown_tokens': unknown,
        'known_bot_kinds': known,
        'checked_count': checked_count,
    }


def cmd_validate_bot_lists(_args: argparse.Namespace) -> dict:
    """Handle the ``validate-bot-lists`` subcommand against the live marshal.json.

    The thin CLI verb over :func:`validate_bot_lists`, reading ``marshal.json``
    through the same path :func:`cmd_migrate_bot_lists` uses. It **never calls**
    ``save_config``: this verb reports, and a reporting verb that can write is one
    an operator has to audit before trusting.

    Two states carry no verdict at all, and both are typed no-op successes rather
    than tracebacks — the same two real filesystem boundaries the migration verb
    already treats that way. A project with NO ``marshal.json`` is un-initialized
    and has no reviewer configuration to check; a project whose config carries no
    ``plan-marshall:automatic-review`` step has no configured reviewer names either.

    ⛔ Both return ``state: noop`` and deliberately carry NO ``checked_count``. The
    absence is the contract (ADR-019): a ``checked_count: 0`` published by a run
    that never looked is indistinguishable from a genuine "looked, found nothing
    configured", so a consumer branching on the count finds no key rather than a
    false zero. Read ``state`` first.
    """
    from _config_core import is_initialized, load_config

    if not is_initialized():
        return {
            'status': 'success',
            'operation': 'validate-bot-lists',
            'state': 'noop',
            'detail': 'no marshal.json — project not initialized, nothing to validate',
        }

    config = load_config()
    steps = (config.get('plan', {}).get('phase-6-finalize', {}) or {}).get('steps') or {}
    params = steps.get(_AUTOMATIC_REVIEW_STEP_ID)
    if not isinstance(params, dict):
        return {
            'status': 'success',
            'operation': 'validate-bot-lists',
            'state': 'noop',
            'detail': f'no {_AUTOMATIC_REVIEW_STEP_ID} step configured',
        }

    return {'status': 'success', 'operation': 'validate-bot-lists', **validate_bot_lists(params)}


# ---------------------------------------------------------------------------
# migrate-review-steps — the retired structural self-review onto the two reviews
# ---------------------------------------------------------------------------
#
# The single structural self-review step was split into the functional review
# and the code review, each switched by its own setting. A configured repository
# still names the retired step in its finalize step map, so this migration
# replaces it IN PLACE by the two successors and carries its setting to both.
#
# It runs before Stage 2's defaults merge, so the merge already sees the two new
# ids as present instead of holding them at its ask-before-add gate. It is
# idempotent and SELF-DISARMING: once the retired id is gone, a re-run is a
# no-op success.

_FUNCTIONAL_REVIEW_STEP_ID = 'default:functional-review'
_CODE_REVIEW_STEP_ID = 'default:code-review'
#: The successors, in the order they replace the retired entry.
_REVIEW_SUCCESSOR_STEP_IDS = (_FUNCTIONAL_REVIEW_STEP_ID, _CODE_REVIEW_STEP_ID)
_LANE_KEY = 'lane'
_LANE_OFF = 'off'
# SHIM(A): the retired structural self-review step and its settings (replaced by the functional and the code review).
# shim-owner: marshall-steward
# shim-floor: the split of the pre-submission self-review into default:functional-review and default:code-review, each switched by its own lane
# shim-remove-when: no live marshal.json names pre-submission-self-review in its finalize steps or removed_steps (idempotent)
_LEGACY_REVIEW_STEP_IDS = ('default:pre-submission-self-review', 'pre-submission-self-review')
_LEGACY_SELF_REVIEW_KEY = 'self_review'
#: A legacy step-owned self_review run-at-all value onto a successor lane; ``auto``
#: maps to no lane, which leaves the carried lane in force.
_LEGACY_SELF_REVIEW_TO_LANE = {'never': 'off', 'always': 'minimal'}
_LEGACY_SELF_REVIEW_AUTO = 'auto'


def _bare_step_id(step_id: str) -> str:
    return step_id[len('default:') :] if step_id.startswith('default:') else step_id


def _carried_review_params(legacy: object) -> tuple[dict, list[str]]:
    """Split the retired entry's params into what both successors inherit and what is dropped.

    The entry's ``lane`` is carried. A legacy ``self_review`` run-at-all value is
    the same setting in its retired spelling, so ``never`` / ``always`` map to
    ``off`` / ``minimal``; ``auto`` adds no lane. When the two disagree, the rule
    :func:`_merged_review_params` applies across entries holds inside one entry
    too: ``off`` wins, otherwise the mapped ``self_review`` value wins, and the
    losing setting is reported as dropped. A ``lane`` that is not a non-empty
    string, a ``self_review`` value other than ``never`` / ``always`` / ``auto``,
    and every other param — ``drop_review_on_scope_gate`` among them — have no
    successor and are reported as dropped, ``key=value``.
    """
    params = legacy if isinstance(legacy, dict) else {}
    carried: dict = {}
    dropped: list[str] = []
    lane = params.get(_LANE_KEY)
    if isinstance(lane, str) and lane:
        carried[_LANE_KEY] = lane
    elif _LANE_KEY in params:
        dropped.append(f'{_LANE_KEY}={json.dumps(lane)}')
    legacy_gate = params.get(_LEGACY_SELF_REVIEW_KEY)
    mapped = _LEGACY_SELF_REVIEW_TO_LANE.get(legacy_gate) if isinstance(legacy_gate, str) else None
    if mapped is None and _LEGACY_SELF_REVIEW_KEY in params and legacy_gate != _LEGACY_SELF_REVIEW_AUTO:
        dropped.append(f'{_LEGACY_SELF_REVIEW_KEY}={json.dumps(legacy_gate)}')
    if mapped is not None:
        current = carried.get(_LANE_KEY)
        if current is None or current == mapped:
            carried[_LANE_KEY] = mapped
        elif current == _LANE_OFF:
            dropped.append(f'{_LEGACY_SELF_REVIEW_KEY}={json.dumps(legacy_gate)}')
        else:
            carried[_LANE_KEY] = mapped
            dropped.append(f'{_LANE_KEY}={json.dumps(current)}')
    dropped.extend(
        f'{key}={json.dumps(value)}' for key, value in params.items() if key not in (_LANE_KEY, _LEGACY_SELF_REVIEW_KEY)
    )
    return carried, dropped


def _merged_review_params(entries: list[object]) -> tuple[dict, list[str]]:
    """Merge the carried and dropped params of every retired entry, in key order.

    A config may name the retired step in both spellings; no entry's setting is
    discarded silently. Each entry's params are derived by
    :func:`_carried_review_params` and their dropped params united, each listed
    once. When the entries carry different lanes, ``off`` wins — an operator who
    switched the review off in either spelling keeps it off — and otherwise the
    first entry's lane wins; every losing lane is reported in ``dropped_params``.
    """
    carried: dict = {}
    dropped: list[str] = []

    def _drop(item: str) -> None:
        if item not in dropped:
            dropped.append(item)

    for entry in entries:
        params, entry_dropped = _carried_review_params(entry)
        for item in entry_dropped:
            _drop(item)
        lane = params.get(_LANE_KEY)
        current = carried.get(_LANE_KEY)
        if lane is None or lane == current:
            continue
        if current is None:
            carried[_LANE_KEY] = lane
            continue
        winner, loser = (lane, current) if lane == _LANE_OFF else (current, lane)
        carried[_LANE_KEY] = winner
        _drop(f'{_LANE_KEY}={json.dumps(loser)}')
    return carried, dropped


def migrate_review_steps(section: dict) -> dict:
    """Replace the retired self-review step by the functional and the code review.

    Pure function over the ``plan.phase-6-finalize`` section. It mutates
    ``section`` in place and returns a report.

    In the ``steps`` map, every key naming the retired step (its ``default:`` or
    bare form) is removed, and the two successors are inserted at the position of
    the first one, functional review first. Both inherit the params
    :func:`_merged_review_params` derives from every retired entry — both
    spellings, when both are present. A successor the operator already
    configured is not inserted again: ITS ENTRY WINS, untouched, wherever it sits.

    In the operator ``removed_steps`` list, a retired id is replaced by both
    successor ids, so a review the operator removed stays removed under its new
    names.

    Args:
        section: The ``plan.phase-6-finalize`` section of marshal.json.

    Returns:
        A report dict: ``state`` (``migrated`` or ``noop``), and on ``migrated``
        the ``replaced`` legacy keys, the ``added`` successors, the successors
        ``kept`` as the operator configured them, and whether
        ``removed_steps_rewritten``. The ``carried`` params and the
        ``dropped_params`` are present only when a retired step entry was
        replaced, not when only ``removed_steps`` named a retired id.
    """
    from _config_defaults import OPERATOR_REMOVED_STEPS_KEY

    steps = section.get('steps')
    steps = steps if isinstance(steps, dict) else {}
    legacy_keys = [key for key in steps if key in _LEGACY_REVIEW_STEP_IDS]
    removed = section.get(OPERATOR_REMOVED_STEPS_KEY)
    removed = removed if isinstance(removed, list) else []
    removed_hits = [entry for entry in removed if entry in _LEGACY_REVIEW_STEP_IDS]
    if not legacy_keys and not removed_hits:
        return {'state': 'noop'}

    report: dict = {'state': 'migrated', 'replaced': legacy_keys, 'added': [], 'kept': []}
    if legacy_keys:
        carried, dropped = _merged_review_params([steps[key] for key in legacy_keys])
        present = {_bare_step_id(key) for key in steps}
        rebuilt: dict = {}
        for key, value in steps.items():
            if key in _LEGACY_REVIEW_STEP_IDS:
                if key == legacy_keys[0]:
                    for successor in _REVIEW_SUCCESSOR_STEP_IDS:
                        if _bare_step_id(successor) in present:
                            continue
                        rebuilt[successor] = dict(carried)
                        report['added'].append(successor)
                continue
            rebuilt[key] = value
        report['kept'] = [s for s in _REVIEW_SUCCESSOR_STEP_IDS if s not in report['added']]
        # Only an inserted successor inherits anything; a kept one keeps its own params,
        # so with no successor inserted the retired entry's carried settings are dropped.
        report['carried'] = [f'{key}={value}' for key, value in carried.items()] if report['added'] else []
        if not report['added']:
            dropped.extend(f'{key}={json.dumps(value)}' for key, value in carried.items())
        report['dropped_params'] = dropped
        section['steps'] = rebuilt

    report['removed_steps_rewritten'] = bool(removed_hits)
    if removed_hits:
        rewritten: list[str] = []
        for entry in removed:
            replacements = list(_REVIEW_SUCCESSOR_STEP_IDS) if entry in _LEGACY_REVIEW_STEP_IDS else [entry]
            rewritten.extend(item for item in replacements if item not in rewritten)
        section[OPERATOR_REMOVED_STEPS_KEY] = rewritten
    return report


def cmd_migrate_review_steps(_args: argparse.Namespace) -> dict:
    """Handle the ``migrate-review-steps`` subcommand against the live marshal.json.

    Loads marshal.json, applies :func:`migrate_review_steps` to the
    ``plan.phase-6-finalize`` section, and writes the config back only when the
    migration changed something. An un-initialized project and a config without a
    finalize section are no-op successes, and a concurrent writer is reported as
    ``error_type: concurrent_modification`` at exit 0 — the same boundaries
    :func:`cmd_migrate_bot_lists` treats that way.
    """
    from _config_core import (
        ConcurrentConfigModificationError,
        is_initialized,
        load_config,
        save_config,
    )

    if not is_initialized():
        return {
            'status': 'success',
            'operation': 'migrate-review-steps',
            'state': 'noop',
            'detail': 'no marshal.json — project not initialized, nothing to migrate',
        }

    config = load_config()
    section = (config.get('plan') or {}).get('phase-6-finalize')
    if not isinstance(section, dict):
        return {
            'status': 'success',
            'operation': 'migrate-review-steps',
            'state': 'noop',
            'detail': 'no plan.phase-6-finalize section configured',
        }

    report = migrate_review_steps(section)
    if report['state'] != 'noop':
        try:
            save_config(config)
        except ConcurrentConfigModificationError as exc:
            return {
                'status': 'error',
                'operation': 'migrate-review-steps',
                'error': str(exc),
                'error_type': 'concurrent_modification',
            }
    return {'status': 'success', 'operation': 'migrate-review-steps', **report}


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


@safe_main
def main() -> int:
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
        'migrate-review-steps',
        help=(
            'Replace the retired structural self-review finalize step by the functional '
            'and the code review, carrying its setting to both. Idempotent and self-disarming.'
        ),
        allow_abbrev=False,
    )

    subparsers.add_parser(
        'migrate-bot-lists',
        help=(
            'One-shot legacy auto-map of the retired enabled_bots knob onto '
            'required_bots / optional_bots. Idempotent and self-disarming.'
        ),
        allow_abbrev=False,
    )

    subparsers.add_parser(
        'validate-bot-lists',
        help=(
            'Report required_bots / optional_bots tokens that match no registered '
            'bot kind, with the live kind set and the checked population size. '
            'Reports only — never rewrites marshal.json.'
        ),
        allow_abbrev=False,
    )

    args = parser.parse_args()

    if args.command == 'plan':
        result = cmd_plan(args)
    elif args.command == 'migrate-review-steps':
        result = cmd_migrate_review_steps(args)
    elif args.command == 'migrate-bot-lists':
        result = cmd_migrate_bot_lists(args)
    elif args.command == 'validate-bot-lists':
        result = cmd_validate_bot_lists(args)
    else:  # pragma: no cover - argparse enforces a valid subcommand
        parser.print_help()
        return 2

    print(serialize_toon(result))
    return 0


if __name__ == '__main__':
    main()
