#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process ``main()`` dispatcher + uncovered-branch tests for ``manage-files.py``.

The sibling ``test_manage_files.py`` exercises the ``cmd_*`` handlers directly
and drives ``discover`` / CLI plumbing through subprocess (``run_script``).
Subprocess runs do not count for coverage, so the ``main()`` argparse builder
and the entire ``cmd_discover`` body were uncovered, along with a handful of
``cmd_list`` / ``cmd_mkdir`` / ``cmd_write`` / ``cmd_create_or_reference``
branches that no direct test reaches.

These tests run in-process so coverage records them, and each asserts a real
behaviour (routing, filtered paths, error discriminator, exit code, content),
never coverage-only padding.
"""

from __future__ import annotations

import io
import sys
from argparse import Namespace

import pytest
from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import load_script_module  # type: ignore[import-not-found]

# Distinct sys.modules name so this load never clobbers the 'manage_files'
# module the sibling test files register.
_mod = load_script_module('plan-marshall', 'manage-files', 'manage-files.py', 'manage_files_maincli')


def _run_main(monkeypatch, capsys, argv):
    """Drive ``main()`` with a patched argv and return (exit_code, stdout)."""
    monkeypatch.setattr(sys, 'argv', ['manage-files', *argv])
    with pytest.raises(SystemExit) as exc:
        _mod.main()
    code = exc.value.code if exc.value.code is not None else 0
    captured = capsys.readouterr()
    return code, captured.out


# =============================================================================
# main() dispatch — one path per verb
# =============================================================================


def test_main_write_then_read_roundtrip(plan_context, monkeypatch, capsys):
    """``write`` then ``read`` route correctly; read prints raw content (no TOON)."""
    pid = plan_context.plan_id
    write_code, write_out = _run_main(
        monkeypatch, capsys, ['write', '--plan-id', pid, '--file', 'note.md', '--content', 'hello world']
    )
    assert write_code == 0
    assert parse_toon(write_out)['status'] == 'success'

    read_code, read_out = _run_main(monkeypatch, capsys, ['read', '--plan-id', pid, '--file', 'note.md'])
    assert read_code == 0
    # cmd_read prints the file body directly and returns None — no TOON emitted.
    assert 'hello world' in read_out


def test_main_list_reports_written_file(plan_context, monkeypatch, capsys):
    """``list`` routes to cmd_list and reports the file in the plan dir."""
    pid = plan_context.plan_id
    (plan_context.plan_dir / 'present.md').write_text('x')
    code, out = _run_main(monkeypatch, capsys, ['list', '--plan-id', pid])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert 'present.md' in data['files']


def test_main_exists_routes_and_reports(plan_context, monkeypatch, capsys):
    """``exists`` routes to cmd_exists and reports presence."""
    pid = plan_context.plan_id
    (plan_context.plan_dir / 'here.md').write_text('x')
    code, out = _run_main(monkeypatch, capsys, ['exists', '--plan-id', pid, '--file', 'here.md'])
    assert code == 0
    assert parse_toon(out)['exists'] is True


def test_main_mkdir_routes(plan_context, monkeypatch, capsys):
    """``mkdir`` routes to cmd_mkdir and creates the subdirectory."""
    pid = plan_context.plan_id
    code, out = _run_main(monkeypatch, capsys, ['mkdir', '--plan-id', pid, '--dir', 'sub'])
    assert code == 0
    data = parse_toon(out)
    assert data['action'] == 'created'
    assert (plan_context.plan_dir / 'sub').is_dir()


def test_main_remove_routes(plan_context, monkeypatch, capsys):
    """``remove`` routes to cmd_remove and deletes the file."""
    pid = plan_context.plan_id
    (plan_context.plan_dir / 'gone.md').write_text('x')
    code, out = _run_main(monkeypatch, capsys, ['remove', '--plan-id', pid, '--file', 'gone.md'])
    assert code == 0
    assert parse_toon(out)['action'] == 'removed'
    assert not (plan_context.plan_dir / 'gone.md').exists()


def test_main_create_or_reference_existing(plan_context, monkeypatch, capsys):
    """``create-or-reference`` routes to cmd_create_or_reference."""
    pid = plan_context.plan_id
    code, out = _run_main(monkeypatch, capsys, ['create-or-reference', '--plan-id', pid])
    assert code == 0
    assert parse_toon(out)['action'] == 'exists'


def test_main_discover_routes(plan_context, monkeypatch, capsys, tmp_path):
    """``discover`` routes to cmd_discover and returns matching paths."""
    (tmp_path / 'a.py').write_text('a')
    code, out = _run_main(monkeypatch, capsys, ['discover', '--root', str(tmp_path), '--glob', '*.py'])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert str((tmp_path / 'a.py').resolve()) in data['paths']


def test_main_missing_subcommand_exits_2(plan_context, monkeypatch, capsys):
    """No subcommand → argparse required-subparser error exits 2."""
    code, _ = _run_main(monkeypatch, capsys, [])
    assert code == 2


def test_main_write_missing_required_file_exits_2(plan_context, monkeypatch, capsys):
    """``write`` without --file → argparse missing-required error exits 2."""
    code, _ = _run_main(monkeypatch, capsys, ['write', '--plan-id', plan_context.plan_id, '--content', 'x'])
    assert code == 2


# =============================================================================
# cmd_discover — branch coverage (in-process; subprocess copies don't count)
# =============================================================================


def _discover_ns(root, glob, include_files=False, include_dirs=False):
    return Namespace(root=str(root), glob=list(glob), include_files=include_files, include_dirs=include_dirs)


def test_discover_default_includes_files_only(tmp_path):
    """With neither flag, discover returns files and omits directories."""
    (tmp_path / 'f.py').write_text('f')
    (tmp_path / 'd').mkdir()
    result = _mod.cmd_discover(_discover_ns(tmp_path, ['*']))
    assert result['status'] == 'success'
    paths = result['paths']
    assert str((tmp_path / 'f.py').resolve()) in paths
    assert str((tmp_path / 'd').resolve()) not in paths


def test_discover_include_dirs_returns_directories(tmp_path):
    """``include_dirs`` returns directories and drops files."""
    (tmp_path / 'f.py').write_text('f')
    (tmp_path / 'd').mkdir()
    result = _mod.cmd_discover(_discover_ns(tmp_path, ['*'], include_dirs=True))
    paths = result['paths']
    assert str((tmp_path / 'd').resolve()) in paths
    assert str((tmp_path / 'f.py').resolve()) not in paths


def test_discover_dedups_overlapping_patterns(tmp_path):
    """Overlapping patterns yield each match exactly once."""
    (tmp_path / 'a.py').write_text('a')
    result = _mod.cmd_discover(_discover_ns(tmp_path, ['*.py', 'a*']))
    a_path = str((tmp_path / 'a.py').resolve())
    assert result['paths'].count(a_path) == 1


def test_discover_invalid_root_errors(tmp_path):
    """A root that does not exist returns the invalid_root discriminator."""
    result = _mod.cmd_discover(_discover_ns(tmp_path / 'missing', ['*.py']))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_root'


def test_discover_no_patterns_errors(tmp_path):
    """Zero patterns returns the no_patterns discriminator."""
    result = _mod.cmd_discover(_discover_ns(tmp_path, []))
    assert result['status'] == 'error'
    assert result['error'] == 'no_patterns'


# =============================================================================
# cmd_list — subdirectory + error branches
# =============================================================================


def test_list_subdir_marks_nested_directories(plan_context):
    """Listing a subdir marks nested directories with a trailing slash."""
    sub = plan_context.plan_dir / 'area'
    sub.mkdir()
    (sub / 'file.md').write_text('x')
    (sub / 'nested').mkdir()

    result = _mod.cmd_list(Namespace(plan_id=plan_context.plan_id, dir='area'))
    assert result['status'] == 'success'
    assert 'file.md' in result['files']
    assert 'nested/' in result['files']


def test_list_invalid_dir_path(plan_context):
    """A traversal dir path returns the invalid_path discriminator."""
    result = _mod.cmd_list(Namespace(plan_id=plan_context.plan_id, dir='../escape'))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_path'


def test_list_dir_not_found(plan_context):
    """A non-existent subdir returns the dir_not_found discriminator."""
    result = _mod.cmd_list(Namespace(plan_id=plan_context.plan_id, dir='absent'))
    assert result['status'] == 'error'
    assert result['error'] == 'dir_not_found'


# =============================================================================
# cmd_mkdir — invalid path branch
# =============================================================================


def test_mkdir_invalid_path(plan_context):
    """A traversal dir path returns the invalid_path discriminator."""
    result = _mod.cmd_mkdir(Namespace(plan_id=plan_context.plan_id, dir='../escape'))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_path'


# =============================================================================
# cmd_create_or_reference — unparseable status.json branch
# =============================================================================


def test_create_or_reference_malformed_status_json_sets_has_status(plan_context):
    """A corrupt status.json falls into the has_status branch (no current_phase)."""
    (plan_context.plan_dir / 'status.json').write_text('{ not valid json')

    result = _mod.cmd_create_or_reference(Namespace(plan_id=plan_context.plan_id))
    assert result['status'] == 'success'
    assert result['action'] == 'exists'
    assert result['has_status'] is True
    assert 'current_phase' not in result


# =============================================================================
# cmd_write — stdin source branch
# =============================================================================


def test_write_reads_content_from_stdin(plan_context, monkeypatch):
    """``--stdin`` reads the payload from sys.stdin and writes it verbatim."""
    monkeypatch.setattr(_mod.sys, 'stdin', io.StringIO('from stdin\n'))
    result = _mod.cmd_write(
        Namespace(plan_id=plan_context.plan_id, file='in.md', content=None, content_file=None, stdin=True)
    )
    assert result['status'] == 'success'
    assert (plan_context.plan_dir / 'in.md').read_text() == 'from stdin\n'


def test_write_empty_stdin_returns_empty_content_error(plan_context, monkeypatch):
    """Empty stdin content is rejected with the empty_content discriminator."""
    monkeypatch.setattr(_mod.sys, 'stdin', io.StringIO(''))
    result = _mod.cmd_write(
        Namespace(plan_id=plan_context.plan_id, file='in.md', content=None, content_file=None, stdin=True)
    )
    assert result['status'] == 'error'
    assert result['error'] == 'empty_content'
