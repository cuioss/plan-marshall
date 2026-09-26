#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _CEREMONY_LANE_GATES,
    _GATE_OWNER_STEP,
    Path,
    json,
)
from _manage_execution_manifest_ceremony_finalize_selection_fixtures_surface_module import (
    _phase_6_with_ceremony_steps,
)


def _seed_marshal(
    finalize_gates: dict[str, object] | None = None,
    ci_provider: str | None = None,
    candidates: list[str] | None = None,
) -> Path:
    """Write a marshal.json carrying the phase-6-finalize gates at their homes.

    Every ceremony gate (``qgate`` / ``self_review`` / ``simplify`` /
    ``security_audit``) is written as its owning finalize step's ``lane`` override
    (``off``/``minimal``/``standard``) nested under the step's param object in
    ``plan.phase-6-finalize.steps`` (the id-keyed map the reader consumes via
    ``_read_step_owned_knob``); any other step-folded knob writes under its own
    param key. There is no flat phase-level ``qgate`` sibling. Callers pass
    ``finalize_gates`` values in the ``lane`` vocabulary.

    Because the composer treats a marshal.json ``steps`` map as the AUTHORITATIVE
    phase-6 candidate list (preferred over the ``--phase-6-steps`` CSV), the
    ``steps`` map written here must carry the FULL candidate set — every candidate
    becomes a key, and the folded knobs nest onto their owning steps. ``candidates``
    defaults to the standard ceremony candidate set used by ``_compose_ns``; tests
    that compose with a custom candidate list pass the matching list here so the
    seeded ``steps`` map and the composed candidate list stay in sync.
    """
    from file_ops import get_marshal_path

    if candidates is None:
        candidates = _phase_6_with_ceremony_steps().split(',')

    def _strip_default(step_id: str) -> str:
        return step_id[len('default:') :] if step_id.startswith('default:') else step_id

    phase_6: dict = {}
    if finalize_gates is not None:
        # Resolve each step-folded gate to its owning step's FULL-prefixed id and
        # collect the nested knob params. A ceremony gate writes its value under the
        # owning step's ``lane`` param; any other knob writes under its own key. A
        # gate whose owner is absent from the candidate list is a no-op (mirrors the
        # runtime: an absent step owns no params to read).
        owned_params: dict[str, dict] = {}
        stripped_candidates = {_strip_default(c) for c in candidates}
        for gate, value in finalize_gates.items():
            owner = _GATE_OWNER_STEP.get(gate)
            if owner is None:
                phase_6[gate] = value
                continue
            if _strip_default(owner) not in stripped_candidates:
                continue
            param_key = 'lane' if gate in _CEREMONY_LANE_GATES else gate
            owned_params.setdefault(owner, {})[param_key] = value

        # Build the FULL candidate keyed-map IN ORDER so the composer's candidate
        # list AND its execution order are unchanged. A candidate that owns nested
        # knobs is written under the owner's FULL-prefixed key at the same
        # position (the composer strips ``default:`` at intake, so the candidate
        # list is unaffected); every other candidate seeds as None (ownerless).
        owner_by_stripped = {_strip_default(o): o for o in owned_params}
        steps: dict[str, dict | None] = {}
        for candidate in candidates:
            owner_key = owner_by_stripped.get(_strip_default(candidate))
            if owner_key is not None:
                steps[owner_key] = owned_params[owner_key]
            else:
                steps[candidate] = None
        phase_6['steps'] = steps

    # Pre-push-quality-gate activation derives from build.map globs
    # (D7/D8). The `**/*.py` build_map glob matches the stubbed footprint so the
    # pre_push_quality_gate_inactive pre-filter does NOT drop the qgate step in
    # the `auto` baseline (lets us isolate the ceremony transform's behaviour).
    marshal: dict = {
        'plan': {'phase-6-finalize': phase_6},
        'build': {
            'map': {
                'python': [
                    {'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'},
                ],
            },
        },
    }
    if ci_provider:
        marshal['providers'] = [{'skill_name': f'plan-marshall:workflow-integration-{ci_provider}', 'category': 'ci'}]

    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2))
    return marshal_path


def _seed_marshal_lane_overrides(candidates, off_steps):
    """Write a marshal.json whose phase-6 steps map carries per-step ``lane`` overrides.

    Every candidate becomes a key in the AUTHORITATIVE ``plan.phase-6-finalize.steps``
    map (the composer prefers it over the CSV). A step in ``off_steps`` carries a
    hand-written ``{'lane': 'off'}`` param; every other step seeds as ``None``.
    """
    from file_ops import get_marshal_path

    steps = {c: ({'lane': 'off'} if c in off_steps else None) for c in candidates}
    marshal = {
        'plan': {'phase-6-finalize': {'steps': steps}},
        'build': {
            'map': {
                'python': [
                    {'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'},
                ],
            },
        },
    }
    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2))
    return marshal_path
