# SPDX-License-Identifier: FSL-1.1-ALv2
"""Lockstep guard for the OpenCode variant emitter's level palette.

The OpenCode variant emitter reuses the Claude target's ``LEVEL_TABLE``
(imported, not copied) so the ordinal level *names* can never drift between
targets. OpenCode's variants are inherit-only (no ``model:`` /
``reasoningEffort:``) unless the emit path is handed a materialized per-level
pin map — a pinned level then carries its configured ``model:``, resolved
through the SAME ``mapping.json::model_map`` seam that an inherited
``model:`` declaration uses. The alias-capability gate
(``ALIAS_GATED_EFFORTS``, ``supports_effort``) stays a Claude-only concern:
OpenCode consumes materialized pins as-is. These tests lock the shared
palette in place and assert the one OpenCode coherence fact the pin-aware
policy rests on: every level alias resolves through ``mapping.json::model_map``
to a concrete ``anthropic/<id>`` model string, and a pinned alias variant is
rendered with exactly that string (never the raw alias).

Companion to ``test/marketplace/targets/claude/test_level_table_lockstep.py``:
that file binds ``LEVEL_TABLE`` to ``effort-levels.md`` and guards the gating
data (``ALIAS_GATED_EFFORTS`` vs ``supports_effort``); this one binds the
palette to the OpenCode adapter.
"""

from __future__ import annotations

import json

from conftest import PROJECT_ROOT
from marketplace.targets.claude import variant_emitter as claude_ve
from marketplace.targets.opencode import variant_emitter as opencode_ve
from marketplace.targets.opencode.frontmatter import (
    OPENCODE_MODEL_PREFIX,
    load_mapping,
    load_rules,
    parse_frontmatter,
)

REPO_ROOT = PROJECT_ROOT
MAPPING_JSON = REPO_ROOT / 'marketplace/targets/opencode/mapping.json'


def _model_map() -> dict[str, dict]:
    data = json.loads(MAPPING_JSON.read_text(encoding='utf-8'))
    model_map: dict[str, dict] = data['model_map']
    return model_map


def test_opencode_reuses_claude_level_table() -> None:
    """Both targets share one table object — no copy, no drift possible."""
    assert opencode_ve.LEVEL_TABLE is claude_ve.LEVEL_TABLE, (
        'OpenCode variant emitter must import LEVEL_TABLE from the Claude target, '
        'not copy it — a copy would let the two palettes drift silently'
    )


def test_level_table_aliases_resolve_to_anthropic_ids() -> None:
    """Every level alias resolves through model_map to a concrete anthropic/<id>."""
    model_map = _model_map()
    for level, binding in opencode_ve.LEVEL_TABLE.items():
        alias = binding['model']
        assert alias in model_map, f'{level}: alias {alias!r} missing from mapping.json model_map'
        entry = model_map[alias]
        assert 'id' in entry and entry['id'], f'{level}: model_map[{alias!r}] has no non-empty id'
        expected = f'{OPENCODE_MODEL_PREFIX}{entry["id"]}'
        assert expected.startswith('anthropic/'), f'{level}: resolved model {expected!r} is not anthropic/-prefixed'


def test_pinned_alias_renders_resolved_id_never_raw_alias() -> None:
    """A pinned alias variant carries the model_map-resolved anthropic/<id> string.

    The pin-aware OpenCode policy resolves a per-level variant pin through the
    identical ``mapping.json::model_map`` seam an inherited ``model:``
    declaration uses, so a pin is never emitted as its raw alias and never
    resolved twice. This locks the two coherence facts together: the palette
    binding (above) and the pin renderer.
    """
    model_map = _model_map()
    rules = load_rules(MAPPING_JSON.parent)
    mapping = load_mapping(MAPPING_JSON.parent)
    fm, _ = _role_agent_source_body()
    for level, binding in opencode_ve.LEVEL_TABLE.items():
        alias = binding['model']
        block = opencode_ve.render_variant_frontmatter(
            fm,
            level,
            mapping,
            rules,
            source_label='agents/demo/execution-context.md',
            level_pin=alias,
        )
        resolved = f'{OPENCODE_MODEL_PREFIX}{model_map[alias]["id"]}'
        assert f'model: {resolved}' in block, (
            f'{level}: pinned alias {alias!r} must render as {resolved!r}, never the raw alias'
        )


def _role_agent_source_body() -> tuple[dict[str, str], str]:
    content = f'---\ndescription: placeholder\ntools: Read\nimplements: {opencode_ve.EXTENSION_POINT}\n---\nbody\n'
    return parse_frontmatter(content)
