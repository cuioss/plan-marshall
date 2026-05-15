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


def _write_source_marketplace(root: Path, plugin_names: list[str]) -> None:
    """Write a minimal source marketplace.json under ``root/.claude-plugin/``."""
    manifest = {
        'name': 'demo-marketplace',
        'plugins': [
            {'name': name, 'description': name, 'source': f'./bundles/{name}'}
            for name in plugin_names
        ],
    }
    _write(root / '.claude-plugin' / 'marketplace.json', json.dumps(manifest, indent=2) + '\n')


@pytest.fixture()
def clean_marketplace(tmp_path: Path) -> tuple[Path, Path]:
    """Source bundle + matching emitted artifact under target/claude/.

    The source bundle's committed plugin.json may still declare a ``skills``
    array (informational metadata), but the regenerator emits ``skills: []``
    so the runtime's default ``skills/`` folder scan owns skill discovery
    without double-loading. The emitted artifact mirrors what the build
    target produces, not the source's metadata view.
    """
    marketplace_root = tmp_path
    marketplace = marketplace_root / 'bundles'
    target = tmp_path / 'target' / 'claude'
    bundle = marketplace / 'demo'

    # Source plugin.json keeps the legacy skills metadata for top-level
    # passthrough; the emitted artifact uses the new empty-skills convention.
    source_plugin_doc = {
        'name': 'demo',
        'version': '0.0.1',
        'description': 'Demo bundle',
        'agents': ['./agents/demo-agent.md'],
        'commands': [],
        'skills': ['./skills/alpha-skill', './skills/zeta-skill'],
    }
    emitted_plugin_doc = {
        'name': 'demo',
        'version': '0.0.1',
        'description': 'Demo bundle',
        'agents': ['./agents/demo-agent.md'],
        'commands': [],
        'skills': [],
    }
    _write(bundle / '.claude-plugin' / 'plugin.json', json.dumps(source_plugin_doc, indent=2) + '\n')
    _write(bundle / 'agents' / 'demo-agent.md', '---\nname: demo-agent\n---\nbody\n')
    _write(bundle / 'skills' / 'alpha-skill' / 'SKILL.md', '---\nname: alpha-skill\ndescription: a\n---\n')
    _write(bundle / 'skills' / 'zeta-skill' / 'SKILL.md', '---\nname: zeta-skill\ndescription: z\n---\n')
    _emitted(target, 'demo', emitted_plugin_doc)

    # The equality engine now also diffs the top-level marketplace.json.
    # Write both source and emitted manifests so the clean fixture passes.
    _write_source_marketplace(marketplace_root, ['demo'])
    _write(
        target / '.claude-plugin' / 'marketplace.json',
        json.dumps(
            {
                'name': 'demo-marketplace',
                'plugins': [{'name': 'demo', 'description': 'demo', 'source': './demo'}],
            },
            indent=2,
        )
        + '\n',
    )
    return marketplace, target


def test_clean_tree_passes(clean_marketplace: tuple[Path, Path]):
    marketplace, target = clean_marketplace
    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)
    assert result.passed is True
    assert result.diffs == []
    assert 'passed' in result.summary


def test_added_agent_without_target_update_drift(clean_marketplace: tuple[Path, Path]):
    """New source agent without re-emit: surfaces as `only_in_generated`."""
    marketplace, target = clean_marketplace
    new_agent = marketplace / 'demo' / 'agents' / 'second-agent.md'
    _write(new_agent, '---\nname: second-agent\n---\nbody\n')
    diffs = check_bundle(marketplace / 'demo', target)
    agents_diff = next((d for d in diffs if d.field == 'agents'), None)
    assert agents_diff is not None
    assert './agents/second-agent.md' in agents_diff.only_in_generated
    assert './agents/second-agent.md' not in (agents_diff.only_in_committed or [])


def test_orphan_target_entry_drift(clean_marketplace: tuple[Path, Path]):
    """Stale entry only in the emitted target: surfaces as `only_in_committed`."""
    marketplace, target = clean_marketplace
    plugin_path = target / 'demo' / '.claude-plugin' / 'plugin.json'
    plugin_doc = json.loads(plugin_path.read_text(encoding='utf-8'))
    plugin_doc['agents'].append('./agents/ghost-agent.md')  # not on disk in source
    plugin_doc['agents'].sort()
    plugin_path.write_text(json.dumps(plugin_doc, indent=2) + '\n', encoding='utf-8')

    diffs = check_bundle(marketplace / 'demo', target)
    agents_diff = next((d for d in diffs if d.field == 'agents'), None)
    assert agents_diff is not None
    assert './agents/ghost-agent.md' in agents_diff.only_in_committed


def test_skills_field_never_drifts_regardless_of_disk_state(clean_marketplace: tuple[Path, Path]):
    """``skills`` is always ``[]`` in the regenerated artifact — adding or
    removing skill dirs on disk must NOT produce drift in the skills field.
    The runtime owns skill discovery via its default ``skills/`` folder scan.
    """
    marketplace, target = clean_marketplace
    _write(
        marketplace / 'demo' / 'skills' / 'new-skill' / 'SKILL.md',
        '---\nname: new-skill\ndescription: n\n---\n',
    )
    diffs = check_bundle(marketplace / 'demo', target)
    assert not any(d.field == 'skills' for d in diffs)


def test_marketplace_json_drift_surfaces(clean_marketplace: tuple[Path, Path]):
    """If the emitted marketplace.json differs from a fresh regeneration,
    the equality check fails with ``marketplace_json_drift=True``.
    """
    marketplace, target = clean_marketplace
    # Mutate the emitted marketplace.json to introduce drift.
    emitted = target / '.claude-plugin' / 'marketplace.json'
    doc = json.loads(emitted.read_text(encoding='utf-8'))
    doc['plugins'][0]['source'] = './stale-name'
    emitted.write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')

    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)
    assert result.passed is False
    assert result.marketplace_json_drift is True
    assert 'marketplace.json' in result.summary


def test_missing_top_level_marketplace_json_surfaces(clean_marketplace: tuple[Path, Path]):
    """If target/claude/.claude-plugin/marketplace.json is missing entirely,
    the equality check fails and the summary names the missing artifact.
    """
    marketplace, target = clean_marketplace
    (target / '.claude-plugin' / 'marketplace.json').unlink()
    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)
    assert result.passed is False
    assert result.marketplace_json_drift is True
    assert 'marketplace.json' in result.summary


def test_run_equality_check_summary_mentions_bundles(clean_marketplace: tuple[Path, Path]):
    marketplace, target = clean_marketplace
    new_agent = marketplace / 'demo' / 'agents' / 'second-agent.md'
    _write(new_agent, '---\nname: second-agent\n---\nbody\n')

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
