#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for _build_server_registry internals.

Drive the machine-global marshalld registry helpers directly by inserting the
script-shared build scripts dir on sys.path. Every test isolates the
machine-global home root by pointing ``PLAN_MARSHALL_HOME`` at a per-test
``tmp_path`` (``home_root()`` reads the env var live on each call), so no test
touches the real ``~/.plan-marshall/marshalld/`` tree.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'script-shared', 'build/_build_server_registry.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _build_server_registry as registry  # noqa: E402


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """Point the machine-global home root at an isolated tmp dir."""
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return Path(tmp_path)


def _read_audit_lines() -> list[dict]:
    path = registry.audit_path()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


# =============================================================================
# Read — missing / corrupt
# =============================================================================


def test_read_registry_missing_file_returns_empty(home):
    result = registry.read_registry()

    assert result == {'version': registry.REGISTRY_VERSION, 'projects': {}}


def test_read_registry_corrupt_file_degrades_to_empty(home):
    registry.ensure_registry_dir()
    registry.registry_path().write_text('{ not valid json', encoding='utf-8')

    result = registry.read_registry()

    assert result['projects'] == {}


def test_read_registry_wrong_shape_normalized(home):
    registry.ensure_registry_dir()
    # Valid JSON but ``projects`` is not a dict.
    registry.registry_path().write_text(json.dumps({'projects': [1, 2]}), encoding='utf-8')

    result = registry.read_registry()

    assert result['projects'] == {}
    assert result['version'] == registry.REGISTRY_VERSION


# =============================================================================
# Register — record shape, persistence, audit
# =============================================================================


def test_register_creates_record_and_file(home):
    root = home / 'proj'
    root.mkdir()

    record = registry.register_project(
        root, worktree_containers=[str(home / 'wts')], notation_allowlist=['a:b:c']
    )

    assert registry.registry_path().exists()
    stored = registry.read_registry()['projects']
    assert record['canonical_root'] in stored
    assert stored[record['canonical_root']] == record


def test_register_record_shape(home):
    root = home / 'proj'
    root.mkdir()

    record = registry.register_project(root, notation_allowlist=['a:b:c'])

    assert set(record) == {
        'canonical_root',
        'worktree_containers',
        'notation_allowlist',
        'registered_at',
        'updated_at',
    }
    assert record['notation_allowlist'] == ['a:b:c']
    assert record['worktree_containers'] == []
    assert record['registered_at']
    assert record['updated_at']


def test_register_appends_audit_line(home):
    root = home / 'proj'
    root.mkdir()

    registry.register_project(root, notation_allowlist=['a:b:c'])
    registry.register_project(root, notation_allowlist=['a:b:d'])

    lines = _read_audit_lines()
    assert len(lines) == 2
    assert all(entry['action'] == registry.ACTION_REGISTER for entry in lines)
    assert lines[0]['canonical_root'] == registry.canonicalize_root(root)
    assert lines[1]['notation_allowlist'] == ['a:b:d']


def test_register_canonicalizes_symlinked_root(home):
    real = home / 'real-proj'
    real.mkdir()
    link = home / 'link-proj'
    os.symlink(real, link)

    record = registry.register_project(link)

    assert record['canonical_root'] == str(real.resolve())


def test_register_idempotent_preserves_registered_at(home):
    root = home / 'proj'
    root.mkdir()

    first = registry.register_project(root, notation_allowlist=['a:b:c'])
    second = registry.register_project(root, notation_allowlist=['a:b:d'])

    assert second['registered_at'] == first['registered_at']
    assert second['notation_allowlist'] == ['a:b:d']
    # Exactly one stored record for the canonical root (upsert, not append).
    assert list(registry.read_registry()['projects']) == [first['canonical_root']]


# =============================================================================
# Unregister
# =============================================================================


def test_unregister_removes_and_audits(home):
    root = home / 'proj'
    root.mkdir()
    registry.register_project(root)

    removed = registry.unregister_project(root)

    assert removed is True
    assert registry.read_registry()['projects'] == {}
    actions = [entry['action'] for entry in _read_audit_lines()]
    assert actions == [registry.ACTION_REGISTER, registry.ACTION_UNREGISTER]


def test_unregister_absent_returns_false_without_audit(home):
    result = registry.unregister_project(home / 'never-registered')

    assert result is False
    assert _read_audit_lines() == []


# =============================================================================
# Lookup
# =============================================================================


def test_get_project_hit_and_miss(home):
    root = home / 'proj'
    root.mkdir()
    registry.register_project(root)
    reg = registry.read_registry()
    canonical = registry.canonicalize_root(root)

    assert registry.get_project(reg, canonical) is not None
    assert registry.get_project(reg, '/nope') is None


def test_find_project_for_root_by_canonical(home):
    root = home / 'proj'
    root.mkdir()
    registry.register_project(root)
    reg = registry.read_registry()

    found = registry.find_project_for_root(reg, root)

    assert found is not None
    assert found['canonical_root'] == registry.canonicalize_root(root)


def test_find_project_for_root_by_container(home):
    root = home / 'proj'
    root.mkdir()
    container = home / 'worktrees'
    container.mkdir()
    registry.register_project(root, worktree_containers=[str(container)])
    reg = registry.read_registry()

    worktree = container / 'feature-x'
    found = registry.find_project_for_root(reg, worktree)

    assert found is not None
    assert found['canonical_root'] == registry.canonicalize_root(root)


def test_find_project_for_root_no_match(home):
    root = home / 'proj'
    root.mkdir()
    registry.register_project(root)
    reg = registry.read_registry()

    assert registry.find_project_for_root(reg, home / 'unrelated') is None


# =============================================================================
# Permissions
# =============================================================================


def test_registry_dir_is_0700(home):
    directory = registry.ensure_registry_dir()

    assert (directory.stat().st_mode & 0o777) == 0o700


def test_registry_file_is_0600(home):
    root = home / 'proj'
    root.mkdir()
    registry.register_project(root)

    assert (registry.registry_path().stat().st_mode & 0o777) == 0o600


# =============================================================================
# ProjectRecord dataclass
# =============================================================================


def test_project_record_from_dict_defaults():
    record = registry.ProjectRecord.from_dict({'canonical_root': '/r'})

    assert record.canonical_root == '/r'
    assert record.worktree_containers == []
    assert record.notation_allowlist == []
    assert record.registered_at == ''


def test_project_record_round_trip():
    record = registry.ProjectRecord(
        canonical_root='/r',
        worktree_containers=['/w'],
        notation_allowlist=['a:b:c'],
        registered_at='t0',
        updated_at='t1',
    )

    assert registry.ProjectRecord.from_dict(record.to_dict()) == record
