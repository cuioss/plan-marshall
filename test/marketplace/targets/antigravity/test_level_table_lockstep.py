# SPDX-License-Identifier: FSL-1.1-ALv2
"""Lockstep guard for the Antigravity variant emitter's level palette."""

from __future__ import annotations

import json

from conftest import PROJECT_ROOT
from marketplace.targets.antigravity import variant_emitter as antigravity_ve
from marketplace.targets.antigravity.frontmatter import (
    load_mapping,
    load_rules,
    parse_frontmatter,
)
from marketplace.targets.claude import variant_emitter as claude_ve

REPO_ROOT = PROJECT_ROOT
MAPPING_JSON = REPO_ROOT / 'marketplace/targets/antigravity/mapping.json'


def _model_map() -> dict[str, dict]:
    data = json.loads(MAPPING_JSON.read_text(encoding='utf-8'))
    model_map: dict[str, dict] = data['model_map']
    return model_map


def test_antigravity_reuses_claude_level_table() -> None:
    """Both targets share one table object — no copy, no drift possible."""
    assert antigravity_ve.LEVEL_TABLE is claude_ve.LEVEL_TABLE, (
        'Antigravity variant emitter must import LEVEL_TABLE from the Claude target, '
        'not copy it — a copy would let the two palettes drift silently'
    )


def test_level_table_aliases_resolve_to_antigravity_models() -> None:
    """Every level alias resolves through model_map to a known Antigravity model."""
    model_map = _model_map()
    valid_models = {'pro', 'flash', 'flash_lite', 'inherit'}
    for level, binding in antigravity_ve.LEVEL_TABLE.items():
        alias = binding['model']
        assert alias in model_map, f'Level {level} alias {alias!r} missing from model_map'
        target_id = model_map[alias]['id']
        assert target_id in valid_models, f'Level {level} target id {target_id!r} not in valid Antigravity models'
