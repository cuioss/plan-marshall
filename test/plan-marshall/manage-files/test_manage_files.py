#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-files.py script."""

import importlib.util
import json
import os
import shutil
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path, get_test_fixture_dir, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-files', 'manage-files.py')

# Tier 2 direct imports - load hyphenated module via importlib
_MANAGE_FILES_SCRIPT = str(
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-files'
    / 'scripts'
    / 'manage-files.py'
)
_spec = importlib.util.spec_from_file_location('manage_files', _MANAGE_FILES_SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_read = _mod.cmd_read
cmd_write = _mod.cmd_write
cmd_remove = _mod.cmd_remove
cmd_list = _mod.cmd_list
cmd_exists = _mod.cmd_exists
cmd_mkdir = _mod.cmd_mkdir
cmd_create_or_reference = _mod.cmd_create_or_reference


# =============================================================================
# Helper: EmptyPlanContext (no pre-created plan directory)
# =============================================================================


class EmptyPlanContext:
    """Context manager for test WITHOUT pre-created plan directory."""

    __test__ = False  # Not a test class - prevent pytest collection warning

    def __init__(self):
        self.fixture_dir = None
        self._original_plan_base_dir = None
        self._original_plan_dir_name = None
        self._is_standalone = False

    def __enter__(self):
        self.fixture_dir = get_test_fixture_dir()
        self._is_standalone = 'TEST_FIXTURE_DIR' not in os.environ

        self._original_plan_base_dir = os.environ.get('PLAN_BASE_DIR')
        self._original_plan_dir_name = os.environ.get('PLAN_DIR_NAME')
        os.environ['PLAN_BASE_DIR'] = str(self.fixture_dir)
        os.environ['PLAN_DIR_NAME'] = '.plan'
        # Create plans directory but NOT the plan subdirectory
        (self.fixture_dir / 'plans').mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._original_plan_base_dir is None:
            os.environ.pop('PLAN_BASE_DIR', None)
        else:
            os.environ['PLAN_BASE_DIR'] = self._original_plan_base_dir

        if self._original_plan_dir_name is None:
            os.environ.pop('PLAN_DIR_NAME', None)
        else:
            os.environ['PLAN_DIR_NAME'] = self._original_plan_dir_name

        # Only cleanup if running standalone
        if self._is_standalone and self.fixture_dir and self.fixture_dir.exists():
            shutil.rmtree(self.fixture_dir, ignore_errors=True)

    @property
    def temp_dir(self):
        """Return the fixture directory."""
        return self.fixture_dir

    def plan_dir(self, plan_id):
        return self.fixture_dir / 'plans' / plan_id


# =============================================================================
# Test: Write and Read
# =============================================================================


def test_write_file(plan_context):
    """Test writing a file."""
    result = cmd_write(Namespace(plan_id=plan_context.plan_id, file='task.md', content='# Task\nDo something', stdin=False))
    assert result['status'] == 'success'
    assert result['action'] == 'created'
    assert result['file'] == 'task.md'
    # Verify file was created
    assert (plan_context.plan_dir / 'task.md').exists()
    assert (plan_context.plan_dir / 'task.md').read_text().rstrip('\n') == '# Task\nDo something'


def test_read_file(plan_context, capsys):
    """Test reading a file (cmd_read prints content and returns None)."""
    (plan_context.plan_dir / 'test.md').write_text('Test content')

    result = cmd_read(Namespace(plan_id=plan_context.plan_id, file='test.md'))
    assert result is None  # cmd_read prints directly, returns None
    captured = capsys.readouterr()
    assert 'Test content' in captured.out


def test_read_nonexistent_file(plan_context):
    """Test reading a file that doesn't exist."""
    result = cmd_read(Namespace(plan_id='file-noexist', file='missing.md'))
    assert result['status'] == 'error'
    assert result['error'] == 'file_not_found'


# =============================================================================
# Test: List and Exists
# =============================================================================


def test_list_empty(plan_context):
    """Test listing files in empty plan."""
    result = cmd_list(Namespace(plan_id=plan_context.plan_id, dir=None))
    assert result['status'] == 'success'
    assert result['files'] == []


def test_list_with_files(plan_context):
    """Test listing files."""
    # Create some files
    (plan_context.plan_dir / 'references.json').write_text('{"branch": "main"}')
    (plan_context.plan_dir / 'task.md').write_text('Task')

    result = cmd_list(Namespace(plan_id=plan_context.plan_id, dir=None))
    assert result['status'] == 'success'
    assert 'task.md' in result['files']
    assert 'references.json' in result['files']


def test_exists_present(plan_context):
    """Test checking if file exists (present)."""
    (plan_context.plan_dir / 'test.md').write_text('Test')

    result = cmd_exists(Namespace(plan_id=plan_context.plan_id, file='test.md'))
    assert result['status'] == 'success'
    assert result['exists'] is True
    assert result['plan_id'] == plan_context.plan_id
    assert result['file'] == 'test.md'
    assert 'path' in result


def test_exists_absent(plan_context):
    """Test checking if file exists (absent)."""
    result = cmd_exists(Namespace(plan_id='file-absent', file='missing.md'))
    assert result['status'] == 'success'
    assert result['exists'] is False
    assert result['plan_id'] == 'file-absent'
    assert result['file'] == 'missing.md'


def test_exists_invalid_plan_id(plan_context):
    """Test exists with invalid plan ID exits via sys.exit(1)."""
    with pytest.raises(SystemExit) as exc_info:
        cmd_exists(Namespace(plan_id='Invalid_Plan', file='test.md'))
    assert exc_info.value.code == 0


def test_exists_invalid_file_path(plan_context):
    """Test exists with invalid file path returns error dict."""
    result = cmd_exists(Namespace(plan_id='file-exists', file='../escape.md'))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_path'


# =============================================================================
# Test: Remove and Mkdir
# =============================================================================


def test_remove_file(plan_context):
    """Test removing a file."""
    (plan_context.plan_dir / 'delete-me.md').write_text('Goodbye')

    result = cmd_remove(Namespace(plan_id=plan_context.plan_id, file='delete-me.md'))
    assert result['status'] == 'success'
    assert result['action'] == 'removed'
    assert not (plan_context.plan_dir / 'delete-me.md').exists()


def test_remove_nonexistent_file(plan_context):
    """Test removing a file that doesn't exist."""
    result = cmd_remove(Namespace(plan_id='file-remove-missing', file='ghost.md'))
    assert result['status'] == 'error'
    assert result['error'] == 'file_not_found'


def test_mkdir(plan_context):
    """Test creating a directory."""
    result = cmd_mkdir(Namespace(plan_id=plan_context.plan_id, dir='requirements'))
    assert result['status'] == 'success'
    assert result['action'] == 'created'
    assert (plan_context.plan_dir / 'requirements').is_dir()


def test_mkdir_already_exists(plan_context):
    """Test creating a directory that already exists."""
    (plan_context.plan_dir / 'existing').mkdir()
    result = cmd_mkdir(Namespace(plan_id=plan_context.plan_id, dir='existing'))
    assert result['status'] == 'success'
    assert result['action'] == 'exists'


# =============================================================================
# Test: Create-or-Reference
# =============================================================================


def test_create_or_reference_new_plan():
    """Test create-or-reference creates new plan directory."""
    with EmptyPlanContext() as ctx:
        result = cmd_create_or_reference(Namespace(plan_id='new-plan'))
        assert result['status'] == 'success'
        assert result['action'] == 'created'
        assert result['plan_id'] == 'new-plan'
        # Verify directory was created
        assert ctx.plan_dir('new-plan').exists()


def test_create_or_reference_existing_plan(plan_context):
    """Test create-or-reference returns exists for existing plan."""
    result = cmd_create_or_reference(Namespace(plan_id=plan_context.plan_id))
    assert result['status'] == 'success'
    assert result['action'] == 'exists'
    assert result['plan_id'] == plan_context.plan_id


def test_create_or_reference_existing_with_status(plan_context):
    """Test create-or-reference returns phase info when status.json exists."""
    # Create status.json with phase info (domain is in references.json, not status.json)
    status_content = json.dumps({'title': 'Test Plan', 'current_phase': 'outline'})
    (plan_context.plan_dir / 'status.json').write_text(status_content)

    result = cmd_create_or_reference(Namespace(plan_id=plan_context.plan_id))
    assert result['status'] == 'success'
    assert result['action'] == 'exists'
    assert result['current_phase'] == 'outline'
    # Domain should NOT be in output (stored in references.json, not status.toon)
    assert 'domain' not in result


def test_create_or_reference_invalid_plan_id():
    """Test create-or-reference rejects invalid plan IDs (sys.exit(1))."""
    with EmptyPlanContext():
        with pytest.raises(SystemExit) as exc_info:
            cmd_create_or_reference(Namespace(plan_id='Invalid_Plan'))
        assert exc_info.value.code == 0


# =============================================================================
# Test: Invalid Plan IDs (direct import)
# =============================================================================


def test_invalid_plan_id_uppercase(plan_context):
    """Test that uppercase plan IDs are rejected."""
    with pytest.raises(SystemExit) as exc_info:
        cmd_list(Namespace(plan_id='My-Plan', dir=None))
    assert exc_info.value.code == 0


def test_invalid_plan_id_underscore(plan_context):
    """Test that underscore in plan IDs are rejected."""
    with pytest.raises(SystemExit) as exc_info:
        cmd_list(Namespace(plan_id='my_plan', dir=None))
    assert exc_info.value.code == 0


# =============================================================================
# Test: Write edge cases
# =============================================================================


def test_write_missing_content(plan_context):
    """Test write fails when neither --content nor --stdin provided."""
    result = cmd_write(Namespace(plan_id='file-write-no-content', file='test.md', content=None, stdin=False))
    assert result['status'] == 'error'
    assert result['error'] == 'missing_content'


def test_write_invalid_path(plan_context):
    """Test write rejects path traversal."""
    result = cmd_write(Namespace(plan_id='file-write-escape', file='../escape.md', content='bad', stdin=False))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_path'


# =============================================================================
# Test: Write with --content-file
# =============================================================================


def test_write_with_content_file_path_succeeds(plan_context, tmp_path):
    """Test write reads payload from --content-file and writes verbatim."""
    payload = '# Heading\n\nMultiline\npayload\n'
    payload_path = tmp_path / 'payload.md'
    payload_path.write_text(payload, encoding='utf-8')

    result = cmd_write(
        Namespace(
            plan_id=plan_context.plan_id,
            file='task.md',
            content=None,
            content_file=str(payload_path),
            stdin=False,
        )
    )
    assert result['status'] == 'success'
    assert result['action'] == 'created'
    assert result['file'] == 'task.md'
    # Verify file contents match the staged payload verbatim.
    target = plan_context.plan_dir / 'task.md'
    assert target.exists()
    assert target.read_text(encoding='utf-8') == payload


def test_write_with_content_file_missing_returns_error(plan_context, tmp_path):
    """Test write returns content_file_not_found when --content-file path is absent."""
    missing_path = tmp_path / 'does-not-exist.md'

    result = cmd_write(
        Namespace(
            plan_id='file-write-cf-missing',
            file='task.md',
            content=None,
            content_file=str(missing_path),
            stdin=False,
        )
    )
    assert result['status'] == 'error'
    assert result['error'] == 'content_file_not_found'
    # The script resolves the path before reporting; assert the resolved
    # form appears in the message so the user can locate the missing file.
    assert str(missing_path.resolve()) in result['message']


def test_write_content_and_content_file_mutually_exclusive(plan_context, tmp_path):
    """Test write rejects --content and --content-file used together."""
    payload_path = tmp_path / 'payload.md'
    payload_path.write_text('payload', encoding='utf-8')

    result = cmd_write(
        Namespace(
            plan_id='file-write-cf-mutex',
            file='task.md',
            content='inline content',
            content_file=str(payload_path),
            stdin=False,
        )
    )
    assert result['status'] == 'error'
    assert result['error'] == 'mutually_exclusive'


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_missing_required_args(plan_context):
    """Test that missing required args produces exit code 2 (argparse error)."""
    result = run_script(SCRIPT_PATH, 'write', '--plan-id', 'test-plan')
    # argparse exits with code 2 for missing required args (--file)
    assert not result.success


def test_cli_help_flag(plan_context):
    """Test that --help produces exit code 0."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.success


def test_cli_subcommand_help(plan_context):
    """Test that subcommand --help produces exit code 0."""
    result = run_script(SCRIPT_PATH, 'write', '--help')
    assert result.success


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
