# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the OpenCode variant emitter (dynamic-level-executor variants).

A role-eligible canonical (declaring ``implements:
ext-point-dynamic-level-executor``) emits one ``{base}-level-N`` file per
ordinal level. Without a pin map every OpenCode variant is an **inherit-only**
copy of the canonical: it carries no ``model:`` and no ``reasoningEffort:``,
so each level variant dispatches on the session model.

When the emit path is handed a materialized pin map (the ``{level: 'inherit'
| model-reference}`` output of ``effort_pins.materialize_levels``), a pinned
level carries its configured ``model:`` — an alias resolves via
``mapping.json::model_map`` to a provider-qualified id, an already-qualified
provider/local string passes through unchanged — while unpinned and
``inherit`` levels stay inherit-only, byte-identical to the canonical.
Non-eligible agents emit a single file as before.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.claude.variant_emitter import EXTENSION_POINT, LEVEL_TABLE
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


def test_unpinned_variants_emit_no_model_key(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR)
    agent_dir = out / 'agent'
    for level in ALL_LEVELS:
        fm = _fm_of(agent_dir / f'execution-context-{level}.md')
        assert 'model' not in fm, f'{level}: unpinned variant must not pin a model'


def test_unpinned_variants_emit_no_effort_key(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR)
    agent_dir = out / 'agent'
    for level in ALL_LEVELS:
        fm = _fm_of(agent_dir / f'execution-context-{level}.md')
        assert 'reasoningEffort' not in fm, f'{level}: variant must not carry an effort key'


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


def test_render_variant_frontmatter_unpinned_shape() -> None:
    """An unpinned render keeps the canonical shape and stays model-free."""
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
    # Unpinned render: no model / effort emitted; implements/levels stripped.
    # Pinned renders are covered by the pin-map tests below.
    assert 'model:' not in block
    assert 'reasoningEffort' not in block
    assert 'implements' not in block
    assert 'permission:' in block


def test_selected_levels_defaults_to_all() -> None:
    fm, _ = parse_frontmatter(_role_agent_source())
    assert selected_levels(fm) == ALL_LEVELS


# --------------------------------------------------------------------------
# Materialized pin map (effort_pins.materialize_levels output shape)
# --------------------------------------------------------------------------

PINS = {
    'level-2': 'local-model-a',  # local kind — passes through unchanged
    'level-4': 'zen/route-r',  # provider kind — passes through unchanged
    'level-6': 'opus',  # alias — resolves via model_map
}


def test_pinned_variant_carries_resolved_local_model(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR, level_pins=PINS)
    fm = _fm_of(out / 'agent' / 'execution-context-level-2.md')
    assert fm['model'] == 'local-model-a'


def test_pinned_variant_carries_qualified_provider_passthrough(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR, level_pins=PINS)
    fm = _fm_of(out / 'agent' / 'execution-context-level-4.md')
    assert fm['model'] == 'zen/route-r'


def test_pinned_variant_resolves_alias_through_model_map(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR, level_pins=PINS)
    fm = _fm_of(out / 'agent' / 'execution-context-level-6.md')
    assert fm['model'] == 'anthropic/claude-opus-4-8'


def test_inherit_sentinel_pin_emits_inherit_variant(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR, level_pins={'level-2': 'inherit'})
    fm = _fm_of(out / 'agent' / 'execution-context-level-2.md')
    assert 'model' not in fm


def test_pinned_emit_never_writes_reasoning_effort(role_bundle: Path, tmp_path: Path) -> None:
    """A pin maps a model reference only — no variant ever emits an effort key."""
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR, level_pins=PINS)
    agent_dir = out / 'agent'
    for level in ALL_LEVELS:
        fm = _fm_of(agent_dir / f'execution-context-{level}.md')
        assert 'reasoningEffort' not in fm, f'{level}: no variant may carry an effort key'


def test_unpinned_level_in_pinned_set_is_byte_identical_to_canonical(role_bundle: Path, tmp_path: Path) -> None:
    """Narrow scope: only the exact pinned levels differ; the rest stay inherit."""
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR, level_pins=PINS)
    agent_dir = out / 'agent'
    canonical = (agent_dir / 'execution-context.md').read_bytes()
    for level in ('level-3', 'level-7'):
        assert (agent_dir / f'execution-context-{level}.md').read_bytes() == canonical, (
            f'{level}: unpinned fallback must be byte-identical to canonical'
        )
    assert (agent_dir / 'execution-context-level-2.md').read_bytes() != canonical, (
        'a pinned variant must differ from the canonical'
    )


def test_lower_tier_keeps_own_pin_when_higher_resolves_stronger(role_bundle: Path, tmp_path: Path) -> None:
    """Never-escalate: a lower tier keeps its own pin, not a higher tier's.

    Each level's pin binds strictly to its own key: a lower tier never
    inherits or escalates to a higher tier's stronger model, and an unpinned
    level stays inherit despite pinned neighbours.
    """
    out = tmp_path / 'out'
    model_map = load_mapping(CONFIG_DIR)['model_map']
    lower = LEVEL_TABLE['level-2']['model']
    higher = LEVEL_TABLE['level-6']['model']
    assert lower is not None
    assert higher is not None
    lower_resolved = f'anthropic/{model_map[lower]["id"]}'
    higher_resolved = f'anthropic/{model_map[higher]["id"]}'
    emit_bundles(
        role_bundle,
        out,
        CONFIG_DIR,
        level_pins={'level-2': lower, 'level-6': higher},
    )
    agent_dir = out / 'agent'
    assert _fm_of(agent_dir / 'execution-context-level-2.md')['model'] == lower_resolved
    assert _fm_of(agent_dir / 'execution-context-level-6.md')['model'] == higher_resolved
    canonical = (agent_dir / 'execution-context.md').read_bytes()
    assert (agent_dir / 'execution-context-level-7.md').read_bytes() == canonical, (
        'an unpinned level stays inherit even when neighbours are pinned'
    )


def test_canonical_with_pins_unchanged(role_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_bundles(role_bundle, out, CONFIG_DIR, level_pins=PINS)
    fm = _fm_of(out / 'agent' / 'execution-context.md')
    assert 'model' not in fm
    assert 'reasoningEffort' not in fm


def test_unknown_pin_level_fails_closed(tmp_path: Path) -> None:
    """A pin keyed outside the known palette is rejected, never silently ignored."""
    fm, _ = parse_frontmatter(_role_agent_source())
    with pytest.raises(ValueError, match='unknown level key'):
        emit_agent_variants(
            fm,
            'body',
            'execution-context',
            tmp_path / 'agent',
            load_mapping(CONFIG_DIR),
            load_rules(CONFIG_DIR),
            source_label='agents/demo/execution-context.md',
            level_pins={'level-99': 'opus'},
        )


def test_render_variant_frontmatter_pinned_model_passthrough() -> None:
    """Both entry kinds resolve through the shared _resolve_model seam."""
    fm, _ = parse_frontmatter(_role_agent_source())
    mapping = load_mapping(CONFIG_DIR)
    rules = load_rules(CONFIG_DIR)
    provider_block = render_variant_frontmatter(
        fm,
        'level-4',
        mapping,
        rules,
        source_label='agents/demo/execution-context.md',
        level_pin='zen/route-r',
    )
    assert 'model: zen/route-r' in provider_block
    alias_block = render_variant_frontmatter(
        fm,
        'level-6',
        mapping,
        rules,
        source_label='agents/demo/execution-context.md',
        level_pin='opus',
    )
    assert 'model: anthropic/claude-opus-4-8' in alias_block
    assert 'reasoningEffort' not in alias_block


def test_render_variant_frontmatter_inherit_sentinel_no_model() -> None:
    fm, _ = parse_frontmatter(_role_agent_source())
    block = render_variant_frontmatter(
        fm,
        'level-2',
        load_mapping(CONFIG_DIR),
        load_rules(CONFIG_DIR),
        source_label='agents/demo/execution-context.md',
        level_pin='inherit',
    )
    assert 'model:' not in block
