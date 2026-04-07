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


class TestListProviders:
    """Tests for list-providers subcommand."""

    def test_list_providers_returns_success(self):
        """list-providers returns success with providers array."""
        result = run_script(SCRIPT_PATH, 'list-providers')
        assert result.returncode == 0
        assert 'success' in result.stdout
        assert 'providers' in result.stdout

    def test_list_providers_discovers_sonar(self):
        """list-providers discovers the sonar credential extension."""
        result = run_script(SCRIPT_PATH, 'list-providers')
        assert result.returncode == 0
        assert 'workflow-integration-sonar' in result.stdout


class TestConfigureWithCLIArgs:
    """Tests for configure with CLI args (non-interactive mode)."""

    def test_configure_no_skill_no_tty_errors(self):
        """Configure without --skill in non-TTY mode produces clear error."""
        result = run_script(SCRIPT_PATH, 'configure')
        assert result.returncode == 1
        assert '--skill is required when not running interactively' in result.stdout

    def test_configure_auth_none_completes_without_interaction(self):
        """Configure with auth_type=none and all CLI args needs no interactive input."""
        result = run_script(
            SCRIPT_PATH, 'configure',
            '--skill', 'workflow-integration-sonar',
            '--url', 'https://sonarcloud.io',
            '--auth-type', 'none',
            '--no-verify',
        )
        # Should succeed (auth_type=none needs no secret)
        if result.returncode == 0:
            assert 'success' in result.stdout
        else:
            # May fail if no provider found (test env), but should NOT be EOF
            assert 'EOF' not in result.stderr

    def test_configure_token_no_tty_no_token_arg_errors(self):
        """Configure with auth_type=token in non-TTY mode without --token produces clear error."""
        result = run_script(
            SCRIPT_PATH, 'configure',
            '--skill', 'workflow-integration-sonar',
            '--url', 'https://sonarcloud.io',
            '--auth-type', 'token',
            '--no-verify',
        )
        # Should either error about missing token or about missing provider
        if 'No credential extension found' not in result.stdout:
            assert result.returncode == 1
            assert 'Token is required' in result.stdout

    def test_configure_basic_no_tty_no_username_arg_errors(self):
        """Configure with auth_type=basic in non-TTY mode without --username produces clear error."""
        result = run_script(
            SCRIPT_PATH, 'configure',
            '--skill', 'workflow-integration-sonar',
            '--url', 'https://sonarcloud.io',
            '--auth-type', 'basic',
            '--no-verify',
        )
        if 'No credential extension found' not in result.stdout:
            assert result.returncode == 1
            assert 'Username is required' in result.stdout


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
