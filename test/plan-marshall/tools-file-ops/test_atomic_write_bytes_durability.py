#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Durability of ``file_ops.atomic_write_bytes``.

The byte writer is the snapshot rollback path: a restore that returns after the
rename while the bytes are still only in the page cache is not a restore, an
artifact that changes mode on every rewrite is a surprise for the next reader,
and a descriptor leaked on the error path is a leak per failed write. Each
property is asserted against the primitive the implementation must use, so the
test fails when the property is dropped rather than when an unrelated detail
changes.
"""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path
from typing import Any

import pytest
from file_ops import atomic_write_bytes


def test_a_replaced_file_keeps_its_previous_mode(tmp_path: Path) -> None:
    """A rewrite must not silently re-permission the artifact it replaces."""
    target = tmp_path / 'snapshot.json'
    target.write_bytes(b'{"old": true}\n')
    os.chmod(target, 0o640)

    atomic_write_bytes(target, b'{"new": true}\n')

    assert target.read_bytes() == b'{"new": true}\n'
    assert stat.S_IMODE(target.stat().st_mode) == 0o640


def test_an_fdopen_failure_leaves_no_open_descriptor_and_no_temp_file(tmp_path: Path, monkeypatch) -> None:
    """``os.fdopen`` can fail, and the descriptor stays this function's problem.

    The injected failure captures the descriptor ``mkstemp`` handed back, so the
    assertions are on the real resource: the fd must be closed afterwards (a
    closed fd answers EBADF), and the temp file must be gone.
    """
    target = tmp_path / 'artifact.json'
    target.write_bytes(b'prior\n')
    captured: dict[str, int] = {}

    def _fail_fdopen(fd: int, *args: Any, **kwargs: Any) -> Any:
        captured['fd'] = fd
        raise OSError('injected fdopen failure')

    monkeypatch.setattr(os, 'fdopen', _fail_fdopen)

    with pytest.raises(OSError, match='injected fdopen failure'):
        atomic_write_bytes(target, b'new\n')

    assert captured['fd'] > 2
    with pytest.raises(OSError):
        os.fstat(captured['fd'])
    assert list(tmp_path.glob('.tmp_*')) == []
    assert target.read_bytes() == b'prior\n'


def test_the_temp_file_is_fsynced_before_the_replace(tmp_path: Path, monkeypatch) -> None:
    """Durability is ordered: data synced, then renamed, then the rename synced.

    Recorded as a call log so the assertion is on order, not on call counts: an
    implementation that replaces first and syncs the result has already published
    bytes a crash can lose.
    """
    target = tmp_path / 'artifact.json'
    target.write_bytes(b'prior\n')
    events: list[tuple[str, Any]] = []
    real_replace = os.replace
    real_fsync = os.fsync

    def _record_fsync(fd: int) -> None:
        events.append(('fsync', fd))
        real_fsync(fd)

    def _record_replace(src: Any, dst: Any, *args: Any, **kwargs: Any) -> None:
        events.append(('replace', str(src), str(dst)))
        real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, 'fsync', _record_fsync)
    monkeypatch.setattr(os, 'replace', _record_replace)

    atomic_write_bytes(target, b'new\n')

    replace_index = next(index for index, event in enumerate(events) if event[0] == 'replace')
    assert [event for event in events[:replace_index] if event[0] == 'fsync'], events
    assert [event for event in events[replace_index + 1 :] if event[0] == 'fsync'], events
    assert target.read_bytes() == b'new\n'


def test_a_first_write_needs_no_previous_mode(tmp_path: Path) -> None:
    """A target that does not exist yet still commits (no mode to preserve)."""
    target = tmp_path / 'fresh' / 'artifact.json'

    atomic_write_bytes(target, b'content\n')

    assert target.read_bytes() == b'content\n'
    assert list(target.parent.glob('.tmp_*')) == []


def test_the_atomic_write_uses_same_directory_temp_files(tmp_path: Path, monkeypatch) -> None:
    """The temp file must live beside the target, or the rename is not atomic."""
    target = tmp_path / 'artifact.json'
    seen: dict[str, str] = {}
    real_mkstemp = tempfile.mkstemp

    def _record_mkstemp(*args: Any, **kwargs: Any) -> Any:
        seen['dir'] = str(kwargs.get('dir'))
        return real_mkstemp(*args, **kwargs)

    monkeypatch.setattr(tempfile, 'mkstemp', _record_mkstemp)

    atomic_write_bytes(target, b'content\n')

    assert Path(seen['dir']) == tmp_path
