#!/usr/bin/env python3
"""Tests for _credentials_core.py module.

Covers path resolution, credential file I/O, RestClient, and provider discovery.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import PlanContext  # noqa: E402

# Direct imports — conftest sets up PYTHONPATH
from _credentials_core import (  # type: ignore[import-not-found]  # noqa: E402
    CREDENTIALS_DIR,
    RestClient,
    discover_credential_providers,
    get_project_name,
    load_credential,
    remove_credential,
    resolve_credential_path,
    save_credential,
)


# =============================================================================
# Path Resolution Tests
# =============================================================================


class TestGetProjectName:
    """Tests for get_project_name()."""

    def test_sanitizes_special_characters(self, tmp_path, monkeypatch):
        """Project names must not contain path traversal characters."""
        marshal = tmp_path / '.plan' / 'marshal.json'
        marshal.parent.mkdir(parents=True)
        marshal.write_text(json.dumps({
            'ci': {'repo_url': 'https://github.com/org/my../repo!name'}
        }))
        monkeypatch.chdir(tmp_path)
        name = get_project_name()
        # Name should only contain safe characters
        assert all(c.isalnum() or c in '._-' for c in name)
        assert '..' not in name
        assert '!' not in name

    def test_falls_back_to_cwd_name(self):
        """Without marshal.json, uses cwd basename."""
        name = get_project_name()
        assert len(name) > 0
        assert all(c.isalnum() or c in '._-' for c in name)


class TestResolveCredentialPath:
    """Tests for resolve_credential_path()."""

    def test_global_scope(self):
        """Global scope resolves directly under CREDENTIALS_DIR."""
        path = resolve_credential_path('test-skill', 'global')
        assert path == CREDENTIALS_DIR / 'test-skill.json'

    def test_project_scope(self):
        """Project scope resolves under project subdirectory."""
        path = resolve_credential_path('test-skill', 'project', 'my-project')
        assert path == CREDENTIALS_DIR / 'my-project' / 'test-skill.json'

    def test_rejects_symlink_escape(self, tmp_path):
        """Paths that escape CREDENTIALS_DIR via symlinks are rejected."""
        with patch('_credentials_core.CREDENTIALS_DIR', tmp_path / 'creds'):
            (tmp_path / 'creds').mkdir()
            # Create a symlink that points outside
            evil_link = tmp_path / 'creds' / 'evil'
            evil_link.symlink_to(tmp_path / 'outside')
            with pytest.raises(ValueError, match='escapes credentials directory'):
                resolve_credential_path('../../etc/passwd', 'global')


# =============================================================================
# Credential File I/O Tests
# =============================================================================


class TestSaveAndLoadCredential:
    """Tests for save_credential() and load_credential()."""

    def test_save_creates_file_with_correct_permissions(self, tmp_path):
        """Saved credential files must have 0o600 permissions."""
        with patch('_credentials_core.CREDENTIALS_DIR', tmp_path / 'creds'):
            data = {'skill': 'test', 'url': 'https://example.com', 'auth_type': 'none'}
            path = save_credential('test', data, 'global')
            assert path.exists()
            mode = path.stat().st_mode & 0o777
            assert mode == 0o600

    def test_save_creates_directory_with_correct_permissions(self, tmp_path):
        """Credentials directory must have 0o700 permissions."""
        creds_dir = tmp_path / 'creds'
        with patch('_credentials_core.CREDENTIALS_DIR', creds_dir):
            data = {'skill': 'test', 'url': 'https://example.com', 'auth_type': 'none'}
            save_credential('test', data, 'global')
            mode = creds_dir.stat().st_mode & 0o777
            assert mode == 0o700

    def test_round_trip(self, tmp_path):
        """Save then load returns the same data."""
        with patch('_credentials_core.CREDENTIALS_DIR', tmp_path / 'creds'):
            data = {
                'skill': 'test-skill',
                'url': 'https://api.example.com',
                'auth_type': 'token',
                'header_name': 'Authorization',
                'header_value_template': 'Bearer {token}',
                'token': 'secret-token-123',
            }
            save_credential('test-skill', data, 'global')
            loaded = load_credential('test-skill', 'global')
            assert loaded == data

    def test_load_returns_none_for_missing(self, tmp_path):
        """Loading a non-existent credential returns None."""
        with patch('_credentials_core.CREDENTIALS_DIR', tmp_path / 'creds'):
            (tmp_path / 'creds').mkdir(mode=0o700)
            result = load_credential('nonexistent', 'global')
            assert result is None

    def test_load_returns_none_for_invalid_json(self, tmp_path):
        """Loading invalid JSON returns None (never exposes file content)."""
        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir(mode=0o700)
        bad_file = creds_dir / 'bad.json'
        bad_file.write_text('not json {{{')
        with patch('_credentials_core.CREDENTIALS_DIR', creds_dir):
            result = load_credential('bad', 'global')
            assert result is None

    def test_auto_scope_project_first(self, tmp_path):
        """Auto scope checks project-scoped first, then global."""
        creds_dir = tmp_path / 'creds'
        with patch('_credentials_core.CREDENTIALS_DIR', creds_dir):
            # Save global
            global_data = {'skill': 'test', 'url': 'https://global.com', 'auth_type': 'none'}
            save_credential('test', global_data, 'global')
            # Save project
            project_data = {'skill': 'test', 'url': 'https://project.com', 'auth_type': 'none'}
            save_credential('test', project_data, 'project', 'my-proj')
            # Auto should find project first
            loaded = load_credential('test', 'auto', 'my-proj')
            assert loaded['url'] == 'https://project.com'


class TestRemoveCredential:
    """Tests for remove_credential()."""

    def test_removes_existing_file(self, tmp_path):
        """Remove deletes the credential file."""
        with patch('_credentials_core.CREDENTIALS_DIR', tmp_path / 'creds'):
            data = {'skill': 'test', 'url': 'https://example.com', 'auth_type': 'none'}
            path = save_credential('test', data, 'global')
            assert path.exists()
            assert remove_credential('test', 'global') is True
            assert not path.exists()

    def test_returns_false_for_missing(self, tmp_path):
        """Remove returns False for non-existent credential."""
        with patch('_credentials_core.CREDENTIALS_DIR', tmp_path / 'creds'):
            (tmp_path / 'creds').mkdir(mode=0o700)
            assert remove_credential('nonexistent', 'global') is False


# =============================================================================
# RestClient Tests
# =============================================================================


class TestRestClient:
    """Tests for RestClient class."""

    def test_rejects_http_with_auth_headers(self):
        """HTTPS is required when authorization headers are present."""
        with pytest.raises(ValueError, match='HTTPS required'):
            RestClient('http://example.com', {'Authorization': 'Bearer token'})

    def test_allows_http_without_auth_headers(self):
        """HTTP is allowed when no auth headers (auth_type=none)."""
        client = RestClient('http://example.com', {})
        assert client.scheme == 'http'
        client.close()

    def test_allows_https_with_auth_headers(self):
        """HTTPS with auth headers is the normal case."""
        client = RestClient('https://example.com', {'Authorization': 'Bearer token'})
        assert client.scheme == 'https'
        client.close()

    def test_redact_body_scrubs_tokens(self):
        """Sensitive patterns in error bodies are redacted."""
        body = 'Error: token: abc123, Bearer xyz789'
        redacted = RestClient._redact_body(body)
        assert 'abc123' not in redacted
        assert '[REDACTED]' in redacted

    def test_base_url_exposed(self):
        """Base URL is accessible (not a secret)."""
        client = RestClient('https://api.example.com/v1', {})
        assert client.url == 'https://api.example.com/v1'
        client.close()

    def test_user_agent_set(self):
        """Custom User-Agent is configured."""
        client = RestClient('https://example.com', {})
        assert client._headers['User-Agent'] == 'plan-marshall-rest/1.0'
        client.close()


# =============================================================================
# Provider Discovery Tests
# =============================================================================


class TestDiscoverCredentialProviders:
    """Tests for discover_credential_providers()."""

    def test_discovers_sonar_extension(self):
        """Should find the credential_extension.py in workflow-integration-sonar."""
        providers = discover_credential_providers()
        skill_names = [p['skill_name'] for p in providers]
        assert 'workflow-integration-sonar' in skill_names

    def test_provider_has_required_fields(self):
        """Each provider must have all required fields."""
        providers = discover_credential_providers()
        sonar = [p for p in providers if p['skill_name'] == 'workflow-integration-sonar']
        assert len(sonar) == 1
        provider = sonar[0]
        required_fields = [
            'skill_name', 'display_name', 'auth_type', 'default_url',
            'header_name', 'header_value_template', 'verify_endpoint',
            'verify_method', 'description',
        ]
        for field in required_fields:
            assert field in provider, f'Missing required field: {field}'
