#!/usr/bin/env python3
"""Tests for _providers_core.py module.

Covers path resolution, credential file I/O, RestClient, and provider discovery.
"""

import json
from unittest.mock import patch

import pytest
from _providers_core import (  # type: ignore[import-not-found]
    CREDENTIALS_DIR,
    VALID_AUTH_TYPES,
    RestClient,
    get_authenticated_client,
    get_project_name,
    load_credential,
    load_declared_providers,
    remove_credential,
    resolve_credential_path,
    save_credential,
    verify_system_auth,
)

import conftest  # noqa: F401

# =============================================================================
# Path Resolution Tests
# =============================================================================


class TestGetProjectName:
    """Tests for get_project_name()."""

    def test_sanitizes_special_characters(self, tmp_path, monkeypatch):
        """Project names must not contain path traversal characters."""
        marshal = tmp_path / '.plan' / 'marshal.json'
        marshal.parent.mkdir(parents=True)
        marshal.write_text(
            json.dumps(
                {
                    'providers': [
                        {
                            'skill_name': 'workflow-integration-github',
                            'auth_type': 'system',
                            'repo_url': 'https://github.com/org/my../repo!name',
                        }
                    ],
                }
            )
        )
        monkeypatch.chdir(tmp_path)
        name = get_project_name()
        # Name should only contain safe characters
        assert all(c.isalnum() or c in '._-' for c in name)
        assert '..' not in name
        assert '!' not in name

    def test_falls_back_to_cwd_name(self, tmp_path, monkeypatch):
        """Without marshal.json, uses cwd basename.

        Redirect CREDENTIALS_DIR defensively — get_project_name() only
        reads marshal.json today, but a future change that touches the
        credentials tree would otherwise leak. monkeypatch.setattr
        restores automatically at teardown.
        """
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', tmp_path / 'creds')
        monkeypatch.chdir(tmp_path)
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

    def test_rejects_symlink_escape(self, tmp_path, monkeypatch):
        """Paths that escape CREDENTIALS_DIR via symlinks are rejected."""
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', tmp_path / 'creds')
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
        with patch('_providers_core.CREDENTIALS_DIR', tmp_path / 'creds'):
            data = {'skill': 'test', 'url': 'https://example.com', 'auth_type': 'none'}
            path = save_credential('test', data, 'global')
            assert path.exists()
            mode = path.stat().st_mode & 0o777
            assert mode == 0o600

    def test_save_creates_directory_with_correct_permissions(self, tmp_path):
        """Credentials directory must have 0o700 permissions."""
        creds_dir = tmp_path / 'creds'
        with patch('_providers_core.CREDENTIALS_DIR', creds_dir):
            data = {'skill': 'test', 'url': 'https://example.com', 'auth_type': 'none'}
            save_credential('test', data, 'global')
            mode = creds_dir.stat().st_mode & 0o777
            assert mode == 0o700

    def test_round_trip(self, tmp_path):
        """Save then load returns the same data."""
        with patch('_providers_core.CREDENTIALS_DIR', tmp_path / 'creds'):
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
        with patch('_providers_core.CREDENTIALS_DIR', tmp_path / 'creds'):
            (tmp_path / 'creds').mkdir(mode=0o700)
            result = load_credential('nonexistent', 'global')
            assert result is None

    def test_load_returns_none_for_invalid_json(self, tmp_path):
        """Loading invalid JSON returns None (never exposes file content)."""
        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir(mode=0o700)
        bad_file = creds_dir / 'bad.json'
        bad_file.write_text('not json {{{')
        with patch('_providers_core.CREDENTIALS_DIR', creds_dir):
            result = load_credential('bad', 'global')
            assert result is None

    def test_auto_scope_project_first(self, tmp_path):
        """Auto scope checks project-scoped first, then global."""
        creds_dir = tmp_path / 'creds'
        with patch('_providers_core.CREDENTIALS_DIR', creds_dir):
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
        with patch('_providers_core.CREDENTIALS_DIR', tmp_path / 'creds'):
            data = {'skill': 'test', 'url': 'https://example.com', 'auth_type': 'none'}
            path = save_credential('test', data, 'global')
            assert path.exists()
            assert remove_credential('test', 'global') is True
            assert not path.exists()

    def test_returns_false_for_missing(self, tmp_path, monkeypatch):
        """Remove returns False for non-existent credential."""
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', tmp_path / 'creds')
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


class TestProviderConfig:
    """Tests for marshal.json provider config read/write."""

    def test_write_and_read_provider_config(self, tmp_path, monkeypatch):
        """Write provider config to marshal.json and read it back."""
        from _providers_core import read_provider_config, write_provider_config  # type: ignore[import-not-found]

        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()

        write_provider_config('test-skill', {'url': 'https://example.com', 'org': 'my-org'})
        config = read_provider_config('test-skill')
        assert config['url'] == 'https://example.com'
        assert config['org'] == 'my-org'

    def test_read_returns_empty_when_no_marshal(self, tmp_path, monkeypatch):
        """Returns empty dict when marshal.json does not exist."""
        from _providers_core import read_provider_config  # type: ignore[import-not-found]

        monkeypatch.chdir(tmp_path)
        config = read_provider_config('nonexistent')
        assert config == {}

    def test_write_preserves_existing_content(self, tmp_path, monkeypatch):
        """Writing provider config preserves other marshal.json content."""
        from _providers_core import write_provider_config  # type: ignore[import-not-found]

        monkeypatch.chdir(tmp_path)
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        marshal = plan_dir / 'marshal.json'
        marshal.write_text(
            json.dumps(
                {
                    'providers': [
                        {
                            'skill_name': 'workflow-integration-github',
                            'auth_type': 'system',
                            'repo_url': 'https://github.com/org/repo',
                        }
                    ],
                }
            )
        )

        write_provider_config('test-skill', {'url': 'https://api.example.com'})

        full_config = json.loads(marshal.read_text())
        assert full_config['providers'][0]['repo_url'] == 'https://github.com/org/repo'
        assert full_config['credentials_config']['test-skill']['url'] == 'https://api.example.com'

    def test_write_updates_existing_provider(self, tmp_path, monkeypatch):
        """Writing to same provider overwrites previous config."""
        from _providers_core import read_provider_config, write_provider_config  # type: ignore[import-not-found]

        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()

        write_provider_config('test-skill', {'url': 'https://old.com'})
        write_provider_config('test-skill', {'url': 'https://new.com'})

        config = read_provider_config('test-skill')
        assert config['url'] == 'https://new.com'


class TestLoadDeclaredProviders:
    """Tests for load_declared_providers()."""

    def test_returns_empty_list_when_no_marshal_json(self, tmp_path, monkeypatch):
        """Should return empty list when marshal.json does not exist."""
        monkeypatch.chdir(tmp_path)
        providers = load_declared_providers()
        assert providers == []

    def test_returns_empty_list_when_no_providers_key(self, tmp_path, monkeypatch):
        """Should return empty list when marshal.json has no providers key."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        (tmp_path / '.plan' / 'marshal.json').write_text('{"other": "data"}')
        providers = load_declared_providers()
        assert providers == []

    def test_returns_providers_from_marshal_json(self, tmp_path, monkeypatch):
        """Should return providers list from marshal.json."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        config = {
            'providers': [
                {'skill_name': 'test-provider', 'display_name': 'Test', 'auth_type': 'token'},
            ],
        }
        (tmp_path / '.plan' / 'marshal.json').write_text(json.dumps(config))
        providers = load_declared_providers()
        assert len(providers) == 1
        assert providers[0]['skill_name'] == 'test-provider'

    def test_handles_invalid_json(self, tmp_path, monkeypatch):
        """Should return empty list on invalid JSON."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        (tmp_path / '.plan' / 'marshal.json').write_text('not json')
        providers = load_declared_providers()
        assert providers == []


# =============================================================================
# VALID_AUTH_TYPES Tests
# =============================================================================


class TestValidAuthTypes:
    """Tests for VALID_AUTH_TYPES constant."""

    def test_system_in_valid_auth_types(self):
        """The 'system' auth type must be included in VALID_AUTH_TYPES."""
        assert 'system' in VALID_AUTH_TYPES

    def test_all_expected_auth_types_present(self):
        """All four auth types must be present: none, token, basic, system."""
        expected = {'none', 'token', 'basic', 'system'}
        assert set(VALID_AUTH_TYPES) == expected


# =============================================================================
# check_credential_completeness with auth_type=system
# =============================================================================


class TestCheckCompletenessSystem:
    """Tests for check_credential_completeness with auth_type=system."""

    def test_system_auth_reports_complete(self, tmp_path, monkeypatch):
        """auth_type=system credential with no secret fields reports complete."""
        from _providers_core import check_credential_completeness  # type: ignore[import-not-found]

        creds_dir = tmp_path / 'creds'
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        skill = 'test-system-complete'
        data = {
            'skill': skill,
            'auth_type': 'system',
        }
        save_credential(skill, data, 'global')
        result = check_credential_completeness(skill, 'global')
        assert result['exists'] is True
        assert result['complete'] is True
        assert result['placeholders'] == []

    def test_system_auth_no_token_check(self, tmp_path, monkeypatch):
        """auth_type=system must not check for missing token field."""
        from _providers_core import check_credential_completeness  # type: ignore[import-not-found]

        creds_dir = tmp_path / 'creds'
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        skill = 'test-system-no-token'
        data = {
            'skill': skill,
            'auth_type': 'system',
            # Deliberately no 'token' field
        }
        save_credential(skill, data, 'global')
        result = check_credential_completeness(skill, 'global')
        assert result['complete'] is True
        assert 'token' not in result['placeholders']


# =============================================================================
# get_authenticated_client with auth_type=system
# =============================================================================


class TestGetAuthenticatedClientSystem:
    """Tests for get_authenticated_client with auth_type=system."""

    def test_system_auth_with_url_returns_client(self, tmp_path, monkeypatch):
        """System auth with URL configured returns a RestClient with no auth headers."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        creds_dir = tmp_path / 'creds'
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        skill = 'test-system-client'
        data = {
            'skill': skill,
            'auth_type': 'system',
        }
        save_credential(skill, data, 'global')
        # Write URL to marshal.json provider config
        from _providers_core import write_provider_config  # type: ignore[import-not-found]

        write_provider_config(skill, {'url': 'https://api.example.com'})

        client = get_authenticated_client(skill)
        # System auth should produce no Authorization header
        assert 'Authorization' not in client._headers
        assert client.url == 'https://api.example.com'
        client.close()

    def test_system_auth_without_url_raises(self, tmp_path, monkeypatch):
        """System auth without URL raises ValueError with helpful message."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        # Write empty provider config (no URL)
        (tmp_path / '.plan' / 'marshal.json').write_text('{}')
        creds_dir = tmp_path / 'creds'
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        skill = 'test-system-no-url'
        data = {
            'skill': skill,
            'auth_type': 'system',
        }
        save_credential(skill, data, 'global')
        with pytest.raises(ValueError, match='no URL configured'):
            get_authenticated_client(skill)

    def test_system_auth_no_secrets_in_credential(self, tmp_path, monkeypatch):
        """System auth credential file should not contain token/username/password."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        creds_dir = tmp_path / 'creds'
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        skill = 'test-system-no-secrets'
        data = {
            'skill': skill,
            'auth_type': 'system',
        }
        save_credential(skill, data, 'global')
        loaded = load_credential(skill, 'global')
        assert loaded is not None
        assert 'token' not in loaded
        assert 'username' not in loaded
        assert 'password' not in loaded


# =============================================================================
# verify_system_auth Tests
# =============================================================================


class TestVerifySystemAuth:
    """Tests for verify_system_auth()."""

    def test_successful_command(self):
        """verify_system_auth returns success when command succeeds."""
        provider = {
            'skill_name': 'test-provider',
            'verify_command': 'echo hello',
        }
        result = verify_system_auth(provider)
        assert result['success'] is True
        assert result['skill'] == 'test-provider'
        assert result['exit_code'] == 0
        assert 'hello' in result['output']

    def test_failed_command(self):
        """verify_system_auth returns failure when command fails."""
        provider = {
            'skill_name': 'test-provider',
            'verify_command': 'false',
        }
        result = verify_system_auth(provider)
        assert result['success'] is False
        assert result['exit_code'] != 0

    def test_missing_command(self):
        """verify_system_auth returns failure when command is not found."""
        provider = {
            'skill_name': 'test-provider',
            'verify_command': 'nonexistent-command-xyz-12345',
        }
        result = verify_system_auth(provider)
        assert result['success'] is False
        assert result['exit_code'] == -1
        assert 'not found' in result['output'].lower()

    def test_no_verify_command(self):
        """verify_system_auth returns failure when no verify_command defined."""
        provider = {
            'skill_name': 'test-provider',
        }
        result = verify_system_auth(provider)
        assert result['success'] is False
        assert 'No verify_command' in result['output']

    def test_empty_verify_command(self):
        """verify_system_auth returns failure when verify_command is empty string."""
        provider = {
            'skill_name': 'test-provider',
            'verify_command': '',
        }
        result = verify_system_auth(provider)
        assert result['success'] is False

    def test_output_truncated_to_500_chars(self):
        """verify_system_auth truncates output to 500 characters."""
        # Use python to generate long output
        provider = {
            'skill_name': 'test-provider',
            'verify_command': 'python3 -c print("x"*1000)',
        }
        result = verify_system_auth(provider)
        assert len(result['output']) <= 500
