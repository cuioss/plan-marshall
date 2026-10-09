#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for how the registry repin treats the registry path and the document it rewrites.

Two contracts are covered. A registry path that is a symbolic link is read but
never written: the repin neither writes through the link nor replaces it. And
the entries the repin rewrites are the ones the shared reader's own walk yields,
so the repin carries no second filter over the registry document.

Every fixture is a real file tree under ``tmp_path``; the real ``~/.claude``
tree is never read or written.
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
NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
BUNDLE = 'plan-marshall'
MARKER = '.orphaned_at'


class LinkedHome(NamedTuple):
    """A fixture home whose registry path is a symbolic link to a file elsewhere."""

    link: Path
    real: Path
    cache_root: Path

    def marker(self) -> Path:
        return self.cache_root / BUNDLE / TARGET / MARKER

    def leftovers(self) -> list[Path]:
        """Every file beside the link other than the link itself: a backup or a temp file."""
        return sorted(path for path in self.link.parent.iterdir() if path != self.link and not path.is_dir())


def _write_registry(path: Path, cache_root: Path, version: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {'scope': 'user', 'installPath': str(cache_root / BUNDLE / version), 'version': version}
    path.write_text(
        json.dumps({'version': 2, 'plugins': {f'{BUNDLE}@plan-marshall': [entry]}}, indent=2) + '\n',
        encoding='utf-8',
    )


def _make_cache(tmp_path: Path) -> Path:
    cache_root = tmp_path / 'plugins' / 'cache' / 'plan-marshall'
    for version in (OLD, TARGET):
        (cache_root / BUNDLE / version).mkdir(parents=True)
    return cache_root


@pytest.fixture
def linked_home(tmp_path: Path) -> LinkedHome:
    """A registry pinned behind the target, reached through a symbolic link.

    The target version directory carries an ``.orphaned_at`` marker, so a run
    that got as far as the first write step is observable.
    """
    cache_root = _make_cache(tmp_path)
    real = tmp_path / 'dotfiles' / 'installed_plugins.json'
    _write_registry(real, cache_root, OLD)
    link = tmp_path / 'plugins' / 'installed_plugins.json'
    link.symlink_to(real)
    home = LinkedHome(link, real, cache_root)
    home.marker().write_text('2026-01-01T00:00:00Z', encoding='utf-8')
    return home


def _run(home: LinkedHome, **kwargs: Any) -> dict[str, Any]:
    return rp.repin(registry_path=home.link, cache_root=home.cache_root, now=NOW, **kwargs)


def _cli_args(home: LinkedHome, *extra: str) -> list[str]:
    return [*extra, '--cache-root', str(home.cache_root), '--registry-path', str(home.link)]


# =============================================================================
# A registry path that is a symbolic link
# =============================================================================


def test_apply_refuses_a_symlinked_registry_and_changes_nothing(linked_home):
    """The link's target is byte-identical, the link is still that link, and no step ran."""
    before = linked_home.real.read_bytes()

    result = _run(linked_home, apply=True)

    assert linked_home.real.read_bytes() == before
    assert linked_home.link.is_symlink()
    assert linked_home.link.readlink() == linked_home.real
    assert linked_home.marker().exists()
    assert linked_home.leftovers() == []
    assert (result['status'], result['gate'], result['exit_code']) == ('error', rp.GATE_FAILED, 1)
    assert [row['action'] for row in result['entries']] == [rp.ACTION_FAILED]


def test_refusal_names_the_link(linked_home):
    """The message says which path is the link, so the operator can find it."""
    result = _run(linked_home, apply=True)

    assert str(linked_home.link) in result['message']
    assert 'symbolic link' in result['message']
    assert 'backup_path' not in result


def test_cli_apply_on_a_symlinked_registry_exits_nonzero_and_prints_the_refusal(linked_home, capsys):
    """``--apply`` through the CLI prints the refusal and the verdict, and writes nothing."""
    before = linked_home.real.read_bytes()

    exit_code = rp.main(_cli_args(linked_home, '--apply'))

    lines = capsys.readouterr().out.splitlines()
    assert exit_code == 1
    assert 'status: error' in lines
    assert any(line.startswith('message: ') and str(linked_home.link) in line for line in lines)
    assert lines[-1] == 'registry_parity: behind'
    assert linked_home.real.read_bytes() == before
    assert linked_home.link.is_symlink()


def test_cli_dry_run_reports_a_symlinked_registry(linked_home, capsys):
    """Without ``--apply`` the report is printed from what the link points at."""
    before = linked_home.real.read_bytes()

    exit_code = rp.main(_cli_args(linked_home))

    lines = capsys.readouterr().out.splitlines()
    assert exit_code == 1
    assert 'status: success' in lines
    assert 'mode: dry_run' in lines
    assert f'  {BUNDLE},user,{OLD},{OLD},{TARGET},{TARGET},report' in lines
    assert lines[-1] == 'registry_parity: behind'
    assert linked_home.real.read_bytes() == before
    assert linked_home.link.is_symlink()


def test_apply_with_nothing_to_rewrite_reads_through_the_link(linked_home):
    """A linked registry already at the target needs no write, so there is nothing to refuse."""
    _write_registry(linked_home.real, linked_home.cache_root, TARGET)
    before = linked_home.real.read_bytes()

    result = _run(linked_home, apply=True)

    assert linked_home.real.read_bytes() == before
    assert linked_home.link.is_symlink()
    assert [row['action'] for row in result['entries']] == [rp.ACTION_NOOP]
    assert (result['status'], result['registry_parity'], result['exit_code']) == ('success', 'in_parity', 0)


def test_replace_refuses_a_path_that_became_a_link_after_the_read(linked_home):
    """The replace step holds the refusal on its own, whatever ran before it."""
    original = linked_home.real.read_bytes()

    with pytest.raises(rp.RepinError, match='symbolic link'):
        rp._replace_registry(linked_home.link, original, {'version': 2, 'plugins': {}})

    assert linked_home.real.read_bytes() == original
    assert linked_home.link.is_symlink()
    assert linked_home.leftovers() == []


def test_apply_rewrites_a_regular_registry_file(tmp_path):
    """The matched control: the same registry as a regular file is repinned."""
    cache_root = _make_cache(tmp_path)
    registry = tmp_path / 'plugins' / 'installed_plugins.json'
    _write_registry(registry, cache_root, OLD)

    result = rp.repin(registry_path=registry, cache_root=cache_root, now=NOW, apply=True)

    document = json.loads(registry.read_text(encoding='utf-8'))
    assert document['plugins'][f'{BUNDLE}@plan-marshall'][0]['version'] == TARGET
    assert (result['status'], result['gate'], result['exit_code']) == ('success', rp.GATE_PASSED, 0)


# =============================================================================
# The repin walks the registry with the shared reader's own walk
# =============================================================================


def test_apply_writes_the_document_the_shared_walk_was_handed(tmp_path, monkeypatch):
    """The entries the repin rewrites are the dicts the shared walk yielded."""
    cache_root = _make_cache(tmp_path)
    registry = tmp_path / 'plugins' / 'installed_plugins.json'
    _write_registry(registry, cache_root, OLD)
    real_walk = rp._registry.iter_marketplace_entries
    walked: list[Any] = []
    yielded: list[dict] = []
    written: list[Any] = []

    def recording_walk(document, *args):
        walked.append(document)
        for bundle, entry in real_walk(document, *args):
            yielded.append(entry)
            yield bundle, entry

    monkeypatch.setattr(rp._registry, 'iter_marketplace_entries', recording_walk)
    monkeypatch.setitem(rp._apply.__globals__, '_replace_registry', lambda _path, _original, doc: written.append(doc))

    rp.repin(registry_path=registry, cache_root=cache_root, now=NOW, apply=True)

    assert len(written) == 1
    assert any(document is written[0] for document in walked)
    rewritten = written[0]['plugins'][f'{BUNDLE}@plan-marshall'][0]
    assert rewritten['version'] == TARGET
    assert any(entry is rewritten for entry in yielded)


def test_module_carries_no_registry_filter_of_its_own():
    """A second filter would have to look the ``plugins`` member up or split a key itself."""
    tree = ast.parse(Path(rp.__file__).read_text(encoding='utf-8'))

    constants = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant)]
    attributes = [node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)]
    plugins_lookups = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == 'get'
        and any(isinstance(arg, ast.Constant) and arg.value == 'plugins' for arg in node.args)
    ]

    assert 'iter_marketplace_entries' in attributes
    assert plugins_lookups == []
    assert '@' not in constants
    assert [name for name in attributes if name in ('rpartition', 'partition', 'split')] == []
