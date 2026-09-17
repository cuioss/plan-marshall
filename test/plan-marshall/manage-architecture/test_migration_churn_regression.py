#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression test reproducing the consumer migration-churn run end to end.

The observed consumer run committed a descriptor tree an older tool version had
written: several module ``enriched.json`` documents carried no ``generation``
header, and one module's ``key_packages`` map held a dotted key the derived
``packages`` bridge resolves to a real directory next to a parent-package key it
does not. A plan's ``architecture-refresh`` then ran ``discover --force``, the
porcelain status went dirty with an empty module union, and the tool migration
was committed as the plan's own "refresh derived data" change.

This suite rebuilds that shape in a throwaway ``git init`` project, commits it,
and drives the verbs in-process through their CLI handlers (``cmd_discover`` and
``cmd_descriptor_regression_check``) with the discovery delegate replaced by a
deterministic stub. It asserts the two properties the fix exists for:

* under ``--apply plan`` the migration-only delta leaves the committed tree
  untouched, and a structural change beside it dirties only its own documents;
* under ``--apply migration`` the same delta is written and the regression gate
  against ``HEAD`` reports the migration and the unresolved key instead of hiding
  them — and still refuses a lost curated entry.

A matched control runs the identical fixture under ``--apply all`` and asserts
the tree IS dirtied, so the clean ``--apply plan`` result is not vacuous.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from conftest import load_script_module

_cmd_manage = load_script_module('plan-marshall', 'manage-architecture', '_cmd_manage.py', '_cmd_manage')
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')

cmd_discover = _cmd_manage.cmd_discover
cmd_descriptor_regression_check = _cmd_client.cmd_descriptor_regression_check

_ARCH_DIR = '.plan/project-architecture'
_META = '_project.json'

#: The consumer run's pre-existing modules. ``module-a`` carries the partial re-key.
_MODULES = ('module-a', 'module-c', 'module-d')
_ADDED_MODULE = 'module-e'
_BRIDGED_KEY = 'com.example.pkg'
_BRIDGE_PATH = 'module-a/src/pkg'
_PARENT_KEY = 'com.example'


# =============================================================================
# Fixture
# =============================================================================


def _git(repo: Path, *argv: str) -> str:
    """Run git in ``repo`` isolated from machine-level ignore and signing config."""
    completed = subprocess.run(
        [
            'git',
            '-c',
            'user.name=test',
            '-c',
            'user.email=test@example.com',
            '-c',
            'commit.gpgsign=false',
            '-c',
            f'core.excludesFile={os.devnull}',
            '-C',
            str(repo),
            *argv,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def _legacy_document(name: str) -> dict[str, Any]:
    """A module document as the older tool wrote it: no ``generation`` header."""
    key_packages: dict[str, Any] = {}
    if name == 'module-a':
        key_packages = {
            _BRIDGED_KEY: {'description': 'Pipeline package'},
            _PARENT_KEY: {'description': 'Parent package'},
        }
    return {'type': 'module', 'responsibility': f'Handles {name}', 'key_packages': key_packages}


def _commit_consumer_tree(project_dir: str) -> None:
    """Write and commit the consumer run's descriptor tree in compact JSON."""
    repo = Path(project_dir)
    (repo / _BRIDGE_PATH).mkdir(parents=True)
    data_dir = repo / _ARCH_DIR
    index = {}
    for name in _MODULES:
        document = _legacy_document(name)
        path = data_dir / name / 'enriched.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document), encoding='utf-8')
        index[name] = {'description': document['responsibility']}
    meta = {
        'name': 'consumer',
        'description': 'Curated consumer project',
        'description_reasoning': 'README',
        'extensions_used': ['ext'],
        'modules': index,
    }
    (data_dir / _META).write_text(json.dumps(meta), encoding='utf-8')
    _git(repo, 'init', '-q')
    _git(repo, 'add', '-f', '-A')
    _git(repo, 'commit', '-q', '-m', 'consumer baseline')


def _stub_discovery(monkeypatch: pytest.MonkeyPatch, *crawled: str) -> None:
    """Replace the discovery delegate with a crawl of exactly ``crawled``.

    ``module-a``'s derived ``packages`` bridge covers the dotted child key only, so
    its parent-package key has no bridge — the partial re-key the run showed.
    """
    import extension_discovery

    def _module_data(name: str) -> dict[str, Any]:
        packages = {_BRIDGED_KEY: {'path': _BRIDGE_PATH}} if name == 'module-a' else {}
        return {
            'name': name,
            'build_systems': ['maven'],
            'paths': {'module': name},
            'metadata': {},
            'packages': packages,
            'dependencies': [],
            'stats': {},
            'commands': {},
        }

    def _discover(_project_root: Any) -> dict[str, Any]:
        return {'modules': {name: _module_data(name) for name in crawled}, 'extensions_used': ['ext']}

    monkeypatch.setattr(extension_discovery, 'discover_project_modules', _discover)


def _discover(project_dir: str, apply: str) -> dict[str, Any]:
    result: dict[str, Any] = cmd_discover(
        SimpleNamespace(project_dir=project_dir, force=True, regenerate_description=False, apply=apply)
    )
    return result


def _regression_check_against_head(project_dir: str) -> dict[str, Any]:
    result: dict[str, Any] = cmd_descriptor_regression_check(SimpleNamespace(pre_ref='HEAD', project_dir=project_dir))
    return result


def _porcelain_paths(project_dir: str) -> set[str]:
    """Every dirty path under the descriptor tree, untracked files listed individually."""
    output = _git(Path(project_dir), 'status', '--porcelain', '--untracked-files=all', '--', _ARCH_DIR)
    return {line[3:] for line in output.splitlines() if line.strip()}


def _document_path(name: str) -> str:
    return f'{_ARCH_DIR}/{name}/enriched.json'


# =============================================================================
# (a) --apply plan over the migration-only delta
# =============================================================================


def test_apply_plan_over_the_consumer_delta_commits_nothing(monkeypatch):
    with tempfile.TemporaryDirectory() as project_dir:
        _commit_consumer_tree(project_dir)
        _stub_discovery(monkeypatch, *_MODULES)

        result = _discover(project_dir, 'plan')

        assert result['status'] == 'success'
        assert result['attribution'] == 'migration_only'
        assert result['applied'] == 'none'
        assert result['unresolved_key_packages_count'] == 1
        assert result['modules_examined'] == len(_MODULES)
        assert _porcelain_paths(project_dir) == set()


def test_matched_control_apply_all_dirties_the_same_fixture(monkeypatch):
    """The clean result above is not vacuous: the same fixture under ``all`` IS dirtied."""
    with tempfile.TemporaryDirectory() as project_dir:
        _commit_consumer_tree(project_dir)
        _stub_discovery(monkeypatch, *_MODULES)

        result = _discover(project_dir, 'all')

        assert result['attribution'] == 'migration_only'
        assert result['applied'] == 'all'
        dirty = _porcelain_paths(project_dir)
        assert dirty, 'the --apply all control left the tree clean, so the --apply plan result proves nothing'
        assert _document_path('module-a') in dirty


# =============================================================================
# (b) a structural change beside the migration
# =============================================================================


def test_apply_plan_with_an_added_module_dirties_only_its_own_documents(monkeypatch):
    with tempfile.TemporaryDirectory() as project_dir:
        _commit_consumer_tree(project_dir)
        _stub_discovery(monkeypatch, *_MODULES, _ADDED_MODULE)

        result = _discover(project_dir, 'plan')

        assert result['attribution'] == 'mixed'
        assert result['applied'] == 'plan'
        assert _porcelain_paths(project_dir) == {f'{_ARCH_DIR}/{_META}', _document_path(_ADDED_MODULE)}
        repo = Path(project_dir)
        for name in _MODULES:
            committed = _git(repo, 'show', f'HEAD:{_document_path(name)}')
            on_disk = (repo / _document_path(name)).read_text(encoding='utf-8')
            assert on_disk == committed, f'{name} was rewritten under --apply plan'


# =============================================================================
# (c) / (d) --apply migration gated on the regression check against HEAD
# =============================================================================


def test_apply_migration_passes_the_regression_gate_and_reports_the_migration(monkeypatch):
    with tempfile.TemporaryDirectory() as project_dir:
        _commit_consumer_tree(project_dir)
        _stub_discovery(monkeypatch, *_MODULES)

        written = _discover(project_dir, 'migration')
        check = _regression_check_against_head(project_dir)

        assert written['applied'] == 'migration'
        assert _porcelain_paths(project_dir), 'the migration wrote nothing, so the regression check has no delta'
        assert check['status'] == 'success'
        assert check['regressive'] is False
        assert check['migrations'] == [{'module': 'module-a', 'from_key': _BRIDGED_KEY, 'to_key': _BRIDGE_PATH}]
        assert check['unresolved_keys'] == [{'module': 'module-a', 'key': _PARENT_KEY}]
        assert check['examined_fields']
        assert check['modules_examined'] == len(_MODULES)


def test_a_lost_curated_entry_in_the_migrated_document_is_regressive(monkeypatch):
    with tempfile.TemporaryDirectory() as project_dir:
        _commit_consumer_tree(project_dir)
        _stub_discovery(monkeypatch, *_MODULES)
        _discover(project_dir, 'migration')

        document_path = Path(project_dir) / _document_path('module-a')
        migrated = json.loads(document_path.read_text(encoding='utf-8'))
        assert _PARENT_KEY in migrated['key_packages'], 'the fixture no longer carries the entry this test deletes'
        del migrated['key_packages'][_PARENT_KEY]
        document_path.write_text(json.dumps(migrated), encoding='utf-8')

        check = _regression_check_against_head(project_dir)

        assert check['regressive'] is True
        assert {violation['field'] for violation in check['violations']} == {'enriched.key_packages'}
