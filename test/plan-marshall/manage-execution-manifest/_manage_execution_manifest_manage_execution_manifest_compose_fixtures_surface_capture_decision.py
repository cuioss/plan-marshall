#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from argparse import Namespace

from conftest import load_script_module

_surface_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_surface_mem_capture_decision'
)
DEFAULT_PHASE_6_STEPS = _surface_mem.DEFAULT_PHASE_6_STEPS


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


# =============================================================================
# envelope_count tests (TASK-16 wiring-gap fix)
#
# compose accepts an optional ``--envelope-count`` input and persists it into
# the composed manifest's ``phase_5`` block as ``envelope_count`` — the
# orchestrator's read-side signal for how many phase-5 execution-context
# envelopes to plan for. When the flag is absent the value defaults to
# ``DEFAULT_ENVELOPE_COUNT`` (1), reproducing the single-envelope behaviour, so
# existing callers that omit the flag are unaffected and a manifest read back
# without the key is interpreted by every reader as this same default. A
# non-positive value is clamped to the default. The field is written across
# every decision-matrix rule (including ``early_terminate``) so the phase_5
# block always carries it.
#
# ``_compose_ns`` deliberately omits ``envelope_count`` from its Namespace —
# the composer reads it via ``getattr(args, 'envelope_count', None)`` — so the
# bare helper exercises the absent-flag (backward-compatibility) path directly.
# The supplied-value path builds a Namespace with the attribute set.
# =============================================================================


def _compose_ns_with_envelope_count(envelope_count, **kwargs) -> Namespace:
    """``_compose_ns`` plus an explicit ``envelope_count`` attribute.

    Used by the supplied-value tests; the bare ``_compose_ns`` is reused for
    the absent-flag (backward-compatibility) path so both code paths in the
    composer's ``getattr(args, 'envelope_count', None)`` branch are covered.
    """
    ns = _compose_ns(**kwargs)
    ns.envelope_count = envelope_count
    return ns
