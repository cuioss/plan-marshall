#!/usr/bin/env python3
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
| S3 | ``change_type`` | ``status.metadata.change_type`` | ∈ {feature, feature_breaking} |
| S4 | ``compatibility`` | ``marshal.json plan.phase-2-refine.compatibility`` | == breaking |
| S5 | request concreteness | regex over ``request.md`` body | NO file path AND NO concrete fix signal |
| S6 | explicit override | ``status.metadata.planning_lane_override`` | == deep forces deep (one-way) |

``deep`` IFF (S1 ∨ S2 ∨ S3 ∨ S4 ∨ S5 ∨ S6-deep); otherwise ``light``.

``plan.phase-1-init.deep_lane`` is read BEFORE the signal set and
short-circuits the evaluation: ``always`` forces deep, ``never`` forces light
(the DQ3 hard-escalation ratchet still fires unless ``plan.phase-1-init.escalation``
is also ``never``), ``auto`` (the default) defers to the signals.
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

from _cmd_classification_validate import run_classification_validation
from _plan_parsing import parse_document_sections  # type: ignore[import-not-found]
from _status_core import read_status, write_status
from constants import FILE_MARSHAL  # type: ignore[import-not-found]
from file_ops import base_path, get_plan_dir, read_json  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]

LIGHT = 'light'
DEEP = 'deep'

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


def _evaluate_signals(plan_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    """Evaluate S1–S6 and return the per-signal verdict + winning lane.

    Returns a dict carrying every signal's resolved value and its deep-bias
    boolean, plus the aggregate ``lane`` and the list of fired deep signals.
    """
    plan_source = metadata.get('plan_source')
    change_type = metadata.get('change_type')
    override = metadata.get('planning_lane_override')

    scope_estimate = _read_scope_estimate(plan_id)
    compatibility = _read_compatibility()
    body = _read_request_body(plan_id)
    concrete = _request_is_concrete(body)

    # S5 — vague ask, no anchors → deep.
    s5_deep = not concrete
    # S1 — free-form source (absent/unset) AND S5 concreteness fails → deep.
    # lesson-id / recipe sources are pre-specified by construction → bias light.
    free_form_source = plan_source in (None, '', 'free_form', 'cli')
    s1_deep = bool(free_form_source and s5_deep)
    # S2 — broad / unknown scope bands → deep.
    s2_deep = scope_estimate in _DEEP_SCOPE_ESTIMATES or scope_estimate is None
    # S3 — generative change types → deep.
    s3_deep = change_type in _DEEP_CHANGE_TYPES
    # S4 — clean-slate breaking changes tend cross-cutting → deep.
    s4_deep = compatibility == 'breaking'
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
    return {
        'lane': lane,
        'fired_signals': fired,
        'signals': {
            'plan_source': plan_source,
            'scope_estimate': scope_estimate,
            'change_type': change_type,
            'compatibility': compatibility,
            'request_concrete': concrete,
            'planning_lane_override': override,
        },
    }


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

    evaluation: dict[str, Any]
    if ceremony == 'always':
        lane = DEEP
        decision = 'plan.phase-1-init.deep_lane=always'
        evaluation = {'lane': lane, 'fired_signals': ['deep_lane:always'], 'signals': {}}
    elif ceremony == 'never':
        lane = LIGHT
        decision = 'plan.phase-1-init.deep_lane=never'
        evaluation = {'lane': lane, 'fired_signals': [], 'signals': {}}
    else:
        evaluation = _evaluate_signals(plan_id, metadata)
        lane = evaluation['lane']
        decision = 'signal_set'

    persisted = False
    if persist:
        if 'metadata' not in status or not isinstance(status['metadata'], dict):
            status['metadata'] = {}
        status['metadata']['planning_lane'] = lane
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
            f'ceremony.deep_lane={ceremony}, signals={evaluation["signals"]})'
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
        'persisted': persisted,
        'classification_validation': {
            'mismatch_count': classification_validation.get('mismatch_count', 0),
            'mismatches': classification_validation.get('mismatches', []),
            'findings_emitted': classification_validation.get('findings_emitted', 0),
        },
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
