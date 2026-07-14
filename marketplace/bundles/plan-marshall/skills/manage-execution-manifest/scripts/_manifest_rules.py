#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pre-filter, ceremony-finalize, and verification-command rule helpers.

Extracted verbatim from ``manage-execution-manifest.py``: the marshal.json step
map reads, the candidate-narrowing pre-filters (commit/push, aspect, simplify,
security-audit, scope-gated finalize), the ceremony-finalize lane-driven
selection, the CI-provider read, and the build verification-command parser. Every
function here is log-free and calls no test-patched name; the entry re-exports
them and keeps the patched callers.
"""

import json
import shlex

from _manifest_core import _strip_default_prefix
from _manifest_lanes import _effective_lane_tier, _lane_override_for
from file_ops import get_marshal_path, read_json


def _read_marshal_phase_step_map(phase_key: str) -> dict[str, dict] | None:
    """Read the id-keyed step MAP for ``phase_key`` from marshal.json.

    ``phase_key`` is the marshal.json key (e.g. ``'phase-5-execute'`` or
    ``'phase-6-finalize'``). The map-field read under that key is phase-aware:
    ``phase-5-execute`` reads ``verification_steps`` while ``phase-6-finalize``
    (and any other phase) reads ``steps``.

    The on-disk serial form is the canonical keyed map:
    ``{step_id: {param: value, ...}, ...}``, with key insertion order as the
    execution order and each value the step's nested param object (``{}`` for a
    config-less step). This is the sole accepted on-disk shape — there is no
    list / dual-form tolerance.

    Returns the internal id-keyed dict (``{step_id: param-object}``, ``{}`` for
    config-less steps, prefixes preserved), or ``None`` when the marshal file is
    missing, the keys are absent, or the value is not a dict.
    """
    marshal_path = get_marshal_path()
    if not marshal_path.exists():
        return None
    try:
        data = read_json(marshal_path, default={})
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    plan = data.get('plan')
    if not isinstance(plan, dict):
        return None
    phase = plan.get(phase_key)
    if not isinstance(phase, dict):
        return None
    field = 'verification_steps' if phase_key == 'phase-5-execute' else 'steps'
    steps = phase.get(field)
    if isinstance(steps, dict):
        return {
            step_id: (params if isinstance(params, dict) else {})
            for step_id, params in steps.items()
            if isinstance(step_id, str) and step_id
        }
    return None


def _snapshot_step_params(
    final_step_ids: list[str], marshal_step_map: dict[str, dict] | None
) -> dict[str, dict | None]:
    """Snapshot the resolved per-step params for the FINAL selected steps.

    ``final_step_ids`` is the composer's final in-manifest step-id list (bare
    names — the ``default:`` prefix is stripped at the compose boundary).
    ``marshal_step_map`` is the marshal.json id-keyed map (full refs preserved),
    as returned by :func:`_read_marshal_phase_step_map`, or ``None`` when the
    marshal file is absent (CSV-fallback path).

    Returns a snapshot ``{step_id: params}`` keyed by the in-manifest (bare)
    step id, carrying each selected step's resolved param object copied from the
    marshal map. Only steps that survive into ``final_step_ids`` are snapshotted.
    An OWNERLESS step (no marshal-side entry, an empty param object, or when the
    marshal map is absent) snapshots as ``None`` (serialized as ``null``) — no
    noisy empty ``{}`` block is written to the manifest. The read boundary
    (:func:`_normalize_step_params_block`) coerces every ``null`` / ``{}`` /
    TOON-``''`` value back to an empty dict, so ownerless steps read back as
    ``{}``. The marshal keys are matched against the bare in-manifest ids via the
    same ``default:`` prefix-strip used at the compose boundary.
    """
    if not marshal_step_map:
        return dict.fromkeys(final_step_ids)
    # Index the marshal map by its prefix-stripped key so a bare in-manifest id
    # matches a ``default:``-prefixed marshal key.
    bare_to_params: dict[str, dict] = {
        _strip_default_prefix(key): params for key, params in marshal_step_map.items()
    }
    # A param-owning step snapshots its nested object; an ownerless step (no
    # marshal entry or an empty param object) snapshots as ``None`` so the
    # manifest carries no empty ``{}``.
    return {
        step_id: (dict(params) if (params := bare_to_params.get(step_id)) else None)
        for step_id in final_step_ids
    }


def _apply_commit_push_disabled(phase_6_candidates: list[str], commit_and_push: bool) -> tuple[list[str], bool]:
    """Pre-filter: drop ``push`` when ``commit_and_push is False``.

    Also drops ``pre-push-quality-gate`` and ``pre-submission-self-review``
    because both gates are only meaningful when a downstream push exists.
    Returns the filtered list plus a flag indicating whether the pre-filter
    fired.
    """
    if commit_and_push:
        return phase_6_candidates, False
    fired = False
    filtered: list[str] = []
    for step in phase_6_candidates:
        if step in {'push', 'pre-push-quality-gate', 'pre-submission-self-review'}:
            fired = True
            continue
        filtered.append(step)
    return filtered, fired


# Footprint roles that gate a whole-tree canonical-verify step. Each canonical
# whose derived matrix role appears here is footprint-gated: when the live
# footprint is non-empty AND carries no path of the gating role, the
# corresponding ``default:verify:{canonical}`` step is dropped from the
# composed phase-5 list. This is the generic, canonical-agnostic
# footprint pre-filter — it adds no per-canonical branch, only a role→suffix
# membership test. ``integration`` / ``e2e`` are the gateable roles because a
# project with no integration/e2e sources never needs those whole-tree gates;
# the core ``quality-gate`` / ``module-tests`` / ``coverage`` roles are NEVER
# footprint-gated (they always run when present).
_FOOTPRINT_GATED_CANONICAL_ROLES: dict[str, tuple[str, ...]] = {
    'integration': ('it.java', 'integrationtest', 'integration_test', 'test_integration', '_it.py'),
    'e2e': ('e2e', 'endtoend', 'end_to_end'),
}


def _footprint_has_role(footprint: list[str], suffix_markers: tuple[str, ...]) -> bool:
    """Return True when any footprint path's lowercased name contains a marker.

    The match is a generic substring test against the path's basename and the
    full path (lowercased), so it is build-system agnostic — it never imports a
    build extension or reads ``build.map``. A canonical whose gating role has at
    least one matching path is kept; one with zero matches is dropped only when
    the footprint is otherwise non-empty.
    """
    for path in footprint:
        low = path.lower()
        if any(marker in low for marker in suffix_markers):
            return True
    return False


# Request aspects (from the ``manage-config aspect-classify`` verb) that drop
# build / quality-gate / test steps from the composed phase-5 manifest. An
# ``analysis`` or ``planning`` request produces no production / test footprint,
# so the build/verify gates have nothing to gate; dropping them keeps phase-5
# from running (and failing) build/quality-gate/test commands against a
# code-free change. ``implementation`` (the safe classifier fallback below the
# ``>= 0.7`` threshold) is NOT in this set — it retains every gate. See the
# aspect-classify threshold contract in
# ``manage-config/scripts/_cmd_aspect_classify.py`` and the outline's
# request-aspect classification deliverable.
_BUILD_DROPPING_ASPECTS = frozenset({'analysis', 'planning'})

def _apply_aspect_step_dropping(
    phase_5_steps: list[str],
    aspect: str | None,
    role_cache: dict[str, str | None],
) -> tuple[list[str], list[str]]:
    """Clear the phase-5 verification list when the request aspect is analysis / planning.

    When ``aspect ∈ {analysis, planning}`` (the build-dropping aspects), the
    ENTIRE phase-5 verification list is dropped — not just the canonical
    build/verify steps (``quality-gate`` / ``module-tests`` / ``coverage``) but
    also every external (``project:`` / ``bundle:skill``) step whose derived
    matrix role is ``None``. Analysis / planning requests carry no production /
    test footprint, so the build/verify gates have nothing to gate.

    Dropping the full list (rather than only the role-matched build steps) is
    load-bearing for the phase-5-execute Step 11b contract: Step 11b fires a
    ``quality-gate`` sweep whenever ``phase_5.verification_steps`` is non-empty.
    A role-only filter that left any external ``None``-role step in the list
    would keep it non-empty and re-trigger ``quality-gate`` via Step 11b for an
    analysis / planning request — exactly the build the aspect drop exists to
    prevent. Clearing the full list keeps the enforcement at the manifest layer
    where it belongs, so Step 11b's non-empty check naturally short-circuits.

    An ``implementation`` aspect (the classifier's safe sub-threshold fallback)
    and an absent aspect are no-ops: every gate is retained.

    Returns ``(kept_steps, dropped_steps)``. ``role_cache`` is retained in the
    signature for call-site symmetry with the other role-driven filters; the
    full-clear path does not consult it.
    """
    if aspect not in _BUILD_DROPPING_ASPECTS:
        return phase_5_steps, []

    # Build-dropping aspect: drop the FULL list (every step, build and external
    # alike). See docstring — a partial role-only drop would leave external
    # None-role steps in place and re-trigger Step 11b's quality-gate sweep.
    return [], list(phase_5_steps)


# Code-touching change types that gate ``finalize-step-simplify`` activation.
# Branch-prefix reconciliation: ``fix`` → ``bug_fix``, ``chore`` → ``tech_debt``,
# ``feature`` → ``feature``. ``analysis`` / ``enhancement`` / ``verification`` are
# excluded. See standards/decision-rules.md § Pre-Filter: simplify_inactive.
_SIMPLIFY_CHANGE_TYPES = frozenset({'feature', 'bug_fix', 'tech_debt'})


def _apply_code_step_inactive(
    phase_6_candidates: list[str],
    step_name: str,
    change_type: str,
    affected_files_count: int,
) -> tuple[list[str], bool]:
    """Pre-filter: drop a code-gated phase-6 step when its activation gate fails.

    Shared gate for ``finalize-step-simplify`` and ``finalize-step-security-audit``.
    Both steps activate when BOTH:

    1. ``change_type ∈ {feature, bug_fix, tech_debt}`` — the three code-touching
       change types; and
    2. ``affected_files_count > 0``.

    When either condition fails, ``step_name`` is removed from
    ``phase_6_candidates``. The pre-filter is a no-op when ``step_name`` is
    already absent from the candidate set. Returns the filtered list plus a flag
    indicating whether the pre-filter fired (i.e., the step was active in the
    input but dropped after the check).
    """
    if step_name not in phase_6_candidates:
        return phase_6_candidates, False

    if change_type in _SIMPLIFY_CHANGE_TYPES and affected_files_count > 0:
        # Gate passes — keep the step.
        return phase_6_candidates, False

    return [s for s in phase_6_candidates if s != step_name], True


def _apply_simplify_inactive(
    phase_6_candidates: list[str],
    change_type: str,
    affected_files_count: int,
) -> tuple[list[str], bool]:
    """Pre-filter: drop ``finalize-step-simplify`` when its activation gate fails."""
    return _apply_code_step_inactive(phase_6_candidates, 'finalize-step-simplify', change_type, affected_files_count)


def _apply_security_audit_inactive(
    phase_6_candidates: list[str],
    change_type: str,
    affected_files_count: int,
) -> tuple[list[str], bool]:
    """Pre-filter: drop ``finalize-step-security-audit`` when its activation gate fails."""
    return _apply_code_step_inactive(phase_6_candidates, 'finalize-step-security-audit', change_type, affected_files_count)


# Scope-gated phase-6 subtraction sets. Each entry lists the step references the
# scope_gated_finalize pre-filter drops, expressed as match-sets that cover both
# the bare and prefixed forms a candidate list may carry. The candidate list is
# boundary-normalized by ``_strip_default_prefix`` before pre-filters run, so the
# optional ``default:`` prefix is already gone; ``project:`` and ``bundle:skill``
# prefixes are preserved verbatim, so the surgical set lists both forms. See
# standards/decision-rules.md § Pre-Filter: scope_gated_finalize.
#
# ``automatic-review`` is deliberately NOT in either implicit set: its presence
# is governed purely by its configured ``lane`` (seeded ``ask`` → resolved by
# marshall-steward) and lane tier, so the implicit scope gate must not drop it.
# The only path that suppresses ``automatic-review`` is the explicit
# ``drop_review_on_scope_gate`` opt-in (see ``_apply_scope_gated_finalize``).
_SCOPE_GATED_SURGICAL_DROP = frozenset(
    {
        'plan-retrospective',
        'plan-marshall:plan-retrospective',
        'pre-submission-self-review',
        'finalize-step-plugin-doctor',
        'project:finalize-step-plugin-doctor',
    }
)
_SCOPE_GATED_SINGLE_MODULE_DROP = frozenset(
    {
        'plan-retrospective',
        'plan-marshall:plan-retrospective',
    }
)
_SCOPE_GATED_OVERRIDE_DROP = frozenset({'automatic-review', 'plan-marshall:automatic-review'})


# Owning finalize step ids for the four ceremony gates and the escape-hatch knob.
# Each ceremony gate is governed by its owning step's per-element ``lane`` override
# (``off``/``minimal``/``auto``) stored nested under the owning step's param object
# in marshal.json's ``phase-6-finalize.steps`` keyed map. There is no flat
# phase-level ``qgate`` sibling — every ceremony gate rides its owning step's
# ``lane``. ``drop_review_on_scope_gate`` remains a step-owned escape hatch under
# the self-review step.
_QGATE_OWNER_STEP = 'default:pre-push-quality-gate'
_SIMPLIFY_OWNER_STEP = 'default:finalize-step-simplify'
_SECURITY_AUDIT_OWNER_STEP = 'default:finalize-step-security-audit'
_PRE_SUBMISSION_SELF_REVIEW_STEP = 'default:pre-submission-self-review'


def _read_step_owned_knob(owner_step_id: str, knob: str) -> object | None:
    """Read a step-owned knob from ``phase-6-finalize.steps`` in marshal.json.

    The step-owned knobs (each ceremony gate's ``lane`` override, plus the
    ``drop_review_on_scope_gate`` escape hatch) live nested under their owning
    finalize step's param object in the ``phase-6-finalize.steps`` keyed map. This
    reads ``steps[owner_step_id][knob]`` via :func:`_read_marshal_phase_step_map`
    (which
    preserves the full ``default:`` / ``project:`` step-id prefixes), returning
    ``None`` when the marshal file is missing, the owning step is absent from the
    map, or the knob is absent from the step's param object. The caller supplies
    the canonical default for the ``None`` case.

    Args:
        owner_step_id: The full-prefixed finalize step id that owns the knob.
        knob: The param key to read from the owning step's nested param object.

    Returns:
        The knob's value, or ``None`` when it cannot be resolved.
    """
    step_map = _read_marshal_phase_step_map('phase-6-finalize')
    if not step_map:
        return None
    params = step_map.get(owner_step_id)
    if not isinstance(params, dict):
        return None
    return params.get(knob)


def _read_drop_review_on_scope_gate() -> bool:
    """Read ``drop_review_on_scope_gate`` from its owning finalize step's params.

    The knob is folded under
    ``phase-6-finalize.steps['default:pre-submission-self-review']
    .drop_review_on_scope_gate`` in marshal.json (its former flat-sibling
    location is gone). Returns ``False`` when the file is missing, the owning step
    is absent, the knob is absent, or the value is not a boolean ``True``. The
    escape hatch defaults to off: only an explicit ``true`` activates the
    additional ``automatic-review`` suppression in the scope_gated_finalize
    pre-filter.
    """
    return _read_step_owned_knob(_PRE_SUBMISSION_SELF_REVIEW_STEP, 'drop_review_on_scope_gate') is True


def _apply_scope_gated_finalize(
    phase_6_candidates: list[str],
    scope_estimate: str,
    drop_review_on_scope_gate: bool,
) -> tuple[list[str], list[str]]:
    """Pre-filter: drop heavyweight phase-6 review/audit steps by scope.

    Subtractions:

    - ``scope_estimate == 'surgical'`` → drop ``plan-marshall:plan-retrospective``,
      ``pre-submission-self-review``, and ``finalize-step-plugin-doctor`` (every
      bare and prefixed form — including the generic ``default:`` /
      meta-project ``project:`` variants).
    - ``scope_estimate == 'single_module'`` → drop only
      ``plan-marshall:plan-retrospective``.
    - Any other scope value → no implicit subtraction.

    ``automatic-review`` is NEVER subtracted by the implicit scope gate — its
    presence is governed purely by its configured ``lane`` and lane tier, so the
    implicit scope gate must not drop it.
    When ``drop_review_on_scope_gate`` is ``True`` AND the plan is itself
    scope-gated (``scope_estimate in ('surgical', 'single_module')``), the gate
    additionally drops ``automatic-review`` — the only path that suppresses the
    bot-review gate, explicitly opted into via marshal.json. The override is
    scoped, not global: on non-scope-gated plans (``multi_module`` / ``broad`` /
    ``none``) the override is inert, so flipping the project-wide knob can never
    silently disable bot review on a large plan.

    Consistent with the composer's "rows and pre-filters only ever narrow the
    candidate list" architecture, this pre-filter runs before the seven-row
    matrix. Returns the filtered candidate list
    plus the list of step references that were dropped (for per-subtraction
    decision-log emission). The dropped list preserves the candidate's verbatim
    form so the decision log names exactly what was removed.
    """
    if scope_estimate == 'surgical':
        drop_set: frozenset[str] = _SCOPE_GATED_SURGICAL_DROP
    elif scope_estimate == 'single_module':
        drop_set = _SCOPE_GATED_SINGLE_MODULE_DROP
    else:
        drop_set = frozenset()

    if drop_review_on_scope_gate and scope_estimate in ('surgical', 'single_module'):
        drop_set = drop_set | _SCOPE_GATED_OVERRIDE_DROP

    if not drop_set:
        return phase_6_candidates, []

    kept: list[str] = []
    dropped: list[str] = []
    for step in phase_6_candidates:
        if step in drop_set:
            dropped.append(step)
        else:
            kept.append(step)
    return kept, dropped


# Gate → (match-set, canonical insertion form). The match-set covers every
# prefixed/bare form a candidate list may carry; the insertion form is the
# canonical identifier `always` re-adds when the step is absent.
_CEREMONY_FINALIZE_STEP_MAP: dict[str, tuple[frozenset[str], str]] = {
    'self_review': (
        frozenset(
            {
                'pre-submission-self-review',
                'default:pre-submission-self-review',
            }
        ),
        'default:pre-submission-self-review',
    ),
    'qgate': (
        frozenset({'pre-push-quality-gate'}),
        'pre-push-quality-gate',
    ),
    'simplify': (
        frozenset({'finalize-step-simplify'}),
        'finalize-step-simplify',
    ),
    'security_audit': (
        frozenset({'finalize-step-security-audit'}),
        'finalize-step-security-audit',
    ),
}

# The four finalize ceremony gates, in canonical order.
_CEREMONY_FINALIZE_GATES = ('self_review', 'qgate', 'simplify', 'security_audit')

# Canonical default for every finalize gate when marshal.json omits the block.
_CEREMONY_FINALIZE_DEFAULT = 'auto'

# Owning finalize step id for each ceremony gate's ``lane`` override. The gate's
# effective run-at-all decision is derived from its owning step's per-element
# ``lane`` value in ``phase-6-finalize.steps`` — there is no flat phase-level
# ``qgate`` sibling anymore.
_CEREMONY_GATE_OWNER_STEP: dict[str, str] = {
    'qgate': _QGATE_OWNER_STEP,
    'self_review': _PRE_SUBMISSION_SELF_REVIEW_STEP,
    'simplify': _SIMPLIFY_OWNER_STEP,
    'security_audit': _SECURITY_AUDIT_OWNER_STEP,
}

# Per-element ``lane`` override → ceremony run-at-all decision. ``off`` forces the
# ceremony step out (``never``); ``minimal`` force-keeps it in (``always``);
# every other value (``auto`` / ``full`` / ``ask`` / absent / malformed) defers
# to the pre-filter machinery (``auto``).
_LANE_TO_CEREMONY_VALUE: dict[str, str] = {
    'off': 'never',
    'minimal': 'always',
}


def _read_finalize_gates() -> dict[str, str]:
    """Resolve the four finalize ceremony gate values from the ``lane`` channel.

    Each of the four ceremony gates (``qgate`` / ``self_review`` / ``simplify`` /
    ``security_audit``) is governed by its owning finalize step's per-element
    ``lane`` override (``steps[<owner>].lane``) in ``phase-6-finalize.steps``,
    read via :func:`_read_step_owned_knob`. The owning steps are:

    - ``qgate`` → ``default:pre-push-quality-gate``
    - ``self_review`` → ``default:pre-submission-self-review``
    - ``simplify`` → ``default:finalize-step-simplify``
    - ``security_audit`` → ``default:finalize-step-security-audit``

    The ``lane`` value maps to the run-at-all decision the ceremony transform
    consumes: ``off`` → ``never`` (force out), ``minimal`` → ``always`` (force
    in), and every other value (``auto`` / ``full`` / ``ask`` / absent) → ``auto``
    (defer to the pre-filter machinery).

    Returns a ``{gate: value}`` dict for the four finalize gates; values are one
    of ``always`` / ``never`` / ``auto``. The caller treats any value other than
    ``always`` / ``never`` as defer.
    """
    resolved: dict[str, str] = dict.fromkeys(_CEREMONY_FINALIZE_GATES, _CEREMONY_FINALIZE_DEFAULT)

    for gate in _CEREMONY_FINALIZE_GATES:
        owner_step = _CEREMONY_GATE_OWNER_STEP[gate]
        lane_value = _read_step_owned_knob(owner_step, 'lane')
        if isinstance(lane_value, str) and lane_value in _LANE_TO_CEREMONY_VALUE:
            resolved[gate] = _LANE_TO_CEREMONY_VALUE[lane_value]

    return resolved


def _ceremony_finalize_insert_index(phase_6_steps: list[str]) -> int:
    """Resolve the insertion position for an ``always``-forced finalize step.

    A ceremony finalize step must run before the plan-mutating tail
    (``archive-plan`` / ``record-metrics`` / ``branch-cleanup`` /
    ``plan-marshall:plan-retrospective``) so the gate is honoured before the
    plan directory is moved or the branch cleaned up. Returns the index of the
    first plan-mutating step, or the end of the list when no anchor is present.
    """
    plan_mutating = {
        'archive-plan',
        'record-metrics',
        'branch-cleanup',
        'plan-marshall:plan-retrospective',
    }
    for index, step in enumerate(phase_6_steps):
        if step in plan_mutating:
            return index
    return len(phase_6_steps)


def _apply_ceremony_finalize_selection(
    phase_6_steps: list[str],
    gates: dict[str, str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Force ceremony finalize gates in (``always``) / out (``never``) in-place.

    For each of the three finalize gates:

    - ``never`` → drop every match-set form of the gate's step from
      ``phase_6_steps`` (a no-op when already absent).
    - ``always`` → ensure the gate's canonical step is present, inserting it
      before the plan-mutating tail when absent (a no-op when any match-set form
      is already present).
    - any other value (``auto`` / malformed) → defer (no-op).

    ``automatic-review`` is NEVER touched — the gate map contains only the three
    ceremony finalize steps, so the bot-review invariant is structurally
    preserved.

    Mutates ``phase_6_steps`` in place. Returns ``(forced_in, forced_out)`` —
    two lists of ``{'gate': ..., 'step': ...}`` dicts naming each gate that
    actually changed the list, for per-change decision-log emission.
    """
    forced_in: list[dict[str, str]] = []
    forced_out: list[dict[str, str]] = []

    for gate in _CEREMONY_FINALIZE_GATES:
        value = gates.get(gate, _CEREMONY_FINALIZE_DEFAULT)
        match_set, canonical = _CEREMONY_FINALIZE_STEP_MAP[gate]

        if value == 'never':
            present = [s for s in phase_6_steps if s in match_set]
            if present:
                phase_6_steps[:] = [s for s in phase_6_steps if s not in match_set]
                forced_out.append({'gate': gate, 'step': present[0]})
        elif value == 'always':
            if not any(s in match_set for s in phase_6_steps):
                insert_index = _ceremony_finalize_insert_index(phase_6_steps)
                phase_6_steps.insert(insert_index, canonical)
                forced_in.append({'gate': gate, 'step': canonical})
        # else: defer (auto / malformed) — no-op.

    return forced_in, forced_out


def _read_ci_provider() -> str | None:
    """Return the CI provider identifier (``github``, ``gitlab``) from marshal.json.

    The provider is resolved from the ``providers[]`` entry where
    ``category == 'ci'``, mapping skill name to a short identifier:

    * ``plan-marshall:workflow-integration-github`` -> ``github``
    * ``plan-marshall:workflow-integration-gitlab`` -> ``gitlab``

    Returns ``None`` when the marshal file is missing, no CI provider is
    declared, or the resolved value is neither ``github`` nor ``gitlab``.
    """
    marshal_path = get_marshal_path()
    if marshal_path is None or not marshal_path.is_file():
        return None
    try:
        data = read_json(marshal_path)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    providers = data.get('providers')
    if not isinstance(providers, list):
        return None
    for entry in providers:
        if not isinstance(entry, dict):
            continue
        if entry.get('category') != 'ci':
            continue
        skill_name = entry.get('skill_name', '')
        if not isinstance(skill_name, str):
            continue
        if skill_name == 'plan-marshall:workflow-integration-github':
            return 'github'
        if skill_name == 'plan-marshall:workflow-integration-gitlab':
            return 'gitlab'
    return None


def _read_sonar_provider() -> str | None:
    """Return the Sonar provider identifier (``sonar``) from marshal.json.

    Sibling of :func:`_read_ci_provider`. The provider is resolved from the
    ``providers[]`` entry whose ``skill_name`` is
    ``plan-marshall:workflow-integration-sonar``. Unlike the CI reader (which
    keys on ``category == 'ci'`` to disambiguate github/gitlab), a Sonar
    integration is identified solely by its skill, so this matches on
    ``skill_name`` directly and returns the single short identifier ``sonar``.

    Returns ``None`` when the marshal file is missing, no Sonar provider is
    declared, or the providers list is absent/malformed. The D6 compose-time
    ``_apply_unresolved_ask_provider_drop`` pre-filter consumes this — a
    non-``None`` result means "Sonar is configured", so an unresolved
    ``lane:ask`` ``sonar-roundtrip`` element is kept rather than dropped.
    """
    marshal_path = get_marshal_path()
    if marshal_path is None or not marshal_path.is_file():
        return None
    try:
        data = read_json(marshal_path)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    providers = data.get('providers')
    if not isinstance(providers, list):
        return None
    for entry in providers:
        if not isinstance(entry, dict):
            continue
        if entry.get('skill_name') == 'plan-marshall:workflow-integration-sonar':
            return 'sonar'
    return None


# The two infra-dependent adversarial finalize elements governed by a seeded
# ``lane: ask`` override. Each maps to the match-set of every prefixed/bare form
# a (boundary-normalized) candidate list may carry. The candidate list is
# ``default:``-stripped at the compose boundary, so ``default:sonar-roundtrip``
# reads back as bare ``sonar-roundtrip``; ``plan-marshall:automatic-review``
# keeps its bundle prefix. Both forms are listed so the match is robust.
_ASK_PROVIDER_INFRA_ELEMENTS: dict[str, frozenset[str]] = {
    'automatic-review': frozenset({'automatic-review', 'plan-marshall:automatic-review'}),
    'sonar-roundtrip': frozenset({'sonar-roundtrip', 'default:sonar-roundtrip'}),
}


def _apply_unresolved_ask_provider_drop(
    phase_6_candidates: list[str],
    marshal_phase_6_map: dict[str, dict] | None,
    ci_provider: str | None,
    sonar_provider: str | None,
) -> tuple[list[str], list[str]]:
    """Pre-filter (D6): drop an UNRESOLVED ``lane:ask`` infra element when its provider is absent.

    For each of the two infra-dependent adversarial elements
    (``automatic-review``, ``sonar-roundtrip``) present in the candidate list,
    resolve its EFFECTIVE lane tier from the marshal.json per-element ``lane``
    override via :func:`_effective_lane_tier`. The seed value for both elements
    is ``ask``, and a steward-persisted answer overwrites it to
    ``off``/``auto``/``full``; so an effective tier still equal to ``ask`` at
    compose is the UNRESOLVED case (the operator never answered). When the
    element is unresolved AND its corresponding provider is absent
    (``ci_provider is None`` for ``automatic-review``; ``sonar_provider is
    None`` for ``sonar-roundtrip``), the element is DROPPED.

    Never drops a RESOLVED ask (effective tier ``off``/``auto``/``full`` — the
    ``off`` case is already handled by the lane-resolution pass; a resolved
    ``auto``/``full`` keeps the element here). Never drops when the provider IS
    configured. Elements other than the two infra elements pass through
    untouched. Consistent with the composer's "rows and pre-filters only ever
    narrow" architecture, this only removes candidates — it never re-adds.

    Returns ``(kept, dropped)``; ``dropped`` preserves each candidate's verbatim
    form for per-drop decision-log emission.
    """
    provider_for: dict[str, str | None] = {
        'automatic-review': ci_provider,
        'sonar-roundtrip': sonar_provider,
    }
    kept: list[str] = []
    dropped: list[str] = []
    for step in phase_6_candidates:
        drop = False
        for element_key, match_set in _ASK_PROVIDER_INFRA_ELEMENTS.items():
            if step in match_set:
                # ``_lane_override_for`` normalizes the marshal map KEY (so a
                # promoted ``plan-marshall:automatic-review`` key strips to bare
                # ``automatic-review``) but compares it against the step_id
                # verbatim. This pre-filter runs at the candidate-narrowing
                # stage, where a promoted infra candidate is still carried in its
                # prefixed ``plan-marshall:automatic-review`` form, so the step
                # must be boundary-normalized to the same bare shape before the
                # lookup — otherwise the prefixed key strips to bare and never
                # matches the prefixed step_id (the drop silently never fires).
                override = _lane_override_for(_strip_default_prefix(step), marshal_phase_6_map)
                effective, _is_off = _effective_lane_tier({}, override)
                if effective == 'ask' and provider_for[element_key] is None:
                    drop = True
                break
        (dropped if drop else kept).append(step)
    return kept, dropped


# Build verb → phase-5 step ID mapping. The four canonical verbs are the
# ones registered by every build skill's ``_CONFIG`` (verify / quality-gate /
# coverage / module-tests). Verbs not in this map are left to the consumer
# (the composer skips routing for unmapped verbs, preserving today's
# behaviour).
#
# The step IDs are BARE (no ``default:`` prefix) per the boundary-
# normalization contract: the candidate lists are stripped to bare names at
# the compose boundary (``_strip_default_prefix``), and ``phase_5.verification
# _steps`` is built from those bare names. Each routed step ID is the bare
# canonical-verify form ``verify:{canonical}`` (the post-strip shape of
# ``default:verify:{canonical}``); both ``verify`` and ``module-tests`` route to
# ``verify:module-tests`` (the canonical-verify step whose derived role is
# ``module-tests``). Emitting a ``default:``-prefixed ID here would append a
# duplicate prefixed form alongside the bare form the matrix already produced,
# and the prefixed stray would then fail the prefix-strict validate gate.
# Keeping the routed step IDs bare matches the rest of the phase-5 list.
_VERB_TO_PHASE_5_STEP: dict[str, str] = {
    'quality-gate': 'verify:quality-gate',
    'verify': 'verify:module-tests',
    'module-tests': 'verify:module-tests',
    'coverage': 'verify:coverage',
}


def _parse_verification_command(cmd: str) -> tuple[str, str] | None:
    """Extract ``(verb, command_args)`` from a Bucket B build verification command.

    Accepts the canonical shape::

        python3 .plan/execute-script.py {build_notation} run --command-args "{args}"

    where ``{args}`` typically reads as ``"<verb> [module]"`` (e.g.
    ``"verify plan-marshall"``). Returns ``(verb, command_args)`` on a
    successful parse, ``None`` for any non-build invocation (raw shell,
    grep, Bucket A ``manage-*`` notations, malformed quoting, etc.). The
    verb is always the first whitespace-separated token of ``command_args``.

    The parse is intentionally permissive on the trailing module/profile
    arguments — only ``verb`` is needed to map to a phase-5 step ID; the
    ``command_args`` payload is forwarded verbatim to ``architecture
    resolve`` when the composer subprocesses it.
    """
    if not cmd:
        return None
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        return None
    # Locate the executor token (allow ``python3`` / ``python`` prefix variations).
    script_index: int | None = None
    for i, tok in enumerate(tokens):
        if tok.endswith('.plan/execute-script.py') or tok.endswith('execute-script.py'):
            script_index = i
            break
    if script_index is None:
        return None
    # Notation immediately follows the script path; the four Bucket B build
    # notations are the only ones that emit execution_tier fields on resolve.
    notation_index = script_index + 1
    if notation_index >= len(tokens):
        return None
    notation = tokens[notation_index]
    if not notation.startswith('plan-marshall:build-'):
        return None
    # Subcommand ``run``.
    sub_index = notation_index + 1
    if sub_index >= len(tokens) or tokens[sub_index] != 'run':
        return None
    # ``--command-args`` (accept ``--command-args VAL`` and ``--command-args=VAL``).
    command_args: str | None = None
    i = sub_index + 1
    while i < len(tokens):
        tok = tokens[i]
        if tok == '--command-args':
            if i + 1 < len(tokens):
                command_args = tokens[i + 1]
            break
        if tok.startswith('--command-args='):
            command_args = tok[len('--command-args=') :]
            break
        i += 1
    if command_args is None or not command_args.strip():
        return None
    verb = command_args.strip().split()[0]
    return verb, command_args


def _verb_to_phase_5_step(verb: str) -> str | None:
    """Return the phase-5 step ID for a build verb, or ``None`` when unmapped."""
    return _VERB_TO_PHASE_5_STEP.get(verb)
