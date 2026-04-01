#!/usr/bin/env python3
"""Tests for manage-interface.py script."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import ScriptResult, get_script_path, run_script

from toon_parser import parse_toon  # type: ignore[import-not-found]


class TestManageInterface(unittest.TestCase):
    """Test cases for interface management script."""

    script_path: Path
    temp_dir: str
    interface_dir: Path
    original_cwd: str

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.script_path = get_script_path('pm-documents', 'manage-interface', 'manage-interface.py')
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

    def run_iface(self, *args) -> 'ScriptResult':
        """Run the interface script with given arguments."""
        return run_script(self.script_path, *args, cwd=self.temp_dir)

    def parse_output(self, result: 'ScriptResult') -> dict:
        """Parse TOON output from stdout."""
        return parse_toon(result.stdout)

    def test_next_number_empty_dir(self):
        """Test next-number returns 1 for empty directory."""
        result = self.run_iface('next-number')
        self.assertEqual(result.returncode, 0)
        output = self.parse_output(result)
        self.assertEqual(output['status'], 'success')
        self.assertEqual(output['next_number'], 1)

    def test_create_interface(self):
        """Test creating a new interface."""
        result = self.run_iface('create', '--title', 'User Service API', '--type', 'REST_API')
        self.assertEqual(result.returncode, 0)
        output = self.parse_output(result)
        self.assertEqual(output['status'], 'success')
        self.assertEqual(output['number'], 1)

        # Verify file exists
        created_file = self.interface_dir / '001-User_Service_API.adoc'
        self.assertTrue(created_file.exists())

        # Verify content
        content = created_file.read_text()
        self.assertIn('INTER-001', content)
        self.assertIn('User Service API', content)
        self.assertIn('REST_API', content)

    def test_create_interface_requires_type(self):
        """Test that create requires --type parameter."""
        result = self.run_iface('create', '--title', 'Some Interface')
        self.assertNotEqual(result.returncode, 0)
        # argparse error goes to stderr
        self.assertIn('--type', result.stderr)

    def test_create_multiple_interfaces(self):
        """Test creating multiple interfaces increments numbers."""
        self.run_iface('create', '--title', 'First', '--type', 'REST_API')
        self.run_iface('create', '--title', 'Second', '--type', 'Event')
        result = self.run_iface('create', '--title', 'Third', '--type', 'gRPC')

        output = self.parse_output(result)
        self.assertEqual(output['number'], 3)

    def test_list_interfaces(self):
        """Test listing interfaces."""
        self.run_iface('create', '--title', 'API One', '--type', 'REST_API')
        self.run_iface('create', '--title', 'API Two', '--type', 'Event')

        result = self.run_iface('list')
        self.assertEqual(result.returncode, 0)
        output = self.parse_output(result)
        self.assertEqual(output['status'], 'success')
        self.assertEqual(output['count'], 2)

    def test_list_interfaces_filter_type(self):
        """Test listing interfaces filtered by type."""
        self.run_iface('create', '--title', 'REST One', '--type', 'REST_API')
        self.run_iface('create', '--title', 'Event One', '--type', 'Event')
        self.run_iface('create', '--title', 'REST Two', '--type', 'REST_API')

        result = self.run_iface('list', '--type', 'REST_API')
        output = self.parse_output(result)
        self.assertEqual(output['status'], 'success')
        self.assertEqual(output['count'], 2)

    def test_read_interface(self):
        """Test reading interface by number."""
        self.run_iface('create', '--title', 'Test Read', '--type', 'Database')

        result = self.run_iface('read', '--number', '1')
        self.assertEqual(result.returncode, 0)
        output = self.parse_output(result)
        self.assertEqual(output['status'], 'success')
        # Content is multiline — check stdout directly
        self.assertIn('Test Read', result.stdout)

    def test_read_interface_not_found(self):
        """Test reading non-existent interface."""
        result = self.run_iface('read', '--number', '999')
        self.assertNotEqual(result.returncode, 0)
        output = self.parse_output(result)
        self.assertEqual(output['status'], 'error')
        self.assertIn('not found', output['message'].lower())

    def test_delete_requires_force(self):
        """Test delete requires --force flag."""
        self.run_iface('create', '--title', 'Delete Test', '--type', 'File')

        result = self.run_iface('delete', '--number', '1')
        self.assertNotEqual(result.returncode, 0)
        output = self.parse_output(result)
        self.assertIn('--force', output['message'])

    def test_delete_with_force(self):
        """Test delete with --force flag."""
        self.run_iface('create', '--title', 'Delete Me', '--type', 'Other')

        result = self.run_iface('delete', '--number', '1', '--force')
        self.assertEqual(result.returncode, 0)
        output = self.parse_output(result)
        self.assertTrue(output['deleted'])

        # Verify file is deleted
        files = list(self.interface_dir.glob('001-*.adoc'))
        self.assertEqual(len(files), 0)

    def test_valid_interface_types(self):
        """Test all valid interface types."""
        valid_types = ['REST_API', 'Event', 'gRPC', 'Database', 'File', 'Other']
        for itype in valid_types:
            result = self.run_iface('create', '--title', f'Test {itype}', '--type', itype)
            output = self.parse_output(result)
            self.assertEqual(output['status'], 'success', f'Failed for type: {itype}')

    def test_invalid_interface_type(self):
        """Test that invalid type is rejected."""
        result = self.run_iface('create', '--title', 'Bad Interface', '--type', 'INVALID')
        self.assertNotEqual(result.returncode, 0)

    def test_filename_sanitization(self):
        """Test filename sanitization for special characters."""
        result = self.run_iface('create', '--title', 'API/Service with Special!', '--type', 'REST_API')
        output = self.parse_output(result)
        self.assertEqual(output['status'], 'success')
        # Get just the filename part
        filename = Path(output['path']).name
        # Special chars should be removed/replaced
        self.assertNotIn('/', filename)
        self.assertNotIn('!', filename)


if __name__ == '__main__':
    unittest.main()
