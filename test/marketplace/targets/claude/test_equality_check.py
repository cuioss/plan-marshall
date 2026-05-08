"""Tests for the Claude target equality-check engine."""

import json
from pathlib import Path

import pytest

from marketplace.targets.claude.emitter import iter_bundle_dirs
from marketplace.targets.claude.equality_check import check_bundle, run_equality_check


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


@pytest.fixture()
def clean_marketplace(tmp_path: Path) -> Path:
    """A marketplace where committed plugin.json matches discovered files."""
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'demo'
    plugin_doc = {
        'name': 'demo',
        'version': '0.0.1',
        'description': 'Demo bundle',
        'agents': ['./agents/demo-agent.md'],
        'commands': [],
        'skills': ['./skills/alpha-skill', './skills/zeta-skill'],
    }
    _write(bundle / '.claude-plugin' / 'plugin.json', json.dumps(plugin_doc, indent=2) + '\n')
    _write(bundle / 'agents' / 'demo-agent.md', '---\nname: demo-agent\n---\nbody\n')
    _write(bundle / 'skills' / 'alpha-skill' / 'SKILL.md', '---\nname: alpha-skill\ndescription: a\n---\n')
    _write(bundle / 'skills' / 'zeta-skill' / 'SKILL.md', '---\nname: zeta-skill\ndescription: z\n---\n')
    return marketplace


def test_clean_tree_passes(clean_marketplace: Path):
    bundles = list(iter_bundle_dirs(clean_marketplace, None))
    result = run_equality_check(clean_marketplace, bundles)
    assert result.passed is True
    assert result.diffs == []
    assert 'passed' in result.summary


def test_added_skill_without_plugin_json_update_drift(clean_marketplace: Path):
    new_skill = clean_marketplace / 'demo' / 'skills' / 'new-skill' / 'SKILL.md'
    _write(new_skill, '---\nname: new-skill\ndescription: n\n---\n')
    diffs = check_bundle(clean_marketplace / 'demo')
    skills_diff = next((d for d in diffs if d.field == 'skills'), None)
    assert skills_diff is not None
    assert './skills/new-skill' in skills_diff.only_in_generated
    assert './skills/new-skill' not in (skills_diff.only_in_committed or [])


def test_orphan_plugin_json_entry_drift(clean_marketplace: Path):
    plugin_path = clean_marketplace / 'demo' / '.claude-plugin' / 'plugin.json'
    plugin_doc = json.loads(plugin_path.read_text(encoding='utf-8'))
    plugin_doc['skills'].append('./skills/ghost-skill')  # not on disk
    plugin_doc['skills'].sort()
    plugin_path.write_text(json.dumps(plugin_doc, indent=2) + '\n', encoding='utf-8')

    diffs = check_bundle(clean_marketplace / 'demo')
    skills_diff = next((d for d in diffs if d.field == 'skills'), None)
    assert skills_diff is not None
    assert './skills/ghost-skill' in skills_diff.only_in_committed


def test_run_equality_check_summary_mentions_bundles(clean_marketplace: Path):
    new_skill = clean_marketplace / 'demo' / 'skills' / 'new-skill' / 'SKILL.md'
    _write(new_skill, '---\nname: new-skill\ndescription: n\n---\n')

    bundles = list(iter_bundle_dirs(clean_marketplace, None))
    result = run_equality_check(clean_marketplace, bundles)
    assert result.passed is False
    assert 'demo' in result.summary
    assert 'failed' in result.summary
