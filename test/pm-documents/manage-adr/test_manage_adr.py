#!/usr/bin/env python3
"""Tests for manage-adr.py script.

Tier 2 (direct import) tests with 2 subprocess CLI plumbing tests retained.
"""

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_script_path, run_script  # noqa: E402

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('pm-documents', 'manage-adr', 'manage-adr.py')

# Tier 2 direct imports - load hyphenated module via importlib
_MANAGE_ADR_SCRIPT = str(
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'pm-documents' / 'skills' / 'manage-adr' / 'scripts' / 'manage-adr.py'
)
_spec = importlib.util.spec_from_file_location('manage_adr', _MANAGE_ADR_SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_list = _mod.cmd_list
cmd_create = _mod.cmd_create
cmd_read = _mod.cmd_read
cmd_update = _mod.cmd_update
cmd_delete = _mod.cmd_delete
cmd_next_number = _mod.cmd_next_number
ADR_DIR_REF = _mod  # for patching ADR_DIR


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
    # Tier 3: Subprocess CLI plumbing tests (retained)
    # =========================================================================

    def test_cli_invalid_status(self):
        """Test creating ADR with invalid status via CLI (argparse rejection)."""
        result = run_script(SCRIPT_PATH, 'create', '--title', 'Invalid Status', '--status', 'InvalidStatus',
                            cwd=self.temp_dir)
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


if __name__ == '__main__':
    unittest.main()
