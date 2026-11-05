#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-105 D4 — the success-criteria parser keeps every criterion.

At HEAD ``**Success Criteria:**`` keeps only unbroken ``- `` lines, so a criterion
wrapped over two lines, one carrying an indented sub-bullet, and a ``*`` bullet
are each frozen as their first line — or dropped. The review then grades part of a
deliverable without saying so.

The migration hazard is the mirror image: an old-parser snapshot of a wrapped
bullet must not read as a rewritten criterion after the parser change.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import _criteria_snapshot as _snap
import _review_support_attribution as _attr
import review_support

PLAN_ID = 'lb105-criteria-parser-d4'


def _outline(block: str) -> str:
    return (
        '# Solution: criteria\n\n## Deliverables\n\n### 1. Deliver the change\n\n'
        '**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        f'**Success Criteria:**\n{block}\n'
    )


def _plan(plan_context: Any, block: str) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    (plan_dir / 'status.json').write_text(
        json.dumps({'title': 'fixture', 'phases': [], 'current_phase': '6-finalize', 'metadata': {}}),
        encoding='utf-8',
    )
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    (plan_dir / 'solution_outline.md').write_text(_outline(block), encoding='utf-8')
    return plan_dir


def _verdict(criterion_ids: list[str]) -> dict[str, Any]:
    return {
        'deliverables': [
            {
                'number': 1,
                'verdict': 'met',
                'criteria': [
                    {
                        'criterion': 'see the frozen criterion',
                        'criterion_id': criterion_id,
                        'status': 'met',
                        'evidence': ['pyproject.toml:1'],
                    }
                    for criterion_id in criterion_ids
                ],
            }
        ],
        'unrequested_changes': [],
        'self_reports': [],
        'files_read': ['pyproject.toml'],
    }


def _sealed(tmp_path: Path, document: dict[str, Any]) -> str:
    path = tmp_path / 'verdict.json'
    path.write_text(json.dumps(document), encoding='utf-8')
    sealed = review_support.run_author_verdict(PLAN_ID, 'functional', str(path))
    assert sealed['status'] == 'success', sealed
    return str(path)


#: The three bullet shapes: a wrapped criterion, one with an indented sub-bullet,
#: and a ``*`` bullet.
MIXED = (
    '- a criterion that wraps\n'
    '  onto a second line\n'
    '- a criterion with a nested\n'
    '  - sub-bullet detail\n'
    '* a star-bullet criterion\n'
)

EXPECTED_MIXED = [
    'a criterion that wraps onto a second line',
    'a criterion with a nested sub-bullet detail',
    'a star-bullet criterion',
]


# --- D4 (a): every bullet shape is one criterion, frozen whole ------------------------------


def test_a_wrapped_sub_bullet_and_star_criterion_all_freeze(plan_context) -> None:
    _plan(plan_context, MIXED)

    snapshot = _snap.build_snapshot(PLAN_ID)

    assert [row['criteria'] for row in snapshot['deliverables']] == [EXPECTED_MIXED]


# --- D4 (b): sealing a verdict that grades C2 and C3 by id succeeds --------------------------


def test_sealing_a_verdict_that_grades_c2_and_c3_by_id_succeeds(plan_context, tmp_path) -> None:
    _plan(plan_context, MIXED)
    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'

    sealed = review_support.run_author_verdict(PLAN_ID, 'functional', _sealed(tmp_path, _verdict(['C1', 'C2', 'C3'])))

    assert sealed['status'] == 'success', sealed


# --- D4 (c): a stray line inside the block is reported, never dropped ----------------------


def test_snapshot_criteria_reports_a_stray_line_as_unparsed(plan_context) -> None:
    _plan(plan_context, '- one criterion\n\nthis line is not a bullet\n- two criterion\n')

    payload = _snap.write_snapshot(PLAN_ID)

    assert payload['status'] == 'success', payload
    assert payload['criterion_count'] == 2
    assert payload['unparsed'] == ['this line is not a bullet']
    assert payload['deliverables'] == [{'number': 1, 'criterion_count': 2, 'unparsed': ['this line is not a bullet']}]


# --- D4 (d): an old-parser snapshot migrates as parser_extended, not drift ------------------


def test_an_old_parser_snapshot_of_a_wrapped_bullet_yields_parser_extended(plan_context, tmp_path) -> None:
    _plan(plan_context, '- a criterion that wraps\n  onto a second line\n')
    snapshot = {
        'schema': _snap.SCHEMA,
        'plan_id': PLAN_ID,
        'deliverables': [{'number': 1, 'title': 'Deliver the change', 'criteria': ['a criterion that wraps']}],
        'request': {'done_when': [], 'source': 'absent'},
        'spec': None,
        'authorized_changes': [],
    }
    path = _snap.snapshot_path(PLAN_ID)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    assert _snap.record_snapshot_digest(PLAN_ID)

    drift = _snap.criteria_drift(PLAN_ID)

    assert [row['kind'] for row in drift] == ['parser_extended'], drift

    verdict = _verdict(['C1'])
    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, verdict), None)
    assert payload.get('errors') == [], payload.get('errors')
    assert payload.get('valid') is True, payload.get('errors')
    assert [finding for finding in payload['findings'] if finding['kind'] == 'criterion_rewritten'] == []


# --- D4 control: single-line bullets are frozen exactly as before ---------------------------


def _retired_parser(block: str) -> list[str]:
    """The retired rule, spelled out: consecutive ``- `` lines, first line only."""
    return [line[2:].strip() for line in block.splitlines() if line.startswith('- ')]


def test_single_line_bullets_freeze_exactly_what_the_retired_parser_produced(plan_context) -> None:
    """The shape the old parser handled yields an identical frozen record."""
    block = '- first criterion\n- second criterion\n- third criterion\n'
    _plan(plan_context, block)

    snapshot = _snap.build_snapshot(PLAN_ID)

    assert snapshot['deliverables'][0]['criteria'] == _retired_parser(block)
    rebuilt = {**snapshot, 'deliverables': [{**snapshot['deliverables'][0], 'criteria': _retired_parser(block)}]}
    assert json.dumps(snapshot, sort_keys=True) == json.dumps(rebuilt, sort_keys=True)
    assert _snap.criteria_drift(PLAN_ID) == []
