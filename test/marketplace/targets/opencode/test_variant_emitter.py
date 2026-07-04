# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the OpenCode variant emitter (dynamic-level-executor variants).

Mirrors the intent of the Claude target's variant-emission tests: a
role-eligible canonical (declaring ``implements:
ext-point-dynamic-level-executor``) emits one ``{base}-level-N`` file per
ordinal level with a concrete, provider-qualified model and — for tiers that
differ only by effort — a ``reasoningEffort`` passthrough that keeps them
distinct. Non-eligible agents emit a single file as before.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

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

CONFIG_DIR = Path(__file__).resolve().parents[4] / 'marketplace' / 'targets' / 'opencode'
ALL_LEVELS = [f'level-{n}' for n in range(1, 8)]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _role_agent_source(*, levels: str | None = None) -> str:
    lines = [
        '---',
        'name: execution-context',
        'description: Generic dispatcher for every plan-marshall Task: invocation.',
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
        assert (agent_dir / f'execution-context-{level}.md').is_file(), (
            f'missing variant for {level}'
        )


def test_canonical_carries_no_model_or_effort(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR)
    fm = _fm_of(out / 'agent' / 'execution-context.md')
    assert 'model' not in fm
    assert 'reasoningEffort' not in fm
    # The canonical keeps its subagent mode + permission block.
    assert fm.get('mode') == 'subagent'


def test_variant_models_resolve_to_anthropic_ids(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR)
    agent_dir = out / 'agent'
    expected = {
        'level-1': 'anthropic/claude-haiku-4-5-20251001',
        'level-2': 'anthropic/claude-sonnet-4-6',
        'level-3': 'anthropic/claude-sonnet-4-6',
        'level-4': 'anthropic/claude-opus-4-8',
        'level-5': 'anthropic/claude-opus-4-8',
        'level-6': 'anthropic/claude-opus-4-8',
        'level-7': 'anthropic/claude-fable-5',
    }
    for level, model in expected.items():
        fm = _fm_of(agent_dir / f'execution-context-{level}.md')
        assert fm.get('model') == model, f'{level}: model mismatch'


def test_variant_effort_passthrough_per_level(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR)
    agent_dir = out / 'agent'
    # level-1 (haiku) carries no effort key; the rest carry their keyword.
    expected = {
        'level-1': None,
        'level-2': 'medium',
        'level-3': 'high',
        'level-4': 'medium',
        'level-5': 'high',
        'level-6': 'xhigh',
        'level-7': 'max',
    }
    for level, effort in expected.items():
        fm = _fm_of(agent_dir / f'execution-context-{level}.md')
        assert fm.get('reasoningEffort') == effort, f'{level}: effort mismatch'


def test_same_model_tiers_stay_distinct(role_bundle: Path, tmp_path: Path) -> None:
    """The effort passthrough keeps same-model tiers from collapsing to identical files."""
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR)
    agent_dir = out / 'agent'
    l2 = (agent_dir / 'execution-context-level-2.md').read_text(encoding='utf-8')
    l3 = (agent_dir / 'execution-context-level-3.md').read_text(encoding='utf-8')
    l4 = (agent_dir / 'execution-context-level-4.md').read_text(encoding='utf-8')
    l5 = (agent_dir / 'execution-context-level-5.md').read_text(encoding='utf-8')
    assert l2 != l3, 'level-2 and level-3 (both sonnet) collapsed to identical files'
    assert l4 != l5, 'level-4 and level-5 (both opus) collapsed to identical files'


def test_variant_body_matches_canonical_body(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR)
    agent_dir = out / 'agent'
    _, canon_body = parse_frontmatter(
        (agent_dir / 'execution-context.md').read_text(encoding='utf-8')
    )
    _, var_body = parse_frontmatter(
        (agent_dir / 'execution-context-level-4.md').read_text(encoding='utf-8')
    )
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
        mapping_path=CONFIG_DIR / 'mapping.json',
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
        '---\nname: bad\ndescription: x\ntools: Read\n'
        f'implements: {EXTENSION_POINT}\nmodel: opus\n---\nbody\n',
    )
    out = tmp_path / 'out'
    with pytest.raises(OpenCodeCanonicalValidationError):
        emit_bundles(marketplace, out, CONFIG_DIR)


def test_gated_effort_skipped_when_alias_lacks_support(tmp_path: Path) -> None:
    """When mapping.json's alias does not advertise a gated effort, that level is skipped."""
    # Custom mapping where opus lacks xhigh -> level-6 must be skipped, but
    # level-4/level-5 (opus medium/high, ungated) still emit.
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
            'fable': {
                'id': 'claude-fable-5',
                'supports_effort': ['medium', 'high', 'xhigh', 'max'],
            },
        },
    }
    mapping_path = tmp_path / 'mapping.json'
    mapping_path.write_text(json.dumps(custom_mapping), encoding='utf-8')

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
        mapping_path=mapping_path,
    )
    assert result is not None
    assert 'level-6' not in result.variants_emitted
    assert 'level-6' in [lvl for lvl, _ in result.variants_skipped]
    assert 'level-4' in result.variants_emitted
    assert 'level-5' in result.variants_emitted
    assert not (agent_dir / 'execution-context-level-6.md').exists()


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
    assert 'model: anthropic/claude-opus-4-8' in block
    assert 'reasoningEffort: xhigh' in block
    # implements/levels are stripped; permission block present.
    assert 'implements' not in block
    assert 'permission:' in block


def test_selected_levels_defaults_to_all() -> None:
    fm, _ = parse_frontmatter(_role_agent_source())
    assert selected_levels(fm) == ALL_LEVELS
