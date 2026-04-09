#!/usr/bin/env python3
"""Tests for Git provider loading from marshal.json declarations."""

import json

from _providers_core import load_declared_providers  # type: ignore[import-not-found]

import conftest  # noqa: F401


class TestGitProviderFromMarshalJson:
    """Tests for Git provider declarations loaded from marshal.json."""

    def test_loads_git_provider(self, tmp_path, monkeypatch):
        """Should load Git provider from marshal.json."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        config = {
            'providers': [
                {
                    'skill_name': 'workflow-integration-git',
                    'display_name': 'Git CLI',
                    'auth_type': 'system',
                    'default_url': None,
                    'verify_command': 'git config user.name',
                    'description': 'Git CLI integration',
                },
            ],
        }
        (tmp_path / '.plan' / 'marshal.json').write_text(json.dumps(config))

        providers = load_declared_providers()
        names = [p['skill_name'] for p in providers]
        assert 'workflow-integration-git' in names

    def test_git_provider_fields(self, tmp_path, monkeypatch):
        """Git provider must have correct system-auth configuration."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        config = {
            'providers': [
                {
                    'skill_name': 'workflow-integration-git',
                    'display_name': 'Git CLI',
                    'auth_type': 'system',
                    'default_url': None,
                    'verify_command': 'git config user.name',
                    'description': 'Git CLI integration',
                },
            ],
        }
        (tmp_path / '.plan' / 'marshal.json').write_text(json.dumps(config))

        providers = load_declared_providers()
        git = next(p for p in providers if p['skill_name'] == 'workflow-integration-git')

        assert git['auth_type'] == 'system'
        assert git['default_url'] is None
        assert git['verify_command'] == 'git config user.name'
        assert git['display_name'] == 'Git CLI'
        assert 'description' in git

    def test_git_provider_has_no_http_auth_fields(self, tmp_path, monkeypatch):
        """System-auth provider must not declare HTTP header fields."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        config = {
            'providers': [
                {
                    'skill_name': 'workflow-integration-git',
                    'display_name': 'Git CLI',
                    'auth_type': 'system',
                    'default_url': None,
                    'verify_command': 'git config user.name',
                    'description': 'Git CLI integration',
                },
            ],
        }
        (tmp_path / '.plan' / 'marshal.json').write_text(json.dumps(config))

        providers = load_declared_providers()
        git = next(p for p in providers if p['skill_name'] == 'workflow-integration-git')

        assert 'header_name' not in git
        assert 'header_value_template' not in git
        assert 'verify_endpoint' not in git
        assert 'verify_method' not in git

    def test_git_provider_has_no_extra_fields(self, tmp_path, monkeypatch):
        """Git system-auth provider should not declare extra_fields."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        config = {
            'providers': [
                {
                    'skill_name': 'workflow-integration-git',
                    'display_name': 'Git CLI',
                    'auth_type': 'system',
                    'default_url': None,
                    'verify_command': 'git config user.name',
                    'description': 'Git CLI integration',
                },
            ],
        }
        (tmp_path / '.plan' / 'marshal.json').write_text(json.dumps(config))

        providers = load_declared_providers()
        git = next(p for p in providers if p['skill_name'] == 'workflow-integration-git')

        assert 'extra_fields' not in git
