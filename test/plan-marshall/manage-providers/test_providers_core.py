#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for _providers_core.py module.

Covers path resolution, credential file I/O, RestClient, and provider discovery.
"""

import errno
import json
from unittest.mock import patch

import pytest
from _providers_core import (
    VALID_AUTH_TYPES,
    RestClient,
    _migrate_credentials_home_if_needed,
    apply_extra_passthrough,
    get_authenticated_client,
    get_project_name,
    load_credential,
    load_declared_providers,
    read_provider_config,
    remove_credential,
    resolve_credential_path,
    save_credential,
    verify_system_auth,
    write_provider_config,
)
from _providers_fixtures import stage_marshal

import _providers_core  # noqa: E402
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
        # Reference the LIVE module attr (the autouse _credentials_dir_sandbox
        # redirects it per-test) rather than the import-time binding.
        assert path == _providers_core.CREDENTIALS_DIR / 'test-skill.json'

    def test_project_scope(self):
        """Project scope resolves under project subdirectory."""
        path = resolve_credential_path('test-skill', 'project', 'my-project')
        assert path == _providers_core.CREDENTIALS_DIR / 'my-project' / 'test-skill.json'

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
        from _providers_core import read_provider_config, write_provider_config

        stage_marshal(tmp_path, monkeypatch, config=None)

        write_provider_config('test-skill', {'url': 'https://example.com', 'org': 'my-org'})
        config = read_provider_config('test-skill')
        assert config['url'] == 'https://example.com'
        assert config['org'] == 'my-org'

    def test_read_returns_empty_when_no_marshal(self, tmp_path, monkeypatch):
        """Returns empty dict when marshal.json does not exist."""
        from _providers_core import read_provider_config

        stage_marshal(tmp_path, monkeypatch, config=None)
        config = read_provider_config('nonexistent')
        assert config == {}

    def test_write_preserves_existing_content(self, tmp_path, monkeypatch):
        """Writing provider config preserves other marshal.json content."""
        from _providers_core import write_provider_config

        marshal = stage_marshal(
            tmp_path,
            monkeypatch,
            {
                'providers': [
                    {
                        'skill_name': 'workflow-integration-github',
                        'auth_type': 'system',
                        'repo_url': 'https://github.com/org/repo',
                    }
                ],
            },
        )

        write_provider_config('test-skill', {'url': 'https://api.example.com'})

        full_config = json.loads(marshal.read_text())
        assert full_config['providers'][0]['repo_url'] == 'https://github.com/org/repo'
        assert full_config['credentials_config']['test-skill']['url'] == 'https://api.example.com'

    def test_write_updates_existing_provider(self, tmp_path, monkeypatch):
        """Writing to same provider overwrites previous config."""
        from _providers_core import read_provider_config, write_provider_config

        stage_marshal(tmp_path, monkeypatch, config=None)

        write_provider_config('test-skill', {'url': 'https://old.com'})
        write_provider_config('test-skill', {'url': 'https://new.com'})

        config = read_provider_config('test-skill')
        assert config['url'] == 'https://new.com'


class TestApplyExtraPassthroughDenylist:
    """Tests for apply_extra_passthrough() — the case-normalized secret/reserved denylist.

    Regression for lesson 2026-06-30-16-001 (CWE-178, improper case handling): a
    caller-controlled ``--extra KEY=VALUE`` key is lower-cased BEFORE the
    secret/reserved denylist membership test, so a mixed-case variant of a secret
    key can never smuggle a secret into the git-tracked marshal.json.
    """

    @pytest.mark.parametrize(
        'key',
        [
            pytest.param('token', id='token-lower'),
            pytest.param('Token', id='token-title'),
            pytest.param('TOKEN', id='token-upper'),
            pytest.param('ToKeN', id='token-mixed'),
            pytest.param('password', id='password-lower'),
            pytest.param('PASSWORD', id='password-upper'),
            pytest.param('username', id='username-lower'),
            pytest.param('Username', id='username-title'),
        ],
    )
    def test_secret_key_rejected_case_insensitively(self, key):
        """A secret key in any case variant is rejected — never written to the config."""
        config: dict = {}
        applied = apply_extra_passthrough(config, [f'{key}=leaked-secret-value'])

        assert applied == []
        # The key is absent from the config in EVERY case form.
        assert key not in config
        assert key.lower() not in config
        assert 'leaked-secret-value' not in config.values()

    @pytest.mark.parametrize(
        'key',
        [pytest.param('url', id='url-lower'), pytest.param('URL', id='url-upper'), pytest.param('Url', id='url-title')],
    )
    def test_reserved_key_rejected_case_insensitively(self, key):
        """The reserved ``url`` key is rejected in any case variant."""
        config: dict = {}
        applied = apply_extra_passthrough(config, [f'{key}=https://evil.example'])

        assert applied == []
        assert key not in config
        assert key.lower() not in config

    def test_non_secret_key_is_applied_verbatim(self):
        """A benign non-secret key is applied with its original casing preserved."""
        config: dict = {}
        applied = apply_extra_passthrough(config, ['Organization=my-org', 'projectKey=abc'])

        assert applied == ['Organization', 'projectKey']
        assert config['Organization'] == 'my-org'
        assert config['projectKey'] == 'abc'

    def test_mixed_batch_applies_benign_and_rejects_secret(self):
        """A batch mixing a benign key and a case-variant secret applies only the benign one."""
        config: dict = {}
        applied = apply_extra_passthrough(config, ['org=acme', 'TOKEN=leaked'])

        assert applied == ['org']
        assert config == {'org': 'acme'}


class TestLoadDeclaredProviders:
    """Tests for load_declared_providers()."""

    def test_returns_empty_list_when_no_marshal_json(self, tmp_path, monkeypatch):
        """Should return empty list when marshal.json does not exist."""
        stage_marshal(tmp_path, monkeypatch, config=None)
        providers = load_declared_providers()
        assert providers == []

    def test_returns_empty_list_when_no_providers_key(self, tmp_path, monkeypatch):
        """Should return empty list when marshal.json has no providers key."""
        stage_marshal(tmp_path, monkeypatch, {'other': 'data'})
        providers = load_declared_providers()
        assert providers == []

    def test_returns_providers_from_marshal_json(self, tmp_path, monkeypatch):
        """Should return providers list from marshal.json."""
        config = {
            'providers': [
                {'skill_name': 'test-provider', 'display_name': 'Test', 'auth_type': 'token'},
            ],
        }
        stage_marshal(tmp_path, monkeypatch, config)
        providers = load_declared_providers()
        assert len(providers) == 1
        assert providers[0]['skill_name'] == 'test-provider'

    def test_handles_invalid_json(self, tmp_path, monkeypatch):
        """Should return empty list on invalid JSON."""
        marshal = stage_marshal(tmp_path, monkeypatch, config=None)
        marshal.write_text('not json')
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
        from _providers_core import check_credential_completeness

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
        from _providers_core import check_credential_completeness

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
        from _providers_core import write_provider_config

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


# =============================================================================
# Credentials home-root migration tests
# =============================================================================


def _migration_env(tmp_path, monkeypatch):
    """Set up an isolated home-root migration sandbox.

    Clears the explicit ``PLAN_MARSHALL_CREDENTIALS_DIR`` override (the autouse
    ``_credentials_dir_sandbox`` sets it, which would otherwise make the
    migration a no-op), points ``PLAN_MARSHALL_HOME`` at a tmp home so
    ``home_root()`` never touches the real ``~``, and redirects the module
    ``CREDENTIALS_DIR`` / ``_OLD_CREDENTIALS_DIR`` constants at tmp paths.

    Returns:
        ``(new_dir, old_dir)`` — the home-root credentials dir and the legacy dir.
    """
    monkeypatch.delenv('PLAN_MARSHALL_CREDENTIALS_DIR', raising=False)
    # PLAN_MARSHALL_HOME, when set, IS the home root verbatim (the ~/.plan-marshall
    # suffix applies only to the unset default), so home_root() == home here and
    # the credentials dir is home/credentials.
    home = tmp_path / 'home'
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(home))
    new_dir = home / 'credentials'
    old_dir = tmp_path / 'old-plan-marshall-credentials'
    monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', new_dir)
    monkeypatch.setattr('_providers_core._OLD_CREDENTIALS_DIR', old_dir)
    return new_dir, old_dir


class TestCredentialsHomeMigration:
    """Tests for _migrate_credentials_home_if_needed() — the lazy, idempotent
    home-root migration that never merges and never reads credential contents.
    """

    def test_migrates_old_to_new_then_idempotent_no_op(self, tmp_path, monkeypatch):
        """Only-old → migrate; a re-run is a no-op reporting already_migrated."""
        new_dir, old_dir = _migration_env(tmp_path, monkeypatch)
        old_dir.mkdir(mode=0o700, parents=True)
        (old_dir / 'github.json').write_text('{"skill": "github", "auth_type": "system"}')
        assert not new_dir.exists()

        result = _migrate_credentials_home_if_needed()

        assert result == 'migrated'
        assert new_dir.is_dir()
        assert (new_dir / 'github.json').is_file()
        assert not old_dir.exists()

        # Idempotent re-run: new present, old absent → already_migrated, no change.
        again = _migrate_credentials_home_if_needed()
        assert again == 'already_migrated'
        assert (new_dir / 'github.json').is_file()

    def test_no_op_when_nothing_to_migrate(self, tmp_path, monkeypatch):
        """Neither dir present → already_migrated and nothing is created."""
        new_dir, old_dir = _migration_env(tmp_path, monkeypatch)
        assert not new_dir.exists()
        assert not old_dir.exists()

        assert _migrate_credentials_home_if_needed() == 'already_migrated'
        assert not new_dir.exists()

    def test_explicit_override_is_never_migrated(self, tmp_path, monkeypatch):
        """When PLAN_MARSHALL_CREDENTIALS_DIR is set, migration is inert."""
        new_dir, old_dir = _migration_env(tmp_path, monkeypatch)
        # Re-assert the explicit override — it must short-circuit the migration.
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(new_dir))
        old_dir.mkdir(mode=0o700, parents=True)
        (old_dir / 'github.json').write_text('{"skill": "github"}')

        assert _migrate_credentials_home_if_needed() == 'already_migrated'
        # Old dir untouched, new dir NOT created — the override is authoritative.
        assert (old_dir / 'github.json').is_file()
        assert not new_dir.exists()

    def test_conflict_keeps_new_and_never_merges(self, tmp_path, monkeypatch, capsys):
        """Both dirs present → conflict; new kept verbatim, old NOT merged in."""
        new_dir, old_dir = _migration_env(tmp_path, monkeypatch)
        new_dir.mkdir(mode=0o700, parents=True)
        (new_dir / 'new-only.json').write_text('{"skill": "new"}')
        old_dir.mkdir(mode=0o700, parents=True)
        (old_dir / 'old-only.json').write_text('{"skill": "old", "token": "SECRET-DO-NOT-LEAK"}')

        result = _migrate_credentials_home_if_needed()

        assert result == 'conflict'
        # New dir untouched; the old file was NOT merged into it.
        assert (new_dir / 'new-only.json').is_file()
        assert not (new_dir / 'old-only.json').exists()
        # Old dir left in place for manual review.
        assert (old_dir / 'old-only.json').is_file()
        # The conflict notice names paths only — never a credential value.
        captured = capsys.readouterr()
        assert 'SECRET-DO-NOT-LEAK' not in captured.out
        assert 'SECRET-DO-NOT-LEAK' not in captured.err

    def test_migration_never_reads_file_contents(self, tmp_path, monkeypatch, capsys):
        """A non-JSON, secret-looking blob migrates verbatim — never parsed/read.

        If the migration parsed or rewrote credential files it would either fail
        on this non-JSON payload or alter the bytes. A byte-identical move proves
        it uses a pure filesystem rename that never reads the content, and no
        secret text appears in any output.
        """
        new_dir, old_dir = _migration_env(tmp_path, monkeypatch)
        old_dir.mkdir(mode=0o700, parents=True)
        secret_blob = b'\x00\x01 not-json token=SECRET-DO-NOT-LEAK \xff\xfe'
        (old_dir / 'weird.bin').write_bytes(secret_blob)

        result = _migrate_credentials_home_if_needed()

        assert result == 'migrated'
        assert (new_dir / 'weird.bin').read_bytes() == secret_blob
        captured = capsys.readouterr()
        assert 'SECRET-DO-NOT-LEAK' not in captured.out
        assert 'SECRET-DO-NOT-LEAK' not in captured.err

    def test_rename_eexist_is_treated_as_lost_race(self, tmp_path, monkeypatch):
        """A sibling claiming new_dir (EEXIST) during os.rename is a lost race.

        Reproduces the PR #923 gap: a concurrent migrator creates CREDENTIALS_DIR
        between our new_dir.exists() check and the os.rename, so os.rename raises
        FileExistsError (errno EEXIST). This must resolve to already_migrated,
        never crash.
        """
        import errno as _errno

        _new_dir, old_dir = _migration_env(tmp_path, monkeypatch)
        old_dir.mkdir(mode=0o700, parents=True)
        (old_dir / 'github.json').write_text('{"skill": "github"}')

        def _raise_eexist(src, dst):
            raise FileExistsError(_errno.EEXIST, 'File exists')

        monkeypatch.setattr('_providers_core.os.rename', _raise_eexist)

        assert _migrate_credentials_home_if_needed() == 'already_migrated'

    def test_rename_enotempty_is_treated_as_lost_race(self, tmp_path, monkeypatch):
        """A non-empty target (ENOTEMPTY) during os.rename is a lost race.

        A sibling both created AND started populating CREDENTIALS_DIR before our
        rename, so os.rename raises OSError with errno ENOTEMPTY. This must
        resolve to already_migrated, never crash.
        """
        import errno as _errno

        _new_dir, old_dir = _migration_env(tmp_path, monkeypatch)
        old_dir.mkdir(mode=0o700, parents=True)
        (old_dir / 'github.json').write_text('{"skill": "github"}')

        def _raise_enotempty(src, dst):
            raise OSError(_errno.ENOTEMPTY, 'Directory not empty')

        monkeypatch.setattr('_providers_core.os.rename', _raise_enotempty)

        assert _migrate_credentials_home_if_needed() == 'already_migrated'

    def test_exdev_fallback_move_race_is_treated_as_lost_race(self, tmp_path, monkeypatch):
        """The EXDEV → shutil.move fallback has the same lost-race exposure.

        os.rename raises EXDEV (cross-filesystem), the shutil.move fallback then
        loses the same race (ENOTEMPTY). The fallback branch must mirror the
        rename branch and resolve to already_migrated, never crash.
        """
        import errno as _errno

        _new_dir, old_dir = _migration_env(tmp_path, monkeypatch)
        old_dir.mkdir(mode=0o700, parents=True)
        (old_dir / 'github.json').write_text('{"skill": "github"}')

        def _raise_exdev(src, dst):
            raise OSError(_errno.EXDEV, 'Invalid cross-device link')

        def _raise_enotempty_move(src, dst):
            raise OSError(_errno.ENOTEMPTY, 'Directory not empty')

        monkeypatch.setattr('_providers_core.os.rename', _raise_exdev)
        monkeypatch.setattr('_providers_core.shutil.move', _raise_enotempty_move)

        assert _migrate_credentials_home_if_needed() == 'already_migrated'

    def test_unrelated_oserror_still_propagates(self, tmp_path, monkeypatch):
        """An OSError that is NOT a lost race (e.g. EACCES) still propagates.

        Guards against over-swallowing: only EEXIST/ENOTEMPTY (and the existing
        FileNotFoundError / EXDEV cases) are handled — a genuine permission
        failure must still surface rather than be silently masked.
        """
        import errno as _errno

        _new_dir, old_dir = _migration_env(tmp_path, monkeypatch)
        old_dir.mkdir(mode=0o700, parents=True)
        (old_dir / 'github.json').write_text('{"skill": "github"}')

        def _raise_eacces(src, dst):
            raise OSError(_errno.EACCES, 'Permission denied')

        monkeypatch.setattr('_providers_core.os.rename', _raise_eacces)

        with pytest.raises(OSError):
            _migrate_credentials_home_if_needed()


class TestGetProjectNameCwdFallbackDisambiguation:
    """Tests for the cwd-fallback disambiguation added to get_project_name()."""

    def test_distinct_dirs_same_basename_resolve_distinct(self, tmp_path, monkeypatch):
        """Two different dirs sharing a basename get distinct project names."""
        stage_marshal(tmp_path, monkeypatch, config=None)  # no marshal → cwd-fallback
        a = tmp_path / 'a' / 'proj'
        b = tmp_path / 'b' / 'proj'
        a.mkdir(parents=True)
        b.mkdir(parents=True)

        monkeypatch.chdir(a)
        name_a = get_project_name()
        monkeypatch.chdir(b)
        name_b = get_project_name()

        assert name_a != name_b
        assert name_a.startswith('proj-')
        assert name_b.startswith('proj-')
        # Deterministic: the same dir always resolves to the same name.
        assert get_project_name() == name_b

    def test_url_derived_output_unchanged_no_hash_suffix(self, tmp_path, monkeypatch):
        """The URL-derived branch is unchanged — plain repo name, no hash suffix."""
        stage_marshal(
            tmp_path,
            monkeypatch,
            {'providers': [{'category': 'version-control', 'url': 'https://github.com/org/myrepo.git'}]},
        )
        assert get_project_name() == 'myrepo'


# =============================================================================
# credentials_config key normalization
# =============================================================================

_PREFIXED_SKILL = 'plan-marshall:workflow-integration-sonar'
_CANONICAL_SKILL = 'workflow-integration-sonar'
_SONAR_URL = 'https://sonarcloud.io'


class TestCredentialsConfigKeyNormalization:
    """Tests for the ``credentials_config`` key normalization.

    ``providers[].skill_name`` is bundle-prefixed while the credential filename is
    prefix-stripped, so a block written under the prefixed spelling used to be
    invisible to a lookup by the stripped one: ``get_authenticated_client`` then
    resolved an empty URL and ``RestClient`` rejected it with "HTTPS required when
    authentication is configured". Writes now canonicalize the storage key and
    reads accept either spelling.
    """

    def test_prefixed_block_resolves_by_canonical_name(self, tmp_path, monkeypatch):
        """The field failure: a block stored prefixed is found by the stripped name."""
        stage_marshal(
            tmp_path,
            monkeypatch,
            {'credentials_config': {_PREFIXED_SKILL: {'url': _SONAR_URL, 'organization': 'cuioss'}}},
        )

        config = read_provider_config(_CANONICAL_SKILL)

        assert config == {'url': _SONAR_URL, 'organization': 'cuioss'}
        assert config['url'] == _SONAR_URL

    def test_authenticated_client_resolves_url_from_prefixed_block(self, tmp_path, monkeypatch):
        """End-to-end: a token credential plus a prefixed config block yields an HTTPS client.

        The credential file deliberately carries no ``url`` key, so the merged URL
        can only come from ``credentials_config``. Without the normalization the
        lookup misses, the URL is empty, and ``RestClient`` raises "HTTPS required".
        """
        creds_dir = tmp_path / 'creds'
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)
        stage_marshal(
            tmp_path,
            monkeypatch,
            {'credentials_config': {_PREFIXED_SKILL: {'url': _SONAR_URL}}},
        )
        save_credential(
            _CANONICAL_SKILL,
            {'skill': _CANONICAL_SKILL, 'auth_type': 'token', 'token': 'real-token-value'},
            'global',
        )

        client = get_authenticated_client(_CANONICAL_SKILL)

        try:
            assert client.url == _SONAR_URL
            assert client.scheme == 'https'
            assert 'Authorization' in client._headers
        finally:
            client.close()

    def test_canonical_block_resolves_by_prefixed_name(self, tmp_path, monkeypatch):
        """Reverse direction: a block stored stripped is found by the prefixed name."""
        stage_marshal(
            tmp_path,
            monkeypatch,
            {'credentials_config': {_CANONICAL_SKILL: {'url': _SONAR_URL}}},
        )

        assert read_provider_config(_PREFIXED_SKILL) == {'url': _SONAR_URL}

    def test_exact_match_wins_over_canonical_candidate(self, tmp_path, monkeypatch):
        """An exactly-matching key is preferred over a canonical-equality candidate.

        The stripped key is inserted FIRST so a scan-only lookup would return it;
        the exact-match attempt must still win.
        """
        stage_marshal(
            tmp_path,
            monkeypatch,
            {
                'credentials_config': {
                    _CANONICAL_SKILL: {'url': 'https://scan-candidate.example'},
                    _PREFIXED_SKILL: {'url': 'https://exact-match.example'},
                }
            },
        )

        assert read_provider_config(_PREFIXED_SKILL) == {'url': 'https://exact-match.example'}
        assert read_provider_config(_CANONICAL_SKILL) == {'url': 'https://scan-candidate.example'}

    def test_write_canonicalizes_key_and_leaves_no_shadow_block(self, tmp_path, monkeypatch):
        """A prefixed write stores the stripped key; a re-write never leaves two blocks."""
        marshal = stage_marshal(tmp_path, monkeypatch, {})

        write_provider_config(_PREFIXED_SKILL, {'url': _SONAR_URL})

        credentials_config = json.loads(marshal.read_text())['credentials_config']
        assert list(credentials_config) == [_CANONICAL_SKILL]

        # A re-configure under the other spelling updates the single block in place.
        write_provider_config(_CANONICAL_SKILL, {'url': 'https://sonar.example/updated'})

        credentials_config = json.loads(marshal.read_text())['credentials_config']
        assert list(credentials_config) == [_CANONICAL_SKILL]
        assert credentials_config[_CANONICAL_SKILL] == {'url': 'https://sonar.example/updated'}

    def test_write_collapses_a_pre_existing_shadow_block(self, tmp_path, monkeypatch):
        """A marshal.json already carrying both spellings collapses to one on write."""
        marshal = stage_marshal(
            tmp_path,
            monkeypatch,
            {
                'credentials_config': {
                    _PREFIXED_SKILL: {'url': 'https://stale-prefixed.example'},
                    _CANONICAL_SKILL: {'url': 'https://stale-canonical.example'},
                }
            },
        )

        write_provider_config(_PREFIXED_SKILL, {'url': _SONAR_URL})

        credentials_config = json.loads(marshal.read_text())['credentials_config']
        assert list(credentials_config) == [_CANONICAL_SKILL]
        assert credentials_config[_CANONICAL_SKILL] == {'url': _SONAR_URL}

    def test_unconfigured_skill_still_returns_empty(self, tmp_path, monkeypatch):
        """An unrelated skill name resolves to {} — the scan never matches a foreign key."""
        stage_marshal(
            tmp_path,
            monkeypatch,
            {'credentials_config': {_PREFIXED_SKILL: {'url': _SONAR_URL}}},
        )

        assert read_provider_config('workflow-integration-github') == {}
        assert read_provider_config('plan-marshall:workflow-integration-github') == {}


class TestCredentialsConfigKeyLazyMigration:
    """Tests for the lazy ``credentials_config`` key migration.

    Stale prefixed keys are canonicalized transparently on the next
    ``credentials_config`` access. The pass is idempotent, never writes when it
    has nothing to change, and refuses to merge two source keys that collapse
    onto one canonical key with differing bodies.
    """

    @staticmethod
    def _count_saves(monkeypatch) -> list[int]:
        """Spy on ``_save_marshal`` and return a list that grows per persist.

        Byte-comparing marshal.json cannot distinguish "no write" from "wrote
        identical bytes", so the no-write assertions count persists directly.
        """
        saves: list[int] = []
        real_save = _providers_core._save_marshal

        def _spy(config):
            saves.append(1)
            real_save(config)

        monkeypatch.setattr('_providers_core._save_marshal', _spy)
        return saves

    def test_stale_prefixed_key_is_canonicalized_in_the_persisted_config(self, tmp_path, monkeypatch):
        """A read through the access path re-keys the stale block on disk."""
        marshal = stage_marshal(
            tmp_path,
            monkeypatch,
            {'credentials_config': {_PREFIXED_SKILL: {'url': _SONAR_URL, 'organization': 'cuioss'}}},
        )

        read_provider_config(_CANONICAL_SKILL)

        credentials_config = json.loads(marshal.read_text())['credentials_config']
        assert list(credentials_config) == [_CANONICAL_SKILL]
        assert credentials_config[_CANONICAL_SKILL] == {'url': _SONAR_URL, 'organization': 'cuioss'}

    def test_second_pass_is_idempotent_and_performs_no_write(self, tmp_path, monkeypatch):
        """Re-running the migration over an already-migrated config writes nothing."""
        marshal = stage_marshal(
            tmp_path,
            monkeypatch,
            {'credentials_config': {_PREFIXED_SKILL: {'url': _SONAR_URL}}},
        )
        read_provider_config(_CANONICAL_SKILL)  # first pass migrates
        saves = self._count_saves(monkeypatch)

        read_provider_config(_CANONICAL_SKILL)  # second pass

        assert saves == []
        assert list(json.loads(marshal.read_text())['credentials_config']) == [_CANONICAL_SKILL]

    def test_already_canonical_config_performs_no_write(self, tmp_path, monkeypatch):
        """A config whose keys are already canonical is never rewritten."""
        stage_marshal(
            tmp_path,
            monkeypatch,
            {'credentials_config': {_CANONICAL_SKILL: {'url': _SONAR_URL}}},
        )
        saves = self._count_saves(monkeypatch)

        assert read_provider_config(_CANONICAL_SKILL) == {'url': _SONAR_URL}
        assert saves == []

    def test_differing_bodies_conflict_leaves_both_keys_and_writes_nothing(self, tmp_path, monkeypatch):
        """Two keys collapsing onto one canonical key with differing bodies are left alone."""
        marshal = stage_marshal(
            tmp_path,
            monkeypatch,
            {
                'credentials_config': {
                    _PREFIXED_SKILL: {'url': 'https://prefixed.example'},
                    _CANONICAL_SKILL: {'url': 'https://canonical.example'},
                }
            },
        )
        saves = self._count_saves(monkeypatch)

        assert read_provider_config(_PREFIXED_SKILL) == {'url': 'https://prefixed.example'}
        assert saves == []

        # Neither block was dropped or merged.
        credentials_config = json.loads(marshal.read_text())['credentials_config']
        assert credentials_config == {
            _PREFIXED_SKILL: {'url': 'https://prefixed.example'},
            _CANONICAL_SKILL: {'url': 'https://canonical.example'},
        }

    def test_persist_oserror_keeps_the_read_resilient(self, tmp_path, monkeypatch, capsys):
        """A failed migration persist never crashes an otherwise-resilient read.

        ``read_provider_config`` only catches ``(json.JSONDecodeError, KeyError)``,
        so an unguarded ``OSError`` from the migration's opportunistic write (full
        or read-only filesystem, permission denied) would propagate out of a
        documented graceful-fallback read. The persist is best-effort: the error is
        reported on stderr, the in-memory config stays canonicalized, and the
        caller still gets its block.
        """
        stage_marshal(
            tmp_path,
            monkeypatch,
            {'credentials_config': {_PREFIXED_SKILL: {'url': _SONAR_URL}}},
        )

        def _raise_oserror(config):
            raise OSError(errno.EROFS, 'Read-only file system')

        monkeypatch.setattr('_providers_core._save_marshal', _raise_oserror)

        assert read_provider_config(_CANONICAL_SKILL) == {'url': _SONAR_URL}
        assert 'WARNING' in capsys.readouterr().err

    def test_persist_oserror_still_reports_migrated(self, tmp_path, monkeypatch):
        """The status literal stays ``migrated`` — the in-memory config IS canonicalized."""
        stage_marshal(tmp_path, monkeypatch, config=None)

        def _raise_oserror(config):
            raise OSError(errno.ENOSPC, 'No space left on device')

        monkeypatch.setattr('_providers_core._save_marshal', _raise_oserror)
        config = {'credentials_config': {_PREFIXED_SKILL: {'url': _SONAR_URL}}}

        assert _providers_core._migrate_credentials_config_keys_if_needed(config) == 'migrated'
        assert list(config['credentials_config']) == [_CANONICAL_SKILL]

    def test_identical_bodies_collapse_without_conflict(self, tmp_path, monkeypatch):
        """Two spellings carrying the same body collapse — nothing is lost."""
        marshal = stage_marshal(
            tmp_path,
            monkeypatch,
            {
                'credentials_config': {
                    _PREFIXED_SKILL: {'url': _SONAR_URL},
                    _CANONICAL_SKILL: {'url': _SONAR_URL},
                }
            },
        )

        read_provider_config(_CANONICAL_SKILL)

        credentials_config = json.loads(marshal.read_text())['credentials_config']
        assert credentials_config == {_CANONICAL_SKILL: {'url': _SONAR_URL}}
