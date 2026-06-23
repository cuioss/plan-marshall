# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the deterministic plugin.json generator."""

import json
from pathlib import Path

import pytest

from marketplace.targets.claude.plugin_json_gen import (
    PASSTHROUGH_FIELDS,
    build_plugin_json,
    discover_components,
    generate_plugin_json,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


@pytest.fixture()
def bundle_dir(tmp_path: Path) -> Path:
    """A tiny bundle with two skills (intentionally unsorted), one agent, no commands."""
    bundle = tmp_path / 'demo'
    plugin_doc = {
        'name': 'demo',
        'version': '0.0.1',
        'description': 'Demo bundle',
        'author': {'name': 'demo author', 'email': 'demo@example.com'},
        'license': 'MIT',
        'homepage': 'https://example.com',
        'repository': 'https://example.com/repo.git',
        'keywords': ['demo'],
        'agents': ['./agents/zeta-agent.md'],
        # Intentionally listed out of alphabetical order.
        'skills': ['./skills/zeta-skill', './skills/alpha-skill'],
        'commands': [],
    }
    _write(bundle / '.claude-plugin' / 'plugin.json', json.dumps(plugin_doc, indent=2) + '\n')
    _write(bundle / 'agents' / 'zeta-agent.md', '---\nname: zeta-agent\n---\nbody\n')
    _write(bundle / 'skills' / 'alpha-skill' / 'SKILL.md', '---\nname: alpha-skill\ndescription: a\n---\n')
    _write(bundle / 'skills' / 'zeta-skill' / 'SKILL.md', '---\nname: zeta-skill\ndescription: z\n---\n')
    return bundle


def test_discover_components_sorts_arrays(bundle_dir: Path):
    discovered = discover_components(bundle_dir)
    assert discovered['agents'] == ['./agents/zeta-agent.md']
    assert discovered['commands'] == []
    # ``skills`` is emitted empty so the runtime's default ``skills/`` scan
    # owns skill discovery (avoids the double-load failure mode documented
    # in the module docstring).
    assert discovered['skills'] == []


def test_build_plugin_json_passes_top_level_fields(bundle_dir: Path):
    output = build_plugin_json(bundle_dir)
    for field in PASSTHROUGH_FIELDS:
        if field == 'keywords':
            assert output[field] == ['demo']
        elif field == 'author':
            assert output[field] == {'name': 'demo author', 'email': 'demo@example.com'}
        else:
            assert field in output


def test_build_plugin_json_replaces_component_arrays(bundle_dir: Path):
    output = build_plugin_json(bundle_dir)
    # ``skills`` is intentionally empty so the runtime's default skills/
    # folder scan handles skill discovery without doubling.
    assert output['skills'] == []
    assert output['commands'] == []


def test_generate_plugin_json_is_deterministic(bundle_dir: Path):
    first = generate_plugin_json(bundle_dir)
    second = generate_plugin_json(bundle_dir)
    assert first == second
    assert first.endswith('\n')
    parsed = json.loads(first)
    assert parsed['name'] == 'demo'


def test_skill_changes_do_not_alter_plugin_json_skills(bundle_dir: Path):
    # Adding or removing skill directories on disk must NOT change the
    # emitted ``skills`` array — the runtime owns skill discovery via its
    # default ``skills/`` folder scan.
    _write(bundle_dir / 'skills' / 'new-skill' / 'SKILL.md', '---\nname: new-skill\ndescription: n\n---\n')
    output_after_add = build_plugin_json(bundle_dir)
    assert output_after_add['skills'] == []

    skill_dir = bundle_dir / 'skills' / 'zeta-skill'
    for child in skill_dir.rglob('*'):
        if child.is_file():
            child.unlink()
    skill_dir.rmdir()
    output_after_remove = build_plugin_json(bundle_dir)
    assert output_after_remove['skills'] == []


def test_missing_committed_plugin_json_raises(tmp_path: Path):
    empty_bundle = tmp_path / 'empty'
    empty_bundle.mkdir()
    with pytest.raises(FileNotFoundError):
        build_plugin_json(empty_bundle)
