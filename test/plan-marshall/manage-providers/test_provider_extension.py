#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for provider loading from marshal.json declarations."""

from _providers_core import load_declared_providers  # type: ignore[import-not-found]
from _providers_fixtures import stage_marshal

import conftest  # noqa: F401

_SONAR_PROVIDER_CONFIG = {
    'providers': [
        {
            'skill_name': 'workflow-integration-sonar',
            'display_name': 'SonarCloud / SonarQube',
            'auth_type': 'token',
            'default_url': 'https://sonarcloud.io',
            'header_name': 'Authorization',
            'header_value_template': 'Bearer {token}',
            'verify_endpoint': '/api/system/status',
            'verify_method': 'GET',
            'description': 'SonarCloud integration',
        },
    ],
}

_GITHUB_PROVIDER = {
    'skill_name': 'workflow-integration-github',
    'display_name': 'GitHub CLI (gh)',
    'auth_type': 'system',
    'default_url': 'https://github.com',
    'verify_command': 'gh auth status',
    'description': 'GitHub integration',
}


class TestProviderLoadingFromMarshalJson:
    """Tests for loading provider declarations from marshal.json."""

    def test_loads_sonar_provider(self, tmp_path, monkeypatch):
        """Should load Sonar provider from marshal.json."""
        stage_marshal(tmp_path, monkeypatch, _SONAR_PROVIDER_CONFIG)

        providers = load_declared_providers()
        names = [p['skill_name'] for p in providers]
        assert 'workflow-integration-sonar' in names

    def test_sonar_provider_fields(self, tmp_path, monkeypatch):
        """Sonar provider must have correct configuration."""
        stage_marshal(tmp_path, monkeypatch, _SONAR_PROVIDER_CONFIG)

        providers = load_declared_providers()
        sonar = next(p for p in providers if p['skill_name'] == 'workflow-integration-sonar')

        assert sonar['auth_type'] == 'token'
        assert sonar['default_url'] == 'https://sonarcloud.io'
        assert sonar['verify_endpoint'] == '/api/system/status'
        assert sonar['verify_method'] == 'GET'
        assert sonar['header_name'] == 'Authorization'
        assert 'Bearer' in sonar['header_value_template']

    def test_returns_list(self, tmp_path, monkeypatch):
        """load_declared_providers always returns a list."""
        stage_marshal(tmp_path, monkeypatch, {'providers': []})

        providers = load_declared_providers()
        assert isinstance(providers, list)

    def test_returns_empty_when_no_marshal_json(self, tmp_path, monkeypatch):
        """Should return empty list when marshal.json does not exist."""
        stage_marshal(tmp_path, monkeypatch, config=None)
        providers = load_declared_providers()
        assert providers == []

    def test_multiple_providers(self, tmp_path, monkeypatch):
        """Should load multiple providers from marshal.json."""
        stage_marshal(
            tmp_path,
            monkeypatch,
            {
                'providers': [
                    {'skill_name': 'provider-a', 'auth_type': 'token'},
                    {'skill_name': 'provider-b', 'auth_type': 'system'},
                ],
            },
        )

        providers = load_declared_providers()
        assert len(providers) == 2
        names = [p['skill_name'] for p in providers]
        assert 'provider-a' in names
        assert 'provider-b' in names


class TestCIProviderFromMarshalJson:
    """Tests for CI provider declarations loaded from marshal.json."""

    def test_loads_github_provider(self, tmp_path, monkeypatch):
        """Should load GitHub CI provider from marshal.json."""
        stage_marshal(tmp_path, monkeypatch, {'providers': [_GITHUB_PROVIDER]})

        providers = load_declared_providers()
        names = [p['skill_name'] for p in providers]
        assert 'workflow-integration-github' in names

    def test_loads_gitlab_provider(self, tmp_path, monkeypatch):
        """Should load GitLab CI provider from marshal.json."""
        config = {
            'providers': [
                {
                    'skill_name': 'workflow-integration-gitlab',
                    'display_name': 'GitLab CLI (glab)',
                    'auth_type': 'system',
                    'default_url': 'https://gitlab.com',
                    'verify_command': 'glab auth status',
                    'description': 'GitLab integration',
                },
            ],
        }
        stage_marshal(tmp_path, monkeypatch, config)

        providers = load_declared_providers()
        names = [p['skill_name'] for p in providers]
        assert 'workflow-integration-gitlab' in names

    def test_system_provider_has_no_http_auth_fields(self, tmp_path, monkeypatch):
        """System-auth providers loaded from marshal.json should not have HTTP auth fields."""
        stage_marshal(tmp_path, monkeypatch, {'providers': [_GITHUB_PROVIDER]})

        providers = load_declared_providers()
        github = next(p for p in providers if p['skill_name'] == 'workflow-integration-github')

        assert 'header_name' not in github
        assert 'header_value_template' not in github
        assert 'verify_endpoint' not in github
        assert 'verify_method' not in github
