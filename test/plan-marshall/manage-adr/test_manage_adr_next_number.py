#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-adr.py script."""


from argparse import Namespace
from pathlib import Path

import pytest
from _manage_adr_fixtures import (
    _build_metadata_block,
    cmd_create,
    cmd_delete,
    cmd_list,
    cmd_next_number,
    cmd_read,
    cmd_update,
    parse_metadata_block,
)


@pytest.fixture
def adr_dir(tmp_path, monkeypatch):
    """Provide a clean doc/adr directory and chdir into the temp project root."""
    directory = tmp_path / 'doc' / 'adr'
    directory.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return directory


# =========================================================================
# Tier 2: Direct import tests
# =========================================================================


def test_next_number_empty_dir(adr_dir):
    """Test next-number returns 1 for empty directory."""
    result = cmd_next_number(Namespace(command='next-number'))

    assert result['status'] == 'success'
    assert result['next_number'] == 1


def test_create_adr(adr_dir):
    """Test creating a new ADR."""
    result = cmd_create(Namespace(command='create', title='Use PostgreSQL', status='Proposed'))

    assert result['status'] == 'success'
    assert result['number'] == 1
    # Empty corpus → default width 4 → 4-digit prefix.
    assert '0001-Use_PostgreSQL.adoc' in result['path']

    created_file = adr_dir / '0001-Use_PostgreSQL.adoc'
    assert created_file.exists()

    content = created_file.read_text()
    assert 'ADR-0001' in content
    assert 'Use PostgreSQL' in content
    assert 'Proposed' in content


def test_create_adr_with_status(adr_dir):
    """Test creating ADR with custom status."""
    result = cmd_create(Namespace(command='create', title='Another Decision', status='Accepted'))

    assert result['status'] == 'success'

    # Empty corpus → default width 4.
    created_file = adr_dir / f'{result["number"]:04d}-Another_Decision.adoc'
    content = created_file.read_text()
    assert 'Accepted' in content


def test_create_multiple_adrs(adr_dir):
    """Test creating multiple ADRs increments numbers."""
    cmd_create(Namespace(command='create', title='First ADR', status='Proposed'))
    cmd_create(Namespace(command='create', title='Second ADR', status='Proposed'))

    result = cmd_create(Namespace(command='create', title='Third ADR', status='Proposed'))

    assert result['number'] == 3


def test_list_adrs(adr_dir):
    """Test listing ADRs."""
    cmd_create(Namespace(command='create', title='ADR One', status='Proposed'))
    cmd_create(Namespace(command='create', title='ADR Two', status='Proposed'))

    result = cmd_list(Namespace(command='list', status=None))

    assert result['status'] == 'success'
    assert result['count'] == 2


def test_list_adrs_filter_status(adr_dir):
    """Test listing ADRs filtered by status."""
    cmd_create(Namespace(command='create', title='Proposed One', status='Proposed'))
    cmd_create(Namespace(command='create', title='Accepted One', status='Accepted'))

    result = cmd_list(Namespace(command='list', status='Proposed'))

    assert result['status'] == 'success'
    assert result['count'] == 1


def test_read_adr(adr_dir):
    """Test reading ADR by number."""
    cmd_create(Namespace(command='create', title='Test Read', status='Proposed'))

    result = cmd_read(Namespace(command='read', number=1))

    assert result['status'] == 'success'
    assert 'Test Read' in result['content']


def test_read_adr_not_found(adr_dir):
    """Test reading non-existent ADR."""
    result = cmd_read(Namespace(command='read', number=999))

    assert result['status'] == 'error'
    assert 'not found' in result['message'].lower()


def test_update_adr_status(adr_dir):
    """Test updating ADR status."""
    cmd_create(Namespace(command='create', title='Update Test', status='Proposed'))

    result = cmd_update(Namespace(command='update', number=1, status='Deprecated'))

    assert result['status'] == 'success'

    read_result = cmd_read(Namespace(command='read', number=1))
    assert 'Deprecated' in read_result['content']


def test_delete_requires_force(adr_dir):
    """Test delete requires --force flag."""
    cmd_create(Namespace(command='create', title='Delete Test', status='Proposed'))

    result = cmd_delete(Namespace(command='delete', number=1, force=False))

    assert result['status'] == 'error'
    assert '--force' in result['message']


def test_delete_with_force(adr_dir):
    """Test delete with --force flag."""
    cmd_create(Namespace(command='create', title='Delete Me', status='Proposed'))

    result = cmd_delete(Namespace(command='delete', number=1, force=True))

    assert result['deleted']

    # Created on an empty corpus → 4-digit prefix; confirm it is gone.
    files = list(adr_dir.glob('0001-*.adoc'))
    assert len(files) == 0


def test_filename_sanitization(adr_dir):
    """Test filename sanitization for special characters."""
    result = cmd_create(Namespace(command='create', title='Use API/REST for User Service!', status='Proposed'))

    assert result['status'] == 'success'
    filename = Path(result['path']).name
    assert '/' not in filename
    assert '!' not in filename


# =========================================================================
# Tier 2: Progressive-disclosure metadata block parsing
# =========================================================================


def test_parse_metadata_block_all_fields_present(adr_dir):
    """All four metadata fields are extracted; list fields are comma-split."""
    content = (
        '= ADR-001: Test\n\n'
        + _build_metadata_block(
            summary='Use a fenced metadata block',
            tags='persistence, scanning',
            affects='plan-marshall, pm-documents',
            supersedes='ADR-000',
        )
        + '\n== Status\n\nProposed\n'
    )

    metadata = parse_metadata_block(content)

    assert metadata['summary'] == 'Use a fenced metadata block'
    assert metadata['tags'] == ['persistence', 'scanning']
    assert metadata['affects'] == ['plan-marshall', 'pm-documents']
    assert metadata['supersedes'] == ['ADR-000']


def test_parse_metadata_block_fields_absent(adr_dir):
    """A block whose fields are blank yields empty scalar/list defaults."""
    content = (
        '= ADR-002: Empty\n\n'
        + _build_metadata_block()
        + '\n== Status\n\nProposed\n'
    )

    metadata = parse_metadata_block(content)

    assert metadata['summary'] == ''
    assert metadata['tags'] == []
    assert metadata['affects'] == []
    assert metadata['supersedes'] == []
