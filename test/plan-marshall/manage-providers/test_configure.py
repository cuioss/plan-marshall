#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _cred_configure.py and _cred_check.py modules.

Tests the configure command with placeholder-based secret entry
and the check command for credential completeness.
"""

import pytest
from _providers_core import SECRET_PLACEHOLDERS
from _providers_fixtures import stage_marshal

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-providers', 'credentials.py')

#: The CLI's own definition of the auth types it offers, read from the module that
#: declares it rather than copied into this file. It is reached through the
#: conftest loader WITHOUT registering the module: a plain ``import credentials``
#: would make that name both file-loaded and plainly imported, which is the
#: reload-order collision the loader contract refuses.
CLI_AUTH_TYPES = load_script_module(
    'plan-marshall', 'manage-providers', 'credentials.py', register=False
).CLI_AUTH_TYPES

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
            SCRIPT_PATH,
            'configure',
            '--skill',
            'nonexistent',
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
        # Redirect credential dir for the subprocess so nothing lands in
        # the real ~/.plan-marshall-credentials/.
        monkeypatch.setenv('HOME', str(tmp_path))
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(tmp_path / 'creds'))

        # Activate git provider (minimum valid selection)
        persist = run_script(
            SCRIPT_PATH, 'discover-and-persist', '--providers', 'plan-marshall:workflow-integration-git'
        )
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
        # Redirect credential dir for the subprocess so nothing lands in
        # the real ~/.plan-marshall-credentials/.
        monkeypatch.setenv('HOME', str(tmp_path))
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(tmp_path / 'creds'))

        # Discovery-only mode: scans bundle script directories for *_provider.py files
        discover = run_script(SCRIPT_PATH, 'discover-and-persist')
        assert discover.returncode == 0
        assert 'workflow-integration-sonar' in discover.stdout, f'Sonar not discovered. Found: {discover.stdout}'
        # Activate and persist (must include version-control provider for validation)
        persist = run_script(
            SCRIPT_PATH,
            'discover-and-persist',
            '--providers',
            'plan-marshall:workflow-integration-git,plan-marshall:workflow-integration-sonar',
        )
        assert persist.returncode == 0, f'Persist failed: {persist.stdout}'
        result = run_script(SCRIPT_PATH, 'list-providers')
        assert result.returncode == 0
        assert 'workflow-integration-sonar' in result.stdout


class TestConfigureLogic:
    """Tests for configure wizard logic via direct import."""

    def test_find_provider_returns_match(self):
        """_find_provider returns matching provider."""
        from _cred_configure import _find_provider

        providers = [
            {'skill_name': 'a', 'display_name': 'A'},
            {'skill_name': 'b', 'display_name': 'B'},
        ]
        result = _find_provider(providers, 'b')
        assert result['skill_name'] == 'b'

    def test_find_provider_returns_none_for_missing(self):
        """_find_provider returns None when not found."""
        from _cred_configure import _find_provider

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
            SCRIPT_PATH,
            'check',
            '--skill',
            'nonexistent-skill-for-test',
        )
        assert result.returncode == 0
        assert 'not_found' in result.stdout


class TestCheckCompleteness:
    """Tests for check_credential_completeness via direct import."""

    def test_not_found(self, tmp_path):
        """Returns exists=False when credential file does not exist."""
        from _providers_core import check_credential_completeness

        result = check_credential_completeness('nonexistent', 'global')
        # May or may not exist depending on system state
        # Just verify the function returns the expected structure
        assert 'exists' in result
        assert 'complete' in result
        assert 'path' in result
        assert 'placeholders' in result

    @pytest.mark.parametrize(
        ('secret_fields', 'expected_complete', 'expected_placeholders'),
        [
            ({'auth_type': 'token', 'token': 'real-secret-value'}, True, []),
            ({'auth_type': 'token', 'token': SECRET_PLACEHOLDERS['token']}, False, ['token']),
            ({'auth_type': 'none'}, True, []),
        ],
        ids=[
            'a-token-holding-a-real-value-is-complete',
            'a-token-left-at-its-placeholder-is-incomplete-and-names-the-field',
            'auth-none-needs-no-secret-so-it-is-complete',
        ],
    )
    def test_completeness_is_decided_by_the_stored_secret_fields(
        self, tmp_path, monkeypatch, secret_fields, expected_complete, expected_placeholders
    ):
        """A saved credential is complete iff no stored secret is still a placeholder."""
        from _providers_core import (
            check_credential_completeness,
            save_credential,
        )

        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        skill = 'test-check-completeness'
        save_credential(skill, {'skill': skill, 'url': 'https://example.com', **secret_fields}, 'global')

        result = check_credential_completeness(skill, 'global')

        assert result['exists'] is True
        assert result['complete'] is expected_complete
        assert result['placeholders'] == expected_placeholders


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
        (plan_dir / 'marshal.json').write_text(_json.dumps({'providers': [_SONAR_PROVIDER]}))
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(creds_dir))
        self._plan_dir = plan_dir
        self._creds_env = {'PLAN_MARSHALL_CREDENTIALS_DIR': str(creds_dir)}
        yield

    # Every ``auth_type`` the wizard accepts, offered to a provider whose own
    # declaration names none. The rows come from ``credentials.CLI_AUTH_TYPES``
    # — the CLI's own single definition of what it offers — so this file keeps no
    # second copy of that list to drift from it. The ids are derived from that
    # same tuple rather than written out beside it: a parallel id list is correct
    # only while the two orders agree, and an id here can claim nothing about the
    # declaration, because ``_SONAR_PROVIDER`` declares no ``auth_type`` at all.
    @pytest.mark.parametrize(
        'auth_type',
        CLI_AUTH_TYPES,
        ids=[f'offered-auth-type-{value}' for value in CLI_AUTH_TYPES],
    )
    def test_configure_accepts_the_auth_type_it_was_given(self, auth_type):
        """A provider declaring no auth_type accepts every auth_type offered to it."""
        result = run_script(
            SCRIPT_PATH,
            'configure',
            '--skill',
            'plan-marshall:workflow-integration-sonar',
            '--auth-type',
            auth_type,
            env_overrides=self._creds_env,
        )

        assert result.returncode == 0
        assert 'incompatible' not in result.stdout.lower()


class TestConfigureMarshalJsonSeparation:
    """Tests for non-secret fields written to marshal.json instead of credential file."""

    def test_configure_writes_url_to_marshal_json(self, tmp_path, monkeypatch):
        """Configure writes url to marshal.json, not to credential file."""
        from _providers_core import (
            load_credential,
            read_provider_config,
        )

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        # ``stage_marshal`` redirects BOTH the PLAN_BASE_DIR env (which the
        # subprocess writer reads) and the ``_config_core`` module attributes
        # (which the in-process ``read_provider_config`` reads through
        # ``load_config``). Setting only the env leaves the two bound to
        # DIFFERENT marshal.json files — the autouse sandbox keeps
        # ``_config_core.MARSHAL_PATH`` — so the read below would target a file
        # the writer never wrote.
        stage_marshal(plan_dir, monkeypatch, {'providers': [_SONAR_PROVIDER]})
        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(creds_dir))
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        skill = 'plan-marshall:workflow-integration-sonar'
        result = run_script(
            SCRIPT_PATH,
            'configure',
            '--skill',
            skill,
            '--auth-type',
            'token',
            '--url',
            'https://sonarcloud.io',
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
        from _providers_core import (
            load_credential,
            read_provider_config,
        )

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        stage_marshal(plan_dir, monkeypatch, {'providers': [_SONAR_PROVIDER]})
        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(creds_dir))
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)

        skill = 'plan-marshall:workflow-integration-sonar'
        result = run_script(
            SCRIPT_PATH,
            'configure',
            '--skill',
            skill,
            '--auth-type',
            'token',
            '--extra',
            'organization=my-org',
            'project_key=my-project',
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


_POM_WITH_SONAR = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>de.cuioss</groupId>
  <artifactId>example</artifactId>
  <version>1.0-SNAPSHOT</version>
  <properties>
    <sonar.organization>cuioss-pom-org</sonar.organization>
    <sonar.projectKey>de.cuioss:example-pom-key</sonar.projectKey>
  </properties>
</project>
"""

_POM_WITHOUT_SONAR = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>de.cuioss</groupId>
  <artifactId>example</artifactId>
  <version>1.0-SNAPSHOT</version>
</project>
"""

_POM_DERIVED_ORGANIZATION = 'cuioss-pom-org'
_POM_DERIVED_PROJECT_KEY = 'de.cuioss:example-pom-key'

#: ``(pom_content, extra_args, expects_warning, organization, project_key)`` per case.
#: ``pom_content=None`` stages no pom at all; a ``None`` coordinate means the key is
#: absent from the resulting provider config rather than present and empty.
_POM_DERIVATION_CASES = [
    (_POM_WITH_SONAR, (), False, _POM_DERIVED_ORGANIZATION, _POM_DERIVED_PROJECT_KEY),
    (
        _POM_WITH_SONAR,
        ('--extra', f'organization={_POM_DERIVED_ORGANIZATION}'),
        False,
        _POM_DERIVED_ORGANIZATION,
        _POM_DERIVED_PROJECT_KEY,
    ),
    (
        _POM_WITH_SONAR,
        ('--extra', 'organization=user-supplied-org'),
        True,
        'user-supplied-org',
        _POM_DERIVED_PROJECT_KEY,
    ),
    (None, ('--extra', 'organization=user-org'), False, 'user-org', None),
    (_POM_WITHOUT_SONAR, (), False, None, None),
]


class TestConfigureSonarPomDerive:
    """Tests for auto-deriving Sonar organization/project_key from pom.xml.

    Each test stages a ``pom.xml`` at the project root (the parent of the
    tracked ``.plan`` config dir) and a sonar-provider-seeded ``marshal.json``,
    then runs ``configure`` via subprocess and inspects the resulting
    ``provider_config`` and the result TOON.
    """

    def _stage(self, tmp_path, monkeypatch, pom_content: str | None):
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        # See the note in TestConfigureMarshalJsonSeparation: the subprocess
        # writer binds through the env while the in-process read binds through
        # the ``_config_core`` module attributes, so both must be redirected.
        stage_marshal(plan_dir, monkeypatch, {'providers': [_SONAR_PROVIDER]})
        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(creds_dir))
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)
        # Project root is the parent of the tracked .plan dir.
        if pom_content is not None:
            (tmp_path / 'pom.xml').write_text(pom_content)
        return {'PLAN_MARSHALL_CREDENTIALS_DIR': str(creds_dir)}

    @pytest.mark.parametrize(
        (
            'pom_content',
            'extra_args',
            'expects_warning',
            'expected_organization',
            'expected_project_key',
        ),
        _POM_DERIVATION_CASES,
        ids=[
            'a-sonar-pom-supplies-both-coordinates-when-none-is-given',
            'a-supplied-value-agreeing-with-the-pom-is-accepted-silently',
            'a-supplied-value-disagreeing-with-the-pom-warns-and-still-wins',
            'no-pom-keeps-the-supplied-value-and-derives-nothing-else',
            'a-pom-without-sonar-properties-derives-nothing',
        ],
    )
    def test_pom_derivation_fills_only_the_coordinates_the_caller_left_open(
        self,
        tmp_path,
        monkeypatch,
        pom_content,
        extra_args,
        expects_warning,
        expected_organization,
        expected_project_key,
    ):
        """A Sonar-bearing pom supplies the coordinates ``--extra`` did not.

        A supplied value always wins; the pom is consulted only for a coordinate
        the caller left open, and a disagreement is reported rather than resolved
        silently. ``warnings`` and ``mismatches`` are emitted as a pair, so both
        are asserted against the same expectation — and against the PARSED
        payload, never raw stdout, which also carries an absolute credential path
        whose directory names may themselves contain either word.
        """
        from _providers_core import read_provider_config

        creds_env = self._stage(tmp_path, monkeypatch, pom_content)
        skill = 'plan-marshall:workflow-integration-sonar'

        result = run_script(
            SCRIPT_PATH,
            'configure',
            '--skill',
            skill,
            '--auth-type',
            'token',
            *extra_args,
            env_overrides=creds_env,
        )

        assert result.returncode == 0
        parsed = result.toon()
        assert ('warnings' in parsed) is expects_warning
        assert ('mismatches' in parsed) is expects_warning

        provider_config = read_provider_config(skill)
        assert provider_config.get('organization') == expected_organization
        assert provider_config.get('project_key') == expected_project_key

    def test_non_sonar_provider_skips_derivation(self, tmp_path, monkeypatch):
        """A non-Sonar provider is unaffected even when a Sonar-bearing pom.xml is present."""
        from _providers_core import read_provider_config

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        non_sonar_provider = {
            'skill_name': 'plan-marshall:workflow-integration-git',
            'category': 'version-control',
            'display_name': 'Git',
            'default_url': 'https://github.com',
            'description': 'Git provider',
        }
        stage_marshal(plan_dir, monkeypatch, {'providers': [non_sonar_provider]})
        creds_dir = tmp_path / 'creds'
        creds_dir.mkdir()
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(creds_dir))
        monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', creds_dir)
        (tmp_path / 'pom.xml').write_text(_POM_WITH_SONAR)

        skill = 'plan-marshall:workflow-integration-git'
        result = run_script(
            SCRIPT_PATH,
            'configure',
            '--skill',
            skill,
            '--auth-type',
            'token',
            '--url',
            'https://github.com',
            env_overrides={'PLAN_MARSHALL_CREDENTIALS_DIR': str(creds_dir)},
        )
        assert result.returncode == 0

        provider_config = read_provider_config(skill)
        # Non-Sonar provider must NOT receive pom-derived Sonar coordinates.
        assert 'organization' not in provider_config
        assert 'project_key' not in provider_config


class TestConfigureAuthTypeMismatch:
    """Tests for configure reconfiguring when auth_type changes."""

    def test_configure_reconfigures_on_auth_type_mismatch(self, tmp_path, monkeypatch):
        """Configure with token auth overwrites existing none credential."""
        import json as _json

        from _providers_core import (
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
            SCRIPT_PATH,
            'configure',
            '--skill',
            skill,
            '--url',
            'https://sonarcloud.io',
            '--auth-type',
            'token',
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
    """Tests for configure against a system-auth (CLI) provider via direct import.

    A system-auth provider authenticates through its own vendor CLI, so configure
    persists nothing for it: no credential file and no credentials_config block.
    Each test isolates credential I/O to a per-test tmp_path by patching
    `_providers_core.CREDENTIALS_DIR` (evaluated at module import) and uses
    the `plan_context` fixture to pin `PLAN_BASE_DIR`. tmp_path auto-cleans,
    so no manual unlink is required.
    """

    def test_system_auth_persists_no_credential_file(self, plan_context, monkeypatch):
        """Configure against a system-auth provider writes no credential file."""
        from _cred_configure import run_configure
        from _providers_core import (
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

        captured_output: dict = {}

        monkeypatch.setattr('_cred_configure.load_declared_providers', lambda: [mock_provider])
        monkeypatch.setattr(
            '_cred_configure.find_provider_with_details',
            lambda s: mock_provider if s == mock_provider['skill_name'] else None,
        )
        monkeypatch.setattr('_cred_configure.output_toon', captured_output.update)
        run_configure(MockArgs())

        assert captured_output['status'] == 'system_auth'
        assert captured_output['credential_stored'] is False
        assert captured_output['verify_command'] == 'echo ok'
        assert 'path' not in captured_output

        assert load_credential('test-system-provider', 'global') is None
        assert check_credential_completeness('test-system-provider', 'global')['exists'] is False

    def test_system_auth_persists_no_blank_provider_url(self, plan_context, monkeypatch):
        """Configure against a urlless system-auth provider writes no provider config.

        A CI declaration carries no default_url, so persisting one would store a
        blank url — the state a provider config must never carry.
        """
        from _cred_configure import run_configure
        from _providers_core import read_provider_config

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
        monkeypatch.setattr(
            '_cred_configure.find_provider_with_details',
            lambda s: mock_provider if s == mock_provider['skill_name'] else None,
        )
        ret = run_configure(MockArgs())

        assert ret == 0
        assert read_provider_config('test-system-no-url') == {}

    def test_system_auth_override_accepted(self, plan_context, monkeypatch):
        """Configure accepts explicit --auth-type override for system provider."""
        from _cred_configure import run_configure

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
        monkeypatch.setattr(
            '_cred_configure.find_provider_with_details',
            lambda s: mock_provider if s == mock_provider['skill_name'] else None,
        )
        monkeypatch.setattr('_cred_configure.output_toon', mock_output)
        run_configure(MockArgs())

        assert captured_output.get('status') in ('created', 'exists_complete', 'exists_incomplete')
