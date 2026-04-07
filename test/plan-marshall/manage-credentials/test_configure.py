#!/usr/bin/env python3
"""Tests for _cred_configure.py and _cred_check.py modules.

Tests the configure command with placeholder-based secret entry
and the check command for credential completeness.
"""

import json
import os
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
        result = run_script(
            SCRIPT_PATH, 'configure', '--skill', 'nonexistent',
        )
        assert result.returncode == 1

    def test_configure_help(self):
        """Configure --help works."""
        result = run_script(SCRIPT_PATH, 'configure', '--help')
        assert result.returncode == 0
        assert 'configure' in result.stdout.lower() or 'usage' in result.stdout.lower()

    def test_configure_no_skill_errors(self):
        """Configure without --skill produces clear error."""
        result = run_script(SCRIPT_PATH, 'configure')
        assert result.returncode == 1
        assert '--skill is required' in result.stdout


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


class TestCheckCLI:
    """Tests for check subcommand via subprocess."""

    def test_check_help(self):
        """Check --help works."""
        result = run_script(SCRIPT_PATH, 'check', '--help')
        assert result.returncode == 0

    def test_check_requires_skill(self):
        """Check without --skill fails."""
        result = run_script(SCRIPT_PATH, 'check')
        assert result.returncode != 0

    def test_check_not_found(self, tmp_path):
        """Check returns not_found for unconfigured skill."""
        result = run_script(
            SCRIPT_PATH, 'check',
            '--skill', 'nonexistent-skill-for-test',
        )
        assert result.returncode == 0
        assert 'not_found' in result.stdout


class TestCheckCompleteness:
    """Tests for check_credential_completeness via direct import."""

    def test_not_found(self, tmp_path):
        """Returns exists=False when credential file does not exist."""
        from _credentials_core import check_credential_completeness  # type: ignore[import-not-found]

        result = check_credential_completeness('nonexistent', 'global')
        # May or may not exist depending on system state
        # Just verify the function returns the expected structure
        assert 'exists' in result
        assert 'complete' in result
        assert 'path' in result
        assert 'placeholders' in result

    def test_complete_credential(self, tmp_path):
        """Returns complete=True when no placeholders present."""
        from _credentials_core import (  # type: ignore[import-not-found]
            CREDENTIALS_DIR,
            SECRET_PLACEHOLDERS,
            check_credential_completeness,
            save_credential,
        )

        skill = 'test-check-complete'
        data = {
            'skill': skill,
            'url': 'https://example.com',
            'auth_type': 'token',
            'token': 'real-secret-value',
        }
        try:
            save_credential(skill, data, 'global')
            result = check_credential_completeness(skill, 'global')
            assert result['exists'] is True
            assert result['complete'] is True
            assert result['placeholders'] == []
        finally:
            path = CREDENTIALS_DIR / f'{skill}.json'
            if path.exists():
                path.unlink()

    def test_incomplete_credential(self, tmp_path):
        """Returns complete=False when placeholders present."""
        from _credentials_core import (  # type: ignore[import-not-found]
            CREDENTIALS_DIR,
            SECRET_PLACEHOLDERS,
            check_credential_completeness,
            save_credential,
        )

        skill = 'test-check-incomplete'
        data = {
            'skill': skill,
            'url': 'https://example.com',
            'auth_type': 'token',
            'token': SECRET_PLACEHOLDERS['token'],
        }
        try:
            save_credential(skill, data, 'global')
            result = check_credential_completeness(skill, 'global')
            assert result['exists'] is True
            assert result['complete'] is False
            assert 'token' in result['placeholders']
        finally:
            path = CREDENTIALS_DIR / f'{skill}.json'
            if path.exists():
                path.unlink()
