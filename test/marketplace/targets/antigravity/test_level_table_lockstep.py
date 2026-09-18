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


def test_antigravity_palette_matches_claude() -> None:
    """Both targets share the identical level palette — no drift possible."""
    assert set(antigravity_ve.DEFAULT_LADDER.keys()) == set(claude_ve.LEVEL_TABLE.keys()), (
        'Antigravity DEFAULT_LADDER must have the exact same level keys as Claude LEVEL_TABLE'
    )


def test_level_table_resolves_to_valid_antigravity_models_and_efforts() -> None:
    """Every level in DEFAULT_LADDER resolves to a valid Antigravity model and effort."""
    model_map = _model_map()
    valid_models = {'pro', 'flash', 'inherit'}
    for level, binding in antigravity_ve.DEFAULT_LADDER.items():
        model = binding['model']
        effort = binding['effort']
        assert model in model_map, f'Level {level} model {model!r} missing from model_map'
        target_id = model_map[model]['id']
        assert target_id in valid_models, f'Level {level} target id {target_id!r} not in valid Antigravity models'
        if effort is not None and effort != 'inherit':
            supports = model_map[model].get('supports_effort', [])
            assert effort in supports, (
                f'Level {level} specifies effort {effort!r} which is not supported by {model!r} (supports: {supports})'
            )


def test_antigravity_option_1_ladder_exact_specification() -> None:
    """Validate the exact Option 1 ladder distribution for Antigravity."""
    expected = {
        'level-1': {'model': 'flash', 'effort': 'low'},
        'level-2': {'model': 'flash', 'effort': 'low'},
        'level-3': {'model': 'flash', 'effort': 'medium'},
        'level-4': {'model': 'flash', 'effort': 'medium'},
        'level-5': {'model': 'flash', 'effort': 'high'},
        'level-6': {'model': 'pro', 'effort': 'low'},
        'level-7': {'model': 'pro', 'effort': 'high'},
    }
    assert antigravity_ve.DEFAULT_LADDER == expected
