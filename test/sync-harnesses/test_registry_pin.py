#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the opt-in plugin-registry repin.

Every test runs against a fixture home under ``tmp_path``: a registry file and a
plugin-cache root holding ``{bundle}/{version}/`` directories. The real
``~/.claude`` tree is never read or written.

The script lives at ``marketplace/targets/claude/registry_pin.py``, not in a
marketplace bundle — the harness sync is meta-project-only tooling.
"""

from __future__ import annotations

import ast
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

import pytest

from marketplace.targets.claude import registry_pin as rp

OLD = '0.1.100'
TARGET = '0.1.200'
NEWER = '0.1.300'
NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
FOREIGN_KEY = 'other-plugin@other-market'
MARKER = '.orphaned_at'
IN_USE = '.in_use'

#: One bundle behind the target, with the target directory in the cache.
BEHIND_PINS = (('plan-marshall', OLD, 'user'),)
BEHIND_CACHE = {'plan-marshall': (OLD, TARGET)}


class Home(NamedTuple):
    """A fixture home: the registry file and the plugin-cache root."""

    registry: Path
    cache_root: Path

    def document(self) -> dict[str, Any]:
        return dict(json.loads(self.registry.read_text(encoding='utf-8')))

    def entries(self, bundle: str) -> list[dict[str, Any]]:
        return list(self.document()['plugins'][f'{bundle}@plan-marshall'])

    def backups(self) -> list[Path]:
        return sorted(self.registry.parent.glob(f'{self.registry.name}.repin-backup-*'))

    def marker(self, bundle: str, version: str) -> Path:
        return self.cache_root / bundle / version / MARKER

    def mark(self, bundle: str, version: str) -> Path:
        marker = self.marker(bundle, version)
        marker.write_text('2026-01-01T00:00:00Z', encoding='utf-8')
        return marker


def make_home(
    tmp_path: Path,
    *,
    pins: tuple[tuple[str, str, str], ...] = BEHIND_PINS,
    cache: dict[str, tuple[str, ...]] | None = None,
) -> Home:
    """Build a registry pinning ``pins`` and a cache holding the ``cache`` version dirs.

    Every version directory carries an ``.in_use`` file, and the registry carries
    one entry of a foreign marketplace beside the plan-marshall ones.
    """
    cache_root = tmp_path / 'plugins' / 'cache' / 'plan-marshall'
    for bundle, versions in (BEHIND_CACHE if cache is None else cache).items():
        for version in versions:
            (cache_root / bundle / version).mkdir(parents=True)
            (cache_root / bundle / version / IN_USE).write_text('1234', encoding='utf-8')

    plugins: dict[str, list[dict[str, str]]] = {
        FOREIGN_KEY: [{'scope': 'user', 'installPath': '/elsewhere/other-plugin/9.9.9', 'version': '9.9.9'}]
    }
    for bundle, version, scope in pins:
        plugins.setdefault(f'{bundle}@plan-marshall', []).append(
            {
                'scope': scope,
                'installPath': str(cache_root / bundle / version),
                'version': version,
                'lastUpdated': '2025-01-01T00:00:00.000Z',
                'gitCommitSha': 'old-sha',
            }
        )
    registry = tmp_path / 'plugins' / 'installed_plugins.json'
    registry.write_text(json.dumps({'version': 2, 'plugins': plugins}, indent=2) + '\n', encoding='utf-8')
    return Home(registry, cache_root)


def run(home: Home, **kwargs: Any) -> dict[str, Any]:
    return rp.repin(registry_path=home.registry, cache_root=home.cache_root, now=NOW, **kwargs)


def actions(result: dict[str, Any]) -> list[tuple[str, str]]:
    return [(row['bundle'], row['action']) for row in result['entries']]


def cli_args(home: Home, *extra: str) -> list[str]:
    return [*extra, '--cache-root', str(home.cache_root), '--registry-path', str(home.registry)]


# =============================================================================
# Dry run — the default
# =============================================================================


def test_dry_run_writes_nothing(tmp_path):
    """A dry run leaves the registry, every marker and the backup set unchanged."""
    home = make_home(tmp_path)
    marker = home.mark('plan-marshall', TARGET)
    before = home.registry.read_bytes()

    result = run(home)

    assert home.registry.read_bytes() == before
    assert marker.exists()
    assert home.backups() == []
    assert (result['mode'], result['markers_removed'], result['gate']) == (rp.MODE_DRY_RUN, 0, rp.GATE_NOT_RUN)


def test_dry_run_reports_the_before_and_after_version_per_entry(tmp_path):
    """A dry-run row states the pinned version and the version an apply would pin."""
    home = make_home(tmp_path)

    result = run(home)

    assert result['entries'] == [
        {
            'bundle': 'plan-marshall',
            'scope': 'user',
            'before_install_path_version': OLD,
            'before_version': OLD,
            'after_install_path_version': TARGET,
            'after_version': TARGET,
            'action': rp.ACTION_REPORT,
        }
    ]


def test_cli_without_apply_is_a_dry_run_that_exits_nonzero_when_behind(tmp_path, capsys):
    """Without ``--apply`` the CLI writes nothing, and a registry behind exits 1.

    The verdict is the last line of the result, so a caller reading the tail of
    the output reads the parity rather than a row.
    """
    home = make_home(tmp_path)
    before = home.registry.read_bytes()

    exit_code = rp.main(cli_args(home))

    lines = capsys.readouterr().out.splitlines()
    assert exit_code == 1
    assert 'mode: dry_run' in lines
    assert lines[-1] == 'registry_parity: behind'
    assert home.registry.read_bytes() == before


@pytest.mark.parametrize('apply', [False, True], ids=['dry-run', 'apply'])
def test_absent_registry_is_unreadable_and_exits_zero(tmp_path, apply):
    """An absent registry is ``unreadable``, not a failure, and nothing is created."""
    home = make_home(tmp_path)
    home.registry.unlink()

    result = run(home, apply=apply)

    assert (result['registry_parity'], result['exit_code'], result['entries']) == ('unreadable', 0, [])
    assert not home.registry.exists()
    assert home.backups() == []


# =============================================================================
# Apply — what is rewritten
# =============================================================================


def test_apply_pins_every_entry_whose_bundle_has_the_target_directory(tmp_path):
    """Each scope entry reads the target in ``installPath`` and ``version``, behind one backup."""
    home = make_home(
        tmp_path,
        pins=(('plan-marshall', OLD, 'user'), ('plan-marshall', OLD, 'project'), ('pm-dev-java', OLD, 'user')),
        cache={'plan-marshall': (OLD, TARGET), 'pm-dev-java': (OLD, TARGET)},
    )
    original = home.registry.read_bytes()

    result = run(home, apply=True)

    for bundle in ('plan-marshall', 'pm-dev-java'):
        for entry in home.entries(bundle):
            assert entry['installPath'] == str((home.cache_root / bundle / TARGET).resolve())
            assert entry['version'] == TARGET
            assert entry['lastUpdated'] == '2026-01-02T03:04:05.000Z'
    assert [backup.read_bytes() for backup in home.backups()] == [original]
    assert {action for _, action in actions(result)} == {rp.ACTION_REPINNED}
    assert (result['gate'], result['registry_parity'], result['exit_code']) == (rp.GATE_PASSED, 'in_parity', 0)


def test_apply_leaves_an_entry_whose_bundle_lacks_the_target_directory(tmp_path):
    """An entry is never pointed at a directory that does not exist; the run reports ``behind``."""
    home = make_home(
        tmp_path,
        pins=(('plan-marshall', OLD, 'user'), ('pm-dev-java', OLD, 'user')),
        cache={'plan-marshall': (OLD, TARGET), 'pm-dev-java': (OLD,)},
    )
    untouched = home.entries('pm-dev-java')

    result = run(home, apply=True, target_version=TARGET)

    assert home.entries('pm-dev-java') == untouched
    assert actions(result) == [('plan-marshall', rp.ACTION_REPINNED), ('pm-dev-java', rp.ACTION_NOOP)]
    assert (result['registry_parity'], result['exit_code']) == ('behind', 1)


@pytest.mark.parametrize(
    'manifest,expected',
    [('{"source_sha": "abc123"}', 'abc123'), (None, 'old-sha'), ('not json', 'old-sha')],
    ids=['manifest-names-sha', 'no-manifest', 'unparseable-manifest'],
)
def test_apply_stamps_the_commit_sha_only_when_the_dist_manifest_names_one(tmp_path, manifest, expected):
    """``gitCommitSha`` follows the cache-root manifest's ``source_sha`` and is otherwise kept."""
    home = make_home(tmp_path)
    if manifest is not None:
        (home.cache_root / 'dist-manifest.json').write_text(manifest, encoding='utf-8')

    run(home, apply=True)

    assert home.entries('plan-marshall')[0]['gitCommitSha'] == expected


def test_apply_leaves_a_foreign_marketplace_entry_identical(tmp_path):
    """Entries of another marketplace are carried through the rewrite unchanged."""
    home = make_home(tmp_path)
    before = json.dumps(home.document()['plugins'][FOREIGN_KEY])

    run(home, apply=True)

    assert json.dumps(home.document()['plugins'][FOREIGN_KEY]) == before
    assert home.entries('plan-marshall')[0]['version'] == TARGET


def test_apply_never_touches_an_in_use_file(tmp_path):
    """Every ``.in_use`` file survives an apply with its content."""
    home = make_home(tmp_path)

    run(home, apply=True)

    for version in (OLD, TARGET):
        assert (home.cache_root / 'plan-marshall' / version / IN_USE).read_text(encoding='utf-8') == '1234'


def test_apply_removes_the_orphan_marker_only_where_an_entry_is_pinned_afterwards(tmp_path):
    """Only a directory the registry names once the run is over is un-orphaned.

    The matched controls are the directory the entry is moved away from and the
    target directory of a bundle whose entry stays ahead of the target.
    """
    home = make_home(
        tmp_path,
        pins=(('plan-marshall', OLD, 'user'), ('pm-dev-java', NEWER, 'user')),
        cache={'plan-marshall': (OLD, TARGET), 'pm-dev-java': (TARGET, NEWER)},
    )
    pinned_after = home.mark('plan-marshall', TARGET)
    left_behind = home.mark('plan-marshall', OLD)
    never_pinned = home.mark('pm-dev-java', TARGET)

    result = run(home, apply=True, target_version=TARGET)

    assert not pinned_after.exists()
    assert left_behind.exists()
    assert never_pinned.exists()
    assert result['markers_removed'] == 1


# =============================================================================
# Apply — what is left alone
# =============================================================================


def test_already_pinned_registry_is_a_noop(tmp_path):
    """A registry at the target is byte-identical afterwards and gains no backup."""
    home = make_home(tmp_path, pins=(('plan-marshall', TARGET, 'user'),))
    marker = home.mark('plan-marshall', TARGET)
    before = home.registry.read_bytes()

    result = run(home, apply=True)

    assert home.registry.read_bytes() == before
    assert home.backups() == []
    assert not marker.exists()
    assert actions(result) == [('plan-marshall', rp.ACTION_NOOP)]
    assert (result['gate'], result['registry_parity'], result['exit_code']) == (rp.GATE_PASSED, 'in_parity', 0)


def test_cli_apply_on_a_registry_ahead_never_moves_the_pin_backwards(tmp_path, capsys):
    """``--apply`` against an older target leaves the registry byte-identical and exits 0."""
    home = make_home(tmp_path, pins=(('plan-marshall', NEWER, 'user'),), cache={'plan-marshall': (TARGET, NEWER)})
    before = home.registry.read_bytes()

    exit_code = rp.main(cli_args(home, '--apply', '--target-version', TARGET))

    lines = capsys.readouterr().out.splitlines()
    assert exit_code == 0
    assert home.registry.read_bytes() == before
    assert home.backups() == []
    assert f'  plan-marshall,user,{NEWER},{NEWER},{NEWER},{NEWER},noop' in lines
    assert lines[-1] == 'registry_parity: ahead'


# =============================================================================
# Apply — order of operations, the gate and the concurrent writer
# =============================================================================


def test_apply_runs_marker_removal_then_backup_then_replace(tmp_path, monkeypatch):
    """The three write steps run in the documented order, each exactly once."""
    home = make_home(tmp_path)
    calls: list[str] = []
    for name in ('_remove_orphan_markers', '_backup_registry', '_replace_registry'):
        real = getattr(rp, name)

        def recording(*args, _name=name, _real=real):
            calls.append(_name)
            return _real(*args)

        monkeypatch.setitem(rp._apply.__globals__, name, recording)

    run(home, apply=True)

    assert calls == ['_remove_orphan_markers', '_backup_registry', '_replace_registry']


def test_failure_after_marker_removal_leaves_the_registry_untouched(tmp_path, monkeypatch):
    """A failure between the marker removal and the registry write changes no registry byte.

    The marker being gone is what places the failure after step 1; the absent
    backup and the unchanged bytes are what place it before the write.
    """
    home = make_home(tmp_path)
    marker = home.mark('plan-marshall', TARGET)
    before = home.registry.read_bytes()

    def fail(*_args):
        raise OSError('disk full')

    monkeypatch.setitem(rp._apply.__globals__, '_backup_registry', fail)

    result = run(home, apply=True)

    assert home.registry.read_bytes() == before
    assert home.backups() == []
    assert not marker.exists()
    assert (result['status'], result['message'], result['exit_code']) == ('error', 'disk full', 1)
    assert actions(result) == [('plan-marshall', rp.ACTION_FAILED)]


def test_gate_fails_when_a_reread_entry_is_not_at_the_target(tmp_path, monkeypatch):
    """A replace that reports nothing wrong and changes nothing is caught by the re-read."""
    home = make_home(tmp_path)
    monkeypatch.setitem(rp._apply.__globals__, '_replace_registry', lambda *_args: None)

    result = run(home, apply=True)

    assert (result['status'], result['gate'], result['exit_code']) == ('error', rp.GATE_FAILED, 1)
    assert 'post-write gate failed' in result['message']
    assert actions(result) == [('plan-marshall', rp.ACTION_FAILED)]


def test_registry_written_by_someone_else_mid_run_is_not_replaced(tmp_path, monkeypatch):
    """A registry whose bytes change between the read and the replace keeps the other writer's bytes."""
    home = make_home(tmp_path)
    foreign = home.registry.read_bytes() + b'\n'
    real_backup = rp._backup_registry

    def backup_then_concurrent_write(*args):
        path = real_backup(*args)
        home.registry.write_bytes(foreign)
        return path

    monkeypatch.setitem(rp._apply.__globals__, '_backup_registry', backup_then_concurrent_write)

    result = run(home, apply=True)

    assert home.registry.read_bytes() == foreign
    assert result['status'] == 'error'
    assert 'changed while it was being repinned' in result['message']
    assert list(home.registry.parent.glob('.installed_plugins.json.*.tmp')) == []


# =============================================================================
# Module constraint
# =============================================================================


def test_module_imports_nothing_from_the_marketplace_package():
    """The script runs standalone under a bare ``python3``, so it imports no ``marketplace`` module."""
    tree = ast.parse(Path(rp.__file__).read_text(encoding='utf-8'))

    imported = [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
    imported += [node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]

    assert imported, 'the import scan found no import at all'
    assert [name for name in imported if name.split('.')[0] == 'marketplace'] == []
