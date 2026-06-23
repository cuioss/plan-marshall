#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-adr.py script.

Tier 2 (direct import) tests with 2 subprocess CLI plumbing tests retained.
"""

from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path, load_script_module, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-adr', 'manage-adr.py')

# Tier 2 direct imports - load hyphenated module via the conftest helper
_mod = load_script_module('plan-marshall', 'manage-adr', 'manage-adr.py', 'manage_adr')

cmd_list = _mod.cmd_list
cmd_create = _mod.cmd_create
cmd_read = _mod.cmd_read
cmd_update = _mod.cmd_update
cmd_delete = _mod.cmd_delete
cmd_next_number = _mod.cmd_next_number
cmd_scan = _mod.cmd_scan
parse_metadata_block = _mod.parse_metadata_block
parse_adr_file = _mod.parse_adr_file
METADATA_BLOCK_START = _mod.METADATA_BLOCK_START
METADATA_BLOCK_END = _mod.METADATA_BLOCK_END


@pytest.fixture
def adr_dir(tmp_path, monkeypatch):
    """Provide a clean doc/adr directory and chdir into the temp project root."""
    directory = tmp_path / 'doc' / 'adr'
    directory.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return directory


def _build_metadata_block(*, summary='', tags='', affects='', supersedes=''):
    """Build a well-formed ADR metadata comment block for tests."""
    return (
        f'{METADATA_BLOCK_START}\n'
        f'// summary: {summary}\n'
        f'// tags: {tags}\n'
        f'// affects: {affects}\n'
        f'// supersedes: {supersedes}\n'
        f'{METADATA_BLOCK_END}\n'
    )


def _write_adr(adr_dir, filename, *, title, status='Proposed', **metadata):
    """Write an ADR file with a metadata block into the test ADR dir."""
    (adr_dir / filename).write_text(
        f'= ADR-{filename[:3]}: {title}\n\n'
        + _build_metadata_block(**metadata)
        + f'\n== Status\n\n{status}\n'
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
    assert '001-Use_PostgreSQL.adoc' in result['path']

    created_file = adr_dir / '001-Use_PostgreSQL.adoc'
    assert created_file.exists()

    content = created_file.read_text()
    assert 'ADR-001' in content
    assert 'Use PostgreSQL' in content
    assert 'Proposed' in content


def test_create_adr_with_status(adr_dir):
    """Test creating ADR with custom status."""
    result = cmd_create(Namespace(command='create', title='Another Decision', status='Accepted'))

    assert result['status'] == 'success'

    created_file = adr_dir / f'{result["number"]:03d}-Another_Decision.adoc'
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

    files = list(adr_dir.glob('001-*.adoc'))
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


def test_parse_metadata_block_missing_block(adr_dir):
    """Content without any metadata block returns all-empty defaults."""
    content = '= ADR-003: No Block\n\n== Status\n\nProposed\n'

    metadata = parse_metadata_block(content)

    assert metadata['summary'] == ''
    assert metadata['tags'] == []
    assert metadata['affects'] == []
    assert metadata['supersedes'] == []


def test_parse_metadata_block_malformed_lines_ignored(adr_dir):
    """Lines that are not `// field: value` comments are skipped."""
    content = (
        '= ADR-004: Malformed\n\n'
        f'{METADATA_BLOCK_START}\n'
        '// summary: Has a summary\n'
        'this is not a comment line\n'
        '// not a known field but well formed: ignored\n'
        '// tags: alpha,beta\n'
        f'{METADATA_BLOCK_END}\n'
        '\n== Status\n\nProposed\n'
    )

    metadata = parse_metadata_block(content)

    assert metadata['summary'] == 'Has a summary'
    assert metadata['tags'] == ['alpha', 'beta']
    assert 'not a known field but well formed' not in metadata


def test_parse_metadata_block_extra_whitespace_in_list(adr_dir):
    """Comma-split list fields strip surrounding whitespace and empties."""
    content = (
        '= ADR-005: Whitespace\n\n'
        + _build_metadata_block(tags=' a ,  b ,, c ')
        + '\n== Status\n\nProposed\n'
    )

    metadata = parse_metadata_block(content)

    assert metadata['tags'] == ['a', 'b', 'c']


def test_parse_adr_file_surfaces_metadata(adr_dir):
    """parse_adr_file folds metadata fields into its returned dict."""
    adr_path = adr_dir / '007-With_Metadata.adoc'
    adr_path.write_text(
        '= ADR-007: With Metadata\n\n'
        + _build_metadata_block(
            summary='Carry metadata through parse_adr_file',
            tags='lifecycle',
            affects='plan-marshall',
            supersedes='',
        )
        + '\n== Status\n\nAccepted\n'
    )

    adr = parse_adr_file(adr_path)

    assert adr['number'] == 7
    assert adr['title'] == 'With Metadata'
    assert adr['status'] == 'Accepted'
    assert adr['summary'] == 'Carry metadata through parse_adr_file'
    assert adr['tags'] == ['lifecycle']
    assert adr['affects'] == ['plan-marshall']
    assert adr['supersedes'] == []


# =========================================================================
# Tier 2: scan subcommand
# =========================================================================


def test_scan_empty_dir(adr_dir):
    """scan over an empty ADR dir returns zero ADRs."""
    result = cmd_scan(Namespace(command='scan', tag=None, affects=None))

    assert result['status'] == 'success'
    assert result['operation'] == 'scan'
    assert result['count'] == 0
    assert result['adrs'] == []


def test_scan_no_filter_returns_all_with_metadata(adr_dir):
    """scan with no filter returns every ADR plus its metadata fields."""
    _write_adr(adr_dir, '001-First.adoc', title='First', summary='first summary', tags='alpha')
    _write_adr(adr_dir, '002-Second.adoc', title='Second', summary='second summary', affects='plan-marshall')

    result = cmd_scan(Namespace(command='scan', tag=None, affects=None))

    assert result['status'] == 'success'
    assert result['count'] == 2

    by_number = {adr['number']: adr for adr in result['adrs']}
    assert by_number[1]['summary'] == 'first summary'
    assert by_number[1]['tags'] == ['alpha']
    assert by_number[2]['summary'] == 'second summary'
    assert by_number[2]['affects'] == ['plan-marshall']
    for adr in result['adrs']:
        for field in ('number', 'title', 'status', 'summary', 'tags', 'affects', 'supersedes'):
            assert field in adr


def test_scan_tag_filter(adr_dir):
    """scan --tag returns only ADRs whose tags include the value."""
    _write_adr(adr_dir, '001-Persist.adoc', title='Persist', tags='persistence,db')
    _write_adr(adr_dir, '002-Other.adoc', title='Other', tags='ui')

    result = cmd_scan(Namespace(command='scan', tag='persistence', affects=None))

    assert result['count'] == 1
    assert result['adrs'][0]['number'] == 1


def test_scan_affects_filter(adr_dir):
    """scan --affects returns only ADRs whose affects include the value."""
    _write_adr(adr_dir, '001-Core.adoc', title='Core', affects='plan-marshall,pm-documents')
    _write_adr(adr_dir, '002-Docs.adoc', title='Docs', affects='pm-documents')

    result = cmd_scan(Namespace(command='scan', tag=None, affects='plan-marshall'))

    assert result['count'] == 1
    assert result['adrs'][0]['number'] == 1


def test_scan_filter_no_match(adr_dir):
    """scan with a filter matching nothing returns zero ADRs."""
    _write_adr(adr_dir, '001-Solo.adoc', title='Solo', tags='alpha')

    result = cmd_scan(Namespace(command='scan', tag='nonexistent', affects=None))

    assert result['count'] == 0
    assert result['adrs'] == []


def test_create_emits_metadata_block(adr_dir):
    """create produces an ADR carrying the (empty) metadata block."""
    result = cmd_create(Namespace(command='create', title='Has Block', status='Proposed'))

    assert result['status'] == 'success'

    created_file = adr_dir / f'{result["number"]:03d}-Has_Block.adoc'
    content = created_file.read_text()
    assert METADATA_BLOCK_START in content
    assert METADATA_BLOCK_END in content

    metadata = parse_metadata_block(content)
    assert metadata['summary'] == ''
    assert metadata['tags'] == []


# =========================================================================
# Tier 3: Subprocess CLI plumbing tests (retained)
# =========================================================================


def test_cli_invalid_status(adr_dir):
    """Test creating ADR with invalid status via CLI (argparse rejection)."""
    result = run_script(
        SCRIPT_PATH, 'create', '--title', 'Invalid Status', '--status', 'InvalidStatus', cwd=str(Path.cwd())
    )

    assert result.returncode != 0
    assert 'invalid choice' in result.stderr.lower()


def test_cli_create_and_list(adr_dir):
    """Test CLI plumbing: create then list via subprocess."""
    result = run_script(SCRIPT_PATH, 'create', '--title', 'CLI Test', cwd=str(Path.cwd()))

    assert result.returncode == 0
    assert 'success' in result.stdout

    result = run_script(SCRIPT_PATH, 'list', cwd=str(Path.cwd()))

    assert result.returncode == 0
    assert 'success' in result.stdout


def test_cli_scan(adr_dir):
    """Test CLI plumbing: create then scan via subprocess."""
    result = run_script(SCRIPT_PATH, 'create', '--title', 'Scan Me', cwd=str(Path.cwd()))

    assert result.returncode == 0

    result = run_script(SCRIPT_PATH, 'scan', cwd=str(Path.cwd()))

    assert result.returncode == 0
    assert 'success' in result.stdout
    assert 'scan' in result.stdout
