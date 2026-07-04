# SPDX-License-Identifier: FSL-1.1-ALv2
"""Lockstep guard for the level -> (model, effort) binding.

``variant_emitter.LEVEL_TABLE`` carries a comment that it must be kept
in lock-step with ``effort-levels.md``, and ``ALIAS_GATED_EFFORTS``
mirrors the gating notes in the same document plus the
``supports_effort`` arrays in ``mapping.json``. Until now that binding
was comment-discipline only; these tests make a silent divergence a
build failure.

Covered bindings:

- effort-levels.md "Level Table" rows == ``LEVEL_TABLE`` exactly.
- Levels marked "Alias-capability-gated" in effort-levels.md carry
  exactly the efforts in ``ALIAS_GATED_EFFORTS``.
- Every ``LEVEL_TABLE`` alias resolves in the shipped
  ``mapping.json::model_map``; every non-gated effort is advertised by
  its alias's ``supports_effort`` (the "universally available" claim).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from marketplace.targets.claude.variant_emitter import (
    ALIAS_GATED_EFFORTS,
    LEVEL_TABLE,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
EFFORT_LEVELS_MD = (
    REPO_ROOT
    / 'marketplace/bundles/plan-marshall/skills/plan-marshall/standards/effort-levels.md'
)
MAPPING_JSON = REPO_ROOT / 'marketplace/targets/opencode/mapping.json'

_ROW_RE = re.compile(
    r'^\|\s*`(?P<level>level-\d+)`\s*'
    r'\|\s*(?P<model>`[^`]+`|\([^)]*\))\s*'
    r'\|\s*(?P<effort>`[^`]+`|\([^)]*\))\s*'
    r'\|\s*(?P<notes>.*)\|\s*$'
)


def _parse_doc_table() -> dict[str, dict[str, str | None]]:
    """Parse the Level Table rows of effort-levels.md into LEVEL_TABLE shape."""
    table: dict[str, dict[str, str | None]] = {}
    for line in EFFORT_LEVELS_MD.read_text(encoding='utf-8').splitlines():
        match = _ROW_RE.match(line.strip())
        if not match:
            continue
        model = match.group('model')
        effort = match.group('effort')
        table[match.group('level')] = {
            'model': model.strip('`') if model.startswith('`') else None,
            'effort': effort.strip('`') if effort.startswith('`') else None,
            '_notes': match.group('notes'),
        }
    return table


def test_doc_table_parses_all_levels() -> None:
    doc = _parse_doc_table()
    assert set(doc) == set(LEVEL_TABLE), (
        f'effort-levels.md Level Table rows {sorted(doc)} do not match '
        f'LEVEL_TABLE keys {sorted(LEVEL_TABLE)} — keep both in lock-step'
    )


def test_level_table_matches_effort_levels_md() -> None:
    doc = _parse_doc_table()
    for level, binding in LEVEL_TABLE.items():
        doc_row = doc[level]
        assert doc_row['model'] == binding['model'], (
            f'{level}: model drift — variant_emitter.LEVEL_TABLE says '
            f'{binding["model"]!r}, effort-levels.md says {doc_row["model"]!r}'
        )
        assert doc_row['effort'] == binding['effort'], (
            f'{level}: effort drift — variant_emitter.LEVEL_TABLE says '
            f'{binding["effort"]!r}, effort-levels.md says {doc_row["effort"]!r}'
        )


def test_alias_gated_efforts_match_doc_gating_notes() -> None:
    doc = _parse_doc_table()
    doc_gated_efforts = {
        row['effort']
        for row in doc.values()
        if 'alias-capability-gated' in str(row['_notes']).lower()
    }
    assert doc_gated_efforts == set(ALIAS_GATED_EFFORTS), (
        f'effort-levels.md marks {sorted(str(e) for e in doc_gated_efforts)} as '
        f'alias-capability-gated; ALIAS_GATED_EFFORTS is '
        f'{sorted(ALIAS_GATED_EFFORTS)} — keep both in lock-step'
    )


def test_level_table_aliases_resolve_in_mapping_json() -> None:
    model_map = json.loads(MAPPING_JSON.read_text(encoding='utf-8'))['model_map']
    for level, binding in LEVEL_TABLE.items():
        alias = binding['model']
        assert alias in model_map, (
            f'{level}: alias {alias!r} missing from mapping.json model_map'
        )


def test_ungated_efforts_are_universally_supported() -> None:
    """Non-gated efforts must be advertised by their alias — the emitter never
    guards them, so a mapping.json regression here would emit unusable variants."""
    model_map = json.loads(MAPPING_JSON.read_text(encoding='utf-8'))['model_map']
    for level, binding in LEVEL_TABLE.items():
        effort = binding['effort']
        if effort is None or effort in ALIAS_GATED_EFFORTS:
            continue
        supported = model_map[binding['model']]['supports_effort']
        assert effort in supported, (
            f'{level}: ungated effort {effort!r} not in '
            f'{binding["model"]}.supports_effort {supported} — either gate it '
            f'in ALIAS_GATED_EFFORTS or fix mapping.json'
        )
