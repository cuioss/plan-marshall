#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for ``enrich_add_domain()`` in ``_cmd_enrich.py``.

Pins the per-module on-disk layout: enrich_add_domain validates the module
via ``_project.json``'s index and writes only the touched module's
``enriched.json``. Legacy monolithic files are intentionally absent from
this surface.
"""

import sys
import tempfile
from pathlib import Path

import pytest

from conftest import load_script_module

sys.path.insert(0, str(Path(__file__).parent))

from _arch_fixtures import setup_test_project  # noqa: E402


_architecture_core = load_script_module('plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core')
_cmd_enrich = load_script_module('plan-marshall', 'manage-architecture', '_cmd_enrich.py', '_cmd_enrich')

ModuleNotFoundInProjectError = _architecture_core.ModuleNotFoundInProjectError
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


# ``setup_test_project`` hoisted to ``_fixtures.py`` (see top-of-file import).


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
        _GENERAL_DEV_SKILLS = {
            'plan-marshall:persona-plan-marshall-agent',
            'plan-marshall:ref-code-quality',
            'plan-marshall:persona-module-tester',
        }
        general_skills = [s for s in all_skills if str(s) in _GENERAL_DEV_SKILLS]
        assert len(java_skills) > 0, 'Should have java skills'
        assert len(general_skills) > 0, 'Should have general-dev skills (persona-plan-marshall-agent, ref-code-quality, persona-module-tester)'


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
        with pytest.raises(ValueError, match='system'):
            enrich_add_domain('module-a', 'system', tmpdir)


def test_add_domain_nonexistent_domain():
    """Non-existent domain raises ValueError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        with pytest.raises(ValueError, match='(?i)not found'):
            enrich_add_domain('module-a', 'nonexistent-domain-xyz', tmpdir)


def test_add_domain_nonexistent_module():
    """Non-existent module raises ModuleNotFoundInProjectError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        with pytest.raises(ModuleNotFoundInProjectError):
            enrich_add_domain('nonexistent-module', 'general-dev', tmpdir)
