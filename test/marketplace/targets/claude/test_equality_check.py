"""Tests for the Claude target equality-check engine.

The engine compares ``build_plugin_json(bundle_dir)`` (regenerated from
the source bundle's frontmatter scan) against the emitted artifact at
``target/claude/{bundle}/.claude-plugin/plugin.json``. The source
bundle's committed ``plugin.json`` is no longer the source of truth.
"""

import json
from pathlib import Path

import pytest

from marketplace.targets.claude.emitter import iter_bundle_dirs
from marketplace.targets.claude.equality_check import check_bundle, run_equality_check


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _emitted(target_dir: Path, bundle_name: str, plugin_doc: dict) -> None:
    """Helper: write an emitted plugin.json into target_dir."""
    _write(
        target_dir / bundle_name / '.claude-plugin' / 'plugin.json',
        json.dumps(plugin_doc, indent=2) + '\n',
    )


@pytest.fixture()
def clean_marketplace(tmp_path: Path) -> tuple[Path, Path]:
    """Source bundle + matching emitted artifact under target/claude/."""
    marketplace = tmp_path / 'bundles'
    target = tmp_path / 'target' / 'claude'
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
    # Mirror the committed plugin.json into the emitted target so a clean
    # tree means "source matches target".
    _emitted(target, 'demo', plugin_doc)
    return marketplace, target


def test_clean_tree_passes(clean_marketplace: tuple[Path, Path]):
    marketplace, target = clean_marketplace
    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)
    assert result.passed is True
    assert result.diffs == []
    assert 'passed' in result.summary


def test_added_skill_without_target_update_drift(clean_marketplace: tuple[Path, Path]):
    """New source skill without re-emit: surfaces as `only_in_generated`."""
    marketplace, target = clean_marketplace
    new_skill = marketplace / 'demo' / 'skills' / 'new-skill' / 'SKILL.md'
    _write(new_skill, '---\nname: new-skill\ndescription: n\n---\n')
    diffs = check_bundle(marketplace / 'demo', target)
    skills_diff = next((d for d in diffs if d.field == 'skills'), None)
    assert skills_diff is not None
    assert './skills/new-skill' in skills_diff.only_in_generated
    assert './skills/new-skill' not in (skills_diff.only_in_committed or [])


def test_orphan_target_entry_drift(clean_marketplace: tuple[Path, Path]):
    """Stale entry only in the emitted target: surfaces as `only_in_committed`."""
    marketplace, target = clean_marketplace
    plugin_path = target / 'demo' / '.claude-plugin' / 'plugin.json'
    plugin_doc = json.loads(plugin_path.read_text(encoding='utf-8'))
    plugin_doc['skills'].append('./skills/ghost-skill')  # not on disk in source
    plugin_doc['skills'].sort()
    plugin_path.write_text(json.dumps(plugin_doc, indent=2) + '\n', encoding='utf-8')

    diffs = check_bundle(marketplace / 'demo', target)
    skills_diff = next((d for d in diffs if d.field == 'skills'), None)
    assert skills_diff is not None
    assert './skills/ghost-skill' in skills_diff.only_in_committed


def test_run_equality_check_summary_mentions_bundles(clean_marketplace: tuple[Path, Path]):
    marketplace, target = clean_marketplace
    new_skill = marketplace / 'demo' / 'skills' / 'new-skill' / 'SKILL.md'
    _write(new_skill, '---\nname: new-skill\ndescription: n\n---\n')

    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)
    assert result.passed is False
    assert 'demo' in result.summary
    assert 'failed' in result.summary


def test_missing_target_dir_returns_diagnostic(clean_marketplace: tuple[Path, Path]):
    """Absent target/claude/ root produces a structured diagnostic, not a crash."""
    marketplace, _target = clean_marketplace
    nowhere = marketplace.parent / 'target' / 'does-not-exist'
    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(nowhere, bundles)
    assert result.passed is False
    assert 'not generated' in result.summary
    assert 'generate.py --target claude' in result.summary
    assert result.missing_target_bundles == ['demo']


def test_missing_per_bundle_target_returns_diagnostic(clean_marketplace: tuple[Path, Path]):
    """target/claude exists but a specific bundle's plugin.json is missing."""
    marketplace, target = clean_marketplace
    # Wipe the demo bundle's emitted plugin.json
    (target / 'demo' / '.claude-plugin' / 'plugin.json').unlink()
    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)
    assert result.passed is False
    assert 'demo' in result.summary
    assert 'missing' in result.summary
    assert result.missing_target_bundles == ['demo']
