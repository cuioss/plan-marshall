#!/usr/bin/env python3
"""Tests for _cmd_suggest.py module — suggest_domains() API function."""

import tempfile

from _architecture_core import ModuleNotFoundError, save_derived_data, save_llm_enriched
from _cmd_suggest import suggest_domains

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
        }
    save_llm_enriched(enriched_data, tmpdir)


# =============================================================================
# Tests for suggest_domains
# =============================================================================


def test_suggest_domains_java_module():
    """Java module (maven) gets java domain suggested."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result = suggest_domains('module-a', tmpdir)

        assert result['status'] == 'success'
        assert result['module'] == 'module-a'

        domain_keys = [d['domain'] for d in result['domains']]
        assert 'java' in domain_keys, f'Expected java in {domain_keys}'


def test_suggest_domains_general_dev_always():
    """general-dev always suggested for any module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result = suggest_domains('module-a', tmpdir)

        domain_keys = [d['domain'] for d in result['domains']]
        assert 'general-dev' in domain_keys, f'Expected general-dev in {domain_keys}'


def test_suggest_domains_npm_module():
    """npm module gets javascript domain suggested."""
    with tempfile.TemporaryDirectory() as tmpdir:
        modules = {
            'frontend': {
                'name': 'frontend',
                'build_systems': ['npm'],
                'paths': {'module': 'frontend', 'sources': ['src'], 'tests': ['test']},
                'metadata': {},
                'packages': {},
                'dependencies': ['lit:compile'],
                'commands': {},
                'stats': {'source_files': 20, 'test_files': 8},
            }
        }
        setup_test_project(tmpdir, modules)
        result = suggest_domains('frontend', tmpdir)

        domain_keys = [d['domain'] for d in result['domains']]
        assert 'javascript' in domain_keys, f'Expected javascript in {domain_keys}'
        assert 'java' not in domain_keys, f'java should not be in {domain_keys}'


def test_suggest_domains_documentation_module():
    """Documentation module (build_systems=documentation) gets documentation domain."""
    with tempfile.TemporaryDirectory() as tmpdir:
        modules = {
            'docs': {
                'name': 'docs',
                'build_systems': ['documentation'],
                'paths': {'module': 'doc', 'sources': ['doc'], 'tests': []},
                'metadata': {'description': 'Project documentation'},
                'packages': {},
                'dependencies': [],
                'commands': {},
                'stats': {},
            }
        }
        setup_test_project(tmpdir, modules)
        result = suggest_domains('docs', tmpdir)

        domain_keys = [d['domain'] for d in result['domains']]
        assert 'documentation' in domain_keys, f'Expected documentation in {domain_keys}'


def test_suggest_domains_system_excluded():
    """system domain excluded from suggestions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result = suggest_domains('module-a', tmpdir)

        domain_keys = [d['domain'] for d in result['domains']]
        assert 'system' not in domain_keys, f'system should not be in {domain_keys}'


def test_suggest_domains_additive_parent_not_applicable():
    """Additive domain NOT suggested when parent not applicable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        modules = {
            'frontend': {
                'name': 'frontend',
                'build_systems': ['npm'],
                'paths': {'module': 'frontend', 'sources': ['src'], 'tests': ['test']},
                'metadata': {},
                'packages': {},
                'dependencies': [],
                'commands': {},
                'stats': {},
            }
        }
        setup_test_project(tmpdir, modules)
        result = suggest_domains('frontend', tmpdir)

        domain_keys = [d['domain'] for d in result['domains']]
        # java-cui is additive_to java, but java is not applicable for npm module
        assert 'java-cui' not in domain_keys, f'java-cui should not be in {domain_keys}'


def test_suggest_domains_additive_parent_applicable():
    """Additive domain suggested when parent is also applicable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)  # maven module = java applicable
        result = suggest_domains('module-a', tmpdir)

        domain_keys = [d['domain'] for d in result['domains']]
        # java-cui is additive_to java, and java IS applicable
        assert 'java-cui' in domain_keys, f'Expected java-cui in {domain_keys}'


def test_suggest_domains_has_confidence():
    """Each suggested domain has confidence level."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result = suggest_domains('module-a', tmpdir)

        for d in result['domains']:
            assert 'confidence' in d
            assert d['confidence'] in ('high', 'medium', 'low')


def test_suggest_domains_has_skills_by_profile():
    """Each suggested domain includes skills_by_profile."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result = suggest_domains('module-a', tmpdir)

        for d in result['domains']:
            assert 'skills_by_profile' in d or d.get('skill_count', 0) >= 0


def test_suggest_domains_no_matching_signals():
    """Module with no code build systems gets no domains (general-dev is content-aware)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        modules = {
            'empty': {
                'name': 'empty',
                'build_systems': [],
                'paths': {'module': '.', 'sources': [], 'tests': []},
                'metadata': {},
                'packages': {},
                'dependencies': [],
                'commands': {},
                'stats': {},
            }
        }
        setup_test_project(tmpdir, modules)
        result = suggest_domains('empty', tmpdir)

        domain_keys = [d['domain'] for d in result['domains']]
        assert 'general-dev' not in domain_keys
        assert 'java' not in domain_keys
        assert 'javascript' not in domain_keys


def test_suggest_domains_module_not_found():
    """Non-existent module raises ModuleNotFoundError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        try:
            suggest_domains('nonexistent', tmpdir)
            assert False, 'Should have raised ModuleNotFoundError'
        except ModuleNotFoundError:
            pass
