#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``planning lane`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

_mod = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_planning_lane.py', '_cmd_planning_lane_under_test'
)


cmd_planning_lane_route = _mod.cmd_planning_lane_route


cmd_planning_lane_escalate = _mod.cmd_planning_lane_escalate


evaluate_signals_pure = _mod.evaluate_signals_pure


project_profile_pure = _mod.project_profile_pure


classify_scope_pure = _mod.classify_scope_pure


scope_estimate_from_request_pure = _mod.scope_estimate_from_request_pure


cmd_scope_estimate_heuristic = _mod.cmd_scope_estimate_heuristic


# =============================================================================
# Fixture authoring helpers
# =============================================================================

# A request body that PASSES S5 concreteness (names a file path) so the S5 /
# S1 deep-bias does not fire — lets the other signals be tested in isolation.
_CONCRETE_BODY = (
    'Update `marketplace/bundles/plan-marshall/skills/x/scripts/x.py` to fix '
    'the parser.'
)


# A vague request body that FAILS S5 (no path, no fix signal) → S5 deep.
_VAGUE_BODY = 'The thing should do the thing per the thing, somehow.'


def _write_request(plan_dir: Path, body: str) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    content = (
        '# Request\n\n'
        '## Original Input\n\n'
        '(unused)\n\n'
        '## Clarified Request\n\n'
        f'{body}\n'
    )
    (plan_dir / 'request.md').write_text(content, encoding='utf-8')


# An INGESTED orchestrator plan spec, embedded verbatim under ``## Original
# Input`` exactly as phase-1-init writes it. Its defining property — and the one
# every pre-existing fixture above lacks — is that it carries its OWN ``## ``
# headings, so an H2-splitting section reader terminates ``original_input`` at
# ``## Objective`` and never sees the surface list below it.
#
# The two readings disagree by construction, which is what makes this fixture a
# pre/post discriminator rather than a restatement:
#
#   truncated (H2-split) -> 1 path, the boilerplate CITATION only -> surgical
#   whole body           -> 5 distinct paths (citation + 4 targets) -> single_module
_INGESTED_SPEC_BODY = (
    '# PLAN-99: An ingested orchestrator plan spec\n'
    '\n'
    'epic: truthful-signals\n'
    '\n'
    '> Staged plan spec — one shippable unit of work. See\n'
    '> `persona-plan-orchestrator/standards/orchestration-model.md` for the\n'
    '> hand-off contract.\n'
    '\n'
    '## Objective\n'
    '\n'
    'Fix the four real targets enumerated below.\n'
    '\n'
    '## Expected Surface\n'
    '\n'
    '- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py`\n'
    '- `test/plan-marshall/manage-status/test_planning_lane.py`\n'
    '- `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md`\n'
    '- `doc/concepts/orchestration.adoc`\n'
)


# The single path token in the truncated head region — a CITATION of a governing
# document, never a target of the work.
_BOILERPLATE_CITATION = 'persona-plan-orchestrator/standards/orchestration-model.md'


# A target named in the ingested body BELOW the first nested ``## `` heading. The
# truncating read could never reach it.
_TARGET_BELOW_NESTED_HEADING = (
    'marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py'
)


def _write_ingested_request(plan_dir: Path, spec_body: str = _INGESTED_SPEC_BODY) -> None:
    """Author a ``request.md`` whose ``## Original Input`` holds an ingested spec.

    Mirrors the phase-1-init shape for an orchestrated plan: a ``# Request``
    title, the virtual-header metadata block, and the spec embedded verbatim
    under ``## Original Input``. There is deliberately NO ``## Clarified
    Request`` section — the scope heuristic runs at phase-1-init, before refine
    authors one.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    content = (
        '# Request: An ingested orchestrator plan spec\n'
        '\n'
        f'plan_id: {plan_dir.name}\n'
        'source: description\n'
        '\n'
        '## Original Input\n'
        '\n'
        f'{spec_body}'
    )
    (plan_dir / 'request.md').write_text(content, encoding='utf-8')


def _write_status(plan_dir: Path, metadata: dict | None = None) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps(
            {'plan_id': plan_dir.name, 'phases': [], 'metadata': metadata or {}}
        ),
        encoding='utf-8',
    )


def _write_references(plan_dir: Path, scope_estimate: str | None) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    refs: dict = {'base_branch': 'main'}
    if scope_estimate is not None:
        refs['scope_estimate'] = scope_estimate
    (plan_dir / 'references.json').write_text(json.dumps(refs), encoding='utf-8')


def _write_marshal(fixture_dir: Path, *, compatibility: str = 'deprecation', deep_lane: str = 'auto') -> None:
    """Write a minimal marshal.json at the fixture root (= PLAN_BASE_DIR)."""
    config = {
        'plan': {
            'phase-1-init': {'deep_lane': deep_lane},
            'phase-2-refine': {'compatibility': compatibility},
        },
    }
    (fixture_dir / 'marshal.json').write_text(json.dumps(config, indent=2), encoding='utf-8')


def _ns_route(plan_id: str, *, lane_override=None, persist=False) -> Namespace:
    return Namespace(plan_id=plan_id, lane_override=lane_override, persist=persist)


def _ns_escalate(plan_id: str, *, trigger='explosion', persist=False) -> Namespace:
    return Namespace(plan_id=plan_id, trigger=trigger, persist=persist)


def _light_setup(plan_context, plan_id: str) -> Path:
    """Seed an all-light baseline: concrete request, light scope, light change_type,
    non-breaking compatibility, auto deep_lane. Every signal biases light.
    """
    plan_dir: Path = plan_context.plan_dir_for(plan_id)
    _write_request(plan_dir, _CONCRETE_BODY)
    _write_status(plan_dir, metadata={'plan_source': 'lesson', 'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='surgical')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='auto')
    return plan_dir


# =============================================================================
# evaluate_signals_pure — direct, I/O-free unit coverage
# =============================================================================
#
# The pure scorer takes the five realized signals (plus the S6 override) as plain
# arguments and performs zero file I/O. These cases lock its scoring against the
# integrated _evaluate_signals path covered above. The all-light baseline below
# biases EVERY signal light; each isolation case flips exactly one argument and
# asserts the resulting lane + fired_signals entry.

# All-light keyword baseline: surgical scope, bug_fix change_type, deprecation
# compatibility, pre-specified source, concrete request, no override.
_LIGHT_PURE_KWARGS = {
    'scope_estimate': 'surgical',
    'change_type': 'bug_fix',
    'compatibility': 'deprecation',
    'plan_source': 'lesson',
    'request_concrete': True,
    'override': None,
}


def _pure(**overrides):
    """Score evaluate_signals_pure from the all-light baseline with overrides applied."""
    kwargs = {**_LIGHT_PURE_KWARGS, **overrides}
    return evaluate_signals_pure(**kwargs)


# =============================================================================
# classify_scope_pure — pre-route coarse scope classifier (D2)
# =============================================================================
#
# A pure, ZERO-architecture-call classifier over two measurements — the count of
# distinct file-path references and the presence of a fan-out marker — emitting
# one of four bands: none (declared unknown) / surgical (1-3 paths, no fan-out) /
# single_module (4-7 paths, or a pathless non-empty body) / multi_module (a real
# fan-out marker, or >= 8 paths). It is a pre-route guess; the deep-lane refine
# Step 9 module-mapping derivation overwrites it when the deep lane runs.
#
# The band line is scale-truthful in BOTH directions, which is the property these
# tests exist to pin: it can say "large" (multi_module) and it can say "I cannot
# bound this" (a fan-out marker WIDENS, it does not narrow).


def _ns_scope(plan_id: str, *, persist: bool = False) -> Namespace:
    return Namespace(plan_id=plan_id, persist=persist)
