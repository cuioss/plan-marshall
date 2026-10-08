#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Unit + integration tests for the Claude path of the sync engine.

Covers parallel rsync, TOON return shape, --from-worktree redirection,
--bundles scoping, --dry-run, the rsync-failure error path, and the
``registry_parity`` block with its ``cache_status`` companion, the
``--registry-path`` / ``--repin`` flags and exit code 3. The
staleness guard gets its own dedicated suite
(``test_staleness_guard.py``); these tests bypass it via
``--skip-staleness-guard`` so they can focus on the engine itself.

Every run passes ``--cache-root``, and every run that reads a registry
passes ``--registry-path`` at a file under ``tmp_path``, so no test reads
or writes the machine's own plugin cache or plugin registry.

The script under test is ``marketplace/targets/sync.py`` run with
``--target claude``, which drives
``marketplace/targets/claude/cache_sync.py``. Neither lives in a
marketplace bundle — the sync engine is meta-project-only tooling that
does not ship to consumers of plan-marshall.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import PROJECT_ROOT, ScriptResult, run_script
from toon_parser import parse_toon

_SYNC_PY = PROJECT_ROOT / 'marketplace' / 'targets' / 'sync.py'


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


def _run(*args: str, cwd: Path | None = None) -> ScriptResult:
    return run_script(_SYNC_PY, '--target', 'claude', *args, cwd=cwd, timeout=60)


_CACHE_SYNC_PY = PROJECT_ROOT / 'marketplace' / 'targets' / 'claude' / 'cache_sync.py'

OLD = '0.1.100'
SYNCED = '0.1.200'
NEWER = '0.1.300'
FOREIGN_KEY = 'other-plugin@other-market'


def _make_registry(registry: Path, cache: Path, pins: dict[str, str]) -> None:
    """Write a plugin registry pinning each bundle of ``pins`` at its version.

    One ``user``-scope entry per bundle, plus one entry of a foreign marketplace.
    """
    plugins: dict[str, list[dict[str, str]]] = {
        FOREIGN_KEY: [{'scope': 'user', 'installPath': '/elsewhere/other-plugin/9.9.9', 'version': '9.9.9'}]
    }
    for bundle, version in pins.items():
        plugins[f'{bundle}@plan-marshall'] = [
            {'scope': 'user', 'installPath': str(cache / bundle / version), 'version': version}
        ]
    _write(registry, json.dumps({'version': 2, 'plugins': plugins}, indent=2) + '\n')


def _pinned(registry: Path, bundle: str) -> tuple[str, str]:
    """The ``(installPath version, version)`` pair the registry holds for ``bundle``."""
    entry = json.loads(registry.read_text(encoding='utf-8'))['plugins'][f'{bundle}@plan-marshall'][0]
    return Path(entry['installPath']).name, entry['version']


def _backups(registry: Path) -> list[Path]:
    return sorted(registry.parent.glob(f'{registry.name}.repin-backup-*'))


def _sync_with_registry(tmp_path: Path, pinned: str | None, *extra: str) -> tuple[ScriptResult, Path, Path]:
    """Sync a one-bundle tree at ``SYNCED`` against a registry pinned at ``pinned``.

    ``pinned=None`` leaves the registry file absent. Returns
    ``(result, registry, cache)``.
    """
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    registry = tmp_path / 'plugins' / 'installed_plugins.json'
    _make_target(target, {'demo': SYNCED})
    if pinned is not None:
        _make_registry(registry, cache, {'demo': pinned})

    result = _run(
        '--source',
        str(target),
        '--cache-root',
        str(cache),
        '--registry-path',
        str(registry),
        '--skip-staleness-guard',
        *extra,
    )
    return result, registry, cache


# ---------------------------------------------------------------------------
# Happy path — parallel sync, TOON shape
# ---------------------------------------------------------------------------


def test_sync_engine_emits_canonical_toon(tmp_path: Path):
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo-a': '0.1.0', 'demo-b': '0.2.0'})

    result = _run(
        '--source',
        str(target),
        '--cache-root',
        str(cache),
        '--skip-staleness-guard',
    )
    assert result.returncode == 0, result.stderr

    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['cache_status'] == 'success'
    assert int(data['synced_count']) == 2
    assert int(data['failed_count']) == 0


def test_overridden_cache_root_without_registry_path_reads_no_registry(tmp_path: Path):
    """A fixture cache root is never judged against the machine's live registry.

    With ``--cache-root`` overridden and no ``--registry-path`` the verdict is
    ``unreadable``, the block names no registry file, and the reason says why.
    """
    target = tmp_path / 'target' / 'claude'
    _make_target(target, {'demo': SYNCED})

    result = _run('--source', str(target), '--cache-root', str(tmp_path / 'cache'), '--skip-staleness-guard')

    assert result.returncode == 0, result.stderr
    data = parse_toon(result.stdout)
    parity = data['registry_parity']
    assert (data['status'], data['cache_status']) == ('success', 'success')
    assert (parity['verdict'], parity['registry_state']) == ('unreadable', 'not_read')
    assert 'registry_path' not in parity
    assert '--registry-path' in parity['reason']
    assert parity['entries'] == []


def test_sync_engine_writes_into_versioned_cache_subdirs(tmp_path: Path):
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo': '0.3.0'})

    result = _run(
        '--source',
        str(target),
        '--cache-root',
        str(cache),
        '--skip-staleness-guard',
    )
    assert result.returncode == 0, result.stderr

    expected_path = cache / 'demo' / '0.3.0' / 'README.md'
    assert expected_path.is_file(), f'expected sync output at {expected_path}'


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
        '--source',
        str(target),
        '--cache-root',
        str(cache),
        '--skip-staleness-guard',
    )
    assert result.returncode == 0
    assert not (cache / 'noplugin').exists()
    assert not (cache / '.claude-plugin').exists()
    assert (cache / 'real-bundle' / '1.0.0' / '.claude-plugin' / 'plugin.json').is_file()


# ---------------------------------------------------------------------------
# --bundles scoping
# ---------------------------------------------------------------------------


def test_sync_engine_bundle_flag_scopes_to_one(tmp_path: Path):
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo-a': '0.1.0', 'demo-b': '0.2.0', 'demo-c': '0.3.0'})

    result = _run(
        '--source',
        str(target),
        '--cache-root',
        str(cache),
        '--skip-staleness-guard',
        '--bundles',
        'demo-b',
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
        '--source',
        str(target),
        '--cache-root',
        str(cache),
        '--skip-staleness-guard',
        '--bundles',
        'nonexistent',
    )
    assert result.returncode == 1
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'no matching bundles' in data['summary_message']


# ---------------------------------------------------------------------------
# --dry-run — the bundles are selected, nothing is written
# ---------------------------------------------------------------------------


def test_sync_engine_dry_run_reports_the_selection_and_writes_nothing(tmp_path: Path):
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo-a': '0.1.0', 'demo-b': '0.2.0'})
    _write(target / 'dist-manifest.json', '{"version": "0.1.1068"}\n')

    result = _run(
        '--source',
        str(target),
        '--cache-root',
        str(cache),
        '--skip-staleness-guard',
        '--dry-run',
    )

    assert result.returncode == 0, result.stderr
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['dry_run'] is True
    assert int(data['synced_count']) == 0
    assert [(row['bundle'], row['status']) for row in data['synced']] == [
        ('demo-a', 'dry_run'),
        ('demo-b', 'dry_run'),
    ]
    assert not cache.exists()


# ---------------------------------------------------------------------------
# --from-worktree redirection
# ---------------------------------------------------------------------------


def test_sync_engine_from_worktree_redirects_source(tmp_path: Path):
    worktree = tmp_path / 'wt'
    target = worktree / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'wt-bundle': '9.9.9'})

    result = _run(
        '--from-worktree',
        str(worktree),
        '--cache-root',
        str(cache),
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
        '--source',
        str(target),
        '--cache-root',
        str(cache),
        '--skip-staleness-guard',
    )

    # All bundles failed → status: error, exit_code 1
    assert result.returncode == 1
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert data['cache_status'] == 'error'
    assert int(data['failed_count']) == 1
    # The failed table is captured; one row per failure
    assert 'failed[1]{bundle,error}:' in result.stdout
    assert 'rsync not found on PATH' in result.stdout


# ---------------------------------------------------------------------------
# dist-manifest.json mirrored into the plugin-cache root after a successful sync
# ---------------------------------------------------------------------------


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
        '--source',
        str(target),
        '--cache-root',
        str(cache),
        '--skip-staleness-guard',
    )
    assert result.returncode == 0, result.stderr

    copied = cache / 'dist-manifest.json'
    assert copied.is_file(), f'expected manifest copied to {copied}'
    assert copied.read_bytes() == (target / 'dist-manifest.json').read_bytes()


def test_sync_engine_dist_manifest_lands_at_cache_root_not_versioned_subdir(tmp_path: Path):
    # The manifest lands at the cache ROOT (alongside the versioned
    # {bundle}/{version}/ dirs), never inside a per-bundle versioned subdir.
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo': '0.4.0'})
    _write(target / 'dist-manifest.json', '{"version": "0.1.1068"}\n')

    result = _run(
        '--source',
        str(target),
        '--cache-root',
        str(cache),
        '--skip-staleness-guard',
    )
    assert result.returncode == 0, result.stderr

    assert (cache / 'dist-manifest.json').is_file()
    assert not (cache / 'demo' / '0.4.0' / 'dist-manifest.json').exists()


def test_sync_engine_absent_dist_manifest_degrades_to_noop(tmp_path: Path):
    # An absent source manifest is a best-effort no-op: the sync still reports
    # success, raises nothing, and leaves no stray file at the cache root.
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo': '0.4.0'})

    result = _run(
        '--source',
        str(target),
        '--cache-root',
        str(cache),
        '--skip-staleness-guard',
    )
    assert result.returncode == 0, result.stderr
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert not (cache / 'dist-manifest.json').exists()


def test_sync_engine_dist_manifest_copy_does_not_perturb_bundle_sync(tmp_path: Path):
    # The manifest copy is additive: the per-bundle rsync outcome
    # (synced_count and the versioned subdir writes) is unchanged.
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    _make_target(target, {'demo-a': '0.1.0', 'demo-b': '0.2.0'})
    _write(target / 'dist-manifest.json', '{"version": "0.1.1068"}\n')

    result = _run(
        '--source',
        str(target),
        '--cache-root',
        str(cache),
        '--skip-staleness-guard',
    )
    assert result.returncode == 0, result.stderr

    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert int(data['synced_count']) == 2
    assert int(data['failed_count']) == 0
    assert (cache / 'demo-a' / '0.1.0' / 'README.md').is_file()
    assert (cache / 'demo-b' / '0.2.0' / 'README.md').is_file()


# ---------------------------------------------------------------------------
# registry_parity — does the registry pin follow the version just synced?
# ---------------------------------------------------------------------------


def test_registry_behind_the_synced_version_is_partial_and_exits_three(tmp_path: Path):
    """A registry pinned one version behind turns a clean cache sync red.

    The cache sync itself succeeded, so ``cache_status`` stays ``success``;
    ``status`` is lowered to ``partial``, the summary names both versions and
    the repin command, and the registry file is left untouched.
    """
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    registry = tmp_path / 'plugins' / 'installed_plugins.json'
    _make_target(target, {'demo': SYNCED})
    _make_registry(registry, cache, {'demo': OLD})
    before = registry.read_bytes()

    result = _run(
        '--source', str(target), '--cache-root', str(cache), '--registry-path', str(registry), '--skip-staleness-guard'
    )

    assert result.returncode == 3, result.stdout
    data = parse_toon(result.stdout)
    assert (data['status'], data['cache_status']) == ('partial', 'success')
    assert int(data['synced_count']) == 1
    parity = data['registry_parity']
    assert (parity['verdict'], parity['registry_state']) == ('behind', 'ok')
    assert parity['registry_path'] == str(registry)
    assert parity['entries'] == [
        {
            'bundle': 'demo',
            'scope': 'user',
            'install_path_version': OLD,
            'version': OLD,
            'synced_version': SYNCED,
            'orphan_marked': False,
        }
    ]
    assert 'repin' not in parity
    for named in (f'pinned {OLD}', f'synced {SYNCED}', 'marketplace/targets/claude/registry_pin.py --apply'):
        assert named in data['summary_message']
    assert registry.read_bytes() == before
    assert _backups(registry) == []


def test_registry_parity_verdict_is_the_last_line_of_the_document(tmp_path: Path):
    """The block is rendered last and its verdict last within it."""
    result, _registry, _cache = _sync_with_registry(tmp_path, OLD)

    assert result.stdout.rstrip('\n').splitlines()[-1] == '  verdict: behind'


def test_registry_at_the_synced_version_is_in_parity_and_exits_zero(tmp_path: Path):
    """CONTROL for the behind case: the same fixture with a matching pin is green."""
    result, _registry, _cache = _sync_with_registry(tmp_path, SYNCED)

    assert result.returncode == 0, result.stdout
    data = parse_toon(result.stdout)
    assert (data['status'], data['cache_status']) == ('success', 'success')
    assert data['registry_parity']['verdict'] == 'in_parity'
    assert 'reason' not in data['registry_parity']
    assert 'registry_pin.py' not in data['summary_message']


def test_absent_registry_is_unreadable_and_exits_zero(tmp_path: Path):
    """No registry file is ``unreadable`` with the reason stated — reported, not red."""
    result, registry, _cache = _sync_with_registry(tmp_path, None)

    assert result.returncode == 0, result.stdout
    data = parse_toon(result.stdout)
    parity = data['registry_parity']
    assert (data['status'], data['cache_status']) == ('success', 'success')
    assert (parity['verdict'], parity['registry_state']) == ('unreadable', 'absent')
    assert 'absent' in parity['reason']
    assert parity['entries'] == []
    assert not registry.exists()


def test_registry_ahead_of_the_synced_version_is_reported_not_red(tmp_path: Path):
    """A pin newer than the synced tree is ``ahead``: status and exit code are unchanged."""
    result, registry, _cache = _sync_with_registry(tmp_path, NEWER)

    assert result.returncode == 0, result.stdout
    data = parse_toon(result.stdout)
    assert (data['status'], data['cache_status']) == ('success', 'success')
    assert data['registry_parity']['verdict'] == 'ahead'
    assert _pinned(registry, 'demo') == (NEWER, NEWER)


def test_repin_closes_a_behind_registry_in_the_same_invocation(tmp_path: Path):
    """``--repin`` moves the pin to the synced version, so the run is green."""
    result, registry, _cache = _sync_with_registry(tmp_path, OLD, '--repin')

    assert result.returncode == 0, result.stdout
    data = parse_toon(result.stdout)
    parity = data['registry_parity']
    assert (data['status'], data['cache_status']) == ('success', 'success')
    assert (parity['verdict'], parity['repin']) == ('in_parity', 'applied')
    assert [(row['install_path_version'], row['version']) for row in parity['entries']] == [(SYNCED, SYNCED)]
    assert _pinned(registry, 'demo') == (SYNCED, SYNCED)
    assert len(_backups(registry)) == 1


def test_repin_leaves_a_foreign_marketplace_entry_identical(tmp_path: Path):
    """The repin the engine drives rewrites plan-marshall entries only."""
    result, registry, _cache = _sync_with_registry(tmp_path, OLD, '--repin')

    assert result.returncode == 0, result.stdout
    foreign = json.loads(registry.read_text(encoding='utf-8'))['plugins'][FOREIGN_KEY]
    assert foreign == [{'scope': 'user', 'installPath': '/elsewhere/other-plugin/9.9.9', 'version': '9.9.9'}]


def test_dry_run_with_repin_writes_no_registry_and_no_cache(tmp_path: Path):
    """``--dry-run --repin`` reports the verdict and writes nothing at all.

    The verdict is judged against the version the run WOULD sync, so a registry
    behind it is still reported ``behind`` and still exits 3.
    """
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    registry = tmp_path / 'plugins' / 'installed_plugins.json'
    _make_target(target, {'demo': SYNCED})
    _make_registry(registry, cache, {'demo': OLD})
    before = registry.read_bytes()

    result = _run(
        '--source',
        str(target),
        '--cache-root',
        str(cache),
        '--registry-path',
        str(registry),
        '--skip-staleness-guard',
        '--dry-run',
        '--repin',
    )

    assert result.returncode == 3, result.stdout
    data = parse_toon(result.stdout)
    parity = data['registry_parity']
    assert data['dry_run'] is True
    assert (parity['verdict'], parity['repin']) == ('behind', 'skipped_dry_run')
    assert registry.read_bytes() == before
    assert _backups(registry) == []
    assert not cache.exists()


def test_entry_of_a_bundle_not_synced_is_listed_and_not_judged(tmp_path: Path):
    """A registry entry whose bundle this run did not sync takes no part in the verdict.

    ``other`` is pinned at an old version and was not synced, so it has no
    reference: it is shown as ``not_synced`` and the verdict over the synced
    bundle stays ``in_parity``.
    """
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    registry = tmp_path / 'plugins' / 'installed_plugins.json'
    _make_target(target, {'demo': SYNCED})
    _make_registry(registry, cache, {'demo': SYNCED, 'other': OLD})

    result = _run(
        '--source', str(target), '--cache-root', str(cache), '--registry-path', str(registry), '--skip-staleness-guard'
    )

    assert result.returncode == 0, result.stdout
    parity = parse_toon(result.stdout)['registry_parity']
    assert parity['verdict'] == 'in_parity'
    assert [(row['bundle'], row['synced_version']) for row in parity['entries']] == [
        ('demo', SYNCED),
        ('other', 'not_synced'),
    ]


def test_registry_holding_only_unsynced_bundles_is_unreadable(tmp_path: Path):
    """CONTROL for the case above: with no judged entry at all there is no verdict to give."""
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    registry = tmp_path / 'plugins' / 'installed_plugins.json'
    _make_target(target, {'demo': SYNCED})
    _make_registry(registry, cache, {'other': OLD})

    result = _run(
        '--source', str(target), '--cache-root', str(cache), '--registry-path', str(registry), '--skip-staleness-guard'
    )

    assert result.returncode == 0, result.stdout
    parity = parse_toon(result.stdout)['registry_parity']
    assert (parity['verdict'], parity['registry_state']) == ('unreadable', 'ok')
    assert 'synced in this invocation' in parity['reason']


def test_orphan_marker_on_the_synced_directory_is_reported(tmp_path: Path):
    """``orphan_marked`` states whether the synced version directory carries the marker.

    Under ``--dry-run`` the directory is not mirrored, so a marker already in
    the cache survives to be reported.
    """
    target = tmp_path / 'target' / 'claude'
    cache = tmp_path / 'cache'
    registry = tmp_path / 'plugins' / 'installed_plugins.json'
    _make_target(target, {'demo': SYNCED})
    _make_registry(registry, cache, {'demo': SYNCED})
    _write(cache / 'demo' / SYNCED / '.orphaned_at', '2026-01-01T00:00:00Z')

    result = _run(
        '--source',
        str(target),
        '--cache-root',
        str(cache),
        '--registry-path',
        str(registry),
        '--skip-staleness-guard',
        '--dry-run',
    )

    assert result.returncode == 0, result.stdout
    parity = parse_toon(result.stdout)['registry_parity']
    assert [row['orphan_marked'] for row in parity['entries']] == [True]
    assert (cache / 'demo' / SYNCED / '.orphaned_at').is_file()


def test_guard_refusal_carries_cache_status_and_no_registry_parity(tmp_path: Path):
    """A staleness-guard refusal synced nothing, so there is no version to judge against."""
    registry = tmp_path / 'plugins' / 'installed_plugins.json'
    _make_registry(registry, tmp_path / 'cache', {'demo': OLD})

    result = _run(
        '--source',
        str(tmp_path / 'no-such-target'),
        '--cache-root',
        str(tmp_path / 'cache'),
        '--registry-path',
        str(registry),
    )

    assert result.returncode == 2, result.stdout
    data = parse_toon(result.stdout)
    assert (data['status'], data['cache_status'], data['guard_outcome']) == ('error', 'error', 'stale')
    assert 'registry_parity' not in data


def test_cache_sync_module_names_no_registry_file():
    """The cache-sync module reads and writes no plugin registry.

    The registry block is computed by the engine after ``sync_cache`` returns,
    so the module carries no reference to the registry file at all.
    """
    source = _CACHE_SYNC_PY.read_text(encoding='utf-8')

    assert 'def sync_cache(' in source, 'the scan did not read the cache-sync module'
    assert 'installed_plugins' not in source
