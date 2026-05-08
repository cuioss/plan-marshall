"""Smoke tests for the OpenCodeTarget end-to-end emit pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from marketplace.targets.opencode.target import OpenCodeTarget


def _write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding='utf-8')


@pytest.fixture()
def fixture_marketplace(tmp_path: Path) -> Path:
    """Marketplace tree with a single bundle covering skills/agents/commands."""
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'demo'
    plugin_doc = json.dumps(
        {
            'name': 'demo',
            'version': '0.0.1',
            'description': 'Demo bundle for OpenCode tests',
            'agents': ['./agents/demo-agent.md'],
            'commands': ['./commands/demo-cmd.md'],
            'skills': ['./skills/demo-skill'],
        },
        indent=2,
    ) + '\n'
    _write(bundle / '.claude-plugin' / 'plugin.json', plugin_doc)
    _write(
        bundle / 'skills' / 'demo-skill' / 'SKILL.md',
        '---\nname: demo-skill\ndescription: a demo skill\n---\n# Demo body\n',
    )
    _write(bundle / 'skills' / 'demo-skill' / 'standards' / 'rule.md', '# rule\n')
    _write(
        bundle / 'agents' / 'demo-agent.md',
        '---\nname: demo-agent\ndescription: demo agent\nmodel: sonnet\ntools: Read, Write\n---\nbody\n',
    )
    _write(
        bundle / 'commands' / 'demo-cmd.md',
        '---\nname: demo-cmd\ndescription: demo command\n---\ncmd body\n',
    )
    return marketplace


def test_opencode_target_name_and_capabilities():
    target = OpenCodeTarget()
    assert target.name == 'opencode'
    assert target.supports_agents() is True
    assert target.supports_commands() is True
    # config_dir resolves to the actual OpenCode target source dir
    assert (target.config_dir / 'mapping.json').exists()
    assert (target.config_dir / 'frontmatter-rules.json').exists()


def test_generate_requires_output_dir(fixture_marketplace: Path):
    target = OpenCodeTarget()
    with pytest.raises(ValueError):
        target.generate(fixture_marketplace, None)


def test_generate_emits_singular_layout(fixture_marketplace: Path, tmp_path: Path):
    target = OpenCodeTarget()
    out_dir = tmp_path / 'opencode-out'
    written = target.generate(fixture_marketplace, out_dir)

    # Singular layout: skill/, agent/, command/ directories.
    skill_dir = out_dir / 'skill' / 'demo-demo-skill'
    agent_dir = out_dir / 'agent'
    command_dir = out_dir / 'command'

    assert skill_dir.is_dir(), f'expected {skill_dir} after emit'
    assert agent_dir.is_dir(), f'expected {agent_dir} after emit'
    assert command_dir.is_dir(), f'expected {command_dir} after emit'

    assert (skill_dir / 'SKILL.md').is_file()
    assert (skill_dir / 'standards' / 'rule.md').is_file()
    assert (agent_dir / 'demo-agent.md').is_file()
    assert (command_dir / 'demo-cmd.md').is_file()

    # written list contains all expected entries
    rels = {p.relative_to(out_dir).as_posix() for p in written}
    assert 'skill/demo-demo-skill/SKILL.md' in rels
    assert 'agent/demo-agent.md' in rels
    assert 'command/demo-cmd.md' in rels
    assert 'opencode.json' in rels


def test_generate_writes_valid_opencode_json(fixture_marketplace: Path, tmp_path: Path):
    target = OpenCodeTarget()
    out_dir = tmp_path / 'opencode-out'
    target.generate(fixture_marketplace, out_dir)

    config_path = out_dir / 'opencode.json'
    assert config_path.is_file()
    config = json.loads(config_path.read_text(encoding='utf-8'))
    assert config['$schema'] == 'https://opencode.ai/config.json'
    assert config['skills']['paths'] == ['./skill']
    # Agent index records emitted agents
    assert 'agent' in config
    assert 'demo-agent' in config['agent']


def test_generate_filters_by_bundle_list(fixture_marketplace: Path, tmp_path: Path):
    target = OpenCodeTarget()
    out_dir = tmp_path / 'opencode-out'

    # An empty list filters everything out
    target.generate(fixture_marketplace, out_dir, bundles=['nonexistent'])
    assert not (out_dir / 'skill').exists()
    assert not (out_dir / 'agent').exists()
