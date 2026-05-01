#!/usr/bin/env python3
"""Tests for ``enrich_all()`` and ``cmd_enrich_all()`` in ``_cmd_enrich.py``.

Pins the per-module on-disk layout: enrich_all iterates ``_project.json``'s
``modules`` index and writes per-module ``enriched.json`` files via
``enrich_add_domain()``. Legacy monolithic files are intentionally absent
from this surface.
"""

import importlib.util
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-architecture' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_architecture_core = _load_module('_architecture_core', '_architecture_core.py')
_cmd_enrich = _load_module('_cmd_enrich', '_cmd_enrich.py')

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
save_module_enriched = _architecture_core.save_module_enriched
load_module_enriched = _architecture_core.load_module_enriched
enrich_all = _cmd_enrich.enrich_all
cmd_enrich_all = _cmd_enrich.cmd_enrich_all


# =============================================================================
# Helper Functions
# =============================================================================


def _extract_skill_names(profile_data: dict) -> list[str]:
    """Extract skill names from structured profile data."""
    skills = []
    if not isinstance(profile_data, dict):
        return skills
    for section in ['defaults', 'optionals']:
        for entry in profile_data.get(section, []):
            skills.append(entry.get('skill', entry) if isinstance(entry, dict) else entry)
    return skills


def _empty_enrichment_stub() -> dict:
    return {
        'responsibility': '',
        'purpose': '',
        'key_packages': {},
        'skills_by_profile': {},
        'skills_by_profile_reasoning': '',
    }


def setup_test_project(tmpdir: str, modules: dict | None = None) -> None:
    """Seed ``_project.json`` plus per-module ``derived.json`` and empty
    ``enriched.json`` stubs for every module."""
    if modules is None:
        modules = {
            'module-a': {
                'name': 'module-a',
                'build_systems': ['maven'],
                'paths': {'module': 'module-a', 'sources': ['src/main/java'], 'tests': ['src/test/java']},
                'metadata': {},
                'packages': {},
                'dependencies': [],
                'commands': {},
                'stats': {'source_files': 10, 'test_files': 5},
            }
        }

    save_project_meta(
        {
            'name': 'test-project',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {name: {} for name in modules},
        },
        tmpdir,
    )
    for name, data in modules.items():
        save_module_derived(name, data, tmpdir)
        save_module_enriched(name, _empty_enrichment_stub(), tmpdir)


# =============================================================================
# Fake Extension Infrastructure
# =============================================================================


def _build_skills_by_profile(bundle: str, skill_name: str) -> dict:
    """Build a minimal skills_by_profile dict for a fake extension."""
    return {
        'implementation': {
            'defaults': [
                {'skill': f'{bundle}:{skill_name}', 'description': f'Fake skill from {bundle}'},
            ],
            'optionals': [],
        },
    }


class _FakeExtensionApplicable:
    """Fake extension that applies to modules with a given build system."""

    def __init__(
        self,
        domain_key: str = 'fake-domain',
        bundle: str = 'fake-bundle',
        skill_name: str = 'fake-skill',
        required_build_system: str = 'maven',
    ):
        self._domain_key = domain_key
        self._bundle = bundle
        self._skill_name = skill_name
        self._required_build_system = required_build_system

    def get_skill_domains(self) -> list[dict]:
        return [
            {
                'domain': {
                    'key': self._domain_key,
                    'name': 'Fake Domain',
                    'description': 'Test fake domain',
                },
                'profiles': {
                    'implementation': {
                        'defaults': [
                            {
                                'skill': f'{self._bundle}:{self._skill_name}',
                                'description': f'Fake skill from {self._bundle}',
                            }
                        ],
                        'optionals': [],
                    }
                },
            }
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        build_systems = module_data.get('build_systems', [])
        if self._required_build_system in build_systems:
            return {
                'applicable': True,
                'confidence': 'high',
                'signals': [f'has {self._required_build_system}'],
                'additive_to': None,
                'skills_by_profile': _build_skills_by_profile(self._bundle, self._skill_name),
            }
        return {
            'applicable': False,
            'confidence': 'none',
            'signals': [],
            'additive_to': None,
            'skills_by_profile': {},
        }


class _FakeExtensionRaises:
    """Fake extension whose get_skill_domains() raises."""

    def get_skill_domains(self) -> list[dict]:
        raise RuntimeError('boom: get_skill_domains failed')

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        return {
            'applicable': False,
            'confidence': 'none',
            'signals': [],
            'additive_to': None,
            'skills_by_profile': {},
        }


def _patch_extensions(monkeypatch: pytest.MonkeyPatch, extensions: list[dict]) -> None:
    """Patch discover_all_extensions at the extension_discovery module level.

    enrich_all and enrich_add_domain both import discover_all_extensions
    inside their function bodies, so patching the module attribute reaches
    every call site.
    """
    import extension_discovery

    monkeypatch.setattr(extension_discovery, 'discover_all_extensions', lambda: extensions)


# =============================================================================
# Tests for enrich_all
# =============================================================================


def test_enrich_all_all_applicable(monkeypatch):
    """Single module with applicable fake extension → enriched, pairs_applied > 0."""
    fake_ext = _FakeExtensionApplicable(
        domain_key='fake-java',
        bundle='fake-java-bundle',
        skill_name='fake-java-core',
        required_build_system='maven',
    )
    _patch_extensions(monkeypatch, [{'bundle': 'fake-java-bundle', 'path': '/fake/path', 'module': fake_ext}])

    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_all(tmpdir)

        assert result['status'] == 'success'
        assert 'module-a' in result['modules_enriched']
        assert result['pairs_applied'] > 0
        assert result['errors'] == []

        # Verify per-module enriched.json was updated.
        enriched = load_module_enriched('module-a', tmpdir)
        sbp = enriched['skills_by_profile']
        assert sbp, 'skills_by_profile should be non-empty'
        all_names: list[str] = []
        for profile_data in sbp.values():
            all_names.extend(_extract_skill_names(profile_data))
        assert any('fake-java-core' in s for s in all_names), f'Expected fake-java-core in {all_names}'


def test_enrich_all_mixed_applicability(monkeypatch):
    """Two modules: one applicable (maven), one not (unknown). Only applicable enriched."""
    fake_applicable = _FakeExtensionApplicable(
        domain_key='fake-maven',
        bundle='fake-maven-bundle',
        skill_name='fake-maven-skill',
        required_build_system='maven',
    )
    _patch_extensions(monkeypatch, [{'bundle': 'fake-maven-bundle', 'path': '/fake/path', 'module': fake_applicable}])

    modules = {
        'applicable-mod': {
            'name': 'applicable-mod',
            'build_systems': ['maven'],
            'paths': {'module': 'applicable-mod'},
            'metadata': {},
            'packages': {},
            'dependencies': [],
            'commands': {},
        },
        'other-mod': {
            'name': 'other-mod',
            'build_systems': ['unknown'],
            'paths': {'module': 'other-mod'},
            'metadata': {},
            'packages': {},
            'dependencies': [],
            'commands': {},
        },
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir, modules=modules)

        result = enrich_all(tmpdir)

        assert result['status'] == 'success'
        assert 'applicable-mod' in result['modules_enriched']
        assert 'other-mod' not in result['modules_enriched']
        assert result['pairs_skipped'] > 0
        assert result['errors'] == []


def test_enrich_all_idempotent(monkeypatch):
    """Running enrich_all twice: second run produces pairs_applied == 0."""
    fake_ext = _FakeExtensionApplicable(
        domain_key='idem-domain',
        bundle='idem-bundle',
        skill_name='idem-skill',
        required_build_system='maven',
    )
    _patch_extensions(monkeypatch, [{'bundle': 'idem-bundle', 'path': '/fake/path', 'module': fake_ext}])

    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        first = enrich_all(tmpdir)
        assert first['status'] == 'success'
        assert first['pairs_applied'] > 0
        assert first['errors'] == []

        second = enrich_all(tmpdir)
        assert second['status'] == 'success'
        assert second['pairs_applied'] == 0, 'Second run should not add duplicates'
        assert second['errors'] == []

        enriched = load_module_enriched('module-a', tmpdir)
        sbp = enriched['skills_by_profile']
        for profile_data in sbp.values():
            names = _extract_skill_names(profile_data)
            assert len(names) == len(set(names)), f'Duplicate skills detected: {names}'


def test_enrich_all_extension_exception_captured(monkeypatch):
    """Extension raising in get_skill_domains() is captured in summary.errors."""
    raising_ext = _FakeExtensionRaises()
    _patch_extensions(monkeypatch, [{'bundle': 'raising-bundle', 'path': '/fake/path', 'module': raising_ext}])

    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_all(tmpdir)

        assert result['status'] == 'success'
        assert result['errors'], 'Expected at least one captured error'
        assert any('raising-bundle' in str(err) for err in result['errors']), (
            f"Expected bundle name in errors, got: {result['errors']}"
        )
        assert result['modules_enriched'] == []
        assert result['pairs_applied'] == 0


def test_enrich_all_missing_project_meta():
    """CLI wrapper returns data_not_found when ``_project.json`` is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Do NOT call setup_test_project — tmpdir is empty.
        args = SimpleNamespace(project_dir=tmpdir, include_optionals=False, reasoning=None)

        result = cmd_enrich_all(args)

        assert result['status'] == 'error'
        assert result['error'] == 'data_not_found'
        assert 'expected_file' in result


def test_enrich_all_empty_extension_list(monkeypatch):
    """No extensions: pairs_applied == 0, pairs_skipped == 0, modules_enriched == []."""
    _patch_extensions(monkeypatch, [])

    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result = enrich_all(tmpdir)

        assert result['status'] == 'success'
        assert result['pairs_applied'] == 0
        assert result['pairs_skipped'] == 0
        assert result['modules_enriched'] == []
        assert result['errors'] == []
