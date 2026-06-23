#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``_architecture_core.py`` — per-module on-disk layout.

Pins the new persistence contract introduced by D2:

* ``_project.json`` — top-level metadata; ``modules`` index is the canonical
  list of "which modules exist".
* ``{module}/derived.json`` — deterministic discovery output for one module.
* ``{module}/enriched.json`` — LLM-augmented fields for one module.

The legacy monolithic ``derived-data.json`` / ``llm-enriched.json`` files
are intentionally absent from this surface — TASK-2 removed them.
"""

import json
import tempfile
from pathlib import Path

import pytest
from file_ops import format_toon_value

from conftest import load_script_module

_architecture_core = load_script_module('plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core')

DATA_DIR = _architecture_core.DATA_DIR
DataNotFoundError = _architecture_core.DataNotFoundError
ModuleNotFoundInProjectError = _architecture_core.ModuleNotFoundInProjectError

get_data_dir = _architecture_core.get_data_dir
get_project_meta_path = _architecture_core.get_project_meta_path
get_module_derived_path = _architecture_core.get_module_derived_path
get_module_enriched_path = _architecture_core.get_module_enriched_path

iter_modules = _architecture_core.iter_modules
load_project_meta = _architecture_core.load_project_meta
save_project_meta = _architecture_core.save_project_meta
load_module_derived = _architecture_core.load_module_derived
save_module_derived = _architecture_core.save_module_derived
load_module_enriched = _architecture_core.load_module_enriched
load_module_enriched_or_empty = _architecture_core.load_module_enriched_or_empty
save_module_enriched = _architecture_core.save_module_enriched
merge_module_data = _architecture_core.merge_module_data
get_root_module = _architecture_core.get_root_module
crawl_all_modules = _architecture_core.crawl_all_modules
invalidate_crawl_cache = _architecture_core.invalidate_crawl_cache


# =============================================================================
# Helpers
# =============================================================================


def _seed_project(tmpdir: str, modules: dict[str, dict] | None = None) -> None:
    """Write ``_project.json`` plus per-module ``derived.json`` files.

    ``modules`` maps module name → its derived dict. ``_project.json``'s
    ``modules`` index is set to the same key set so ``iter_modules`` returns it.
    """
    if modules is None:
        modules = {}
    invalidate_crawl_cache()
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


# =============================================================================
# Tests for Path Functions
# =============================================================================


def test_get_data_dir_default():
    """get_data_dir returns .plan/project-architecture by default."""
    path = get_data_dir()
    assert path == Path('.') / DATA_DIR


def test_get_data_dir_with_project():
    """get_data_dir respects project_dir parameter."""
    path = get_data_dir('/my/project')
    assert path == Path('/my/project') / DATA_DIR


def test_get_project_meta_path_ends_with_project_json():
    """get_project_meta_path resolves to ``_project.json`` under the data dir."""
    path = get_project_meta_path('/my/project')
    assert str(path).endswith('_project.json')
    assert 'project-architecture' in str(path)


def test_get_module_derived_path_per_module():
    """get_module_derived_path nests ``derived.json`` under the module dir."""
    path = get_module_derived_path('module-a', '/my/project')
    assert path.name == 'derived.json'
    assert path.parent.name == 'module-a'


def test_get_module_enriched_path_per_module():
    """get_module_enriched_path nests ``enriched.json`` under the module dir."""
    path = get_module_enriched_path('module-a', '/my/project')
    assert path.name == 'enriched.json'
    assert path.parent.name == 'module-a'


# =============================================================================
# Tests for Project Meta Load/Save
# =============================================================================


def test_load_project_meta_success():
    """load_project_meta reads ``_project.json``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta = {
            'name': 'demo',
            'description': 'desc',
            'description_reasoning': 'reason',
            'extensions_used': [],
            'modules': {'a': {}, 'b': {}},
        }
        save_project_meta(meta, tmpdir)

        loaded = load_project_meta(tmpdir)
        assert loaded == meta


def test_load_project_meta_missing_raises():
    """load_project_meta raises DataNotFoundError when file missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(DataNotFoundError, match='(?i)discover'):
            load_project_meta(tmpdir)


def test_save_project_meta_creates_dir_and_file():
    """save_project_meta creates the data dir and writes ``_project.json``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta = {'name': 'demo', 'modules': {}}
        result_path = save_project_meta(meta, tmpdir)

        assert result_path.exists()
        assert result_path.name == '_project.json'
        loaded = json.loads(result_path.read_text())
        assert loaded['name'] == 'demo'


# =============================================================================
# Tests for Per-Module Derived Load/Save
# =============================================================================


def test_load_module_derived_success():
    """load_module_derived reads ``{module}/derived.json``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data = {'name': 'mod-a', 'paths': {'module': 'mod-a'}}
        _seed_project(tmpdir, {'mod-a': data})

        loaded = load_module_derived('mod-a', tmpdir)
        assert loaded == data


def test_load_module_derived_missing_raises():
    """load_module_derived raises DataNotFoundError when file missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(DataNotFoundError, match='(?i)discover'):
            load_module_derived('mod-a', tmpdir)


def test_save_module_derived_writes_per_module_file():
    """save_module_derived writes under ``{module}/derived.json``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data = {'name': 'mod-a', 'paths': {'module': 'mod-a'}}
        result_path = save_module_derived('mod-a', data, tmpdir)

        assert result_path.exists()
        assert result_path.name == 'derived.json'
        assert result_path.parent.name == 'mod-a'
        assert json.loads(result_path.read_text()) == data


# =============================================================================
# Tests for Per-Module Enriched Load/Save
# =============================================================================


def test_load_module_enriched_success():
    """load_module_enriched reads ``{module}/enriched.json``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        save_module_enriched('mod-a', {'responsibility': 'resp'}, tmpdir)
        loaded = load_module_enriched('mod-a', tmpdir)
        assert loaded == {'responsibility': 'resp'}


def test_load_module_enriched_missing_raises():
    """load_module_enriched raises DataNotFoundError when file missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(DataNotFoundError, match='(?i)init'):
            load_module_enriched('mod-a', tmpdir)


def test_load_module_enriched_or_empty_returns_empty_when_missing():
    """load_module_enriched_or_empty returns empty dict when the file is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = load_module_enriched_or_empty('mod-a', tmpdir)
        assert result == {}


def test_load_module_enriched_or_empty_returns_data_when_present():
    """load_module_enriched_or_empty returns the stored dict when present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        save_module_enriched('mod-a', {'responsibility': 'resp'}, tmpdir)
        result = load_module_enriched_or_empty('mod-a', tmpdir)
        assert result == {'responsibility': 'resp'}


def test_save_module_enriched_writes_per_module_file():
    """save_module_enriched writes under ``{module}/enriched.json``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result_path = save_module_enriched('mod-a', {'purpose': 'library'}, tmpdir)

        assert result_path.exists()
        assert result_path.name == 'enriched.json'
        assert result_path.parent.name == 'mod-a'
        assert json.loads(result_path.read_text()) == {'purpose': 'library'}


# =============================================================================
# Tests for iter_modules
# =============================================================================


def test_iter_modules_returns_index_keys_sorted():
    """iter_modules returns ``_project.json``'s modules in sorted order."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(tmpdir, {'b': {}, 'a': {}, 'c': {}})

        names = iter_modules(tmpdir)
        assert names == ['a', 'b', 'c']


def test_iter_modules_empty_when_no_modules():
    """iter_modules returns [] when ``_project.json`` has no modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(tmpdir, {})
        assert iter_modules(tmpdir) == []


def test_iter_modules_missing_meta_returns_empty():
    """iter_modules returns an empty list when no modules exist (no crawl hits).

    Under the on-demand crawl model iter_modules calls crawl_all_modules
    against the live filesystem. When the project tree has no recognisable
    modules and no on-disk derived.json fallback, the result is the empty
    list (not a raised DataNotFoundError as in the legacy index-based model).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        assert iter_modules(tmpdir) == []


def test_iter_modules_surfaces_modules_via_disk_fallback():
    """iter_modules returns every module whose derived.json the disk fallback finds.

    Under the on-demand crawl model the crawl returns whichever modules the
    live filesystem reveals. For tmp project trees the synthetic fallback
    reads on-disk derived.json files seeded by tests, so 'orphan' modules
    seeded outside _project.json's index are now visible — the index is no
    longer the gatekeeper.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(tmpdir, {'a': {}})
        save_module_derived('orphan', {'name': 'orphan'}, tmpdir)

        names = iter_modules(tmpdir)
        assert 'a' in names
        assert 'orphan' in names


# =============================================================================
# Tests for get_root_module
# =============================================================================


def test_get_root_module_finds_dot_path():
    """get_root_module returns the module whose paths.module == '.'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(
            tmpdir,
            {
                'child': {'paths': {'module': 'child'}},
                'parent': {'paths': {'module': '.'}},
            },
        )

        assert get_root_module(tmpdir) == 'parent'


def test_get_root_module_finds_empty_path():
    """get_root_module returns the module whose paths.module is ''."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(
            tmpdir,
            {
                'child': {'paths': {'module': 'child'}},
                'root': {'paths': {'module': ''}},
            },
        )

        assert get_root_module(tmpdir) == 'root'


def test_get_root_module_fallback_to_first():
    """get_root_module falls back to the first sorted module name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(
            tmpdir,
            {
                'only-module': {'paths': {'module': 'only-module'}},
            },
        )

        assert get_root_module(tmpdir) == 'only-module'


def test_get_root_module_returns_none_when_no_meta():
    """get_root_module returns None when ``_project.json`` is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert get_root_module(tmpdir) is None


def test_get_root_module_returns_none_when_no_modules():
    """get_root_module returns None when ``_project.json`` has no modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(tmpdir, {})
        assert get_root_module(tmpdir) is None


# =============================================================================
# Tests for crawl memoization + single-crawl get_root_module
# =============================================================================


def test_crawl_all_modules_memoizes_second_call(monkeypatch):
    """A second crawl_all_modules for the same project hits the memo (no recompute)."""
    invalidate_crawl_cache()
    compute_calls = []
    real_compute = _architecture_core._compute_all_modules

    def _spy_compute(project_dir, project_path):
        compute_calls.append(project_dir)
        return real_compute(project_dir, project_path)

    monkeypatch.setattr(_architecture_core, '_compute_all_modules', _spy_compute)

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(tmpdir, {'a': {'name': 'a', 'paths': {'module': 'a'}}})
        try:
            first = crawl_all_modules(tmpdir)
            second = crawl_all_modules(tmpdir)
        finally:
            invalidate_crawl_cache(tmpdir)

    assert len(compute_calls) == 1, 'second crawl must hit the memo, not recompute'
    assert first == second


def test_crawl_all_modules_returns_independent_copies(monkeypatch):
    """Each crawl_all_modules call returns a deep copy — mutating one is isolated."""
    invalidate_crawl_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(tmpdir, {'a': {'name': 'a', 'paths': {'module': 'a'}}})
        try:
            first = crawl_all_modules(tmpdir)
            first['a']['name'] = 'MUTATED'
            second = crawl_all_modules(tmpdir)
        finally:
            invalidate_crawl_cache(tmpdir)

    assert second['a']['name'] == 'a', 'cached map must not be corrupted by a caller mutation'


def test_invalidate_crawl_cache_forces_recrawl(monkeypatch):
    """invalidate_crawl_cache drops the memo so the next call recomputes."""
    invalidate_crawl_cache()
    compute_calls = []
    real_compute = _architecture_core._compute_all_modules

    def _spy_compute(project_dir, project_path):
        compute_calls.append(project_dir)
        return real_compute(project_dir, project_path)

    monkeypatch.setattr(_architecture_core, '_compute_all_modules', _spy_compute)

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(tmpdir, {'a': {'name': 'a', 'paths': {'module': 'a'}}})
        try:
            crawl_all_modules(tmpdir)
            invalidate_crawl_cache(tmpdir)
            crawl_all_modules(tmpdir)
        finally:
            invalidate_crawl_cache(tmpdir)

    assert len(compute_calls) == 2, 'invalidation must force a re-crawl'


def test_get_root_module_uses_single_crawl(monkeypatch):
    """get_root_module crawls exactly once (no per-module re-crawl)."""
    invalidate_crawl_cache()
    compute_calls = []
    real_compute = _architecture_core._compute_all_modules

    def _spy_compute(project_dir, project_path):
        compute_calls.append(project_dir)
        return real_compute(project_dir, project_path)

    monkeypatch.setattr(_architecture_core, '_compute_all_modules', _spy_compute)

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(
            tmpdir,
            {
                'child': {'paths': {'module': 'child'}},
                'parent': {'paths': {'module': '.'}},
                'other': {'paths': {'module': 'other'}},
            },
        )
        try:
            root = get_root_module(tmpdir)
        finally:
            invalidate_crawl_cache(tmpdir)

    assert root == 'parent'
    assert len(compute_calls) == 1, 'get_root_module must crawl once, not once per module'


# =============================================================================
# Tests for merge_module_data (2-arg form)
# =============================================================================


def test_merge_module_data_combines_derived_and_enriched():
    """merge_module_data overlays per-module enriched onto per-module derived."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(
            tmpdir,
            {
                'test': {
                    'name': 'test',
                    'paths': {'module': 'test'},
                    'dependencies': ['dep1'],
                }
            },
        )
        save_module_enriched(
            'test',
            {'responsibility': 'Test module', 'purpose': 'library'},
            tmpdir,
        )

        result = merge_module_data('test', tmpdir)

        assert result['name'] == 'test'
        assert result['paths']['module'] == 'test'
        assert result['dependencies'] == ['dep1']
        assert result['responsibility'] == 'Test module'
        assert result['purpose'] == 'library'


def test_merge_module_data_enriched_overwrites_derived_when_truthy():
    """Truthy enriched fields override derived; falsy ones do not."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(tmpdir, {'test': {'description': 'derived desc'}})
        save_module_enriched('test', {'description': 'enriched desc'}, tmpdir)

        result = merge_module_data('test', tmpdir)
        assert result['description'] == 'enriched desc'


def test_merge_module_data_falsy_enriched_does_not_overwrite():
    """An empty-string enriched field MUST NOT clobber a derived value."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(tmpdir, {'test': {'description': 'derived desc'}})
        save_module_enriched('test', {'description': ''}, tmpdir)

        result = merge_module_data('test', tmpdir)
        assert result['description'] == 'derived desc'


def test_merge_module_data_missing_enriched_returns_derived():
    """Missing per-module ``enriched.json`` is treated as empty enrichment."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(tmpdir, {'test': {'name': 'test', 'paths': {}}})

        result = merge_module_data('test', tmpdir)
        assert result['name'] == 'test'


def test_merge_module_data_skills_by_profile_from_enriched():
    """skills_by_profile flows from enriched into the merged result."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(
            tmpdir,
            {
                'test': {
                    'name': 'test',
                    'paths': {'module': 'test'},
                }
            },
        )
        save_module_enriched(
            'test',
            {
                'skills_by_profile': {
                    'implementation': ['pm-dev-java:java-core'],
                    'unit-testing': ['pm-dev-java:junit-core'],
                }
            },
            tmpdir,
        )

        result = merge_module_data('test', tmpdir)

        assert 'skills_by_profile' in result
        assert result['skills_by_profile']['implementation'] == ['pm-dev-java:java-core']
        assert result['skills_by_profile']['unit-testing'] == ['pm-dev-java:junit-core']


def test_merge_module_data_missing_derived_raises():
    """merge_module_data raises DataNotFoundError when derived.json is gone."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # _project.json present but module's derived.json absent (lists 'gone').
        save_project_meta({'name': 'p', 'modules': {'gone': {}}, 'extensions_used': []}, tmpdir)
        with pytest.raises(DataNotFoundError):
            merge_module_data('gone', tmpdir)


# =============================================================================
# Tests for TOON Formatting
# =============================================================================


def test_format_toon_value_none():
    """format_toon_value returns empty string for None."""
    assert format_toon_value(None) == ''


def test_format_toon_value_bool():
    """format_toon_value formats booleans."""
    assert format_toon_value(True) == 'true'
    assert format_toon_value(False) == 'false'


def test_format_toon_value_list():
    """format_toon_value joins list with +."""
    assert format_toon_value(['a', 'b', 'c']) == 'a+b+c'


def test_format_toon_value_string():
    """format_toon_value passes strings through."""
    assert format_toon_value('test') == 'test'


def test_format_toon_value_int():
    """format_toon_value converts int to string."""
    assert format_toon_value(42) == '42'
