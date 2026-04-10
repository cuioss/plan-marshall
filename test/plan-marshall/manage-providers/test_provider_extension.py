#!/usr/bin/env python3
"""Tests for provider loading from marshal.json declarations."""

import json

from _providers_core import load_declared_providers  # type: ignore[import-not-found]

import conftest  # noqa: F401


class TestProviderLoadingFromMarshalJson:
    """Tests for loading provider declarations from marshal.json."""

    def test_loads_sonar_provider(self, tmp_path, monkeypatch):
        """Should load Sonar provider from marshal.json."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        config = {
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
        (tmp_path / '.plan' / 'marshal.json').write_text(json.dumps(config))

        providers = load_declared_providers()
        names = [p['skill_name'] for p in providers]
        assert 'workflow-integration-sonar' in names

    def test_sonar_provider_fields(self, tmp_path, monkeypatch):
        """Sonar provider must have correct configuration."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        config = {
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
        (tmp_path / '.plan' / 'marshal.json').write_text(json.dumps(config))

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
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        (tmp_path / '.plan' / 'marshal.json').write_text('{"providers": []}')

        providers = load_declared_providers()
        assert isinstance(providers, list)

    def test_returns_empty_when_no_marshal_json(self, tmp_path, monkeypatch):
        """Should return empty list when marshal.json does not exist."""
        monkeypatch.chdir(tmp_path)
        providers = load_declared_providers()
        assert providers == []

    def test_multiple_providers(self, tmp_path, monkeypatch):
        """Should load multiple providers from marshal.json."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        config = {
            'providers': [
                {'skill_name': 'provider-a', 'auth_type': 'token'},
                {'skill_name': 'provider-b', 'auth_type': 'system'},
            ],
        }
        (tmp_path / '.plan' / 'marshal.json').write_text(json.dumps(config))

        providers = load_declared_providers()
        assert len(providers) == 2
        names = [p['skill_name'] for p in providers]
        assert 'provider-a' in names
        assert 'provider-b' in names


class TestCIProviderFromMarshalJson:
    """Tests for CI provider declarations loaded from marshal.json."""

    def test_loads_github_provider(self, tmp_path, monkeypatch):
        """Should load GitHub CI provider from marshal.json."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        config = {
            'providers': [
                {
                    'skill_name': 'workflow-integration-github',
                    'display_name': 'GitHub CLI (gh)',
                    'auth_type': 'system',
                    'default_url': 'https://github.com',
                    'verify_command': 'gh auth status',
                    'description': 'GitHub integration',
                },
            ],
        }
        (tmp_path / '.plan' / 'marshal.json').write_text(json.dumps(config))

        providers = load_declared_providers()
        names = [p['skill_name'] for p in providers]
        assert 'workflow-integration-github' in names

    def test_loads_gitlab_provider(self, tmp_path, monkeypatch):
        """Should load GitLab CI provider from marshal.json."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
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
        (tmp_path / '.plan' / 'marshal.json').write_text(json.dumps(config))

        providers = load_declared_providers()
        names = [p['skill_name'] for p in providers]
        assert 'workflow-integration-gitlab' in names

    def test_system_provider_has_no_http_auth_fields(self, tmp_path, monkeypatch):
        """System-auth providers loaded from marshal.json should not have HTTP auth fields."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        config = {
            'providers': [
                {
                    'skill_name': 'workflow-integration-github',
                    'display_name': 'GitHub CLI (gh)',
                    'auth_type': 'system',
                    'default_url': 'https://github.com',
                    'verify_command': 'gh auth status',
                    'description': 'GitHub integration',
                },
            ],
        }
        (tmp_path / '.plan' / 'marshal.json').write_text(json.dumps(config))

        providers = load_declared_providers()
        github = next(p for p in providers if p['skill_name'] == 'workflow-integration-github')

        assert 'header_name' not in github
        assert 'header_value_template' not in github
        assert 'verify_endpoint' not in github
        assert 'verify_method' not in github
