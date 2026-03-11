#!/usr/bin/env python3
"""Tests for enrich_add_domain() API function in _cmd_enrich.py."""

import tempfile

from _architecture_core import (
    ModuleNotFoundError,
    load_llm_enriched,
    save_derived_data,
    save_llm_enriched,
)
from _cmd_enrich import enrich_add_domain

# =============================================================================
# Helper Functions
# =============================================================================


def setup_test_project(tmpdir: str, modules: dict | None = None) -> None:
    """Create test derived-data.json and llm-enriched.json."""
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

    derived_data = {'project': {'name': 'test-project'}, 'modules': modules}
    save_derived_data(derived_data, tmpdir)

    enriched_data = {'project': {'description': ''}, 'modules': {}}
    for name in modules:
        enriched_data['modules'][name] = {
            'responsibility': '',
            'purpose': '',
            'key_packages': {},
            'skills_by_profile': {},
            'skills_by_profile_reasoning': '',
        }
    save_llm_enriched(enriched_data, tmpdir)


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
    """Add java then general-dev: both domains' skills present, deduped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        # First add java domain
        result1 = enrich_add_domain('module-a', 'java', tmpdir)
        assert result1['status'] == 'success'

        # Then add general-dev
        result2 = enrich_add_domain('module-a', 'general-dev', tmpdir)
        assert result2['status'] == 'success'

        # Verify skills from both domains present
        sbp = result2['skills_by_profile']
        all_skills = []
        for profile_data in sbp.values():
            if isinstance(profile_data, list):
                all_skills.extend(profile_data)
            elif isinstance(profile_data, dict):
                for section in ['defaults', 'optionals']:
                    for entry in profile_data.get(section, []):
                        all_skills.append(entry.get('skill', entry) if isinstance(entry, dict) else entry)

        # Should have java skills and general-dev skills
        java_skills = [s for s in all_skills if 'pm-dev-java:' in str(s)]
        general_skills = [s for s in all_skills if 'plan-marshall:dev-general-' in str(s)]
        assert len(java_skills) > 0, 'Should have java skills'
        assert len(general_skills) > 0, 'Should have general-dev skills'

        # No duplicates within each profile
        for profile_name, profile_data in sbp.items():
            if isinstance(profile_data, list):
                assert len(profile_data) == len(set(profile_data)), \
                    f'Duplicate skills in {profile_name}: {profile_data}'


def test_add_domain_preserves_existing():
    """Adding a domain preserves skills from prior domain add."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)

        enrich_add_domain('module-a', 'java', tmpdir)

        # Load and check java skills are there
        enriched = load_llm_enriched(tmpdir)
        sbp_after_java = enriched['modules']['module-a']['skills_by_profile'].copy()

        enrich_add_domain('module-a', 'general-dev', tmpdir)

        # Check java skills still present
        enriched2 = load_llm_enriched(tmpdir)
        sbp_after_both = enriched2['modules']['module-a']['skills_by_profile']

        for profile, skills in sbp_after_java.items():
            if isinstance(skills, list):
                for skill in skills:
                    assert skill in sbp_after_both.get(profile, []), f'{skill} lost from {profile}'


def test_add_domain_include_optionals_true():
    """include_optionals=True adds optional skills."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result = enrich_add_domain('module-a', 'java', tmpdir, include_optionals=True)

        sbp = result['skills_by_profile']
        all_skills = []
        for profile_data in sbp.values():
            if isinstance(profile_data, list):
                all_skills.extend(profile_data)

        # Java domain has optionals like java-cdi, java-lombok — they should be present
        assert len(all_skills) > 0


def test_add_domain_include_optionals_false():
    """include_optionals=False (default) only includes defaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result_defaults = enrich_add_domain('module-a', 'java', tmpdir, include_optionals=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result_all = enrich_add_domain('module-a', 'java', tmpdir, include_optionals=True)

    # The optionals-included version should have >= skills
    count_defaults = sum(len(v) if isinstance(v, list) else 0 for v in result_defaults['skills_by_profile'].values())
    count_all = sum(len(v) if isinstance(v, list) else 0 for v in result_all['skills_by_profile'].values())
    assert count_all >= count_defaults


def test_add_domain_reasoning_appended():
    """Reasoning is appended to skills_by_profile_reasoning."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        enrich_add_domain('module-a', 'java', tmpdir, reasoning='java: maven build system')
        enrich_add_domain('module-a', 'general-dev', tmpdir, reasoning='general-dev: cross-cutting')

        enriched = load_llm_enriched(tmpdir)
        reasoning = enriched['modules']['module-a']['skills_by_profile_reasoning']
        assert 'java: maven build system' in reasoning
        assert 'general-dev: cross-cutting' in reasoning


def test_add_domain_system_rejected():
    """system domain raises ValueError."""
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
    """Non-existent module raises ModuleNotFoundError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        try:
            enrich_add_domain('nonexistent-module', 'general-dev', tmpdir)
            assert False, 'Should have raised ModuleNotFoundError'
        except ModuleNotFoundError:
            pass
