#!/usr/bin/env python3
"""Tests for ``enrich_add_domain()`` in ``_cmd_enrich.py``.

Pins the per-module on-disk layout: enrich_add_domain validates the module
via ``_project.json``'s index and writes only the touched module's
``enriched.json``. Legacy monolithic files are intentionally absent from
this surface.
"""

import importlib.util
import sys
import tempfile
from pathlib import Path

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

ModuleNotFoundInProjectError = _architecture_core.ModuleNotFoundInProjectError
save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
save_module_enriched = _architecture_core.save_module_enriched
load_module_enriched = _architecture_core.load_module_enriched
enrich_add_domain = _cmd_enrich.enrich_add_domain


# =============================================================================
# Helper Functions
# =============================================================================


def _extract_skill_names(profile_data: dict) -> list[str]:
    """Extract skill names from structured profile data."""
    skills = []
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
                'dependencies': ['jakarta.enterprise.cdi-api:jakarta.enterprise:compile'],
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
# Tests for enrich_add_domain
# =============================================================================


def test_add_domain_general_dev():
    """Add general-dev domain to a module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result = enrich_add_domain('module-a', 'general-dev', tmpdir)

        assert result['status'] == 'success'
        assert result['module'] == 'module-a'
        assert result['domain'] == 'general-dev'
        assert len(result['profiles_updated']) > 0
        assert 'skills_by_profile' in result


def test_add_domain_creates_profiles():
    """Adding a domain to empty skills_by_profile creates new profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result = enrich_add_domain('module-a', 'general-dev', tmpdir)

        sbp = result['skills_by_profile']
        assert 'implementation' in sbp or 'module_testing' in sbp


def test_add_domain_additive_merge():
    """Add java then general-dev: both domains' skills are present, deduped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        result1 = enrich_add_domain('module-a', 'java', tmpdir)
        assert result1['status'] == 'success'

        result2 = enrich_add_domain('module-a', 'general-dev', tmpdir)
        assert result2['status'] == 'success'

        sbp = result2['skills_by_profile']
        all_skills: list[str] = []
        for profile_data in sbp.values():
            if isinstance(profile_data, dict):
                for section in ['defaults', 'optionals']:
                    for entry in profile_data.get(section, []):
                        all_skills.append(entry.get('skill', entry) if isinstance(entry, dict) else entry)

        java_skills = [s for s in all_skills if 'pm-dev-java:' in str(s)]
        general_skills = [s for s in all_skills if 'plan-marshall:dev-general-' in str(s)]
        assert len(java_skills) > 0, 'Should have java skills'
        assert len(general_skills) > 0, 'Should have general-dev skills'


def test_add_domain_preserves_existing():
    """Adding a domain preserves skills from a prior domain add."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        enrich_add_domain('module-a', 'java', tmpdir)
        enriched_after_java = load_module_enriched('module-a', tmpdir)
        sbp_after_java = enriched_after_java['skills_by_profile'].copy()

        enrich_add_domain('module-a', 'general-dev', tmpdir)

        enriched_after_both = load_module_enriched('module-a', tmpdir)
        sbp_after_both = enriched_after_both['skills_by_profile']

        for profile, skills in sbp_after_java.items():
            if isinstance(skills, dict):
                existing_names = _extract_skill_names(skills)
                after_names = _extract_skill_names(sbp_after_both.get(profile, {}))
                for skill in existing_names:
                    assert skill in after_names, f'{skill} lost from {profile}'


def test_add_domain_include_optionals_true():
    """include_optionals=True adds optional skills."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result = enrich_add_domain('module-a', 'java', tmpdir, include_optionals=True)

        sbp = result['skills_by_profile']
        all_skills: list[str] = []
        for profile_data in sbp.values():
            if isinstance(profile_data, dict):
                all_skills.extend(_extract_skill_names(profile_data))

        assert len(all_skills) > 0


def test_add_domain_include_optionals_false_subset_of_true():
    """include_optionals=True returns at least as many skills as defaults-only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result_defaults = enrich_add_domain('module-a', 'java', tmpdir, include_optionals=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result_all = enrich_add_domain('module-a', 'java', tmpdir, include_optionals=True)

    count_defaults = sum(
        len(_extract_skill_names(v)) for v in result_defaults['skills_by_profile'].values() if isinstance(v, dict)
    )
    count_all = sum(
        len(_extract_skill_names(v)) for v in result_all['skills_by_profile'].values() if isinstance(v, dict)
    )
    assert count_all >= count_defaults


def test_add_domain_reasoning_appended():
    """Reasoning is appended to skills_by_profile_reasoning."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        enrich_add_domain('module-a', 'java', tmpdir, reasoning='java: maven build system')
        enrich_add_domain('module-a', 'general-dev', tmpdir, reasoning='general-dev: cross-cutting')

        enriched = load_module_enriched('module-a', tmpdir)
        reasoning = enriched['skills_by_profile_reasoning']
        assert 'java: maven build system' in reasoning
        assert 'general-dev: cross-cutting' in reasoning


def test_add_domain_system_rejected():
    """Adding the 'system' domain raises ValueError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        try:
            enrich_add_domain('module-a', 'system', tmpdir)
            assert False, 'Should have raised ValueError'
        except ValueError as e:
            assert 'system' in str(e)


def test_add_domain_nonexistent_domain():
    """Non-existent domain raises ValueError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        try:
            enrich_add_domain('module-a', 'nonexistent-domain-xyz', tmpdir)
            assert False, 'Should have raised ValueError'
        except ValueError as e:
            assert 'not found' in str(e).lower()


def test_add_domain_nonexistent_module():
    """Non-existent module raises ModuleNotFoundInProjectError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        try:
            enrich_add_domain('nonexistent-module', 'general-dev', tmpdir)
            assert False, 'Should have raised ModuleNotFoundInProjectError'
        except ModuleNotFoundInProjectError:
            pass
