#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for provider loading from marshal.json declarations."""

from argparse import Namespace
from typing import Any

from _providers_core import load_declared_providers
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

# The CLI lane declares no ``default_url``: gh resolves its own host, so the
# provider carries no URL at all. Only the REST lane (Sonar above) and the
# version-control git-remote resolution produce one.
_GITHUB_PROVIDER = {
    'skill_name': 'workflow-integration-github',
    'display_name': 'GitHub CLI (gh)',
    'auth_type': 'system',
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
        """A CLI-lane provider carries no HTTP auth fields and no URL.

        The URL assertions are the abstraction boundary: a ``gh``-transport
        provider that declared a REST base URL invited callers to build an HTTP
        client against a lane that has none.
        """
        stage_marshal(tmp_path, monkeypatch, {'providers': [_GITHUB_PROVIDER]})

        providers = load_declared_providers()
        github = next(p for p in providers if p['skill_name'] == 'workflow-integration-github')

        assert 'header_name' not in github
        assert 'header_value_template' not in github
        assert 'verify_endpoint' not in github
        assert 'verify_method' not in github
        assert 'default_url' not in github
        assert 'url' not in github

    def test_rest_lane_provider_keeps_its_default_url(self, tmp_path, monkeypatch):
        """Negative control: the REST lane still declares its base URL.

        Without this, dropping ``default_url`` from every provider would satisfy
        the CLI-lane assertions above while breaking the lane that needs it.
        """
        stage_marshal(tmp_path, monkeypatch, _SONAR_PROVIDER_CONFIG)

        providers = load_declared_providers()
        sonar = next(p for p in providers if p['skill_name'] == 'workflow-integration-sonar')

        assert sonar['default_url'] == 'https://sonarcloud.io'


# =============================================================================
# Declaration-to-marshal.json round trip
# =============================================================================
#
# The declarations below are the DECLARED form — what a ``*_provider.py``
# module returns — not the persisted form, because the round trip below feeds
# them to the real persist path so ``_build_persisted_entry()`` runs.

# CLI lane: gh resolves its own host, so the declaration carries no
# ``default_url`` and none of the token-auth fields.
_CLI_LANE_DECLARATION: dict[str, Any] = {
    'skill_name': 'plan-marshall:workflow-integration-github',
    'category': 'ci',
    'display_name': 'GitHub CLI (gh)',
    'description': 'GitHub integration',
    'verify_command': 'gh auth status',
    'detection': {'url_patterns': [r'github\.com'], 'directory_markers': ['.github']},
}

# REST lane: the declared ``default_url`` is the only thing that produces a
# persisted ``url`` for a non-version-control provider.
_REST_LANE_DECLARATION: dict[str, Any] = {
    'skill_name': 'plan-marshall:workflow-integration-sonar',
    'category': 'other',
    'display_name': 'SonarCloud / SonarQube',
    'description': 'SonarCloud integration',
    'default_url': 'https://sonarcloud.io',
    'header_name': 'Authorization',
    'header_value_template': 'Bearer {token}',
    'verify_endpoint': '/api/system/status',
    'verify_method': 'GET',
}

# Cardinality requires exactly one version-control provider in any activation,
# so the round trip carries one. Its url comes from the git remote rather than
# from a declaration — the third derivation route, stubbed below so the
# assertion does not depend on the developer's checkout.
_VERSION_CONTROL_DECLARATION: dict[str, Any] = {
    'skill_name': 'plan-marshall:workflow-integration-git',
    'category': 'version-control',
    'display_name': 'Git',
    'description': 'Git integration',
    'verify_command': 'git config user.name',
}

_STUBBED_REMOTE_URL = 'https://github.com/cuioss/plan-marshall.git'


class TestDiscoverAndPersistRoundTrip:
    """The declaration-to-marshal.json round trip through _build_persisted_entry.

    Staging an already-persisted entry and reading it back asserts the persisted
    shape at both ends of the trip, so the mapping that produces it never runs:
    a change reintroducing ``default_url`` on a CI declaration would leave such
    assertions green while marshal.json regained the ``url`` key. These drive the
    real path instead — the declaration goes in, ``_build_persisted_entry()``
    maps it, and both the persisted entry and the ``list-providers`` rendering
    are read back out.

    The CLI and REST declarations are a matched control pair: absence asserted
    on one lane means nothing unless the other lane still produces the field.
    """

    @staticmethod
    def _persist(tmp_path, monkeypatch) -> list[dict]:
        """Activate all three declarations through the real persist path.

        Returns the ``providers`` list read back out of the staged marshal.json.
        """
        import _list_providers

        declarations = [_CLI_LANE_DECLARATION, _REST_LANE_DECLARATION, _VERSION_CONTROL_DECLARATION]

        stage_marshal(tmp_path, monkeypatch, {'providers': []})
        monkeypatch.setattr(_list_providers, '_scan_for_providers', lambda: declarations)
        monkeypatch.setattr(_list_providers, '_get_git_remote_url', lambda: _STUBBED_REMOTE_URL)
        monkeypatch.setattr(_list_providers, 'output_toon', lambda payload: None)

        selected = ','.join(d['skill_name'] for d in declarations)
        assert _list_providers.run_discover_and_persist(Namespace(providers=selected)) == 0

        return load_declared_providers()

    @staticmethod
    def _entry(providers: list[dict], skill_name: str) -> dict:
        """Return the persisted entry for ``skill_name``."""
        return next(p for p in providers if p['skill_name'] == skill_name)

    def test_cli_lane_persists_no_url_key(self, tmp_path, monkeypatch):
        """Positive control: a CLI-lane declaration persists with no url key.

        Asserted as key ABSENCE rather than an empty value, because an entry
        carrying ``url: ''`` is exactly the blank-URL state the contract exists
        to keep out of marshal.json.
        """
        providers = self._persist(tmp_path, monkeypatch)

        assert 'url' not in self._entry(providers, 'plan-marshall:workflow-integration-github')

    def test_rest_lane_persists_url_mapped_from_default_url(self, tmp_path, monkeypatch):
        """Negative control: the REST lane's declared default_url becomes url.

        This is what proves the assertion above measures the lane split rather
        than a field that stopped being persisted for every provider.
        """
        providers = self._persist(tmp_path, monkeypatch)

        sonar = self._entry(providers, 'plan-marshall:workflow-integration-sonar')
        assert sonar['url'] == 'https://sonarcloud.io'

    def test_version_control_lane_resolves_url_from_the_git_remote(self, tmp_path, monkeypatch):
        """The version-control route produces a url without declaring one."""
        providers = self._persist(tmp_path, monkeypatch)

        git = self._entry(providers, 'plan-marshall:workflow-integration-git')
        assert git['url'] == _STUBBED_REMOTE_URL

    def test_verify_command_persists_for_the_declaring_lane_only(self, tmp_path, monkeypatch):
        """verify_command selects the CLI lane, so only a declarer persists one.

        The same per-lane split the persisted-schema table records: required for
        the CLI lane, absent for the REST lane.
        """
        providers = self._persist(tmp_path, monkeypatch)

        github = self._entry(providers, 'plan-marshall:workflow-integration-github')
        assert github['verify_command'] == 'gh auth status'
        assert 'verify_command' not in self._entry(providers, 'plan-marshall:workflow-integration-sonar')

    def test_wizard_time_declaration_fields_are_not_persisted(self, tmp_path, monkeypatch):
        """Only the activation subset survives the trip into marshal.json."""
        providers = self._persist(tmp_path, monkeypatch)

        github = self._entry(providers, 'plan-marshall:workflow-integration-github')
        sonar = self._entry(providers, 'plan-marshall:workflow-integration-sonar')

        assert 'detection' not in github
        assert 'display_name' not in github
        for key in ('default_url', 'header_name', 'header_value_template', 'verify_endpoint', 'verify_method'):
            assert key not in sonar

    def test_list_providers_omits_the_url_key_for_the_cli_lane(self, tmp_path, monkeypatch):
        """The operator-visible rendering omits url rather than emitting ''.

        An entry persisted without a url must not reappear here as a blank
        string, which reads as a provider configured with an empty URL.
        """
        import _list_providers

        self._persist(tmp_path, monkeypatch)

        captured: dict[str, Any] = {}
        monkeypatch.setattr(_list_providers, 'output_toon', captured.update)
        assert _list_providers.run_list_providers(Namespace()) == 0

        rendered: list[dict[str, Any]] = captured['providers']
        listed = {p['skill_name']: p for p in rendered}
        assert 'url' not in listed['plan-marshall:workflow-integration-github']
        assert listed['plan-marshall:workflow-integration-sonar']['url'] == 'https://sonarcloud.io'
