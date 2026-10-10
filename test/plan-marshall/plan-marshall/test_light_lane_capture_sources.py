#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Capture-source matrix: every refine-boundary product has a light-lane producer.

On the deep lane, phase-2-refine Step 13 persists the values later phases read
at and after the ``2-refine`` boundary. The light lane never runs that step, so
planning.md's "Light-lane branch" publishes a capture-source matrix naming the
light-lane producer of each one. The matrix test DERIVES the product set from
Step 13's own persist items rather than pinning a hand-copied list, so a new
Step 13 persist without a light-lane row fails here. The fixture case runs the
``track`` persist exactly as light-lane.md documents it and reads it back the
way phase-4-plan does.
"""

from __future__ import annotations

import re

from toon_parser import parse_toon

from conftest import MARKETPLACE_ROOT, get_script_path, run_script

SKILLS_ROOT = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'
REFINE_SKILL_MD = SKILLS_ROOT / 'phase-2-refine' / 'SKILL.md'
PLANNING_MD = SKILLS_ROOT / 'plan-marshall' / 'workflow' / 'planning.md'
LIGHT_LANE_MD = SKILLS_ROOT / 'phase-3-outline' / 'workflow' / 'light-lane.md'

REFERENCES_SCRIPT = get_script_path('plan-marshall', 'manage-references', 'manage-references.py')

_STEP_13_HEADING = '### Step 13: Persist and Return Results'
_MATRIX_ANCHOR = '**Light-lane capture-source matrix.**'
_MATRIX_END = '**Deep-lane branch**'

# A top-level numbered Step 13 item: "N. **Bold head** rest of the item".
_ITEM_RE = re.compile(r'^\d+\. \*\*(?P<head>[^*]+)\*\*(?P<body>.*)$', re.MULTILINE)
_FIELD_RE = re.compile(r'--field (?P<field>\w+)')
_PERSIST_HEAD_RE = re.compile(r'^(?:author and )?persist\s+', re.IGNORECASE)

# The documented light-lane track persist (the command may wrap onto a
# continuation line between the notation and the verb).
_TRACK_PERSIST_RE = re.compile(
    r'manage-references:manage-references\s*\\?\s*set --plan-id \{plan_id\} --field track --value (?P<value>\S+)'
)


def _section(text: str, start_marker: str, end_marker: str, label: str) -> str:
    start = text.find(start_marker)
    assert start != -1, f'{start_marker!r} not found in {label}'
    end = text.find(end_marker, start + len(start_marker))
    assert end != -1, f'{end_marker!r} not found after {start_marker!r} in {label}'
    return text[start:end]


def _step_13_products() -> set[str]:
    """Derive the product set from Step 13's persist items.

    A persist item's product is the ``--field`` it writes when it names one
    (``scope_estimate``, ``track``, ``pr_title``), otherwise the bold head with
    its ``Persist`` verb stripped (``module mapping``, a file artifact).
    """
    section = _section(REFINE_SKILL_MD.read_text(encoding='utf-8'), _STEP_13_HEADING, '\n### ', str(REFINE_SKILL_MD))
    products: set[str] = set()
    for item in _ITEM_RE.finditer(section):
        head = item.group('head').strip()
        if 'persist' not in head.lower():
            continue
        field = _FIELD_RE.search(item.group('body'))
        products.add(field.group('field') if field else _PERSIST_HEAD_RE.sub('', head).strip())
    return products


def _matrix_rows() -> list[list[str]]:
    section = _section(PLANNING_MD.read_text(encoding='utf-8'), _MATRIX_ANCHOR, _MATRIX_END, str(PLANNING_MD))
    rows: list[list[str]] = []
    for line in section.splitlines():
        if not line.startswith('|') or set(line) <= {'|', '-', ' '}:
            continue
        rows.append([cell.strip() for cell in line.strip().strip('|').split('|')])
    assert rows, f'no table rows found under {_MATRIX_ANCHOR!r} in {PLANNING_MD}'
    header, body = rows[0], rows[1:]
    assert header[:3] == ['Product', 'Deep-lane producer', 'Light-lane producer'], header
    return body


def test_capture_source_matrix_is_published_once() -> None:
    text = PLANNING_MD.read_text(encoding='utf-8')
    assert text.count(_MATRIX_ANCHOR) == 1, f'expected the capture-source matrix exactly once in {PLANNING_MD}'


def test_every_step_13_product_has_a_named_light_lane_producer() -> None:
    products = _step_13_products()
    # Non-vacuity: the derivation must find Step 13's persist items, including
    # the two this matrix exists to cover, or the loop below proves nothing.
    assert {'track', 'pr_title'} <= products, f'Step 13 persist derivation found {sorted(products)}'

    rows = _matrix_rows()
    missing: list[str] = []
    for product in sorted(products):
        matching = [row for row in rows if f'`{product}`' in row[0] or row[0].startswith(product)]
        if len(matching) != 1 or not matching[0][2] or not matching[0][3]:
            missing.append(product)
    assert not missing, (
        f'Step 13 product(s) without exactly one matrix row naming a light-lane producer and its consequence: {missing}'
    )


def test_matrix_covers_the_refine_transition_artifact() -> None:
    rows = _matrix_rows()
    artifact_rows = [row for row in rows if '## Clarified Request' in row[0]]
    assert len(artifact_rows) == 1, 'the matrix must carry one row for the 2-refine transition artifact'
    assert '--allow-bare-transition' in artifact_rows[0][2], artifact_rows[0]


def test_documented_light_lane_track_persist_is_read_back_as_simple(plan_context) -> None:
    matches = list(_TRACK_PERSIST_RE.finditer(LIGHT_LANE_MD.read_text(encoding='utf-8')))
    assert len(matches) == 1, f'expected exactly one track persist in {LIGHT_LANE_MD}, found {len(matches)}'
    documented_value = matches[0].group('value')

    plan_id = 'test-plan'
    create = run_script(REFERENCES_SCRIPT, 'create', '--plan-id', plan_id, '--branch', f'feature/{plan_id}')
    assert create.success, f'manage-references create failed: {create.stderr}'

    persist = run_script(
        REFERENCES_SCRIPT, 'set', '--plan-id', plan_id, '--field', 'track', '--value', documented_value
    )
    assert persist.success, f'manage-references set --field track failed: {persist.stderr}'
    assert parse_toon(persist.stdout)['status'] == 'success', persist.stdout

    read = run_script(REFERENCES_SCRIPT, 'get', '--plan-id', plan_id, '--field', 'track')
    assert read.success, f'manage-references get --field track failed: {read.stderr}'
    data = parse_toon(read.stdout)
    assert data['status'] == 'success', data
    assert data['value'] == 'simple', data
