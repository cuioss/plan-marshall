#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``validate`` subcommand of manage-execution-manifest.py.

Split from test_manage_execution_manifest.py — tier 2 direct-import tests for
the validate path plus the CLI happy-path roundtrip.
"""

import json
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

# Script path for subprocess (CLI plumbing) tests.
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py')

# Tier 2 direct imports, resolved by (bundle, skill, script).


_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_mem_script'
)
cmd_compose = _mem.cmd_compose
cmd_validate = _mem.cmd_validate
cmd_step_params_get = _mem.cmd_step_params_get
get_manifest_path = _mem.get_manifest_path
read_manifest = _mem.read_manifest
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Step-owner schema primitives live in _manifest_core (loaded directly; the
# hyphenated entry does not re-export them). See _manifest_core.py § "Step
# ownership".
_core = load_script_module('plan-marshall', 'manage-execution-manifest', '_manifest_core.py', module_name='_mem_core')
VALID_STEP_OWNERS = _core.VALID_STEP_OWNERS
validate_step_owner = _core.validate_step_owner
owner_of = _core.owner_of
ORCHESTRATOR_OWNED_STEPS = _core.ORCHESTRATOR_OWNED_STEPS

# Ascending-order barrier primitives live in _manifest_validation (loaded
# directly following the _manifest_core convention above). _check_ascending_order
# asserts the composed phase_6.steps hold non-decreasing frontmatter order;
# _resolve_step_order yields a step's frontmatter order (or None when unresolvable).
_validation = load_script_module(
    'plan-marshall', 'manage-execution-manifest', '_manifest_validation.py', module_name='_mem_validation'
)
_check_ascending_order = _validation._check_ascending_order
_resolve_step_order = _validation._resolve_step_order

# Quiet down the best-effort decision-log subprocess.
_mem._log_decision = lambda *a, **kw: None

# =============================================================================
# Namespace Helpers
# =============================================================================


def _compose_ns(
    plan_id: str = 'test-plan',
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'quality-gate,module-tests',
    phase_6_steps: str | None = ','.join(DEFAULT_PHASE_6_STEPS),
    commit_and_push: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps,
        phase_6_steps=phase_6_steps,
        commit_and_push=commit_and_push,
    )


def _validate_ns(
    plan_id: str = 'test-plan',
    phase_5_steps: str | None = 'quality-gate,module-tests,coverage',
    phase_6_steps: str | None = ','.join(DEFAULT_PHASE_6_STEPS),
) -> Namespace:
    return Namespace(plan_id=plan_id, phase_5_steps=phase_5_steps, phase_6_steps=phase_6_steps)


# =============================================================================
# Keyed-map marshal.json -> DICT manifest step_params snapshot bridge
# =============================================================================
#
# marshal.json persists `verification_steps` / `steps` in the canonical keyed-map
# form (`{}` for config-less steps). The composer reads that keyed map through
# `_read_marshal_phase_step_map` and snapshots the per-step params into the
# manifest as an id-keyed DICT (`body[phase].step_params`) — the plan-local
# override surface that `step-params get/set` resolve against. These tests lock
# that bridge: a keyed-map marshal.json composes to a DICT manifest snapshot, the
# params survive, validate succeeds against it, and `step-params get` resolves the
# DICT snapshot.


def _seed_keyed_map_marshal(fixture_dir: Path) -> None:
    """Write a marshal.json whose phase-6-finalize steps are the canonical keyed map.

    Config-less steps map to {}; param-bearing steps carry their nested param
    object — the on-disk serial form every config write verb persists.
    """
    marshal_path = fixture_dir / 'marshal.json'
    data = {
        'plan': {
            'phase-6-finalize': {
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'plan-marshall:automatic-review': {'review_bot_buffer_seconds': 240},
                    'default:sonar-roundtrip': {},
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {
                        'pr_merge_strategy': 'squash',
                        'final_merge_without_asking': False,
                    },
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                }
            }
        }
    }
    marshal_path.write_text(json.dumps(data), encoding='utf-8')


# =============================================================================
# Ascending-order barrier invariant (general regression, order-independent)
#
# Distinct verification scope from the single-case reproduction
# (test_manage_execution_manifest_compose.py :: test_compose_sorts_phase_6_steps
# _by_frontmatter_order, which pins one archive-plan/preference-emitter pair):
# this drives cmd_compose across SEVERAL shuffled seed orderings of the SAME
# order-resolvable candidate set and asserts the barrier invariant holds for
# EVERY seed regardless of input order. The invariant is checked structurally via
# _check_ascending_order + _resolve_step_order — no order magnitudes are hardcoded
# beyond archive-plan being the highest-order finalize step.
# =============================================================================

# Order-resolvable phase-6 steps spanning the full frontmatter-order range, from
# the earliest finalize step to the archive-plan barrier. Every entry resolves to
# a non-None frontmatter order, so all participate in the ascending assertion.
_ORDER_RESOLVABLE_CANDIDATES = [
    'finalize-step-sync-baseline',  # order 3
    'architecture-refresh',  # order 10
    'push',  # order 11
    'ci-verify',  # order 22
    'branch-cleanup',  # order 70
    'finalize-step-preference-emitter',  # order 992
    'record-metrics',  # order 998
    'finalize-step-print-phase-breakdown',  # order 999
    'archive-plan',  # order 1100 — the plan-mutating barrier, highest order (terminus)
]

# Several arbitrary/shuffled seed orderings of the SAME candidate set. Each is a
# permutation of _ORDER_RESOLVABLE_CANDIDATES (self-checked in the test body).
# Includes orders that place archive-plan early and orders that interleave
# multiple order-resolvable steps around it.
_SHUFFLED_SEED_ORDERINGS = [
    # archive-plan placed FIRST (the extreme early-placement case).
    [
        'archive-plan',
        'finalize-step-preference-emitter',
        'push',
        'record-metrics',
        'ci-verify',
        'finalize-step-print-phase-breakdown',
        'architecture-refresh',
        'finalize-step-sync-baseline',
        'branch-cleanup',
    ],
    # Fully reverse-sorted: archive-plan first, every step in descending order.
    [
        'archive-plan',  # 1100
        'finalize-step-print-phase-breakdown',  # 999
        'record-metrics',  # 998
        'finalize-step-preference-emitter',  # 992
        'branch-cleanup',  # 70
        'ci-verify',  # 22
        'push',  # 11
        'architecture-refresh',  # 10
        'finalize-step-sync-baseline',  # 3
    ],
    # High/low interleave: archive-plan mid-list, high-order steps scattered
    # among low-order ones.
    [
        'record-metrics',
        'push',
        'archive-plan',
        'ci-verify',
        'finalize-step-print-phase-breakdown',
        'architecture-refresh',
        'finalize-step-preference-emitter',
        'finalize-step-sync-baseline',
        'branch-cleanup',
    ],
    # Another arbitrary shuffle with archive-plan near the front.
    [
        'branch-cleanup',
        'archive-plan',
        'finalize-step-sync-baseline',
        'finalize-step-print-phase-breakdown',
        'push',
        'finalize-step-preference-emitter',
        'record-metrics',
        'ci-verify',
        'architecture-refresh',
    ],
]
