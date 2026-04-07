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
