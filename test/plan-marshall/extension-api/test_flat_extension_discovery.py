# SPDX-License-Identifier: FSL-1.1-ALv2
"""Extension discovery over a FLAT deployed tree, emitted by the REAL targets.

A flat install (``{root}/skills/{bundle}-{skill}/``) used to yield no extension at
all: the discovery walks treated every directory under the bundles root as a
bundle, and a flat tree has none — and even a flat-aware walk would have found
nothing, because the emitters dropped the ``implements:`` declaration that is the
only thing ``find_extension_path`` reads. With no extension found, module
discovery came back empty and no build command resolved.

Every case here builds its fixture by running a real target emitter
(``marketplace/targets/{opencode,antigravity}/emitter.py``) over a two-bundle
source, so the deployed ``SKILL.md`` under test is the file a machine actually
gets. The assertions are the three the flat leg exists for: the deployed manifest
declares its archetype, ``discover_all_extensions`` names the domain bundle by its
REAL name, and ``discover_applicable_extensions`` returns the modules the
extension reports.
"""

from __future__ import annotations

import json
from pathlib import Path

import deployed_layout
import pytest

from conftest import PROJECT_ROOT, load_script_module
from marketplace.targets.antigravity.emitter import emit_bundles as emit_antigravity
from marketplace.targets.opencode.emitter import emit_bundles as emit_opencode

_DISC_NAME = 'extension_discovery_flat'
_disc = load_script_module('plan-marshall', 'extension-api', 'extension_discovery.py', _DISC_NAME)

#: The archetype a domain bundle announces, and the ext point the opt-in step
#: fixture implements. Both are read from the source tree's own vocabulary.
_DOMAIN_BUNDLE_ARCHETYPE = 'plan-marshall:extension-api/standards/ext-point-domain-bundle'
_FINALIZE_STEP_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

_DOMAIN_BUNDLE = 'demo-domain'
_OPT_IN_BUNDLE = 'demo-opt'
_DOMAIN_SKILL = 'plan-marshall-plugin'
_OPT_IN_SKILL = 'plan-retrospective'
_UNDECLARED_SKILL = 'plain-skill'

#: The extension the fixture's domain bundle ships. Standalone (no marketplace
#: imports) so it loads from the deployed tree exactly as a real one does.
_EXTENSION_SOURCE = '''\
"""Fixture domain-bundle extension."""

MODULE_NAME = 'demo-module'


class Extension:
    """The minimal domain-bundle extension: one module for any project."""

    def discover_modules(self, project_root):
        return [{'name': MODULE_NAME, 'build_systems': ['maven'], 'paths': {'module': '.'}}]
'''

_EMITTERS = {
    'opencode': (emit_opencode, PROJECT_ROOT / 'marketplace' / 'targets' / 'opencode'),
    'antigravity': (emit_antigravity, PROJECT_ROOT / 'marketplace' / 'targets' / 'antigravity'),
}


def _write_skill(bundle: Path, skill: str, frontmatter: str) -> Path:
    skill_dir = bundle / 'skills' / skill
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text(f'---\n{frontmatter}---\n\n# body\n', encoding='utf-8')
    return skill_dir


def _write_bundle(marketplace: Path, name: str, skills: dict[str, str]) -> Path:
    """Create one source bundle with the given ``{skill: frontmatter}`` map."""
    bundle = marketplace / name
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text(
        json.dumps({'name': name, 'skills': [f'./skills/{skill}' for skill in skills]}) + '\n',
        encoding='utf-8',
    )
    for skill, frontmatter in skills.items():
        _write_skill(bundle, skill, frontmatter)
    return bundle


@pytest.fixture()
def two_bundle_source(tmp_path: Path) -> Path:
    """A two-bundle marketplace source: one domain bundle, one opt-in step.

    The domain bundle carries an ``extension.py`` beside the manifest that declares
    the archetype, plus a second skill that declares nothing — the undeclared one
    proves ``find_extension_path`` keeps its contract on the flat tree too.
    """
    marketplace = tmp_path / 'marketplace' / 'bundles'
    domain = _write_bundle(
        marketplace,
        _DOMAIN_BUNDLE,
        {
            _DOMAIN_SKILL: (
                f'name: {_DOMAIN_SKILL}\ndescription: demo domain bundle\nimplements: {_DOMAIN_BUNDLE_ARCHETYPE}\n'
            ),
            _UNDECLARED_SKILL: 'name: plain-skill\ndescription: declares no archetype\n',
        },
    )
    (domain / 'skills' / _DOMAIN_SKILL / 'extension.py').write_text(_EXTENSION_SOURCE, encoding='utf-8')
    _write_bundle(
        marketplace,
        _OPT_IN_BUNDLE,
        {
            _OPT_IN_SKILL: (
                f'name: {_OPT_IN_SKILL}\n'
                f'description: demo opt-in step\n'
                f'order: 995\n'
                f'default_on: false\n'
                f'implements: {_FINALIZE_STEP_EXT_POINT}\n'
            )
        },
    )
    return marketplace


def _emit(target: str, source: Path, tmp_path: Path) -> Path:
    emit, config_dir = _EMITTERS[target]
    output = tmp_path / f'emitted-{target}'
    emit(source, output, config_dir)
    return output


def _deployed_skill(root: Path, bundle: str, skill: str) -> Path:
    name = deployed_layout.flat_skill_dir_name(bundle, skill)
    matches = [skill_dir for skill_dir in deployed_layout.flat_skill_dirs(root) if skill_dir.name == name]
    assert matches, f'{name} is not in the emitted tree at {root}'
    return matches[0]


@pytest.mark.parametrize('target', sorted(_EMITTERS))
def test_the_deployed_manifest_declares_the_archetype(target: str, two_bundle_source: Path, tmp_path: Path) -> None:
    """The emitted ``SKILL.md`` reads back as the archetype the source declares."""
    root = _emit(target, two_bundle_source, tmp_path)
    deployed = _deployed_skill(root, _DOMAIN_BUNDLE, _DOMAIN_SKILL)

    assert _disc.read_implements_field(deployed / 'SKILL.md') == [_DOMAIN_BUNDLE_ARCHETYPE]

    undeclared = _deployed_skill(root, _DOMAIN_BUNDLE, _UNDECLARED_SKILL)
    assert _disc.read_implements_field(undeclared / 'SKILL.md') == []


@pytest.mark.parametrize('target', sorted(_EMITTERS))
def test_a_block_sequence_declaration_survives_the_emitters(
    target: str, two_bundle_source: Path, tmp_path: Path
) -> None:
    """A multi-value ``implements:`` block sequence keeps every value, in order."""
    manifest = two_bundle_source / _DOMAIN_BUNDLE / 'skills' / _DOMAIN_SKILL / 'SKILL.md'
    manifest.write_text(
        '---\nname: plan-marshall-plugin\ndescription: demo domain bundle\nimplements:\n'
        f'  - {_DOMAIN_BUNDLE_ARCHETYPE}\n'
        f'  - {_FINALIZE_STEP_EXT_POINT}\n'
        '---\n\n# body\n',
        encoding='utf-8',
    )

    root = _emit(target, two_bundle_source, tmp_path)
    deployed = _deployed_skill(root, _DOMAIN_BUNDLE, _DOMAIN_SKILL)

    assert _disc.read_implements_field(deployed / 'SKILL.md') == [
        _DOMAIN_BUNDLE_ARCHETYPE,
        _FINALIZE_STEP_EXT_POINT,
    ]


@pytest.mark.parametrize('target', sorted(_EMITTERS))
def test_discover_all_extensions_finds_the_domain_bundle_by_its_real_name(
    target: str, two_bundle_source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The flat tree is the ONLY root, and the bundle is named from its identity."""
    root = _emit(target, two_bundle_source, tmp_path)
    monkeypatch.setattr(_disc, 'get_marketplace_bundles_path', lambda: root)
    monkeypatch.setattr(_disc, 'get_bundle_cache_roots', lambda: ())

    extensions = _disc.discover_all_extensions()

    assert [ext['bundle'] for ext in extensions] == [_DOMAIN_BUNDLE], extensions
    assert extensions[0]['path'].endswith('extension.py')
    assert extensions[0]['module'] is not None


@pytest.mark.parametrize('target', sorted(_EMITTERS))
def test_discover_applicable_extensions_reports_modules_on_a_flat_tree(
    target: str, two_bundle_source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The discovered extension's own ``discover_modules`` runs and finds modules."""
    root = _emit(target, two_bundle_source, tmp_path)
    monkeypatch.setattr(_disc, 'get_marketplace_bundles_path', lambda: root)
    monkeypatch.setattr(_disc, 'get_bundle_cache_roots', lambda: ())
    project = tmp_path / 'project'
    project.mkdir()

    applicable = _disc.discover_applicable_extensions(project)

    assert [ext['bundle'] for ext in applicable] == [_DOMAIN_BUNDLE]
    assert applicable[0]['discovered_modules'], 'module discovery came back empty on the flat tree'


@pytest.mark.parametrize('target', sorted(_EMITTERS))
def test_the_opt_in_step_is_found_on_a_flat_tree(
    target: str, two_bundle_source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_scan_skills_roots_for_implementors`` finds a bundle-optional implementor."""
    root = _emit(target, two_bundle_source, tmp_path)
    monkeypatch.setattr(_disc, 'get_marketplace_bundles_path', lambda: root)
    monkeypatch.setattr(_disc, 'get_bundle_cache_roots', lambda: ())

    records = _disc._scan_skills_roots_for_implementors(_FINALIZE_STEP_EXT_POINT)

    assert [record['name'] for record in records] == [f'{_OPT_IN_BUNDLE}:{_OPT_IN_SKILL}']
    assert records[0]['source'] == 'bundle-optional'


# =============================================================================
# The nested and versioned legs are unchanged
# =============================================================================


def _nested_source(tmp_path: Path) -> Path:
    marketplace = tmp_path / 'nested' / 'marketplace' / 'bundles'
    domain = _write_bundle(
        marketplace,
        _DOMAIN_BUNDLE,
        {_DOMAIN_SKILL: f'name: {_DOMAIN_SKILL}\ndescription: d\nimplements: {_DOMAIN_BUNDLE_ARCHETYPE}\n'},
    )
    (domain / 'skills' / _DOMAIN_SKILL / 'extension.py').write_text(_EXTENSION_SOURCE, encoding='utf-8')
    return marketplace


def _versioned_root(tmp_path: Path) -> Path:
    cache = tmp_path / 'cache'
    version_dir = cache / _DOMAIN_BUNDLE / '0.1.1'
    (version_dir / '.claude-plugin').mkdir(parents=True)
    (version_dir / '.claude-plugin' / 'plugin.json').write_text('{"name": "demo-domain"}', encoding='utf-8')
    skill_dir = version_dir / 'skills' / _DOMAIN_SKILL
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text(
        f'---\nname: {_DOMAIN_SKILL}\ndescription: d\nimplements: {_DOMAIN_BUNDLE_ARCHETYPE}\n---\n# body\n',
        encoding='utf-8',
    )
    (skill_dir / 'extension.py').write_text(_EXTENSION_SOURCE, encoding='utf-8')
    return cache


def test_the_nested_source_leg_still_finds_the_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _nested_source(tmp_path)
    monkeypatch.setattr(_disc, 'get_marketplace_bundles_path', lambda: source)
    monkeypatch.setattr(_disc, 'get_bundle_cache_roots', lambda: ())

    assert _disc.discover_flat_extensions(source) == []
    assert [ext['bundle'] for ext in _disc.discover_all_extensions()] == [_DOMAIN_BUNDLE]


def test_the_versioned_cache_leg_still_finds_the_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = _versioned_root(tmp_path)
    monkeypatch.setattr(_disc, 'get_marketplace_bundles_path', lambda: cache)
    monkeypatch.setattr(_disc, 'get_bundle_cache_roots', lambda: ())

    assert _disc.discover_flat_extensions(cache) == []
    assert [ext['bundle'] for ext in _disc.discover_all_extensions()] == [_DOMAIN_BUNDLE]
