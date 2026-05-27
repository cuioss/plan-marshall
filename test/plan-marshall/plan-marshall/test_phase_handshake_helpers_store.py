#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for phase_handshake _git_helpers and _handshake_store.

Split from test_phase_handshake.py: covers low-level git helpers
(`git_head`, `git_dirty_count`) and the handshake store CRUD verbs
(`upsert_row`, `load_rows`, `remove_row`, `get_row`).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from _handshake_fixtures import git_helpers, store


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Create a minimal git repo with one commit and a .gitignore."""
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(tmp_path)], check=True)
    subprocess.run(['git', '-C', str(tmp_path), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(tmp_path), 'config', 'user.name', 'Test'], check=True)
    (tmp_path / '.gitignore').write_text('.plan/\n')
    (tmp_path / 'README.md').write_text('x\n')
    subprocess.run(['git', '-C', str(tmp_path), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(tmp_path), 'commit', '-q', '-m', 'init'], check=True)
    return tmp_path


# =============================================================================
# _git_helpers
# =============================================================================


def test_git_head_returns_sha(repo: Path) -> None:
    sha = git_helpers.git_head(repo)
    assert sha is not None
    assert len(sha) == 40


def test_git_dirty_count_clean_repo(repo: Path) -> None:
    assert git_helpers.git_dirty_count(repo) == 0


def test_git_dirty_count_with_untracked(repo: Path) -> None:
    (repo / 'new.txt').write_text('y\n')
    assert git_helpers.git_dirty_count(repo) == 1


def test_git_head_outside_repo(tmp_path: Path) -> None:
    assert git_helpers.git_head(tmp_path) is None


# =============================================================================
# _handshake_store
# =============================================================================


def test_store_upsert_and_load(plan_context) -> None:
    store.upsert_row('handshake-store-a', {'phase': '5-execute', 'main_sha': 'abc'})
    rows = store.load_rows('handshake-store-a')
    assert len(rows) == 1
    assert rows[0]['phase'] == '5-execute'
    assert rows[0]['main_sha'] == 'abc'


def test_store_upsert_replaces_existing_phase(plan_context) -> None:
    store.upsert_row('handshake-store-b', {'phase': '5-execute', 'main_sha': 'old'})
    store.upsert_row('handshake-store-b', {'phase': '5-execute', 'main_sha': 'new'})
    rows = store.load_rows('handshake-store-b')
    assert len(rows) == 1
    assert rows[0]['main_sha'] == 'new'


def test_store_multiple_phases(plan_context) -> None:
    store.upsert_row('handshake-store-c', {'phase': '5-execute', 'main_sha': 'a'})
    store.upsert_row('handshake-store-c', {'phase': '6-finalize', 'main_sha': 'b'})
    rows = store.load_rows('handshake-store-c')
    phases = {r['phase'] for r in rows}
    assert phases == {'5-execute', '6-finalize'}


def test_store_remove_row(plan_context) -> None:
    store.upsert_row('handshake-store-d', {'phase': '5-execute', 'main_sha': 'a'})
    store.upsert_row('handshake-store-d', {'phase': '6-finalize', 'main_sha': 'b'})
    removed = store.remove_row('handshake-store-d', '5-execute')
    assert removed is True
    rows = store.load_rows('handshake-store-d')
    assert len(rows) == 1
    assert rows[0]['phase'] == '6-finalize'


def test_store_remove_missing_phase_returns_false(plan_context) -> None:
    store.upsert_row('handshake-store-e', {'phase': '5-execute', 'main_sha': 'a'})
    assert store.remove_row('handshake-store-e', '3-outline') is False


def test_store_load_missing_file(plan_context) -> None:
    assert store.load_rows('handshake-store-f') == []
