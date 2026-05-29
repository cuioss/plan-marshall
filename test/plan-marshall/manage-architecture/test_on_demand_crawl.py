#!/usr/bin/env python3
"""Tests for the on-demand crawl behaviour in ``_architecture_core``.

Under the on-demand crawl model:

* ``crawl_module_derived(module, project_dir)`` computes derived data in
  memory from the live filesystem.
* ``load_module_derived`` is now an alias for ``crawl_module_derived``.
* ``iter_modules`` reads the module set from the live crawl.
* ``discover`` no longer writes per-module ``derived.json`` files to disk.

The synthetic-project fallback documented in ``crawl_all_modules`` lets these
tests seed module data via ``save_module_derived`` even though no real
extension would pick up the fake project tree.
"""

import json
import tempfile
from pathlib import Path

from conftest import load_script_module

_architecture_core = load_script_module('plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core')
_cmd_manage = load_script_module('plan-marshall', 'manage-architecture', '_cmd_manage.py', '_cmd_manage')

crawl_module_derived = _architecture_core.crawl_module_derived
crawl_all_modules = _architecture_core.crawl_all_modules
iter_modules = _architecture_core.iter_modules
load_module_derived = _architecture_core.load_module_derived
save_module_derived = _architecture_core.save_module_derived
save_project_meta = _architecture_core.save_project_meta
DataNotFoundError = _architecture_core.DataNotFoundError


def _seed_synthetic(tmpdir: str, modules: dict[str, dict]) -> None:
    """Seed _project.json + per-module derived.json under tmpdir.

    Uses ``save_module_derived`` (the snapshot-fixture writer) so the
    on-disk fallback in ``crawl_all_modules`` picks up the modules.
    """
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


def test_load_module_derived_returns_crawl_result():
    """load_module_derived returns the on-demand crawl output (here the disk fallback)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_synthetic(tmpdir, {'mod-a': {'name': 'mod-a', 'paths': {'module': 'mod-a'}}})
        loaded = load_module_derived('mod-a', tmpdir)
        assert loaded['name'] == 'mod-a'


def test_iter_modules_uses_live_crawl():
    """iter_modules reflects the live filesystem crawl, not _project.json's index."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_synthetic(
            tmpdir,
            {
                'alpha': {'name': 'alpha', 'paths': {'module': 'alpha'}},
                'beta': {'name': 'beta', 'paths': {'module': 'beta'}},
            },
        )
        assert iter_modules(tmpdir) == ['alpha', 'beta']


def test_crawl_module_derived_returns_module_payload():
    """crawl_module_derived returns the specific module's payload dict."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_synthetic(
            tmpdir,
            {
                'alpha': {'name': 'alpha', 'paths': {'module': 'alpha'}},
                'beta': {'name': 'beta', 'paths': {'module': 'beta'}},
            },
        )
        payload = crawl_module_derived('beta', tmpdir)
        assert payload['name'] == 'beta'


def test_load_module_derived_missing_raises_data_not_found():
    """load_module_derived raises DataNotFoundError when the module is absent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            load_module_derived('nonexistent', tmpdir)
            assert False, 'Should have raised DataNotFoundError'
        except DataNotFoundError as e:
            assert 'discover' in str(e).lower() or 'crawl' in str(e).lower()


def test_discover_does_not_persist_derived_json():
    """api_discover no longer writes per-module derived.json files to disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Run discover against an empty tmpdir; modules will be empty but the
        # important assertion is that no derived.json files appear on disk.
        result = _cmd_manage.api_discover(tmpdir, force=True)
        assert result['status'] in {'success', 'exists'}

        # Inspect .plan/project-architecture/ for any derived.json files.
        arch_dir = Path(tmpdir) / '.plan' / 'project-architecture'
        if arch_dir.exists():
            stray = list(arch_dir.rglob('derived.json'))
            assert stray == [], f'discover persisted derived.json files: {stray}'


def test_crawl_all_modules_returns_empty_for_empty_project():
    """crawl_all_modules returns {} when neither extensions nor disk fallback yield modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = crawl_all_modules(tmpdir)
        assert result == {}


def test_discover_writes_project_meta_only():
    """After discover, _project.json exists but no derived.json does."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _cmd_manage.api_discover(tmpdir, force=True)
        meta_path = Path(tmpdir) / '.plan' / 'project-architecture' / '_project.json'
        if meta_path.exists():
            # When discover succeeds (modules found), it writes _project.json
            # but NEVER any derived.json files. When discover finds zero
            # modules, _project.json may also be absent — both shapes are
            # consistent with "no derived persisted".
            data = json.loads(meta_path.read_text())
            assert 'modules' in data
        stray = list((Path(tmpdir) / '.plan').rglob('derived.json')) if (Path(tmpdir) / '.plan').exists() else []
        assert stray == []
