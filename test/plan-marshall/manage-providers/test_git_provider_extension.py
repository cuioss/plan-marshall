#!/usr/bin/env python3
"""Tests for the Git credential extension provider (workflow-integration-git)."""


from _providers_core import discover_provider_extensions  # type: ignore[import-not-found]

import conftest  # noqa: F401


class TestGitCredentialExtension:
    """Tests for the Git credential extension discovery and fields."""

    def test_discovers_git_provider(self):
        """Should find the Git credential extension via discovery."""
        providers = discover_provider_extensions()
        names = [p['skill_name'] for p in providers]
        assert 'workflow-integration-git' in names

    def test_git_provider_fields(self):
        """Git provider must have correct system-auth configuration."""
        providers = discover_provider_extensions()
        git = next(p for p in providers if p['skill_name'] == 'workflow-integration-git')

        assert git['auth_type'] == 'system'
        assert git['default_url'] is None
        assert git['verify_command'] == 'git config user.name'
        assert git['display_name'] == 'Git CLI'
        assert 'description' in git

    def test_git_provider_has_no_http_auth_fields(self):
        """System-auth provider must not declare HTTP header fields."""
        providers = discover_provider_extensions()
        git = next(p for p in providers if p['skill_name'] == 'workflow-integration-git')

        assert 'header_name' not in git, (
            'workflow-integration-git should not have header_name (system auth)'
        )
        assert 'header_value_template' not in git, (
            'workflow-integration-git should not have header_value_template (system auth)'
        )
        assert 'verify_endpoint' not in git, (
            'workflow-integration-git should not have verify_endpoint (system auth)'
        )
        assert 'verify_method' not in git, (
            'workflow-integration-git should not have verify_method (system auth)'
        )

    def test_git_provider_has_no_extra_fields(self):
        """Git system-auth provider should not declare extra_fields."""
        providers = discover_provider_extensions()
        git = next(p for p in providers if p['skill_name'] == 'workflow-integration-git')

        assert 'extra_fields' not in git, (
            'workflow-integration-git should not have extra_fields'
        )

    def test_git_extension_returns_exactly_one_provider(self):
        """The Git credential extension must return exactly one provider."""
        import importlib.util
        from pathlib import Path

        ext_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / 'marketplace' / 'bundles' / 'plan-marshall'
            / 'skills' / 'workflow-integration-git' / 'scripts'
            / 'git_provider.py'
        )
        spec = importlib.util.spec_from_file_location('git_provider', ext_path)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        git_providers = mod.get_provider_declarations()
        assert len(git_providers) == 1
        assert git_providers[0]['skill_name'] == 'workflow-integration-git'
