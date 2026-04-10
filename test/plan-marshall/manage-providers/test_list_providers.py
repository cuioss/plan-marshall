#!/usr/bin/env python3
"""Tests for _list_providers.py module.

Covers discover-and-persist (PYTHONPATH scanning + marshal.json persistence)
and list-providers (reading from marshal.json).

Tier 2 (direct import) tests.
"""

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

import conftest  # noqa: F401

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-providers' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_list_providers = _load_module('_list_providers_test', str(_SCRIPTS_DIR / '_list_providers.py'))
_scan_pythonpath_for_providers = _list_providers._scan_pythonpath_for_providers
_load_provider_module = _list_providers._load_provider_module
run_discover_and_persist = _list_providers.run_discover_and_persist
run_list_providers = _list_providers.run_list_providers
_validate_provider_selection = _list_providers._validate_provider_selection


# =============================================================================
# _scan_pythonpath_for_providers Tests
# =============================================================================


class TestScanPythonpathForProviders:
    """Tests for _scan_pythonpath_for_providers()."""

    def test_returns_empty_when_pythonpath_empty(self, monkeypatch):
        """Returns empty list when PYTHONPATH is empty."""
        monkeypatch.setenv('PYTHONPATH', '')
        result = _scan_pythonpath_for_providers()
        assert result == []

    def test_returns_empty_when_pythonpath_unset(self, monkeypatch):
        """Returns empty list when PYTHONPATH is not set."""
        monkeypatch.delenv('PYTHONPATH', raising=False)
        result = _scan_pythonpath_for_providers()
        assert result == []

    def test_discovers_provider_files(self, tmp_path, monkeypatch):
        """Finds *_provider.py files in PYTHONPATH directories."""
        provider_dir = tmp_path / 'providers'
        provider_dir.mkdir()
        # Create a valid provider module
        provider_file = provider_dir / 'test_provider.py'
        provider_file.write_text(
            'def get_provider_declarations():\n'
            '    return [{"skill_name": "plan-marshall:workflow-integration-git", "category": "version-control"}]\n'
        )
        monkeypatch.setenv('PYTHONPATH', str(provider_dir))
        result = _scan_pythonpath_for_providers()
        assert len(result) == 1
        assert result[0]['skill_name'] == 'plan-marshall:workflow-integration-git'

    def test_skips_nonexistent_directories(self, tmp_path, monkeypatch):
        """Skips directories that do not exist."""
        nonexistent = str(tmp_path / 'does-not-exist')
        monkeypatch.setenv('PYTHONPATH', nonexistent)
        result = _scan_pythonpath_for_providers()
        assert result == []

    def test_deduplicates_by_resolved_path(self, tmp_path, monkeypatch):
        """Same file reached via different paths is loaded only once."""
        provider_dir = tmp_path / 'providers'
        provider_dir.mkdir()
        provider_file = provider_dir / 'dup_provider.py'
        provider_file.write_text(
            'def get_provider_declarations():\n'
            '    return [{"skill_name": "dup-skill"}]\n'
        )
        # List same directory twice
        monkeypatch.setenv('PYTHONPATH', f'{provider_dir}{__import__("os").pathsep}{provider_dir}')
        result = _scan_pythonpath_for_providers()
        assert len(result) == 1

    def test_skips_modules_without_get_provider_declarations(self, tmp_path, monkeypatch):
        """Files without get_provider_declarations() are ignored."""
        provider_dir = tmp_path / 'providers'
        provider_dir.mkdir()
        (provider_dir / 'empty_provider.py').write_text('x = 1\n')
        monkeypatch.setenv('PYTHONPATH', str(provider_dir))
        result = _scan_pythonpath_for_providers()
        assert result == []

    def test_skips_modules_that_raise_on_import(self, tmp_path, monkeypatch):
        """Modules that fail to import are silently skipped."""
        provider_dir = tmp_path / 'providers'
        provider_dir.mkdir()
        (provider_dir / 'broken_provider.py').write_text('raise RuntimeError("boom")\n')
        monkeypatch.setenv('PYTHONPATH', str(provider_dir))
        result = _scan_pythonpath_for_providers()
        assert result == []

    def test_collects_from_multiple_directories(self, tmp_path, monkeypatch):
        """Collects providers from multiple PYTHONPATH directories."""
        dir_a = tmp_path / 'a'
        dir_b = tmp_path / 'b'
        dir_a.mkdir()
        dir_b.mkdir()
        (dir_a / 'alpha_provider.py').write_text(
            'def get_provider_declarations():\n'
            '    return [{"skill_name": "alpha"}]\n'
        )
        (dir_b / 'beta_provider.py').write_text(
            'def get_provider_declarations():\n'
            '    return [{"skill_name": "beta"}]\n'
        )
        monkeypatch.setenv('PYTHONPATH', f'{dir_a}{__import__("os").pathsep}{dir_b}')
        result = _scan_pythonpath_for_providers()
        names = [p['skill_name'] for p in result]
        assert 'alpha' in names
        assert 'beta' in names


# =============================================================================
# _load_provider_module Tests
# =============================================================================


class TestLoadProviderModule:
    """Tests for _load_provider_module()."""

    def test_loads_valid_module(self, tmp_path):
        """Loads module and calls get_provider_declarations()."""
        pf = tmp_path / 'valid_provider.py'
        pf.write_text(
            'def get_provider_declarations():\n'
            '    return [{"skill_name": "plan-marshall:workflow-integration-git", "category": "version-control"}]\n'
        )
        result = _load_provider_module(pf)
        assert len(result) == 1
        assert result[0]['skill_name'] == 'plan-marshall:workflow-integration-git'

    def test_returns_empty_for_missing_function(self, tmp_path):
        """Returns empty list when module has no get_provider_declarations."""
        pf = tmp_path / 'no_func_provider.py'
        pf.write_text('x = 42\n')
        result = _load_provider_module(pf)
        assert result == []

    def test_returns_empty_on_import_error(self, tmp_path):
        """Returns empty list when module raises on import."""
        pf = tmp_path / 'err_provider.py'
        pf.write_text('raise ValueError("bad")\n')
        result = _load_provider_module(pf)
        assert result == []

    def test_returns_multiple_declarations(self, tmp_path):
        """A single module can return multiple provider declarations."""
        pf = tmp_path / 'multi_provider.py'
        pf.write_text(
            'def get_provider_declarations():\n'
            '    return [\n'
            '        {"skill_name": "one"},\n'
            '        {"skill_name": "two"},\n'
            '    ]\n'
        )
        result = _load_provider_module(pf)
        assert len(result) == 2


# =============================================================================
# _validate_provider_selection Tests
# =============================================================================


def _make_provider(skill_name: str, category: str) -> dict:
    """Create a minimal provider dict with skill_name and category."""
    return {'skill_name': skill_name, 'category': category}


class TestValidateProviderSelection:
    """Tests for _validate_provider_selection()."""

    def test_valid_all_categories(self):
        """git + github + sonar passes validation (empty errors)."""
        providers = [
            _make_provider('plan-marshall:workflow-integration-git', 'version-control'),
            _make_provider('plan-marshall:workflow-integration-github', 'ci'),
            _make_provider('plan-marshall:workflow-integration-sonar', 'other'),
        ]
        errors = _validate_provider_selection(providers, [
            'plan-marshall:workflow-integration-git',
            'plan-marshall:workflow-integration-github',
            'plan-marshall:workflow-integration-sonar',
        ])
        assert errors == []

    def test_valid_git_and_ci_only(self):
        """git + github passes (CI is optional, no other required)."""
        providers = [
            _make_provider('plan-marshall:workflow-integration-git', 'version-control'),
            _make_provider('plan-marshall:workflow-integration-github', 'ci'),
        ]
        errors = _validate_provider_selection(providers, [
            'plan-marshall:workflow-integration-git',
            'plan-marshall:workflow-integration-github',
        ])
        assert errors == []

    def test_valid_git_only(self):
        """git alone passes (no CI is valid)."""
        providers = [
            _make_provider('plan-marshall:workflow-integration-git', 'version-control'),
            _make_provider('plan-marshall:workflow-integration-github', 'ci'),
        ]
        errors = _validate_provider_selection(providers, [
            'plan-marshall:workflow-integration-git',
        ])
        assert errors == []

    def test_missing_version_control(self):
        """github only fails with version-control error."""
        providers = [
            _make_provider('plan-marshall:workflow-integration-git', 'version-control'),
            _make_provider('plan-marshall:workflow-integration-github', 'ci'),
        ]
        errors = _validate_provider_selection(providers, [
            'plan-marshall:workflow-integration-github',
        ])
        assert len(errors) == 1
        assert 'version-control' in errors[0]

    def test_both_ci_providers_selected(self):
        """git + github + gitlab fails with ci error."""
        providers = [
            _make_provider('plan-marshall:workflow-integration-git', 'version-control'),
            _make_provider('plan-marshall:workflow-integration-github', 'ci'),
            _make_provider('plan-marshall:workflow-integration-gitlab', 'ci'),
        ]
        errors = _validate_provider_selection(providers, [
            'plan-marshall:workflow-integration-git',
            'plan-marshall:workflow-integration-github',
            'plan-marshall:workflow-integration-gitlab',
        ])
        assert len(errors) == 1
        assert 'ci' in errors[0]

    def test_multiple_other_providers_valid(self):
        """git + github + sonar + another_other passes (other has no limit)."""
        providers = [
            _make_provider('plan-marshall:workflow-integration-git', 'version-control'),
            _make_provider('plan-marshall:workflow-integration-github', 'ci'),
            _make_provider('plan-marshall:workflow-integration-sonar', 'other'),
            _make_provider('plan-marshall:custom-tool', 'other'),
        ]
        errors = _validate_provider_selection(
            providers, [
                'plan-marshall:workflow-integration-git',
                'plan-marshall:workflow-integration-github',
                'plan-marshall:workflow-integration-sonar',
                'plan-marshall:custom-tool',
            ],
        )
        assert errors == []


# =============================================================================
# run_discover_and_persist Tests
# =============================================================================


class TestRunDiscoverAndPersist:
    """Tests for run_discover_and_persist()."""

    def test_persists_providers_to_marshal_json(self, tmp_path, monkeypatch):
        """Writes discovered providers to marshal.json with only persisted fields."""
        import _config_core

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        marshal_path = plan_dir / 'marshal.json'
        marshal_path.write_text(json.dumps({'skill_domains': {}}))

        _config_core.PLAN_BASE_DIR = tmp_path
        _config_core.MARSHAL_PATH = marshal_path

        provider_dir = tmp_path / 'ext'
        provider_dir.mkdir()
        (provider_dir / 'sample_provider.py').write_text(
            'def get_provider_declarations():\n'
            '    return [{\n'
            '        "skill_name": "plan-marshall:workflow-integration-git",\n'
            '        "category": "version-control",\n'
            '        "verify_command": "git --version",\n'
            '        "display_name": "Git",\n'
            '        "description": "Git version control",\n'
            '        "default_url": "https://github.com",\n'
            '    }]\n'
        )
        monkeypatch.setenv('PYTHONPATH', str(provider_dir))

        exit_code = run_discover_and_persist(Namespace(providers='plan-marshall:workflow-integration-git'))
        assert exit_code == 0

        config = json.loads(marshal_path.read_text())
        assert 'providers' in config
        assert len(config['providers']) == 1
        persisted = config['providers'][0]
        assert persisted['skill_name'] == 'plan-marshall:workflow-integration-git'
        assert persisted['category'] == 'version-control'
        assert persisted['verify_command'] == 'git --version'
        # Verify runtime fields ARE persisted
        assert 'description' in persisted
        assert persisted['url'] == 'https://github.com'  # mapped from default_url
        # Verify wizard-only fields are NOT persisted
        assert 'display_name' not in persisted
        assert 'auth_type' not in persisted
        assert 'default_url' not in persisted

    def test_rejects_when_no_providers_discovered(self, tmp_path, monkeypatch):
        """Returns validation error when no providers are discovered."""
        import _config_core

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        marshal_path = plan_dir / 'marshal.json'
        marshal_path.write_text(json.dumps({'skill_domains': {}}))

        _config_core.PLAN_BASE_DIR = tmp_path
        _config_core.MARSHAL_PATH = marshal_path

        monkeypatch.setenv('PYTHONPATH', '')

        exit_code = run_discover_and_persist(Namespace(providers='nonexistent'))
        assert exit_code == 1

        # Verify providers were NOT persisted
        config = json.loads(marshal_path.read_text())
        assert 'providers' not in config

    def test_rejects_invalid_provider_selection(self, tmp_path, monkeypatch, capsys):
        """discover-and-persist returns error when validation fails (no VC provider)."""
        import _config_core

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        marshal_path = plan_dir / 'marshal.json'
        marshal_path.write_text(json.dumps({'skill_domains': {}}))

        _config_core.PLAN_BASE_DIR = tmp_path
        _config_core.MARSHAL_PATH = marshal_path

        provider_dir = tmp_path / 'ext'
        provider_dir.mkdir()
        (provider_dir / 'ci_provider.py').write_text(
            'def get_provider_declarations():\n'
            '    return [{"skill_name": "plan-marshall:workflow-integration-github", "category": "ci"}]\n'
        )
        monkeypatch.setenv('PYTHONPATH', str(provider_dir))

        exit_code = run_discover_and_persist(Namespace(providers='plan-marshall:workflow-integration-github'))
        assert exit_code == 1

        # Verify providers were NOT persisted
        config = json.loads(marshal_path.read_text())
        assert 'providers' not in config

    def test_preserves_existing_config(self, tmp_path, monkeypatch):
        """discover-and-persist does not destroy other marshal.json keys."""
        import _config_core

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        marshal_path = plan_dir / 'marshal.json'
        marshal_path.write_text(json.dumps({
            'skill_domains': {'java': {}},
            'custom_key': 'preserved',
        }))

        _config_core.PLAN_BASE_DIR = tmp_path
        _config_core.MARSHAL_PATH = marshal_path
        monkeypatch.setenv('PYTHONPATH', '')

        run_discover_and_persist(Namespace(providers='nonexistent'))

        config = json.loads(marshal_path.read_text())
        assert config['custom_key'] == 'preserved'
        assert config['skill_domains'] == {'java': {}}


# =============================================================================
# run_list_providers Tests
# =============================================================================


class TestRunListProviders:
    """Tests for run_list_providers()."""

    def test_returns_success_with_providers(self, tmp_path, capsys):
        """Lists providers from marshal.json with skill_name, category, verify_command."""
        import _config_core

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        marshal_path = plan_dir / 'marshal.json'
        marshal_path.write_text(json.dumps({
            'providers': [
                {
                    'skill_name': 'plan-marshall:workflow-integration-git',
                    'category': 'version-control',
                    'verify_command': 'git --version',
                },
            ],
        }))

        _config_core.PLAN_BASE_DIR = tmp_path
        _config_core.MARSHAL_PATH = marshal_path

        exit_code = run_list_providers(Namespace())
        assert exit_code == 0

        captured = capsys.readouterr()
        assert 'plan-marshall:workflow-integration-git' in captured.out
        assert 'version-control' in captured.out
        assert 'git --version' in captured.out

    def test_returns_empty_when_no_providers_key(self, tmp_path, capsys):
        """Returns empty list when marshal.json has no providers key."""
        import _config_core

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        marshal_path = plan_dir / 'marshal.json'
        marshal_path.write_text(json.dumps({'skill_domains': {}}))

        _config_core.PLAN_BASE_DIR = tmp_path
        _config_core.MARSHAL_PATH = marshal_path

        exit_code = run_list_providers(Namespace())
        assert exit_code == 0

    def test_outputs_persisted_fields(self, tmp_path, capsys):
        """Output contains persisted fields including url and description."""
        import _config_core

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        marshal_path = plan_dir / 'marshal.json'
        marshal_path.write_text(json.dumps({
            'providers': [
                {
                    'skill_name': 'plan-marshall:workflow-integration-sonar',
                    'category': 'other',
                    'verify_command': 'sonar --version',
                    'url': 'https://sonarcloud.io',
                    'description': 'SonarCloud code analysis',
                },
            ],
        }))

        _config_core.PLAN_BASE_DIR = tmp_path
        _config_core.MARSHAL_PATH = marshal_path

        exit_code = run_list_providers(Namespace())
        assert exit_code == 0

        captured = capsys.readouterr()
        assert 'plan-marshall:workflow-integration-sonar' in captured.out
        assert 'other' in captured.out
        assert 'sonarcloud.io' in captured.out
        assert 'SonarCloud code analysis' in captured.out
        # Verify wizard-only fields are NOT in output
        assert 'display_name' not in captured.out
        assert 'auth_type' not in captured.out
