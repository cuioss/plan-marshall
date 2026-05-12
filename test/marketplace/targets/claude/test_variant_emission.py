"""Tests for the Claude target's variant-emission contract.

Covers ``variant_emitter`` directly plus the integration points in
``emitter.emit_bundle_verbatim`` and ``plugin_json_gen.discover_components``.
The contract pinned here:

- Canonicals declaring ``implements:
  plan-marshall:extension-api/standards/ext-point-dynamic-level-executor``
  emit one variant per level (or per ``levels:`` whitelist) plus the
  canonical no-suffix file with ``implements:`` and ``levels:`` stripped.
- ``model:``/``effort:`` is set on variants per the level table; haiku
  variants omit ``effort:``.
- ``max`` is suppressed when the canonical alias does not accept
  ``effort: xhigh``.
- ``model:``/``effort:`` on a canonical with ``implements:`` is a build
  error.
- Non-eligible agents copy through verbatim (existing emitter contract).
- ``plugin.json`` agents array expands variants.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from marketplace.targets.claude.emitter import emit_bundle_verbatim
from marketplace.targets.claude.plugin_json_gen import discover_components
from marketplace.targets.claude.variant_emitter import (
    LEVEL_TABLE,
    CanonicalValidationError,
    emit_variants_for_agent,
    is_role_eligible,
    parse_frontmatter,
    render_variant,
    selected_levels,
)

EXTENSION_POINT = (
    'plan-marshall:extension-api/standards/ext-point-dynamic-level-executor'
)


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


@pytest.fixture()
def mapping_path(tmp_path: Path) -> Path:
    """Fixture mapping.json with opus xhigh-capable; sonnet/haiku not."""
    path = tmp_path / 'mapping.json'
    path.write_text(
        json.dumps(
            {
                'tool_permissions': {},
                'model_map': {
                    'opus': {
                        'id': 'claude-opus-4-7',
                        'supports_effort': ['medium', 'high', 'xhigh'],
                    },
                    'sonnet': {
                        'id': 'claude-sonnet-4-6',
                        'supports_effort': ['medium', 'high'],
                    },
                    'haiku': {
                        'id': 'claude-haiku-4-5',
                        'supports_effort': [],
                    },
                },
            }
        ),
        encoding='utf-8',
    )
    return path


# =============================================================================
# parse_frontmatter / is_role_eligible / selected_levels
# =============================================================================


def test_parse_frontmatter_extracts_implements_and_levels():
    text = (
        '---\n'
        'name: my-agent\n'
        'tools: Read, Bash\n'
        f'implements: {EXTENSION_POINT}\n'
        'levels: [high, xxhigh]\n'
        '---\n'
        'body content\n'
    )
    fm, body = parse_frontmatter(text)
    assert fm is not None
    assert fm.name == 'my-agent'
    assert fm.implements == EXTENSION_POINT
    assert fm.levels == ['high', 'xxhigh']
    assert body == 'body content\n'


def test_parse_frontmatter_no_block_returns_none():
    fm, body = parse_frontmatter('# no frontmatter here\n')
    assert fm is None
    assert body == '# no frontmatter here\n'


def test_is_role_eligible_true_when_implements_matches():
    text = f'---\nname: x\nimplements: {EXTENSION_POINT}\n---\nbody'
    fm, _ = parse_frontmatter(text)
    assert is_role_eligible(fm)


def test_is_role_eligible_false_when_implements_missing():
    fm, _ = parse_frontmatter('---\nname: x\n---\nbody')
    assert not is_role_eligible(fm)


def test_is_role_eligible_false_for_other_extension_point():
    fm, _ = parse_frontmatter('---\nname: x\nimplements: other:ext-point-foo\n---\nbody')
    assert not is_role_eligible(fm)


def test_selected_levels_default_returns_all_six():
    fm, _ = parse_frontmatter(f'---\nname: x\nimplements: {EXTENSION_POINT}\n---\nbody')
    assert fm is not None
    assert selected_levels(fm) == ['low', 'medium', 'high', 'xhigh', 'xxhigh', 'max']


def test_selected_levels_whitelist_filters():
    fm, _ = parse_frontmatter(
        f'---\nname: x\nimplements: {EXTENSION_POINT}\nlevels: [high, xxhigh]\n---\nbody'
    )
    assert fm is not None
    assert selected_levels(fm) == ['high', 'xxhigh']


# =============================================================================
# render_variant
# =============================================================================


def test_render_variant_haiku_omits_effort():
    fm, body = parse_frontmatter(
        f'---\nname: poc-agent\ntools: Read\nimplements: {EXTENSION_POINT}\n---\nbody\n'
    )
    assert fm is not None
    rendered = render_variant(fm, body, 'low')
    assert 'name: poc-agent-low' in rendered
    assert 'model: haiku' in rendered
    assert 'effort:' not in rendered  # haiku does not accept effort
    assert f'implements: {EXTENSION_POINT}' not in rendered


def test_render_variant_high_sets_model_and_effort():
    fm, body = parse_frontmatter(
        f'---\nname: poc-agent\nimplements: {EXTENSION_POINT}\n---\nbody\n'
    )
    assert fm is not None
    rendered = render_variant(fm, body, 'high')
    assert 'name: poc-agent-high' in rendered
    assert 'model: sonnet' in rendered
    assert 'effort: high' in rendered


def test_render_variant_xxhigh_uses_opus_high():
    """`xxhigh` resolves to `(opus, high)` under the rebound palette."""
    fm, body = parse_frontmatter(
        f'---\nname: poc-agent\nimplements: {EXTENSION_POINT}\n---\nbody\n'
    )
    assert fm is not None
    rendered = render_variant(fm, body, 'xxhigh')
    assert 'model: opus' in rendered
    assert 'effort: high' in rendered


def test_render_variant_xhigh_uses_opus_medium():
    """`xhigh` resolves to `(opus, medium)` under the rebound palette."""
    fm, body = parse_frontmatter(
        f'---\nname: poc-agent\nimplements: {EXTENSION_POINT}\n---\nbody\n'
    )
    assert fm is not None
    rendered = render_variant(fm, body, 'xhigh')
    assert 'model: opus' in rendered
    assert 'effort: medium' in rendered


def test_render_variant_max_uses_opus_xhigh():
    """`max` resolves to `(opus, xhigh)` — Opus-4.7-only top tier."""
    fm, body = parse_frontmatter(
        f'---\nname: poc-agent\nimplements: {EXTENSION_POINT}\n---\nbody\n'
    )
    assert fm is not None
    rendered = render_variant(fm, body, 'max')
    assert 'model: opus' in rendered
    assert 'effort: xhigh' in rendered


# =============================================================================
# emit_variants_for_agent (file emission)
# =============================================================================


def test_emit_variants_default_levels_creates_seven_files(tmp_path: Path, mapping_path: Path):
    src = _write(
        tmp_path / 'src' / 'poc.md',
        f'---\nname: poc\ntools: Read\nimplements: {EXTENSION_POINT}\n---\nbody\n',
    )
    dest = tmp_path / 'out' / 'poc.md'
    result = emit_variants_for_agent(src, dest, mapping_path)
    assert result is not None
    # canonical + 6 variants
    assert dest.exists()
    for level in ['low', 'medium', 'high', 'xhigh', 'xxhigh', 'max']:
        assert (dest.parent / f'poc-{level}.md').exists(), level
    assert sorted(result.variants_emitted) == sorted(LEVEL_TABLE.keys())
    assert result.variants_skipped == []


def test_emit_variants_with_levels_whitelist(tmp_path: Path, mapping_path: Path):
    src = _write(
        tmp_path / 'src' / 'poc.md',
        f'---\nname: poc\nimplements: {EXTENSION_POINT}\nlevels: [high, xxhigh]\n---\nbody\n',
    )
    dest = tmp_path / 'out' / 'poc.md'
    result = emit_variants_for_agent(src, dest, mapping_path)
    assert result is not None
    assert dest.exists()  # canonical
    assert (dest.parent / 'poc-high.md').exists()
    assert (dest.parent / 'poc-xxhigh.md').exists()
    # other levels not emitted
    for omitted in ['low', 'medium', 'xhigh']:
        assert not (dest.parent / f'poc-{omitted}.md').exists()


def test_emit_variants_canonical_strips_role_fields(tmp_path: Path, mapping_path: Path):
    src = _write(
        tmp_path / 'src' / 'poc.md',
        f'---\nname: poc\ntools: Read\nimplements: {EXTENSION_POINT}\nlevels: [high]\n---\nbody\n',
    )
    dest = tmp_path / 'out' / 'poc.md'
    emit_variants_for_agent(src, dest, mapping_path)
    canonical_text = dest.read_text(encoding='utf-8')
    assert f'implements: {EXTENSION_POINT}' not in canonical_text
    assert 'levels:' not in canonical_text
    assert 'name: poc' in canonical_text  # canonical keeps base name
    assert 'tools: Read' in canonical_text  # other fields preserved


def test_emit_variants_skips_max_when_opus_lacks_xhigh(tmp_path: Path):
    """Opus alias with supports_effort missing `xhigh`: `max` is suppressed."""
    mapping = tmp_path / 'mapping_opus_no_xhigh.json'
    mapping.write_text(
        json.dumps(
            {
                'tool_permissions': {},
                'model_map': {
                    'opus': {'id': 'claude-opus-old', 'supports_effort': ['medium', 'high']},
                    'sonnet': {'id': 'sonnet-x', 'supports_effort': ['medium', 'high']},
                    'haiku': {'id': 'haiku-y', 'supports_effort': []},
                },
            }
        ),
        encoding='utf-8',
    )
    src = _write(
        tmp_path / 'src' / 'poc.md',
        f'---\nname: poc\nimplements: {EXTENSION_POINT}\nlevels: [high, xxhigh, max]\n---\nbody\n',
    )
    dest = tmp_path / 'out' / 'poc.md'
    result = emit_variants_for_agent(src, dest, mapping)
    assert result is not None
    assert (dest.parent / 'poc-high.md').exists()
    assert (dest.parent / 'poc-xxhigh.md').exists()  # opus-high is fine
    assert not (dest.parent / 'poc-max.md').exists()
    skipped_max = [(lvl, reason) for lvl, reason in result.variants_skipped if lvl == 'max']
    assert skipped_max, 'max should be in variants_skipped'
    assert 'xhigh' in skipped_max[0][1].lower()


def test_emit_variants_emits_max_when_opus_supports_xhigh(tmp_path: Path, mapping_path: Path):
    """Default fixture: opus supports xhigh, `max` variant is emitted."""
    src = _write(
        tmp_path / 'src' / 'poc.md',
        f'---\nname: poc\nimplements: {EXTENSION_POINT}\nlevels: [max]\n---\nbody\n',
    )
    dest = tmp_path / 'out' / 'poc.md'
    result = emit_variants_for_agent(src, dest, mapping_path)
    assert result is not None
    assert (dest.parent / 'poc-max.md').exists()
    assert 'max' in result.variants_emitted
    assert all(lvl != 'max' for lvl, _reason in result.variants_skipped)


def test_emit_variants_canonical_with_model_raises(tmp_path: Path, mapping_path: Path):
    """Canonical declaring `implements:` AND `model:` is a build error."""
    src = _write(
        tmp_path / 'src' / 'poc.md',
        f'---\nname: poc\nimplements: {EXTENSION_POINT}\nmodel: opus\n---\nbody\n',
    )
    dest = tmp_path / 'out' / 'poc.md'
    with pytest.raises(CanonicalValidationError, match='model:'):
        emit_variants_for_agent(src, dest, mapping_path)


def test_emit_variants_canonical_with_effort_raises(tmp_path: Path, mapping_path: Path):
    src = _write(
        tmp_path / 'src' / 'poc.md',
        f'---\nname: poc\nimplements: {EXTENSION_POINT}\neffort: high\n---\nbody\n',
    )
    dest = tmp_path / 'out' / 'poc.md'
    with pytest.raises(CanonicalValidationError, match='effort:'):
        emit_variants_for_agent(src, dest, mapping_path)


def test_emit_variants_returns_none_for_non_role_agent(tmp_path: Path, mapping_path: Path):
    """Non-eligible agent: emitter returns None and writes nothing."""
    src = _write(tmp_path / 'src' / 'plain.md', '---\nname: plain\n---\nbody\n')
    dest = tmp_path / 'out' / 'plain.md'
    result = emit_variants_for_agent(src, dest, mapping_path)
    assert result is None
    assert not dest.exists()  # caller is responsible for verbatim copy in this branch


# =============================================================================
# Integration with emit_bundle_verbatim
# =============================================================================


def _bundle_with_role_agent(bundle_root: Path, name: str = 'demo') -> Path:
    bundle = bundle_root / name
    plugin = bundle / '.claude-plugin' / 'plugin.json'
    plugin.parent.mkdir(parents=True, exist_ok=True)
    plugin.write_text(
        json.dumps({'name': name, 'version': '0.0.1', 'agents': [], 'commands': [], 'skills': []}),
        encoding='utf-8',
    )
    _write(
        bundle / 'agents' / 'role-agent.md',
        f'---\nname: role-agent\ntools: Read\nimplements: {EXTENSION_POINT}\nlevels: [high, xxhigh]\n---\nbody\n',
    )
    _write(bundle / 'agents' / 'plain-agent.md', '---\nname: plain-agent\n---\nbody\n')
    return bundle


def test_emit_bundle_verbatim_routes_role_agents_to_variant_emission(tmp_path: Path):
    bundles_root = tmp_path / 'bundles'
    bundle_dir = _bundle_with_role_agent(bundles_root)
    out_dir = tmp_path / 'out'
    written = emit_bundle_verbatim(bundle_dir, out_dir)

    # Canonical role-agent is rewritten (not byte-copy) — implements stripped.
    canonical = out_dir / 'demo' / 'agents' / 'role-agent.md'
    assert canonical.exists()
    assert f'implements: {EXTENSION_POINT}' not in canonical.read_text(encoding='utf-8')

    # Variants exist for whitelisted levels only.
    assert (out_dir / 'demo' / 'agents' / 'role-agent-high.md').exists()
    assert (out_dir / 'demo' / 'agents' / 'role-agent-xxhigh.md').exists()
    assert not (out_dir / 'demo' / 'agents' / 'role-agent-low.md').exists()

    # Plain agent is byte-copied verbatim (no variants).
    plain = out_dir / 'demo' / 'agents' / 'plain-agent.md'
    assert plain.read_text(encoding='utf-8') == '---\nname: plain-agent\n---\nbody\n'

    # The written list mentions variants.
    paths = {str(p) for p in written}
    assert any('role-agent-high.md' in p for p in paths)


# =============================================================================
# plugin_json_gen integration
# =============================================================================


def test_discover_components_expands_role_agents(tmp_path: Path):
    bundles_root = tmp_path / 'bundles'
    bundle_dir = _bundle_with_role_agent(bundles_root)

    discovered = discover_components(bundle_dir)
    agents = discovered['agents']

    # Canonical + per-level entries (whitelist [high, xxhigh]); plain unchanged.
    assert './agents/role-agent.md' in agents
    assert './agents/role-agent-high.md' in agents
    assert './agents/role-agent-xxhigh.md' in agents
    assert './agents/plain-agent.md' in agents
    # Excluded levels: low, medium, xhigh
    assert './agents/role-agent-low.md' not in agents
    # Sorted output
    assert agents == sorted(agents)
