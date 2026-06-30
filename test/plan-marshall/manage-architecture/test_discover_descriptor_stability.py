#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Regression tests for ``discover --force`` project-identity stability.

Lesson ``2026-06-29-23-002``: ``architecture discover --force`` run inside a
worktree (e.g. the ``architecture-refresh`` finalize step) overwrote the
project ``name`` with the worktree/plan-id basename and blanked the curated
``description`` / ``description_reasoning``. ``api_discover`` now resolves the
project-identity fields from a stable anchor — the existing ``_project.json``
when present, else the repository-root basename (never ``project_path.name``)
— and preserves the description unless ``regenerate_description=True``.

These tests reproduce the corruption and assert it no longer occurs.
"""

import sys
import tempfile
from pathlib import Path

from conftest import load_script_module

sys.path.insert(0, str(Path(__file__).parent))


_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_manage = load_script_module('plan-marshall', 'manage-architecture', '_cmd_manage.py', '_cmd_manage')

save_project_meta = _architecture_core.save_project_meta
load_project_meta = _architecture_core.load_project_meta

api_discover = _cmd_manage.api_discover


def _fake_discover_one_module(_project_root):
    """Deterministic discovery stub returning a single maven module."""
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
        },
        'extensions_used': ['pm-dev-java'],
    }


def _patch_discovery(monkeypatch):
    """Replace the heavy discovery delegate with the deterministic stub.

    ``api_discover`` imports ``extension_discovery`` lazily inside its body, so
    patching the already-loaded module attribute is sufficient.
    """
    import extension_discovery  # type: ignore[import-not-found]

    monkeypatch.setattr(extension_discovery, 'discover_project_modules', _fake_discover_one_module)


def test_rediscover_preserves_curated_name(monkeypatch):
    """A forced rediscovery keeps the curated ``name``, not the dir basename.

    Reproduces the worktree-basename corruption: pre-fix, ``discover --force``
    rewrote ``name`` to ``project_path.name`` (the tmpdir/worktree basename).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        save_project_meta(
            {
                'name': 'curated-project',
                'description': 'A curated description',
                'description_reasoning': 'From README.md first paragraph',
                'extensions_used': [],
                'modules': {},
            },
            tmpdir,
        )
        # Sanity: the tmpdir basename is NOT the curated name, so a passing
        # assertion proves identity was preserved rather than coincidentally
        # matching the basename.
        assert Path(tmpdir).name != 'curated-project'

        _patch_discovery(monkeypatch)

        result = api_discover(tmpdir, force=True)
        assert result['status'] == 'success'

        meta = load_project_meta(tmpdir)
        assert meta['name'] == 'curated-project'
        # Never the worktree/plan-id basename.
        assert meta['name'] != Path(tmpdir).name


def test_rediscover_preserves_description_fields(monkeypatch):
    """A forced rediscovery preserves ``description`` / ``description_reasoning``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        save_project_meta(
            {
                'name': 'curated-project',
                'description': 'A curated description',
                'description_reasoning': 'From README.md first paragraph',
                'extensions_used': [],
                'modules': {},
            },
            tmpdir,
        )

        _patch_discovery(monkeypatch)

        result = api_discover(tmpdir, force=True)
        assert result['status'] == 'success'

        meta = load_project_meta(tmpdir)
        assert meta['description'] == 'A curated description'
        assert meta['description_reasoning'] == 'From README.md first paragraph'


def test_first_run_falls_back_to_repo_root_name(monkeypatch):
    """First-run discover (no ``_project.json``) anchors to the repo-root basename.

    The fallback MUST resolve from the repository root, NEVER from
    ``project_path.name`` (the worktree/plan-id basename). The repo-root
    resolver is patched so the assertion is deterministic and host-independent.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # No _project.json on disk — this is the first-run path.
        monkeypatch.setattr(_cmd_manage, '_resolve_repo_root_name', lambda _path: 'repo-root-name')
        # The tmpdir basename must differ from the patched repo-root name so a
        # passing assertion proves the fallback used the repo root, not the dir.
        assert Path(tmpdir).name != 'repo-root-name'

        _patch_discovery(monkeypatch)

        result = api_discover(tmpdir, force=True)
        assert result['status'] == 'success'

        meta = load_project_meta(tmpdir)
        assert meta['name'] == 'repo-root-name'
        assert meta['name'] != Path(tmpdir).name


def test_regenerate_description_opts_back_into_blanking(monkeypatch):
    """``regenerate_description=True`` blanks description while preserving name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        save_project_meta(
            {
                'name': 'curated-project',
                'description': 'A curated description',
                'description_reasoning': 'From README.md first paragraph',
                'extensions_used': [],
                'modules': {},
            },
            tmpdir,
        )

        _patch_discovery(monkeypatch)

        result = api_discover(tmpdir, force=True, regenerate_description=True)
        assert result['status'] == 'success'

        meta = load_project_meta(tmpdir)
        # Description blanked on opt-in regeneration ...
        assert meta['description'] == ''
        assert meta['description_reasoning'] == ''
        # ... but the curated name is still preserved.
        assert meta['name'] == 'curated-project'
