# SPDX-License-Identifier: FSL-1.1-ALv2
"""Lockstep guard for the OpenCode variant emitter's level palette.

The OpenCode variant emitter reuses the Claude target's ``LEVEL_TABLE``
(imported, not copied) so the ordinal level *names* can never drift between
targets. It does NOT consume the model/effort binding or the alias-capability
gate: OpenCode emits every level variant as an inherit-only copy (no
``model:`` / ``reasoningEffort:``), so ``ALIAS_GATED_EFFORTS`` and
``supports_effort`` are Claude-only concerns. These tests lock the shared
palette in place and assert the one OpenCode-specific coherence fact that
survives the inherit-only policy: every level alias still resolves through
``mapping.json::model_map`` to a concrete ``anthropic/<id>`` model string
(the resolution path the OpenCode frontmatter transformer uses for skill /
user-invocable ``model:`` declarations).

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
from marketplace.targets.opencode.frontmatter import OPENCODE_MODEL_PREFIX

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
