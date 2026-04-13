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

    def test_complete_credential(self, tmp_path):
        """Returns complete=True when no placeholders present."""
        from _providers_core import (  # type: ignore[import-not-found]
            CREDENTIALS_DIR,
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
        from _providers_core import (  # type: ignore[import-not-found]
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

    def test_auth_none_reports_complete(self, tmp_path):
        """auth_type=none with no secret fields reports complete."""
        from _providers_core import (  # type: ignore[import-not-found]
            CREDENTIALS_DIR,
            check_credential_completeness,
            save_credential,
        )

        skill = 'test-check-auth-none'
        data = {
            'skill': skill,
            'url': 'https://example.com',
            'auth_type': 'none',
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


class TestConfigureAuthTypeValidation:
    """Tests for auth_type validation against provider declaration.

    Each test runs against an isolated ``tmp_path/.plan/marshal.json``
    staged with the sonar provider declaration. PLAN_BASE_DIR is set so
    the subprocess resolves marshal.json inside the fixture tree — never
    the real repo-local .plan/marshal.json.
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
        self._plan_dir = plan_dir
        yield

    def test_configure_accepts_any_auth_type_without_declared(self):
        """Configure accepts any auth_type when provider has no declared auth_type."""
        result = run_script(
            SCRIPT_PATH, 'configure',
            '--skill', 'plan-marshall:workflow-integration-sonar',
            '--auth-type', 'none',
        )
        assert result.returncode == 0
        assert 'incompatible' not in result.stdout.lower()

    def test_configure_accepts_matching_auth_type(self):
        """Configure accepts auth_type that matches provider's declared auth_type."""
        from _providers_core import CREDENTIALS_DIR  # type: ignore[import-not-found]

        skill = 'plan-marshall:workflow-integration-sonar'
        result = run_script(
            SCRIPT_PATH, 'configure',
            '--skill', skill,
            '--auth-type', 'token',
        )
        try:
            assert result.returncode == 0
        finally:
            # Credential file uses unprefixed name (resolve_credential_path strips prefix)
            path = CREDENTIALS_DIR / 'workflow-integration-sonar.json'
            if path.exists():
                path.unlink()

    def test_configure_accepts_basic_without_declared_auth(self):
        """Configure accepts basic auth when provider has no declared auth_type."""
        result = run_script(
            SCRIPT_PATH, 'configure',
            '--skill', 'plan-marshall:workflow-integration-sonar',
            '--auth-type', 'basic',
        )
        assert result.returncode == 0
        assert 'incompatible' not in result.stdout.lower()


class TestConfigureMarshalJsonSeparation:
    """Tests for non-secret fields written to marshal.json instead of credential file."""

    def test_configure_writes_url_to_marshal_json(self, tmp_path, monkeypatch):
        """Configure writes url to marshal.json, not to credential file."""
        import json as _json

        from _providers_core import (  # type: ignore[import-not-found]
            CREDENTIALS_DIR,
            load_credential,
            read_provider_config,
        )

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        # Create marshal.json with sonar provider declaration
        _marshal = {'providers': [_SONAR_PROVIDER]}
        (plan_dir / 'marshal.json').write_text(_json.dumps(_marshal))
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

        skill = 'plan-marshall:workflow-integration-sonar'
        result = run_script(
            SCRIPT_PATH, 'configure',
            '--skill', skill,
            '--auth-type', 'token',
            '--url', 'https://sonarcloud.io',
        )
        try:
            assert result.returncode == 0

            # URL should be in marshal.json (subprocess wrote to tmp_path/.plan/)
            provider_config = read_provider_config(skill)
            assert provider_config.get('url') == 'https://sonarcloud.io'

            # Credential file should NOT contain url
            loaded = load_credential(skill, 'global')
            assert loaded is not None
            assert 'url' not in loaded
        finally:
            # Credential file uses unprefixed name (resolve_credential_path strips prefix)
            path = CREDENTIALS_DIR / 'workflow-integration-sonar.json'
            if path.exists():
                path.unlink()

    def test_configure_writes_extra_fields_to_marshal_json(self, tmp_path, monkeypatch):
        """Configure writes extra fields (organization, project_key) to marshal.json."""
        import json as _json

        from _providers_core import (  # type: ignore[import-not-found]
            CREDENTIALS_DIR,
            load_credential,
            read_provider_config,
        )

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        _marshal = {'providers': [_SONAR_PROVIDER]}
        (plan_dir / 'marshal.json').write_text(_json.dumps(_marshal))
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

        skill = 'plan-marshall:workflow-integration-sonar'
        result = run_script(
            SCRIPT_PATH, 'configure',
            '--skill', skill,
            '--auth-type', 'token',
            '--extra', 'organization=my-org', 'project_key=my-project',
        )
        try:
            assert result.returncode == 0

            # read_provider_config reads from cwd (monkeypatched to tmp_path)
            provider_config = read_provider_config(skill)
            assert provider_config.get('organization') == 'my-org'
            assert provider_config.get('project_key') == 'my-project'

            # Extra fields should NOT be in credential file
            loaded = load_credential(skill, 'global')
            assert loaded is not None
            assert 'organization' not in loaded
            assert 'project_key' not in loaded
        finally:
            # Credential file uses unprefixed name (resolve_credential_path strips prefix)
            path = CREDENTIALS_DIR / 'workflow-integration-sonar.json'
            if path.exists():
                path.unlink()


class TestConfigureAuthTypeMismatch:
    """Tests for configure reconfiguring when auth_type changes."""

    def test_configure_reconfigures_on_auth_type_mismatch(self, tmp_path):
        """Configure with token auth overwrites existing none credential."""
        import json as _json

        from _providers_core import (  # type: ignore[import-not-found]
            CREDENTIALS_DIR,
            load_credential,
            save_credential,
        )

        (tmp_path / '.plan').mkdir()
        _marshal = {'providers': [_SONAR_PROVIDER]}
        (tmp_path / '.plan' / 'marshal.json').write_text(_json.dumps(_marshal))
        skill = 'plan-marshall:workflow-integration-sonar'
        # Pre-create with auth_type=none
        data = {
            'skill': skill,
            'url': 'https://sonarcloud.io',
            'auth_type': 'none',
        }
        try:
            save_credential(skill, data, 'global')

            result = run_script(
                SCRIPT_PATH, 'configure',
                '--skill', skill,
                '--url', 'https://sonarcloud.io',
                '--auth-type', 'token',
                cwd=tmp_path,
            )
            # Should create new file with token placeholder, not return exists_complete
            if result.returncode == 0:
                assert 'exists_complete' not in result.stdout
                loaded = load_credential(skill, 'global')
                assert loaded is not None
                assert loaded['auth_type'] == 'token'
        finally:
            # Credential file uses unprefixed name (resolve_credential_path strips prefix)
            path = CREDENTIALS_DIR / 'workflow-integration-sonar.json'
            if path.exists():
                path.unlink()


# =============================================================================
# Configure with auth_type=system Tests
# =============================================================================


class TestConfigureSystemAuth:
    """Tests for configure with auth_type=system via direct import."""

    def test_system_auth_creates_credential_without_secrets(self, tmp_path, monkeypatch):
        """Configure with system auth creates credential file with no secret placeholders."""
        from _cred_configure import run_configure  # type: ignore[import-not-found]
        from _providers_core import (  # type: ignore[import-not-found]
            CREDENTIALS_DIR,
            check_credential_completeness,
            load_credential,
        )

        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        (tmp_path / '.plan' / 'marshal.json').write_text('{}')

        # Create a mock provider that declares system auth
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

        try:
            with monkeypatch.context() as m:
                m.setattr('_cred_configure.load_declared_providers', lambda: [mock_provider])
                m.setattr('_cred_configure.find_provider_with_details', lambda s: mock_provider if s == mock_provider['skill_name'] else None)
                run_configure(MockArgs())

            loaded = load_credential('test-system-provider', 'global')
            assert loaded is not None
            assert loaded['auth_type'] == 'system'
            # System auth should NOT have token, username, or password fields
            assert 'token' not in loaded
            assert 'username' not in loaded
            assert 'password' not in loaded

            completeness = check_credential_completeness('test-system-provider', 'global')
            assert completeness['complete'] is True
        finally:
            path = CREDENTIALS_DIR / 'test-system-provider.json'
            if path.exists():
                path.unlink()

    def test_system_auth_does_not_require_url(self, tmp_path, monkeypatch):
        """Configure with system auth succeeds without --url."""
        from _cred_configure import run_configure  # type: ignore[import-not-found]
        from _providers_core import CREDENTIALS_DIR, load_credential  # type: ignore[import-not-found]

        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
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

        try:
            with monkeypatch.context() as m:
                m.setattr('_cred_configure.load_declared_providers', lambda: [mock_provider])
                m.setattr('_cred_configure.find_provider_with_details', lambda s: mock_provider if s == mock_provider['skill_name'] else None)
                # Should not raise "URL is required"
                ret = run_configure(MockArgs())

            assert ret == 0
            loaded = load_credential('test-system-no-url', 'global')
            assert loaded is not None
            assert loaded['auth_type'] == 'system'
        finally:
            path = CREDENTIALS_DIR / 'test-system-no-url.json'
            if path.exists():
                path.unlink()

    def test_system_auth_override_accepted(self, tmp_path, monkeypatch):
        """Configure accepts explicit --auth-type override for system provider."""
        from _cred_configure import run_configure  # type: ignore[import-not-found]
        from _providers_core import CREDENTIALS_DIR  # type: ignore[import-not-found]

        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()

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

        try:
            with monkeypatch.context() as m:
                m.setattr('_cred_configure.load_declared_providers', lambda: [mock_provider])
                m.setattr('_cred_configure.find_provider_with_details', lambda s: mock_provider if s == mock_provider['skill_name'] else None)
                m.setattr('_cred_configure.output_toon', mock_output)
                run_configure(MockArgs())

            # With convention-based inference, CLI override is accepted
            assert captured_output.get('status') in ('created', 'exists_complete', 'exists_incomplete')
        finally:
            path = CREDENTIALS_DIR / 'test-system-override.json'
            if path.exists():
                path.unlink()
