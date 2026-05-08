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
