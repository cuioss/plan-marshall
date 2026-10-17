#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic stage-plan / gate-decision emitter for the ``upgrade`` verb.

``marshall-steward`` is a hybrid skill: an LLM workflow router plus
deterministic decision-emitter scripts (``determine_mode``) that the router
consumes. This script extends that model with the ``upgrade`` verb's planner.
It emits the fixed four-stage post-change-reconciliation plan and, for each
stage, the top-level-gate disposition and the ordered ``sub_steps`` the router
must drive.

The stage plan itself is a **pure function of ``(integrate, project_kind)``**
(emitted by :func:`build_plan`, which invokes no machinery, mutates no
filesystem, and makes no git/CI calls). The ``plan`` verb wraps that pure core
with the executor bootstrap (:func:`bootstrap_executor`): it validates the
serving executor against the newest plugin-cache version and regenerates it
from that cache when stale BEFORE emitting the stage plan, so the plan and
every downstream stage resolve current-version scripts. Only
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
    Stage 2 reconcile-config    both:     [reconcile-marshal-json, review-held-defaults,
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
    python3 upgrade.py plan --bootstrap true   # consent to rewrite a stale executor
    python3 upgrade.py migrate-bot-lists
    python3 upgrade.py validate-bot-lists

Output (TOON):
    status: success
    integrate: false
    project_kind: meta
    bootstrap: {status, action, executor_version, newest_cache_version, warning, ...}
    stages[4]{order,key,name,mutating,top_level_gate,nested_gates,sub_steps}:
    1,regenerate-targets,Regenerate targets,true,prompt,"[]","[\"regenerate-target-tree\", \"regenerate-executor\"]"
    ...

The ``bootstrap`` block reports the executor bootstrap (``fresh`` |
``regenerated`` | ``regenerate_required`` | ``no_cache`` |
``regenerate_failed`` | ``unknown``). Rewriting a merely-stale executor is gated
on ``--bootstrap true`` (default false — a stale executor reports
``regenerate_required`` and is left untouched); a missing-or-broken executor is
always restored from the newest cache. A ``warning`` names a skill/planner
version split and its remedy instead of a silently stale run.

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
import re
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
# The standard reviewer roster, single-sourced from manage-config's
# :mod:`_config_defaults` (the canonical host). The deferred import keeps this
# module importable where the sibling skill scripts are not on ``sys.path``
# (unit-test import topology); the fallback preserves the last-known literals
# for that topology only. The private aliases preserve this module's
# established names for existing readers.
try:
    from _config_defaults import STANDARD_OPTIONAL_BOTS, STANDARD_REQUIRED_BOTS
except ImportError:
    STANDARD_REQUIRED_BOTS = 'cuioss-review-bot,coderabbit'
    STANDARD_OPTIONAL_BOTS = 'sourcery'
_STANDARD_REQUIRED_BOTS = STANDARD_REQUIRED_BOTS
_STANDARD_OPTIONAL_BOTS = STANDARD_OPTIONAL_BOTS


def _has_operator_answer(params: dict) -> bool:
    """Return True when the operator has answered the two-list model.

    Only a non-empty value, or an explicit ``bot_lists_provenance: answered``,
    counts — mere key presence does not. A ``sync-defaults`` back-fill writes
    empty strings for absent keys, and treating that presence as an answer is
    what deleted the legacy list without migrating it.
    """
    if params.get(_PROVENANCE_KEY) == 'answered':
        return True
    required = params.get(_REQUIRED_BOTS_KEY)
    if isinstance(required, str) and required.strip():
        return True
    optional = params.get(_OPTIONAL_BOTS_KEY)
    if isinstance(optional, str) and optional.strip():
        return True
    return False


def _named_discarded_bots(legacy: object) -> list[str]:
    """Return the individual bot names carried by a raw ``enabled_bots`` value.

    Accepts the raw value as read off the step's param object (``object`` — its
    static type there is ``Any | None``) and coerces it to text before splitting.
    The migration reports each discarded bot BY NAME rather than echoing the raw
    CSV string, so a dropped bot — including one the registry does not know — is
    visible to the operator (and to :func:`validate_bot_lists`) by name.
    """
    return [name.strip() for name in str(legacy).split(',') if name.strip()]


def migrate_bot_lists(params: dict) -> dict:
    """Auto-map a retired ``enabled_bots`` value onto the two-list model.

    Pure function over ONE step's param object. It mutates ``params`` in place
    and returns a report describing which of the four input states applied.

    The four states are exhaustive:

    1. **legacy present, no operator answer** — seed the standard roster
       (``required_bots: cuioss-review-bot,coderabbit``,
       ``optional_bots: sourcery``), remove ``enabled_bots``, and record
       provenance ``migrated``. Seeding the standard roster (not the legacy
       value verbatim) is what leaves a legacy-only config valid without hand
       repair: the discarded bots are named individually in ``discarded_legacy``
       so no name disappears silently, and any unknown name is reported by
       ``validate_bot_lists`` rather than copied.
    2. **legacy present, operator answered** — the operator has already
       answered, so THEIR ANSWER WINS: the new keys are left untouched and
       only the stale legacy key is removed. Both values are reported so the
       operator can see what was discarded. Provenance is NOT downgraded to
       ``migrated`` — an answered value stays ``answered``.
    3. **legacy absent, no operator answer** — nothing to migrate; a no-op
       success that leaves the never-asked posture intact.
    4. **already migrated** — indistinguishable from (3) once the legacy key is
       gone. This is what makes the migration self-disarming and re-runnable.

    Only a non-empty value, or ``bot_lists_provenance: answered``, counts as
    an operator answer — mere key presence does not, because ``sync-defaults``
    back-fills empty strings for absent keys.

    Args:
        params: The ``plan-marshall:automatic-review`` step's param object.

    Returns:
        A report dict: ``state`` (one of ``migrated`` / ``operator_answer_kept`` /
        ``noop``), plus ``required_bots`` / ``optional_bots`` (the resulting
        values) and, when a legacy value was discarded, ``discarded_legacy``
        (the list of dropped bot names — never the raw ``enabled_bots`` string).
    """
    legacy = params.get(_LEGACY_BOT_LIST_KEY)
    has_legacy = legacy is not None
    has_new = _has_operator_answer(params)

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
            'discarded_legacy': _named_discarded_bots(legacy),
        }

    # State (1) — seed the standard roster; name each dropped bot explicitly.
    params[_REQUIRED_BOTS_KEY] = _STANDARD_REQUIRED_BOTS
    params[_OPTIONAL_BOTS_KEY] = _STANDARD_OPTIONAL_BOTS
    params[_PROVENANCE_KEY] = 'migrated'
    del params[_LEGACY_BOT_LIST_KEY]
    return {
        'state': 'migrated',
        'required_bots': _STANDARD_REQUIRED_BOTS,
        'optional_bots': _STANDARD_OPTIONAL_BOTS,
        'discarded_legacy': _named_discarded_bots(legacy),
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
# executor bootstrap — validate against the newest cache before the stage plan
# ---------------------------------------------------------------------------
#
# ``upgrade.py plan`` is requested by the router BEFORE any stage runs, while
# the executor serving the request may itself be stale: a stale executor
# resolves every downstream stage to stale scripts. The bootstrap validates the
# serving executor's embedded ``MARSHALL_VERSION`` against the newest
# plugin-cache version and regenerates the executor from that cache when stale,
# so the plan and every downstream stage resolve current-version scripts. The
# newest-version scan and the version readers are reused from the
# cache-freshness / registry helpers — the comparison and the version-dir
# ordering are never re-implemented here.
#
# When the skill surface and the planner disagree on the version (the executor
# is AHEAD of the newest cache, or regeneration failed and the executor is
# still behind), the bootstrap reports a ``warning`` naming the split and its
# remedy instead of letting the router run a silently stale plan: re-sync the
# plugin cache, reload the plugin set, and re-request the stage plan.
#
# Regeneration runs the generator DIRECTLY, by its resolved script path — the
# same sanctioned direct-path surface Stage 1's ``regenerate-executor``
# sub-step uses (see ``references/upgrade-flow.md``), so a recovery run works
# even when the serving executor is broken. The generator path is resolved per
# kind exactly as that sub-step resolves it: meta uses the marketplace-source
# generator under the clone; consumer uses the newest cache-version generator.
# Discovery is anchored via the ``PM_MARKETPLACE_ROOT`` env var (never a bare
# flag alone): ``discover_scripts`` propagates the marketplace root to its scan
# subprocess only through that anchor, and an unanchored run silently degrades
# to the version-unaware glob fallback.

_BOOTSTRAP_BUNDLE = 'plan-marshall'

_BOOTSTRAP_REGENERATE_TIMEOUT_SECONDS = 120

#: Remedy surfaced with every version-split warning: re-sync the installed
#: plugin in place, reload the session plugin set so the refreshed cache is
#: visible, then re-request the stage plan so the skill docs and the planner
#: resolve one version.
_VERSION_SPLIT_REMEDY = (
    "Run '/plugin update plan-marshall' to update the installed plugin in place, "
    'reload the session plugin set so the refreshed cache is visible to the running '
    'session, then re-request the stage plan so the skill docs and the planner '
    'resolve one version.'
)


def _default_bootstrap_executor_path() -> Path:
    """The serving executor: ``.plan/execute-script.py`` under the cwd."""
    return Path.cwd() / '.plan' / 'execute-script.py'


def _default_bootstrap_cache_root() -> Path | None:
    """The deployed plugin-cache root, or ``None`` when unresolvable."""
    from marketplace_paths import get_plugin_cache_path

    try:
        return get_plugin_cache_path()
    except Exception:
        return None


def _resolve_bootstrap_generator(project_kind: str, cache_root: Path | None, newest: str) -> tuple[Path | None, Path]:
    """Resolve ``(generator_path, anchor)`` for the regeneration run.

    The generator path follows the Stage 1 ``regenerate-executor`` resolution:
    meta uses the marketplace-source generator under the clone; consumer uses
    the newest cache-version generator. The anchor pins discovery via
    ``PM_MARKETPLACE_ROOT``: the clone root on meta (it contains
    ``marketplace/bundles``), the newest versioned bundle tree on consumer (no
    ``marketplace/`` level there — the anchor still pins discovery to the
    newest versioned tree instead of degrading to the glob fallback).
    ``generator_path`` is ``None`` when the resolved generator file is absent.
    """
    clone_root = Path.cwd()
    if project_kind == 'meta':
        generator = (
            clone_root
            / 'marketplace'
            / 'bundles'
            / _BOOTSTRAP_BUNDLE
            / 'skills'
            / 'tools-script-executor'
            / 'scripts'
            / 'generate_executor.py'
        )
        return (generator if generator.is_file() else None, clone_root)
    anchor = cache_root / _BOOTSTRAP_BUNDLE / newest if cache_root is not None else clone_root
    generator = anchor / 'skills' / 'tools-script-executor' / 'scripts' / 'generate_executor.py'
    return (generator if generator.is_file() else None, anchor)


def _run_bootstrap_generate(generator: Path, anchor: Path, project_dir: Path) -> tuple[int, str, str]:
    """Regenerate the executor via the resolved generator. Never raises.

    ``cwd`` is pinned to the project dir because the generator resolves its
    OUTPUT location by walking up from cwd; ``PM_MARKETPLACE_ROOT`` pins bundle
    DISCOVERY (see the section header). Returns
    ``(returncode, stdout, stderr)``.
    """
    import os
    import subprocess

    env = dict(os.environ)
    env['PM_MARKETPLACE_ROOT'] = str(anchor)
    try:
        result = subprocess.run(
            ['python3', str(generator), 'generate'],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=_BOOTSTRAP_REGENERATE_TIMEOUT_SECONDS,
            env=env,
        )
    except FileNotFoundError:
        return 127, '', 'python3 executable not found on PATH'
    except subprocess.TimeoutExpired:
        return 124, '', f'generate_executor generate timed out after {_BOOTSTRAP_REGENERATE_TIMEOUT_SECONDS}s'
    return result.returncode, result.stdout, result.stderr


#: Import-failure markers in a probe's stderr: the Python import-error phrases
#: and the executor's own bootstrap-guard message (``cannot start:``), which
#: prints instead of a traceback when the failed import coincides with an
#: unresolved bootstrap directory.
_IMPORT_FAILURE_MARKERS = ('ModuleNotFoundError', 'ImportError', 'No module named', 'cannot start:')

#: Timeout for the read-only executor import probe.
_BOOTSTRAP_PROBE_TIMEOUT_SECONDS = 30


def _probe_executor_import(executor_path: Path) -> str:
    """Probe the serving executor's module-level imports. Never raises.

    Runs ``python3 <executor> --list`` — the executor's cheapest read-only entry
    point: it exercises the module-level bootstrap import block (every import
    the executor needs to start) and exits before any notation resolution or
    dispatch, so a broken import is observed without running any verb. Returns a
    short reason when the probe observed an IMPORT failure, and ``''`` for a
    healthy executor, a missing file, or any other failure — a non-import
    nonzero exit is NOT an import failure, and an inconclusive probe never
    triggers a recovery.
    """
    import subprocess

    if not executor_path.is_file():
        return ''
    try:
        result = subprocess.run(
            ['python3', str(executor_path), '--list'],
            cwd=str(executor_path.parent.parent),
            capture_output=True,
            text=True,
            timeout=_BOOTSTRAP_PROBE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ''
    if result.returncode == 0:
        return ''
    stderr = result.stderr or ''
    if not any(marker in stderr for marker in _IMPORT_FAILURE_MARKERS):
        return ''
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    return (lines[-1] if lines else 'import failure')[:200]


# A plugin-cache version directory name (``.../plan-marshall/0.1.1916/…``).
_VERSION_DIR_RE = re.compile(r'^\d+\.\d+')


def _version_dir_version(path: Path) -> str:
    """The version-dir segment of ``path``'s ancestry, or ``''`` when it has none.

    A script executed from a deployed plugin-cache version directory
    (``.../plan-marshall/<version>/skills/…``) carries its skill-tree version in
    the path; one executed from the marketplace source tree (a meta clone)
    carries none, and ``''`` says so rather than guessing.
    """
    for ancestor in path.resolve().parents:
        if _VERSION_DIR_RE.match(ancestor.name):
            return ancestor.name
    return ''


def _planner_version() -> str:
    """The version of the skill tree the running planner (this script) belongs to.

    ``''`` when the planner runs from the marketplace source tree rather than a
    deployed version directory — the meta-clone case, where there is no
    skill/planner version pair to compare and the split is therefore not
    asserted.
    """
    return _version_dir_version(Path(__file__))


def _loaded_skill_version(registry_path: Path | None = None) -> str:
    """The plan-marshall version the plugin manager has loaded, or ``''``.

    The plugin registry (``installed_plugins.json``) is the plugin manager's
    record of what it installed and loaded, so it is the one store that can name
    a version the newest cache has already moved past. That is exactly the
    condition the executor-stamp-vs-cache comparison cannot see: the executor
    stamp and the cache agree (both regenerated) while the skill surface the
    session loaded still lags the planner, so the router docs describe stages the
    running planner no longer emits. Every skill of a bundle ships in lock-step,
    so the plan-marshall bundle version IS the marshall-steward skill version.

    Returns ``''`` when the registry is absent, unreadable, carries no
    plan-marshall entry, or its rows disagree on the version: an unknown loaded
    version is never compared, and never guessed.
    """
    from plugin_registry import REGISTRY_OK, default_registry_path, read_registry

    path = registry_path if registry_path is not None else default_registry_path()
    state, rows = read_registry(path)
    if state != REGISTRY_OK:
        return ''
    versions = {
        value
        for row in rows
        for value in (row.get('install_path_version'), row.get('version'))
        if isinstance(value, str) and value
    }
    if len(versions) != 1:
        return ''
    return next(iter(versions))


def _skill_planner_split_warning(loaded_skill_version: str | None, planner_version: str | None) -> str:
    """Warn when the loaded skill surface and the planner disagree on the version.

    Independent of the executor-stamp-vs-cache comparison: the two answer
    different questions, and a split here is reported whether or not the executor
    stamp and the newest cache agree. Empty exactly when either version is
    unknown/unorderable or the two agree, so an unreadable store never fabricates
    a split.
    """
    from generate_executor import _version_tuple

    if not loaded_skill_version or not planner_version:
        return ''
    loaded = _version_tuple(loaded_skill_version)
    planner = _version_tuple(planner_version)
    if not loaded or not planner or loaded == planner:
        return ''
    if planner > loaded:
        return (
            f'skill/planner version split: the planner at {planner_version} is ahead of the loaded '
            f'marshall-steward skill at {loaded_skill_version} — the router docs lag the planner. '
            f'{_VERSION_SPLIT_REMEDY}'
        )
    return (
        f'skill/planner version split: the loaded marshall-steward skill at {loaded_skill_version} is '
        f'ahead of the planner at {planner_version} — the planner lags the installed skill surface. '
        f'{_VERSION_SPLIT_REMEDY}'
    )


def _join_warnings(*warnings: str) -> str:
    """Join the non-empty warnings with a single space, preserving order."""
    return ' '.join(warning for warning in warnings if warning)


def resolve_bootstrap_action(
    executor_version: str | None,
    newest_cache_version: str | None,
    loaded_skill_version: str | None = None,
    planner_version: str | None = None,
) -> tuple[str, str]:
    """Pure decision: ``(action, warning)`` from the versions.

    Actions: ``fresh`` (executor at or ahead of the cache — an AHEAD executor
    still carries a split warning, since the installed skill surface lags the
    planner), ``regenerate_required`` (executor behind, unreadable, or
    unorderable — the generator's ordering maps an empty or non-numeric stamp
    to the lowest version, so an unproven executor regenerates rather than
    reading ``fresh``), ``no_cache`` (no newest cache version to compare
    against — the fresh-install boundary, never a failure).

    Two independent comparisons feed the warning, and neither replaces the
    other. The executor-stamp-vs-cache comparison catches an executor ahead of
    the cache; the loaded-skill-vs-planner comparison
    (:func:`_skill_planner_split_warning`) catches a skill/planner split the
    executor stamp cannot see, because the stamp and the cache can agree while
    the loaded skill surface still lags the planner. The warning names the
    remedy; it is empty exactly when no warning is owed. Comparing uses the
    generator's own version ordering, never a local re-implementation.
    """
    from generate_executor import _version_tuple

    split = _skill_planner_split_warning(loaded_skill_version, planner_version)
    if not newest_cache_version:
        return 'no_cache', split
    if not executor_version:
        return 'regenerate_required', split
    current = _version_tuple(executor_version)
    newest = _version_tuple(newest_cache_version)
    if current >= newest:
        if current == newest:
            return 'fresh', split
        return (
            'fresh',
            _join_warnings(
                f'skill/planner version split: planner at {executor_version} is ahead of the newest '
                f'installed skill surface at {newest_cache_version} — the router docs lag the '
                f'planner. {_VERSION_SPLIT_REMEDY}',
                split,
            ),
        )
    return 'regenerate_required', split


def bootstrap_executor(
    project_kind: str = 'consumer',
    cache_root: Path | None = None,
    executor_path: Path | None = None,
    _run_generate=None,
    allow_regenerate: bool = True,
    registry_path: Path | None = None,
) -> dict:
    """Validate the serving executor against the newest cache; regenerate when stale or broken.

    Resolves the newest plugin-cache version for the plan-marshall bundle and
    the serving executor's embedded ``MARSHALL_VERSION``, decides via
    :func:`resolve_bootstrap_action`, and regenerates the executor from the
    newest cache (per-kind generator resolution, ``PM_MARKETPLACE_ROOT``
    anchored) when the decision requires it. Read-only except for the stale
    regeneration itself; a failed regeneration is REPORTED (``action:
    regenerate_failed`` with a split warning), never fatal — the stage plan is
    still emitted and Stage 1's ``regenerate-executor`` sub-step remains the
    repair.

    Args:
        project_kind: ``'meta'`` or ``'consumer'`` — selects the generator
            resolution (marketplace-source vs newest cache-version generator).
        cache_root: Explicit plugin-cache root, or ``None`` to resolve the
            deployed root (tests / alternate installs pass a fixture root).
        executor_path: Explicit serving-executor path, or ``None`` for
            ``.plan/execute-script.py`` under the cwd.
        _run_generate: Injectable regeneration seam
            ``(generator, anchor, project_dir) -> (rc, stdout, stderr)``.
            Tests pass a fake; production uses :func:`_run_bootstrap_generate`.
        allow_regenerate: Consent gate for REWRITING a merely-stale executor.
            When ``False``, a stale-but-readable executor is validated and the
            ``regenerate_required`` decision is REPORTED in the returned block —
            never rewritten unasked. When ``True`` (the default for a direct
            caller) the decision is acted on; ``cmd_plan`` threads the
            ``--bootstrap`` flag here, whose default is ``false``, so the
            ``plan`` verb reports a stale executor rather than rewriting it
            unasked. The missing-or-broken executor RECOVERY is not gated: an
            absent, unreadable or version-less executor — or one whose import
            probe fails — is always restored from the newest cache regardless
            of this flag, because no plan can run against a broken tool and
            consent to restore one is meaningless.
        registry_path: Explicit plugin-registry path, or ``None`` to resolve the
            plugin manager's registry (tests pass a fixture registry). It is
            read for the loaded marshall-steward skill version the skill/planner
            split comparison consumes.

    Returns:
        A report dict: ``status`` (``success``, or ``error`` only when the
        report itself could not be produced), ``action`` (``fresh`` |
        ``regenerated`` | ``regenerate_required`` | ``no_cache`` |
        ``regenerate_failed`` | ``unknown``),
        ``executor_version`` / ``newest_cache_version`` (``''`` when
        unresolved), ``executor_path`` / ``cache_root`` / ``generator`` (the
        resolved inputs), and ``warning`` (the split/remedy message, or ``''``).
    """
    from cache_freshness import newest_cache_version
    from plugin_registry import EXECUTOR_VERSION_FOUND, read_executor_version

    if cache_root is None:
        cache_root = _default_bootstrap_cache_root()
    if executor_path is None:
        executor_path = _default_bootstrap_executor_path()

    # Read the loaded-skill and planner versions BEFORE the cache check: the
    # loaded-skill-vs-planner comparison is independent of the executor-stamp-vs-
    # cache one, so it is surfaced on every branch, the fresh-install one
    # included.
    loaded_skill_version = _loaded_skill_version(registry_path)
    planner_version = _planner_version()

    newest = newest_cache_version(cache_root) if cache_root is not None and cache_root.is_dir() else ''
    if not newest:
        return {
            'status': 'success',
            'action': 'no_cache',
            'executor_version': '',
            'newest_cache_version': '',
            'executor_path': str(executor_path),
            'cache_root': str(cache_root) if cache_root is not None else '',
            'generator': '',
            'warning': _skill_planner_split_warning(loaded_skill_version, planner_version),
            'detail': 'no plugin cache resolvable — nothing to regenerate from (fresh-install boundary)',
        }

    state, current = read_executor_version(executor_path)
    executor_version = current if state == EXECUTOR_VERSION_FOUND else None

    # An executor can exist and carry the newest stamp and still fail to IMPORT:
    # the stamp is read as text, so the version comparison alone cannot see a
    # broken import (the original PLAN-LB-40 failure). The probe observes it,
    # and an observed import failure forces the ungated recovery below.
    import_failure = _probe_executor_import(executor_path)

    action, warning = resolve_bootstrap_action(executor_version, newest, loaded_skill_version, planner_version)
    if import_failure:
        action = 'regenerate_required'
        warning = _join_warnings(
            f'executor at {executor_path} fails to import ({import_failure}); restoring it from '
            f'the newest cache at {newest} like a missing executor.',
            warning,
        )
    generator: Path | None = None
    anchor = executor_path.parent.parent

    # A merely-stale executor is rewritten ONLY with consent (allow_regenerate).
    # Without it the decision is reported and the executor is left untouched, so
    # an unconsented reconcile never rewrites the executor out from under the
    # running session. The missing-or-broken RECOVERY is not gated: it covers an
    # absent, unreadable or version-less executor (executor_version is None) and
    # one whose probe observed an import failure (import_failure) — no plan can
    # run against a tool that cannot start.
    needs_recovery = executor_version is None or bool(import_failure)
    if action == 'regenerate_required' and not needs_recovery and not allow_regenerate:
        return {
            'status': 'success',
            'action': 'regenerate_required',
            'executor_version': executor_version or '',
            'newest_cache_version': newest,
            'executor_path': str(executor_path),
            'cache_root': str(cache_root),
            'generator': '',
            'warning': (
                f'executor at {executor_version or "unknown"} is behind the newest cache at '
                f'{newest}; regeneration was not authorised (--bootstrap true is the consent '
                f'gate), so the executor is reported and left untouched. Re-run with '
                f'--bootstrap true to rewrite it. {_VERSION_SPLIT_REMEDY}'
            ),
            'detail': 'stale executor reported; regeneration gated on --bootstrap true',
        }

    if action == 'regenerate_required':
        generator, anchor = _resolve_bootstrap_generator(project_kind, cache_root, newest)
        # The phrase naming WHY the executor cannot serve: an observed import
        # failure is not a version gap, and the stale phrasing would read false
        # against an executor whose stamp matches the newest cache.
        gap = (
            f'executor at {executor_path} fails to import ({import_failure})'
            if import_failure
            else (
                f'skill/planner version split: executor at {executor_version or "unknown"} is behind '
                f'the newest cache at {newest}'
            )
        )
        if generator is None:
            return {
                'status': 'success',
                'action': 'unknown',
                'executor_version': executor_version or '',
                'newest_cache_version': newest,
                'executor_path': str(executor_path),
                'cache_root': str(cache_root),
                'generator': '',
                'warning': (
                    f'{gap}, but no generator resolves for {project_kind!r} — currency cannot be '
                    f'restored here. {_VERSION_SPLIT_REMEDY}'
                ),
                'detail': 'executor cannot be brought current: no generator resolves',
            }
        run_generate = _run_generate or _run_bootstrap_generate
        project_dir = executor_path.parent.parent
        rc, stdout, _stderr = run_generate(generator, anchor, project_dir)
        if rc != 0:
            return {
                'status': 'success',
                'action': 'regenerate_failed',
                'executor_version': executor_version or '',
                'newest_cache_version': newest,
                'executor_path': str(executor_path),
                'cache_root': str(cache_root),
                'generator': str(generator),
                'warning': (
                    f'{gap} and regeneration failed (rc={rc}): '
                    f'{(stdout or "").strip()[:200] or "no output"} — {_VERSION_SPLIT_REMEDY}'
                ),
                'detail': 'regeneration attempted and failed; Stage 1 regenerate-executor remains the repair',
            }
        reread_state, reread = read_executor_version(executor_path)
        if reread_state == EXECUTOR_VERSION_FOUND:
            executor_version = reread
        else:
            # The regeneration succeeded but the stamp cannot confirm it: the
            # reread state (unreadable / not_found / empty) is the fact, and
            # the stale pre-regeneration version must not survive as if it
            # were re-observed. Report unknown with a warning instead of a
            # silent regenerated-with-empty-version.
            executor_version = ''
            warning = (
                f'executor regenerated from the newest cache at {newest} but its version '
                f'stamp is {reread_state} — the regenerated version could not be confirmed. '
                f'{_VERSION_SPLIT_REMEDY}'
            )
        action = 'regenerated'

    if action == 'regenerated' and executor_version and executor_version != newest:
        warning = (
            f'skill/planner version split: planner at {executor_version} does not match the '
            f'newest cache at {newest} after regeneration. {_VERSION_SPLIT_REMEDY}'
        )
    return {
        'status': 'success',
        'action': action,
        'executor_version': executor_version or '',
        'newest_cache_version': newest,
        'executor_path': str(executor_path),
        'cache_root': str(cache_root),
        'generator': str(generator) if generator is not None else '',
        'warning': warning,
        'detail': f'executor bootstrap {action}: planner at {executor_version or "unknown"}, newest cache at {newest}',
    }


def cmd_plan(args: argparse.Namespace) -> dict:
    """Handle the ``plan`` subcommand.

    Resolves ``--project-kind auto`` via :func:`detect_project_kind` against the
    current working directory (keeping :func:`build_plan` pure and directly
    testable), runs the executor bootstrap (:func:`bootstrap_executor`) BEFORE
    the stage plan is emitted, then delegates to the pure builder and merges the
    bootstrap report.

    The bootstrap ALWAYS validates the serving executor against the newest cache
    and reports the outcome; only whether it may REWRITE a merely-stale executor
    is gated by ``--bootstrap`` (default false — a stale executor is reported,
    never rewritten unasked). The missing-or-broken executor recovery is not
    gated, because a plan cannot run against a broken tool. A bootstrap
    ``status: error`` fails closed with no plan emitted.
    """
    integrate = args.integrate == 'true'
    project_kind = args.project_kind
    if project_kind == 'auto':
        project_kind = detect_project_kind(Path.cwd())
    bootstrap = bootstrap_executor(
        project_kind=project_kind,
        allow_regenerate=getattr(args, 'bootstrap', 'false') == 'true',
    )
    if bootstrap.get('status') != 'success':
        return bootstrap
    plan = build_plan(integrate, project_kind)
    plan['bootstrap'] = bootstrap
    return plan


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
    plan_parser.add_argument(
        '--bootstrap',
        choices=['true', 'false'],
        default='false',
        help=(
            'Consent gate for REGENERATING the serving executor from the newest plugin-cache '
            'version when it is merely stale. Default false: the bootstrap still VALIDATES and '
            'REPORTS a stale executor in the ``bootstrap`` block, but does not rewrite it '
            'unasked. Pass true to authorise the in-place regeneration. The missing-or-broken '
            'executor recovery is not gated by this flag — a recovery run always restores the '
            'executor from the newest cache (see references/upgrade-flow.md Step 0).'
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
