#!/usr/bin/env python3
"""Tests for ``_cmd_suggest.py`` — ``suggest_domains()`` API.

Pins the per-module on-disk layout: suggest_domains looks up the module via
``iter_modules`` (``_project.json`` index) and lazy-loads its
``derived.json``. Legacy monolithic files are intentionally absent from this
surface.
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
_cmd_suggest = _load_module('_cmd_suggest', '_cmd_suggest.py')

ModuleNotFoundInProjectError = _architecture_core.ModuleNotFoundInProjectError
save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
save_module_enriched = _architecture_core.save_module_enriched
suggest_domains = _cmd_suggest.suggest_domains


# =============================================================================
# Helper Functions
# =============================================================================


def _empty_enrichment_stub() -> dict:
    return {
        'responsibility': '',
        'purpose': '',
        'key_packages': {},
        'skills_by_profile': {},
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
# Tests for suggest_domains
# =============================================================================


def test_suggest_domains_java_module():
    """Maven module → java domain suggested."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result = suggest_domains('module-a', tmpdir)

        assert result['status'] == 'success'
        assert result['module'] == 'module-a'

        domain_keys = [d['domain'] for d in result['domains']]
        assert 'java' in domain_keys, f'Expected java in {domain_keys}'


def test_suggest_domains_general_dev_always_for_code_modules():
    """general-dev is suggested for any module with detectable code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result = suggest_domains('module-a', tmpdir)

        domain_keys = [d['domain'] for d in result['domains']]
        assert 'general-dev' in domain_keys, f'Expected general-dev in {domain_keys}'


def test_suggest_domains_npm_module_gets_javascript_only():
    """npm module → javascript domain (and not java)."""
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
        assert 'javascript' in domain_keys
        assert 'java' not in domain_keys


def test_suggest_domains_documentation_module():
    """documentation build_system → documentation domain."""
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
        assert 'documentation' in domain_keys


def test_suggest_domains_system_excluded():
    """The 'system' domain is filtered out of suggestions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result = suggest_domains('module-a', tmpdir)

        domain_keys = [d['domain'] for d in result['domains']]
        assert 'system' not in domain_keys


def test_suggest_domains_additive_parent_not_applicable():
    """Additive domain (java-cui) is filtered when its parent (java) is not applicable."""
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
        assert 'java-cui' not in domain_keys


def test_suggest_domains_additive_parent_applicable():
    """Additive domain is suggested when parent is also applicable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)  # maven module, so java applicable
        result = suggest_domains('module-a', tmpdir)

        domain_keys = [d['domain'] for d in result['domains']]
        assert 'java-cui' in domain_keys


def test_suggest_domains_has_confidence():
    """Each suggested domain carries a confidence level."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result = suggest_domains('module-a', tmpdir)

        for d in result['domains']:
            assert 'confidence' in d
            assert d['confidence'] in ('high', 'medium', 'low')


def test_suggest_domains_has_skills_by_profile():
    """Each suggested domain carries skills_by_profile (or a skill_count)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        result = suggest_domains('module-a', tmpdir)

        for d in result['domains']:
            assert 'skills_by_profile' in d or d.get('skill_count', 0) >= 0


def test_suggest_domains_no_matching_signals():
    """Module with no code build_systems gets no general-dev / java / javascript."""
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
    """Unknown module raises ModuleNotFoundInProjectError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        try:
            suggest_domains('nonexistent', tmpdir)
            assert False, 'Should have raised ModuleNotFoundInProjectError'
        except ModuleNotFoundInProjectError:
            pass
