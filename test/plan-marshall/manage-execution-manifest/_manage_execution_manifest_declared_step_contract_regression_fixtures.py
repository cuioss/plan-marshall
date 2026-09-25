#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end regression coverage for the composer's declared-step contracts.

Sibling unit tests pin the composer's helpers at the unit boundary. This
module exercises the same two defects from the USER-VISIBLE angle: it drives the
real ``cmd_compose`` / ``cmd_lanes_preview`` entry points over seeded marshal
fixtures and reads the result back from the PERSISTED ``execution.toon``, never
from in-memory composer internals. Three regression families:

(a) an operator-declared ``lane: minimal`` on ``plan-marshall:plan-retrospective``
    survives a ``single_module`` compose (declared-lane immunity) — asserted for
    BOTH declaration channels, project-wide marshal.json and plan-local
    ``status.metadata.finalize_step_overrides``;
(b) the composed ``phase_6.steps`` is in ascending frontmatter ``order``, asserted
    specifically for the BARE ``finalize-step-preference-emitter`` id placed
    after the merge gate ``branch-cleanup`` (the emitter declares
    ``post_run_review: true``, so its evidence is only complete once the gate has
    run);
(c) ``cmd_lanes_preview`` membership equals ``cmd_compose`` membership for the
    same posture and marshal seed.

**Non-vacuity evidence.** Each family carries its discriminator IN-TEST rather
than relying on an out-of-band "ran it against the old code" claim: every test
that asserts the fixed behaviour is paired with an assertion that pins the
pre-fix behaviour on the same inputs — the undeclared-lane compose still drops
the step (a), the legacy ``_check_ascending_order`` still reports nothing on the
pinned list while the new gate rejects it (b), and the raw lane projection still
differs in sequence from the preview (c). A test whose discriminator also passed
before the fix would be vacuous; these cannot, because the paired assertions
observe the two behaviours diverging inside one run.
"""

# ruff: noqa: I001

import json
from argparse import Namespace
from conftest import load_script_module

_mem = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    'manage-execution-manifest.py',
    module_name='_mem_declared_contract_regression',
)
_mem._log_decision = lambda *a, **kw: None

cmd_compose = _mem.cmd_compose
cmd_lanes_preview = _mem.cmd_lanes_preview
read_manifest = _mem.read_manifest

_RETROSPECTIVE = 'plan-marshall:plan-retrospective'
_EMITTER = 'finalize-step-preference-emitter'


# =============================================================================
# Fixtures — seed a real marshal.json; the composer prefers it over the CSV
# =============================================================================


def _seed_marshal(steps: dict[str, dict | None]) -> None:
    """Write a marshal.json whose ``phase-6-finalize.steps`` map IS the candidate list.

    Key insertion order is the seed execution order, and each value is the step's
    nested param object — the channel a per-element ``lane`` override rides.
    """
    from file_ops import get_marshal_path

    marshal = {'plan': {'phase-6-finalize': {'steps': steps}}}
    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2), encoding='utf-8')


def _write_execution_profile(plan_context, plan_id: str, posture: str) -> None:
    """Seed ``status.metadata.execution_profile`` so the lane cutoff is deterministic."""
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_id, 'metadata': {'execution_profile': posture}}, indent=2),
        encoding='utf-8',
    )


def _write_plan_local_overrides(plan_context, plan_id: str, overrides: dict) -> None:
    """Seed the PLAN-LOCAL declaration channel for ``plan_id``.

    ``status.metadata.finalize_step_overrides`` mirrors marshal.json's
    ``phase-6-finalize.steps`` shape exactly — an id-keyed map of nested param
    objects, same key forms, same lane enum — but lives beside marshal rather than
    inside it, so one plan's answer never leaks into every later plan.
    """
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_id, 'metadata': {'finalize_step_overrides': overrides}}, indent=2),
        encoding='utf-8',
    )


def _compose_ns(
    plan_id: str,
    scope_estimate: str = 'multi_module',
    change_type: str = 'bug_fix',
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track='complex',
        scope_estimate=scope_estimate,
        recipe_key=None,
        affected_files_count=4,
        phase_5_steps='verify:quality-gate',
        phase_6_steps=None,  # marshal.json is authoritative
        commit_and_push=None,
    )


def _persisted_phase_6_steps(plan_id: str) -> list[str]:
    """Read the step list back from the PERSISTED manifest, not the compose result."""
    manifest = read_manifest(plan_id)
    assert manifest is not None, f'no manifest persisted for {plan_id}'
    return list(manifest['phase_6']['steps'])
