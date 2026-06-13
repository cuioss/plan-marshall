#!/usr/bin/env python3
"""Tests for manage-adr.py script.

Tier 2 (direct import) tests with 2 subprocess CLI plumbing tests retained.
"""

import os
import shutil
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

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


class TestManageAdr(unittest.TestCase):
    """Test cases for ADR management script (Tier 2 direct import)."""

    temp_dir: str
    adr_dir: Path
    original_cwd: str

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.adr_dir = Path(cls.temp_dir) / 'doc' / 'adr'
        cls.adr_dir.mkdir(parents=True)
        cls.original_cwd = os.getcwd()
        os.chdir(cls.temp_dir)

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures."""
        os.chdir(cls.original_cwd)
        shutil.rmtree(cls.temp_dir)

    def setUp(self):
        """Clean ADR directory before each test."""
        for f in self.adr_dir.glob('*.adoc'):
            f.unlink()

    # =========================================================================
    # Tier 2: Direct import tests
    # =========================================================================

    def test_next_number_empty_dir(self):
        """Test next-number returns 1 for empty directory."""
        result = cmd_next_number(Namespace(command='next-number'))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['next_number'], 1)

    def test_create_adr(self):
        """Test creating a new ADR."""
        result = cmd_create(Namespace(command='create', title='Use PostgreSQL', status='Proposed'))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['number'], 1)
        self.assertIn('001-Use_PostgreSQL.adoc', result['path'])

        # Verify file exists
        created_file = self.adr_dir / '001-Use_PostgreSQL.adoc'
        self.assertTrue(created_file.exists())

        # Verify content
        content = created_file.read_text()
        self.assertIn('ADR-001', content)
        self.assertIn('Use PostgreSQL', content)
        self.assertIn('Proposed', content)

    def test_create_adr_with_status(self):
        """Test creating ADR with custom status."""
        result = cmd_create(Namespace(command='create', title='Another Decision', status='Accepted'))
        self.assertEqual(result['status'], 'success')

        # Verify status in file
        created_file = self.adr_dir / f'{result["number"]:03d}-Another_Decision.adoc'
        content = created_file.read_text()
        self.assertIn('Accepted', content)

    def test_create_multiple_adrs(self):
        """Test creating multiple ADRs increments numbers."""
        cmd_create(Namespace(command='create', title='First ADR', status='Proposed'))
        cmd_create(Namespace(command='create', title='Second ADR', status='Proposed'))
        result = cmd_create(Namespace(command='create', title='Third ADR', status='Proposed'))
        self.assertEqual(result['number'], 3)

    def test_list_adrs(self):
        """Test listing ADRs."""
        cmd_create(Namespace(command='create', title='ADR One', status='Proposed'))
        cmd_create(Namespace(command='create', title='ADR Two', status='Proposed'))

        result = cmd_list(Namespace(command='list', status=None))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['count'], 2)

    def test_list_adrs_filter_status(self):
        """Test listing ADRs filtered by status."""
        cmd_create(Namespace(command='create', title='Proposed One', status='Proposed'))
        cmd_create(Namespace(command='create', title='Accepted One', status='Accepted'))

        result = cmd_list(Namespace(command='list', status='Proposed'))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['count'], 1)

    def test_read_adr(self):
        """Test reading ADR by number."""
        cmd_create(Namespace(command='create', title='Test Read', status='Proposed'))

        result = cmd_read(Namespace(command='read', number=1))
        self.assertEqual(result['status'], 'success')
        self.assertIn('Test Read', result['content'])

    def test_read_adr_not_found(self):
        """Test reading non-existent ADR."""
        result = cmd_read(Namespace(command='read', number=999))
        self.assertEqual(result['status'], 'error')
        self.assertIn('not found', result['message'].lower())

    def test_update_adr_status(self):
        """Test updating ADR status."""
        cmd_create(Namespace(command='create', title='Update Test', status='Proposed'))

        result = cmd_update(Namespace(command='update', number=1, status='Deprecated'))
        self.assertEqual(result['status'], 'success')

        # Verify status updated
        read_result = cmd_read(Namespace(command='read', number=1))
        self.assertIn('Deprecated', read_result['content'])

    def test_delete_requires_force(self):
        """Test delete requires --force flag."""
        cmd_create(Namespace(command='create', title='Delete Test', status='Proposed'))

        result = cmd_delete(Namespace(command='delete', number=1, force=False))
        self.assertEqual(result['status'], 'error')
        self.assertIn('--force', result['message'])

    def test_delete_with_force(self):
        """Test delete with --force flag."""
        cmd_create(Namespace(command='create', title='Delete Me', status='Proposed'))

        result = cmd_delete(Namespace(command='delete', number=1, force=True))
        self.assertTrue(result['deleted'])

        # Verify file is deleted
        files = list(self.adr_dir.glob('001-*.adoc'))
        self.assertEqual(len(files), 0)

    def test_filename_sanitization(self):
        """Test filename sanitization for special characters."""
        result = cmd_create(Namespace(command='create', title='Use API/REST for User Service!', status='Proposed'))
        self.assertEqual(result['status'], 'success')
        # Get just the filename part
        filename = Path(result['path']).name
        # Special chars should be removed/replaced
        self.assertNotIn('/', filename)
        self.assertNotIn('!', filename)

    # =========================================================================
    # Tier 2: Progressive-disclosure metadata block parsing
    # =========================================================================

    @staticmethod
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

    def test_parse_metadata_block_all_fields_present(self):
        """All four metadata fields are extracted; list fields are comma-split."""
        content = (
            '= ADR-001: Test\n\n'
            + self._build_metadata_block(
                summary='Use a fenced metadata block',
                tags='persistence, scanning',
                affects='plan-marshall, pm-documents',
                supersedes='ADR-000',
            )
            + '\n== Status\n\nProposed\n'
        )
        metadata = parse_metadata_block(content)
        self.assertEqual(metadata['summary'], 'Use a fenced metadata block')
        self.assertEqual(metadata['tags'], ['persistence', 'scanning'])
        self.assertEqual(metadata['affects'], ['plan-marshall', 'pm-documents'])
        self.assertEqual(metadata['supersedes'], ['ADR-000'])

    def test_parse_metadata_block_fields_absent(self):
        """A block whose fields are blank yields empty scalar/list defaults."""
        content = (
            '= ADR-002: Empty\n\n'
            + self._build_metadata_block()
            + '\n== Status\n\nProposed\n'
        )
        metadata = parse_metadata_block(content)
        self.assertEqual(metadata['summary'], '')
        self.assertEqual(metadata['tags'], [])
        self.assertEqual(metadata['affects'], [])
        self.assertEqual(metadata['supersedes'], [])

    def test_parse_metadata_block_missing_block(self):
        """Content without any metadata block returns all-empty defaults."""
        content = '= ADR-003: No Block\n\n== Status\n\nProposed\n'
        metadata = parse_metadata_block(content)
        self.assertEqual(metadata['summary'], '')
        self.assertEqual(metadata['tags'], [])
        self.assertEqual(metadata['affects'], [])
        self.assertEqual(metadata['supersedes'], [])

    def test_parse_metadata_block_malformed_lines_ignored(self):
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
        self.assertEqual(metadata['summary'], 'Has a summary')
        self.assertEqual(metadata['tags'], ['alpha', 'beta'])
        # Unknown field is silently dropped, not surfaced.
        self.assertNotIn('not a known field but well formed', metadata)

    def test_parse_metadata_block_extra_whitespace_in_list(self):
        """Comma-split list fields strip surrounding whitespace and empties."""
        content = (
            '= ADR-005: Whitespace\n\n'
            + self._build_metadata_block(tags=' a ,  b ,, c ')
            + '\n== Status\n\nProposed\n'
        )
        metadata = parse_metadata_block(content)
        self.assertEqual(metadata['tags'], ['a', 'b', 'c'])

    def test_parse_adr_file_surfaces_metadata(self):
        """parse_adr_file folds metadata fields into its returned dict."""
        adr_path = self.adr_dir / '007-With_Metadata.adoc'
        adr_path.write_text(
            '= ADR-007: With Metadata\n\n'
            + self._build_metadata_block(
                summary='Carry metadata through parse_adr_file',
                tags='lifecycle',
                affects='plan-marshall',
                supersedes='',
            )
            + '\n== Status\n\nAccepted\n'
        )
        adr = parse_adr_file(adr_path)
        self.assertEqual(adr['number'], 7)
        self.assertEqual(adr['title'], 'With Metadata')
        self.assertEqual(adr['status'], 'Accepted')
        self.assertEqual(adr['summary'], 'Carry metadata through parse_adr_file')
        self.assertEqual(adr['tags'], ['lifecycle'])
        self.assertEqual(adr['affects'], ['plan-marshall'])
        self.assertEqual(adr['supersedes'], [])

    # =========================================================================
    # Tier 2: scan subcommand
    # =========================================================================

    def _write_adr(self, filename, *, title, status='Proposed', **metadata):
        """Write an ADR file with a metadata block into the test ADR dir."""
        (self.adr_dir / filename).write_text(
            f'= ADR-{filename[:3]}: {title}\n\n'
            + self._build_metadata_block(**metadata)
            + f'\n== Status\n\n{status}\n'
        )

    def test_scan_empty_dir(self):
        """scan over an empty ADR dir returns zero ADRs."""
        result = cmd_scan(Namespace(command='scan', tag=None, affects=None))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['operation'], 'scan')
        self.assertEqual(result['count'], 0)
        self.assertEqual(result['adrs'], [])

    def test_scan_no_filter_returns_all_with_metadata(self):
        """scan with no filter returns every ADR plus its metadata fields."""
        self._write_adr('001-First.adoc', title='First', summary='first summary', tags='alpha')
        self._write_adr('002-Second.adoc', title='Second', summary='second summary', affects='plan-marshall')

        result = cmd_scan(Namespace(command='scan', tag=None, affects=None))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['count'], 2)

        by_number = {adr['number']: adr for adr in result['adrs']}
        self.assertEqual(by_number[1]['summary'], 'first summary')
        self.assertEqual(by_number[1]['tags'], ['alpha'])
        self.assertEqual(by_number[2]['summary'], 'second summary')
        self.assertEqual(by_number[2]['affects'], ['plan-marshall'])
        # scan payload carries the scannable fields for progressive disclosure.
        for adr in result['adrs']:
            for field in ('number', 'title', 'status', 'summary', 'tags', 'affects', 'supersedes'):
                self.assertIn(field, adr)

    def test_scan_tag_filter(self):
        """scan --tag returns only ADRs whose tags include the value."""
        self._write_adr('001-Persist.adoc', title='Persist', tags='persistence,db')
        self._write_adr('002-Other.adoc', title='Other', tags='ui')

        result = cmd_scan(Namespace(command='scan', tag='persistence', affects=None))
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['adrs'][0]['number'], 1)

    def test_scan_affects_filter(self):
        """scan --affects returns only ADRs whose affects include the value."""
        self._write_adr('001-Core.adoc', title='Core', affects='plan-marshall,pm-documents')
        self._write_adr('002-Docs.adoc', title='Docs', affects='pm-documents')

        result = cmd_scan(Namespace(command='scan', tag=None, affects='plan-marshall'))
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['adrs'][0]['number'], 1)

    def test_scan_filter_no_match(self):
        """scan with a filter matching nothing returns zero ADRs."""
        self._write_adr('001-Solo.adoc', title='Solo', tags='alpha')

        result = cmd_scan(Namespace(command='scan', tag='nonexistent', affects=None))
        self.assertEqual(result['count'], 0)
        self.assertEqual(result['adrs'], [])

    def test_create_emits_metadata_block(self):
        """create produces an ADR carrying the (empty) metadata block."""
        result = cmd_create(Namespace(command='create', title='Has Block', status='Proposed'))
        self.assertEqual(result['status'], 'success')

        created_file = self.adr_dir / f'{result["number"]:03d}-Has_Block.adoc'
        content = created_file.read_text()
        self.assertIn(METADATA_BLOCK_START, content)
        self.assertIn(METADATA_BLOCK_END, content)
        # The created ADR is scannable: parse_metadata_block yields empty defaults.
        metadata = parse_metadata_block(content)
        self.assertEqual(metadata['summary'], '')
        self.assertEqual(metadata['tags'], [])

    # =========================================================================
    # Tier 3: Subprocess CLI plumbing tests (retained)
    # =========================================================================

    def test_cli_invalid_status(self):
        """Test creating ADR with invalid status via CLI (argparse rejection)."""
        result = run_script(
            SCRIPT_PATH, 'create', '--title', 'Invalid Status', '--status', 'InvalidStatus', cwd=self.temp_dir
        )
        # argparse will reject invalid choices with exit code 2
        self.assertNotEqual(result.returncode, 0)
        # Error message is in stderr from argparse
        self.assertIn('invalid choice', result.stderr.lower())

    def test_cli_create_and_list(self):
        """Test CLI plumbing: create then list via subprocess."""
        result = run_script(SCRIPT_PATH, 'create', '--title', 'CLI Test', cwd=self.temp_dir)
        self.assertEqual(result.returncode, 0)
        self.assertIn('success', result.stdout)

        result = run_script(SCRIPT_PATH, 'list', cwd=self.temp_dir)
        self.assertEqual(result.returncode, 0)
        self.assertIn('success', result.stdout)

    def test_cli_scan(self):
        """Test CLI plumbing: create then scan via subprocess."""
        result = run_script(SCRIPT_PATH, 'create', '--title', 'Scan Me', cwd=self.temp_dir)
        self.assertEqual(result.returncode, 0)

        result = run_script(SCRIPT_PATH, 'scan', cwd=self.temp_dir)
        self.assertEqual(result.returncode, 0)
        self.assertIn('success', result.stdout)
        self.assertIn('scan', result.stdout)


if __name__ == '__main__':
    unittest.main()
