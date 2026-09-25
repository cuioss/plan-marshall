#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests for manage-files discovery and document resolution."""

from pathlib import Path

import pytest
from _manage_files_fixtures import SCRIPT_PATH, _mod, run_script

# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


@pytest.mark.parametrize(
    ('argv', 'expect_success'),
    [
        (('write', '--plan-id', 'test-plan'), False),
        (('--help',), True),
        (('write', '--help'), True),
    ],
    ids=[
        'write-without-required-file-flag-is-rejected',
        'top-level-help-exits-zero',
        'subcommand-help-exits-zero',
    ],
)
def test_cli_argv_exit_status(plan_context, argv, expect_success):
    """Help exits zero at both levels; argparse rejects a command missing a required flag."""
    result = run_script(SCRIPT_PATH, *argv)

    assert result.success is expect_success


# =============================================================================
# Test: Discover (subprocess + TOON output contract)
# =============================================================================


def _make_discover_tree(root: Path) -> None:
    """Build a fixture filesystem under ``root`` for discover tests.

    Layout:
        root/
            a.py
            b.py
            sub/
                c.py
                notes.adoc
                deeper/
                    d.adoc
            other/
                e.txt
    """
    (root / 'a.py').write_text('a')
    (root / 'b.py').write_text('b')
    sub = root / 'sub'
    sub.mkdir()
    (sub / 'c.py').write_text('c')
    (sub / 'notes.adoc').write_text('notes')
    deeper = sub / 'deeper'
    deeper.mkdir()
    (deeper / 'd.adoc').write_text('deeper')
    other = root / 'other'
    other.mkdir()
    (other / 'e.txt').write_text('e')


def test_discover_single_pattern_returns_sorted_absolute_paths(tmp_path):
    """Single-pattern match returns sorted absolute paths."""
    _make_discover_tree(tmp_path)

    result = run_script(SCRIPT_PATH, 'discover', '--root', str(tmp_path), '--glob', '*.py')

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    assert data['root'] == str(tmp_path.resolve())
    paths = data['paths']
    # Top-level *.py must match exactly a.py and b.py — sorted, absolute.
    expected = sorted(str(p.resolve()) for p in [tmp_path / 'a.py', tmp_path / 'b.py'])
    assert paths == expected
    for path in paths:
        assert Path(path).is_absolute()


def test_discover_multiple_glob_patterns_deduplicated(tmp_path):
    """Multiple --glob patterns deduplicate overlapping matches."""
    _make_discover_tree(tmp_path)

    # `*.py` and `a*` both match a.py — must appear only once.
    result = run_script(
        SCRIPT_PATH,
        'discover',
        '--root',
        str(tmp_path),
        '--glob',
        '*.py',
        '--glob',
        'a*',
    )

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    paths = data['paths']
    a_path = str((tmp_path / 'a.py').resolve())
    # Deduplication: a.py appears exactly once across the merged result.
    assert paths.count(a_path) == 1
    # Ensure b.py from the *.py pattern is present.
    assert str((tmp_path / 'b.py').resolve()) in paths


def test_discover_include_files_filters_out_directories(tmp_path):
    """--include-files filters out directories from matches."""
    _make_discover_tree(tmp_path)

    # `*` at the root matches both files (a.py, b.py) and dirs (sub, other).
    # With --include-files, only files should remain.
    result = run_script(
        SCRIPT_PATH,
        'discover',
        '--root',
        str(tmp_path),
        '--glob',
        '*',
        '--include-files',
    )

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    paths = data['paths']
    # All returned paths must be files; no directories.
    for path in paths:
        p = Path(path)
        assert p.is_file()
        assert not p.is_dir()
    # Directory entries must not be present.
    assert str((tmp_path / 'sub').resolve()) not in paths
    assert str((tmp_path / 'other').resolve()) not in paths


def test_discover_include_dirs_keeps_only_directories(tmp_path):
    """--include-dirs keeps only directories in matches."""
    _make_discover_tree(tmp_path)

    result = run_script(
        SCRIPT_PATH,
        'discover',
        '--root',
        str(tmp_path),
        '--glob',
        '*',
        '--include-dirs',
    )

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    paths = data['paths']
    # Every result must be a directory.
    for path in paths:
        assert Path(path).is_dir()
    # Both top-level dirs present, no files.
    assert str((tmp_path / 'sub').resolve()) in paths
    assert str((tmp_path / 'other').resolve()) in paths
    assert str((tmp_path / 'a.py').resolve()) not in paths


def test_discover_invalid_root_returns_error(tmp_path):
    """Invalid root returns status: error / error: invalid_root."""
    missing = tmp_path / 'does-not-exist'

    result = run_script(SCRIPT_PATH, 'discover', '--root', str(missing), '--glob', '*.py')

    # Script exits 0 (returns dict via output_toon) — error surfaces in TOON.
    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'error'
    assert data['error'] == 'invalid_root'


def test_discover_zero_patterns_returns_error(tmp_path):
    """Zero --glob patterns returns status: error / error: no_patterns."""
    _make_discover_tree(tmp_path)

    result = run_script(SCRIPT_PATH, 'discover', '--root', str(tmp_path))

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'error'
    assert data['error'] == 'no_patterns'


def test_discover_zero_matches_returns_success_with_empty_paths(tmp_path):
    """Zero matches returns success with empty paths array."""
    _make_discover_tree(tmp_path)

    result = run_script(
        SCRIPT_PATH,
        'discover',
        '--root',
        str(tmp_path),
        '--glob',
        '*.nonexistent',
    )

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    assert data['paths'] == []


def test_discover_recursive_glob_across_subdirs(tmp_path):
    """Recursive **/*.adoc glob discovers .adoc files across nested dirs."""
    _make_discover_tree(tmp_path)

    result = run_script(
        SCRIPT_PATH,
        'discover',
        '--root',
        str(tmp_path),
        '--glob',
        '**/*.adoc',
    )

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    paths = data['paths']
    expected = sorted(
        str(p.resolve())
        for p in [
            tmp_path / 'sub' / 'notes.adoc',
            tmp_path / 'sub' / 'deeper' / 'd.adoc',
        ]
    )
    assert paths == expected


# =============================================================================
# _resolve_document_path — helper-based executor resolution
# =============================================================================
#
# _resolve_document_path delegates executor location to file_ops.get_executor_path()
# (worktree-safe resolution via git-common-dir). When the resolved executor exists
# on disk it is invoked verbatim; on RuntimeError or a missing file the canonical
# PATH-relative '.plan/execute-script.py' is used as a defensive fallback.


class _RecordingProc:
    """Stand-in for subprocess.CompletedProcess capturing the argv."""

    def __init__(self, argv, returncode=0, stdout='', stderr=''):
        self.args = argv
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestResolveDocumentPathExecutor:
    """Verify _resolve_document_path uses the helper-resolved executor path."""

    def _patch_subprocess(self, monkeypatch, returncode=0, stdout='path: /abs/request.md\n'):
        captured = {}

        def fake_run(cmd, *args, **kwargs):
            captured['cmd'] = cmd
            return _RecordingProc(cmd, returncode=returncode, stdout=stdout)

        monkeypatch.setattr(_mod.subprocess, 'run', fake_run)
        return captured

    def test_uses_resolved_executor_when_it_exists(self, tmp_path, monkeypatch):
        """When get_executor_path resolves an existing file, it is used in the argv."""
        executor = tmp_path / 'execute-script.py'
        executor.write_text('# executor\n')
        monkeypatch.setattr(_mod, 'get_executor_path', lambda: executor)
        captured = self._patch_subprocess(monkeypatch)

        path, detail = _mod._resolve_document_path('test-plan', 'request')

        assert detail is None
        assert path == Path('/abs/request.md')
        assert str(executor) in captured['cmd']

    def test_falls_back_to_canonical_path_when_executor_missing(self, tmp_path, monkeypatch):
        """When the resolved executor does not exist, the canonical relative path is used."""
        missing = tmp_path / 'execute-script.py'  # never created
        monkeypatch.setattr(_mod, 'get_executor_path', lambda: missing)
        captured = self._patch_subprocess(monkeypatch)

        path, detail = _mod._resolve_document_path('test-plan', 'request')

        assert detail is None
        assert path == Path('/abs/request.md')
        assert '.plan/execute-script.py' in captured['cmd']
        assert str(missing) not in captured['cmd']

    def test_falls_back_when_helper_raises_runtime_error(self, monkeypatch):
        """RuntimeError from get_executor_path → canonical relative path fallback."""

        def _raise():
            raise RuntimeError('no git repository')

        monkeypatch.setattr(_mod, 'get_executor_path', _raise)
        captured = self._patch_subprocess(monkeypatch)

        path, detail = _mod._resolve_document_path('test-plan', 'request')

        assert detail is None
        assert path == Path('/abs/request.md')
        assert '.plan/execute-script.py' in captured['cmd']

    def test_resolver_nonzero_exit_returns_detail(self, tmp_path, monkeypatch):
        """A non-zero resolver exit returns (None, detail)."""
        executor = tmp_path / 'execute-script.py'
        executor.write_text('# executor\n')
        monkeypatch.setattr(_mod, 'get_executor_path', lambda: executor)
        self._patch_subprocess(monkeypatch, returncode=1, stdout='')

        path, detail = _mod._resolve_document_path('test-plan', 'request')

        assert path is None
        assert detail is not None
