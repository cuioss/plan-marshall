#!/usr/bin/env python3
"""Tests for _cred_configure.py module.

Tests the interactive configure wizard with mocked input/getpass.
"""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_script_path, run_script  # noqa: E402

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-credentials', 'credentials.py')


class TestConfigureCLI:
    """Tests for configure subcommand via subprocess."""

    def test_configure_no_providers_fails(self, tmp_path):
        """Configure fails gracefully when no providers exist."""
        # Point to empty bundles dir so no extensions are found
        result = run_script(
            SCRIPT_PATH, 'configure', '--skill', 'nonexistent',
        )
        # Should fail because nonexistent skill has no extension
        assert result.returncode == 1

    def test_configure_help(self):
        """Configure --help works."""
        result = run_script(SCRIPT_PATH, 'configure', '--help')
        assert result.returncode == 0
        assert 'configure' in result.stdout.lower() or 'usage' in result.stdout.lower()


class TestConfigureLogic:
    """Tests for configure wizard logic via direct import."""

    def test_find_provider_returns_match(self):
        """_find_provider returns matching provider."""
        from _cred_configure import _find_provider  # type: ignore[import-not-found]

        providers = [
            {'skill_name': 'a', 'display_name': 'A'},
            {'skill_name': 'b', 'display_name': 'B'},
        ]
        result = _find_provider(providers, 'b')
        assert result['skill_name'] == 'b'

    def test_find_provider_returns_none_for_missing(self):
        """_find_provider returns None when not found."""
        from _cred_configure import _find_provider  # type: ignore[import-not-found]

        providers = [{'skill_name': 'a'}]
        assert _find_provider(providers, 'missing') is None
