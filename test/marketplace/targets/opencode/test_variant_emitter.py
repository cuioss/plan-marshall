# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the OpenCode variant emitter (dynamic-level-executor variants).

A role-eligible canonical (declaring ``implements:
ext-point-dynamic-level-executor``) emits one ``{base}-level-N`` file per
ordinal level. Every OpenCode variant is an **inherit-only** copy of the
canonical: it carries no ``model:`` and no ``reasoningEffort:``, so each
level variant dispatches on the session model. Non-eligible agents emit a
single file as before.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.claude.variant_emitter import EXTENSION_POINT
from marketplace.targets.opencode.emitter import emit_bundles
from marketplace.targets.opencode.frontmatter import load_mapping, load_rules, parse_frontmatter
from marketplace.targets.opencode.variant_emitter import (
    OpenCodeCanonicalValidationError,
    emit_agent_variants,
    is_role_eligible,
    render_variant_frontmatter,
    selected_levels,
)

CONFIG_DIR = PROJECT_ROOT / 'marketplace' / 'targets' / 'opencode'
ALL_LEVELS = [f'level-{n}' for n in range(1, 8)]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _role_agent_source(*, levels: str | None = None) -> str:
    lines = [
        '---',
        'name: execution-context',
        # Quoted: an unquoted `: ` makes this frontmatter invalid YAML, which
        # the real agent avoids with a `|` block scalar.
        "description: 'Generic dispatcher for every plan-marshall Task: invocation.'",
        'tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Skill',
        'forwards_tool_capabilities: true',
        f'implements: {EXTENSION_POINT}',
    ]
    if levels is not None:
        lines.append(f'levels: {levels}')
    lines += ['---', '', '# Execution Context', '', 'Body text.', '']
    return '\n'.join(lines)


@pytest.fixture()
def role_bundle(tmp_path: Path) -> Path:
    """Marketplace tree with one bundle whose agent opts into level variants."""
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'demo'
    _write(
        bundle / '.claude-plugin' / 'plugin.json',
        json.dumps({'name': 'demo', 'agents': ['./agents/execution-context.md']}) + '\n',
    )
    _write(bundle / 'agents' / 'execution-context.md', _role_agent_source())
    return marketplace


def _fm_of(path: Path) -> dict[str, str]:
    fm, _ = parse_frontmatter(path.read_text(encoding='utf-8'))
    return fm


# --------------------------------------------------------------------------
# End-to-end emit through emit_bundles
# --------------------------------------------------------------------------


def test_emit_writes_canonical_plus_seven_variants(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR)
    agent_dir = out / 'agent'
    assert (agent_dir / 'execution-context.md').is_file()
    for level in ALL_LEVELS:
        assert (agent_dir / f'execution-context-{level}.md').is_file(), f'missing variant for {level}'


def test_canonical_carries_no_model_or_effort(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR)
    fm = _fm_of(out / 'agent' / 'execution-context.md')
    assert 'model' not in fm
    assert 'reasoningEffort' not in fm
    # The canonical keeps its subagent mode + permission block.
    assert fm.get('mode') == 'subagent'


def test_variants_carry_no_pinned_model(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR)
    agent_dir = out / 'agent'
    for level in ALL_LEVELS:
        fm = _fm_of(agent_dir / f'execution-context-{level}.md')
        assert 'model' not in fm, f'{level}: variant must not pin a model'


def test_variants_carry_no_effort_key(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR)
    agent_dir = out / 'agent'
    for level in ALL_LEVELS:
        fm = _fm_of(agent_dir / f'execution-context-{level}.md')
        assert 'reasoningEffort' not in fm, f'{level}: variant must not carry an effort key'


def test_all_level_variants_are_inherit_copies_of_canonical(role_bundle: Path, tmp_path: Path) -> None:
    """Every level variant is frontmatter-identical to the canonical (inherit)."""
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR)
    agent_dir = out / 'agent'
    canon_fm = _fm_of(agent_dir / 'execution-context.md')
    for level in ALL_LEVELS:
        fm = _fm_of(agent_dir / f'execution-context-{level}.md')
        assert fm == canon_fm, f'{level}: variant frontmatter must equal the canonical (inherit)'


def test_variant_body_matches_canonical_body(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR)
    agent_dir = out / 'agent'
    _, canon_body = parse_frontmatter((agent_dir / 'execution-context.md').read_text(encoding='utf-8'))
    _, var_body = parse_frontmatter((agent_dir / 'execution-context-level-4.md').read_text(encoding='utf-8'))
    assert canon_body == var_body


def test_opencode_json_indexes_variants(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR)
    config = json.loads((out / 'opencode.json').read_text(encoding='utf-8'))
    agents = config['agent']
    assert 'execution-context' in agents
    for level in ALL_LEVELS:
        assert f'execution-context-{level}' in agents


def test_levels_subset_limits_emitted_variants(tmp_path: Path) -> None:
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'demo'
    _write(
        bundle / '.claude-plugin' / 'plugin.json',
        json.dumps({'name': 'demo', 'agents': ['./agents/execution-context.md']}) + '\n',
    )
    _write(
        bundle / 'agents' / 'execution-context.md',
        _role_agent_source(levels='[level-1, level-3]'),
    )
    out = tmp_path / 'out'
    emit_bundles(marketplace, out, CONFIG_DIR)
    agent_dir = out / 'agent'
    assert (agent_dir / 'execution-context-level-1.md').is_file()
    assert (agent_dir / 'execution-context-level-3.md').is_file()
    assert not (agent_dir / 'execution-context-level-2.md').exists()
    assert not (agent_dir / 'execution-context-level-7.md').exists()


# --------------------------------------------------------------------------
# Unit-level behaviour
# --------------------------------------------------------------------------


def test_non_eligible_agent_emits_no_variants(tmp_path: Path) -> None:
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'demo'
    _write(
        bundle / '.claude-plugin' / 'plugin.json',
        json.dumps({'name': 'demo', 'agents': ['./agents/plain.md']}) + '\n',
    )
    _write(
        bundle / 'agents' / 'plain.md',
        '---\nname: plain\ndescription: a plain agent\ntools: Read\n---\nbody\n',
    )
    out = tmp_path / 'out'
    emit_bundles(marketplace, out, CONFIG_DIR)
    variants = list((out / 'agent').glob('plain-level-*.md'))
    assert variants == []


def test_emit_agent_variants_returns_none_for_non_eligible() -> None:
    fm = {'description': 'x', 'tools': 'Read'}
    assert not is_role_eligible(fm)
    result = emit_agent_variants(
        fm,
        'body',
        'plain',
        Path('/does/not/matter'),
        load_mapping(CONFIG_DIR),
        load_rules(CONFIG_DIR),
        source_label='agents/demo/plain.md',
    )
    assert result is None


def test_validate_canonical_rejects_model(tmp_path: Path) -> None:
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'demo'
    _write(
        bundle / '.claude-plugin' / 'plugin.json',
        json.dumps({'name': 'demo', 'agents': ['./agents/bad.md']}) + '\n',
    )
    _write(
        bundle / 'agents' / 'bad.md',
        f'---\nname: bad\ndescription: x\ntools: Read\nimplements: {EXTENSION_POINT}\nmodel: opus\n---\nbody\n',
    )
    out = tmp_path / 'out'
    with pytest.raises(OpenCodeCanonicalValidationError):
        emit_bundles(marketplace, out, CONFIG_DIR)


def test_all_levels_emit_regardless_of_mapping_capabilities(tmp_path: Path) -> None:
    """The alias-capability gate is Claude-only: OpenCode emits every level."""
    # Custom mapping where opus/fable advertise no xhigh/max — the Claude side
    # would skip level-6/level-7 here; OpenCode must still emit all seven.
    custom_mapping = {
        'tool_permissions': {
            'Read': 'read',
            'Write': 'edit',
            'Edit': 'edit',
            'Glob': 'glob',
            'Grep': 'grep',
            'Bash': 'bash',
            'AskUserQuestion': 'question',
            'Skill': 'skill',
        },
        'model_map': {
            'haiku': {'id': 'claude-haiku-4-5-20251001', 'supports_effort': []},
            'sonnet': {'id': 'claude-sonnet-4-6', 'supports_effort': ['medium', 'high']},
            'opus': {'id': 'claude-opus-4-8', 'supports_effort': ['medium', 'high']},
            'fable': {'id': 'claude-fable-5', 'supports_effort': []},
        },
    }

    fm, _ = parse_frontmatter(_role_agent_source())
    agent_dir = tmp_path / 'agent'
    result = emit_agent_variants(
        fm,
        'body',
        'execution-context',
        agent_dir,
        custom_mapping,
        load_rules(CONFIG_DIR),
        source_label='agents/demo/execution-context.md',
    )
    assert result is not None
    assert result.variants_emitted == ALL_LEVELS
    assert result.variants_skipped == []
    for level in ALL_LEVELS:
        assert (agent_dir / f'execution-context-{level}.md').is_file(), f'missing variant for {level}'


def test_render_variant_frontmatter_shape() -> None:
    fm, _ = parse_frontmatter(_role_agent_source())
    block = render_variant_frontmatter(
        fm,
        'level-6',
        load_mapping(CONFIG_DIR),
        load_rules(CONFIG_DIR),
        source_label='agents/demo/execution-context.md',
    )
    assert block.startswith('---\n')
    assert block.rstrip().endswith('---')
    assert 'mode: subagent' in block
    # Inherit policy: no model / effort pin; implements/levels stripped.
    assert 'model:' not in block
    assert 'reasoningEffort' not in block
    assert 'implements' not in block
    assert 'permission:' in block


def test_selected_levels_defaults_to_all() -> None:
    fm, _ = parse_frontmatter(_role_agent_source())
    assert selected_levels(fm) == ALL_LEVELS
