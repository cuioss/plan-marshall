# SPDX-License-Identifier: FSL-1.1-ALv2
"""Lockstep guard for the OpenCode variant emitter's level -> model binding.

The OpenCode variant emitter reuses the Claude target's ``LEVEL_TABLE`` and
``ALIAS_GATED_EFFORTS`` (imported, not copied) so the ordinal
level -> (model alias, effort) binding can never drift between targets. These
tests lock that reuse in place and assert the OpenCode-specific half of the
contract: every alias resolves through ``mapping.json::model_map`` to a
concrete ``anthropic/<id>`` model string, and the alias-capability gate lines
up with the ``supports_effort`` arrays the OpenCode adapter ships.

Companion to ``test/marketplace/targets/claude/test_level_table_lockstep.py``:
that file binds ``LEVEL_TABLE`` to ``effort-levels.md``; this one binds it to
the OpenCode model resolution + effort passthrough.
"""

from __future__ import annotations

import json
from pathlib import Path

from marketplace.targets.claude import variant_emitter as claude_ve
from marketplace.targets.opencode import variant_emitter as opencode_ve
from marketplace.targets.opencode.frontmatter import OPENCODE_MODEL_PREFIX

REPO_ROOT = Path(__file__).resolve().parents[4]
MAPPING_JSON = REPO_ROOT / 'marketplace/targets/opencode/mapping.json'


def _model_map() -> dict[str, dict]:
    return json.loads(MAPPING_JSON.read_text(encoding='utf-8'))['model_map']


def test_opencode_reuses_claude_level_tables() -> None:
    """The two targets share one table object — no copy, no drift possible."""
    assert opencode_ve.LEVEL_TABLE is claude_ve.LEVEL_TABLE, (
        'OpenCode variant emitter must import LEVEL_TABLE from the Claude target, '
        'not copy it — a copy would let the two tables drift silently'
    )
    assert opencode_ve.ALIAS_GATED_EFFORTS is claude_ve.ALIAS_GATED_EFFORTS, (
        'OpenCode variant emitter must import ALIAS_GATED_EFFORTS from the Claude '
        'target, not copy it'
    )


def test_level_table_aliases_resolve_to_anthropic_ids() -> None:
    """Every level alias resolves through model_map to a concrete anthropic/<id>."""
    model_map = _model_map()
    for level, binding in opencode_ve.LEVEL_TABLE.items():
        alias = binding['model']
        assert alias in model_map, (
            f'{level}: alias {alias!r} missing from mapping.json model_map'
        )
        entry = model_map[alias]
        assert 'id' in entry and entry['id'], (
            f'{level}: model_map[{alias!r}] has no non-empty id'
        )
        expected = f'{OPENCODE_MODEL_PREFIX}{entry["id"]}'
        assert expected.startswith('anthropic/'), (
            f'{level}: resolved model {expected!r} is not anthropic/-prefixed'
        )


def test_gated_efforts_are_advertised_by_their_alias() -> None:
    """A gated (xhigh/max) level is only emittable when its alias advertises it.

    The shipped mapping.json must advertise every gated effort the table asks
    for — otherwise the top tiers would always be skipped, which the level
    palette does not intend.
    """
    model_map = _model_map()
    for level, binding in opencode_ve.LEVEL_TABLE.items():
        effort = binding['effort']
        if effort not in opencode_ve.ALIAS_GATED_EFFORTS:
            continue
        supported = model_map[binding['model']]['supports_effort']
        assert effort in supported, (
            f'{level}: gated effort {effort!r} not advertised by '
            f'{binding["model"]}.supports_effort {supported} — the top tier '
            f'would always be skipped on OpenCode'
        )


def test_ungated_efforts_are_universally_supported() -> None:
    """Non-gated efforts must be advertised by their alias.

    The emitter never guards these, so a mapping.json regression here would
    emit an unusable passthrough (an effort the alias does not accept)."""
    model_map = _model_map()
    for level, binding in opencode_ve.LEVEL_TABLE.items():
        effort = binding['effort']
        if effort is None or effort in opencode_ve.ALIAS_GATED_EFFORTS:
            continue
        supported = model_map[binding['model']]['supports_effort']
        assert effort in supported, (
            f'{level}: ungated effort {effort!r} not in '
            f'{binding["model"]}.supports_effort {supported} — either gate it '
            f'in ALIAS_GATED_EFFORTS or fix mapping.json'
        )
