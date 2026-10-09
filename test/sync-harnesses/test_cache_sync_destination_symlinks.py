# SPDX-License-Identifier: FSL-1.1-ALv2
"""Destination-symlink tests for the Claude plugin-cache sync.

``marketplace/targets/claude/cache_sync.py`` never mirrors through a
symbolic link it finds in the cache: a linked ``{bundle}`` or
``{bundle}/{version}`` directory, a link inside a version directory at a
path the bundle holds as a real entry, and a linked ``dist-manifest.json``
are refused before the first bundle is mirrored.

The refusal precedes ``rsync``, so no test here needs ``rsync`` on PATH.
Every case starts from a hand-built previous cache whose source has since
changed, so a cache that is byte-identical after the run proves nothing was
mirrored — including the bundle that was not refused.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
from pathlib import Path
from typing import NamedTuple

import pytest
from toon_parser import parse_toon

from conftest import PROJECT_ROOT, run_script
from marketplace.targets import fs_safety
from marketplace.targets.claude import cache_sync

_SYNC_PY = PROJECT_ROOT / 'marketplace' / 'targets' / 'sync.py'

SENTINEL = b'operator data, not ours\n'
VERSION = '0.1.0'

#: Every cache path the sync creates, mirrors into or writes, with the kind of
#: entry the link planted there points at.
REFUSED_LINK_SITES = [
    ('demo', 'dir'),
    (f'demo/{VERSION}', 'dir'),
    (f'demo/{VERSION}/README.md', 'file'),
    (f'demo/{VERSION}/.claude-plugin', 'dir'),
    ('dist-manifest.json', 'file'),
]


class Sandbox(NamedTuple):
    source: Path
    cache: Path
    outside: Path


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _make_bundle_tree(root: Path, version_dir: bool, marker: str) -> None:
    """Write the ``demo`` and ``other`` bundles under ``root``, as source or as cache."""
    for name in ('demo', 'other'):
        bundle = root / name / VERSION if version_dir else root / name
        _write(bundle / '.claude-plugin' / 'plugin.json', json.dumps({'name': name, 'version': VERSION}) + '\n')
        _write(bundle / 'README.md', f'# {name} {marker}\n')
    _write(root / 'dist-manifest.json', f'{{"marker": "{marker}"}}\n')


def _snapshot(root: Path) -> dict[str, tuple[object, ...]]:
    """Every entry under ``root`` with its kind, mode and bytes; links are not followed."""
    entries: dict[str, tuple[object, ...]] = {}
    for current, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                entries[rel] = ('link', os.readlink(path))
            elif path.is_dir():
                entries[rel] = ('dir', stat.S_IMODE(path.stat().st_mode))
            else:
                entries[rel] = ('file', stat.S_IMODE(path.stat().st_mode), path.read_bytes())
    return entries


def _relink(path: Path, target: Path) -> Path:
    """Replace whatever is at ``path`` with a link to ``target``."""
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)
    path.symlink_to(target, target_is_directory=target.is_dir())
    return path


@pytest.fixture
def sandbox(tmp_path: Path) -> Sandbox:
    """A previous cache of two bundles, a changed source, and operator data outside both."""
    box = Sandbox(tmp_path / 'target' / 'claude', tmp_path / 'cache', tmp_path / 'outside')
    _make_bundle_tree(box.cache, version_dir=True, marker='v1')
    _make_bundle_tree(box.source, version_dir=False, marker='v2')
    box.outside.mkdir()
    (box.outside / 'keep.txt').write_bytes(SENTINEL)
    (box.outside / 'nested').mkdir()
    (box.outside / 'nested' / 'data.txt').write_bytes(SENTINEL)
    return box


def _plant(box: Sandbox, site: str, kind: str) -> Path:
    return _relink(box.cache / site, box.outside if kind == 'dir' else box.outside / 'keep.txt')


def _sync(box: Sandbox, *, dry_run: bool = False) -> cache_sync.CacheSyncResult:
    return cache_sync.sync_cache(
        source_root=box.source,
        marketplace_root=box.source.parent / 'no-marketplace',
        cache_root=box.cache,
        skip_staleness_guard=True,
        dry_run=dry_run,
    )


@pytest.mark.parametrize(('site', 'kind'), REFUSED_LINK_SITES, ids=[site for site, _ in REFUSED_LINK_SITES])
@pytest.mark.parametrize('dry_run', [False, True], ids=['real-run', 'dry-run'])
def test_link_at_a_mirrored_path_is_refused_and_nothing_is_changed(
    site: str, kind: str, dry_run: bool, sandbox: Sandbox
):
    """A refused link is named and kept; neither its target nor any bundle's cache changes."""
    link = _plant(sandbox, site, kind)
    cache_before = _snapshot(sandbox.cache)
    outside_before = _snapshot(sandbox.outside)

    result = _sync(sandbox, dry_run=dry_run)

    assert (result.exit_code, result.status, result.synced) == (1, 'error', [])
    assert 'refused' in result.summary_message
    assert str(link) in result.summary_message
    assert [str(link) in row['error'] for row in result.failed] == [True]
    assert parse_toon(cache_sync.render(result))['status'] == 'error'
    assert _snapshot(sandbox.outside) == outside_before
    assert _snapshot(sandbox.cache) == cache_before


def test_clean_cache_has_no_refusal(sandbox: Sandbox):
    """Control: without a link nothing is refused, so the refusal cases are not vacuous."""
    bundles = [sandbox.source / 'demo', sandbox.source / 'other']

    assert cache_sync._destination_refusals(sandbox.source, sandbox.cache, bundles) == []


def test_symlinked_cache_root_is_not_refused(sandbox: Sandbox, tmp_path: Path):
    """Control: the cache root itself may be a link — only what lies below it is checked."""
    root_link = tmp_path / 'cache-link'
    root_link.symlink_to(sandbox.cache, target_is_directory=True)

    assert cache_sync._destination_refusals(sandbox.source, root_link, [sandbox.source / 'demo']) == []


def test_link_the_bundle_ships_as_a_link_is_left_to_rsync(sandbox: Sandbox):
    """A cached link at a path the bundle itself holds as a link is the previous mirror, not a refusal."""
    (sandbox.source / 'demo' / 'alias.md').symlink_to('README.md')
    (sandbox.cache / 'demo' / VERSION / 'alias.md').symlink_to('README.md')

    refusal = cache_sync._destination_refusal(
        fs_safety,
        source_dir=sandbox.source / 'demo',
        dest_dir=sandbox.cache / 'demo' / VERSION,
        cache_root=sandbox.cache,
    )

    assert refusal is None


@pytest.mark.parametrize('site', ['demo', f'demo/{VERSION}'])
def test_rsync_step_refuses_a_linked_destination_on_its_own(site: str, sandbox: Sandbox):
    """The mirror step repeats the check at the point of the write, before it looks for rsync."""
    link = _plant(sandbox, site, 'dir')
    cache_before = _snapshot(sandbox.cache)
    outside_before = _snapshot(sandbox.outside)

    status, error = cache_sync._rsync_bundle(
        source_dir=sandbox.source / 'demo', dest_dir=sandbox.cache / 'demo' / VERSION
    )

    assert status == 'failed'
    assert str(link) in error
    assert _snapshot(sandbox.outside) == outside_before
    assert _snapshot(sandbox.cache) == cache_before


def test_manifest_copy_leaves_a_linked_manifest_alone(sandbox: Sandbox):
    """The manifest copy neither follows nor replaces a link at the cache root."""
    link = _plant(sandbox, 'dist-manifest.json', 'file')

    copied = cache_sync._copy_dist_manifest(sandbox.source, sandbox.cache)

    assert copied is False
    assert link.is_symlink()
    assert (sandbox.outside / 'keep.txt').read_bytes() == SENTINEL


def test_refusal_through_the_engine_is_an_error_document(sandbox: Sandbox):
    """``--target claude`` renders the refusal as its result document, never as a traceback."""
    link = _plant(sandbox, f'demo/{VERSION}', 'dir')
    outside_before = _snapshot(sandbox.outside)

    result = run_script(
        _SYNC_PY,
        '--target',
        'claude',
        '--source',
        str(sandbox.source),
        '--cache-root',
        str(sandbox.cache),
        '--skip-staleness-guard',
        timeout=60,
    )

    assert result.returncode == 1
    assert 'Traceback' not in result.stderr
    data = parse_toon(result.stdout)
    assert (data['status'], data['cache_status']) == ('error', 'error')
    assert str(link) in data['summary_message']
    assert _snapshot(sandbox.outside) == outside_before
