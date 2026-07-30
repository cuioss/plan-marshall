#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Compose-level regression: an operator-named step survives the implicit scope gate.

**The defect.** ``_apply_scope_gated_finalize`` is an IMPLICIT gate — it infers
"you probably do not want this" from ``scope_estimate``. Its one escape hatch is
declared-lane immunity: a step carrying an explicit non-``auto`` per-element
``lane`` is never dropped. Before the fix that immunity predicate could only see
a declaration written into project-wide ``marshal.json``, so an operator's
answer *for this plan* — which must never leak into every later plan — was
invisible to it and the named step was silently subtracted.

**What this module pins, end to end through ``cmd_compose``.** Four arms, each
of which fails on its own if the corresponding half of the fix regresses:

1. **The immunity arm** — a plan-local declaration at
   ``status.metadata.finalize_step_overrides`` makes ``plan-marshall:plan-retrospective``
   immune at ``scope_estimate=surgical``: it appears in ``scope_gated_finalize_immune``,
   not in ``scope_gated_finalize_dropped``, and survives into ``phase_6.steps``.
2. **The negative control** — the byte-identical compose with NO declaration
   drops the step. Without this arm the immunity assertion is satisfied by a
   scope gate that stopped dropping anything at all.
3. **The anti-leak control** — ``marshal.json`` is byte-identical before and
   after. A "fix" that made immunity work by writing the operator's answer into
   the project-wide file would pass arms 1 and 2 and violate the entire reason
   the plan-local channel exists.
4. **The R2 peer** — the SAME plan-local declaration mechanism, applied to a
   ceremony-owning step, must reach the OTHER reader
   (``_read_step_owned_knob`` → ``_read_finalize_gates``) and produce the same
   gate value a marshal declaration produces. This arm is what makes the module
   insufficient-proof-resistant: a fix that widened only ``_lane_override_for``
   passes arms 1-3 and fails here, which is exactly the half-applied
   symmetric-pair defect. The arm is written as an EQUIVALENCE between the two
   declaration channels rather than as two independent expectations, so it fails
   the moment the channels diverge even if each still "works" alone.

The ceremony owner exercised here is ``default:finalize-step-security-audit``,
deliberately distinct from the ``default:pre-submission-self-review`` owner that
``test_ceremony_finalize_selection.py`` already covers — one declaration channel
reaching one owner is not evidence it reaches another.
"""

import json
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

_mem = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    'manage-execution-manifest.py',
    module_name='_mem_operator_named_step_lane_immunity',
)

cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Silence the in-process decision-log writer. Every name assigned below MUST
# still exist on the module: ``setattr`` succeeds for a name that was never
# defined, so a stale entry silently RE-CREATES a removed attribute instead of
# failing loudly — which is how a neutralization outlives the emitter it was
# written for.
_mem._emit_decision_log = lambda *a, **kw: None

# Speed stub: the per-step execution_tier stamp subprocesses ``architecture
# resolve`` once per canonical-verify step. The stamp is advisory and orthogonal
# to every assertion here, so it is pinned rather than paid for. Scoped to THIS
# module's own copy of the composer (``load_script_module`` registered it under a
# module-unique name), so no sibling test module observes the stub.
_mem._resolve_step_execution_tier = lambda _canonical, _plan_id: 'per_task'

#: The operator-named step. A genuinely opt-in ``{bundle}:{skill}`` finalize step
#: (never canonicalized to a bare name) that IS a member of the ``surgical``
#: scope-gate drop set — so the gate really fires on it and immunity is the only
#: thing that can keep it.
_OPERATOR_NAMED_STEP = 'plan-marshall:plan-retrospective'

#: The ceremony-owning step for the R2 peer arm.
_SECURITY_AUDIT_OWNER = 'default:finalize-step-security-audit'

_PHASE_5_CSV = 'verify:quality-gate,verify:module-tests'


def _candidates() -> list[str]:
    """The phase-6 candidate list: the defaults plus the operator-named step."""
    return [*DEFAULT_PHASE_6_STEPS, _OPERATOR_NAMED_STEP]


def _seed_marshal(candidates: list[str], step_params: dict[str, dict] | None = None) -> Path:
    """Write a marshal.json whose ``phase-6-finalize.steps`` map IS ``candidates``.

    The composer treats a marshal ``steps`` map as the AUTHORITATIVE phase-6
    candidate list (preferred over the ``--phase-6-steps`` CSV), so the seeded map
    must carry the full candidate set in execution order. ``step_params`` overlays
    the marshal-side declaration for the channel-equivalence arm; every other
    candidate seeds ownerless.

    The ``build.map`` block is present so the build-necessity authority has globs
    to consult — without it every verdict degrades to "no buildable file types"
    and the pre-push gate's fate would be decided by the wrong signal.
    """
    from file_ops import get_marshal_path

    declared = step_params or {}
    steps: dict[str, dict | None] = {c: declared.get(c) for c in candidates}
    marshal = {
        'plan': {'phase-6-finalize': {'steps': steps}},
        'build': {
            'map': {
                'python': [{'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'}],
            },
        },
    }
    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2))
    return marshal_path


def _write_status(plan_context, plan_id: str, overrides: dict | None = None) -> Path:
    """Seed ``status.json`` with (optionally) a plan-local step-override map.

    ``overrides=None`` writes the SAME file shape with no declaration, so the
    negative control differs from the positive arm in exactly one key.
    """
    metadata: dict = {}
    if overrides is not None:
        metadata['finalize_step_overrides'] = overrides
    status_path = Path(plan_context.plan_dir_for(plan_id)) / 'status.json'
    status_path.write_text(json.dumps({'metadata': metadata}))
    return status_path


def _compose_ns(
    plan_id: str,
    candidates: list[str],
    scope_estimate: str = 'surgical',
    change_type: str = 'bug_fix',
    affected_files_count: int = 2,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track='simple',
        scope_estimate=scope_estimate,
        recipe_key=None,
        affected_files_count=affected_files_count,
        phase_5_steps=_PHASE_5_CSV,
        phase_6_steps=','.join(candidates),
        commit_and_push=None,
    )


def _manifest_phase_6_steps(result: dict) -> list[str]:
    manifest = read_manifest(result['plan_id'])
    assert manifest is not None
    return list(manifest.get('phase_6', {}).get('steps', []))


# =============================================================================
# Arm 1 + Arm 2 — immunity, and the negative control that makes it non-vacuous
# =============================================================================


class TestPlanLocalDeclarationGrantsScopeGateImmunity:
    """A plan-local ``lane`` survives ``scope_gated_finalize`` at ``surgical``."""

    def test_operator_named_step_is_immune_and_survives(self, plan_context):
        plan_id = 'operator-named-immune'
        candidates = _candidates()
        _seed_marshal(candidates)
        _write_status(plan_context, plan_id, {_OPERATOR_NAMED_STEP: {'lane': 'full'}})

        result = cmd_compose(_compose_ns(plan_id, candidates))

        assert result is not None and result['status'] == 'success'
        assert _OPERATOR_NAMED_STEP in result['scope_gated_finalize_immune']
        assert _OPERATOR_NAMED_STEP not in result['scope_gated_finalize_dropped']
        assert _OPERATOR_NAMED_STEP in _manifest_phase_6_steps(result)

    def test_no_declaration_still_drops_the_step(self, plan_context):
        """The negative control — without it the immunity arm is vacuous.

        Identical inputs except the declaration. A scope gate that had simply
        stopped dropping anything would satisfy the positive arm above and fail
        here, so this is what proves the gate is live and immunity is what
        spared the step.
        """
        plan_id = 'operator-named-undeclared'
        candidates = _candidates()
        _seed_marshal(candidates)
        _write_status(plan_context, plan_id, None)

        result = cmd_compose(_compose_ns(plan_id, candidates))

        assert result is not None and result['status'] == 'success'
        assert _OPERATOR_NAMED_STEP in result['scope_gated_finalize_dropped']
        assert _OPERATOR_NAMED_STEP not in result['scope_gated_finalize_immune']
        assert _OPERATOR_NAMED_STEP not in _manifest_phase_6_steps(result)

    def test_immunity_is_scoped_to_the_declaring_plan(self, plan_context):
        """One plan's answer must not travel to the next plan.

        Two composes against the SAME marshal.json: the first plan declares, the
        second does not. The second must still be dropped — the assertion that
        fails if the declaration were persisted anywhere project-wide.
        """
        candidates = _candidates()
        _seed_marshal(candidates)

        _write_status(plan_context, 'declaring-plan', {_OPERATOR_NAMED_STEP: {'lane': 'full'}})
        declaring = cmd_compose(_compose_ns('declaring-plan', candidates))

        _write_status(plan_context, 'sibling-plan', None)
        sibling = cmd_compose(_compose_ns('sibling-plan', candidates))

        assert declaring is not None and sibling is not None
        assert _OPERATOR_NAMED_STEP in declaring['scope_gated_finalize_immune']
        assert _OPERATOR_NAMED_STEP in sibling['scope_gated_finalize_dropped']


# =============================================================================
# Arm 3 — the anti-leak control
# =============================================================================


class TestPlanLocalDeclarationNeverTouchesMarshal:
    """The plan-local channel lives BESIDE marshal.json, never inside it."""

    def test_marshal_json_is_byte_identical_across_the_compose(self, plan_context):
        plan_id = 'operator-named-no-leak'
        candidates = _candidates()
        marshal_path = _seed_marshal(candidates)
        before = marshal_path.read_bytes()
        _write_status(plan_context, plan_id, {_OPERATOR_NAMED_STEP: {'lane': 'full'}})

        result = cmd_compose(_compose_ns(plan_id, candidates))

        assert result is not None and result['status'] == 'success'
        # The immunity really was granted (otherwise an unchanged marshal proves
        # nothing — a compose that ignored the declaration also leaves it alone).
        assert _OPERATOR_NAMED_STEP in result['scope_gated_finalize_immune']
        assert marshal_path.read_bytes() == before


# =============================================================================
# Arm 4 — the R2 peer: the SECOND reader sees the same declaration
# =============================================================================


class TestPlanLocalDeclarationReachesTheCeremonyReader:
    """``_read_finalize_gates`` resolves a plan-local declaration identically.

    ``_lane_override_for`` (scope-gate immunity) and ``_read_step_owned_knob``
    (each ceremony gate's run-at-all knob) resolve the SAME
    ``steps[<step>].lane`` field through different readers. Widening only the
    first is the half-applied symmetric-pair defect: the step would be spared the
    scope gate and then dropped by a ceremony gate that never heard about the
    declaration. Every assertion below is written as an equivalence between the
    plan-local and marshal channels, which is what fails when they diverge.
    """

    def test_read_finalize_gates_resolves_the_plan_local_lane(self, plan_context):
        """The direct reader-level assertion, independent of any compose path."""
        plan_id = 'ceremony-owner-plan-local'
        candidates = _candidates()
        _seed_marshal(candidates)
        _write_status(plan_context, plan_id, {_SECURITY_AUDIT_OWNER: {'lane': 'off'}})

        gates = _mem._read_finalize_gates(plan_id)

        assert gates['security_audit'] == 'never'

    def test_plan_local_and_marshal_channels_produce_the_same_gate(self, plan_context):
        candidates = _candidates()

        # Channel A — plan-local only; marshal declares nothing for the owner.
        _seed_marshal(candidates)
        _write_status(plan_context, 'secaudit-plan-local', {_SECURITY_AUDIT_OWNER: {'lane': 'off'}})
        plan_local = cmd_compose(_compose_ns('secaudit-plan-local', candidates))

        # Channel B — marshal only; the plan declares nothing.
        _seed_marshal(candidates, step_params={'finalize-step-security-audit': {'lane': 'off'}})
        _write_status(plan_context, 'secaudit-marshal', None)
        marshal = cmd_compose(_compose_ns('secaudit-marshal', candidates))

        assert plan_local is not None and marshal is not None
        assert plan_local['ceremony_finalize_gates']['security_audit'] == 'never'
        assert (
            plan_local['ceremony_finalize_gates']['security_audit']
            == marshal['ceremony_finalize_gates']['security_audit']
        )
        assert 'finalize-step-security-audit' not in _manifest_phase_6_steps(plan_local)
        assert 'finalize-step-security-audit' not in _manifest_phase_6_steps(marshal)

    def test_one_declaration_reaches_both_readers_at_once(self, plan_context):
        """The assertion that pins the defect directly.

        A single plan-local declaration on a ceremony-owning step must
        SIMULTANEOUSLY (a) resolve the ceremony gate and (b) grant scope-gate
        immunity. If only the immunity predicate saw the plan-local channel — the
        pre-fix state — the step would be spared one subtraction and silently
        taken by another.
        """
        plan_id = 'secaudit-both-readers'
        candidates = _candidates()
        _seed_marshal(candidates)
        _write_status(
            plan_context,
            plan_id,
            {
                _SECURITY_AUDIT_OWNER: {'lane': 'minimal'},
                _OPERATOR_NAMED_STEP: {'lane': 'full'},
            },
        )

        result = cmd_compose(_compose_ns(plan_id, candidates))

        assert result is not None and result['status'] == 'success'
        # Reader 2 — the ceremony gate resolved the plan-local ``minimal``.
        assert result['ceremony_finalize_gates']['security_audit'] == 'always'
        # Reader 1 — the immunity predicate resolved the sibling declaration.
        assert _OPERATOR_NAMED_STEP in result['scope_gated_finalize_immune']
        assert 'finalize-step-security-audit' in _manifest_phase_6_steps(result)
