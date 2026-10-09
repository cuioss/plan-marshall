#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for how the registry repin treats a symbolic link inside the plugin cache.

The repin removes an ``.orphaned_at`` marker from ``{cache_root}/{bundle}/{version}``
and records that directory as the entry's ``installPath``. When the bundle
directory, the version directory or the marker is a link, an apply is refused
before anything is removed or written. The cache root itself may be a link.

Every fixture is a real file tree under ``tmp_path``; the real ``~/.claude``
tree is never read or written.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

import pytest

from marketplace.targets.claude import registry_pin as rp

OLD = '0.1.100'
TARGET = '0.1.200'
NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
BUNDLE = 'plan-marshall'
MARKER = '.orphaned_at'
MARKER_TEXT = '2026-01-01T00:00:00Z'


class Home(NamedTuple):
    """A fixture home: a registry pinned behind the target, the cache root, and a place outside it."""

    registry: Path
    cache_root: Path
    outside: Path

    def version_dir(self) -> Path:
        return self.cache_root / BUNDLE / TARGET

    def backups(self) -> list[Path]:
        return sorted(self.registry.parent.glob(f'{self.registry.name}.repin-backup-*'))

    def pinned_version(self) -> str:
        document = json.loads(self.registry.read_text(encoding='utf-8'))
        return str(document['plugins'][f'{BUNDLE}@plan-marshall'][0]['version'])


def _make_home(tmp_path: Path, cache_root: Path | None = None) -> Home:
    """Build the registry and a cache holding the old and the target version directory."""
    root = cache_root if cache_root is not None else tmp_path / 'plugins' / 'cache' / 'plan-marshall'
    for version in (OLD, TARGET):
        (root / BUNDLE / version).mkdir(parents=True)
    entry = {'scope': 'user', 'installPath': str(root / BUNDLE / OLD), 'version': OLD}
    registry = tmp_path / 'plugins' / 'installed_plugins.json'
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        json.dumps({'version': 2, 'plugins': {f'{BUNDLE}@plan-marshall': [entry]}}, indent=2) + '\n',
        encoding='utf-8',
    )
    outside = tmp_path / 'outside'
    outside.mkdir()
    return Home(registry, root, outside)


def _link_version_dir(home: Home) -> tuple[Path, Path]:
    """Replace the target version directory by a link to a marked directory outside the cache."""
    target = home.outside / TARGET
    home.version_dir().rename(target)
    home.version_dir().symlink_to(target, target_is_directory=True)
    (target / MARKER).write_text(MARKER_TEXT, encoding='utf-8')
    return home.version_dir(), target / MARKER


def _link_bundle_dir(home: Home) -> tuple[Path, Path]:
    """Replace the bundle directory by a link to a directory outside the cache."""
    target = home.outside / BUNDLE
    (home.cache_root / BUNDLE).rename(target)
    (home.cache_root / BUNDLE).symlink_to(target, target_is_directory=True)
    (target / TARGET / MARKER).write_text(MARKER_TEXT, encoding='utf-8')
    return home.cache_root / BUNDLE, target / TARGET / MARKER


def _link_marker(home: Home) -> tuple[Path, Path]:
    """Put a marker in the target version directory that is a link to a file outside the cache."""
    target = home.outside / 'marker-target'
    target.write_text(MARKER_TEXT, encoding='utf-8')
    (home.version_dir() / MARKER).symlink_to(target)
    return home.version_dir() / MARKER, target


def _run(home: Home, **kwargs: Any) -> dict[str, Any]:
    return rp.repin(registry_path=home.registry, cache_root=home.cache_root, now=NOW, **kwargs)


LINK_SHAPES = pytest.mark.parametrize(
    'make_link',
    [_link_version_dir, _link_bundle_dir, _link_marker],
    ids=['symlinked-version-dir', 'symlinked-bundle-dir', 'symlinked-marker'],
)


@LINK_SHAPES
def test_apply_refuses_a_link_inside_the_cache_and_changes_nothing(tmp_path, make_link):
    """The file behind the link survives, the link stays a link, and the registry is byte-identical."""
    home = _make_home(tmp_path)
    link, behind_link = make_link(home)
    before = home.registry.read_bytes()

    result = _run(home, apply=True)

    assert behind_link.read_text(encoding='utf-8') == MARKER_TEXT
    assert link.is_symlink()
    assert home.registry.read_bytes() == before
    assert home.backups() == []
    assert (result['status'], result['gate'], result['exit_code']) == ('error', rp.GATE_FAILED, 1)
    assert (result['markers_removed'], [row['action'] for row in result['entries']]) == (0, [rp.ACTION_FAILED])


@LINK_SHAPES
def test_refusal_names_the_link(tmp_path, make_link):
    """The message says which cache path is the link."""
    home = _make_home(tmp_path)
    link, _ = make_link(home)

    result = _run(home, apply=True)

    assert str(link) in result['message']
    assert 'symbolic link' in result['message']


@LINK_SHAPES
def test_dry_run_reports_through_a_link_inside_the_cache(tmp_path, make_link):
    """Without ``apply`` the report is produced as before and nothing is touched."""
    home = _make_home(tmp_path)
    _, behind_link = make_link(home)
    before = home.registry.read_bytes()

    result = _run(home)

    assert (result['status'], result['mode'], result['registry_parity']) == ('success', rp.MODE_DRY_RUN, 'behind')
    assert [(row['after_version'], row['action']) for row in result['entries']] == [(TARGET, rp.ACTION_REPORT)]
    assert behind_link.read_text(encoding='utf-8') == MARKER_TEXT
    assert home.registry.read_bytes() == before


def test_apply_refuses_a_bundle_that_resolves_outside_the_cache_root(tmp_path):
    """A registry key whose bundle part climbs out of the cache is refused without a link being involved."""
    home = _make_home(tmp_path)
    escaped = home.cache_root.parent / 'elsewhere' / TARGET
    escaped.mkdir(parents=True)
    (escaped / MARKER).write_text(MARKER_TEXT, encoding='utf-8')
    entry = {'scope': 'user', 'installPath': '/somewhere/0.1.100', 'version': OLD}
    home.registry.write_text(
        json.dumps({'version': 2, 'plugins': {'../elsewhere@plan-marshall': [entry]}}), encoding='utf-8'
    )
    before = home.registry.read_bytes()

    result = _run(home, apply=True)

    assert (escaped / MARKER).exists()
    assert home.registry.read_bytes() == before
    assert result['status'] == 'error'
    assert 'outside the cache root' in result['message']


def test_apply_removes_the_marker_of_a_real_directory_and_repins(tmp_path):
    """The matched control: with real directories the marker goes and the entry is repinned."""
    home = _make_home(tmp_path)
    marker = home.version_dir() / MARKER
    marker.write_text(MARKER_TEXT, encoding='utf-8')

    result = _run(home, apply=True)

    assert not marker.exists()
    assert home.pinned_version() == TARGET
    assert (result['status'], result['markers_removed'], result['gate']) == ('success', 1, rp.GATE_PASSED)


def test_apply_accepts_a_symlinked_cache_root(tmp_path):
    """A cache root that is itself a link is the location the caller named, and is repinned through."""
    real_root = tmp_path / 'real-cache'
    home = _make_home(tmp_path, cache_root=real_root)
    marker = home.version_dir() / MARKER
    marker.write_text(MARKER_TEXT, encoding='utf-8')
    linked_root = tmp_path / 'plugins' / 'cache-link'
    linked_root.symlink_to(real_root, target_is_directory=True)

    result = rp.repin(registry_path=home.registry, cache_root=linked_root, now=NOW, apply=True)

    assert not marker.exists()
    assert home.pinned_version() == TARGET
    assert (result['status'], result['gate'], result['exit_code']) == ('success', rp.GATE_PASSED, 0)
