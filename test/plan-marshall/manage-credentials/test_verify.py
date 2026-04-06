#!/usr/bin/env python3
"""Tests for _cmd_verify.py module.

Tests connectivity verification with mocked HTTP.
"""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_script_path, run_script  # noqa: E402

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-credentials', 'credentials.py')


class TestVerifyCLI:
    """Tests for verify subcommand."""

    def test_verify_requires_skill(self):
        """Verify without --skill returns error."""
        result = run_script(SCRIPT_PATH, 'verify')
        assert result.returncode == 1
        output = result.stdout + result.stderr
        assert 'skill' in output.lower() or 'required' in output.lower()

    def test_verify_unconfigured_skill_fails(self):
        """Verify for unconfigured skill returns error."""
        result = run_script(SCRIPT_PATH, 'verify', '--skill', 'nonexistent-skill')
        assert result.returncode == 1
