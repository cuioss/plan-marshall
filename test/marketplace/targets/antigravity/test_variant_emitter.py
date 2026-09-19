# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the Antigravity variant emitter (dynamic-level-executor variants)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.antigravity.emitter import emit_bundles
from marketplace.targets.antigravity.frontmatter import (
    load_mapping,
    load_rules,
    parse_frontmatter,
)
from marketplace.targets.antigravity.variant_emitter import (
    AntigravityCanonicalValidationError,
    emit_agent_variants,
    is_role_eligible,
    render_variant_frontmatter,
    selected_levels,
)
from marketplace.targets.claude.variant_emitter import EXTENSION_POINT, LEVEL_TABLE

CONFIG_DIR = PROJECT_ROOT / 'marketplace' / 'targets' / 'antigravity'
ALL_LEVELS = list(LEVEL_TABLE)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _role_agent_source(*, levels: str | None = None) -> str:
    lines = [
        '---',
        'name: execution-context',
        "description: 'Generic dispatcher for every plan-marshall Task: invocation.'",
        'tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Skill',
        f'implements: {EXTENSION_POINT}',
    ]
    if levels is not None:
        lines.append(f'levels: {levels}')
    lines += ['---', '', '# Execution Context', '', 'Body text.', '']
    return '\n'.join(lines)


@pytest.fixture()
def role_bundle(tmp_path: Path) -> Path:
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'demo'
    _write(
        bundle / '.claude-plugin' / 'plugin.json',
        json.dumps(
            {
                'name': 'demo',
                'version': '0.0.1',
                'description': 'Demo bundle',
                'agents': ['./agents/execution-context.md'],
            }
        ),
    )
    _write(bundle / 'agents' / 'execution-context.md', _role_agent_source())
    return marketplace


def test_is_role_eligible():
    assert is_role_eligible({'implements': EXTENSION_POINT}) is True
    assert is_role_eligible({'implements': 'other'}) is False
    assert is_role_eligible({}) is False


def test_selected_levels_default():
    assert selected_levels({}) == ALL_LEVELS


def test_selected_levels_filtered():
    assert selected_levels({'levels': 'level-1, level-3'}) == ['level-1', 'level-3']


def test_validate_canonical_raises_on_model():
    fm, _ = parse_frontmatter(f'---\nname: ec\ndescription: d\nimplements: {EXTENSION_POINT}\nmodel: opus\n---\nbody')
    with pytest.raises(AntigravityCanonicalValidationError):
        emit_agent_variants(fm, 'body', 'ec', Path('/tmp'), {}, {}, source_label='test')


def test_render_variant_frontmatter_unpinned(tmp_path: Path):
    mapping = load_mapping(CONFIG_DIR)
    rules = load_rules(CONFIG_DIR)
    fm = {
        'name': 'ec',
        'description': 'dispatcher',
        'tools': 'Read, Write',
        'implements': EXTENSION_POINT,
    }
    rendered = render_variant_frontmatter(fm, 'level-1', mapping, rules, source_label='test', level_pin='inherit')
    assert 'implements' not in rendered
    assert 'mode: subagent' in rendered
    assert 'model:' not in rendered
    assert 'effort:' not in rendered


def test_render_variant_frontmatter_pinned(tmp_path: Path):
    mapping = load_mapping(CONFIG_DIR)
    rules = load_rules(CONFIG_DIR)
    fm = {
        'name': 'ec',
        'description': 'dispatcher',
        'tools': 'Read, Write',
        'implements': EXTENSION_POINT,
    }
    rendered = render_variant_frontmatter(
        fm, 'level-7', mapping, rules, source_label='test', level_pin={'model': 'pro', 'effort': 'high'}
    )
    assert 'model: pro' in rendered
    assert 'effort: high' in rendered


def test_emit_agent_variants_end_to_end(role_bundle: Path, tmp_path: Path):
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR)

    agents_dir = out / 'agents'
    assert (agents_dir / 'execution-context.md').is_file()
    for level in ALL_LEVELS:
        variant = agents_dir / f'execution-context-{level}.md'
        assert variant.is_file(), f'expected variant {variant}'
        content = variant.read_text(encoding='utf-8')
        assert 'mode: subagent' in content

    # Check Option 1 ladder defaults baked into emitted files
    l1_content = (agents_dir / 'execution-context-level-1.md').read_text(encoding='utf-8')
    assert 'model: flash' in l1_content
    assert 'effort: low' in l1_content

    l5_content = (agents_dir / 'execution-context-level-5.md').read_text(encoding='utf-8')
    assert 'model: flash' in l5_content
    assert 'effort: high' in l5_content

    l6_content = (agents_dir / 'execution-context-level-6.md').read_text(encoding='utf-8')
    assert 'model: pro' in l6_content
    assert 'effort: low' in l6_content

    l7_content = (agents_dir / 'execution-context-level-7.md').read_text(encoding='utf-8')
    assert 'model: pro' in l7_content
    assert 'effort: high' in l7_content


def test_emit_agent_variants_with_pins(role_bundle: Path, tmp_path: Path):
    out = tmp_path / 'out'
    pins: dict[str, Any] = {
        'level-1': {'model': 'flash', 'effort': 'high'},
        'level-4': 'inherit',
    }
    emit_bundles(role_bundle, out, CONFIG_DIR, level_pins=pins)

    agents_dir = out / 'agents'
    l1_content = (agents_dir / 'execution-context-level-1.md').read_text(encoding='utf-8')
    assert 'model: flash' in l1_content
    assert 'effort: high' in l1_content

    l4_content = (agents_dir / 'execution-context-level-4.md').read_text(encoding='utf-8')
    assert 'model:' not in l4_content
    assert 'effort:' not in l4_content


def test_emit_agent_variants_unknown_pin_key_raises(role_bundle: Path, tmp_path: Path):
    out = tmp_path / 'out'
    with pytest.raises(ValueError, match='unknown level key'):
        emit_bundles(role_bundle, out, CONFIG_DIR, level_pins={'level-99': 'pro'})
