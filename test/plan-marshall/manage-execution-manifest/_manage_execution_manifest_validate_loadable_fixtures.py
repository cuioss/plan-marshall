#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the manage-execution-manifest ``validate-loadable`` subcommand.

Covers the loadability fail-fast guard consumed by phase-6-finalize Step 1.5:

- Single-step happy path (built-in step with present standards file)
- Single-step missing-file path (canonical actionable message)
- External step short-circuit (project: / bundle:skill → loadable=true, no check)
- ``default:`` prefix is accepted and stripped
- ``--all`` happy path against a real manifest
- ``--all`` reports per-step results and unloadable_count when one entry is missing
- Mutual-exclusivity + missing-mode validation errors
- Manifest-missing yields ``file_not_found`` for ``--all``
"""

# ruff: noqa: I001

from argparse import Namespace
# Tier 2 direct import — match the test layout used by sibling tests.


from conftest import load_script_module

_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_mem_validate_loadable'
)
cmd_compose = _mem.cmd_compose
cmd_validate_loadable = _mem.cmd_validate_loadable
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Silence the best-effort decision-log subprocess so tests do not depend on a
# running executor.
_mem._log_decision = lambda *a, **kw: None

# =============================================================================
# Namespace helpers
# =============================================================================


def _validate_loadable_ns(
    plan_id: str = 'vl-test',
    step_id: str | None = None,
    use_all: bool = False,
    check_seed: bool = False,
) -> Namespace:
    return Namespace(plan_id=plan_id, step_id=step_id, all=use_all, check_seed=check_seed)


# =============================================================================
# record-metrics order regression — must trail every token-consuming step
# =============================================================================
#
# `default:record-metrics` is the LAST token-accounting finalize step: its
# `end-phase` call folds the `<usage>` spend of every dispatched finalize step
# into the closed `6-finalize` phase row, so it MUST resolve to a frontmatter
# `order` strictly greater than every token-consuming step's order. The
# token-consuming finalize steps are the ones whose bodies dispatch a subagent
# or run a token-spending sweep before record-metrics closes the ledger:
# finalize-step-deploy-target, finalize-step-sync-plugin-cache,
# finalize-step-lessons-housekeeping, finalize-step-plugin-doctor, and
# pre-submission-self-review. This regression would fail if record-metrics'
# order were reverted below any of them (the defect this plan corrected).


# The token-consuming finalize steps that MUST precede record-metrics, in the
# step-id form `_resolve_step_order` consumes (project: steps resolve from
# `.claude/skills/{bare-name}/SKILL.md`).
_TOKEN_CONSUMING_FINALIZE_STEPS: list[str] = [
    'project:finalize-step-deploy-target',
    'project:finalize-step-sync-plugin-cache',
    'project:finalize-step-lessons-housekeeping',
    'project:finalize-step-plugin-doctor',
    'default:pre-submission-self-review',
]


# =============================================================================
# Order-resolution verdicts + the post-compose ascending-order gate
#
# ``_sort_steps_by_frontmatter_order`` PINS every entry whose order resolves to
# ``None`` at its original index, and ``_check_ascending_order`` SKIPS exactly
# those entries. Composed, the two behaviours let a step that SHOULD carry an
# order but whose source cannot be read sit wherever the seed put it while the
# ascending walk declines to check that position — a green compose over a broken
# barrier. ``check_emitted_steps_ascending_order`` closes it by treating an entry
# it cannot verify as an offence. The empirical reproduction that established
# this is recorded in the plan artifact ``work/defect-b-gate-reproduction.md``.
# =============================================================================
def _compose_ns(
    plan_id: str,
    phase_6_steps: str | None = None,
    change_type: str = 'feature',
    scope_estimate: str = 'multi_module',
    affected_files_count: int = 5,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track='complex',
        scope_estimate=scope_estimate,
        recipe_key=None,
        affected_files_count=affected_files_count,
        phase_5_steps=','.join(DEFAULT_PHASE_5_STEPS),
        phase_6_steps=phase_6_steps if phase_6_steps is not None else ','.join(DEFAULT_PHASE_6_STEPS),
        commit_and_push=None,
    )


_EMITTER = 'finalize-step-preference-emitter'
