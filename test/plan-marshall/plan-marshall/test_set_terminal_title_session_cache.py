#!/usr/bin/env python3
"""Tests for set_terminal_title.py session-cache write-through.

On every hook invocation (non-statusline, with a valid `session_id` in the
stdin payload), the script writes the id into:

- `~/.cache/plan-marshall/sessions/by-cwd/{sha256(cwd)}`
- `~/.cache/plan-marshall/sessions/current`

These writes populate the cache read by `manage_session.py current`. This
test module verifies the write-through directly (via direct calls to the
private helpers) and end-to-end (subprocess hook invocation with piped
stdin JSON).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from unittest import mock

import set_terminal_title  # type: ignore[import-not-found]  # noqa: E402

from conftest import MARKETPLACE_ROOT  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall' / 'scripts' / 'set_terminal_title.py'
)


def _expected_paths(home: Path, cwd: str) -> tuple[Path, Path]:
    cwd_hash = hashlib.sha256(cwd.encode('utf-8')).hexdigest()
    base = home / '.cache' / 'plan-marshall' / 'sessions'
    return base / 'by-cwd' / cwd_hash, base / 'current'


class TestWriteSessionCache:
    """Direct-invocation tests for _write_session_cache."""

    def test_writes_both_by_cwd_and_current(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
        cwd = '/path/to/my/repo'

        set_terminal_title._write_session_cache('session-xyz', cwd)

        by_cwd, current = _expected_paths(tmp_path, cwd)
        assert by_cwd.read_text(encoding='utf-8') == 'session-xyz'
        assert current.read_text(encoding='utf-8') == 'session-xyz'

    def test_empty_session_id_writes_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))

        set_terminal_title._write_session_cache('', '/some/cwd')
        set_terminal_title._write_session_cache(None, '/some/cwd')

        base = tmp_path / '.cache' / 'plan-marshall' / 'sessions'
        # The directory tree should not have been created at all.
        assert not base.exists()

    def test_empty_cwd_writes_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))

        set_terminal_title._write_session_cache('session-abc', '')

        base = tmp_path / '.cache' / 'plan-marshall' / 'sessions'
        assert not base.exists()

    def test_os_error_is_swallowed(self, tmp_path, monkeypatch):
        """Hook invariant: write failures must never propagate to the caller."""
        monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))

        def _raising(self, *_args, **_kwargs):
            raise OSError('disk full')

        with mock.patch.object(Path, 'write_text', _raising):
            # Must not raise
            set_terminal_title._write_session_cache('session-boom', '/some/cwd')

    def test_repeated_calls_overwrite_singleton_last_write_wins(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
        cwd_a = '/repo/a'
        cwd_b = '/repo/b'

        set_terminal_title._write_session_cache('session-a', cwd_a)
        set_terminal_title._write_session_cache('session-b', cwd_b)

        by_cwd_a, current = _expected_paths(tmp_path, cwd_a)
        by_cwd_b, _ = _expected_paths(tmp_path, cwd_b)

        # by-cwd entries for different cwds coexist; singleton reflects last write.
        assert by_cwd_a.read_text(encoding='utf-8') == 'session-a'
        assert by_cwd_b.read_text(encoding='utf-8') == 'session-b'
        assert current.read_text(encoding='utf-8') == 'session-b'


class TestHookWriteThrough:
    """Subprocess tests: full hook invocation with piped stdin JSON."""

    def _invoke(self, home: Path, payload: dict, status: str = 'running') -> subprocess.CompletedProcess:
        return subprocess.run(
            ['python3', str(SCRIPT_PATH), status],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={'HOME': str(home), 'PATH': '/usr/bin:/bin'},
            timeout=10,
        )

    def test_user_prompt_submit_populates_cache(self, tmp_path):
        payload = {
            'cwd': '/fake/repo/cwd',
            'prompt': '/plan-marshall action=execute',
            'session_id': 'hook-session-42',
        }
        result = self._invoke(tmp_path, payload, status='running')
        assert result.returncode == 0, f'Hook failed: {result.stderr}'

        by_cwd, current = _expected_paths(tmp_path, payload['cwd'])
        assert by_cwd.read_text(encoding='utf-8') == 'hook-session-42'
        assert current.read_text(encoding='utf-8') == 'hook-session-42'

    def test_missing_session_id_writes_no_cache(self, tmp_path):
        payload = {
            'cwd': '/fake/repo/cwd',
            'prompt': '/foo',
            # No session_id
        }
        result = self._invoke(tmp_path, payload, status='running')
        assert result.returncode == 0

        base = tmp_path / '.cache' / 'plan-marshall' / 'sessions'
        # Neither by-cwd nor current should exist.
        assert not (base / 'by-cwd').exists()
        assert not (base / 'current').exists()

    def test_statusline_does_not_write_cache(self, tmp_path):
        """The `--statusline` code path must be a pure read — no mutations."""
        payload = {
            'cwd': '/fake/repo/cwd',
            'prompt': '/foo',
            'session_id': 'statusline-should-not-write',
        }
        result = subprocess.run(
            ['python3', str(SCRIPT_PATH), 'idle', '--statusline'],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={'HOME': str(tmp_path), 'PATH': '/usr/bin:/bin'},
            timeout=10,
        )
        assert result.returncode == 0

        base = tmp_path / '.cache' / 'plan-marshall' / 'sessions'
        # No cache directory created on a pure read.
        assert not (base / 'by-cwd').exists()
        assert not (base / 'current').exists()
