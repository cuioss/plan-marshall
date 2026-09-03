#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for manage-adr.py script.

Its sections, in order:

* Direct import tests
* scan subcommand
* Width-agnostic numeric-prefix parsing and numbering
"""


from argparse import Namespace
from pathlib import Path

from _manage_adr_fixtures import (
    METADATA_BLOCK_END,
    METADATA_BLOCK_START,
    _touch_adr,
    adr_dir,
    cmd_create,
    cmd_delete,
    cmd_list,
    cmd_next_number,
    cmd_read,
    cmd_update,
    parse_metadata_block,
)

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


# =========================================================================
# Tier 2: scan subcommand
# =========================================================================

def test_create_emits_metadata_block(adr_dir):
    """create produces an ADR carrying the (empty) metadata block."""
    result = cmd_create(Namespace(command='create', title='Has Block', status='Proposed'))

    assert result['status'] == 'success'

    # Empty corpus → default width 4.
    created_file = adr_dir / f'{result["number"]:04d}-Has_Block.adoc'
    content = created_file.read_text()
    assert METADATA_BLOCK_START in content
    assert METADATA_BLOCK_END in content

    metadata = parse_metadata_block(content)
    assert metadata['summary'] == ''
    assert metadata['tags'] == []


# =========================================================================
# Tier 2: Width-agnostic numeric-prefix parsing and numbering
# =========================================================================

def test_create_next_filename_on_seven_adr_three_digit_corpus(adr_dir):
    """Success criterion: a 7-ADR 3-digit corpus emits the next ADR as 008-."""
    for n in range(1, 8):
        _touch_adr(adr_dir, f'{n:03d}-Decision_{n}.adoc')

    result = cmd_create(Namespace(command='create', title='Eighth Decision', status='Proposed'))

    assert result['status'] == 'success'
    assert result['number'] == 8
    assert Path(result['path']).name == '008-Eighth_Decision.adoc'
    assert 'ADR-008' in (adr_dir / '008-Eighth_Decision.adoc').read_text()


def test_create_on_empty_corpus_emits_four_digit_prefix(adr_dir):
    """Success criterion: an empty corpus emits 0001- (default width 4)."""
    result = cmd_create(Namespace(command='create', title='First Decision', status='Proposed'))

    assert result['status'] == 'success'
    assert result['number'] == 1
    assert Path(result['path']).name == '0001-First_Decision.adoc'


# =========================================================================
# Tier 2: Direct import tests
# =========================================================================

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


# =========================================================================
# Tier 2: Width-agnostic numeric-prefix parsing and numbering
# =========================================================================

def test_read_update_delete_on_four_digit_corpus(adr_dir):
    """read/update/delete resolve a 4-digit-prefixed ADR by its number."""
    _touch_adr(adr_dir, '0008-Wide.adoc', title='Wide', status='Proposed')

    read_result = cmd_read(Namespace(command='read', number=8))
    assert read_result['status'] == 'success'
    assert 'Wide' in read_result['content']

    update_result = cmd_update(Namespace(command='update', number=8, status='Accepted'))
    assert update_result['status'] == 'success'
    assert 'Accepted' in (adr_dir / '0008-Wide.adoc').read_text()

    delete_result = cmd_delete(Namespace(command='delete', number=8, force=True))
    assert delete_result['deleted']
    assert not (adr_dir / '0008-Wide.adoc').exists()


# =========================================================================
# Tier 2: Direct import tests
# =========================================================================

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
