"""Tests for the Claude verbatim emitter."""

import json
from pathlib import Path

import pytest

from marketplace.targets.claude.emitter import (
    EXCLUDED_DIR_NAMES,
    emit_bundle_verbatim,
    iter_bundle_dirs,
)


def _write_bundle(bundle_root: Path, bundle_name: str, files: dict[str, str | bytes]) -> Path:
    bundle_dir = bundle_root / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        target = bundle_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding='utf-8')
    return bundle_dir


@pytest.fixture()
def fixture_marketplace(tmp_path: Path) -> Path:
    """Build a tiny marketplace tree with a single complete bundle."""
    marketplace = tmp_path / 'bundles'
    marketplace.mkdir()
    plugin_doc = json.dumps(
        {
            'name': 'demo',
            'version': '0.0.1',
            'description': 'Demo bundle',
            'agents': ['./agents/demo-agent.md'],
            'commands': [],
            'skills': ['./skills/demo-skill'],
        },
        indent=2,
    ) + '\n'
    _write_bundle(
        marketplace,
        'demo',
        {
            '.claude-plugin/plugin.json': plugin_doc,
            'agents/demo-agent.md': '---\nname: demo-agent\n---\nbody',
            'skills/demo-skill/SKILL.md': '---\nname: demo-skill\ndescription: demo\n---\n# demo',
            'skills/demo-skill/standards/rule.md': '# rule\n',
            'README.md': '# demo bundle\n',
            'skills/demo-skill/__pycache__/junk.pyc': b'\x00\x01',
        },
    )
    return marketplace


def test_iter_bundle_dirs_yields_only_bundles(fixture_marketplace: Path):
    bundles = list(iter_bundle_dirs(fixture_marketplace, None))
    assert [b.name for b in bundles] == ['demo']


def test_iter_bundle_dirs_filters_by_name(fixture_marketplace: Path):
    bundles = list(iter_bundle_dirs(fixture_marketplace, ['nonexistent']))
    assert bundles == []


def test_emit_bundle_verbatim_byte_equal(fixture_marketplace: Path, tmp_path: Path):
    bundle_dir = fixture_marketplace / 'demo'
    out_dir = tmp_path / 'out'
    written = emit_bundle_verbatim(bundle_dir, out_dir)

    # plugin.json is excluded — emitter does not write it.
    assert all('plugin.json' not in str(p) for p in written), written

    # README and skill body are byte-equal to source.
    assert (out_dir / 'demo' / 'README.md').read_bytes() == (bundle_dir / 'README.md').read_bytes()
    skill_path = out_dir / 'demo' / 'skills' / 'demo-skill' / 'SKILL.md'
    assert skill_path.read_bytes() == (bundle_dir / 'skills' / 'demo-skill' / 'SKILL.md').read_bytes()


def test_emit_bundle_verbatim_excludes_pycache(fixture_marketplace: Path, tmp_path: Path):
    bundle_dir = fixture_marketplace / 'demo'
    out_dir = tmp_path / 'out'
    emit_bundle_verbatim(bundle_dir, out_dir)
    # __pycache__ should never appear in the mirror.
    pycache_present = any('__pycache__' in str(p) for p in (out_dir / 'demo').rglob('*'))
    assert not pycache_present
    assert '__pycache__' in EXCLUDED_DIR_NAMES


def test_emit_bundle_verbatim_excludes_plugin_json(fixture_marketplace: Path, tmp_path: Path):
    bundle_dir = fixture_marketplace / 'demo'
    out_dir = tmp_path / 'out'
    emit_bundle_verbatim(bundle_dir, out_dir)
    target_plugin_json = out_dir / 'demo' / '.claude-plugin' / 'plugin.json'
    assert not target_plugin_json.exists()


def test_emit_bundle_verbatim_directory_structure(fixture_marketplace: Path, tmp_path: Path):
    bundle_dir = fixture_marketplace / 'demo'
    out_dir = tmp_path / 'out'
    emit_bundle_verbatim(bundle_dir, out_dir)

    expected_files = {
        'README.md',
        'agents/demo-agent.md',
        'skills/demo-skill/SKILL.md',
        'skills/demo-skill/standards/rule.md',
    }
    actual = {
        str(p.relative_to(out_dir / 'demo'))
        for p in (out_dir / 'demo').rglob('*')
        if p.is_file() and '__pycache__' not in str(p)
    }
    assert expected_files.issubset(actual), actual - expected_files


def test_emit_bundle_verbatim_wipes_stale_artifacts(fixture_marketplace: Path, tmp_path: Path):
    """Pre-emit cleanup: the destination bundle dir is wiped before copying so
    stale artifacts from a prior emit (e.g. variant files for a source canonical
    that has since been removed) do NOT linger in the target tree.
    """
    bundle_dir = fixture_marketplace / 'demo'
    out_dir = tmp_path / 'out'

    # Simulate leftovers from a prior emit run: a canonical and its variants
    # that no longer exist in source, plus a stale skill standards file.
    stale_canonical = out_dir / 'demo' / 'agents' / 'removed-agent.md'
    stale_variant = out_dir / 'demo' / 'agents' / 'removed-agent-high.md'
    stale_skill_file = out_dir / 'demo' / 'skills' / 'deleted-skill' / 'SKILL.md'
    for stale in (stale_canonical, stale_variant, stale_skill_file):
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text('---\nname: stale\n---\nstale body', encoding='utf-8')

    emit_bundle_verbatim(bundle_dir, out_dir)

    assert not stale_canonical.exists()
    assert not stale_variant.exists()
    assert not stale_skill_file.exists()
    # Fresh source content was emitted in their place.
    assert (out_dir / 'demo' / 'agents' / 'demo-agent.md').is_file()


def test_emit_bundle_verbatim_does_not_touch_sibling_bundles(tmp_path: Path):
    """The wipe is scoped to the emitting bundle's destination directory —
    sibling bundles and the top-level ``.claude-plugin/`` (which holds the
    marketplace.json registration manifest) must NOT be affected.
    """
    marketplace = tmp_path / 'bundles'
    out_dir = tmp_path / 'out'
    plugin_doc = json.dumps(
        {'name': 'a', 'version': '0.0.1', 'description': 'a'}, indent=2
    ) + '\n'
    _write_bundle(
        marketplace,
        'a',
        {
            '.claude-plugin/plugin.json': plugin_doc,
            'agents/a-agent.md': '---\nname: a-agent\n---\nbody',
        },
    )

    # Pre-populate the output with a sibling bundle AND a top-level
    # .claude-plugin/marketplace.json.
    sibling_file = out_dir / 'b' / 'agents' / 'b-agent.md'
    sibling_file.parent.mkdir(parents=True, exist_ok=True)
    sibling_file.write_text('---\nname: b-agent\n---\nbody', encoding='utf-8')
    top_marketplace = out_dir / '.claude-plugin' / 'marketplace.json'
    top_marketplace.parent.mkdir(parents=True, exist_ok=True)
    top_marketplace.write_text('{"name": "marketplace"}\n', encoding='utf-8')

    emit_bundle_verbatim(marketplace / 'a', out_dir)

    assert sibling_file.is_file()
    assert top_marketplace.is_file()
    assert (out_dir / 'a' / 'agents' / 'a-agent.md').is_file()
