#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic planning-lane router for phase-1-init.

Computes ``planning_lane ∈ {light, deep}`` from cheap field reads + a
``request.md`` regex, with ZERO codebase discovery and ZERO LLM cognition.
The default is ``light``; any deep-precondition signal forces ``deep``;
escalation is one-way (light may ratchet to deep, never deep→light).

The signal set (DQ1 of the planning-lanes solution outline):

| # | Signal | Source (cheap read) | → deep when |
|---|--------|---------------------|-------------|
| S1 | ``plan_source`` | ``status.metadata.plan_source`` | free-form (absent/unset) **AND** S5 concreteness fails |
| S2 | ``scope_estimate`` | ``references.scope_estimate`` | ∈ {multi_module, broad, none, unset} |
| S3 | ``change_type`` | ``status.metadata.change_type`` | ∈ {feature, feature_breaking} **AND NOT** narrow-and-concrete |
| S4 | ``compatibility`` | ``marshal.json plan.phase-2-refine.compatibility`` | == breaking **AND NOT** narrow-and-concrete |
| S5 | request concreteness | regex over ``request.md`` body | NO file path AND NO concrete fix signal |
| S6 | explicit override | ``status.metadata.planning_lane_override`` | == deep forces deep (one-way) |

``deep`` IFF (S1 ∨ S2 ∨ S3 ∨ S4 ∨ S5 ∨ S6-deep); otherwise ``light``.

The narrow-and-concrete carve-out: when ``scope_estimate ∈ {surgical,
single_module}`` AND the request is concrete, S3 (generative change_type) and S4
(breaking compatibility) are suppressed so they cannot force ``deep`` *alone* for
a positively-bounded, well-specified request. The carve-out relaxes ONLY this
co-firing — S1/S2/S5 (the unknown-to-deep defaults) and S6 (explicit override)
still bias ``deep`` unchanged, so the conservative unknown case is untouched.

``plan.phase-1-init.deep_lane`` is read BEFORE the signal set and
short-circuits the evaluation: ``always`` forces deep, ``never`` forces light
(the DQ3 hard-escalation ratchet still fires unless ``plan.phase-1-init.escalation``
is also ``never``), ``auto`` (the default) defers to the signals.

The router also projects a RECOMMENDED execution-profile posture
(``minimal`` / ``auto`` / ``full``) over the SAME signals via
``project_profile_pure``. The projection is a pure derivation that adds no
discovery and no cognition; it is independent of the ``deep_lane`` ceremony gate
(``deep_lane=always`` governs planning depth, NOT the profile — see
``extension-api/standards/ext-point-lane-element.md`` for the lane contract). On
``--persist`` the route command writes the projected posture into
``status.metadata.execution_profile`` as the init-time default; the phase-1-init
posture dialogue may override it via ``manage-status metadata``.
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

from _cmd_classification_validate import run_classification_validation
from _plan_parsing import parse_document_sections
from _status_core import read_status, write_status
from constants import FILE_MARSHAL
from file_ops import base_path, get_plan_dir, read_json, write_json
from plan_logging import log_entry

LIGHT = 'light'
DEEP = 'deep'

# Execution-profile postures (the lane lattice minimal ⊏ auto ⊏ full). The
# planning-lane router projects a RECOMMENDED posture over the same signals it
# already scores for the {light, deep} verdict; the projection is independent of
# the deep_lane ceremony gate (deep_lane governs planning DEPTH, not the profile
# — see ext-point-lane-element.md and §4.2 of the lane-selection outline).
MINIMAL = 'minimal'
AUTO = 'auto'
FULL = 'full'

# Scope bands that read as broad-surface for the profile projection (a superset
# trigger toward keeping full ceremony when combined with a generative change).
_BROAD_SCOPE_ESTIMATES = frozenset({'multi_module', 'broad'})
# Scope bands that read as narrow/localized for the minimal recommendation.
_NARROW_SCOPE_ESTIMATES = frozenset({'surgical', 'single_module'})

# S2 — scope_estimate values that bias deep (broad-surface / unknown bands).
# surgical / single_module bias light.
_DEEP_SCOPE_ESTIMATES = frozenset({'multi_module', 'broad', 'none'})

# S3 — change_type values that bias deep (generative, broad-surface).
# bug_fix / tech_debt / enhancement / verification bias light.
_DEEP_CHANGE_TYPES = frozenset({'feature', 'feature_breaking'})

# S5 — request-concreteness regexes.
# A file-path anchor: a repo-relative path with a directory separator and an
# extension (e.g. ``marketplace/.../foo.py``, ``test/x/test_y.py``).
_PATH_RE = re.compile(r'[\w./-]+/[\w.-]+\.[A-Za-z0-9]+')
# A concrete fix signal: a fenced code block, a ``python3 .plan/execute-script.py``
# CLI invocation, or an inline ``manage-*`` notation.
_FENCE_RE = re.compile(r'```')
_CLI_RE = re.compile(r'python3\s+\.plan/execute-script\.py')
_NOTATION_RE = re.compile(r'\bmanage-[a-z-]+\b')


def _distinct_paths(body: str) -> set[str]:
    """Return the DISTINCT repo-relative file paths ``_PATH_RE`` extracts from ``body``.

    The single source of the distinct-path extraction shared by
    ``scope_estimate_from_request_pure`` and ``cmd_scope_estimate_heuristic``.
    Callers guard the empty-``body`` case themselves and layer their own
    downstream ``sorted()`` / ``len()`` on the returned set.
    """
    return {m.group(0) for m in _PATH_RE.finditer(body)}


# --- Pre-route scope_estimate heuristic --------------------------------------
# Coarse scope bands the pre-route heuristic emits (the two narrow bands the
# light lane cares about). This is a pre-route GUESS from cheap request signals,
# never the authoritative scope — the deep-lane refine Step 9 module-mapping
# derivation overwrites it with the accurate band (multi_module / broad) when
# the deep lane runs.
SURGICAL = 'surgical'
SINGLE_MODULE = 'single_module'
# At most this many distinct file-path references still reads as a surgical,
# tightly-bounded change.
_SURGICAL_MAX_PATHS = 3
# A glob / pattern fan-out marker (``**``, ``/*``, ``*/``, ``*.ext``) disqualifies
# the surgical band even with few explicit paths — a pattern implies fan-out
# across an unbounded file set.
_GLOB_RE = re.compile(r'\*\*|/\*|\*/|\*\.[A-Za-z0-9]+')


def _read_request_body(plan_id: str) -> str:
    """Return the clarified-request (or original-input fallback) narrative.

    Returns the empty string when ``request.md`` is missing or carries neither
    section — the S5 concreteness check then fails (no anchors), biasing deep,
    which is the documented deep-default for an unknown request body.
    """
    request_path = get_plan_dir(plan_id) / 'request.md'
    if not request_path.exists():
        return ''
    try:
        content = request_path.read_text(encoding='utf-8')
    except OSError:
        return ''
    sections = parse_document_sections(content)
    for candidate in ('clarified_request', 'original_input'):
        body = sections.get(candidate)
        if isinstance(body, str) and body.strip():
            return body
    return ''


def _request_is_concrete(body: str) -> bool:
    """S5 — the request names an existing file path OR a concrete fix signal.

    Concrete (returns True) when the body contains a file-path anchor OR a
    fenced code block / CLI invocation / ``manage-*`` notation. A vague ask
    with no anchors returns False (→ deep).
    """
    if not body:
        return False
    if _PATH_RE.search(body):
        return True
    if _FENCE_RE.search(body):
        return True
    if _CLI_RE.search(body):
        return True
    if _NOTATION_RE.search(body):
        return True
    return False


def _read_scope_estimate(plan_id: str) -> str | None:
    """S2 — read ``scope_estimate`` from references.json (None when absent)."""
    try:
        references = read_json(get_plan_dir(plan_id) / 'references.json', default={})
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(references, dict):
        value = references.get('scope_estimate')
        if isinstance(value, str):
            return value
    return None


def _read_compatibility() -> str | None:
    """S4 — read ``plan.phase-2-refine.compatibility`` from marshal.json."""
    try:
        config = read_json(base_path(FILE_MARSHAL), default={})
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(config, dict):
        plan_block = config.get('plan', {})
        if isinstance(plan_block, dict):
            refine = plan_block.get('phase-2-refine', {})
            if isinstance(refine, dict):
                value = refine.get('compatibility')
                if isinstance(value, str):
                    return value
    return None


def _read_deep_lane_gate() -> str:
    """Read ``plan.phase-1-init.deep_lane`` (``auto`` when absent)."""
    try:
        config = read_json(base_path(FILE_MARSHAL), default={})
    except (OSError, json.JSONDecodeError):
        return 'auto'
    if isinstance(config, dict):
        plan_block = config.get('plan', {})
        if isinstance(plan_block, dict):
            init = plan_block.get('phase-1-init', {})
            if isinstance(init, dict):
                value = init.get('deep_lane')
                if value in ('auto', 'always', 'never'):
                    return str(value)
    return 'auto'


def scope_estimate_from_request_pure(body: str | None) -> str:
    """Classify a coarse ``scope_estimate`` from the request body — pure, I/O-free.

    Counts the DISTINCT repo-relative file-path references ``_PATH_RE`` extracts
    from the body and classifies with ZERO architecture queries (the same
    zero-discovery invariant the lane router itself preserves):

    - ``surgical`` — between one and three distinct file paths AND no glob /
      pattern fan-out marker (``**``, ``/*``, ``*.ext``). A tightly-bounded,
      explicitly-named change.
    - ``single_module`` — everything else: no explicit path (an ambiguous ask), a
      glob/pattern present (unbounded fan-out), or more than three distinct
      paths. This is the coarse default; the deep-lane refine Step 9
      module-mapping derivation overwrites it with the accurate band
      (``multi_module`` / ``broad``) when the deep lane runs.

    The vocabulary is deliberately limited to the two narrow bands the light
    lane cares about — the heuristic is a cheap pre-route guess, not the
    authoritative scope estimate.
    """
    if not body:
        return SINGLE_MODULE
    if _GLOB_RE.search(body):
        return SINGLE_MODULE
    distinct_paths = _distinct_paths(body)
    if 1 <= len(distinct_paths) <= _SURGICAL_MAX_PATHS:
        return SURGICAL
    return SINGLE_MODULE


def project_profile_pure(
    scope_estimate: str | None,
    change_type: str | None,
    compatibility: str | None,
    request_concrete: bool,
) -> str:
    """Project the recommended execution-profile posture — pure, I/O-free.

    A deterministic function of the SAME signals the lane verdict scores (it
    adds no discovery and no cognition). It recommends a posture on the
    ``minimal ⊏ auto ⊏ full`` lattice:

    - ``minimal`` — a narrow (surgical / single_module) AND concretely specified
      change. A mechanical, well-anchored, low-stakes change. This is the same
      narrow-and-concrete predicate the lane verdict's S3/S4 carve-out uses, so a
      bounded surgical fix stays ``minimal`` even when its ``change_type`` reads
      generative or its ``compatibility`` reads breaking — the narrow, concrete
      bound dominates.
    - ``full`` — a generative change (``change_type ∈ {feature,
      feature_breaking}``) that is also broad (``scope_estimate`` ∈ multi_module
      / broad) OR clean-slate breaking, and NOT narrow-and-concrete. These are
      the correctly-deep features where the adversarial ceremony earns its cost.
    - ``auto`` — everything else (the generic recommendation / default).

    The recommendation is exactly that — a default the operator overrides. It is
    independent of the ``deep_lane`` ceremony gate (which governs planning depth,
    not the profile).
    """
    narrow_and_concrete = scope_estimate in _NARROW_SCOPE_ESTIMATES and request_concrete
    if narrow_and_concrete:
        return MINIMAL
    generative = change_type in _DEEP_CHANGE_TYPES
    broad = scope_estimate in _BROAD_SCOPE_ESTIMATES
    breaking = compatibility == 'breaking'
    if generative and (broad or breaking):
        return FULL
    return AUTO


def evaluate_signals_pure(
    scope_estimate: str | None,
    change_type: str | None,
    compatibility: str | None,
    plan_source: str | None,
    request_concrete: bool,
    override: str | None = None,
) -> dict[str, Any]:
    """Score the S1–S6 signal set into a lane verdict — pure, I/O-free.

    Takes the realized signal values directly (the reads happen in the caller)
    and returns the ``{lane, fired_signals, signals, profile}`` dict that drives
    the route dispatch. ``profile`` carries the recommended execution-profile
    posture (``project_profile_pure``) plus the candidate posture lattice — the
    init dialogue consumes it as the default recommendation. Importable by
    downstream consumers (e.g. the audit retrospective check) so the routing
    thresholds are never duplicated.
    """
    # Carve-out — the positively-bounded case. A request that is BOTH narrowly
    # scoped (scope_estimate ∈ {surgical, single_module}) AND concretely
    # specified is well-bounded enough that S3 (generative change_type) and S4
    # (breaking compatibility) firing *alone* must not force deep. The carve-out
    # relaxes ONLY this co-firing: S1/S2/S5 (the unknown-to-deep defaults) and
    # S6 (explicit override) are unaffected, so the conservative unknown case
    # keeps biasing deep unchanged.
    narrow_and_concrete = scope_estimate in _NARROW_SCOPE_ESTIMATES and request_concrete
    # S5 — vague ask, no anchors → deep.
    s5_deep = not request_concrete
    # S1 — free-form source (absent/unset) AND S5 concreteness fails → deep.
    # lesson-id / recipe sources are pre-specified by construction → bias light.
    free_form_source = plan_source in (None, '', 'free_form', 'cli')
    s1_deep = bool(free_form_source and s5_deep)
    # S2 — broad / unknown scope bands → deep.
    s2_deep = scope_estimate in _DEEP_SCOPE_ESTIMATES or scope_estimate is None
    # S3 — generative change types → deep, EXCEPT in the narrow-and-concrete
    # carve-out where a bounded, well-specified generative change stays light.
    s3_deep = change_type in _DEEP_CHANGE_TYPES and not narrow_and_concrete
    # S4 — clean-slate breaking changes tend cross-cutting → deep, EXCEPT in the
    # narrow-and-concrete carve-out.
    s4_deep = compatibility == 'breaking' and not narrow_and_concrete
    # S6 — explicit user override to deep is one-way.
    s6_deep = override == DEEP

    fired = []
    if s1_deep:
        fired.append('S1:plan_source')
    if s2_deep:
        fired.append('S2:scope_estimate')
    if s3_deep:
        fired.append('S3:change_type')
    if s4_deep:
        fired.append('S4:compatibility')
    if s5_deep:
        fired.append('S5:concreteness')
    if s6_deep:
        fired.append('S6:override')

    lane = DEEP if fired else LIGHT
    recommended_posture = project_profile_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility=compatibility,
        request_concrete=request_concrete,
    )
    return {
        'lane': lane,
        'fired_signals': fired,
        'signals': {
            'plan_source': plan_source,
            'scope_estimate': scope_estimate,
            'change_type': change_type,
            'compatibility': compatibility,
            'request_concrete': request_concrete,
            'planning_lane_override': override,
        },
        'profile': {
            'recommended_posture': recommended_posture,
            'candidate_postures': [MINIMAL, AUTO, FULL],
        },
    }


def _evaluate_signals(plan_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    """Read S1–S6 signals from disk and delegate scoring to the pure helper.

    Returns the dict produced by ``evaluate_signals_pure``:

    - ``lane`` — the aggregate ``{light|deep}`` verdict.
    - ``fired_signals`` — the list of deep-bias signals that fired.
    - ``signals`` — the resolved S1-S6 input values (``plan_source``,
      ``scope_estimate``, ``change_type``, ``compatibility``,
      ``request_concrete``, ``planning_lane_override``).
    """
    plan_source = metadata.get('plan_source')
    change_type = metadata.get('change_type')
    override = metadata.get('planning_lane_override')

    scope_estimate = _read_scope_estimate(plan_id)
    compatibility = _read_compatibility()
    body = _read_request_body(plan_id)
    concrete = _request_is_concrete(body)

    return evaluate_signals_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility=compatibility,
        plan_source=plan_source,
        request_concrete=concrete,
        override=override,
    )


def cmd_planning_lane_route(args: argparse.Namespace) -> dict[str, Any]:
    """Resolve ``{light|deep}`` from the DQ1 signal set and persist it.

    ``--lane-override {deep|light}`` seeds ``status.metadata.planning_lane_override``
    before the signal evaluation (a CLI-init convenience). ``--persist`` writes
    the resolved lane into ``status.metadata.planning_lane`` and emits one
    decision-log line naming every signal value and the winning predicate.
    """
    plan_id: str = args.plan_id
    lane_override: str | None = getattr(args, 'lane_override', None)
    persist: bool = bool(getattr(args, 'persist', False))

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'message': f'Plan directory not found: {plan_dir}',
        }

    try:
        status = read_status(plan_id)
    except FileNotFoundError:
        status = {}
    metadata = status.get('metadata')
    if not isinstance(metadata, dict):
        metadata = {}

    # A CLI --lane-override seeds the S6 signal source so the evaluation sees it.
    if lane_override in (DEEP, LIGHT):
        metadata = dict(metadata)
        metadata['planning_lane_override'] = lane_override

    # Pre-route validation pass (deterministic, flag-not-block): cross-check
    # change_type / scope_estimate against cheap request signals and emit a
    # Q-Gate finding on a mismatch. This NEVER gates the lane resolution — the
    # gate result is surfaced under ``classification_validation`` for
    # observability and the routing continues unconditionally.
    classification_validation = run_classification_validation(plan_id)

    ceremony = _read_deep_lane_gate()

    # The signal set is scored unconditionally so the execution-profile
    # projection is available regardless of the deep_lane ceremony gate. The
    # gate short-circuits ONLY the {light, deep} planning-depth verdict; it must
    # NOT coerce the profile (deep_lane=always does not force `full` — §4.2).
    signal_evaluation = _evaluate_signals(plan_id, metadata)
    profile = signal_evaluation['profile']

    evaluation: dict[str, Any]
    if ceremony == 'always':
        lane = DEEP
        decision = 'plan.phase-1-init.deep_lane=always'
        evaluation = {
            'lane': lane,
            'fired_signals': ['deep_lane:always'],
            'signals': signal_evaluation['signals'],
            'profile': profile,
        }
    elif ceremony == 'never':
        lane = LIGHT
        decision = 'plan.phase-1-init.deep_lane=never'
        evaluation = {'lane': lane, 'fired_signals': [], 'signals': signal_evaluation['signals'], 'profile': profile}
    else:
        evaluation = signal_evaluation
        lane = evaluation['lane']
        decision = 'signal_set'

    recommended_posture = profile['recommended_posture']

    persisted = False
    if persist:
        if 'metadata' not in status or not isinstance(status['metadata'], dict):
            status['metadata'] = {}
        status['metadata']['planning_lane'] = lane
        # Persist the projected posture as the init-time default; the operator's
        # final choice (if it overrides the recommendation) is written by the
        # phase-1-init dialogue via `manage-status metadata`.
        if 'execution_profile' not in status['metadata']:
            status['metadata']['execution_profile'] = recommended_posture
        if lane_override in (DEEP, LIGHT):
            status['metadata']['planning_lane_override'] = lane_override
        write_status(plan_id, status)
        persisted = True

    fired = evaluation['fired_signals']
    log_entry(
        'decision',
        plan_id,
        'INFO',
        (
            f'(plan-marshall:manage-status:planning-lane) Routed planning_lane={lane} '
            f'(predicate={decision}, fired={fired or "none"}, '
            f'ceremony.deep_lane={ceremony}, execution_profile={recommended_posture}, '
            f'signals={evaluation["signals"]})'
        ),
    )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'planning_lane': lane,
        'ceremony_deep_lane': ceremony,
        'decision_predicate': decision,
        'fired_signals': fired,
        'signals': evaluation['signals'],
        'execution_profile': recommended_posture,
        'profile': profile,
        'persisted': persisted,
        'classification_validation': {
            'mismatch_count': classification_validation.get('mismatch_count', 0),
            'mismatches': classification_validation.get('mismatches', []),
            'findings_emitted': classification_validation.get('findings_emitted', 0),
        },
    }


def cmd_scope_estimate_heuristic(args: argparse.Namespace) -> dict[str, Any]:
    """Classify a coarse ``scope_estimate`` from the request and persist it.

    Reads the clarified-request (or original-input) narrative, classifies it via
    ``scope_estimate_from_request_pure`` (distinct-file-path count, ZERO
    architecture queries), and with ``--persist`` writes it to
    ``references.json``'s ``scope_estimate`` field — the same field
    ``_read_scope_estimate`` (the router's S2 signal source) reads. Run at
    phase-1-init BEFORE the planning-lane route so the router reads a real
    ``scope_estimate`` instead of ``None``. The deep-lane refine Step 9
    module-mapping derivation later overwrites the coarse guess when the deep
    lane runs, so no accuracy is lost.
    """
    plan_id: str = args.plan_id
    persist: bool = bool(getattr(args, 'persist', False))

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'message': f'Plan directory not found: {plan_dir}',
        }

    body = _read_request_body(plan_id)
    scope_estimate = scope_estimate_from_request_pure(body)
    distinct_paths = sorted(_distinct_paths(body)) if body else []

    persisted = False
    if persist:
        references_path = get_plan_dir(plan_id) / 'references.json'
        references = read_json(references_path, default={})
        if not isinstance(references, dict):
            references = {}
        references['scope_estimate'] = scope_estimate
        write_json(references_path, references)
        persisted = True
        log_entry(
            'decision',
            plan_id,
            'INFO',
            (
                f'(plan-marshall:manage-status:scope-estimate-heuristic) '
                f'Classified scope_estimate={scope_estimate} '
                f'(distinct_paths={len(distinct_paths)}, glob={bool(_GLOB_RE.search(body))}) '
                f'— pre-route coarse guess, deep-lane Step 9 may overwrite'
            ),
        )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'scope_estimate': scope_estimate,
        'distinct_path_count': len(distinct_paths),
        'distinct_paths': distinct_paths,
        'persisted': persisted,
    }


def cmd_planning_lane_escalate(args: argparse.Namespace) -> dict[str, Any]:
    """One-way ratchet: set ``planning_lane=deep`` + ``lane_escalated=true``.

    Monotonic light→deep. Refuses any attempt to set a lane back to ``light``
    once ``lane_escalated`` is true — there is no downgrade path. The trigger
    (``explosion`` / ``premise`` / ``cross_cutting``) is recorded in
    ``status.metadata.escalation_trigger``. ``--persist`` writes the mutation.
    """
    plan_id: str = args.plan_id
    trigger: str = args.trigger
    persist: bool = bool(getattr(args, 'persist', False))

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'message': f'Plan directory not found: {plan_dir}',
        }

    try:
        status = read_status(plan_id)
    except FileNotFoundError:
        status = {}
    if 'metadata' not in status or not isinstance(status['metadata'], dict):
        status['metadata'] = {}
    metadata = status['metadata']

    metadata['planning_lane'] = DEEP
    metadata['lane_escalated'] = True
    metadata['escalation_trigger'] = trigger

    persisted = False
    if persist:
        write_status(plan_id, status)
        persisted = True

    log_entry(
        'decision',
        plan_id,
        'INFO',
        (
            f'(plan-marshall:manage-status:planning-lane) Escalated planning_lane=deep '
            f'(trigger={trigger}, lane_escalated=true) — one-way ratchet, no downgrade'
        ),
    )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'planning_lane': DEEP,
        'lane_escalated': True,
        'escalation_trigger': trigger,
        'persisted': persisted,
    }
