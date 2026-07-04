#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for ``_cmd_manage.py`` — discover, init, derived, derived-module.

Pins the per-module on-disk layout: ``_project.json`` is the canonical module
index and per-module ``derived.json`` / ``enriched.json`` files hold module
data. The legacy monolithic files are intentionally absent from this test
surface.
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

from conftest import load_script_module

sys.path.insert(0, str(Path(__file__).parent))

from _arch_fixtures import create_test_project  # noqa: E402


_architecture_core = load_script_module('plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core')
_cmd_manage = load_script_module('plan-marshall', 'manage-architecture', '_cmd_manage.py', '_cmd_manage')

DataNotFoundError = _architecture_core.DataNotFoundError
ModuleNotFoundInProjectError = _architecture_core.ModuleNotFoundInProjectError

save_project_meta = _architecture_core.save_project_meta
load_module_enriched = _architecture_core.load_module_enriched
load_module_enriched_or_empty = _architecture_core.load_module_enriched_or_empty
get_module_enriched_path = _architecture_core.get_module_enriched_path
get_project_meta_path = _architecture_core.get_project_meta_path

api_discover = _cmd_manage.api_discover
api_get_derived = _cmd_manage.api_get_derived
api_get_derived_module = _cmd_manage.api_get_derived_module
api_init = _cmd_manage.api_init
list_modules = _cmd_manage.list_modules
save_module_enriched = _architecture_core.save_module_enriched


# Helper definitions hoisted to ``_fixtures.py`` (see top-of-file import).


# =============================================================================
# Tests for api_init
# =============================================================================


def test_api_init_creates_per_module_enriched_files():
    """api_init writes ``{module}/enriched.json`` for every indexed module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir, shape='metadata_rich')

        result = api_init(tmpdir)

        assert result['status'] == 'success'
        assert result['modules_initialized'] == 2
        # output_file is the project meta — the canonical anchor.
        assert result['output_file'] == str(get_project_meta_path(tmpdir))

        # Per-module enriched files exist with the canonical empty stub shape.
        for name in ('module-a', 'module-b'):
            path = get_module_enriched_path(name, tmpdir)
            assert path.exists()
            data = json.loads(path.read_text())
            assert 'responsibility' in data
            assert 'purpose' in data
            assert 'key_packages' in data


def test_api_init_check_existing_reports_count():
    """api_init(check=True) reports how many per-module enriched files exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir, shape='metadata_rich')
        api_init(tmpdir)  # populate stubs

        result = api_init(tmpdir, check=True)

        assert result['status'] == 'exists'
        assert result['modules_enriched'] == 2


def test_api_init_check_missing_reports_missing():
    """api_init(check=True) reports missing when ``_project.json`` is absent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = api_init(tmpdir, check=True)
        assert result['status'] == 'missing'


def test_api_init_no_overwrite_when_already_initialised():
    """Re-running api_init without force is a no-op for already-initialised modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir, shape='metadata_rich')
        api_init(tmpdir)

        result = api_init(tmpdir)

        # Both modules already have enriched.json so 0 are re-initialised.
        assert result['status'] == 'success'
        assert result['modules_initialized'] == 0


def test_api_init_force_overwrites_existing():
    """api_init(force=True) re-initialises every module's ``enriched.json``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir, shape='metadata_rich')
        api_init(tmpdir)

        # Mutate one to detect that force truly overwrites.
        from _architecture_core import save_module_enriched

        save_module_enriched('module-a', {'responsibility': 'custom'}, tmpdir)
        assert load_module_enriched('module-a', tmpdir)['responsibility'] == 'custom'

        result = api_init(tmpdir, force=True)
        assert result['status'] == 'success'
        assert result['modules_initialized'] == 2

        # The mutation has been clobbered back to the empty stub.
        assert load_module_enriched('module-a', tmpdir)['responsibility'] == ''


def test_api_init_missing_project_meta_returns_error():
    """api_init returns error when ``_project.json`` is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = api_init(tmpdir)

        assert result['status'] == 'error'
        assert 'discover' in result.get('error', '').lower()


# =============================================================================
# Tests for api_discover
# =============================================================================


def test_api_discover_preserves_enrichment(monkeypatch):
    """api_discover(force=True) preserves curated enriched.json for known modules.

    Regression test for lesson 2026-05-01-21-001: prior to the fix,
    re-running ``architecture discover --force`` overwrote every module's
    ``enriched.json`` with the empty stub, silently destroying LLM-authored
    responsibility / key_packages / skills_by_profile content. The current
    contract is: if a module already has an ``enriched.json`` (even one
    surviving the tmp+swap because it was loaded BEFORE the swap), its
    content must round-trip byte-for-byte through the discover run. New
    modules — those with no prior enrichment — still receive the canonical
    empty stub.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Seed an existing layout so api_discover's preservation branch has
        # something to read from. The pre-seeded modules['module-a'] gets
        # curated enrichment; 'module-c' is added later by the mocked
        # discovery to exercise the fresh-module fallback.
        create_test_project(tmpdir, shape='metadata_rich')

        curated = {
            'responsibility': 'Authoritative HTTP adapter for upstream auth',
            'responsibility_reasoning': 'Derived from package layout and CDI scopes',
            'purpose': 'Bridge OAuth provider responses into typed domain results',
            'purpose_reasoning': 'Inferred from public API surface',
            'key_packages': {
                'com.example.a.adapter': {
                    'role': 'Adapter layer',
                    'highlights': ['HttpHandler', 'HttpResult'],
                },
            },
            'internal_dependencies': ['module-b'],
            'key_dependencies': ['org.example:dep1'],
            'key_dependencies_reasoning': 'Pinned for reproducibility',
            'skills_by_profile': {
                'implementation': ['pm-dev-java-cui:cui-http'],
                'module_testing': ['pm-dev-java:junit-core'],
            },
            'skills_by_profile_reasoning': 'Matches CUI HTTP testing standard',
            'tips': ['Always wrap upstream calls in HttpResult'],
            'insights': ['Provider responses fan out into 3 result types'],
            'best_practices': ['Inject HttpHandler via constructor'],
        }
        save_module_enriched('module-a', curated, tmpdir)

        # Sanity check: the curated content is on disk before discover runs.
        assert load_module_enriched('module-a', tmpdir) == curated

        # Replace the heavy discovery delegate with a deterministic stub that
        # returns the same module-a (which has prior enrichment) plus a brand
        # new module-c (which has none). The api_discover function imports
        # extension_discovery lazily inside its body, so monkeypatching the
        # already-loaded module is sufficient — no need to manipulate
        # sys.modules.
        import extension_discovery

        def _fake_discover(_project_root):
            return {
                'modules': {
                    'module-a': {
                        'name': 'module-a',
                        'build_systems': ['maven'],
                        'paths': {'module': 'module-a'},
                        'metadata': {},
                        'packages': {},
                        'dependencies': [],
                        'stats': {},
                        'commands': {},
                    },
                    'module-c': {
                        'name': 'module-c',
                        'build_systems': ['maven'],
                        'paths': {'module': 'module-c'},
                        'metadata': {},
                        'packages': {},
                        'dependencies': [],
                        'stats': {},
                        'commands': {},
                    },
                },
                'extensions_used': ['pm-dev-java'],
            }

        monkeypatch.setattr(extension_discovery, 'discover_project_modules', _fake_discover)

        result = api_discover(tmpdir, force=True)

        assert result['status'] == 'success'
        assert result['modules_discovered'] == 2

        # Positive branch: module-a's curated enrichment survived the swap
        # byte-for-byte. JSON round-trips dict equality, which is sufficient
        # to prove no field was clobbered, reordered, or coerced.
        assert load_module_enriched('module-a', tmpdir) == curated

        # Negative branch: module-c had no prior enrichment, so it gets the
        # canonical empty stub shape. This guards against the opposite
        # regression — preservation accidentally skipping fresh modules.
        fresh = load_module_enriched('module-c', tmpdir)
        assert fresh['responsibility'] == ''
        assert fresh['purpose'] == ''
        assert fresh['key_packages'] == {}
        assert fresh['skills_by_profile'] == {}
        # Spot-check a few more empty-stub fields so a future shape change
        # to _empty_module_enrichment fails this test loudly.
        assert fresh['internal_dependencies'] == []
        assert fresh['tips'] == []


# =============================================================================
# Tests for api_get_derived
# =============================================================================


def test_api_get_derived_assembles_legacy_shape():
    """api_get_derived re-assembles ``{project, modules, extensions_used}``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir, shape='metadata_rich')

        result = api_get_derived(tmpdir)

        assert result['project']['name'] == 'test-project'
        assert 'module-a' in result['modules']
        assert 'module-b' in result['modules']
        assert result['modules']['module-a']['build_systems'] == ['maven']
        assert 'extensions_used' in result


def test_api_get_derived_missing_meta_raises():
    """api_get_derived raises DataNotFoundError when ``_project.json`` is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(DataNotFoundError):
            api_get_derived(tmpdir)


def test_api_get_derived_module_missing_derived_returns_empty_modules():
    """An indexed module with no live filesystem presence does NOT surface.

    Under the on-demand crawl model api_get_derived computes the modules
    dict from the live filesystem crawl — _project.json's index is no
    longer the source of truth. A module listed in the index but absent
    from the live crawl simply does not appear in the result.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # _project.json lists 'gone' but no derived.json or real module exists.
        save_project_meta(
            {'name': 'p', 'description': '', 'modules': {'gone': {}}, 'extensions_used': []},
            tmpdir,
        )

        result = api_get_derived(tmpdir)

        # Under the on-demand crawl the index is no longer consulted; 'gone'
        # is absent from the modules dict.
        assert result['modules'] == {}


# =============================================================================
# Tests for api_get_derived_module
# =============================================================================


def test_api_get_derived_module_returns_single_module_dict():
    """api_get_derived_module returns one module's derived dict."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir, shape='metadata_rich')

        result = api_get_derived_module('module-a', tmpdir)

        assert result['name'] == 'module-a'
        assert result['build_systems'] == ['maven']
        assert 'com.example.a' in result['packages']


def test_api_get_derived_module_unknown_module_raises():
    """api_get_derived_module raises ModuleNotFoundInProjectError for unknown name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir, shape='metadata_rich')

        with pytest.raises(ModuleNotFoundInProjectError):
            api_get_derived_module('nonexistent', tmpdir)


def test_api_get_derived_module_missing_from_crawl_raises_module_not_found():
    """api_get_derived_module raises when the module is absent from the live crawl.

    Under the on-demand crawl model the index is no longer consulted —
    a module listed in _project.json but absent from the live filesystem
    surfaces as ModuleNotFoundInProjectError (the "module not found in
    crawl" case), not as DataNotFoundError.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        save_project_meta(
            {'name': 'p', 'description': '', 'modules': {'gone': {}}, 'extensions_used': []},
            tmpdir,
        )

        with pytest.raises(ModuleNotFoundInProjectError):
            api_get_derived_module('gone', tmpdir)


# =============================================================================
# Tests for list_modules
# =============================================================================


def test_list_modules_returns_index_keys():
    """list_modules returns the sorted module names from ``_project.json``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir, shape='metadata_rich')

        result = list_modules(tmpdir)

        assert sorted(result) == ['module-a', 'module-b']


def test_list_modules_missing_meta_returns_empty():
    """list_modules returns an empty list when the crawl finds no modules.

    Under the on-demand crawl model list_modules calls iter_modules which
    crawls the live filesystem. A tmpdir with no real modules and no
    on-disk derived.json fallback yields the empty list (the legacy
    DataNotFoundError-on-missing-meta contract is replaced).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        assert list_modules(tmpdir) == []


# =============================================================================
# Suppress unused-import warnings for re-exported helpers used by other tests.
# =============================================================================


_ = (load_module_enriched_or_empty,)
