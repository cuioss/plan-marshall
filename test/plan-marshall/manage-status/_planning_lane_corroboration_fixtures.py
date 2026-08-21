#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``planning lane corroboration`` test module.

Holds the module-level loads, constants and helpers it uses, so
the module itself carries the import and not the preamble.
"""


from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

_mod = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_planning_lane.py', '_cmd_planning_lane_corroboration'
)


evaluate_signals_pure = _mod.evaluate_signals_pure


cmd_planning_lane_route = _mod.cmd_planning_lane_route


# The EXACT recorded signal vector from the observed over-route (plan 240 § Problem),
# transcribed so D3(a) can replay it without the archived decision log (which lives
# under .plan/, absent from this clone). fired=['S7:risk_prose'] alone bought deep.
_RECORDED_VECTOR = {
    'plan_source': None,
    'scope_estimate': 'single_module',
    'change_type': None,
    'compatibility': None,
    'request_concrete': True,
    'risk_prose': True,
    'override': None,
}


# =============================================================================
# D0/D3(b) — the orchestrator-spec plan_source bridge (end-to-end via the router)
# =============================================================================


def _write_orchestrator_request(plan_dir: Path, source_id: str, body: str) -> None:
    """Author a ``request.md`` in phase-1-init's file-pointer (orchestrator-spec) shape.

    ``source: description`` with a non-empty ``source_id`` header — the exact shape
    phase-1-init writes via ``request create --source-id`` on the file-pointer
    branch, and the one it never mirrors into ``status.metadata.plan_source``.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    content = (
        '# Request: An ingested orchestrator plan spec\n'
        '\n'
        f'plan_id: {plan_dir.name}\n'
        'source: description\n'
        f'source_id: {source_id}\n'
        'created: 2026-01-01T00:00:00Z\n'
        '\n'
        '## Original Input\n'
        '\n'
        f'{body}\n'
    )
    (plan_dir / 'request.md').write_text(content, encoding='utf-8')


def _write_plaintext_request(plan_dir: Path, body: str) -> None:
    """A plain-text ``description`` request: ``source: description``, NO ``source_id``.

    phase-1-init strips the ``source_id`` line for a plain-text description (the
    template placeholder is cleaned when unset), so this is the shape that must NOT
    resolve orchestrator provenance.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    content = (
        '# Request: A plain-text description\n'
        '\n'
        f'plan_id: {plan_dir.name}\n'
        'source: description\n'
        'created: 2026-01-01T00:00:00Z\n'
        '\n'
        '## Original Input\n'
        '\n'
        f'{body}\n'
    )
    (plan_dir / 'request.md').write_text(content, encoding='utf-8')


def _write_status(plan_dir: Path, metadata: dict | None = None) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_dir.name, 'phases': [], 'metadata': metadata or {}}),
        encoding='utf-8',
    )


def _write_references(plan_dir: Path, scope_estimate: str | None) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    refs: dict = {'base_branch': 'main'}
    if scope_estimate is not None:
        refs['scope_estimate'] = scope_estimate
    (plan_dir / 'references.json').write_text(json.dumps(refs), encoding='utf-8')


def _write_marshal(fixture_dir: Path) -> None:
    (fixture_dir / 'marshal.json').write_text(
        json.dumps(
            {
                'plan': {
                    'phase-1-init': {'deep_lane': 'auto'},
                    'phase-2-refine': {'compatibility': 'deprecation'},
                }
            },
            indent=2,
        ),
        encoding='utf-8',
    )


def _ns_route(plan_id: str) -> Namespace:
    return Namespace(plan_id=plan_id, lane_override=None, persist=False)
