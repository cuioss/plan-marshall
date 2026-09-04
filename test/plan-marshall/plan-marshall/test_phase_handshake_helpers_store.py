#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for phase_handshake _git_helpers and _handshake_store.

Split from test_phase_handshake.py: covers low-level git helpers
(`git_head`, `git_dirty_count`) and the handshake store CRUD verbs
(`upsert_row`, `load_rows`, `remove_row`, `get_row`).
"""

from __future__ import annotations

import os
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


def test_git_head_outside_repo(outside_repo_dir: Path) -> None:
    # Must be OUTSIDE the repo: pytest's tmp_path now roots under the repo-local
    # --basetemp, where git_head would resolve HEAD instead of returning None.
    assert git_helpers.git_head(outside_repo_dir) is None


# =============================================================================
# Undecodable path bytes
# =============================================================================
#
# A Git path is a byte string, and POSIX admits every byte but NUL and ``/``. The
# two PATH-bearing helpers decode their subprocess output, and a STRICT decode
# raises ``UnicodeDecodeError`` — a ``ValueError``, therefore outside the
# ``(CalledProcessError, FileNotFoundError, TimeoutExpired)`` tuple both helpers
# catch, so it escapes the caller uncaught rather than degrading to the ``None``
# the helpers document. ``-z`` made the two sides of the downstream comparison
# agree on QUOTING; it says nothing about the BYTES.

#: A byte no UTF-8 decoder accepts.
_UNDECODABLE_BYTE = b'\xff'
#: The path the stand-in git reports, as raw bytes.
_UNDECODABLE_PATH = b'bad' + _UNDECODABLE_BYTE + b'.txt'


@pytest.fixture
def git_emitting_an_undecodable_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Put a stand-in ``git`` on PATH that writes an undecodable path byte.

    The bytes have to arrive through a real subprocess pipe, because the decode
    under test is the one ``subprocess.run`` performs. The filesystem is not a
    usable source of them: APFS rejects a filename that is not valid UTF-8, so a
    fixture creating one would error on macOS before reaching the subject and
    would exercise the helper on Linux only.

    The stand-in answers both spellings the helpers use — it NUL-terminates the
    record when ``-z`` is present and newline-terminates it otherwise.
    """
    bin_dir = tmp_path / 'fakebin'
    bin_dir.mkdir()
    script = bin_dir / 'git'
    script.write_text(
        '#!/usr/bin/env python3\n'
        'import sys\n'
        f'sys.stdout.buffer.write(b"?? " + {_UNDECODABLE_PATH!r})\n'
        'sys.stdout.buffer.write(b"\\x00" if "-z" in sys.argv else b"\\n")\n',
        encoding='utf-8',
    )
    script.chmod(0o755)
    monkeypatch.setenv('PATH', str(bin_dir), prepend=os.pathsep)
    return bin_dir


def test_git_dirty_files_reports_a_path_carrying_an_undecodable_byte(
    git_emitting_an_undecodable_path: Path, tmp_path: Path
) -> None:
    """The path is returned round-trippably instead of raising out of the helper."""
    paths = git_helpers.git_dirty_files(tmp_path)

    assert paths is not None
    assert [p.encode('utf-8', 'surrogateescape') for p in paths] == [_UNDECODABLE_PATH]


def test_git_dirty_count_counts_a_path_carrying_an_undecodable_byte(
    git_emitting_an_undecodable_path: Path, tmp_path: Path
) -> None:
    """The sibling counter performs the same decode and needs the same tolerance."""
    assert git_helpers.git_dirty_count(tmp_path) == 1


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
