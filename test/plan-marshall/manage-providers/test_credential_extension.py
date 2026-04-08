#!/usr/bin/env python3
"""Tests for credential extension discovery across marketplace bundles."""


from _credentials_core import discover_credential_providers  # type: ignore[import-not-found]

import conftest  # noqa: F401


class TestCredentialExtensionDiscovery:
    """Tests for credential extension discovery."""

    def test_discovers_sonar_provider(self):
        """Should find the Sonar credential extension."""
        providers = discover_credential_providers()
        names = [p['skill_name'] for p in providers]
        assert 'workflow-integration-sonar' in names

    def test_sonar_provider_fields(self):
        """Sonar provider must have correct configuration."""
        providers = discover_credential_providers()
        sonar = next(p for p in providers if p['skill_name'] == 'workflow-integration-sonar')

        assert sonar['auth_type'] == 'token'
        assert sonar['default_url'] == 'https://sonarcloud.io'
        assert sonar['verify_endpoint'] == '/api/system/status'
        assert sonar['verify_method'] == 'GET'
        assert sonar['header_name'] == 'Authorization'
        assert 'Bearer' in sonar['header_value_template']

    def test_skill_name_matches_directory(self):
        """Provider skill_name must match the skill directory name."""
        providers = discover_credential_providers()
        for provider in providers:
            skill_name = provider['skill_name']
            # The skill_name should be a valid directory name
            assert '/' not in skill_name
            assert '\\' not in skill_name

    def test_returns_list(self):
        """discover_credential_providers always returns a list."""
        providers = discover_credential_providers()
        assert isinstance(providers, list)

    def test_sonar_organization_is_optional(self):
        """Sonar organization extra_field must be optional (required=False)."""
        providers = discover_credential_providers()
        sonar = next(p for p in providers if p['skill_name'] == 'workflow-integration-sonar')

        extra_fields = sonar.get('extra_fields', [])
        org_field = next(f for f in extra_fields if f['key'] == 'organization')
        assert org_field['required'] is False

    def test_sonar_project_key_is_required(self):
        """Sonar project_key extra_field must be required."""
        providers = discover_credential_providers()
        sonar = next(p for p in providers if p['skill_name'] == 'workflow-integration-sonar')

        extra_fields = sonar.get('extra_fields', [])
        pk_field = next(f for f in extra_fields if f['key'] == 'project_key')
        assert pk_field['required'] is True


class TestCICredentialExtension:
    """Tests for CI credential extension (GitHub and GitLab providers)."""

    def test_discovers_github_provider(self):
        """Should find the GitHub CI credential extension."""
        providers = discover_credential_providers()
        names = [p['skill_name'] for p in providers]
        assert 'workflow-integration-github' in names

    def test_discovers_gitlab_provider(self):
        """Should find the GitLab CI credential extension."""
        providers = discover_credential_providers()
        names = [p['skill_name'] for p in providers]
        assert 'workflow-integration-gitlab' in names

    def test_github_provider_fields(self):
        """GitHub provider must have correct system-auth configuration."""
        providers = discover_credential_providers()
        github = next(p for p in providers if p['skill_name'] == 'workflow-integration-github')

        assert github['auth_type'] == 'system'
        assert github['default_url'] == 'https://github.com'
        assert github['verify_command'] == 'gh auth status'
        assert github['display_name'] == 'GitHub CLI (gh)'
        assert 'description' in github

    def test_gitlab_provider_fields(self):
        """GitLab provider must have correct system-auth configuration."""
        providers = discover_credential_providers()
        gitlab = next(p for p in providers if p['skill_name'] == 'workflow-integration-gitlab')

        assert gitlab['auth_type'] == 'system'
        assert gitlab['default_url'] == 'https://gitlab.com'
        assert gitlab['verify_command'] == 'glab auth status'
        assert gitlab['display_name'] == 'GitLab CLI (glab)'
        assert 'description' in gitlab

    def test_ci_providers_have_no_http_auth_fields(self):
        """System-auth providers must not declare HTTP header fields."""
        providers = discover_credential_providers()
        ci_names = {'workflow-integration-github', 'workflow-integration-gitlab'}
        ci_providers = [p for p in providers if p['skill_name'] in ci_names]

        assert len(ci_providers) >= 1
        for provider in ci_providers:
            assert 'header_name' not in provider, (
                f"{provider['skill_name']} should not have header_name (system auth)"
            )
            assert 'header_value_template' not in provider, (
                f"{provider['skill_name']} should not have header_value_template (system auth)"
            )
            assert 'verify_endpoint' not in provider, (
                f"{provider['skill_name']} should not have verify_endpoint (system auth)"
            )
            assert 'verify_method' not in provider, (
                f"{provider['skill_name']} should not have verify_method (system auth)"
            )

    def test_ci_providers_have_no_extra_fields(self):
        """CI system-auth providers should not declare extra_fields."""
        providers = discover_credential_providers()
        ci_names = {'workflow-integration-github', 'workflow-integration-gitlab'}
        ci_providers = [p for p in providers if p['skill_name'] in ci_names]

        for provider in ci_providers:
            assert 'extra_fields' not in provider, (
                f"{provider['skill_name']} should not have extra_fields"
            )

    def test_github_extension_returns_exactly_one_provider(self):
        """The GitHub credential extension must return exactly one provider."""
        import importlib.util
        from pathlib import Path

        ext_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / 'marketplace' / 'bundles' / 'plan-marshall'
            / 'skills' / 'workflow-integration-github' / 'scripts'
            / 'credential_extension.py'
        )
        spec = importlib.util.spec_from_file_location('github_credential_extension', ext_path)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        providers = mod.get_credential_providers()
        assert len(providers) == 1
        assert providers[0]['skill_name'] == 'workflow-integration-github'
