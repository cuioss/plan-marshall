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
- ``level-6`` / ``level-7`` are suppressed when the canonical alias does
  not accept the level's gated effort (opus-``xhigh`` for ``level-6``,
  fable-``max`` for ``level-7``).
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
    supports_effort,
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
    """Fixture mapping.json with opus xhigh-capable and fable max-capable;
    sonnet/haiku not. Includes `fable` so the `level-7` top tier emits."""
    path = tmp_path / 'mapping.json'
    path.write_text(
        json.dumps(
            {
                'tool_permissions': {},
                'model_map': {
                    'opus': {
                        'id': 'claude-opus-4-8',
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
                    'fable': {
                        'id': 'claude-fable-5',
                        'supports_effort': ['medium', 'high', 'xhigh', 'max'],
                    },
                },
            }
        ),
        encoding='utf-8',
    )
    return path


# =============================================================================
# supports_effort (per-effort capability guard)
# =============================================================================


@pytest.fixture()
def mapping_path_with_fable(tmp_path: Path) -> Path:
    """Fixture mapping.json including the `fable` top-tier alias (supports max)."""
    path = tmp_path / 'mapping_fable.json'
    path.write_text(
        json.dumps(
            {
                'tool_permissions': {},
                'model_map': {
                    'opus': {
                        'id': 'claude-opus-4-8',
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
                    'fable': {
                        'id': 'claude-fable-5',
                        'supports_effort': ['medium', 'high', 'xhigh', 'max'],
                    },
                },
            }
        ),
        encoding='utf-8',
    )
    return path


def test_supports_effort_fable_accepts_max(mapping_path_with_fable: Path):
    assert supports_effort('fable', 'max', mapping_path_with_fable) is True


def test_supports_effort_opus_accepts_xhigh(mapping_path_with_fable: Path):
    assert supports_effort('opus', 'xhigh', mapping_path_with_fable) is True


def test_supports_effort_sonnet_rejects_max(mapping_path_with_fable: Path):
    assert supports_effort('sonnet', 'max', mapping_path_with_fable) is False


def test_supports_effort_refuses_unknown_alias(mapping_path_with_fable: Path):
    """Conservative refuse-on-missing: an absent alias never accepts any effort."""
    assert supports_effort('nonexistent', 'medium', mapping_path_with_fable) is False


def test_supports_effort_refuses_missing_mapping(tmp_path: Path):
    """A missing mapping file yields the conservative refuse-emit answer."""
    assert supports_effort('opus', 'xhigh', tmp_path / 'absent.json') is False


# =============================================================================
# parse_frontmatter / is_role_eligible / selected_levels
# =============================================================================


def test_parse_frontmatter_extracts_implements_and_levels():
    text = (
        '---\n'
        'name: my-agent\n'
        'tools: Read, Bash\n'
        f'implements: {EXTENSION_POINT}\n'
        'levels: [level-3, level-5]\n'
        '---\n'
        'body content\n'
    )
    fm, body = parse_frontmatter(text)
    assert fm is not None
    assert fm.name == 'my-agent'
    assert fm.implements == EXTENSION_POINT
    assert fm.levels == ['level-3', 'level-5']
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


def test_selected_levels_default_returns_all_seven():
    fm, _ = parse_frontmatter(f'---\nname: x\nimplements: {EXTENSION_POINT}\n---\nbody')
    assert fm is not None
    assert selected_levels(fm) == [
        'level-1', 'level-2', 'level-3', 'level-4', 'level-5', 'level-6', 'level-7'
    ]


def test_selected_levels_whitelist_filters():
    fm, _ = parse_frontmatter(
        f'---\nname: x\nimplements: {EXTENSION_POINT}\nlevels: [level-3, level-5]\n---\nbody'
    )
    assert fm is not None
    assert selected_levels(fm) == ['level-3', 'level-5']


# =============================================================================
# render_variant
# =============================================================================


def test_render_variant_haiku_omits_effort():
    fm, body = parse_frontmatter(
        f'---\nname: poc-agent\ntools: Read\nimplements: {EXTENSION_POINT}\n---\nbody\n'
    )
    assert fm is not None
    rendered = render_variant(fm, body, 'level-1')
    assert 'name: poc-agent-level-1' in rendered
    assert 'model: haiku' in rendered
    assert 'effort:' not in rendered  # haiku does not accept effort
    assert f'implements: {EXTENSION_POINT}' not in rendered


def test_render_variant_level_3_sets_model_and_effort():
    fm, body = parse_frontmatter(
        f'---\nname: poc-agent\nimplements: {EXTENSION_POINT}\n---\nbody\n'
    )
    assert fm is not None
    rendered = render_variant(fm, body, 'level-3')
    assert 'name: poc-agent-level-3' in rendered
    assert 'model: sonnet' in rendered
    assert 'effort: high' in rendered


def test_render_variant_level_5_uses_opus_high():
    """`level-5` resolves to `(opus, high)`."""
    fm, body = parse_frontmatter(
        f'---\nname: poc-agent\nimplements: {EXTENSION_POINT}\n---\nbody\n'
    )
    assert fm is not None
    rendered = render_variant(fm, body, 'level-5')
    assert 'model: opus' in rendered
    assert 'effort: high' in rendered


def test_render_variant_level_4_uses_opus_medium():
    """`level-4` resolves to `(opus, medium)`."""
    fm, body = parse_frontmatter(
        f'---\nname: poc-agent\nimplements: {EXTENSION_POINT}\n---\nbody\n'
    )
    assert fm is not None
    rendered = render_variant(fm, body, 'level-4')
    assert 'model: opus' in rendered
    assert 'effort: medium' in rendered


def test_render_variant_level_6_uses_opus_xhigh():
    """`level-6` resolves to `(opus, xhigh)` — Opus-4.8-only tier."""
    fm, body = parse_frontmatter(
        f'---\nname: poc-agent\nimplements: {EXTENSION_POINT}\n---\nbody\n'
    )
    assert fm is not None
    rendered = render_variant(fm, body, 'level-6')
    assert 'model: opus' in rendered
    assert 'effort: xhigh' in rendered


def test_render_variant_level_7_uses_fable_max():
    """`level-7` resolves to `(fable, max)` — the new top tier above Opus."""
    fm, body = parse_frontmatter(
        f'---\nname: poc-agent\nimplements: {EXTENSION_POINT}\n---\nbody\n'
    )
    assert fm is not None
    rendered = render_variant(fm, body, 'level-7')
    assert 'model: fable' in rendered
    assert 'effort: max' in rendered


# =============================================================================
# emit_variants_for_agent (file emission)
# =============================================================================


def test_emit_variants_default_levels_creates_eight_files(tmp_path: Path, mapping_path: Path):
    src = _write(
        tmp_path / 'src' / 'poc.md',
        f'---\nname: poc\ntools: Read\nimplements: {EXTENSION_POINT}\n---\nbody\n',
    )
    dest = tmp_path / 'out' / 'poc.md'
    result = emit_variants_for_agent(src, dest, mapping_path)
    assert result is not None
    # canonical + 7 variants
    assert dest.exists()
    for level in [
        'level-1', 'level-2', 'level-3', 'level-4', 'level-5', 'level-6', 'level-7'
    ]:
        assert (dest.parent / f'poc-{level}.md').exists(), level
    assert sorted(result.variants_emitted) == sorted(LEVEL_TABLE.keys())
    assert result.variants_skipped == []


def test_emit_variants_with_levels_whitelist(tmp_path: Path, mapping_path: Path):
    src = _write(
        tmp_path / 'src' / 'poc.md',
        f'---\nname: poc\nimplements: {EXTENSION_POINT}\nlevels: [level-3, level-5]\n---\nbody\n',
    )
    dest = tmp_path / 'out' / 'poc.md'
    result = emit_variants_for_agent(src, dest, mapping_path)
    assert result is not None
    assert dest.exists()  # canonical
    assert (dest.parent / 'poc-level-3.md').exists()
    assert (dest.parent / 'poc-level-5.md').exists()
    # other levels not emitted
    for omitted in ['level-1', 'level-2', 'level-4']:
        assert not (dest.parent / f'poc-{omitted}.md').exists()


def test_emit_variants_canonical_strips_role_fields(tmp_path: Path, mapping_path: Path):
    src = _write(
        tmp_path / 'src' / 'poc.md',
        f'---\nname: poc\ntools: Read\nimplements: {EXTENSION_POINT}\nlevels: [level-3]\n---\nbody\n',
    )
    dest = tmp_path / 'out' / 'poc.md'
    emit_variants_for_agent(src, dest, mapping_path)
    canonical_text = dest.read_text(encoding='utf-8')
    assert f'implements: {EXTENSION_POINT}' not in canonical_text
    assert 'levels:' not in canonical_text
    assert 'name: poc' in canonical_text  # canonical keeps base name
    assert 'tools: Read' in canonical_text  # other fields preserved


def test_emit_variants_skips_level_6_when_opus_lacks_xhigh(tmp_path: Path):
    """Opus alias with supports_effort missing `xhigh`: `level-6` is suppressed.

    The fixture also omits a `fable` alias, so `level-7` is suppressed too —
    the test pins the `level-6` (opus-xhigh) guard specifically.
    """
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
        f'---\nname: poc\nimplements: {EXTENSION_POINT}\nlevels: [level-3, level-5, level-6]\n---\nbody\n',
    )
    dest = tmp_path / 'out' / 'poc.md'
    result = emit_variants_for_agent(src, dest, mapping)
    assert result is not None
    assert (dest.parent / 'poc-level-3.md').exists()
    assert (dest.parent / 'poc-level-5.md').exists()  # opus-high is fine
    assert not (dest.parent / 'poc-level-6.md').exists()
    skipped = [(lvl, reason) for lvl, reason in result.variants_skipped if lvl == 'level-6']
    assert skipped, 'level-6 should be in variants_skipped'
    assert 'xhigh' in skipped[0][1].lower()


def test_emit_variants_emits_level_6_when_opus_supports_xhigh(tmp_path: Path, mapping_path: Path):
    """Default fixture: opus supports xhigh, `level-6` variant is emitted."""
    src = _write(
        tmp_path / 'src' / 'poc.md',
        f'---\nname: poc\nimplements: {EXTENSION_POINT}\nlevels: [level-6]\n---\nbody\n',
    )
    dest = tmp_path / 'out' / 'poc.md'
    result = emit_variants_for_agent(src, dest, mapping_path)
    assert result is not None
    assert (dest.parent / 'poc-level-6.md').exists()
    assert 'level-6' in result.variants_emitted
    assert all(lvl != 'level-6' for lvl, _reason in result.variants_skipped)


def test_emit_variants_emits_level_7_when_fable_supports_max(tmp_path: Path, mapping_path: Path):
    """Default fixture: fable supports max, `level-7` variant is emitted."""
    src = _write(
        tmp_path / 'src' / 'poc.md',
        f'---\nname: poc\nimplements: {EXTENSION_POINT}\nlevels: [level-7]\n---\nbody\n',
    )
    dest = tmp_path / 'out' / 'poc.md'
    result = emit_variants_for_agent(src, dest, mapping_path)
    assert result is not None
    assert (dest.parent / 'poc-level-7.md').exists()
    assert 'level-7' in result.variants_emitted
    assert all(lvl != 'level-7' for lvl, _reason in result.variants_skipped)


def test_emit_variants_skips_level_7_when_fable_lacks_max(tmp_path: Path):
    """Fable alias whose supports_effort omits `max`: `level-7` is suppressed."""
    mapping = tmp_path / 'mapping_fable_no_max.json'
    mapping.write_text(
        json.dumps(
            {
                'tool_permissions': {},
                'model_map': {
                    'opus': {'id': 'claude-opus-4-8', 'supports_effort': ['medium', 'high', 'xhigh']},
                    'sonnet': {'id': 'sonnet-x', 'supports_effort': ['medium', 'high']},
                    'haiku': {'id': 'haiku-y', 'supports_effort': []},
                    'fable': {'id': 'claude-fable-5', 'supports_effort': ['medium', 'high', 'xhigh']},
                },
            }
        ),
        encoding='utf-8',
    )
    src = _write(
        tmp_path / 'src' / 'poc.md',
        f'---\nname: poc\nimplements: {EXTENSION_POINT}\nlevels: [level-6, level-7]\n---\nbody\n',
    )
    dest = tmp_path / 'out' / 'poc.md'
    result = emit_variants_for_agent(src, dest, mapping)
    assert result is not None
    assert (dest.parent / 'poc-level-6.md').exists()  # opus-xhigh is fine
    assert not (dest.parent / 'poc-level-7.md').exists()
    skipped = [(lvl, reason) for lvl, reason in result.variants_skipped if lvl == 'level-7']
    assert skipped, 'level-7 should be in variants_skipped'
    assert 'max' in skipped[0][1].lower()


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
        f'---\nname: role-agent\ntools: Read\nimplements: {EXTENSION_POINT}\nlevels: [level-3, level-5]\n---\nbody\n',
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
    assert (out_dir / 'demo' / 'agents' / 'role-agent-level-3.md').exists()
    assert (out_dir / 'demo' / 'agents' / 'role-agent-level-5.md').exists()
    assert not (out_dir / 'demo' / 'agents' / 'role-agent-level-1.md').exists()

    # Plain agent is byte-copied verbatim (no variants).
    plain = out_dir / 'demo' / 'agents' / 'plain-agent.md'
    assert plain.read_text(encoding='utf-8') == '---\nname: plain-agent\n---\nbody\n'

    # The written list mentions variants.
    paths = {str(p) for p in written}
    assert any('role-agent-level-3.md' in p for p in paths)


# =============================================================================
# plugin_json_gen integration
# =============================================================================


def test_discover_components_expands_role_agents(tmp_path: Path):
    bundles_root = tmp_path / 'bundles'
    bundle_dir = _bundle_with_role_agent(bundles_root)

    discovered = discover_components(bundle_dir)
    agents = discovered['agents']

    # Canonical + per-level entries (whitelist [level-3, level-5]); plain unchanged.
    assert './agents/role-agent.md' in agents
    assert './agents/role-agent-level-3.md' in agents
    assert './agents/role-agent-level-5.md' in agents
    assert './agents/plain-agent.md' in agents
    # Excluded levels: level-1, level-2, level-4
    assert './agents/role-agent-level-1.md' not in agents
    # Sorted output
    assert agents == sorted(agents)
