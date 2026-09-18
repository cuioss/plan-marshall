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
from pathlib import Path

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


def _compose_ns(plan_id: str, candidates: list[str] | None = None) -> Namespace:
    """A Row-7 default compose over ``candidates`` — no matrix narrowing, no scope gate."""
    return Namespace(
        plan_id=plan_id,
        change_type='feature',
        track='complex',
        scope_estimate='multi_module',
        recipe_key=None,
        affected_files_count=5,
        phase_5_steps='quality-gate,module-tests',
        phase_6_steps=','.join(_CANDIDATES if candidates is None else candidates),
        commit_and_push=None,
    )


def _seed_marshal(off_steps: list[str], candidates: list[str] | None = None) -> Path:
    """Write a marshal.json whose phase-6 steps map HAND-CARRIES the ``lane`` overrides.

    Written directly to disk rather than through ``manage-config``'s write surface
    — which is what makes the stored values in these arms *legacy* values: the
    write-time refusal never saw them. Every candidate becomes a key (the composer
    treats the map as the authoritative candidate list); a step in ``off_steps``
    carries ``{'lane': 'off'}`` and every other seeds as ``None``.
    """
    from file_ops import get_marshal_path

    steps = {c: ({'lane': 'off'} if c in off_steps else None) for c in (candidates or _CANDIDATES)}
    marshal = {
        'plan': {'phase-6-finalize': {'steps': steps}},
        'build': {'map': {'python': [{'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'}]}},
    }
    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2), encoding='utf-8')
    return marshal_path


def _write_execution_profile(plan_context, plan_id: str, posture: str) -> None:
    """Seed ``status.metadata.execution_profile`` — the posture the lane pass projects."""
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_id, 'metadata': {'execution_profile': posture}}, indent=2),
        encoding='utf-8',
    )


def _stub_footprint(footprint: list[str] | None) -> None:
    """Pin BOTH footprint seams in lock-step.

    ``_mem._resolve_footprint`` and ``extension_base._resolve_plan_footprint`` are
    symmetric peers that must never disagree about the same worktree, so a test
    that pinned only one would leave an activation pre-filter reading the real
    tree while its sibling read the fixture.
    """
    import extension_base

    def _resolve(_plan_id):
        return None if footprint is None else list(footprint)

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


# --- anti-vacuity: every fixture's class comes from the live resolver ---------


def test_every_fixture_class_is_derived():
    """Each fixture step's ``lane.class`` is READ, not assumed.

    Reading these from memory would let every arm below pass for a reason
    unrelated to the immunity rule — a floor arm satisfied by a step that is no
    longer floor-classed, or a matched negative satisfied by one that never was.
    The floor membership itself is derived too: the arms assert against
    ``_IMMUNE_TO_OFF_CLASSES``, not against the literal ``'core'``.
    """
    for step in [*_FLOOR_STEPS, 'archive-plan']:
        lane = _mem._resolve_element_lane(step)
        assert lane, f'{step} resolves no lane block, so it is not lane-participating at all'
        assert lane.get('class') in _IMMUNE_TO_OFF_CLASSES, (
            f'{step} no longer resolves to a floor class ({lane}) — the floor arms below are void.'
        )

    for step in (_OPT_OUT_STEP, _RECLASSIFIED_STEP):
        lane = _mem._resolve_element_lane(step)
        assert lane, f'{step} resolves no lane block'
        assert lane.get('class') not in _IMMUNE_TO_OFF_CLASSES, (
            f'{step} resolves to a FLOOR class ({lane}) — its off would be neutralized, '
            f'so it cannot serve as the matched negative.'
        )


# --- arm (a): a floor off is neutralized, under every pruning posture ---------


@pytest.mark.parametrize('posture', ['standard', 'minimal'])
def test_floor_element_survives_an_explicit_off_and_the_neutralization_is_reported(plan_context, posture):
    """A ``core`` element carrying an explicit ``off`` still composes — and says so.

    Asserted under BOTH pruning postures because the rule is a property of the
    class, not of the posture. ``full`` is excluded deliberately: that posture
    short-circuits the lane pass entirely, so it would report the same survival
    for a reason that has nothing to do with immunity (see the ``full``-posture
    control in the legacy-value arm below).

    Survival alone is not the contract — a composer that silently ignored the
    stored value would satisfy it. The warning is what makes the neutralization
    visible to the operator who wrote the ``off``, so both are asserted together.
    """
    plan_id = f'class-off-floor-{posture}'
    _seed_marshal(off_steps=_FLOOR_STEPS)
    _stub_footprint(_FOOTPRINT)
    _write_execution_profile(plan_context, plan_id, posture)

    result = cmd_compose(_compose_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    assert result['execution_profile'] == posture

    composed = _composed_steps(plan_id)
    dropped = _dropped_reasons(result)
    warned = _warnings_by_step(result)
    for step in _FLOOR_STEPS:
        assert step in composed, f'{step} must survive a floor off under {posture}'
        assert step not in dropped, f'{step} was dropped despite being floor-classed'
        assert step in warned, f'{step} neutralized its off silently — the operator is not told'
        assert 'immune' in warned[step]
        assert 'cannot be weakened' in warned[step]
        # The warning names the CLASS it resolved, so the operator can tell WHY the
        # value was refused rather than only THAT it was.
        assert _mem._resolve_element_lane(step)['class'] in warned[step]


# --- arm (b): the matched negative — the same off on a non-floor class binds --


@pytest.mark.parametrize('posture', ['standard', 'minimal'])
def test_non_floor_element_is_dropped_by_the_same_off_under_the_same_posture(plan_context, posture):
    """MATCHED NEGATIVE on the CLASS axis: identical value, identical posture.

    Without this arm, the floor arm above would be satisfied by a lane pass that
    had simply stopped dropping anything at all. The only difference between the
    two composes is which class the target step declares, which is what attributes
    the split to the immunity rule rather than to the posture, the candidate list,
    or a disabled lane pass.
    """
    plan_id = f'class-off-nonfloor-{posture}'
    _seed_marshal(off_steps=[_OPT_OUT_STEP])
    _stub_footprint(_FOOTPRINT)
    _write_execution_profile(plan_context, plan_id, posture)

    result = cmd_compose(_compose_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    composed = _composed_steps(plan_id)
    dropped = _dropped_reasons(result)
    warned = _warnings_by_step(result)

    assert _OPT_OUT_STEP not in composed
    assert _OPT_OUT_STEP in dropped
    # The drop is attributed to the opt-out, not to the posture cutoff — two
    # different facts about the same removal, and an operator reading the record
    # needs to tell them apart.
    assert "'off'" in dropped[_OPT_OUT_STEP]
    assert 'posture cutoff' not in dropped[_OPT_OUT_STEP]
    # A real opt-out is a clean drop: nothing was neutralized, so nothing warns.
    assert _OPT_OUT_STEP not in warned
    # The floor steps in the same compose declare no override and are untouched —
    # the drop is the override's doing, not the compose's.
    for step in _FLOOR_STEPS:
        assert step in composed


# --- arm (c): a legacy stored inert value ------------------------------------


def test_a_legacy_stored_inert_off_still_produces_the_compose_time_warning(plan_context):
    """A stored inert ``off`` is reported at compose time, however it got there.

    The write surface now REFUSES an ``off`` on a floor element, so no new one can
    be stored — but the refusal is a gate on future writes, not a sweep of what is
    already on disk. Values written before it existed, and any written by hand as
    this fixture does, survive in marshal.json. Compose must therefore keep
    neutralizing and reporting them rather than treating an inert stored value as
    impossible.

    The write-time refusal itself is NOT re-asserted here — it is owned by
    ``test_cmd_quality_phases.py``'s step-set refusal cases, and duplicating it
    would make this module a second source of truth for a rule it only consumes.
    """
    plan_id = 'class-off-legacy-stored'
    _seed_marshal(off_steps=[_FLOOR_STEPS[0]])
    _stub_footprint(_FOOTPRINT)
    _write_execution_profile(plan_context, plan_id, 'standard')

    result = cmd_compose(_compose_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    warned = _warnings_by_step(result)
    assert _FLOOR_STEPS[0] in warned
    assert 'immune' in warned[_FLOOR_STEPS[0]]
    assert _FLOOR_STEPS[0] in _composed_steps(plan_id)


def test_a_legacy_stored_inert_off_is_silent_under_the_full_posture(plan_context):
    """The caveat on the arm above: ``full`` reports nothing, because it resolves nothing.

    The ``full`` posture short-circuits the lane pass, so no element is examined
    and no neutralization is computed — the stored inert value is invisible. This
    is stated as its own control rather than left implicit because the two facts
    read as contradictory otherwise: a value the composer "always reports" is in
    fact reported only under a posture that prunes. An operator on a full-posture
    plan learns nothing about their inert override from this channel.
    """
    plan_id = 'class-off-legacy-full'
    _seed_marshal(off_steps=[_FLOOR_STEPS[0]])
    _stub_footprint(_FOOTPRINT)
    _write_execution_profile(plan_context, plan_id, 'full')

    result = cmd_compose(_compose_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    assert result['execution_profile'] == 'full'
    assert result['lane_warnings'] == []
    assert result['lane_dropped'] == []
    assert _FLOOR_STEPS[0] in _composed_steps(plan_id)


# --- arm (d): the reclassified element drops by BOTH routes ------------------


def test_reclassified_lessons_capture_is_dropped_by_an_explicit_off(plan_context):
    """Route 1 — the ``off`` now BINDS, which is the point of the reclassification.

    Under its former ``core`` classification this exact stored value was
    neutralized: the one control an operator had over an advisory step did not
    work. The baseline compose in the same test is what makes the drop
    attributable to the override rather than to the posture — ``standard`` keeps
    the step when nothing is declared.
    """
    _stub_footprint(_FOOTPRINT)

    # Baseline: no override at all → the prunable class default (standard) is
    # within the standard posture, so the step is kept.
    _seed_marshal(off_steps=[])
    _write_execution_profile(plan_context, 'lessons-off-baseline', 'standard')
    baseline = cmd_compose(_compose_ns('lessons-off-baseline'))
    assert baseline is not None and baseline['status'] == 'success'
    assert _RECLASSIFIED_STEP in _composed_steps('lessons-off-baseline')
    assert _RECLASSIFIED_STEP not in _dropped_reasons(baseline)

    # Same posture, same candidates — only the stored override differs.
    _seed_marshal(off_steps=[_RECLASSIFIED_STEP])
    _write_execution_profile(plan_context, 'lessons-off-declared', 'standard')
    result = cmd_compose(_compose_ns('lessons-off-declared'))

    assert result is not None and result['status'] == 'success'
    dropped = _dropped_reasons(result)
    assert _RECLASSIFIED_STEP not in _composed_steps('lessons-off-declared')
    assert _RECLASSIFIED_STEP in dropped
    assert "'off'" in dropped[_RECLASSIFIED_STEP]
    # An honoured opt-out is a clean drop — a neutralization warning here would
    # mean the element was still being treated as floor.
    assert _RECLASSIFIED_STEP not in _warnings_by_step(result)


def test_reclassified_lessons_capture_falls_outside_the_minimal_posture_with_no_override(plan_context):
    """Route 2 — the accepted side effect: a ``minimal`` plan stops running it.

    No override is declared anywhere here. A non-floor class defaults to tier
    ``standard`` rather than ``core``'s ``minimal``, so the step now sits above the
    ``minimal`` cutoff. This is a consequence of the same property that makes its
    ``off`` honourable, and it is pinned deliberately rather than discovered later:
    the recorded reason must name the POSTURE CUTOFF, not an opt-out, because no
    operator asked for this removal.
    """
    plan_id = 'lessons-minimal-no-override'
    _seed_marshal(off_steps=[])
    _stub_footprint(_FOOTPRINT)
    _write_execution_profile(plan_context, plan_id, 'minimal')

    result = cmd_compose(_compose_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    dropped = _dropped_reasons(result)
    assert _RECLASSIFIED_STEP not in _composed_steps(plan_id)
    assert _RECLASSIFIED_STEP in dropped
    assert 'posture cutoff' in dropped[_RECLASSIFIED_STEP]
    assert "'off'" not in dropped[_RECLASSIFIED_STEP]
    # The floor steps in the same minimal compose are untouched, so the drop is the
    # tier cutoff acting on ONE class rather than the posture emptying the list.
    composed = _composed_steps(plan_id)
    for step in _FLOOR_STEPS:
        assert step in composed


# --- arm (e): predicate dormancy ---------------------------------------------


def test_prunable_when_is_declared_but_never_evaluated_at_compose_time(plan_context):
    """``prunable_when`` is contract-live and implementation-DORMANT.

    The reclassification's third consequence — eligibility for a predicate-driven
    skip — changes nothing today, because no composer code reads the key. This arm
    holds that claim to its word: the fixture step declares a ``prunable_when``
    predicate whose condition is satisfied (an empty footprint is the
    ``no_code_delta`` shape), its effective tier is within the posture, and it is
    KEPT.

    ⛔ This test is designed to FAIL the day predicate evaluation is wired. That
    failure is the signal, not a defect: the dormancy sentence in the step's own
    documentation asserts a property of the composer, and it must be revisited in
    the same change that makes it false rather than being discovered stale later.
    """
    plan_id = 'prunable-when-dormant'
    _seed_marshal(off_steps=[])
    # An empty — not unresolvable — footprint: the resolvable-and-genuinely-empty
    # state a `no_code_delta` predicate would read as "the condition holds".
    _stub_footprint([])
    _write_execution_profile(plan_context, plan_id, 'standard')

    # Derived, not assumed: the arm means nothing unless the fixture step actually
    # declares a predicate for the composer to ignore.
    lane = _mem._resolve_element_lane(_OPT_OUT_STEP)
    assert lane and lane.get('prunable_when'), (
        f'{_OPT_OUT_STEP} declares no prunable_when, so this arm pins no dormancy.'
    )

    result = cmd_compose(_compose_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    assert _OPT_OUT_STEP in _composed_steps(plan_id)
    assert _OPT_OUT_STEP not in _dropped_reasons(result)
