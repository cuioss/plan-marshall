#!/usr/bin/env python3
"""Tests for _cmd_ci.py module.

Covers CI provider lookup from marshal.json providers[], persist verb,
and edge cases not covered by test_plan_marshall_config.py happy-path tests.

Tier 2 (direct import) tests.
"""

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

from test_helpers import (
    create_marshal_json,
    patch_config_paths,
)

import conftest  # noqa: F401
from conftest import PlanContext

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-config' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_ci = _load_module('_cmd_ci_test', str(_SCRIPTS_DIR / '_cmd_ci.py'))
cmd_ci = _cmd_ci.cmd_ci
_find_ci_provider = _cmd_ci._find_ci_provider
_get_ci_data = _cmd_ci._get_ci_data


# =============================================================================
# _find_ci_provider Tests
# =============================================================================


class TestFindCiProvider:
    """Tests for _find_ci_provider()."""

    def test_finds_github_provider(self):
        """Finds provider with skill_name starting with workflow-integration-gi."""
        providers = [
            {'skill_name': 'workflow-integration-sonar', 'auth_type': 'token'},
            {'skill_name': 'workflow-integration-github', 'auth_type': 'system'},
        ]
        result = _find_ci_provider(providers)
        assert result is not None
        assert result['skill_name'] == 'workflow-integration-github'

    def test_finds_gitlab_provider(self):
        """Finds GitLab provider matching the prefix."""
        providers = [
            {'skill_name': 'workflow-integration-gitlab', 'auth_type': 'system'},
        ]
        result = _find_ci_provider(providers)
        assert result is not None
        assert result['skill_name'] == 'workflow-integration-gitlab'

    def test_returns_none_when_no_ci_provider(self):
        """Returns None when no CI provider exists."""
        providers = [
            {'skill_name': 'workflow-integration-sonar', 'auth_type': 'token'},
        ]
        result = _find_ci_provider(providers)
        assert result is None

    def test_returns_none_for_empty_list(self):
        """Returns None for empty providers list."""
        assert _find_ci_provider([]) is None

    def test_requires_system_auth_type(self):
        """Provider must have auth_type=system to match."""
        providers = [
            {'skill_name': 'workflow-integration-github', 'auth_type': 'token'},
        ]
        result = _find_ci_provider(providers)
        assert result is None


# =============================================================================
# _get_ci_data Tests
# =============================================================================


class TestGetCiData:
    """Tests for _get_ci_data()."""

    def test_extracts_ci_fields(self):
        """Extracts provider, repo_url, detected_at from matching entry."""
        providers = [
            {
                'skill_name': 'workflow-integration-github',
                'auth_type': 'system',
                'provider': 'github',
                'repo_url': 'https://github.com/org/repo',
                'detected_at': '2025-01-15T10:00:00Z',
            },
        ]
        data = _get_ci_data(providers)
        assert data['provider'] == 'github'
        assert data['repo_url'] == 'https://github.com/org/repo'
        assert data['detected_at'] == '2025-01-15T10:00:00Z'

    def test_returns_empty_when_no_match(self):
        """Returns empty dict when no CI provider found."""
        providers = [
            {'skill_name': 'workflow-integration-sonar', 'auth_type': 'token'},
        ]
        assert _get_ci_data(providers) == {}

    def test_defaults_provider_to_unknown(self):
        """Defaults provider field to 'unknown' when not set."""
        providers = [
            {
                'skill_name': 'workflow-integration-github',
                'auth_type': 'system',
            },
        ]
        data = _get_ci_data(providers)
        assert data['provider'] == 'unknown'


# =============================================================================
# cmd_ci persist Tests
# =============================================================================


class TestCiPersist:
    """Tests for ci persist verb."""

    def test_persist_updates_provider_entry(self):
        """persist writes provider and repo_url to CI provider entry."""
        with PlanContext() as ctx:
            create_marshal_json(ctx.fixture_dir)
            patch_config_paths(ctx.fixture_dir)

            result = cmd_ci(Namespace(
                verb='persist',
                provider='github',
                repo_url='https://github.com/new/repo',
                tools=None,
                git_present=None,
            ))

            assert result['status'] == 'success'
            assert result['provider'] == 'github'
            assert result['repo_url'] == 'https://github.com/new/repo'

            # Verify persisted in marshal.json
            config = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
            ci_entry = None
            for p in config.get('providers', []):
                if p.get('skill_name', '').startswith('workflow-integration-gi'):
                    ci_entry = p
                    break
            assert ci_entry is not None
            assert ci_entry['provider'] == 'github'
            assert ci_entry['repo_url'] == 'https://github.com/new/repo'
            assert ci_entry['detected_at'] is not None

    def test_persist_with_tools_updates_run_config(self):
        """persist with tools also updates run-configuration.json."""
        with PlanContext() as ctx:
            create_marshal_json(ctx.fixture_dir)
            patch_config_paths(ctx.fixture_dir)

            result = cmd_ci(Namespace(
                verb='persist',
                provider='github',
                repo_url='https://github.com/org/repo',
                tools='git,gh,python3',
                git_present='true',
            ))

            assert result['status'] == 'success'

            # Verify run-configuration.json updated
            run_config = json.loads((ctx.fixture_dir / 'run-configuration.json').read_text())
            assert 'gh' in run_config['ci']['authenticated_tools']
            assert run_config['ci']['git_present'] is True

    def test_persist_fails_without_ci_provider(self):
        """persist fails when no CI provider in providers list."""
        with PlanContext() as ctx:
            # Create marshal.json with no CI provider
            marshal_path = ctx.fixture_dir / 'marshal.json'
            marshal_path.write_text(json.dumps({
                'providers': [
                    {'skill_name': 'workflow-integration-sonar', 'auth_type': 'token'},
                ],
            }))
            patch_config_paths(ctx.fixture_dir)

            result = cmd_ci(Namespace(
                verb='persist',
                provider='github',
                repo_url='https://github.com/org/repo',
                tools=None,
                git_present=None,
            ))

            assert result['status'] == 'error'
            assert 'discover-and-persist' in result['error']


# =============================================================================
# cmd_ci set-provider Edge Cases
# =============================================================================


class TestCiSetProviderEdgeCases:
    """Edge case tests for ci set-provider verb."""

    def test_set_provider_fails_without_ci_provider(self):
        """set-provider fails when no CI provider in providers list."""
        with PlanContext() as ctx:
            marshal_path = ctx.fixture_dir / 'marshal.json'
            marshal_path.write_text(json.dumps({'providers': []}))
            patch_config_paths(ctx.fixture_dir)

            result = cmd_ci(Namespace(
                verb='set-provider',
                provider='github',
                repo_url='https://github.com/org/repo',
            ))

            assert result['status'] == 'error'
            assert 'discover-and-persist' in result['error']


# =============================================================================
# cmd_ci unknown verb
# =============================================================================


class TestCiUnknownVerb:
    """Tests for unknown verb handling."""

    def test_unknown_verb_returns_error(self):
        """Unknown verb returns error status."""
        with PlanContext() as ctx:
            create_marshal_json(ctx.fixture_dir)
            patch_config_paths(ctx.fixture_dir)

            result = cmd_ci(Namespace(verb='nonexistent'))

            assert result['status'] == 'error'
            assert 'Unknown' in result['error']


# =============================================================================
# cmd_ci get with empty providers
# =============================================================================


class TestCiGetEmptyProviders:
    """Tests for ci get/get-provider with no providers."""

    def test_get_returns_empty_ci_when_no_providers(self):
        """ci get returns empty ci dict when providers list is empty."""
        with PlanContext() as ctx:
            marshal_path = ctx.fixture_dir / 'marshal.json'
            marshal_path.write_text(json.dumps({'providers': []}))
            patch_config_paths(ctx.fixture_dir)

            result = cmd_ci(Namespace(verb='get'))

            assert result['status'] == 'success'
            assert result['ci'] == {}

    def test_get_provider_returns_unknown_when_no_providers(self):
        """ci get-provider returns unknown when no CI provider found."""
        with PlanContext() as ctx:
            marshal_path = ctx.fixture_dir / 'marshal.json'
            marshal_path.write_text(json.dumps({'providers': []}))
            patch_config_paths(ctx.fixture_dir)

            result = cmd_ci(Namespace(verb='get-provider'))

            assert result['status'] == 'success'
            assert result['provider'] == 'unknown'
            assert result['confidence'] == 'unknown'
