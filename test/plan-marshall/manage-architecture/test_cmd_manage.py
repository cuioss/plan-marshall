#!/usr/bin/env python3
"""Tests for ``_cmd_manage.py`` — discover, init, derived, derived-module.

Pins the per-module on-disk layout: ``_project.json`` is the canonical module
index and per-module ``derived.json`` / ``enriched.json`` files hold module
data. The legacy monolithic files are intentionally absent from this test
surface.
"""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-architecture'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_architecture_core = _load_module('_architecture_core', '_architecture_core.py')
_cmd_manage = _load_module('_cmd_manage', '_cmd_manage.py')

DataNotFoundError = _architecture_core.DataNotFoundError
ModuleNotFoundInProjectError = _architecture_core.ModuleNotFoundInProjectError

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
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


# =============================================================================
# Helper Functions
# =============================================================================


def create_test_project(tmpdir: str) -> dict:
    """Seed ``_project.json`` plus per-module ``derived.json`` for two modules.

    Returns the assembled dict equivalent to what api_get_derived will surface.
    """
    modules = {
        'module-a': {
            'name': 'module-a',
            'build_systems': ['maven'],
            'paths': {
                'module': 'module-a',
                'descriptor': 'module-a/pom.xml',
                'sources': ['module-a/src/main/java'],
                'tests': ['module-a/src/test/java'],
                'readme': 'module-a/README.md',
            },
            'metadata': {'artifact_id': 'module-a', 'description': 'Module A description'},
            'packages': {'com.example.a': {'path': 'module-a/src/main/java/com/example/a'}},
            'dependencies': ['org.example:dep1:compile'],
            'stats': {'source_files': 10, 'test_files': 5},
            'commands': {
                'module-tests': 'python3 .plan/execute-script.py ...',
                'verify': 'python3 .plan/execute-script.py ...',
            },
        },
        'module-b': {
            'name': 'module-b',
            'build_systems': ['maven'],
            'paths': {'module': 'module-b'},
            'metadata': {},
            'packages': {},
            'dependencies': [],
            'stats': {},
            'commands': {},
        },
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

    return {'project': {'name': 'test-project'}, 'modules': modules}


# =============================================================================
# Tests for api_init
# =============================================================================


def test_api_init_creates_per_module_enriched_files():
    """api_init writes ``{module}/enriched.json`` for every indexed module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir)

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
        create_test_project(tmpdir)
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
        create_test_project(tmpdir)
        api_init(tmpdir)

        result = api_init(tmpdir)

        # Both modules already have enriched.json so 0 are re-initialised.
        assert result['status'] == 'success'
        assert result['modules_initialized'] == 0


def test_api_init_force_overwrites_existing():
    """api_init(force=True) re-initialises every module's ``enriched.json``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir)
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
        create_test_project(tmpdir)

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
        import extension_discovery  # type: ignore[import-not-found]

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
        create_test_project(tmpdir)

        result = api_get_derived(tmpdir)

        assert result['project']['name'] == 'test-project'
        assert 'module-a' in result['modules']
        assert 'module-b' in result['modules']
        assert result['modules']['module-a']['build_systems'] == ['maven']
        assert 'extensions_used' in result


def test_api_get_derived_missing_meta_raises():
    """api_get_derived raises DataNotFoundError when ``_project.json`` is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            api_get_derived(tmpdir)
            assert False, 'Should have raised DataNotFoundError'
        except DataNotFoundError:
            pass


def test_api_get_derived_module_missing_derived_returns_empty_dict():
    """An indexed module with no ``derived.json`` surfaces as ``{}``.

    The index is the canonical truth; if a per-module file vanishes we return
    a stable empty dict rather than crashing or skipping the module.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # _project.json lists 'gone' but no derived.json exists for it.
        save_project_meta(
            {'name': 'p', 'description': '', 'modules': {'gone': {}}, 'extensions_used': []},
            tmpdir,
        )

        result = api_get_derived(tmpdir)

        assert 'gone' in result['modules']
        assert result['modules']['gone'] == {}


# =============================================================================
# Tests for api_get_derived_module
# =============================================================================


def test_api_get_derived_module_returns_single_module_dict():
    """api_get_derived_module returns one module's derived dict."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir)

        result = api_get_derived_module('module-a', tmpdir)

        assert result['name'] == 'module-a'
        assert result['build_systems'] == ['maven']
        assert 'com.example.a' in result['packages']


def test_api_get_derived_module_unknown_module_raises():
    """api_get_derived_module raises ModuleNotFoundInProjectError for unknown name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir)

        try:
            api_get_derived_module('nonexistent', tmpdir)
            assert False, 'Should have raised ModuleNotFoundInProjectError'
        except ModuleNotFoundInProjectError:
            pass


def test_api_get_derived_module_missing_derived_raises():
    """api_get_derived_module raises DataNotFoundError when derived.json is gone.

    Distinct from "module not found in index": the module IS in the index but
    its per-module file has been removed (e.g. half-cleanup state).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        save_project_meta(
            {'name': 'p', 'description': '', 'modules': {'gone': {}}, 'extensions_used': []},
            tmpdir,
        )

        try:
            api_get_derived_module('gone', tmpdir)
            assert False, 'Should have raised DataNotFoundError'
        except DataNotFoundError:
            pass


# =============================================================================
# Tests for list_modules
# =============================================================================


def test_list_modules_returns_index_keys():
    """list_modules returns the sorted module names from ``_project.json``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir)

        result = list_modules(tmpdir)

        assert sorted(result) == ['module-a', 'module-b']


def test_list_modules_missing_meta_raises():
    """list_modules raises DataNotFoundError when ``_project.json`` is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            list_modules(tmpdir)
            assert False, 'Should have raised DataNotFoundError'
        except DataNotFoundError:
            pass


# =============================================================================
# Suppress unused-import warnings for re-exported helpers used by other tests.
# =============================================================================


_ = (load_module_enriched_or_empty,)
