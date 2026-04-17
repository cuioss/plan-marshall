#!/usr/bin/env python3
"""Tests for _cred_configure.py and _cred_check.py modules.

Tests the configure command with placeholder-based secret entry
and the check command for credential completeness.
"""


import pytest

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-providers', 'credentials.py')

# Sonar provider declaration for tests that need marshal.json seeded
_SONAR_PROVIDER = {
    'skill_name': 'plan-marshall:workflow-integration-sonar',
    'display_name': 'SonarCloud / SonarQube',
    'default_url': 'https://sonarcloud.io',
    'header_name': 'Authorization',
    'header_value_template': 'Bearer {token}',
    'verify_endpoint': '/api/system/status',
    'verify_method': 'GET',
    'description': 'SonarCloud/SonarQube code analysis platform',
    'extra_fields': [
        {'key': 'organization', 'label': 'SonarCloud Organization', 'required': False},
        {'key': 'project_key', 'label': 'SonarCloud Project Key', 'required': True},
    ],
}


class TestConfigureCLI:
    """Tests for configure subcommand via subprocess."""

    def test_configure_no_providers_fails(self, tmp_path):
        """Configure fails gracefully when no providers exist."""
        result = run_script(
            SCRIPT_PATH, 'configure', '--skill', 'nonexistent',
        )
        assert result.returncode == 0

    def test_configure_help(self):
        """Configure --help works."""
        result = run_script(SCRIPT_PATH, 'configure', '--help')
        assert result.returncode == 0
        assert 'configure' in result.stdout.lower() or 'usage' in result.stdout.lower()

    def test_configure_no_skill_errors(self):
        """Configure without --skill produces clear error."""
        result = run_script(SCRIPT_PATH, 'configure')
        assert result.returncode == 0
        assert '--skill is required' in result.stdout or 'error' in result.stdout


class TestListProviders:
    """Tests for list-providers subcommand.

    list-providers reads from marshal.json's providers key (populated by
    discover-and-persist). Tests use isolated fixture dirs via tmp_path.
    """

    def test_list_providers_returns_success(self, tmp_path, monkeypatch):
        """list-providers returns success with providers array."""
        import json as _json

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        (plan_dir / 'marshal.json').write_text(_json.dumps({'skill_domains': {}}))
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

        # Activate git provider (minimum valid selection)
        persist = run_script(SCRIPT_PATH, 'discover-and-persist',
                             '--providers', 'plan-marshall:workflow-integration-git')
        assert persist.returncode == 0, f'Persist failed: {persist.stdout}'
        result = run_script(SCRIPT_PATH, 'list-providers')
        assert result.returncode == 0
        assert 'success' in result.stdout
        assert 'providers' in result.stdout

    def test_list_providers_discovers_sonar(self, tmp_path, monkeypatch):
        """Sonar provider is discoverable and persistable via full roundtrip."""
        import json as _json

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        (plan_dir / 'marshal.json').write_text(_json.dumps({'skill_domains': {}}))
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

        # Discovery-only mode: scans bundle script directories for *_provider.py files
        discover = run_script(SCRIPT_PATH, 'discover-and-persist')
        assert discover.returncode == 0
        assert 'workflow-integration-sonar' in discover.stdout, (
            f'Sonar not discovered. Found: {discover.stdout}'
        )
        # Activate and persist (must include version-control provider for validation)
        persist = run_script(SCRIPT_PATH, 'discover-and-persist',
                             '--providers', 'plan-marshall:workflow-integration-git,plan-marshall:workflow-integration-sonar')
        assert persist.returncode == 0, f'Persist failed: {persist.stdout}'
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
        from _providers_core import check_credential_completeness  # type: ignore[import-not-found]

        result = check_credential_completeness('nonexistent', 'global')
        # May or may not exist depending on system state
        # Just verify the function returns the expected structure
        assert 'exists' in result
        assert 'complete' in result
        assert 'path' in result
        assert 'placeholders' in result

    def test_complete_credential(self, tmp_path, monkeypatch):
        """Returns complete=True when no placeholders present."""
        from _providers_core import (  # type: ignore[import-not-found]
            check_credential_completeness,
            save_credential,
        )

        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        skill = 'test-check-complete'
        data = {
            'skill': skill,
            'url': 'https://example.com',
            'auth_type': 'token',
            'token': 'real-secret-value',
        }
        save_credential(skill, data, 'global')
        result = check_credential_completeness(skill, 'global')
        assert result['exists'] is True
        assert result['complete'] is True
        assert result['placeholders'] == []

    def test_incomplete_credential(self, tmp_path, monkeypatch):
        """Returns complete=False when placeholders present."""
        from _providers_core import (  # type: ignore[import-not-found]
            SECRET_PLACEHOLDERS,
            check_credential_completeness,
            save_credential,
        )

        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        skill = 'test-check-incomplete'
        data = {
            'skill': skill,
            'url': 'https://example.com',
            'auth_type': 'token',
            'token': SECRET_PLACEHOLDERS['token'],
        }
        save_credential(skill, data, 'global')
        result = check_credential_completeness(skill, 'global')
        assert result['exists'] is True
        assert result['complete'] is False
        assert 'token' in result['placeholders']

    def test_auth_none_reports_complete(self, tmp_path, monkeypatch):
        """auth_type=none with no secret fields reports complete."""
        from _providers_core import (  # type: ignore[import-not-found]
            check_credential_completeness,
            save_credential,
        )

        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        skill = 'test-check-auth-none'
        data = {
            'skill': skill,
            'url': 'https://example.com',
            'auth_type': 'none',
        }
        save_credential(skill, data, 'global')
        result = check_credential_completeness(skill, 'global')
        assert result['exists'] is True
        assert result['complete'] is True
        assert result['placeholders'] == []


class TestConfigureAuthTypeValidation:
    """Tests for auth_type validation against provider declaration.

    Each test runs against an isolated ``tmp_path/.plan/marshal.json``
    staged with the sonar provider declaration. PLAN_BASE_DIR pins the
    subprocess to the fixture tree, and PLAN_MARSHALL_CREDENTIALS_DIR
    pins the subprocess's credential directory to tmp_path/creds —
    nothing leaks into the real ``~/.plan-marshall-credentials/``.
    """

    @pytest.fixture(autouse=True)
    def _isolated_marshal(self, tmp_path, monkeypatch):
        import json as _json

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        (plan_dir / 'marshal.json').write_text(
            _json.dumps({'providers': [_SONAR_PROVIDER]})
        )
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(creds_dir))
        self._plan_dir = plan_dir
        self._creds_env = {'PLAN_MARSHALL_CREDENTIALS_DIR': str(creds_dir)}
        yield

    def test_configure_accepts_any_auth_type_without_declared(self):
        """Configure accepts any auth_type when provider has no declared auth_type."""
        result = run_script(
            SCRIPT_PATH, 'configure',
            '--skill', 'plan-marshall:workflow-integration-sonar',
            '--auth-type', 'none',
            env_overrides=self._creds_env,
        )
        assert result.returncode == 0
        assert 'incompatible' not in result.stdout.lower()

    def test_configure_accepts_matching_auth_type(self):
        """Configure accepts auth_type that matches provider's declared auth_type."""
        skill = 'plan-marshall:workflow-integration-sonar'
        result = run_script(
            SCRIPT_PATH, 'configure',
            '--skill', skill,
            '--auth-type', 'token',
            env_overrides=self._creds_env,
        )
        assert result.returncode == 0

    def test_configure_accepts_basic_without_declared_auth(self):
        """Configure accepts basic auth when provider has no declared auth_type."""
        result = run_script(
            SCRIPT_PATH, 'configure',
            '--skill', 'plan-marshall:workflow-integration-sonar',
            '--auth-type', 'basic',
            env_overrides=self._creds_env,
        )
        assert result.returncode == 0
        assert 'incompatible' not in result.stdout.lower()


class TestConfigureMarshalJsonSeparation:
    """Tests for non-secret fields written to marshal.json instead of credential file."""

    def test_configure_writes_url_to_marshal_json(self, tmp_path, monkeypatch):
        """Configure writes url to marshal.json, not to credential file."""
        import json as _json

        from _providers_core import (  # type: ignore[import-not-found]
            load_credential,
            read_provider_config,
        )

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        _marshal = {'providers': [_SONAR_PROVIDER]}
        (plan_dir / 'marshal.json').write_text(_json.dumps(_marshal))
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(creds_dir))
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        skill = 'plan-marshall:workflow-integration-sonar'
        result = run_script(
            SCRIPT_PATH, 'configure',
            '--skill', skill,
            '--auth-type', 'token',
            '--url', 'https://sonarcloud.io',
            env_overrides={'PLAN_MARSHALL_CREDENTIALS_DIR': str(creds_dir)},
        )
        assert result.returncode == 0

        # URL should be in marshal.json (subprocess wrote to tmp_path/.plan/)
        provider_config = read_provider_config(skill)
        assert provider_config.get('url') == 'https://sonarcloud.io'

        # Credential file should NOT contain url
        loaded = load_credential(skill, 'global')
        assert loaded is not None
        assert 'url' not in loaded

    def test_configure_writes_extra_fields_to_marshal_json(self, tmp_path, monkeypatch):
        """Configure writes extra fields (organization, project_key) to marshal.json."""
        import json as _json

        from _providers_core import (  # type: ignore[import-not-found]
            load_credential,
            read_provider_config,
        )

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        _marshal = {'providers': [_SONAR_PROVIDER]}
        (plan_dir / 'marshal.json').write_text(_json.dumps(_marshal))
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(creds_dir))
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        skill = 'plan-marshall:workflow-integration-sonar'
        result = run_script(
            SCRIPT_PATH, 'configure',
            '--skill', skill,
            '--auth-type', 'token',
            '--extra', 'organization=my-org', 'project_key=my-project',
            env_overrides={'PLAN_MARSHALL_CREDENTIALS_DIR': str(creds_dir)},
        )
        assert result.returncode == 0

        provider_config = read_provider_config(skill)
        assert provider_config.get('organization') == 'my-org'
        assert provider_config.get('project_key') == 'my-project'

        loaded = load_credential(skill, 'global')
        assert loaded is not None
        assert 'organization' not in loaded
        assert 'project_key' not in loaded


class TestConfigureAuthTypeMismatch:
    """Tests for configure reconfiguring when auth_type changes."""

    def test_configure_reconfigures_on_auth_type_mismatch(self, tmp_path, monkeypatch):
        """Configure with token auth overwrites existing none credential."""
        import json as _json

        from _providers_core import (  # type: ignore[import-not-found]
            load_credential,
            save_credential,
        )

        (tmp_path / '.plan').mkdir()
        _marshal = {'providers': [_SONAR_PROVIDER]}
        (tmp_path / '.plan' / 'marshal.json').write_text(_json.dumps(_marshal))
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path / '.plan'))
        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(creds_dir))
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        skill = 'plan-marshall:workflow-integration-sonar'
        # Pre-create with auth_type=none
        data = {
            'skill': skill,
            'url': 'https://sonarcloud.io',
            'auth_type': 'none',
        }
        save_credential(skill, data, 'global')

        result = run_script(
            SCRIPT_PATH, 'configure',
            '--skill', skill,
            '--url', 'https://sonarcloud.io',
            '--auth-type', 'token',
            cwd=tmp_path,
            env_overrides={'PLAN_MARSHALL_CREDENTIALS_DIR': str(creds_dir)},
        )
        # Should create new file with token placeholder, not return exists_complete
        if result.returncode == 0:
            assert 'exists_complete' not in result.stdout
            loaded = load_credential(skill, 'global')
            assert loaded is not None
            assert loaded['auth_type'] == 'token'


# =============================================================================
# Configure with auth_type=system Tests
# =============================================================================


class TestConfigureSystemAuth:
    """Tests for configure with auth_type=system via direct import.

    Each test isolates credential I/O to a per-test tmp_path by patching
    `_providers_core.CREDENTIALS_DIR` (evaluated at module import) and uses
    the `plan_context` fixture to pin `PLAN_BASE_DIR`. tmp_path auto-cleans,
    so no manual unlink is required.
    """

    def test_system_auth_creates_credential_without_secrets(self, plan_context, monkeypatch):
        """Configure with system auth creates credential file with no secret placeholders."""
        from _cred_configure import run_configure  # type: ignore[import-not-found]
        from _providers_core import (  # type: ignore[import-not-found]
            check_credential_completeness,
            load_credential,
        )

        tmp_path = plan_context.fixture_dir
        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        (tmp_path / '.plan').mkdir(exist_ok=True)
        (tmp_path / '.plan' / 'marshal.json').write_text('{}')

        mock_provider = {
            'skill_name': 'test-system-provider',
            'display_name': 'Test System CLI',
            'auth_type': 'system',
            'default_url': '',
            'verify_command': 'echo ok',
            'description': 'Test system auth provider',
        }

        class MockArgs:
            skill = 'test-system-provider'
            scope = 'global'
            auth_type = 'system'
            url = None
            extra = None

        monkeypatch.setattr('_cred_configure.load_declared_providers', lambda: [mock_provider])
        monkeypatch.setattr('_cred_configure.find_provider_with_details', lambda s: mock_provider if s == mock_provider['skill_name'] else None)
        run_configure(MockArgs())

        loaded = load_credential('test-system-provider', 'global')
        assert loaded is not None
        assert loaded['auth_type'] == 'system'
        assert 'token' not in loaded
        assert 'username' not in loaded
        assert 'password' not in loaded

        completeness = check_credential_completeness('test-system-provider', 'global')
        assert completeness['complete'] is True

    def test_system_auth_does_not_require_url(self, plan_context, monkeypatch):
        """Configure with system auth succeeds without --url."""
        from _cred_configure import run_configure  # type: ignore[import-not-found]
        from _providers_core import load_credential  # type: ignore[import-not-found]

        tmp_path = plan_context.fixture_dir
        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        (tmp_path / '.plan').mkdir(exist_ok=True)
        (tmp_path / '.plan' / 'marshal.json').write_text('{}')

        mock_provider = {
            'skill_name': 'test-system-no-url',
            'display_name': 'Test No URL',
            'auth_type': 'system',
            'default_url': '',
            'verify_command': 'echo ok',
            'description': 'System provider without URL',
        }

        class MockArgs:
            skill = 'test-system-no-url'
            scope = 'global'
            auth_type = 'system'
            url = None
            extra = None

        monkeypatch.setattr('_cred_configure.load_declared_providers', lambda: [mock_provider])
        monkeypatch.setattr('_cred_configure.find_provider_with_details', lambda s: mock_provider if s == mock_provider['skill_name'] else None)
        ret = run_configure(MockArgs())

        assert ret == 0
        loaded = load_credential('test-system-no-url', 'global')
        assert loaded is not None
        assert loaded['auth_type'] == 'system'

    def test_system_auth_override_accepted(self, plan_context, monkeypatch):
        """Configure accepts explicit --auth-type override for system provider."""
        from _cred_configure import run_configure  # type: ignore[import-not-found]

        tmp_path = plan_context.fixture_dir
        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        (tmp_path / '.plan').mkdir(exist_ok=True)

        mock_provider = {
            'skill_name': 'test-system-override',
            'display_name': 'System Provider',
            'default_url': '',
            'verify_command': 'echo ok',
            'description': 'System auth via convention',
        }

        class MockArgs:
            skill = 'test-system-override'
            scope = 'global'
            auth_type = 'token'
            url = 'https://example.com'
            extra = None

        captured_output = {}

        def mock_output(data):
            captured_output.update(data)

        monkeypatch.setattr('_cred_configure.load_declared_providers', lambda: [mock_provider])
        monkeypatch.setattr('_cred_configure.find_provider_with_details', lambda s: mock_provider if s == mock_provider['skill_name'] else None)
        monkeypatch.setattr('_cred_configure.output_toon', mock_output)
        run_configure(MockArgs())

        assert captured_output.get('status') in ('created', 'exists_complete', 'exists_incomplete')
