#!/usr/bin/env python3
"""Tests for manage-interface.py script.

Tier 2 (direct import) tests with 2 subprocess CLI plumbing tests retained.
"""

import importlib.util
import os
import shutil
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('pm-documents', 'manage-interface', 'manage-interface.py')

# Tier 2 direct imports - load hyphenated module via importlib
_MANAGE_IFACE_SCRIPT = str(
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'pm-documents' / 'skills' / 'manage-interface' / 'scripts' / 'manage-interface.py'
)
_spec = importlib.util.spec_from_file_location('manage_interface', _MANAGE_IFACE_SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_list = _mod.cmd_list
cmd_create = _mod.cmd_create
cmd_read = _mod.cmd_read
cmd_update = _mod.cmd_update
cmd_delete = _mod.cmd_delete
cmd_next_number = _mod.cmd_next_number


class TestManageInterface(unittest.TestCase):
    """Test cases for interface management script (Tier 2 direct import)."""

    temp_dir: str
    interface_dir: Path
    original_cwd: str

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.interface_dir = Path(cls.temp_dir) / 'doc' / 'interfaces'
        cls.interface_dir.mkdir(parents=True)
        cls.original_cwd = os.getcwd()
        os.chdir(cls.temp_dir)

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures."""
        os.chdir(cls.original_cwd)
        shutil.rmtree(cls.temp_dir)

    def setUp(self):
        """Clean interface directory before each test."""
        for f in self.interface_dir.glob('*.adoc'):
            f.unlink()

    # =========================================================================
    # Tier 2: Direct import tests
    # =========================================================================

    def test_next_number_empty_dir(self):
        """Test next-number returns 1 for empty directory."""
        result = cmd_next_number(Namespace(command='next-number'))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['next_number'], 1)

    def test_create_interface(self):
        """Test creating a new interface."""
        result = cmd_create(Namespace(command='create', title='User Service API', type='REST_API'))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['number'], 1)

        # Verify file exists
        created_file = self.interface_dir / '001-User_Service_API.adoc'
        self.assertTrue(created_file.exists())

        # Verify content
        content = created_file.read_text()
        self.assertIn('INTER-001', content)
        self.assertIn('User Service API', content)
        self.assertIn('REST_API', content)

    def test_create_multiple_interfaces(self):
        """Test creating multiple interfaces increments numbers."""
        cmd_create(Namespace(command='create', title='First', type='REST_API'))
        cmd_create(Namespace(command='create', title='Second', type='Event'))
        result = cmd_create(Namespace(command='create', title='Third', type='gRPC'))
        self.assertEqual(result['number'], 3)

    def test_list_interfaces(self):
        """Test listing interfaces."""
        cmd_create(Namespace(command='create', title='API One', type='REST_API'))
        cmd_create(Namespace(command='create', title='API Two', type='Event'))

        result = cmd_list(Namespace(command='list', type=None))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['count'], 2)

    def test_list_interfaces_filter_type(self):
        """Test listing interfaces filtered by type."""
        cmd_create(Namespace(command='create', title='REST One', type='REST_API'))
        cmd_create(Namespace(command='create', title='Event One', type='Event'))
        cmd_create(Namespace(command='create', title='REST Two', type='REST_API'))

        result = cmd_list(Namespace(command='list', type='REST_API'))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['count'], 2)

    def test_read_interface(self):
        """Test reading interface by number."""
        cmd_create(Namespace(command='create', title='Test Read', type='Database'))

        result = cmd_read(Namespace(command='read', number=1))
        self.assertEqual(result['status'], 'success')
        self.assertIn('Test Read', result['content'])

    def test_read_interface_not_found(self):
        """Test reading non-existent interface."""
        result = cmd_read(Namespace(command='read', number=999))
        self.assertEqual(result['status'], 'error')
        self.assertIn('not found', result['message'].lower())

    def test_delete_requires_force(self):
        """Test delete requires --force flag."""
        cmd_create(Namespace(command='create', title='Delete Test', type='File'))

        result = cmd_delete(Namespace(command='delete', number=1, force=False))
        self.assertEqual(result['status'], 'error')
        self.assertIn('--force', result['message'])

    def test_delete_with_force(self):
        """Test delete with --force flag."""
        cmd_create(Namespace(command='create', title='Delete Me', type='Other'))

        result = cmd_delete(Namespace(command='delete', number=1, force=True))
        self.assertTrue(result['deleted'])

        # Verify file is deleted
        files = list(self.interface_dir.glob('001-*.adoc'))
        self.assertEqual(len(files), 0)

    def test_valid_interface_types(self):
        """Test all valid interface types."""
        valid_types = ['REST_API', 'Event', 'gRPC', 'Database', 'File', 'Other']
        for itype in valid_types:
            result = cmd_create(Namespace(command='create', title=f'Test {itype}', type=itype))
            self.assertEqual(result['status'], 'success', f'Failed for type: {itype}')

    def test_filename_sanitization(self):
        """Test filename sanitization for special characters."""
        result = cmd_create(Namespace(command='create', title='API/Service with Special!', type='REST_API'))
        self.assertEqual(result['status'], 'success')
        # Get just the filename part
        filename = Path(result['path']).name
        # Special chars should be removed/replaced
        self.assertNotIn('/', filename)
        self.assertNotIn('!', filename)

    # =========================================================================
    # Tier 3: Subprocess CLI plumbing tests (retained)
    # =========================================================================

    def test_cli_create_requires_type(self):
        """Test that create requires --type parameter via CLI (argparse rejection)."""
        result = run_script(SCRIPT_PATH, 'create', '--title', 'Some Interface', cwd=self.temp_dir)
        self.assertNotEqual(result.returncode, 0)
        # argparse error goes to stderr
        self.assertIn('--type', result.stderr)

    def test_cli_invalid_interface_type(self):
        """Test that invalid type is rejected via CLI."""
        result = run_script(SCRIPT_PATH, 'create', '--title', 'Bad Interface', '--type', 'INVALID',
                            cwd=self.temp_dir)
        self.assertNotEqual(result.returncode, 0)

    def test_cli_create_and_list(self):
        """Test CLI plumbing: create then list via subprocess."""
        result = run_script(SCRIPT_PATH, 'create', '--title', 'CLI Test', '--type', 'REST_API',
                            cwd=self.temp_dir)
        self.assertEqual(result.returncode, 0)
        self.assertIn('success', result.stdout)

        result = run_script(SCRIPT_PATH, 'list', cwd=self.temp_dir)
        self.assertEqual(result.returncode, 0)
        self.assertIn('success', result.stdout)


if __name__ == '__main__':
    unittest.main()
