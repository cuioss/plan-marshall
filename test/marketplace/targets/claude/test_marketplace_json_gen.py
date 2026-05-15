"""Tests for the top-level marketplace.json generator."""

import json
from pathlib import Path

import pytest

from marketplace.targets.claude.marketplace_json_gen import (
    build_marketplace_json,
    generate_marketplace_json,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


@pytest.fixture()
def marketplace_src(tmp_path: Path) -> Path:
    """A tiny source marketplace with two plugins."""
    root = tmp_path / 'marketplace-src'
    manifest = {
        'name': 'demo-marketplace',
        'owner': {'name': 'demo owner'},
        'metadata': {'description': 'demo', 'version': '1.2.3'},
        'plugins': [
            {
                'name': 'alpha',
                'description': 'alpha plugin',
                'source': './bundles/alpha',
                'strict': False,
            },
            {
                'name': 'beta',
                'description': 'beta plugin',
                'source': './bundles/beta',
                'strict': True,
            },
        ],
    }
    _write(root / '.claude-plugin' / 'marketplace.json', json.dumps(manifest, indent=2) + '\n')
    return root


def test_build_marketplace_json_rewrites_plugin_sources(marketplace_src: Path):
    output = build_marketplace_json(marketplace_src)
    sources = [p['source'] for p in output['plugins']]
    assert sources == ['./alpha', './beta']


def test_build_marketplace_json_preserves_top_level_fields(marketplace_src: Path):
    output = build_marketplace_json(marketplace_src)
    assert output['name'] == 'demo-marketplace'
    assert output['owner'] == {'name': 'demo owner'}
    assert output['metadata'] == {'description': 'demo', 'version': '1.2.3'}


def test_build_marketplace_json_preserves_per_plugin_fields(marketplace_src: Path):
    output = build_marketplace_json(marketplace_src)
    alpha = next(p for p in output['plugins'] if p['name'] == 'alpha')
    beta = next(p for p in output['plugins'] if p['name'] == 'beta')
    assert alpha['description'] == 'alpha plugin'
    assert alpha['strict'] is False
    assert beta['description'] == 'beta plugin'
    assert beta['strict'] is True


def test_build_marketplace_json_keeps_all_plugins(marketplace_src: Path):
    # Per the agreed scope, the emitted marketplace.json always carries the
    # full plugins[] list; it is not filtered by the caller's --bundles
    # selection.
    output = build_marketplace_json(marketplace_src)
    names = [p['name'] for p in output['plugins']]
    assert names == ['alpha', 'beta']


def test_generate_marketplace_json_is_deterministic(marketplace_src: Path):
    first = generate_marketplace_json(marketplace_src)
    second = generate_marketplace_json(marketplace_src)
    assert first == second
    assert first.endswith('\n')
    parsed = json.loads(first)
    assert parsed['name'] == 'demo-marketplace'


def test_missing_source_manifest_raises(tmp_path: Path):
    empty = tmp_path / 'empty'
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        build_marketplace_json(empty)


def test_unrecognised_source_prefix_raises(tmp_path: Path):
    root = tmp_path / 'bad-prefix'
    manifest = {
        'name': 'bad',
        'plugins': [
            {'name': 'gamma', 'description': 'g', 'source': '/abs/path/to/gamma'},
        ],
    }
    _write(root / '.claude-plugin' / 'marketplace.json', json.dumps(manifest, indent=2) + '\n')
    with pytest.raises(ValueError, match='gamma'):
        build_marketplace_json(root)


def test_plugin_without_source_is_passed_through(tmp_path: Path):
    # Defensive: if a source manifest omits the ``source`` field entirely,
    # the generator must not crash. It just leaves the entry alone.
    root = tmp_path / 'no-source'
    manifest = {
        'name': 'no-source',
        'plugins': [{'name': 'delta', 'description': 'd'}],
    }
    _write(root / '.claude-plugin' / 'marketplace.json', json.dumps(manifest, indent=2) + '\n')
    output = build_marketplace_json(root)
    assert output['plugins'] == [{'name': 'delta', 'description': 'd'}]
