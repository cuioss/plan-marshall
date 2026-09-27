#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Controls for the lane-CLASS ``off`` immunity rule and for the reclassified element.

Two questions this module answers, both about ``lane.class`` and nothing else:

1. Does a weakening ``off`` on a FLOOR class (``core`` / ``derived-state``) stay
   neutralized — the element kept, the neutralization reported — while the same
   ``off`` on a non-floor class remains a real opt-out?
2. Does ``lessons-capture``, reclassified off the floor to ``prunable``, now obey
   an ``off`` and fall outside the ``minimal`` posture?

**Not a duplicate of ``test_operator_named_step_lane_immunity.py``.** That module
pins SCOPE-GATE immunity: an explicitly declared lane keeps a step from being
dropped by the implicit ``scope_gated_finalize`` pre-filter. This one pins
CLASS-OFF immunity: the lane resolver ignores a weakening ``off`` on a floor
class. Different mechanism, different stage, different input — the two share only
the word "immunity", which is why this module is named for the class rule rather
than for the floor.

**The classes are DERIVED, not remembered.** Every arm below turns on which side
of the floor a step's ``lane.class`` falls on, and that fact lives in shipped
frontmatter that this plan itself changed. ``test_every_fixture_class_is_derived``
reads each one from the live resolver, so a reclassification that invalidates an
arm fails loudly here instead of letting the arm pass for an unrelated reason.
The composes below therefore run against the REAL frontmatter — no canned lane
blocks — because the shipped classification is the subject, not a fixture.
"""

import json
from argparse import Namespace

import pytest
from _manifest_lanes import _IMMUNE_TO_OFF_CLASSES

from conftest import load_script_module

_mem = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    'manage-execution-manifest.py',
    module_name='_mem_script_lane_class_off_immunity',
)
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest

# Silence the best-effort decision-log subprocesses so the tests do not depend on
# a running executor. Every name assigned here must still exist on the module:
# ``setattr`` succeeds for a name that was never defined, so a stale entry would
# re-create a removed emitter instead of failing loudly.
_mem._log_decision = lambda *a, **kw: None
_mem._log_commit_push_omitted = lambda *a, **kw: None
_mem._log_scope_gated_finalize_subtraction = lambda *a, **kw: None
_mem._log_ceremony_finalize_selection = lambda *a, **kw: None
_mem._log_candidate_source = lambda *a, **kw: None
_mem._log_prefilter_omitted = lambda *a, **kw: None
_mem._log_execution_tier_routing = lambda *a, **kw: None


# --- fixtures ----------------------------------------------------------------

#: Floor elements — shipped ``lane.class: core``. A weakening ``off`` on these is
#: neutralized. Three rather than one: the rule is a property of the CLASS, and a
#: single-step arm could pass for a reason peculiar to that step.
_FLOOR_STEPS = ['push', 'create-pr', 'branch-cleanup']

#: The matched negative — shipped ``lane.class: prunable``, so its ``off`` binds.
#: Chosen because it also declares a ``prunable_when`` predicate, which the
#: dormancy arm needs.
_OPT_OUT_STEP = 'adr-propose'

#: The element deliverable 5 moved OFF the floor: ``core`` → ``prunable``.
_RECLASSIFIED_STEP = 'lessons-capture'

#: The composed candidate set. ``archive-plan`` is the terminus every finalize
#: list carries; it is floor-classed and declares no override in any arm.
_CANDIDATES = [*_FLOOR_STEPS, _OPT_OUT_STEP, _RECLASSIFIED_STEP, 'archive-plan']

#: A production path, so the build verdict is ``build`` and the whole-tree
#: build-verdict assertion has a real footprint to agree with.
_FOOTPRINT = ['marketplace/bundles/plan-marshall/skills/demo/scripts/demo.py']


def _compose_ns(plan_id: str) -> Namespace:
    """A Row-7 default compose over ``_CANDIDATES`` — no matrix narrowing, no scope gate."""
    return Namespace(
        plan_id=plan_id,
        change_type='feature',
        track='complex',
        scope_estimate='multi_module',
        recipe_key=None,
        affected_files_count=5,
        phase_5_steps='quality-gate,module-tests',
        phase_6_steps=','.join(_CANDIDATES),
        commit_and_push=None,
    )


def _seed_marshal(off_steps: list[str]) -> None:
    """Write a marshal.json whose phase-6 steps map HAND-CARRIES the ``lane`` overrides.

    Written directly to disk rather than through ``manage-config``'s write surface
    — which is what makes the stored values in these arms *legacy* values: the
    write-time refusal never saw them. Every candidate becomes a key (the composer
    treats the map as the authoritative candidate list); a step in ``off_steps``
    carries ``{'lane': 'off'}`` and every other seeds as ``None``.
    """
    from file_ops import get_marshal_path

    steps = {c: ({'lane': 'off'} if c in off_steps else None) for c in _CANDIDATES}
    marshal = {
        'plan': {'phase-6-finalize': {'steps': steps}},
        'build': {'map': {'python': [{'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'}]}},
    }
    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2), encoding='utf-8')


def _write_execution_profile(plan_context, plan_id: str, posture: str) -> None:
    """Seed ``status.metadata.execution_profile`` — the posture the lane pass projects."""
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_id, 'metadata': {'execution_profile': posture}}, indent=2),
        encoding='utf-8',
    )


def _stub_footprint(footprint: list[str]) -> None:
    """Pin BOTH footprint seams in lock-step.

    ``_mem._resolve_footprint`` and ``extension_base._resolve_plan_footprint`` are
    symmetric peers that must never disagree about the same worktree, so a test
    that pinned only one would leave an activation pre-filter reading the real
    tree while its sibling read the fixture.
    """
    import extension_base

    def _resolve(_plan_id):
        return list(footprint)

    _mem._resolve_footprint = _resolve
    extension_base._resolve_plan_footprint = _resolve


@pytest.fixture(autouse=True)
def _restore_footprint_resolvers():
    """Snapshot + restore both seams so a stub never leaks into an unrelated module.

    ``extension_base`` is shared cross-skill: restoring only the ``_mem`` half once
    left a sibling test module observing this module's stub for the rest of the
    worker process.
    """
    import extension_base

    original_mem = _mem._resolve_footprint
    original_shared = extension_base._resolve_plan_footprint
    yield
    _mem._resolve_footprint = original_mem
    extension_base._resolve_plan_footprint = original_shared


def _composed_steps(plan_id: str) -> list[str]:
    """Read the persisted manifest's ``phase_6.steps``."""
    manifest = read_manifest(plan_id)
    assert manifest is not None, f'compose persisted no manifest for {plan_id}'
    return list(manifest.get('phase_6', {}).get('steps', []))


def _dropped_reasons(result: dict) -> dict[str, str]:
    """Index ``lane_dropped``'s ``{step, reason}`` records by step id."""
    return {record['step']: record['reason'] for record in result['lane_dropped']}


def _warnings_by_step(result: dict) -> dict[str, str]:
    """Index ``lane_warnings``'s ``{step, warning}`` records by step id."""
    return {record['step']: record['warning'] for record in result['lane_warnings']}
