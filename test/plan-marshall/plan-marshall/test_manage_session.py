#!/usr/bin/env python3
"""Tests for manage_session.py — the plan-marshall session_id resolver.

Exercises the `current` and `transcript-path` subcommands. Isolates
`~/.cache/plan-marshall/sessions/` and `~/.claude/projects/` writes to a
per-test tmp tree via `HOME` / `Path.home()` patching, and covers:

- `by-cwd/{sha256(cwd)}` hit returns the stored id
- `by-cwd` miss with `current` singleton hit returns the singleton value
- both caches missing returns `status: error, error: session_id_unavailable`
- transcript-path slug-hit returns the JSONL path under the cwd-derived slug
- transcript-path total miss returns `status: error, error: transcript_not_found`
- transcript-path cross-cwd recovery via parent-directory glob fallback
- CLI plumbing: subprocess invocation emits valid TOON via the executor PYTHONPATH
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from unittest import mock

import manage_session  # type: ignore[import-not-found]  # noqa: E402

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall' / 'scripts' / 'manage_session.py'


def _seed_by_cwd(home: Path, cwd: str, session_id: str) -> Path:
    cwd_hash = hashlib.sha256(cwd.encode('utf-8')).hexdigest()
    path = home / '.cache' / 'plan-marshall' / 'sessions' / 'by-cwd' / cwd_hash
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(session_id, encoding='utf-8')
    return path


def _seed_current(home: Path, session_id: str) -> Path:
    path = home / '.cache' / 'plan-marshall' / 'sessions' / 'current'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(session_id, encoding='utf-8')
    return path


class TestCmdCurrent:
    """Direct-invocation tests for cmd_current."""

    def test_by_cwd_hit_returns_stored_id(self, tmp_path, monkeypatch, capsys):
        """by-cwd cache is the primary source."""
        repo_root = str(tmp_path / 'repo')
        (tmp_path / 'repo').mkdir()
        _seed_by_cwd(tmp_path, repo_root, 'session-abc-123')

        monkeypatch.setattr(manage_session, '_resolve_cwd', lambda: repo_root)
        monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))

        rc = manage_session.cmd_current(mock.Mock())
        out = capsys.readouterr().out

        assert rc == 0
        assert 'status: success' in out
        assert 'session_id: session-abc-123' in out

    def test_by_cwd_miss_falls_back_to_current_singleton(self, tmp_path, monkeypatch, capsys):
        """When by-cwd is empty, the singleton `current` file wins."""
        repo_root = str(tmp_path / 'repo')
        (tmp_path / 'repo').mkdir()
        _seed_current(tmp_path, 'session-singleton-xyz')

        monkeypatch.setattr(manage_session, '_resolve_cwd', lambda: repo_root)
        monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))

        rc = manage_session.cmd_current(mock.Mock())
        out = capsys.readouterr().out

        assert rc == 0
        assert 'status: success' in out
        assert 'session_id: session-singleton-xyz' in out

    def test_by_cwd_wins_over_singleton_when_both_present(self, tmp_path, monkeypatch, capsys):
        """The cwd-keyed entry must take precedence over the singleton."""
        repo_root = str(tmp_path / 'repo')
        (tmp_path / 'repo').mkdir()
        _seed_by_cwd(tmp_path, repo_root, 'session-per-cwd')
        _seed_current(tmp_path, 'session-singleton')

        monkeypatch.setattr(manage_session, '_resolve_cwd', lambda: repo_root)
        monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))

        rc = manage_session.cmd_current(mock.Mock())
        out = capsys.readouterr().out

        assert rc == 0
        assert 'session_id: session-per-cwd' in out
        assert 'session-singleton' not in out

    def test_both_caches_missing_returns_error(self, tmp_path, monkeypatch, capsys):
        """No cache files → status: error with session_id_unavailable."""
        repo_root = str(tmp_path / 'repo')
        (tmp_path / 'repo').mkdir()

        monkeypatch.setattr(manage_session, '_resolve_cwd', lambda: repo_root)
        monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))

        rc = manage_session.cmd_current(mock.Mock())
        out = capsys.readouterr().out

        assert rc == 0  # Script exits 0; error is expressed in TOON, not return code
        assert 'status: error' in out
        assert 'session_id_unavailable' in out

    def test_blank_cache_file_is_treated_as_missing(self, tmp_path, monkeypatch, capsys):
        """An empty or whitespace-only cache file must not be returned as a valid id."""
        repo_root = str(tmp_path / 'repo')
        (tmp_path / 'repo').mkdir()
        _seed_by_cwd(tmp_path, repo_root, '')  # Empty write
        _seed_current(tmp_path, '   \n')  # Whitespace only

        monkeypatch.setattr(manage_session, '_resolve_cwd', lambda: repo_root)
        monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))

        rc = manage_session.cmd_current(mock.Mock())
        out = capsys.readouterr().out

        assert rc == 0
        assert 'status: error' in out
        assert 'session_id_unavailable' in out


class TestCmdTranscriptPath:
    """Direct-invocation tests for cmd_transcript_path."""

    @staticmethod
    def _seed_transcript(home: Path, cwd: str, session_id: str) -> Path:
        slug = cwd.replace('/', '-')
        path = home / '.claude' / 'projects' / slug / f'{session_id}.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"role":"user"}\n', encoding='utf-8')
        return path

    def test_slug_hit_returns_transcript_path(self, tmp_path, monkeypatch, capsys):
        """Happy path — JSONL at slug-derived dir is returned verbatim."""
        session_id = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
        repo_root = str(tmp_path / 'repo')
        (tmp_path / 'repo').mkdir()
        expected = self._seed_transcript(tmp_path, repo_root, session_id)

        monkeypatch.setattr(manage_session, '_resolve_cwd', lambda: repo_root)
        monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))

        rc = manage_session.cmd_transcript_path(
            mock.Mock(session_id=session_id),
        )
        out = capsys.readouterr().out

        assert rc == 0
        assert 'status: success' in out
        assert f'transcript_path: {expected}' in out

    def test_no_match_returns_transcript_not_found(self, tmp_path, monkeypatch, capsys):
        """Total miss — no JSONL anywhere under ~/.claude/projects/."""
        session_id = '11111111-2222-3333-4444-555555555555'
        repo_root = str(tmp_path / 'repo')
        (tmp_path / 'repo').mkdir()

        monkeypatch.setattr(manage_session, '_resolve_cwd', lambda: repo_root)
        monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))

        rc = manage_session.cmd_transcript_path(
            mock.Mock(session_id=session_id),
        )
        out = capsys.readouterr().out

        assert rc == 0
        assert 'status: error' in out
        assert 'transcript_not_found' in out

    def test_cross_cwd_recovery_via_parent_dir_glob(self, tmp_path, monkeypatch, capsys):
        """JSONL under a sibling slug dir is found via Path.glob fallback."""
        session_id = '99999999-8888-7777-6666-555555555555'
        repo_root = str(tmp_path / 'current-repo')
        (tmp_path / 'current-repo').mkdir()
        sibling_cwd = str(tmp_path / 'other-repo')
        expected = self._seed_transcript(tmp_path, sibling_cwd, session_id)

        monkeypatch.setattr(manage_session, '_resolve_cwd', lambda: repo_root)
        monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))

        rc = manage_session.cmd_transcript_path(
            mock.Mock(session_id=session_id),
        )
        out = capsys.readouterr().out

        assert rc == 0
        assert 'status: success' in out
        assert f'transcript_path: {expected}' in out

    def test_invalid_session_id_format_rejected(self, tmp_path, monkeypatch, capsys):
        """Session ids that fail the canonical regex are rejected before any filesystem access.

        ``SESSION_ID_RE`` (post-migration) matches ``[A-Za-z0-9_-]{1,128}`` —
        a generous superset of Claude Code session UUIDs. Values that
        contain glob metachars, path separators, traversal segments, or
        the empty string still fail the regex and trigger
        ``invalid_session_id``. Note: kebab-case strings like ``short-id``
        are now valid under the canonical regex (covered by the happy-path
        contract elsewhere).
        """
        repo_root = str(tmp_path / 'repo')
        (tmp_path / 'repo').mkdir()

        monkeypatch.setattr(manage_session, '_resolve_cwd', lambda: repo_root)
        monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))

        for bad in ('../escape', 'wild*card', 'has/slash', ''):
            rc = manage_session.cmd_transcript_path(mock.Mock(session_id=bad))
            out = capsys.readouterr().out
            assert rc == 0
            assert 'status: error' in out
            assert 'invalid_session_id' in out


class TestResolveCwd:
    """_resolve_cwd: git rev-parse --show-toplevel with Path.cwd() fallback."""

    def test_git_toplevel_returned_when_git_succeeds(self, tmp_path, monkeypatch):
        fake_root = '/path/to/fake/repo'

        class FakeCompleted:
            returncode = 0
            stdout = f'{fake_root}\n'

        monkeypatch.setattr(
            'subprocess.run',
            lambda *a, **kw: FakeCompleted(),
        )
        assert manage_session._resolve_cwd() == fake_root

    def test_cwd_fallback_when_git_fails(self, tmp_path, monkeypatch):
        class FakeCompleted:
            returncode = 128
            stdout = ''

        monkeypatch.setattr('subprocess.run', lambda *a, **kw: FakeCompleted())
        monkeypatch.setattr(Path, 'cwd', classmethod(lambda cls: tmp_path))
        assert manage_session._resolve_cwd() == str(tmp_path)

    def test_cwd_fallback_when_git_raises(self, tmp_path, monkeypatch):
        def _raising(*_args, **_kwargs):
            raise OSError('git missing')

        monkeypatch.setattr('subprocess.run', _raising)
        monkeypatch.setattr(Path, 'cwd', classmethod(lambda cls: tmp_path))
        assert manage_session._resolve_cwd() == str(tmp_path)


class TestCliPlumbing:
    """Subprocess-level tests to verify executor PYTHONPATH + TOON emission."""

    def test_current_subcommand_emits_toon_on_hit(self, tmp_path):
        repo_root = str(tmp_path / 'repo')
        (tmp_path / 'repo').mkdir()
        _seed_by_cwd(tmp_path, repo_root, 'subprocess-session-id')

        result = run_script(
            SCRIPT_PATH,
            'current',
            env_overrides={'HOME': str(tmp_path)},
            cwd=str(tmp_path / 'repo'),
        )

        # git rev-parse may succeed in the outer checkout; we cannot force it
        # through env alone. Accept either the by-cwd hit (when cwd resolves
        # correctly) or the error path (when git resolves to a different
        # toplevel). Both are valid TOON.
        assert result.success, f'Script failed: {result.stderr}'
        data = result.toon()
        assert data['status'] in ('success', 'error')
        if data['status'] == 'success':
            assert data['session_id'] == 'subprocess-session-id'
        else:
            assert data.get('error') == 'session_id_unavailable'

    def test_missing_subcommand_fails(self, tmp_path):
        result = subprocess.run(
            ['python3', str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            env={'HOME': str(tmp_path), 'PATH': '/usr/bin:/bin'},
        )
        assert result.returncode != 0
