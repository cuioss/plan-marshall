#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Unit + integration tests for the project-local sync.py engine.

Covers parallel rsync, TOON return shape, --from-worktree redirection,
--bundle scoping, and the rsync-failure error path. The staleness guard
gets its own dedicated suite (``test_staleness_guard.py``); these tests
bypass it via ``--skip-staleness-guard`` so they can focus on the
engine itself.

The script under test lives at
``.claude/skills/sync-plugin-cache/scripts/sync.py`` (project-local),
not in any marketplace bundle — sync-plugin-cache is meta-project-only
tooling that does not ship to consumers of plan-marshall.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]

_SYNC_PY = PROJECT_ROOT / '.claude' / 'skills' / 'sync-plugin-cache' / 'scripts' / 'sync.py'


def _write(path: Path, content: str | bytes = '') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding='utf-8')


def _make_target(target_root: Path, bundles: dict[str, str]) -> None:
    """Build a fixture target/claude/ tree with the given bundles → versions."""
    for name, version in bundles.items():
        plugin_doc = json.dumps({'name': name, 'version': version}, indent=2) + '\n'
        _write(target_root / name / '.claude-plugin' / 'plugin.json', plugin_doc)
        _write(target_root / name / 'README.md', f'# {name} {version}\n')


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SYNC_PY), *args],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=cwd,
    )


# ---------------------------------------------------------------------------
# Happy path — parallel sync, TOON shape
# ---------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which('rsync') is None, reason='rsync not on PATH')
def test_sync_engine_emits_canonical_toon(tmp_path: Path):
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo-a': '0.1.0', 'demo-b': '0.2.0'})

    result = _run(
        '--source-root', str(target),
        '--cache-root', str(cache),
        '--skip-staleness-guard',
    )
    assert result.returncode == 0, result.stderr

    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert int(data['synced_count']) == 2
    assert int(data['failed_count']) == 0


@pytest.mark.skipif(shutil.which('rsync') is None, reason='rsync not on PATH')
def test_sync_engine_writes_into_versioned_cache_subdirs(tmp_path: Path):
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo': '0.3.0'})

    result = _run(
        '--source-root', str(target),
        '--cache-root', str(cache),
        '--skip-staleness-guard',
    )
    assert result.returncode == 0, result.stderr

    expected_path = cache / 'demo' / '0.3.0' / 'README.md'
    assert expected_path.is_file(), f'expected sync output at {expected_path}'


@pytest.mark.skipif(shutil.which('rsync') is None, reason='rsync not on PATH')
def test_sync_engine_skips_directories_without_plugin_json(tmp_path: Path):
    # Directories under target/claude/ that lack ``.claude-plugin/plugin.json``
    # are NOT bundles and must NOT be rsynced into the cache. Specifically,
    # the top-level ``.claude-plugin/`` directory holds the marketplace.json
    # registration manifest, not bundle content; and stray non-bundle dirs
    # may exist on a developer machine. Both are skipped.
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _write(target / 'noplugin' / 'README.md', '# no plugin\n')
    _write(target / '.claude-plugin' / 'marketplace.json', '{}\n')
    _write(target / 'real-bundle' / '.claude-plugin' / 'plugin.json', '{"version": "1.0.0"}\n')
    _write(target / 'real-bundle' / 'agents' / 'demo.md', '---\nname: demo\n---\n')

    result = _run(
        '--source-root', str(target),
        '--cache-root', str(cache),
        '--skip-staleness-guard',
    )
    assert result.returncode == 0
    assert not (cache / 'noplugin').exists()
    assert not (cache / '.claude-plugin').exists()
    assert (cache / 'real-bundle' / '1.0.0' / '.claude-plugin' / 'plugin.json').is_file()


# ---------------------------------------------------------------------------
# --bundle scoping
# ---------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which('rsync') is None, reason='rsync not on PATH')
def test_sync_engine_bundle_flag_scopes_to_one(tmp_path: Path):
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo-a': '0.1.0', 'demo-b': '0.2.0', 'demo-c': '0.3.0'})

    result = _run(
        '--source-root', str(target),
        '--cache-root', str(cache),
        '--skip-staleness-guard',
        '--bundle', 'demo-b',
    )
    assert result.returncode == 0

    assert (cache / 'demo-b' / '0.2.0' / 'README.md').is_file()
    assert not (cache / 'demo-a').exists()
    assert not (cache / 'demo-c').exists()


def test_sync_engine_bundle_flag_unknown_returns_error(tmp_path: Path):
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo': '0.1.0'})

    result = _run(
        '--source-root', str(target),
        '--cache-root', str(cache),
        '--skip-staleness-guard',
        '--bundle', 'nonexistent',
    )
    assert result.returncode == 1
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'no matching bundles' in data['summary_message']


# ---------------------------------------------------------------------------
# --from-worktree redirection
# ---------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which('rsync') is None, reason='rsync not on PATH')
def test_sync_engine_from_worktree_redirects_source(tmp_path: Path):
    worktree = tmp_path / 'wt'
    target = worktree / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'wt-bundle': '9.9.9'})

    result = _run(
        '--from-worktree', str(worktree),
        '--cache-root', str(cache),
        '--skip-staleness-guard',
    )
    assert result.returncode == 0
    assert (cache / 'wt-bundle' / '9.9.9' / 'README.md').is_file()


# ---------------------------------------------------------------------------
# Error path: rsync failure surfaces in TOON
# ---------------------------------------------------------------------------


def test_sync_engine_failure_path_when_rsync_missing(tmp_path: Path, monkeypatch):
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo': '0.1.0'})

    # Simulate rsync absence by pointing PATH at an empty dir
    empty_path = tmp_path / 'empty-bin'
    empty_path.mkdir()
    monkeypatch.setenv('PATH', str(empty_path))

    result = _run(
        '--source-root', str(target),
        '--cache-root', str(cache),
        '--skip-staleness-guard',
    )

    # All bundles failed → status: error, exit_code 1
    assert result.returncode == 1
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert int(data['failed_count']) == 1
    # The failed table is captured; one row per failure
    assert 'failed[1]{bundle,error}:' in result.stdout
    assert 'rsync not found on PATH' in result.stdout
