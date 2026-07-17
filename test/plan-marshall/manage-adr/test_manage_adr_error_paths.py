#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Error-path and parser-edge tests for manage-adr.py.

The sibling ``test_manage_adr.py`` covers the happy paths (create/list/read/
update/delete/scan/metadata). This module fills the uncovered error branches:
missing-directory rejections, not-found rejections, invalid-status rejection on
the direct ``cmd_create`` / ``cmd_update`` paths, the ``status``-omitted update
no-op, the ``get_next_number`` fallback when no file carries the NNN- prefix, and
``parse_adr_file``'s ``Unknown`` fallbacks for a file with neither an
``= ADR-NNN:`` title line nor a numeric filename prefix.

Tier 2 (direct import) — the cmd_* functions are called with constructed
Namespaces so the argparse ``choices=`` guard is bypassed and the in-function
defensive checks are exercised.
"""

from argparse import Namespace

import pytest

from conftest import load_script_module

# Load the hyphenated module under a unique name so it does not collide with the
# ``manage_adr`` instance the sibling test registers in sys.modules.
_mod = load_script_module('plan-marshall', 'manage-adr', 'manage-adr.py', 'manage_adr_errpaths')

cmd_create = _mod.cmd_create
cmd_read = _mod.cmd_read
cmd_update = _mod.cmd_update
cmd_delete = _mod.cmd_delete
cmd_next_number = _mod.cmd_next_number
cmd_list = _mod.cmd_list
parse_adr_file = _mod.parse_adr_file
get_next_number = _mod.get_next_number


@pytest.fixture
def adr_dir(tmp_path, monkeypatch):
    """Chdir into a temp project root that HAS a doc/adr directory."""
    directory = tmp_path / 'doc' / 'adr'
    directory.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return directory


@pytest.fixture
def no_adr_dir(tmp_path, monkeypatch):
    """Chdir into a temp project root that has NO doc/adr directory."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


# =========================================================================
# Missing-directory rejections (ADR_DIR.exists() is False)
# =========================================================================


def test_read_rejects_missing_directory(no_adr_dir):
    """cmd_read returns dir_not_found when doc/adr is absent."""
    result = cmd_read(Namespace(command='read', number=1))

    assert result['status'] == 'error'
    assert result['error'] == 'dir_not_found'
    assert result['operation'] == 'read'


def test_update_rejects_missing_directory(no_adr_dir):
    """cmd_update returns dir_not_found when doc/adr is absent."""
    result = cmd_update(Namespace(command='update', number=1, status='Accepted'))

    assert result['status'] == 'error'
    assert result['error'] == 'dir_not_found'
    assert result['operation'] == 'update'


def test_delete_rejects_missing_directory_after_force(no_adr_dir):
    """cmd_delete with --force returns dir_not_found when doc/adr is absent.

    The ``--force`` gate is checked first; with force supplied the next failure
    is the missing directory rather than the force-required error.
    """
    result = cmd_delete(Namespace(command='delete', number=1, force=True))

    assert result['status'] == 'error'
    assert result['error'] == 'dir_not_found'
    assert result['operation'] == 'delete'


# =========================================================================
# Not-found rejections (directory present, ADR number absent)
# =========================================================================


def test_update_rejects_unknown_number(adr_dir):
    """cmd_update returns not_found when no ADR matches the number."""
    result = cmd_update(Namespace(command='update', number=42, status='Accepted'))

    assert result['status'] == 'error'
    assert result['error'] == 'not_found'
    assert '42' in result['message']


def test_delete_rejects_unknown_number(adr_dir):
    """cmd_delete (with force) returns not_found when no ADR matches the number."""
    result = cmd_delete(Namespace(command='delete', number=7, force=True))

    assert result['status'] == 'error'
    assert result['error'] == 'not_found'
    assert '7' in result['message']


# =========================================================================
# Ambiguous-number rejections (two files share a number at different widths)
# =========================================================================


def _write_ambiguous_pair(adr_dir):
    """Write a 3-digit and a 4-digit prefixed ADR file for the same number 8."""
    narrow = adr_dir / '008-First_Copy.adoc'
    wide = adr_dir / '0008-Second_Copy.adoc'
    narrow.write_text('= ADR-008: First Copy\n\n== Status\n\nProposed\n\n')
    wide.write_text('= ADR-0008: Second Copy\n\n== Status\n\nProposed\n\n')
    return narrow, wide


def test_read_rejects_ambiguous_number(adr_dir):
    """cmd_read returns ambiguous_number when two files share the number."""
    _write_ambiguous_pair(adr_dir)

    result = cmd_read(Namespace(command='read', number=8))

    assert result['status'] == 'error'
    assert result['error'] == 'ambiguous_number'
    assert result['operation'] == 'read'
    # Both ambiguous filenames are surfaced so the caller can disambiguate.
    assert '008-First_Copy.adoc' in result['message']
    assert '0008-Second_Copy.adoc' in result['message']


def test_update_rejects_ambiguous_number_without_modifying_files(adr_dir):
    """cmd_update returns ambiguous_number and modifies neither matching file."""
    narrow, wide = _write_ambiguous_pair(adr_dir)
    narrow_before = narrow.read_text()
    wide_before = wide.read_text()

    result = cmd_update(Namespace(command='update', number=8, status='Accepted'))

    assert result['status'] == 'error'
    assert result['error'] == 'ambiguous_number'
    assert result['operation'] == 'update'
    # Neither file's content changed — the guard fires before any write.
    assert narrow.read_text() == narrow_before
    assert wide.read_text() == wide_before


def test_delete_rejects_ambiguous_number_without_deleting_files(adr_dir):
    """cmd_delete (with force) returns ambiguous_number and deletes neither file."""
    narrow, wide = _write_ambiguous_pair(adr_dir)

    result = cmd_delete(Namespace(command='delete', number=8, force=True))

    assert result['status'] == 'error'
    assert result['error'] == 'ambiguous_number'
    assert result['operation'] == 'delete'
    # Both ambiguous files survive — nothing was unlinked.
    assert narrow.exists()
    assert wide.exists()


# =========================================================================
# Invalid-status rejection on the direct cmd path (argparse choices bypassed)
# =========================================================================


def test_create_rejects_invalid_status(adr_dir):
    """cmd_create returns invalid_status for a status outside VALID_STATUSES.

    No ADR file is written when the status check fails.
    """
    result = cmd_create(Namespace(command='create', title='Bad Status ADR', status='Bogus'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_status'
    assert 'Bogus' in result['message']
    # The status check fires before the file write, so nothing landed on disk.
    assert list(adr_dir.glob('*.adoc')) == []


def test_update_rejects_invalid_status(adr_dir):
    """cmd_update returns invalid_status for a status outside VALID_STATUSES."""
    cmd_create(Namespace(command='create', title='Update Bad', status='Proposed'))

    result = cmd_update(Namespace(command='update', number=1, status='NotAStatus'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_status'
    assert 'NotAStatus' in result['message']


# =========================================================================
# Update with status omitted — the "unchanged" no-op branch
# =========================================================================


def test_update_without_status_is_unchanged_noop(adr_dir):
    """cmd_update with status=None succeeds without rewriting the Status section."""
    cmd_create(Namespace(command='create', title='Unchanged ADR', status='Accepted'))
    original = (adr_dir / '0001-Unchanged_ADR.adoc').read_text()

    result = cmd_update(Namespace(command='update', number=1, status=None))

    assert result['status'] == 'success'
    assert result['adr_status'] == 'unchanged'
    # File content is byte-identical — no status rewrite occurred.
    assert (adr_dir / '0001-Unchanged_ADR.adoc').read_text() == original


# =========================================================================
# get_next_number fallback: files present but none carry the NNN- prefix
# =========================================================================


def test_next_number_ignores_files_without_numeric_prefix(adr_dir):
    """get_next_number returns 1 when existing .adoc files lack the NNN- prefix."""
    (adr_dir / 'README.adoc').write_text('= Not an ADR\n')
    (adr_dir / 'template.adoc').write_text('= Template\n')

    assert get_next_number() == 1

    result = cmd_next_number(Namespace(command='next-number'))
    assert result['status'] == 'success'
    assert result['next_number'] == 1


# =========================================================================
# parse_adr_file fallbacks for a malformed file
# =========================================================================


def test_parse_adr_file_unknown_fallbacks_for_malformed_file(adr_dir):
    """parse_adr_file yields number=0 / Unknown title+status for a malformed file.

    The filename does not match the ``NNN-*.adoc`` pattern and the content
    carries neither an ``= ADR-NNN:`` title line nor a ``== Status`` section, so
    every extractor falls back to its sentinel.
    """
    malformed = adr_dir / 'not-a-real-adr.adoc'
    malformed.write_text('Just some prose with no ADR structure at all.\n')

    adr = parse_adr_file(malformed)

    assert adr['number'] == 0
    assert adr['title'] == 'Unknown'
    assert adr['status'] == 'Unknown'
    # Metadata fields default to empty when no metadata block is present.
    assert adr['tags'] == []
    assert adr['summary'] == ''


def test_list_surfaces_malformed_file_with_unknown_fields(adr_dir):
    """cmd_list parses a malformed .adoc file, surfacing its Unknown fallbacks."""
    (adr_dir / 'orphan.adoc').write_text('no structure here\n')

    result = cmd_list(Namespace(command='list', status=None))

    assert result['status'] == 'success'
    assert result['count'] == 1
    only = result['adrs'][0]
    assert only['number'] == 0
    assert only['title'] == 'Unknown'
    assert only['status'] == 'Unknown'
