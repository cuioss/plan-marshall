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

from conftest import PROJECT_ROOT
from toon_parser import parse_toon

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


# ---------------------------------------------------------------------------
# dist-manifest.json mirrored into the plugin-cache root after a successful sync
# ---------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which('rsync') is None, reason='rsync not on PATH')
def test_sync_engine_copies_dist_manifest_to_cache_root_byte_for_byte(tmp_path: Path):
    # After a successful sync the top-level target/claude/dist-manifest.json is
    # mirrored to {cache_root}/dist-manifest.json byte-for-byte, so the
    # dist-branch versioning feature can resolve the installed version from
    # base_path/dist-manifest.json in the meta-project's own preflight.
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo': '0.4.0'})
    manifest_doc = json.dumps({'version': '0.1.1068', 'bundles': {}}, indent=2) + '\n'
    _write(target / 'dist-manifest.json', manifest_doc)

    result = _run(
        '--source-root', str(target),
        '--cache-root', str(cache),
        '--skip-staleness-guard',
    )
    assert result.returncode == 0, result.stderr

    copied = cache / 'dist-manifest.json'
    assert copied.is_file(), f'expected manifest copied to {copied}'
    assert copied.read_bytes() == (target / 'dist-manifest.json').read_bytes()


@pytest.mark.skipif(shutil.which('rsync') is None, reason='rsync not on PATH')
def test_sync_engine_dist_manifest_lands_at_cache_root_not_versioned_subdir(tmp_path: Path):
    # The manifest lands at the cache ROOT (alongside the versioned
    # {bundle}/{version}/ dirs), never inside a per-bundle versioned subdir.
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo': '0.4.0'})
    _write(target / 'dist-manifest.json', '{"version": "0.1.1068"}\n')

    result = _run(
        '--source-root', str(target),
        '--cache-root', str(cache),
        '--skip-staleness-guard',
    )
    assert result.returncode == 0, result.stderr

    assert (cache / 'dist-manifest.json').is_file()
    assert not (cache / 'demo' / '0.4.0' / 'dist-manifest.json').exists()


@pytest.mark.skipif(shutil.which('rsync') is None, reason='rsync not on PATH')
def test_sync_engine_absent_dist_manifest_degrades_to_noop(tmp_path: Path):
    # An absent source manifest is a best-effort no-op: the sync still reports
    # success, raises nothing, and leaves no stray file at the cache root.
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo': '0.4.0'})

    result = _run(
        '--source-root', str(target),
        '--cache-root', str(cache),
        '--skip-staleness-guard',
    )
    assert result.returncode == 0, result.stderr
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert not (cache / 'dist-manifest.json').exists()


@pytest.mark.skipif(shutil.which('rsync') is None, reason='rsync not on PATH')
def test_sync_engine_dist_manifest_copy_does_not_perturb_bundle_sync(tmp_path: Path):
    # The manifest copy is additive: the per-bundle rsync outcome
    # (synced_count and the versioned subdir writes) is unchanged.
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo-a': '0.1.0', 'demo-b': '0.2.0'})
    _write(target / 'dist-manifest.json', '{"version": "0.1.1068"}\n')

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
    assert (cache / 'demo-a' / '0.1.0' / 'README.md').is_file()
    assert (cache / 'demo-b' / '0.2.0' / 'README.md').is_file()
