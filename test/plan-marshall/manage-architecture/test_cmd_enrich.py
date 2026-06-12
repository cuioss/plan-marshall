#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for ``_cmd_enrich.py`` — per-module enrichment commands.

Pins the per-module on-disk layout: ``enrich project`` updates
``_project.json``; module-scoped enrich commands load and save only the
touched module's ``enriched.json``. Legacy monolithic files are intentionally
absent from this surface.
"""

import sys
import tempfile
from pathlib import Path

import pytest

from conftest import load_script_module

sys.path.insert(0, str(Path(__file__).parent))

from _arch_fixtures import seed_project as _seed_project  # noqa: E402
from _arch_fixtures import setup_test_project  # noqa: E402


_architecture_core = load_script_module('plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core')
_cmd_enrich = load_script_module('plan-marshall', 'manage-architecture', '_cmd_enrich.py', '_cmd_enrich')

DataNotFoundError = _architecture_core.DataNotFoundError
ModuleNotFoundInProjectError = _architecture_core.ModuleNotFoundInProjectError

load_project_meta = _architecture_core.load_project_meta
load_module_enriched = _architecture_core.load_module_enriched
load_module_enriched_or_empty = _architecture_core.load_module_enriched_or_empty

enrich_all = _cmd_enrich.enrich_all
enrich_best_practice = _cmd_enrich.enrich_best_practice
enrich_dependencies = _cmd_enrich.enrich_dependencies
enrich_insight = _cmd_enrich.enrich_insight
enrich_module = _cmd_enrich.enrich_module
enrich_package = _cmd_enrich.enrich_package
enrich_project = _cmd_enrich.enrich_project
enrich_skills_by_profile = _cmd_enrich.enrich_skills_by_profile
enrich_tip = _cmd_enrich.enrich_tip


# =============================================================================
# Tests for enrich_project
# =============================================================================


def test_enrich_project_updates_description_on_meta():
    """enrich_project writes description into ``_project.json``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_project('Test project description', tmpdir)

        assert result['status'] == 'success'
        assert result['updated'] == 'project.description'

        meta = load_project_meta(tmpdir)
        assert meta['description'] == 'Test project description'


def test_enrich_project_with_reasoning_persists_reasoning():
    """enrich_project stores reasoning when provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        enrich_project('Test project description', tmpdir, reasoning='Derived from README.md first paragraph')

        meta = load_project_meta(tmpdir)
        assert meta['description'] == 'Test project description'
        assert meta['description_reasoning'] == 'Derived from README.md first paragraph'


def test_enrich_project_without_reasoning_preserves_existing():
    """enrich_project without reasoning does not overwrite stored reasoning."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        enrich_project('Desc 1', tmpdir, reasoning='Original reasoning')
        enrich_project('Desc 2', tmpdir)

        meta = load_project_meta(tmpdir)
        assert meta['description'] == 'Desc 2'
        assert meta['description_reasoning'] == 'Original reasoning'


def test_enrich_project_missing_meta_raises():
    """enrich_project raises DataNotFoundError when ``_project.json`` is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            enrich_project('desc', tmpdir)
            assert False, 'Should have raised DataNotFoundError'
        except DataNotFoundError:
            pass


# =============================================================================
# Tests for enrich_module
# =============================================================================


def test_enrich_module_updates_responsibility():
    """enrich_module updates the module's ``enriched.json`` responsibility."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_module('module-a', 'Core validation logic', None, tmpdir)

        assert result['status'] == 'success'
        assert result['module'] == 'module-a'
        assert 'responsibility' in result['updated']

        enriched = load_module_enriched('module-a', tmpdir)
        assert enriched['responsibility'] == 'Core validation logic'


def test_enrich_module_updates_purpose():
    """enrich_module updates module purpose when provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_module('module-a', 'Core logic', 'library', tmpdir)

        assert 'purpose' in result['updated']

        enriched = load_module_enriched('module-a', tmpdir)
        assert enriched['purpose'] == 'library'


def test_enrich_module_unknown_module_raises():
    """enrich_module raises ModuleNotFoundInProjectError for unknown module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        try:
            enrich_module('nonexistent', 'desc', None, tmpdir)
            assert False, 'Should have raised ModuleNotFoundInProjectError'
        except ModuleNotFoundInProjectError:
            pass


def test_enrich_module_with_shared_reasoning_applied_to_both():
    """enrich_module applies the shared `reasoning` to both fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        enrich_module(
            'module-a',
            'Core validation logic',
            'library',
            tmpdir,
            reasoning='Derived from README overview',
        )

        enriched = load_module_enriched('module-a', tmpdir)
        assert enriched['responsibility_reasoning'] == 'Derived from README overview'
        assert enriched['purpose_reasoning'] == 'Derived from README overview'


def test_enrich_module_with_separate_reasoning():
    """enrich_module supports distinct responsibility and purpose reasoning."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        enrich_module(
            'module-a',
            'Core validation logic',
            'library',
            tmpdir,
            responsibility_reasoning='From README',
            purpose_reasoning='packaging=jar analysis',
        )

        enriched = load_module_enriched('module-a', tmpdir)
        assert enriched['responsibility_reasoning'] == 'From README'
        assert enriched['purpose_reasoning'] == 'packaging=jar analysis'


# =============================================================================
# Tests for enrich_package
# =============================================================================


def test_enrich_package_adds_new_key_package():
    """enrich_package adds a new entry into the module's ``key_packages``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_package('module-a', 'com.example.core', 'Core package', tmpdir)

        assert result['status'] == 'success'
        assert result['action'] == 'added'

        enriched = load_module_enriched('module-a', tmpdir)
        assert 'com.example.core' in enriched['key_packages']
        assert enriched['key_packages']['com.example.core']['description'] == 'Core package'


def test_enrich_package_updates_existing():
    """enrich_package updates an existing key package description."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        enrich_package('module-a', 'com.example.core', 'Original', tmpdir)
        result = enrich_package('module-a', 'com.example.core', 'Updated', tmpdir)

        assert result['action'] == 'updated'
        enriched = load_module_enriched('module-a', tmpdir)
        assert enriched['key_packages']['com.example.core']['description'] == 'Updated'


def test_enrich_package_with_components():
    """enrich_package stores components when provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        components = ['ClaimValidator', 'JwtPipeline', 'ValidationResult']
        result = enrich_package('module-a', 'com.example.core', 'Core components', tmpdir, components=components)

        assert result['status'] == 'success'
        assert result['components'] == components

        enriched = load_module_enriched('module-a', tmpdir)
        pkg = enriched['key_packages']['com.example.core']
        assert pkg['description'] == 'Core components'
        assert pkg['components'] == components


def test_enrich_package_update_preserves_components():
    """Updating description without components preserves the stored components."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        enrich_package('module-a', 'com.example.core', 'Original', tmpdir, components=['Class1', 'Class2'])
        enrich_package('module-a', 'com.example.core', 'Updated', tmpdir)

        enriched = load_module_enriched('module-a', tmpdir)
        pkg = enriched['key_packages']['com.example.core']
        assert pkg['description'] == 'Updated'
        assert pkg['components'] == ['Class1', 'Class2']


def test_enrich_package_update_components():
    """enrich_package can replace components on an existing package."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        enrich_package('module-a', 'com.example.core', 'Desc', tmpdir, components=['Class1'])
        enrich_package('module-a', 'com.example.core', 'Desc', tmpdir, components=['Class1', 'Class2', 'Class3'])

        enriched = load_module_enriched('module-a', tmpdir)
        pkg = enriched['key_packages']['com.example.core']
        assert pkg['components'] == ['Class1', 'Class2', 'Class3']


# =============================================================================
# Tests for enrich_skills_by_profile
# =============================================================================


def test_enrich_skills_by_profile_sets_structure():
    """enrich_skills_by_profile stores the dict on the module's enriched.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        skills_by_profile = {
            'implementation': ['pm-dev-java:java-core', 'pm-dev-java:java-cdi'],
            'unit-testing': ['pm-dev-java:java-core', 'pm-dev-java:junit-core'],
        }
        result = enrich_skills_by_profile('module-a', skills_by_profile, tmpdir)

        assert result['status'] == 'success'
        assert result['skills_by_profile'] == skills_by_profile

        enriched = load_module_enriched('module-a', tmpdir)
        assert enriched['skills_by_profile'] == skills_by_profile


def test_enrich_skills_by_profile_with_all_profile_types():
    """enrich_skills_by_profile handles all profile types."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        skills_by_profile = {
            'implementation': ['pm-dev-java:java-core'],
            'unit-testing': ['pm-dev-java:junit-core'],
            'integration-testing': ['pm-dev-java:junit-integration'],
            'benchmark-testing': ['pm-dev-java:java-core'],
        }
        result = enrich_skills_by_profile('module-a', skills_by_profile, tmpdir)

        assert result['status'] == 'success'
        assert len(result['skills_by_profile']) == 4


def test_enrich_skills_by_profile_with_reasoning():
    """enrich_skills_by_profile stores reasoning when provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        skills_by_profile = {'implementation': ['pm-dev-java:java-core']}
        enrich_skills_by_profile('module-a', skills_by_profile, tmpdir, reasoning='Pure Java library with no CDI')

        enriched = load_module_enriched('module-a', tmpdir)
        assert enriched['skills_by_profile_reasoning'] == 'Pure Java library with no CDI'


def test_enrich_skills_by_profile_unknown_module_raises():
    """enrich_skills_by_profile raises ModuleNotFoundInProjectError for unknown module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        try:
            enrich_skills_by_profile('nonexistent', {'implementation': []}, tmpdir)
            assert False, 'Should have raised ModuleNotFoundInProjectError'
        except ModuleNotFoundInProjectError:
            pass


def test_enrich_skills_by_profile_overwrites():
    """A second call overwrites the prior skills_by_profile structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        enrich_skills_by_profile('module-a', {'implementation': ['skill-1']}, tmpdir)
        enrich_skills_by_profile('module-a', {'implementation': ['skill-2']}, tmpdir)

        enriched = load_module_enriched('module-a', tmpdir)
        assert enriched['skills_by_profile']['implementation'] == ['skill-2']


def test_enrich_skills_by_profile_defaults_optionals_structure():
    """enrich_skills_by_profile accepts the structured defaults/optionals shape."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        skills_by_profile = {
            'implementation': {
                'defaults': [
                    {
                        'skill': 'pm-plugin-development:plugin-architecture',
                        'description': 'Architecture principles for building marketplace components',
                    }
                ],
                'optionals': [
                    {
                        'skill': 'pm-plugin-development:plugin-script-architecture',
                        'description': 'Script development standards covering implementation patterns',
                    },
                    {
                        'skill': 'plan-marshall:ref-toon-format',
                        'description': 'TOON format knowledge for output specifications',
                    },
                ],
            }
        }
        result = enrich_skills_by_profile('module-a', skills_by_profile, tmpdir)

        assert result['status'] == 'success'
        assert result['skills_by_profile'] == skills_by_profile

        enriched = load_module_enriched('module-a', tmpdir)
        stored = enriched['skills_by_profile']
        assert stored['implementation']['defaults'][0]['skill'] == 'pm-plugin-development:plugin-architecture'
        assert 'description' in stored['implementation']['defaults'][0]
        assert len(stored['implementation']['optionals']) == 2


def test_enrich_skills_by_profile_warns_on_missing_bundle_prefix():
    """enrich_skills_by_profile emits warnings when bundle:skill notation is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        skills_by_profile = {
            'implementation': {
                'defaults': [{'skill': 'plugin-architecture', 'description': 'Missing bundle prefix'}],
                'optionals': [],
            }
        }
        result = enrich_skills_by_profile('module-a', skills_by_profile, tmpdir)

        assert result['status'] == 'success'
        assert 'warnings' in result
        assert any('missing bundle:skill notation' in w for w in result['warnings'])


def test_enrich_skills_by_profile_warns_on_missing_description():
    """enrich_skills_by_profile emits warnings when description is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        skills_by_profile = {
            'implementation': {
                'defaults': [{'skill': 'pm-plugin-development:plugin-architecture'}],
                'optionals': [],
            }
        }
        result = enrich_skills_by_profile('module-a', skills_by_profile, tmpdir)

        assert result['status'] == 'success'
        assert 'warnings' in result
        assert any("missing 'description' field" in w for w in result['warnings'])


def test_enrich_skills_by_profile_empty_optionals_no_warnings():
    """Valid structure with empty optionals produces no warnings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        skills_by_profile = {
            'implementation': {
                'defaults': [
                    {'skill': 'pm-plugin-development:plugin-architecture', 'description': 'Architecture principles'}
                ],
                'optionals': [],
            }
        }
        result = enrich_skills_by_profile('module-a', skills_by_profile, tmpdir)

        assert result['status'] == 'success'
        assert 'warnings' not in result or len(result.get('warnings', [])) == 0

        enriched = load_module_enriched('module-a', tmpdir)
        stored = enriched['skills_by_profile']
        assert stored['implementation']['optionals'] == []


def test_enrich_skills_by_profile_mixed_format():
    """enrich_skills_by_profile accepts the structured format across multiple profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        skills_by_profile = {
            'implementation': {
                'defaults': [
                    {'skill': 'pm-plugin-development:plugin-architecture', 'description': 'Architecture principles'}
                ],
                'optionals': [],
            },
            'module_testing': {
                'defaults': [
                    {'skill': 'pm-plugin-development:plugin-architecture', 'description': 'Architecture principles'}
                ],
                'optionals': [],
            },
        }
        result = enrich_skills_by_profile('module-a', skills_by_profile, tmpdir)

        assert result['status'] == 'success'
        enriched = load_module_enriched('module-a', tmpdir)
        stored = enriched['skills_by_profile']
        assert isinstance(stored['implementation'], dict)
        assert isinstance(stored['module_testing'], dict)


# =============================================================================
# Tests for enrich_dependencies
# =============================================================================


def test_enrich_dependencies_sets_key():
    """enrich_dependencies stores key dependencies on the module's enriched.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        key_deps = ['org.example:dep1', 'org.example:dep2']
        result = enrich_dependencies('module-a', key_deps, None, tmpdir)

        assert result['status'] == 'success'
        assert result['key_dependencies'] == key_deps

        enriched = load_module_enriched('module-a', tmpdir)
        assert enriched['key_dependencies'] == key_deps


def test_enrich_dependencies_with_reasoning():
    """enrich_dependencies stores reasoning when provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        key_deps = ['de.cuioss:cui-java-tools']
        enrich_dependencies('module-a', key_deps, None, tmpdir, reasoning='Core utilities used throughout the module')

        enriched = load_module_enriched('module-a', tmpdir)
        assert enriched['key_dependencies_reasoning'] == 'Core utilities used throughout the module'


def test_enrich_dependencies_sets_internal():
    """enrich_dependencies stores internal_dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        internal_deps = ['module-b', 'module-c']
        result = enrich_dependencies('module-a', None, internal_deps, tmpdir)

        assert result['status'] == 'success'
        assert result['internal_dependencies'] == internal_deps


def test_enrich_dependencies_sets_both():
    """enrich_dependencies can set both key and internal in one call."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_dependencies('module-a', ['dep1'], ['mod-b'], tmpdir)

        assert 'key_dependencies' in result
        assert 'internal_dependencies' in result


# =============================================================================
# Tests for Dependency Cross-Check Validation
# =============================================================================


def _setup_project_with_deps(tmpdir: str, dependencies: list[str]) -> None:
    """Seed a single-module project whose derived.json has the given deps."""
    _seed_project(
        tmpdir,
        {
            'module-a': {
                'name': 'module-a',
                'build_systems': ['maven'],
                'paths': {'module': 'module-a'},
                'metadata': {},
                'packages': {},
                'dependencies': dependencies,
                'commands': {},
            }
        },
        with_enrichment_stubs=True,
    )


def test_enrich_dependencies_warns_on_unmatched():
    """enrich_dependencies warns when key_dep absent from declared deps."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _setup_project_with_deps(tmpdir, ['de.cuioss:cui-java-tools:compile'])

        key_deps = ['de.cuioss:cui-java-tools', 'com.nimbusds:nimbus-jose-jwt']
        result = enrich_dependencies('module-a', key_deps, None, tmpdir)

        assert result['status'] == 'success'
        assert 'warnings' in result
        assert len(result['warnings']) == 1
        assert 'nimbus-jose-jwt' in result['warnings'][0]


def test_enrich_dependencies_no_warning_when_all_match():
    """enrich_dependencies emits no warnings when every key_dep matches a declared dep."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _setup_project_with_deps(
            tmpdir,
            [
                'de.cuioss:cui-java-tools:compile',
                'io.quarkus:quarkus-core:compile',
            ],
        )

        key_deps = ['de.cuioss:cui-java-tools', 'io.quarkus:quarkus-core']
        result = enrich_dependencies('module-a', key_deps, None, tmpdir)

        assert result['status'] == 'success'
        assert 'warnings' not in result


def test_enrich_dependencies_warns_all_unmatched_against_empty():
    """enrich_dependencies warns on every key_dep when the module has no declared deps."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _setup_project_with_deps(tmpdir, [])

        key_deps = ['com.nimbusds:nimbus-jose-jwt']
        result = enrich_dependencies('module-a', key_deps, None, tmpdir)

        assert result['status'] == 'success'
        assert 'warnings' in result
        assert len(result['warnings']) == 1


def test_enrich_dependencies_persists_despite_warnings():
    """enrich_dependencies persists key_deps even when warnings are emitted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _setup_project_with_deps(tmpdir, [])

        key_deps = ['com.nimbusds:nimbus-jose-jwt']
        result = enrich_dependencies('module-a', key_deps, None, tmpdir)

        assert result['key_dependencies'] == key_deps
        enriched = load_module_enriched('module-a', tmpdir)
        assert enriched['key_dependencies'] == key_deps


# =============================================================================
# Tests for Array Append Commands
# =============================================================================


def test_enrich_tip_appends():
    """enrich_tip appends to tips array in the module's enriched.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_tip('module-a', 'Tip 1', tmpdir)
        assert result['tips'] == ['Tip 1']

        result = enrich_tip('module-a', 'Tip 2', tmpdir)
        assert result['tips'] == ['Tip 1', 'Tip 2']


def test_enrich_tip_no_duplicates():
    """enrich_tip does not append duplicate tips."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        enrich_tip('module-a', 'Same tip', tmpdir)
        result = enrich_tip('module-a', 'Same tip', tmpdir)

        assert result['tips'] == ['Same tip']


def test_enrich_insight_appends():
    """enrich_insight appends to insights array."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_insight('module-a', 'Insight 1', tmpdir)
        assert result['insights'] == ['Insight 1']


def test_enrich_best_practice_appends():
    """enrich_best_practice appends to best_practices array."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_best_practice('module-a', 'Practice 1', tmpdir)
        assert result['best_practices'] == ['Practice 1']


# =============================================================================
# Regression: tier-0 enrich discovery is memoized to a single worktree crawl
# =============================================================================
#
# History: ``enrich_all`` delegated every (module × domain) pair to
# ``enrich_add_domain`` -> ``_load_module_or_raise``, which re-ran
# ``iter_modules`` + ``load_module_derived`` — each a fresh
# ``crawl_all_modules`` over the whole worktree. With M modules and D applicable
# domains that is O(M × D) whole-worktree crawls per enrich invocation (the
# per-iteration discovery storm). The fix crawls once in ``enrich_all`` and
# threads the result through ``crawled_modules`` so discovery runs exactly once
# regardless of M × D.


class _FakeExtensionApplicable:
    """Minimal fake extension that applies to any module with a maven build."""

    def __init__(self, domain_key: str, bundle: str, skill_name: str):
        self._domain_key = domain_key
        self._bundle = bundle
        self._skill_name = skill_name

    def get_skill_domains(self) -> list[dict]:
        return [
            {
                'domain': {'key': self._domain_key, 'name': 'Fake Domain', 'description': 'Test fake domain'},
                'profiles': {
                    'implementation': {
                        'defaults': [
                            {'skill': f'{self._bundle}:{self._skill_name}', 'description': f'Fake from {self._bundle}'}
                        ],
                        'optionals': [],
                    }
                },
            }
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        if 'maven' in module_data.get('build_systems', []):
            return {
                'applicable': True,
                'confidence': 'high',
                'signals': ['has maven'],
                'additive_to': None,
                'skills_by_profile': {
                    'implementation': {
                        'defaults': [
                            {'skill': f'{self._bundle}:{self._skill_name}', 'description': f'Fake from {self._bundle}'}
                        ],
                        'optionals': [],
                    }
                },
            }
        return {
            'applicable': False,
            'confidence': 'none',
            'signals': [],
            'additive_to': None,
            'skills_by_profile': {},
        }


def _patch_extensions(monkeypatch: pytest.MonkeyPatch, extensions: list[dict]) -> None:
    """Patch ``discover_all_extensions`` at the extension_discovery module level.

    ``enrich_all`` and ``enrich_add_domain`` both import ``discover_all_extensions``
    inside their function bodies, so patching the module attribute reaches every
    call site.
    """
    import extension_discovery

    monkeypatch.setattr(extension_discovery, 'discover_all_extensions', lambda: extensions)


def _multi_module_maven_project() -> dict[str, dict]:
    """Three maven modules → multiple (module × domain) pairs in one enrich_all."""
    return {
        name: {
            'name': name,
            'build_systems': ['maven'],
            'paths': {'module': name},
            'metadata': {},
            'packages': {},
            'dependencies': [],
            'commands': {},
        }
        for name in ('module-a', 'module-b', 'module-c')
    }


def test_enrich_all_memoizes_module_discovery_to_single_crawl(monkeypatch):
    """enrich_all triggers exactly ONE whole-worktree crawl regardless of M × D.

    Spies on ``crawl_all_modules`` (the single discovery primitive that
    ``iter_modules`` and ``load_module_derived`` both fan out to). The
    memoization fix crawls once in ``enrich_all`` and threads the result via
    ``crawled_modules``, so the spy is hit exactly once. Against the pre-fix
    per-(module × domain) discovery, the spy would be hit many times (≥ 2 × M ×
    D) — once per ``iter_modules`` + ``load_module_derived`` inside every
    ``_load_module_or_raise`` call.
    """
    fake_ext = _FakeExtensionApplicable(
        domain_key='memo-domain', bundle='memo-bundle', skill_name='memo-skill'
    )
    _patch_extensions(monkeypatch, [{'bundle': 'memo-bundle', 'path': '/fake/path', 'module': fake_ext}])

    call_count = 0
    real_crawl = _cmd_enrich.crawl_all_modules

    def _counting_crawl(project_dir: str = '.'):
        nonlocal call_count
        call_count += 1
        return real_crawl(project_dir)

    monkeypatch.setattr(_cmd_enrich, 'crawl_all_modules', _counting_crawl)

    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir, modules=_multi_module_maven_project())

        result = enrich_all(tmpdir)

        assert result['status'] == 'success'
        # All three maven modules enriched by the single applicable domain.
        assert sorted(result['modules_enriched']) == ['module-a', 'module-b', 'module-c']
        # The memoization invariant: discovery ran exactly once for the whole
        # invocation, not once per (module × domain) pair.
        assert call_count == 1, (
            f'enrich_all crawled the worktree {call_count} times — expected exactly 1. '
            'The per-iteration discovery storm has regressed (crawled_modules is no '
            'longer threaded through _load_module_or_raise).'
        )


# =============================================================================
# Suppress unused-import lint warnings.
# =============================================================================


_ = (load_module_enriched_or_empty,)
